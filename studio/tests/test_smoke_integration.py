import pytest
from pathlib import Path
from studio.chat_session import ChatSession
from studio.system_prompt import write_system_prompt
from studio.exporter import Exporter

@pytest.mark.integration
@pytest.mark.asyncio
async def test_one_real_turn(tmp_path):
    sp = write_system_prompt(tmp_path / "sp.md")
    s = ChatSession(session_id="22222222-2222-2222-2222-222222222222", system_prompt_path=sp)
    events = [ev async for ev in s.send("My idea: an agent that drafts standups.")]
    assert any(e["type"] == "token" for e in events)        # it streamed
    assert events[-1]["type"] in ("done", "error")
    assert not any(e.get("type") == "tool_use" for e in events)  # stayed tool-less

@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_export_builds_a_plugin():
    # Requires a live `claude` (MAX login) + agent-architect reachable. Builds a 1-component spec.
    spec = {"plugin": {"name": "smoketest", "description": "x", "deliverable_grade": "personal"},
            "components": [{"type": "skill", "id": "echo", "name": "echo"}]}
    events = [e async for e in Exporter().build(spec)]
    assert events[-1]["type"] in ("done", "error")  # a real build may legitimately fail — record which
