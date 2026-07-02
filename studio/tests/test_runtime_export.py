from pathlib import Path
from studio.runtime_export import materialize_runtime

def test_storage_creates_dirs_and_readme(tmp_path):
    paths = materialize_runtime({"storage": [{"what": "deliverables", "where": "outputs", "kind": "filesystem"}]}, tmp_path)
    assert (tmp_path / "outputs").is_dir()
    assert (tmp_path / "README.md").exists()
    assert any("outputs" in p for p in paths)

def test_memory_and_routines_append_readme(tmp_path):
    materialize_runtime({
        "memory": [{"fact_type": "project", "note": "tracks engagements"}],
        "routines": [{"name": "digest", "schedule": "0 9 * * 1", "does": "weekly summary"}],
    }, tmp_path)
    txt = (tmp_path / "README.md").read_text(encoding="utf-8")
    assert "Memory" in txt and "Scheduling" in txt and "/schedule" in txt

def test_empty_runtime_is_noop(tmp_path):
    assert materialize_runtime({}, tmp_path) == []
    assert not (tmp_path / "README.md").exists()

def test_prepends_to_existing_readme(tmp_path):
    (tmp_path / "README.md").write_text("# My Plugin\n\nExisting body.\n", encoding="utf-8")
    materialize_runtime({"memory": [{"fact_type": "project", "note": "tracks engagements"}]}, tmp_path)
    txt = (tmp_path / "README.md").read_text(encoding="utf-8")
    # the original content survives and leads; the new section follows it.
    assert txt.index("Existing body.") < txt.index("## Memory")

def test_storage_entry_without_where_renders_no_bullet(tmp_path):
    paths = materialize_runtime(
        {"storage": [{"what": "notes", "kind": "filesystem"}]}, tmp_path)  # no `where`
    # nothing to materialize: no dir, no README, no `None` bullet.
    assert paths == []
    assert not (tmp_path / "README.md").exists()
