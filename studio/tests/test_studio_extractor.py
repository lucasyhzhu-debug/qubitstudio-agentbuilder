from studio.studio_extractor import extract_studio

IDS = {"crm", "briefing", "scheduling", "tasks", "intake", "drain"}

def _block(inner):
    return f"Some prose.\n```studio\n{inner}\n```\nMore prose."

def test_extracts_valid_block():
    out = extract_studio(_block('{"picks": ["crm", "briefing"], "name": "my-cos", "ready": false}'), IDS)
    assert out == {"picks": ["crm", "briefing"], "name": "my-cos", "ready": False, "ask": None}

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


# --- ask channel (onboarding-cards spec §4.1) ---

def test_valid_ask_extracted():
    out = extract_studio(_block(
        '{"picks": [], "ask": {"id": "triage", "title": "How deep should triage go?",'
        ' "why": "sets drafting", "options": ['
        '{"id": "a", "label": "Summarize only", "why": "you act"},'
        '{"label": "Draft replies"}], "multi": false}}'), IDS)
    assert out["ask"]["title"] == "How deep should triage go?"
    assert out["ask"]["options"][0] == {"id": "a", "label": "Summarize only", "why": "you act"}
    assert out["ask"]["options"][1]["id"] == "b"          # positional default
    assert out["ask"]["allow_custom"] is True             # forced in v1
    assert out["ask"]["multi"] is False

def test_ask_absent_is_none():
    assert extract_studio(_block('{"picks": []}'), IDS)["ask"] is None

def test_ask_single_option_dropped_picks_kept():
    out = extract_studio(_block(
        '{"picks": ["crm"], "ask": {"title": "t", "options": [{"label": "only one"}]}}'), IDS)
    assert out["ask"] is None and out["picks"] == ["crm"]

def test_ask_missing_title_dropped():
    out = extract_studio(_block(
        '{"picks": [], "ask": {"options": [{"label": "x"}, {"label": "y"}]}}'), IDS)
    assert out["ask"] is None

def test_ask_non_dict_dropped():
    assert extract_studio(_block('{"picks": [], "ask": "what?"}'), IDS)["ask"] is None

def test_ask_multi_coerced():
    out = extract_studio(_block(
        '{"picks": [], "ask": {"title": "t", "multi": 1,'
        ' "options": [{"label": "x"}, {"label": "y"}]}}'), IDS)
    assert out["ask"]["multi"] is True
