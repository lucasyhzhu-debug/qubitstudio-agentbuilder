from studio.studio_extractor import extract_studio

IDS = {"crm", "briefing", "scheduling", "tasks", "intake", "drain"}

def _block(inner):
    return f"Some prose.\n```studio\n{inner}\n```\nMore prose."

def test_extracts_valid_block():
    out = extract_studio(_block('{"picks": ["crm", "briefing"], "name": "my-cos", "ready": false}'), IDS)
    assert out == {"picks": ["crm", "briefing"], "name": "my-cos", "ready": False,
                   "ask": None, "chapter": None}

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


# --- chapter field (dossier spec §3.1/§3.2) ---

def test_valid_chapter_extracted():
    out = extract_studio(_block(
        '{"picks": ["tasks"], "chapter": {"title": "Taming the inbox", "phase": "skills"}}'), IDS)
    assert out["chapter"] == {"title": "Taming the inbox", "phase": "skills", "blocks": []}

def test_chapter_absent_is_none():
    assert extract_studio(_block('{"picks": []}'), IDS)["chapter"] is None

def test_chapter_malformed_none_picks_and_ask_survive():
    # the standing tolerant rule: a broken chapter must never kill the picks/ask sync
    out = extract_studio(_block(
        '{"picks": ["crm"], "ask": {"title": "t", "options": [{"label": "x"}, {"label": "y"}]},'
        ' "chapter": "skills"}'), IDS)
    assert out["chapter"] is None and out["picks"] == ["crm"] and out["ask"] is not None

def test_chapter_unknown_phase_treated_absent():
    out = extract_studio(_block(
        '{"picks": [], "chapter": {"title": "t", "phase": "epilogue"}}'), IDS)
    assert out["chapter"] is None

def test_chapter_title_over_80_dropped():
    out = extract_studio(_block(
        '{"picks": [], "chapter": {"title": "' + "x" * 81 + '", "phase": "skills"}}'), IDS)
    assert out["chapter"] is None

def test_chapter_blocks_valid_vocabulary():
    out = extract_studio(_block(
        '{"picks": ["tasks"], "chapter": {"title": "Connect Linear", "phase": "connect",'
        ' "blocks": ['
        '{"type": "step", "n": 1, "text": "Open linear.app"},'
        '{"type": "key-field", "integration": "linear", "label": "Paste your key"},'
        '{"type": "checklist", "items": ["Key created", "Smoke green"]},'
        '{"type": "note", "text": "Keys stay local"},'
        '{"type": "skill-card", "id": "tasks"}]}}'), IDS)
    types = [b["type"] for b in out["chapter"]["blocks"]]
    assert types == ["step", "key-field", "checklist", "note", "skill-card"]
    assert out["chapter"]["blocks"][0] == {"type": "step", "n": 1, "text": "Open linear.app"}
    assert out["chapter"]["blocks"][1]["integration"] == "linear"

def test_chapter_unknown_block_type_skipped_rest_render():
    out = extract_studio(_block(
        '{"picks": [], "chapter": {"title": "t", "phase": "connect", "blocks": ['
        '{"type": "hologram", "text": "x"}, {"type": "note", "text": "kept"}]}}'), IDS)
    assert [b["type"] for b in out["chapter"]["blocks"]] == ["note"]

def test_chapter_malformed_blocks_empty_title_lands():
    out = extract_studio(_block(
        '{"picks": [], "chapter": {"title": "t", "phase": "build", "blocks": "steps"}}'), IDS)
    assert out["chapter"] == {"title": "t", "phase": "build", "blocks": []}

def test_step_without_text_skipped():
    out = extract_studio(_block(
        '{"picks": [], "chapter": {"title": "t", "phase": "build", "blocks": ['
        '{"type": "step", "n": 1}, {"type": "step", "n": 2, "text": "real"}]}}'), IDS)
    assert [b["text"] for b in out["chapter"]["blocks"]] == ["real"]

def test_key_field_unknown_integration_skipped():
    out = extract_studio(_block(
        '{"picks": [], "chapter": {"title": "t", "phase": "connect", "blocks": ['
        '{"type": "key-field", "integration": "fax-machine"},'
        '{"type": "key-field", "integration": "linear"}]}}'), IDS)
    assert [b["integration"] for b in out["chapter"]["blocks"]] == ["linear"]

def test_skill_card_unknown_id_skipped():
    out = extract_studio(_block(
        '{"picks": [], "chapter": {"title": "t", "phase": "build", "blocks": ['
        '{"type": "skill-card", "id": "hallucinated"}]}}'), IDS)
    assert out["chapter"]["blocks"] == []
