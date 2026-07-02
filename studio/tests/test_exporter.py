from studio.exporter import parse_marker

def test_parse_stage_marker():
    assert parse_marker("[[studio:stage:generate:running]]") == {
        "type": "stage", "name": "generate", "status": "running"}

def test_parse_component_marker():
    assert parse_marker("noise [[studio:component:skill:standup:ok]] trailing") == {
        "type": "component", "key": "skill:standup", "status": "ok"}

def test_parse_non_marker_returns_none():
    assert parse_marker("just a log line") is None
    assert parse_marker("[[studio:stage:bogus:weird]]") is None

def test_parse_unknown_stage_with_valid_status_returns_none():
    # valid status enum but a stage name outside _STAGES — exercises the set filter,
    # not just the status regex (which `bogus:weird` above already fails on).
    assert parse_marker("[[studio:stage:bogus:ok]]") is None

# ---------------------------------------------------------------------------
# Task 2: Exporter build orchestration tests
# ---------------------------------------------------------------------------
import asyncio
from pathlib import Path
from studio.exporter import Exporter, force_client_ready

def test_force_client_ready_overrides_personal():
    spec = {"plugin": {"name": "demo", "deliverable_grade": "personal"}, "components": []}
    out = force_client_ready(spec)
    assert out["plugin"]["deliverable_grade"] == "client-ready"
    # original not mutated (defensive copy)
    assert spec["plugin"]["deliverable_grade"] == "personal"

def test_build_argv_is_tools_enabled_and_repo_cwd(tmp_path):
    ex = Exporter(claude_bin="claude", repo_root=tmp_path)
    argv = ex.build_argv(tmp_path / "spec.json", tmp_path / "ws", tmp_path / "dist")
    assert "--output-format" in argv and "stream-json" in argv
    # NOT tool-less: the empty --allowed-tools "" form from chat must be absent
    joined = " ".join(argv)
    assert "Task" in joined and "Write" in joined  # generation needs tools

def test_build_argv_run_evals_toggles_eval_scripts(tmp_path):
    ex = Exporter(claude_bin="claude", repo_root=tmp_path)
    with_evals = " ".join(ex.build_argv(tmp_path/"s.json", tmp_path/"ws", tmp_path/"d", run_evals=True))
    no_evals = " ".join(ex.build_argv(tmp_path/"s.json", tmp_path/"ws", tmp_path/"d", run_evals=False))
    assert "run the M3 eval stage" in with_evals and "run_eval_win" in with_evals
    assert "SKIP the M3 eval stage" in no_evals and "run the M3 eval stage" not in no_evals
    # packaging always happens regardless of the eval toggle
    assert "package_plugin" in with_evals and "package_plugin" in no_evals

# The project runs pytest-asyncio in AUTO mode (studio/tests/pytest.ini: asyncio_mode = auto),
# so async tests are plain `async def` — no event-loop juggling (matches test_smoke_integration.py).
async def _aiter(lines):
    for l in lines:
        yield l

def _astream(*texts):
    """Build fake stream-json lines whose assistant text carries the given marker strings."""
    import json as _j
    return [_j.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": t + "\n"}]}})
            for t in texts] + [_j.dumps({"type": "result"})]

async def test_build_emits_stages_from_marker_stream(monkeypatch, tmp_path):
    ex = Exporter(claude_bin="claude", repo_root=tmp_path)
    fake = _astream("[[studio:stage:generate:running]]",
                    "[[studio:component:skill:standup:ok]]",
                    "[[studio:stage:package:ok]]")
    monkeypatch.setattr(ex, "_spawn_lines", lambda *a, **k: _aiter(fake))
    monkeypatch.setattr(ex, "_locate_plugin", lambda *a, **k: tmp_path / "dist" / "demo.plugin")
    events = [e async for e in ex.build({"plugin": {"name": "demo"}, "components": []})]
    kinds = [(e.get("type"), e.get("name") or e.get("key")) for e in events]
    assert ("stage", "generate") in kinds
    assert ("component", "skill:standup") in kinds
    assert events[-1]["type"] == "done" and events[-1]["grade"] == "verified"

async def test_build_without_evals_grades_validated(monkeypatch, tmp_path):
    ex = Exporter(claude_bin="claude", repo_root=tmp_path)
    fake = _astream("[[studio:stage:package:ok]]")
    monkeypatch.setattr(ex, "_spawn_lines", lambda *a, **k: _aiter(fake))
    monkeypatch.setattr(ex, "_locate_plugin", lambda *a, **k: tmp_path / "dist" / "demo.plugin")
    events = [e async for e in ex.build({"plugin": {"name": "demo"}, "components": []}, run_evals=False)]
    assert events[-1]["type"] == "done" and events[-1]["grade"] == "validated"

async def test_build_fail_marker_yields_error_and_handoff(monkeypatch, tmp_path):
    import studio.exporter as mod; mod._DIST = tmp_path / "dist"
    ex = Exporter(claude_bin="claude", repo_root=tmp_path)
    fake = _astream("[[studio:stage:validate:fail]]")
    monkeypatch.setattr(ex, "_spawn_lines", lambda *a, **k: _aiter(fake))
    events = [e async for e in ex.build({"plugin": {"name": "demo"}, "components": []})]
    err = events[-1]
    assert err["type"] == "error" and err["stage"] == "validate" and "handoff" in err

async def test_build_no_plugin_located_yields_error(monkeypatch, tmp_path):
    import studio.exporter as mod; mod._DIST = tmp_path / "dist"
    ex = Exporter(claude_bin="claude", repo_root=tmp_path)
    fake = _astream("[[studio:stage:package:ok]]")
    monkeypatch.setattr(ex, "_spawn_lines", lambda *a, **k: _aiter(fake))
    monkeypatch.setattr(ex, "_locate_plugin", lambda *a, **k: None)
    events = [e async for e in ex.build({"plugin": {"name": "demo"}, "components": []})]
    assert events[-1]["type"] == "error" and events[-1]["stage"] == "package"

# ---------------------------------------------------------------------------
# Task 8b: Export prompt mentions runtime materialization
# ---------------------------------------------------------------------------
def test_export_prompt_mentions_runtime(tmp_path):
    ex = Exporter(claude_bin="claude", repo_root=tmp_path)
    argv = ex.build_argv(tmp_path / "s.json", tmp_path / "ws", tmp_path / "dist")
    assert "runtime" in " ".join(argv)

# ---------------------------------------------------------------------------
# Task 3: Option-C handoff writer
# ---------------------------------------------------------------------------
def test_handoff_writes_spec_and_generate_md(tmp_path):
    ex = Exporter(claude_bin="claude", repo_root=tmp_path)
    import studio.exporter as mod
    monkey_dist = tmp_path / "dist"; mod._DIST = monkey_dist
    spec = {"plugin": {"name": "demo", "deliverable_grade": "client-ready"}, "components": []}
    out = ex._handoff(spec, tmp_path / "ws")
    spec_file = Path(out["spec_path"]); gen_file = Path(out["generate_md"])
    assert spec_file.exists() and gen_file.exists()
    assert "client-ready" in spec_file.read_text(encoding="utf-8")
    assert "/agent-architect" in gen_file.read_text(encoding="utf-8")
