import asyncio
import pytest
from pathlib import Path

from studio.distiller import build_distill_argv, distill


def test_argv_shape(tmp_path):
    a, b = tmp_path / "inbox", tmp_path / "notes"
    argv = build_distill_argv("claude", [a, b])
    assert argv[0] == "claude" and argv[1] == "-p"
    i = argv.index("--allowed-tools")
    assert argv[i + 1] == "Read"                      # Read only — no write surface
    assert argv.count("--add-dir") == 2
    assert str(a) in argv and str(b) in argv


def test_prompt_contents(tmp_path):
    argv = build_distill_argv("claude", [tmp_path / "inbox"])
    prompt = argv[2]
    assert str(tmp_path / "inbox") in prompt
    assert "sample" in prompt.lower()                 # large-folder sampling guidance (review I5)
    assert "profile" in prompt.lower()


@pytest.mark.asyncio
async def test_nonzero_exit_raises(tmp_path, monkeypatch):
    class _Proc:
        returncode = 3
        async def communicate(self):
            return b"", b"boom"
    async def fake_exec(*a, **k):
        return _Proc()
    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)
    monkeypatch.setattr("studio.distiller.resolve_claude", lambda: "claude")
    with pytest.raises(RuntimeError):
        await distill([tmp_path])


@pytest.mark.asyncio
async def test_missing_cli_raises(tmp_path, monkeypatch):
    monkeypatch.setattr("studio.distiller.resolve_claude", lambda: None)
    async def never_spawn(*a, **k):                   # must bail before any exec
        pytest.fail("create_subprocess_exec should not be reached when the CLI is missing")
    monkeypatch.setattr(asyncio, "create_subprocess_exec", never_spawn)
    with pytest.raises(RuntimeError):
        await distill([tmp_path])


@pytest.mark.asyncio
async def test_timeout_raises(tmp_path, monkeypatch):
    class _Proc:
        returncode = None
        async def communicate(self):
            await asyncio.sleep(60)
        def kill(self):
            pass
        async def wait(self):
            return 0
    async def fake_exec(*a, **k):
        return _Proc()
    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)
    monkeypatch.setattr("studio.distiller.resolve_claude", lambda: "claude")
    with pytest.raises(RuntimeError):
        await distill([tmp_path], timeout=0.05)
