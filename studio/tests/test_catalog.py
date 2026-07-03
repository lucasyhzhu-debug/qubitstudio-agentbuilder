import json
from pathlib import Path

CAT = json.loads(Path("studio/catalog.json").read_text(encoding="utf-8"))


def test_every_shelf_item_has_needs_skills():
    for it in CAT["shelf"]["items"]:
        assert "needs_skills" in it, f"{it['id']} missing needs_skills"
        assert isinstance(it["needs_skills"], list)


def test_drain_routes_to_expected_skills():
    drain = next(i for i in CAT["shelf"]["items"] if i["id"] == "drain")
    assert set(drain["needs_skills"]) >= {"intake", "tasks", "crm", "scheduling"}


def test_daily_interest_brief_is_keyless_free_tier():
    it = next(i for i in CAT["shelf"]["items"] if i["id"] == "daily-interest-brief")
    assert it["requires"] == []
    assert it["needs_skills"] == []
    assert it["cost"]["tier"] == "free"
