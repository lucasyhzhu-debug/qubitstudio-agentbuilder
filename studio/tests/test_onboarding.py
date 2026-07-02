import base64
import json
import pytest
from pathlib import Path

from studio import onboarding as ob


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    monkeypatch.setattr(ob, "STATE_PATH", tmp_path / "cache" / "onboarding.json")
    monkeypatch.setattr(ob, "STAGING", tmp_path / "cache" / "onboarding-inbox")
    monkeypatch.setattr(ob, "_REPO", tmp_path / "repo")
    (tmp_path / "repo").mkdir()
    yield


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def test_state_roundtrip_and_empty_default():
    assert ob.load_state() == {}
    ob.save_state({"name": "Ada"})
    assert ob.load_state()["name"] == "Ada"
    assert ob.completed() is False


def test_set_name_validates():
    assert ob.set_name("  Ada  ")["name"] == "Ada"
    with pytest.raises(ValueError):
        ob.set_name("")
    with pytest.raises(ValueError):
        ob.set_name("x" * 61)


def test_stage_file_sanitizes_and_writes():
    ob.stage_file("../../evil.md", _b64(b"hello"))
    assert (ob.STAGING / "evil.md").read_bytes() == b"hello"   # basename only


def test_stage_file_caps():
    with pytest.raises(ValueError):
        ob.stage_file("big.bin", _b64(b"x" * (ob.MAX_FILE_BYTES + 1)))
    ob.save_state({"materials": {"copied": [f"f{i}" for i in range(ob.MAX_FILES)], "folders": []}})
    with pytest.raises(ValueError):
        ob.stage_file("one-too-many.md", _b64(b"x"))


def test_register_folder_must_exist(tmp_path):
    d = tmp_path / "essays"; d.mkdir()
    out = ob.register_folder(str(d))
    # Compare Paths, not substrings — resolve() may fold drive-letter case on Windows.
    assert Path(out["materials"]["folders"][0]) == d.resolve()
    with pytest.raises(ValueError):
        ob.register_folder(str(tmp_path / "nope"))


def test_second_brain_created_staged_moved(tmp_path):
    ob.set_name("Ada")
    ob.stage_file("cv.md", _b64(b"# cv"))
    sb = tmp_path / "second-brain"
    state = ob.set_second_brain(str(sb))
    assert Path(state["second_brain"]) == sb
    assert (sb / "inbox" / "onboarding" / "cv.md").read_bytes() == b"# cv"
    assert "cv.md" in (sb / "materials.md").read_text(encoding="utf-8")


def test_second_brain_rejects_repo_interior():
    with pytest.raises(ValueError):
        ob.set_second_brain(str(ob._REPO / "dist" / "sb"))


def test_materials_sources_staging_and_folders(tmp_path):
    d = tmp_path / "notes"; d.mkdir()
    ob.register_folder(str(d))
    ob.stage_file("cv.md", _b64(b"x"))
    src = ob.materials_sources()
    assert ob.STAGING in src and d in src


def test_materials_sources_folders_only_creates_staging(tmp_path):
    d = tmp_path / "notes"; d.mkdir()
    ob.register_folder(str(d))
    src = ob.materials_sources()          # staging empty -> not a source, but must exist
    assert ob.STAGING.exists() and ob.STAGING not in src and d in src


def test_write_profile_real_and_stub(tmp_path):
    ob.set_name("Ada")
    ob.set_second_brain(str(tmp_path / "sb"))
    p = ob.write_profile("# Ada\n\nBuilt engines.")
    assert "engines" in p.read_text(encoding="utf-8")
    assert ob.completed() is True
    p2 = ob.write_profile(None)           # stub fallback (distiller failed)
    text = p2.read_text(encoding="utf-8")
    assert "Ada" in text and "not yet distilled" in text


def test_write_profile_requires_second_brain():
    with pytest.raises(ValueError):
        ob.write_profile("text")
