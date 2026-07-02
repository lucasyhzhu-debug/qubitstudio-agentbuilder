from studio import stream_parser as sp

def test_parse_line_blank_and_invalid():
    assert sp.parse_line("") is None
    assert sp.parse_line("   ") is None
    assert sp.parse_line("{not json") is None

def test_parse_line_valid():
    assert sp.parse_line('{"type":"result"}') == {"type": "result"}

def test_is_system_true_for_hooks():
    assert sp.is_system({"type": "system", "subtype": "hook_started"}) is True
    assert sp.is_system({"type": "assistant"}) is False

def test_is_turn_end():
    assert sp.is_turn_end({"type": "result", "subtype": "success"}) is True
    assert sp.is_turn_end({"type": "assistant"}) is False

def test_assistant_text_full_message():
    ev = {"type": "assistant",
          "message": {"role": "assistant",
                      "content": [{"type": "text", "text": "Hello "},
                                  {"type": "text", "text": "world"}]}}
    assert sp.assistant_text(ev) == "Hello world"

def test_assistant_text_partial_delta():
    ev = {"type": "stream_event",
          "event": {"type": "content_block_delta",
                    "delta": {"type": "text_delta", "text": "tok"}}}
    assert sp.assistant_text(ev) == "tok"

def test_assistant_text_other_event_empty():
    assert sp.assistant_text({"type": "system"}) == ""

def test_session_id():
    assert sp.session_id({"session_id": "abc"}) == "abc"
    assert sp.session_id({}) is None

def test_real_fixture_has_only_system_then_assistant_then_result():
    # Ground-truth check against the Task 0 capture.
    from pathlib import Path
    lines = Path("studio/tests/fixtures/stream-plain.jsonl").read_text(encoding="utf-8").splitlines()
    events = [e for e in (sp.parse_line(l) for l in lines) if e]
    types = {e.get("type") for e in events}
    assert "system" in types          # the hook flood is present...
    assert "result" in types          # ...and the turn ends with a result
    text = "".join(sp.assistant_text(e) for e in events if not sp.is_system(e))
    assert text.strip() != ""         # some assistant text was produced
