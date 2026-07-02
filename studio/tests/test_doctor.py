import studio.__main__ as m

def test_check_claude_missing(monkeypatch):
    monkeypatch.setattr(m.shutil, "which", lambda _: None)
    name, ok, fix = m.check_claude()
    assert name == "claude on PATH" and ok is False and "claude auth login" in fix

def test_check_port_free_picks_next(monkeypatch):
    # 8765 taken → returns the next free port and reports it
    taken = {8765}
    monkeypatch.setattr(m, "_port_open", lambda p: p in taken)
    port, msg = m.pick_port(8765)
    assert port == 8766 and "8766" in msg

def test_doctor_excludes_auth_smoke_by_default(monkeypatch):
    # normal launch must NOT pay the 25s auth call (P-I1)
    called = []
    monkeypatch.setattr(m, "check_python", lambda: ("Python >= 3.10", True, ""))
    monkeypatch.setattr(m, "check_claude", lambda: ("claude on PATH", True, ""))
    monkeypatch.setattr(m, "check_claude_auth", lambda: called.append(1) or ("claude authed", True, ""))
    monkeypatch.setattr(m, "check_deps", lambda: ("deps importable", True, ""))
    monkeypatch.setattr(m, "check_git", lambda: ("git on PATH", True, ""))
    rows = m.doctor()                      # default include_auth=False
    assert len(rows) == 4 and not called   # auth smoke skipped
    rows_full = m.doctor(include_auth=True)
    assert len(rows_full) == 5 and called  # --doctor runs it

def test_doctor_flag_ensures_venv_first(monkeypatch):
    # --doctor is pre-work: it must pre-install deps so re-running goes all-green (M6)
    called = []
    monkeypatch.setattr(m, "_ensure_venv", lambda: called.append(1))
    monkeypatch.setattr(m, "doctor", lambda include_auth=False, deps_ok=None: [("ok row", True, "")])
    monkeypatch.setattr(m, "_print_doctor", lambda rows: all(ok for _, ok, _ in rows))
    rc = m.main(["--doctor"])
    assert called and rc == 0
