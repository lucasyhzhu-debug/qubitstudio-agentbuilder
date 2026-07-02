from pathlib import Path
from studio.chat_session import ChatSession, dedup_text
from studio import stream_parser as sp


def _fold_fixture(name):
    """Replay a captured stream-json fixture through the dedup, returning the text a
    turn would stream to the browser."""
    lines = Path(f"studio/tests/fixtures/{name}").read_text(encoding="utf-8").splitlines()
    saw, out = False, []
    for line in lines:
        ev = sp.parse_line(line)
        if not ev or sp.is_system(ev):
            continue
        text, saw = dedup_text(ev, saw)
        if text:
            out.append(text)
    return "".join(out)


def test_dedup_drops_full_message_after_deltas():
    # --include-partial-messages emits deltas AND a final full assistant event with the
    # SAME text; the turn must stream it ONCE, not doubled.
    assert _fold_fixture("stream-partial.jsonl") == "Hello, ready to help!"


def test_dedup_keeps_full_message_when_no_deltas():
    # Plain stream (no partials): the full assistant event is the only text source, so it
    # must still be emitted.
    out = _fold_fixture("stream-plain.jsonl")
    assert out.strip() != ""


def _sess(tmp_path):
    sp = tmp_path / "sp.md"; sp.write_text("prompt", encoding="utf-8")
    return ChatSession(session_id="11111111-1111-1111-1111-111111111111", system_prompt_path=sp)

def test_first_turn_uses_session_id(tmp_path):
    s = _sess(tmp_path)
    argv = s.build_argv("hello")
    assert "--session-id" in argv
    assert s.session_id in argv
    assert "--resume" not in argv

def test_later_turn_uses_resume(tmp_path):
    s = _sess(tmp_path)
    s.started = True
    argv = s.build_argv("again")
    assert "--resume" in argv
    assert "--session-id" not in argv

def test_argv_is_toolless_and_replaces_prompt(tmp_path):
    s = _sess(tmp_path)
    argv = s.build_argv("hi")
    # tool-less via the brain.mjs-proven form: --allowed-tools "" (not enumerated --disallowed-tools)
    assert "--allowed-tools" in argv
    assert argv[argv.index("--allowed-tools") + 1] == ""
    assert "--disallowed-tools" not in argv
    assert "--system-prompt-file" in argv
    assert "--append-system-prompt" not in argv
    assert "--exclude-dynamic-system-prompt-sections" in argv
    assert "--output-format" in argv and "stream-json" in argv

def test_session_flag_not_swallowed_by_variadic(tmp_path):
    # --allowed-tools takes ONE value (""), so the session id can never be absorbed (CP3).
    s = _sess(tmp_path); s.started = True
    argv = s.build_argv("again")
    assert argv[argv.index("--resume") + 1] == s.session_id

def test_argv_never_uses_shell_metachars_inline(tmp_path):
    # message is passed as its own argv element, not interpolated
    s = _sess(tmp_path)
    argv = s.build_argv("hi; rm -rf /")
    assert "hi; rm -rf /" in argv
