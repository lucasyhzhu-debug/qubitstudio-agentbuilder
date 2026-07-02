import json
from pathlib import Path
from fastapi.testclient import TestClient
from studio import server

class _FakeSession:
    def __init__(self):
        self.spec = {"plugin": {"name": "demo"}, "components": []}
    async def send(self, msg):
        yield {"type": "token", "text": "Hi "}
        yield {"type": "token", "text": "there"}
        yield {"type": "done", "spec": self.spec, "studio": None}

def test_new_session_returns_id():
    c = TestClient(server.app)
    r = c.post("/api/session/new")
    assert r.status_code == 200 and "session_id" in r.json()

def test_chat_streams_tokens_then_done(monkeypatch):
    c = TestClient(server.app)
    sid = c.post("/api/session/new").json()["session_id"]
    server.SESSIONS[sid] = _FakeSession()
    with c.stream("POST", "/api/chat", json={"session_id": sid, "message": "hi"}) as r:
        body = "".join(chunk for chunk in r.iter_text())
    assert "Hi " in body and "there" in body
    assert '"type": "done"' in body or '"type":"done"' in body
    assert "demo" in body  # the spec rode the done event

def test_spec_endpoint_returns_current():
    c = TestClient(server.app)
    sid = c.post("/api/session/new").json()["session_id"]
    server.SESSIONS[sid] = _FakeSession()
    r = c.get("/api/spec", params={"session_id": sid})
    assert r.json()["spec"]["plugin"]["name"] == "demo"

def test_index_served():
    c = TestClient(server.app)
    assert c.get("/").status_code == 200


class _FakeExporter:
    async def build(self, spec, run_evals=True):
        yield {"type": "stage", "name": "generate", "status": "running"}
        grade = "verified" if run_evals else "validated"
        yield {"type": "done", "grade": grade, "plugin_path": "dist/demo.plugin"}

def test_export_streams_and_caches_result(monkeypatch):
    c = TestClient(server.app)
    sid = c.post("/api/session/new").json()["session_id"]
    server.SESSIONS[sid] = _FakeSession()
    monkeypatch.setattr(server, "Exporter", lambda *a, **k: _FakeExporter())
    with c.stream("POST", "/api/export", json={"session_id": sid, "run_evals": True}) as r:
        body = "".join(r.iter_text())
    assert "generate" in body and "verified" in body
    res = c.get("/api/export/result", params={"session_id": sid}).json()
    assert res["result"]["grade"] == "verified"

def test_export_defaults_to_no_evals(monkeypatch):
    # No run_evals in the body → evals OFF for now → grade "validated".
    c = TestClient(server.app)
    sid = c.post("/api/session/new").json()["session_id"]
    server.SESSIONS[sid] = _FakeSession()
    monkeypatch.setattr(server, "Exporter", lambda *a, **k: _FakeExporter())
    with c.stream("POST", "/api/export", json={"session_id": sid}) as r:
        body = "".join(r.iter_text())
    assert "validated" in body and "verified" not in body

def test_export_refuses_without_spec():
    c = TestClient(server.app)
    sid = c.post("/api/session/new").json()["session_id"]
    server.SESSIONS[sid].spec = None  # real ChatSession, no spec yet
    with c.stream("POST", "/api/export", json={"session_id": sid}) as r:
        body = "".join(r.iter_text())
    assert "error" in body and "no spec" in body.lower()

def test_load_accepts_valid_spec():
    c = TestClient(server.app)
    spec = {"plugin": {"name": "loaded"}, "components": []}
    r = c.post("/api/session/load", json={"spec": spec})
    assert r.status_code == 200
    sid = r.json()["session_id"]
    assert server.SESSIONS[sid].spec["plugin"]["name"] == "loaded"

def test_load_rejects_junk():
    c = TestClient(server.app)
    r = c.post("/api/session/load", json={"spec": {"nope": 1}})
    assert r.status_code == 400

def test_new_session_defaults_to_workshop():
    c = TestClient(server.app)
    r = c.post("/api/session/new")               # bare POST, no body — must keep working
    assert r.status_code == 200 and r.json()["mode"] == "workshop"
    sid = r.json()["session_id"]
    assert server.SESSIONS[sid].catalog_ids       # shelf ids wired in
    assert "crm" in server.SESSIONS[sid].catalog_ids

def test_new_session_architect_mode():
    c = TestClient(server.app)
    r = c.post("/api/session/new", json={"mode": "architect"})
    assert r.json()["mode"] == "architect"
    assert server.SESSIONS[r.json()["session_id"]].catalog_ids is None

def test_new_session_junk_mode_falls_back_to_workshop():
    c = TestClient(server.app)
    r = c.post("/api/session/new", json={"mode": "banana"})
    assert r.json()["mode"] == "workshop"

def test_chat_done_carries_studio(monkeypatch):
    class _FakeStudioSession:
        spec = None
        async def send(self, msg):
            yield {"type": "token", "text": "hi"}
            yield {"type": "done", "spec": None, "studio": {"picks": ["crm"], "name": None, "ready": False}}
    c = TestClient(server.app)
    sid = c.post("/api/session/new").json()["session_id"]
    server.SESSIONS[sid] = _FakeStudioSession()
    with c.stream("POST", "/api/chat", json={"session_id": sid, "message": "hi"}) as r:
        body = "".join(r.iter_text())
    assert '"picks"' in body and '"crm"' in body


# --- onboarding endpoints (onboarding-cards spec §5.2) ---
import base64 as _b64mod

def _iso_now():
    return "2026-07-02T00:00:00+00:00"

def _ob(monkeypatch, tmp_path, **state):
    from studio import onboarding as ob
    monkeypatch.setattr(ob, "STATE_PATH", tmp_path / "onboarding.json")
    monkeypatch.setattr(ob, "STAGING", tmp_path / "inbox")
    if state:
        ob.save_state(state)
    return ob

def test_onboarding_get_default(monkeypatch, tmp_path):
    _ob(monkeypatch, tmp_path)
    c = TestClient(server.app)
    r = c.get("/api/onboarding")
    assert r.status_code == 200 and r.json()["completed"] is False

def test_onboarding_name_and_file_and_folder(monkeypatch, tmp_path):
    ob = _ob(monkeypatch, tmp_path)
    c = TestClient(server.app)
    assert c.post("/api/onboarding/name", json={"name": "Ada"}).json()["ok"]
    b64 = _b64mod.b64encode(b"# cv").decode()
    assert c.post("/api/onboarding/materials", json={"file": {"name": "cv.md", "b64": b64}}).json()["ok"]
    d = tmp_path / "essays"; d.mkdir()
    assert c.post("/api/onboarding/materials", json={"folder": str(d)}).json()["ok"]
    assert c.post("/api/onboarding/materials", json={"folder": str(tmp_path / "no")}).json()["ok"] is False

def test_onboarding_complete_requires_second_brain(monkeypatch, tmp_path):
    _ob(monkeypatch, tmp_path, name="Ada")
    c = TestClient(server.app)
    with c.stream("POST", "/api/onboarding/complete") as r:
        body = "".join(r.iter_text())
    assert "second brain" in body and "preflight" in body

def test_onboarding_complete_inline_distill_and_profile(monkeypatch, tmp_path):
    ob = _ob(monkeypatch, tmp_path, name="Ada")
    c = TestClient(server.app)
    c.post("/api/onboarding/second-brain", json={"path": str(tmp_path / "sb")})
    # Simulate a restart that already cleared staging: the copied file sits in the
    # second brain's inbox — the fallback may only distill it because it holds files (C1).
    (tmp_path / "sb" / "inbox" / "onboarding" / "cv.md").write_text("# cv", encoding="utf-8")
    async def fake_distill(sources, timeout=180):
        return "# Ada\n\nBuilt engines."
    monkeypatch.setattr(server._distiller, "distill", fake_distill)
    server._DISTILL_TASK = None                      # restart-lost-task path (review I1)
    with c.stream("POST", "/api/onboarding/complete") as r:
        body = "".join(r.iter_text())
    assert "engines" in body
    assert '"type": "profile"' in body
    assert (tmp_path / "sb" / "profile.md").exists()
    assert ob.completed() is True

def test_session_new_injects_participant(monkeypatch, tmp_path):
    sb = tmp_path / "sb"; sb.mkdir()
    (sb / "profile.md").write_text("# Ada\nBuilt engines.", encoding="utf-8")
    _ob(monkeypatch, tmp_path, name="Ada", second_brain=str(sb), completed_at=_iso_now(),
        materials={"copied": ["cv.md"], "folders": []})
    c = TestClient(server.app)
    r = c.post("/api/session/new")
    assert r.status_code == 200
    text = server._WORKSHOP_PROMPT.read_text(encoding="utf-8")
    assert "Ada" in text and "engines" in text and "studio event" not in text

def test_session_new_onboarding_contract_when_incomplete(monkeypatch, tmp_path):
    _ob(monkeypatch, tmp_path, name="Ada")
    c = TestClient(server.app)
    c.post("/api/session/new")
    text = server._WORKSHOP_PROMPT.read_text(encoding="utf-8")
    assert "studio event" in text

def test_session_new_degrades_when_sb_missing(monkeypatch, tmp_path):
    _ob(monkeypatch, tmp_path, name="Ada", second_brain=str(tmp_path / "gone"),
        completed_at=_iso_now())
    c = TestClient(server.app)
    r = c.post("/api/session/new")                   # must not 500 (review I4)
    assert r.status_code == 200
    text = server._WORKSHOP_PROMPT.read_text(encoding="utf-8")
    # heading form uniquely marks the injected participant section; the always-on ask
    # contract legitimately contains the prose "The participant's answer ..." (merged code).
    assert "# The participant" not in text

def test_onboarding_complete_skip_all_no_distill_stub_profile(monkeypatch, tmp_path):
    # Skip-all path (final review C1): second brain set, its inbox/onboarding dir exists
    # but is EMPTY (set_second_brain always creates it) — the inline-restart fallback
    # must NOT distill an empty dir into a hallucinated profile.
    import pytest
    sb = tmp_path / "sb"
    (sb / "inbox" / "onboarding").mkdir(parents=True)
    _ob(monkeypatch, tmp_path, name="Ada", second_brain=str(sb))
    async def never_distill(sources, timeout=180):
        pytest.fail("distill must not run on the skip-all path")
    monkeypatch.setattr(server._distiller, "distill", never_distill)
    server._DISTILL_TASK = None
    c = TestClient(server.app)
    with c.stream("POST", "/api/onboarding/complete") as r:
        body = "".join(r.iter_text())
    assert '"distilled": false' in body
    assert (sb / "profile.md").exists()               # stub profile written

def test_compose_uses_second_brain_vault(monkeypatch, tmp_path):
    sb = tmp_path / "sb"; sb.mkdir()
    (sb / "profile.md").write_text("x", encoding="utf-8")
    _ob(monkeypatch, tmp_path, name="Ada", second_brain=str(sb), completed_at=_iso_now())
    seen = {}
    async def fake_compose(picks, name, outdir, vault_dir):
        seen["vault"] = str(vault_dir)
        yield {"type": "done", "grade": "composed", "plugin_path": "x", "vault_path": str(vault_dir)}
    monkeypatch.setattr(server._composer, "compose", fake_compose)
    c = TestClient(server.app)
    with c.stream("POST", "/api/compose", json={"picks": ["crm"], "name": "my cos"}) as r:
        "".join(r.iter_text())
    assert seen["vault"] == str(sb)

def test_compose_default_vault_is_in_home(monkeypatch, tmp_path):
    # No completed onboarding → the default vault is INSIDE the agent home (lean §5),
    # not the old dist/<slug>-vault sibling.
    _ob(monkeypatch, tmp_path)
    seen = {}
    async def fake_compose(picks, name, outdir, vault_dir):
        seen["vault"] = Path(vault_dir)
        yield {"type": "done", "grade": "composed", "plugin_path": "x", "vault_path": str(vault_dir)}
    monkeypatch.setattr(server._composer, "compose", fake_compose)
    c = TestClient(server.app)
    with c.stream("POST", "/api/compose", json={"picks": ["crm"], "name": "my cos"}) as r:
        "".join(r.iter_text())
    assert seen["vault"] == server._composer._REPO / "dist" / "my-cos-cos" / "vault"

# --- beats replay endpoint (dossier spec §4.1/§10) ---

def test_beats_endpoint_unknown_session_404():
    c = TestClient(server.app)
    assert c.get("/api/session/not-a-session/beats").status_code == 404

def test_beats_endpoint_returns_accumulated_and_last_compose():
    c = TestClient(server.app)
    sid = c.post("/api/session/new").json()["session_id"]
    server.SESSIONS[sid].beats = [
        {"user": "Begin the workshop interview.",
         "prose": 'Welcome to the studio.\n```studio\n{"picks": []}\n```',
         "studio": {"picks": [], "name": None, "ready": False, "ask": None,
                    "chapter": {"title": "Welcome", "phase": "welcome", "blocks": []}}},
        {"user": "I drown in email.",
         "prose": 'Noted.\n```studio\n{"picks": ["tasks"]}\n```',
         "studio": {"picks": ["tasks"], "name": None, "ready": False, "ask": None,
                    "chapter": None}},
    ]
    server.LAST_COMPOSE = None
    out = c.get(f"/api/session/{sid}/beats").json()
    assert out["session_id"] == sid and len(out["beats"]) == 2
    # prose + studio state sufficient to re-render the document (spec §10)
    assert "Welcome to the studio." in out["beats"][0]["prose"]
    assert out["beats"][0]["studio"]["chapter"]["phase"] == "welcome"
    assert out["beats"][1]["studio"]["picks"] == ["tasks"]
    assert out["last_compose"] is None      # no build yet this studio run
    # gate-2 S6: the payload piggybacks the server's last compose so a reload
    # restores lastDone — replayed connect chapters keep their live key rows.
    server.LAST_COMPOSE = {"plugin_path": "x", "install": "cd x ; claude",
                           "integrations": ["linear"], "picks": ["tasks"]}
    out = c.get(f"/api/session/{sid}/beats").json()
    assert out["last_compose"]["install"] == "cd x ; claude"
    server.LAST_COMPOSE = None              # leave the module global clean

def test_compose_done_captured_for_replay_and_first_breath(monkeypatch, tmp_path):
    # gate-2 S6: compose_endpoint records its own done event in LAST_COMPOSE — the
    # beats payload (above) and Task 14's first breath both read it.
    _ob(monkeypatch, tmp_path)
    server.LAST_COMPOSE = None
    async def fake_compose(picks, name, outdir, vault_dir):
        yield {"type": "done", "grade": "composed", "plugin_path": str(tmp_path),
               "vault_path": "v", "integrations": ["linear"], "install": "cd x ; claude"}
    monkeypatch.setattr(server._composer, "compose", fake_compose)
    c = TestClient(server.app)
    with c.stream("POST", "/api/compose", json={"picks": ["tasks"], "name": "atlas"}) as r:
        "".join(r.iter_text())
    assert server.LAST_COMPOSE["plugin_path"] == str(tmp_path)
    assert server.LAST_COMPOSE["picks"] == ["tasks"]

def test_chat_done_carries_chapter_through_sse(monkeypatch):
    class _FakeChapterSession:
        spec = None
        async def send(self, msg):
            yield {"type": "done", "spec": None,
                   "studio": {"picks": [], "name": None, "ready": False, "ask": None,
                              "chapter": {"title": "Taming the inbox", "phase": "skills",
                                          "blocks": []}}}
    c = TestClient(server.app)
    sid = c.post("/api/session/new").json()["session_id"]
    server.SESSIONS[sid] = _FakeChapterSession()
    with c.stream("POST", "/api/chat", json={"session_id": sid, "message": "hi"}) as r:
        body = "".join(r.iter_text())
    assert '"chapter"' in body and "Taming the inbox" in body
