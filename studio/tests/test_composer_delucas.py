# studio/tests/test_composer_delucas.py
from pathlib import Path
from studio import composer

def _tree_text(tree):
    return "\n".join(p.read_text(encoding="utf-8", errors="ignore")
                     for p in Path(tree).rglob("*") if p.is_file())

def test_delucas_leaves_zero_owner_literals(tmp_path):
    tree = tmp_path / "plug"
    composer.copy_home(tree, ["crm", "drain"])          # drain drags in the Lucas-heavy refs
    composer.delucas(tree, "Sam Rivera", tmp_path / "sam-vault")
    blob = _tree_text(tree)
    assert "Lucas" not in blob
    assert "LUCAS_USER_ID" not in blob
    assert "d885fd34-71e6-4e8b-8fc6-da4f6bbf1875" not in blob
    assert "504fb62b-28ba-4140-9031-1f03e189c70c" not in blob
    assert "Documents/wiki-brain" not in blob and r"Documents\wiki-brain" not in blob
    assert "lucas@ikigaiventures.ai" not in blob
    assert "wiki-brain/people/" not in blob
    assert "lucasknowledgebot" not in blob
    # participant's vault path is now present
    assert "sam-vault" in blob
    # deliberately survive de-Lucas'ing: workshop repo URL + a functional label, not owner PII
    assert "lucasyhzhu-debug" in blob
    assert "needs-lucas" in blob
