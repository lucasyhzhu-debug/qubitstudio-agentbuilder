"""FastAPI backend for agent-studio. Local single-user; state in memory. Bind 127.0.0.1 only."""
from __future__ import annotations
import json
import uuid
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from studio import composer as _composer
from studio import keys
from studio import smokes
from studio import tweaker
from studio.chat_session import ChatSession
from studio.exporter import Exporter
from studio.spec_extractor import _is_valid_blueprint
from studio.system_prompt import write_system_prompt

_HERE = Path(__file__).resolve().parent
_STATIC = _HERE / "static"
_SYSTEM_PROMPT = _HERE / ".cache" / "architect-system-prompt.md"
_CATALOG = _HERE / "catalog.json"

app = FastAPI(title="agent-studio")
SESSIONS: dict[str, ChatSession] = {}
EXPORTS: dict[str, dict] = {}
BUILDING: set[str] = set()


@app.post("/api/session/new")
async def new_session() -> JSONResponse:
    write_system_prompt(_SYSTEM_PROMPT)  # idempotent; refreshes from current architect refs
    sid = str(uuid.uuid4())
    SESSIONS[sid] = ChatSession(session_id=sid, system_prompt_path=_SYSTEM_PROMPT)
    return JSONResponse({"session_id": sid})


@app.post("/api/session/load")
async def load_session(req: Request) -> JSONResponse:
    body = await req.json()
    spec = body.get("spec")
    if not _is_valid_blueprint(spec):
        return JSONResponse({"error": "invalid spec"}, status_code=400)
    write_system_prompt(_SYSTEM_PROMPT)
    sid = str(uuid.uuid4())
    s = ChatSession(session_id=sid, system_prompt_path=_SYSTEM_PROMPT)
    s.spec = spec
    SESSIONS[sid] = s
    return JSONResponse({"session_id": sid})


@app.post("/api/chat")
async def chat(req: Request) -> StreamingResponse:
    body = await req.json()
    sid, message = body.get("session_id"), body.get("message", "")
    session = SESSIONS.get(sid)

    async def event_stream():
        if session is None:
            yield _sse({"type": "error", "message": "unknown session"})
            return
        async for ev in session.send(message):
            yield _sse(ev)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/api/spec")
async def get_spec(session_id: str) -> JSONResponse:
    session = SESSIONS.get(session_id)
    return JSONResponse({"spec": session.spec if session else None})


@app.post("/api/export")
async def export(req: Request) -> StreamingResponse:
    body = await req.json()
    sid = body.get("session_id")
    # M3 evals fan out many nested claude runs and are slow; default them OFF for now (grade
    # "validated"). Send run_evals=true to build the verified grade.
    run_evals = bool(body.get("run_evals", False))
    session = SESSIONS.get(sid)

    async def stream():
        if session is None or getattr(session, "spec", None) is None:
            yield _sse_preflight_error("no spec to export")
            return
        if sid in BUILDING:
            yield _sse_preflight_error("build already running")
            return
        BUILDING.add(sid)
        try:
            async for ev in Exporter().build(session.spec, run_evals=run_evals):
                if ev.get("type") in ("done", "error"):
                    EXPORTS[sid] = ev
                yield _sse(ev)
        finally:
            BUILDING.discard(sid)

    return StreamingResponse(stream(), media_type="text/event-stream")


@app.get("/api/export/result")
async def export_result(session_id: str) -> JSONResponse:
    return JSONResponse({"result": EXPORTS.get(session_id)})


@app.post("/api/compose")
async def compose_endpoint(req: Request) -> StreamingResponse:
    body = await req.json()
    picks = body.get("picks") or []
    name = (body.get("name") or "").strip()

    async def stream():
        if not picks or not name:
            yield _sse_preflight_error("pick at least one skill and enter your name")
            return
        slug = _composer._slug(name)
        if not slug:
            yield _sse_preflight_error("couldn't make a plugin name from that — use some letters or numbers (a-z, 0-9)")
            return
        vault = _composer._REPO / "dist" / f"{slug}-vault"
        async for ev in _composer.compose(picks, name, _composer._REPO / "dist", vault):
            yield _sse(ev)

    return StreamingResponse(stream(), media_type="text/event-stream")


@app.post("/api/tweak")
async def tweak_endpoint(req: Request) -> StreamingResponse:
    body = await req.json()
    tree = body.get("tree")
    vault = body.get("vault")
    fields = body.get("fields") or {}

    async def stream():
        if not tree or not Path(tree).exists():
            yield _sse_preflight_error("no plugin tree to personalize")
            return
        # `vault` is optional — the sibling vault output from compose (carries the seeded
        # `{{OWNER_*}}` personality.md). Absent is fine (e.g. export builds have no vault);
        # provided-but-missing is a real preflight error, not silently ignored.
        if vault and not Path(vault).exists():
            yield _sse_preflight_error("vault path given but not found")
            return
        async for ev in tweaker.tweak(Path(tree), fields, vault_dir=Path(vault) if vault else None):
            yield _sse(ev)

    return StreamingResponse(stream(), media_type="text/event-stream")


@app.post("/api/keys/test")
async def keys_test(req: Request) -> JSONResponse:
    """Run the smoke for `integration` with `values`; on success, if `tree` is given,
    persist the values as OS env vars (+ a `.env` reference copy under `tree`) so the
    participant's installed plugin can read them later. Plain JSON, not SSE — this is a
    single quick round trip, not a streamed build.

    `persist_only: true` skips the smoke entirely (used by the google row, which can never
    smoke-test with just a client id/secret — see keyRowHtml in app.js) and just saves."""
    body = await req.json()
    integration = body.get("integration", "")
    values = body.get("values") or {}
    tree = body.get("tree")
    persist_only = bool(body.get("persist_only"))

    if persist_only:
        if not tree:
            return JSONResponse({"ok": False, "message": "no plugin path to save into"})
        try:
            summary = keys.persist(values, Path(tree))
        except Exception as e:
            return JSONResponse({"ok": False, "message": f"couldn't save: {e}"})
        return JSONResponse({"ok": True, "message": "saved — finish the Google consent step at home", **summary})

    result = smokes.smoke(integration, values)
    if result.get("ok") and tree:
        try:
            summary = keys.persist(values, Path(tree))
        except Exception as e:
            return JSONResponse({"ok": True, "message": f"connected — but couldn't save keys locally: {e}. Set them manually (see SETUP)", "written": []})
        result = {**result, **summary}
    return JSONResponse(result)


@app.get("/api/catalog")
async def catalog() -> JSONResponse:
    """The shop's back room — the baseline + à la carte skill shelf. Read live on each
    request so editing catalog.json and refreshing is enough (no restart)."""
    try:
        data = json.loads(_CATALOG.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        data = {"baseline": {"items": []}, "shelf": {"items": []}}
    return JSONResponse(data)


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(_STATIC / "index.html")


app.mount("/static", StaticFiles(directory=_STATIC), name="static")


def _sse(obj: dict) -> str:
    return f"data: {json.dumps(obj)}\n\n"


def _sse_preflight_error(message: str) -> str:
    return _sse({"type": "error", "stage": "preflight", "message": message})
