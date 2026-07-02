from pathlib import Path
from studio import composer

def test_copy_includes_substrate_and_only_picked_skill_bodies(tmp_path):
    tree = tmp_path / "plug"
    composer.copy_plugin(tree, ["crm"])
    # shared substrate always present
    assert (tree / "agents/context-gatherer.md").exists()
    assert (tree / "references/google-auth.md").exists()
    # picked skill's SKILL.md present
    assert (tree / "skills/crm/SKILL.md").exists()
    # a NON-picked skill's SKILL.md absent, but its references dir is still copied (inert, hard-dep safe)
    assert not (tree / "skills/drain/SKILL.md").exists()
    assert (tree / "skills/drain/references/linear-api.md").exists()
