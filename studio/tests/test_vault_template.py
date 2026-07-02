from pathlib import Path

VT = Path("studio/templates/vault")

def test_template_tree_present():
    assert (VT / "meta/chief-of-staff/personality.md").exists()
    assert (VT / "meta/memories.md").exists()
    assert (VT / "meta/chief-of-staff/lessons.md").exists()
    assert (VT / "people/.gitkeep").exists() and (VT / "meetings/.gitkeep").exists()

def test_identity_has_placeholders_and_no_lucas():
    p = (VT / "meta/chief-of-staff/personality.md").read_text(encoding="utf-8")
    assert "{{OWNER_NAME}}" in p
    assert "Lucas" not in p  # de-Lucas by construction
