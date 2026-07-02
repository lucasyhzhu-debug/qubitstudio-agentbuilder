from pathlib import Path
import pytest
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

def test_catalog_ids_default_none_and_studio_none(tmp_path):
    s = _sess(tmp_path)
    assert s.catalog_ids is None and s.studio is None

def test_extract_pass_architect_mode_skips_studio(tmp_path):
    # catalog_ids None -> studio extraction never runs, even on a studio-looking text
    s = _sess(tmp_path)
    s._extract('```studio\n{"picks": ["crm"]}\n```')
    assert s.studio is None

def test_extract_pass_workshop_mode_sets_studio(tmp_path):
    sp_path = tmp_path / "sp.md"; sp_path.write_text("p", encoding="utf-8")
    from studio.chat_session import ChatSession
    s = ChatSession(session_id="11111111-1111-1111-1111-111111111111",
                    system_prompt_path=sp_path, catalog_ids={"crm", "tasks"})
    s._extract('hi\n```studio\n{"picks": ["crm"], "name": "my-cos", "ready": false}\n```')
    assert s.studio == {"picks": ["crm"], "name": "my-cos", "ready": False,
                         "ask": None, "chapter": None}

def test_extract_pass_keeps_prior_studio_on_garbage(tmp_path):
    sp_path = tmp_path / "sp.md"; sp_path.write_text("p", encoding="utf-8")
    from studio.chat_session import ChatSession
    s = ChatSession(session_id="11111111-1111-1111-1111-111111111111",
                    system_prompt_path=sp_path, catalog_ids={"crm"})
    s._extract('```studio\n{"picks": ["crm"]}\n```')
    s._extract('no block this turn')
    assert s.studio == {"picks": ["crm"], "name": None, "ready": False,
                         "ask": None, "chapter": None}

@pytest.mark.asyncio
async def test_concurrent_sends_serialize(tmp_path, monkeypatch):
    # Two overlapping send() calls must not run two `claude -p --resume` subprocesses
    # at once (onboarding-cards spec §5.4.8): spawn/finish pairs must not interleave.
    import asyncio as aio
    order = []

    class _FakeProc:
        returncode = 0
        stderr = None
        def __init__(self):
            self.stdout = self
        def __aiter__(self):
            return self
        async def __anext__(self):
            raise StopAsyncIteration
        async def wait(self):
            return 0

    async def fake_exec(*argv, **kw):
        order.append("spawn")
        await aio.sleep(0.05)      # long enough for the other task to try to enter
        order.append("live")
        return _FakeProc()

    monkeypatch.setattr(aio, "create_subprocess_exec", fake_exec)
    s = _sess(tmp_path)

    async def drain(msg):
        async for _ in s.send(msg):
            pass

    await aio.gather(drain("a"), drain("b"))
    assert order == ["spawn", "live", "spawn", "live"]   # serialized, not interleaved
