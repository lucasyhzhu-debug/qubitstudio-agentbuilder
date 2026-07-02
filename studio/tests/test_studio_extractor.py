from studio.studio_extractor import extract_studio

IDS = {"crm", "briefing", "scheduling", "tasks", "intake", "drain"}

def _block(inner):
    return f"Some prose.\n```studio\n{inner}\n```\nMore prose."

def test_extracts_valid_block():
    out = extract_studio(_block('{"picks": ["crm", "briefing"], "name": "my-cos", "ready": false}'), IDS)
    assert out == {"picks": ["crm", "briefing"], "name": "my-cos", "ready": False}

def test_absent_block_returns_none():
    assert extract_studio("no fences here", IDS) is None

def test_malformed_json_returns_none():
    assert extract_studio(_block('{"picks": [oops'), IDS) is None

def test_missing_picks_returns_none():
    # picks-as-list is what structurally identifies a studio block
    assert extract_studio(_block('{"name": "x", "ready": true}'), IDS) is None

def test_unknown_ids_dropped_valid_kept():
    out = extract_studio(_block('{"picks": ["crm", "hallucinated", "tasks"]}'), IDS)
    assert out["picks"] == ["crm", "tasks"]

def test_last_block_wins():
    text = _block('{"picks": ["crm"]}') + "\n" + _block('{"picks": ["tasks"]}')
    assert extract_studio(text, IDS)["picks"] == ["tasks"]

def test_ready_and_name_coercion():
    out = extract_studio(_block('{"picks": [], "name": "", "ready": 1}'), IDS)
    assert out["name"] is None and out["ready"] is True

def test_spec_fence_not_matched():
    # a ```spec block must never parse as a studio block, and vice versa
    text = '```spec\n{"plugin": {"name": "x"}, "components": [], "picks": ["crm"]}\n```'
    assert extract_studio(text, IDS) is None

def test_json_fence_not_matched():
    # no ```json fallback — that fence belongs to the spec extractor
    text = '```json\n{"picks": ["crm"]}\n```'
    assert extract_studio(text, IDS) is None

def test_duplicate_picks_deduped():
    out = extract_studio(_block('{"picks": ["crm", "crm", "tasks"]}'), IDS)
    assert out["picks"] == ["crm", "tasks"]
