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


def test_vault_path_backslashes_normalized_to_forward_slashes(tmp_path):
    # Finding #12: templates authored on Windows carried `{{VAULT_PATH}}\people\`-style tokens;
    # after substitution the backslashes survived, so live skills pointed at dead paths on macOS.
    tree = tmp_path / "plug"; tree.mkdir()
    (tree / "sample.md").write_text(
        "CRM lives at `{{VAULT_PATH}}\\people\\` and voice at "
        "`{{VAULT_PATH}}\\meta\\chief-of-staff\\personality.md`.", encoding="utf-8")
    composer.delucas(tree, "Sam Rivera", tmp_path / "sam-vault")
    out = (tree / "sample.md").read_text(encoding="utf-8")
    vault_fwd = str(tmp_path / "sam-vault").replace("\\", "/")
    assert f"{vault_fwd}/people/" in out
    assert f"{vault_fwd}/meta/chief-of-staff/personality.md" in out
    assert "\\people\\" not in out and "\\meta\\" not in out


def test_substrate_has_no_backslash_vault_tokens():
    # Regression guard: the substrate itself must stay forward-slash (cross-platform contract).
    import re
    bad = []
    for f in composer._COS.rglob("*"):
        if f.is_file() and f.suffix.lower() in composer._TEXT_EXT:
            for m in re.finditer(r"\{\{VAULT_PATH\}\}[^\s`'\"()\[\]]*", f.read_text(encoding="utf-8", errors="ignore")):
                if "\\" in m.group(0):
                    bad.append(f"{f}: {m.group(0)}")
    assert not bad, "backslash vault tokens reintroduced:\n" + "\n".join(bad)
