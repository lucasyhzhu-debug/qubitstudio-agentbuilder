from pathlib import Path
from studio import composer

def test_copy_includes_substrate_and_only_picked_skill_bodies(tmp_path):
    tree = tmp_path / "plug"
    composer.copy_plugin(tree, ["crm"])
    # shared substrate always present
    assert (tree / "agents/context-gatherer.md").exists()
    assert (tree / "references/google-auth.md").exists()
    # picked skill's SKILL.md present, with its references beside it
    assert (tree / "skills/crm/SKILL.md").exists()
    assert (tree / "skills/crm/references/crm-page-format.md").exists()
    # a NON-picked skill's references are still shipped (inert, hard-dep safe) — but under
    # references/skills/, NOT skills/: a skills/ folder without SKILL.md reads as a malformed
    # skill to the plugin loader ("1 error during load", finding #7).
    assert not (tree / "skills/drain").exists()
    assert (tree / "references/skills/drain/linear-api.md").exists()


def test_every_dir_under_skills_is_a_wellformed_skill(tmp_path):
    # loader guard: nothing under skills/ may lack a SKILL.md
    tree = tmp_path / "plug"
    composer.copy_plugin(tree, ["crm", "briefing"])
    for d in (tree / "skills").iterdir():
        assert (d / "SKILL.md").exists(), f"malformed skill dir shipped: {d.name}"


def test_copy_writes_identity_claude_md(tmp_path):
    # finding #8: the promised "raw-skills agent home" CLAUDE.md was never written, so composed
    # agents shipped with no identity and the participant's voice never applied.
    tree = tmp_path / "plug"
    composer.copy_plugin(tree, ["crm", "briefing"])
    identity = (tree / "CLAUDE.md").read_text(encoding="utf-8")
    assert "{{OWNER_NAME}}" in identity          # placeholders left for delucas to fill
    assert "## Voice" in identity                # the block the tweaker's voice pass rewrites
    assert "- `crm`" in identity and "- `briefing`" in identity
    assert "- `drain`" not in identity           # only picked skills are listed
