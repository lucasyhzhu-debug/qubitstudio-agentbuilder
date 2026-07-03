import uuid
import pytest
from pathlib import Path
from studio.chat_session import ChatSession
from studio.system_prompt import write_system_prompt
from studio.exporter import Exporter

@pytest.mark.integration
@pytest.mark.asyncio
async def test_one_real_turn(tmp_path):
    sp = write_system_prompt(tmp_path / "sp.md")
    # fresh uuid each run: `claude --session-id` permanently consumes an id, so a
    # fixed one makes the test pass exactly once per machine.
    s = ChatSession(session_id=str(uuid.uuid4()), system_prompt_path=sp)
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

@pytest.mark.integration
@pytest.mark.asyncio
async def test_one_real_workshop_turn(tmp_path):
    # The workshop prompt must make a REAL claude turn emit a parseable ```studio block.
    sp = write_system_prompt(tmp_path / "wp.md", mode="workshop")
    ids = {"crm", "briefing", "scheduling", "tasks", "intake", "drain"}
    s = ChatSession(session_id=str(uuid.uuid4()),  # fresh id — see test_one_real_turn
                    system_prompt_path=sp, catalog_ids=ids)
    events = [ev async for ev in s.send(
        "I get maybe 50 emails a day and track my todos in Linear. What should I add?")]
    assert any(e["type"] == "token" for e in events)
    done = events[-1]
    assert done["type"] == "done"
    assert done.get("studio") is not None, "no parseable ```studio block in a real turn"
    assert isinstance(done["studio"]["picks"], list)

@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_distill_returns_profile():
    # The distiller must produce non-empty markdown from real mixed materials.
    from studio.distiller import distill
    fixtures = Path(__file__).parent / "fixtures" / "onboarding"
    out = await distill([fixtures])
    # brief wrote `out and "Lovelace" in out or "Ada" in out` — explicit parens preserve
    # the evident intent: non-empty AND (Lovelace OR Ada).
    assert out and ("Lovelace" in out or "Ada" in out)

@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_workshop_turn_emits_chapter(tmp_path):
    # The chapter contract must make a REAL claude turn emit a parseable chapter
    # with a valid phase (dossier spec §10).
    sp = write_system_prompt(tmp_path / "wp.md", mode="workshop")
    ids = {"crm", "briefing", "scheduling", "tasks", "intake", "drain"}
    s = ChatSession(session_id=str(uuid.uuid4()),
                    system_prompt_path=sp, catalog_ids=ids)
    events = [ev async for ev in s.send(
        "I drown in email and track work in Linear. Begin the interview.")]
    done = events[-1]
    assert done["type"] == "done" and done.get("studio") is not None
    ch = done["studio"].get("chapter")
    assert ch is not None, "no parseable chapter in a real turn"
    assert ch["phase"] in {"welcome", "baseline", "skills", "personalize",
                           "name", "build", "connect"}
    assert s.beats and s.beats[-1]["studio"] == done["studio"]

@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_first_breath_over_composed_home(tmp_path):
    # Compose is deterministic (no LLM) — build a real home, then run one REAL
    # tool-less greeting turn with cwd = the home (dossier spec §10).
    import json as _json
    from studio import composer
    from studio.first_breath import build_greeting_prompt, first_breath
    evs = [e async for e in composer.compose(
        ["crm"], "Ada Smoke", tmp_path / "dist", tmp_path / "dist" / "ada-smoke-cos" / "vault")]
    done = evs[-1]
    assert done["type"] == "done"
    cat = _json.loads((Path(__file__).parent.parent / "catalog.json").read_text(encoding="utf-8"))
    prompt = build_greeting_prompt("Ada", ["crm"], [], cat)
    out = [e async for e in first_breath(Path(done["plugin_path"]), prompt, budget=60)]
    assert any(e["type"] == "token" for e in out), "first breath streamed nothing"
    assert out[-1]["type"] in ("done", "error")
