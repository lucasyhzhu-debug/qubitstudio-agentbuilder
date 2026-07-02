# studio/tests/test_server_compose.py — hermetic: monkeypatch compose (real compose is
# exercised by the composer unit tests with tmp_path); here we assert only the endpoint wiring (P-I2).
from fastapi.testclient import TestClient
from studio import server

def _fake_compose(picks, owner_name, outdir, vault_dir):
    async def gen():
        yield {"type": "stage", "name": "preflight", "status": "ok"}
        yield {"type": "done", "grade": "composed", "plugin_path": f"{outdir}/sam-rivera-cos"}
    return gen()

def test_compose_streams_done(monkeypatch):
    monkeypatch.setattr(server._composer, "compose", _fake_compose)
    c = TestClient(server.app)
    r = c.post("/api/compose", json={"picks": ["crm"], "name": "Sam Rivera"})
    assert r.status_code == 200
    assert '"type": "done"' in r.text and "sam-rivera-cos" in r.text

def test_compose_rejects_empty_picks():
    c = TestClient(server.app)
    r = c.post("/api/compose", json={"picks": [], "name": "Sam"})
    assert '"type": "error"' in r.text


def test_compose_rejects_empty_slug_name():
    # non-ASCII name with no a-z0-9 slugs to "" — must be rejected before compose runs.
    c = TestClient(server.app)
    r = c.post("/api/compose", json={"picks": ["crm"], "name": "李明"})
    assert '"type": "error"' in r.text
    assert '"done"' not in r.text
