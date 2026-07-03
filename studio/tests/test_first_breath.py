# studio/tests/test_first_breath.py
import asyncio
import pytest
from pathlib import Path

from studio.first_breath import build_first_breath_argv, build_greeting_prompt, first_breath

_CAT = {"shelf": {"items": [
    {"id": "tasks", "name": "Task list"}, {"id": "crm", "name": "CRM"}]}}


def test_argv_loads_the_homes_claude_md():
    argv = build_first_breath_argv("claude", "hello", Path("empty-mcp.json"))
    # the §6.4 flag set: the agent home's OWN CLAUDE.md must load —
    # no prompt-replacement flags, tool-less, MCP fenced to an empty config
    assert "--system-prompt-file" not in argv
    assert "--exclude-dynamic-system-prompt-sections" not in argv
    i = argv.index("--allowed-tools")
    assert argv[i + 1] == ""
    assert "--strict-mcp-config" in argv
    j = argv.index("--mcp-config")
    assert argv[j + 1].endswith("empty-mcp.json")
    assert argv[:2] == ["claude", "-p"]
    assert "--output-format" in argv and "stream-json" in argv


def test_greeting_prompt_constrained_to_composed_reality():
    p = build_greeting_prompt("Ada", ["tasks"], ["linear"], _CAT)
    assert "Ada" in p                       # greets the participant by name
    assert "Task list" in p                 # references actual picks
    assert "linear" in p                    # hands into the connect chapters
    assert "promise nothing" in p.lower()   # no unbuilt claims (no scheduling until r1-A)
    assert "do not ask questions" in p.lower()


def test_greeting_prompt_no_integrations_case():
    p = build_greeting_prompt("Ada", ["crm"], [], _CAT)
    assert "none" in p.lower()


class _Proc:
    returncode = 0
    stderr = None
    def __init__(self, lines, stall=0.0):
        self._lines = list(lines)
        self._stall = stall
        self.stdout = self
    async def readline(self):
        if self._stall:
            await asyncio.sleep(self._stall)
        return self._lines.pop(0) if self._lines else b""
    async def wait(self):
        return 0
    def kill(self):
        pass


def _lines():
    import json
    return [
        (json.dumps({"type": "assistant", "message": {"content": [
            {"type": "text", "text": "Morning, Ada. I'm atlas."}]}}) + "\n").encode(),
        (json.dumps({"type": "result"}) + "\n").encode(),
    ]


async def test_stream_yields_tokens_then_done(tmp_path, monkeypatch):
    async def fake_exec(*argv, **kw):
        assert kw.get("cwd") == str(tmp_path)     # cwd IS the agent home
        return _Proc(_lines())
    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)
    monkeypatch.setattr("studio.first_breath.resolve_claude", lambda: "claude")
    evs = [e async for e in first_breath(tmp_path, "greet")]
    assert any(e["type"] == "token" and "atlas" in e["text"] for e in evs)
    assert evs[-1]["type"] == "done"


async def test_budget_exceeded_yields_error_never_hangs(tmp_path, monkeypatch):
    async def fake_exec(*argv, **kw):
        return _Proc(_lines(), stall=60)
    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)
    monkeypatch.setattr("studio.first_breath.resolve_claude", lambda: "claude")
    evs = [e async for e in first_breath(tmp_path, "greet", budget=0.05)]
    assert evs[-1]["type"] == "error" and "budget" in evs[-1]["message"]
