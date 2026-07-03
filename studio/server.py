"""FastAPI backend for agent-studio. Local single-user; state in memory. Bind 127.0.0.1 only."""
from __future__ import annotations
import asyncio
import json
import uuid
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from studio import composer as _composer
from studio import distiller as _distiller
from studio import first_breath as _first_breath
from studio import keys
from studio import onboarding as _onboarding
from studio import smokes
from studio import tweaker
from studio.chat_session import ChatSession
from studio.exporter import Exporter
from studio.spec_extractor import _is_valid_blueprint
from studio.system_prompt import write_system_prompt

_HERE = Path(__file__).resolve().parent
_STATIC = _HERE / "static"
_SYSTEM_PROMPT = _HERE / ".cache" / "architect-system-prompt.md"
_WORKSHOP_PROMPT = _HERE / ".cache" / "workshop-system-prompt.md"
_CATALOG = _HERE / "catalog.json"


def _catalog_ids() -> set[str]:
    try:
        data = json.loads(_CATALOG.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()
    return {it["id"] for it in data.get("shelf", {}).get("items", [])
            if isinstance(it, dict) and it.get("id")}


app = FastAPI(title="agent-studio")
SESSIONS: dict[str, ChatSession] = {}
EXPORTS: dict[str, dict] = {}
BUILDING: set[str] = set()
_DISTILL_TASK: asyncio.Task | None = None    # materials distill runs in the background
LAST_COMPOSE: dict | None = None   # this studio run's last successful compose done event
                                   # (+ picks) — piggybacked on the beats payload (gate-2
                                   # S6) and consumed by the first-breath endpoint (D1c)


@app.post("/api/session/new")
async def new_session(req: Request) -> JSONResponse:
    # Tolerant body parse: absent/empty/invalid body -> workshop default (spec §4.1).
    try:
        body = await req.json()
    except Exception:
        body = {}
    mode = body.get("mode") if isinstance(body, dict) else None
    if mode not in ("workshop", "architect"):
        mode = "workshop"
    sid = str(uuid.uuid4())
    if mode == "architect":
        write_system_prompt(_SYSTEM_PROMPT)  # idempotent; refreshes from current architect refs
        SESSIONS[sid] = ChatSession(session_id=sid, system_prompt_path=_SYSTEM_PROMPT)
    else:
        state = _onboarding.load_state()
        participant, onboarding_mode = None, False
        sb = Path(state["second_brain"]) if state.get("second_brain") else None
        if state.get("completed_at") and sb is not None and (sb / "profile.md").exists():
            mats = state.get("materials", {})
            participant = {
                "name": state.get("name", ""),
                "second_brain": str(sb),
                "profile_text": (sb / "profile.md").read_text(encoding="utf-8"),
                "materials_index": ", ".join(mats.get("copied", []) + mats.get("folders", [])),
            }
        elif not state.get("completed_at"):
            onboarding_mode = True
        # completed but second brain missing -> neither section (degrade, review I4)
        write_system_prompt(_WORKSHOP_PROMPT, mode="workshop",
                            participant=participant, onboarding=onboarding_mode)
        SESSIONS[sid] = ChatSession(session_id=sid, system_prompt_path=_WORKSHOP_PROMPT,
                                    catalog_ids=_catalog_ids())
    return JSONResponse({"session_id": sid, "mode": mode})


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


@app.get("/api/session/{session_id}/beats")
async def session_beats(session_id: str) -> JSONResponse:
    """Beats replay (dossier spec §4.1): the accumulated turns of a live session so a
    page reload re-renders the whole document. Survives reloads, NOT studio restarts
    (sessions are in-memory — spec §8 non-goal). `last_compose` rides along (gate-2 S6)
    so the page can restore its launch/connect state (`lastDone`) too."""
    session = SESSIONS.get(session_id)
    if session is None:
        return JSONResponse({"error": "unknown session"}, status_code=404)
    return JSONResponse({"session_id": session_id,
                         "beats": getattr(session, "beats", []),
                         "last_compose": LAST_COMPOSE})


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
        state = _onboarding.load_state()
        if state.get("completed_at") and state.get("second_brain"):
            vault = Path(state["second_brain"])       # onboarding: the second brain IS the vault
        else:
            vault = _composer._REPO / "dist" / f"{slug}-cos" / "vault"   # lean §5: <home>/vault/ default
        async for ev in _composer.compose(picks, name, _composer._REPO / "dist", vault):
            if ev.get("type") == "done":
                global LAST_COMPOSE
                LAST_COMPOSE = {**ev, "picks": list(picks)}
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


@app.post("/api/first-breath")
async def first_breath_endpoint() -> StreamingResponse:
    """One real greeting turn from the composed agent (dossier spec §6.4). The agent
    home comes from OUR OWN compose result — never the request body."""
    async def stream():
        done = LAST_COMPOSE
        if not done or not Path(done.get("plugin_path", "")).is_dir():
            yield _sse_preflight_error("no composed agent yet — build first")
            return
        owner = _onboarding.load_state().get("name") or "there"
        try:
            catalog = json.loads(_CATALOG.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            catalog = {"shelf": {"items": []}}
        prompt = _first_breath.build_greeting_prompt(
            owner, done.get("picks", []), done.get("integrations", []), catalog)
        async for ev in _first_breath.first_breath(Path(done["plugin_path"]), prompt):
            yield _sse(ev)

    return StreamingResponse(stream(), media_type="text/event-stream")


@app.get("/api/catalog")
async def catalog() -> JSONResponse:
    """The shop's back room — the baseline + à la carte skill shelf. Read live on each
    request so editing catalog.json and refreshing is enough (no restart)."""
    try:
        data = json.loads(_CATALOG.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        data = {"baseline": {"items": []}, "shelf": {"items": []}}
    return JSONResponse(data)


# ── Onboarding (onboarding-cards spec §5.2) ───────────────────────────────────
def _ok(state: dict) -> JSONResponse:
    return JSONResponse({"ok": True, **state, "completed": bool(state.get("completed_at"))})


def _bad(e: Exception) -> JSONResponse:
    return JSONResponse({"ok": False, "message": str(e)}, status_code=400)


@app.get("/api/onboarding")
async def onboarding_state() -> JSONResponse:
    return _ok(_onboarding.load_state())


@app.post("/api/onboarding/name")
async def onboarding_name(req: Request) -> JSONResponse:
    body = await req.json()
    try:
        return _ok(_onboarding.set_name(body.get("name", "")))
    except ValueError as e:
        return _bad(e)


@app.post("/api/onboarding/materials")
async def onboarding_materials(req: Request) -> JSONResponse:
    body = await req.json()
    try:
        if body.get("folder"):
            return _ok(_onboarding.register_folder(body["folder"]))
        f = body.get("file") or {}
        return _ok(_onboarding.stage_file(f.get("name", ""), f.get("b64", "")))
    except ValueError as e:
        return _bad(e)


@app.post("/api/onboarding/materials/done")
async def onboarding_materials_done() -> JSONResponse:
    global _DISTILL_TASK
    sources = _onboarding.materials_sources()
    if sources and _DISTILL_TASK is None:
        _DISTILL_TASK = asyncio.create_task(_distiller.distill(sources))
    mats = _onboarding.load_state().get("materials", {})
    return JSONResponse({"ok": True, "copied": mats.get("copied", []),
                         "folders": mats.get("folders", [])})


@app.post("/api/onboarding/second-brain")
async def onboarding_second_brain(req: Request) -> JSONResponse:
    body = await req.json()
    try:
        return _ok(_onboarding.set_second_brain(body.get("path", "")))
    except ValueError as e:
        return _bad(e)


@app.post("/api/onboarding/complete")
async def onboarding_complete() -> StreamingResponse:
    async def stream():
        global _DISTILL_TASK
        state = _onboarding.load_state()
        if not state.get("second_brain"):
            yield _sse_preflight_error("choose your second brain location first")
            return
        task = _DISTILL_TASK
        if task is None:
            # Studio restarted between materials/done and here (review I1): start inline.
            # set_second_brain COPIED staged files into <sb>/inbox/onboarding/; if staging
            # was already cleared, fall back to that dir — but only when it actually holds
            # files, or a skip-all run would distill an empty dir into a hallucinated
            # profile (final review C1).
            sources = _onboarding.materials_sources()
            if not sources:
                moved = Path(state["second_brain"]) / "inbox" / "onboarding"
                if moved.is_dir() and any(f.is_file() for f in moved.iterdir()):
                    sources = [moved]
            task = asyncio.create_task(_distiller.distill(sources)) if sources else None
        yield _sse({"type": "stage", "name": "distill", "status": "running"})
        text = None
        if task is not None:
            try:
                text = await task
            except Exception:
                text = None                 # non-fatal (spec §5.6) — stub profile below
        _DISTILL_TASK = None
        yield _sse({"type": "stage", "name": "distill", "status": "ok" if text else "fail"})
        profile_path = _onboarding.write_profile(text)
        try:
            # Copies live in <sb>/inbox/onboarding/ and the distill has settled — clear
            # staging now (copy-not-move, final review C2). Best-effort: cleanup failure
            # must never break completion.
            if _onboarding.STAGING.exists():
                for f in _onboarding.STAGING.iterdir():
                    if f.is_file():
                        f.unlink()
        except Exception:
            pass
        yield _sse({"type": "profile",
                    "text": profile_path.read_text(encoding="utf-8"),
                    "distilled": bool(text)})
        yield _sse({"type": "done"})

    return StreamingResponse(stream(), media_type="text/event-stream")


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(_STATIC / "index.html")


app.mount("/static", StaticFiles(directory=_STATIC), name="static")


def _sse(obj: dict) -> str:
    return f"data: {json.dumps(obj)}\n\n"


def _sse_preflight_error(message: str) -> str:
    return _sse({"type": "error", "stage": "preflight", "message": message})
