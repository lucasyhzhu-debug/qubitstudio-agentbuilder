import json
from fastapi.testclient import TestClient
from studio import server

class _FakeSession:
    def __init__(self):
        self.spec = {"plugin": {"name": "demo"}, "components": []}
    async def send(self, msg):
        yield {"type": "token", "text": "Hi "}
        yield {"type": "token", "text": "there"}
        yield {"type": "done", "spec": self.spec}

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
