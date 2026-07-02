"""Drive one agent-architect chat as a sequence of `claude -p` subprocess turns.

Tool-less + replaced system prompt + session continuity. The user's global SessionStart hooks
still fire, but (a) with no Skill tool the chat can't act on them and (b) the parser drops their
`type:"system"` events. Streaming is async so a turn never blocks the web event loop.
"""
from __future__ import annotations
import asyncio
import shutil
import tempfile
from pathlib import Path
from typing import AsyncIterator

from studio import stream_parser as sp
from studio.spec_extractor import extract_spec


def resolve_claude() -> str | None:
    """Resolve the claude CLI to a real path (it's a .cmd/.ps1 shim on Windows; bare exec
    of 'claude' can fail — sandbox/brain.mjs:141). Use the form Task 0 verified."""
    return shutil.which("claude")


def dedup_text(event: dict, saw_delta: bool) -> tuple[str, bool]:
    """Decide what assistant text to emit for one stream event, de-duplicating the
    final full `type:"assistant"` aggregate against the partial deltas that already
    streamed the same text. `--include-partial-messages` emits BOTH a run of
    `stream_event` `content_block_delta` token deltas AND a final `assistant` event
    carrying the complete message — counting both doubles every turn. Once any delta
    has streamed, drop the full `assistant` text. When partials are absent (no deltas),
    the full `assistant` event is still emitted as the fallback. Returns
    (text_to_emit, updated_saw_delta)."""
    text = sp.assistant_text(event)
    is_delta = event.get("type") == "stream_event" and bool(text)
    if text and event.get("type") == "assistant" and saw_delta:
        text = ""
    return text, (saw_delta or is_delta)


class ChatSession:
    def __init__(self, session_id: str, system_prompt_path: Path, claude_bin: str | None = None):
        self.session_id = session_id
        self.system_prompt_path = str(system_prompt_path)
        # full resolved path to the shim (CP1); falls back to "claude" for non-Windows/tests.
        self.claude_bin = claude_bin or resolve_claude() or "claude"
        self.started = False
        self.spec: dict | None = None

    def build_argv(self, user_msg: str) -> list[str]:
        # Tool-less via --allowed-tools "" (single value — the brain.mjs:152 form), so the variadic
        # footgun is gone and the session id below can't be swallowed (CP3).
        argv = [self.claude_bin, "-p", user_msg,
                "--output-format", "stream-json", "--verbose",
                "--include-partial-messages",
                "--system-prompt-file", self.system_prompt_path,
                "--exclude-dynamic-system-prompt-sections",
                "--allowed-tools", ""]
        if self.started:
            argv += ["--resume", self.session_id]
        else:
            argv += ["--session-id", self.session_id]
        return argv

    async def send(self, user_msg: str) -> AsyncIterator[dict]:
        argv = self.build_argv(user_msg)
        try:
            # cwd = a neutral temp dir so the chat does NOT load THIS repo's CLAUDE.md / project
            # hooks (brain.mjs:23-25 does the same) — less derailment surface (IP1).
            proc = await asyncio.create_subprocess_exec(
                *argv, cwd=tempfile.gettempdir(),
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        except FileNotFoundError:
            yield {"type": "error", "message": "`claude` CLI not found on PATH."}
            return

        full_text: list[str] = []
        saw_delta = False
        assert proc.stdout is not None
        async for raw in proc.stdout:
            event = sp.parse_line(raw.decode("utf-8", "replace"))
            if not event or sp.is_system(event):
                continue
            text, saw_delta = dedup_text(event, saw_delta)
            if text:
                full_text.append(text)
                yield {"type": "token", "text": text}
            if sp.is_turn_end(event):
                break

        await proc.wait()
        if proc.returncode not in (0, None):
            err = (await proc.stderr.read()).decode("utf-8", "replace") if proc.stderr else ""
            yield {"type": "error", "message": f"claude exited {proc.returncode}: {err[:500]}"}
            return

        self.started = True
        new_spec = extract_spec("".join(full_text))
        if new_spec is not None:
            self.spec = new_spec
        yield {"type": "done", "spec": self.spec}
