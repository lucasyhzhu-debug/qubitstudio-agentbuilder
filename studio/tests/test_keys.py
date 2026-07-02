# studio/tests/test_keys.py — persist() never touches real OS env/shell profiles in tests
# (monkeypatch _write_os_env); server test monkeypatches smokes.smoke + keys.persist (hermetic,
# style of test_server_compose.py).
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from studio import keys


def test_persist_writes_env_reference_copy(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(keys, "_write_os_env", lambda k, v: calls.append((k, v)))
    out = keys.persist({"LINEAR_API_KEY": "lin_x"}, tmp_path)
    assert (tmp_path / ".env").read_text(encoding="utf-8").strip() == "LINEAR_API_KEY=lin_x"
    assert ("LINEAR_API_KEY", "lin_x") in calls and "LINEAR_API_KEY" in out["written"]


def test_persist_multiple_values_and_env_cmds(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(keys, "_write_os_env", lambda k, v: calls.append((k, v)))
    out = keys.persist({"A": "1", "B": "2"}, tmp_path)
    assert set(out["written"]) == {"A", "B"}
    assert len(out["env_cmds"]) == 2
    assert len(calls) == 2
    text = (tmp_path / ".env").read_text(encoding="utf-8")
    assert "A=1" in text and "B=2" in text


def test_persist_never_calls_real_os_env_writer(tmp_path, monkeypatch):
    # if _write_os_env were NOT monkeypatched here and persist() called subprocess/opened
    # profile files for real, this would be the one place it'd blow up in CI.
    sentinel = {"called": False}

    def fake(k, v):
        sentinel["called"] = True

    monkeypatch.setattr(keys, "_write_os_env", fake)
    keys.persist({"X": "y"}, tmp_path)
    assert sentinel["called"] is True


def test_persist_rejects_newline_value(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(keys, "_write_os_env", lambda k, v: calls.append((k, v)))
    with pytest.raises(ValueError):
        keys.persist({"LINEAR_API_KEY": "lin_x\nrm -rf /"}, tmp_path)
    # nothing written before the reject — validated up front, not mid-loop
    assert calls == []
    assert not (tmp_path / ".env").exists()


def test_posix_export_line_is_shlex_quoted():
    # exercise the line-builder directly (factored out of _write_os_env precisely so this
    # doesn't require monkeypatching os.name / touching a real shell profile).
    value = 'value with "quotes" and $(evil) and `backticks`'
    line = keys._posix_export_line("K", value)
    assert line.startswith("export K=")
    # shlex.quote's single-quote form neutralizes $()/backticks/double-quotes — a raw
    # double-quoted `export K="$(evil)"` would instead let the shell execute $(evil).
    import shlex as _shlex
    assert line.split("=", 1)[1].strip() == _shlex.quote(value)
    # round-trip: the quoted form parses back to exactly one token, the original value.
    rebuilt = _shlex.split(line.split("=", 1)[1])
    assert rebuilt == [value]


def test_api_keys_test_success_persists(tmp_path, monkeypatch):
    from studio import server

    persisted = {}

    def fake_smoke(integration, values):
        return {"ok": True, "message": "connected ✓"}

    def fake_persist(values, tree):
        persisted["values"] = values
        persisted["tree"] = tree
        return {"written": list(values.keys()), "env_cmds": ["setx K V"]}

    monkeypatch.setattr(server.smokes, "smoke", fake_smoke)
    monkeypatch.setattr(server.keys, "persist", fake_persist)

    c = TestClient(server.app)
    r = c.post("/api/keys/test", json={
        "integration": "linear",
        "values": {"LINEAR_API_KEY": "lin_x"},
        "tree": str(tmp_path),
    })
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["message"] == "connected ✓"
    assert body["written"] == ["LINEAR_API_KEY"]
    assert persisted["values"] == {"LINEAR_API_KEY": "lin_x"}
    assert persisted["tree"] == Path(str(tmp_path))


def test_api_keys_test_failure_does_not_persist(monkeypatch):
    from studio import server

    persist_calls = []

    def fake_smoke(integration, values):
        return {"ok": False, "message": "HTTP 401"}

    def fake_persist(values, tree):
        persist_calls.append((values, tree))
        return {"written": [], "env_cmds": []}

    monkeypatch.setattr(server.smokes, "smoke", fake_smoke)
    monkeypatch.setattr(server.keys, "persist", fake_persist)

    c = TestClient(server.app)
    r = c.post("/api/keys/test", json={
        "integration": "linear",
        "values": {"LINEAR_API_KEY": "bad"},
        "tree": "/tmp/whatever",
    })
    assert r.status_code == 200
    body = r.json()
    assert body == {"ok": False, "message": "HTTP 401"}
    assert persist_calls == []


def test_api_keys_test_success_without_tree_skips_persist(monkeypatch):
    from studio import server

    persist_calls = []

    def fake_smoke(integration, values):
        return {"ok": True, "message": "connected ✓"}

    def fake_persist(values, tree):
        persist_calls.append((values, tree))
        return {"written": [], "env_cmds": []}

    monkeypatch.setattr(server.smokes, "smoke", fake_smoke)
    monkeypatch.setattr(server.keys, "persist", fake_persist)

    c = TestClient(server.app)
    r = c.post("/api/keys/test", json={
        "integration": "linear",
        "values": {"LINEAR_API_KEY": "lin_x"},
    })
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert persist_calls == []


def test_api_keys_test_persist_only_skips_smoke_and_persists(tmp_path, monkeypatch):
    from studio import server

    def smoke_must_not_be_called(integration, values):
        raise AssertionError("smoke() must not run for persist_only")

    persisted = {}

    def fake_persist(values, tree):
        persisted["values"] = values
        persisted["tree"] = tree
        return {"written": list(values.keys()), "env_cmds": []}

    monkeypatch.setattr(server.smokes, "smoke", smoke_must_not_be_called)
    monkeypatch.setattr(server.keys, "persist", fake_persist)

    c = TestClient(server.app)
    r = c.post("/api/keys/test", json={
        "integration": "google",
        "values": {"GOOGLE_OAUTH_CLIENT_ID": "id", "GOOGLE_OAUTH_CLIENT_SECRET": "secret"},
        "tree": str(tmp_path),
        "persist_only": True,
    })
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert "saved" in body["message"].lower()
    assert set(body["written"]) == {"GOOGLE_OAUTH_CLIENT_ID", "GOOGLE_OAUTH_CLIENT_SECRET"}
    assert persisted["values"] == {"GOOGLE_OAUTH_CLIENT_ID": "id", "GOOGLE_OAUTH_CLIENT_SECRET": "secret"}
    assert persisted["tree"] == Path(str(tmp_path))


def test_api_keys_test_persist_only_persist_failure_returns_ok_false(tmp_path, monkeypatch):
    from studio import server

    def smoke_must_not_be_called(integration, values):
        raise AssertionError("smoke() must not run for persist_only")

    def failing_persist(values, tree):
        raise ValueError("value for 'X' contains a newline")

    monkeypatch.setattr(server.smokes, "smoke", smoke_must_not_be_called)
    monkeypatch.setattr(server.keys, "persist", failing_persist)

    c = TestClient(server.app)
    r = c.post("/api/keys/test", json={
        "integration": "google",
        "values": {"GOOGLE_OAUTH_CLIENT_ID": "id\nbad"},
        "tree": str(tmp_path),
        "persist_only": True,
    })
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is False
    assert "couldn't save" in body["message"]


def test_api_keys_test_smoke_pass_persist_raises_returns_ok_true_with_warning(tmp_path, monkeypatch):
    from studio import server

    def fake_smoke(integration, values):
        return {"ok": True, "message": "connected ✓"}

    def failing_persist(values, tree):
        raise OSError("disk full")

    monkeypatch.setattr(server.smokes, "smoke", fake_smoke)
    monkeypatch.setattr(server.keys, "persist", failing_persist)

    c = TestClient(server.app)
    r = c.post("/api/keys/test", json={
        "integration": "linear",
        "values": {"LINEAR_API_KEY": "lin_x"},
        "tree": str(tmp_path),
    })
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert "couldn't save keys locally" in body["message"]
    assert "disk full" in body["message"]
    assert body["written"] == []
