from pathlib import Path
from studio.system_prompt import build_system_prompt

def test_includes_quiz_and_schema():
    p = build_system_prompt()
    assert "Q0" in p                       # the quiz is present
    assert "architecture spec" in p.lower()  # the schema is present

def test_includes_studio_contract():
    p = build_system_prompt()
    assert "```spec" in p                   # emit-the-block instruction
    assert "runtime" in p                   # the extension schema
    assert "superpowers" in p.lower()       # the ignore-skill-injection override

def test_excludes_generation_pipeline():
    p = build_system_prompt()
    # M2-M4 machinery must NOT leak into a pure-chat prompt
    assert "render_setup" not in p
    assert "package_plugin" not in p
    assert "plugin-generator" not in p

def test_writes_file(tmp_path: Path):
    from studio.system_prompt import write_system_prompt
    out = write_system_prompt(tmp_path / "sp.md")
    assert out.exists() and out.read_text(encoding="utf-8").strip() != ""

def test_slicer_kept_q0_dropped_render_setup():
    """Extra: proves the slicer actually cut both files — Q0 present, render_setup absent.
    Both source files contain render_setup; if either is included un-sliced the test fails.
    """
    p = build_system_prompt()
    assert "Q0" in p              # quiz content survived the Q10-section excision
    assert "render_setup" not in p  # sliced out of both architecture-spec.md (§11) and quiz-bank.md (Q10 section)
