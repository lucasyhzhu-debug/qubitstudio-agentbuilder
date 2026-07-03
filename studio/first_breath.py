# studio/first_breath.py
"""One REAL greeting turn from the freshly composed agent (dossier spec §6 beat 4).

Reuse seam (§6.4): stream_parser.parse_line + chat_session.dedup_text + the wait_for
budget idiom — NOT ChatSession. Its cwd/tempdir, --system-prompt-file, and
exclude-dynamic flags are exactly what first breath must not use: cwd IS the agent
home so its own CLAUDE.md loads (D0's raw-skills form is what makes that possible).
Tool-less via --allowed-tools ""; --strict-mcp-config with an EMPTY MCP config so no
MCP server can spawn without keys. No integration keys are needed for this turn.

The caller (server endpoint) derives `home` from its own compose result — never from
a request body — so a localhost POST can never spawn claude in an arbitrary directory.
Any error or budget overrun yields an `error` event; the page falls back to the static
first-words card (the ceremony never hangs the room).
"""
from __future__ import annotations
import asyncio
from pathlib import Path
from typing import AsyncIterator

from studio import stream_parser as sp
from studio.chat_session import dedup_text, resolve_claude

_HERE = Path(__file__).resolve().parent
BUDGET_S = 20.0


def build_greeting_prompt(owner_name: str, picks: list[str],
                          integrations: list[str], catalog: dict) -> str:
    """Constrained to composed reality (§6.4): the participant's name, the actual
    picks, and the still-unconnected integrations — and nothing unbuilt. No scheduling
    promises until r1-A ships the always-on scheduler."""
    by_id = {it["id"]: it for it in catalog.get("shelf", {}).get("items", [])}
    skills = ", ".join(by_id[p]["name"] for p in picks if p in by_id) or "your baseline"
    unconnected = ", ".join(integrations) or "none"
    return (
        f"You have just been composed at the workshop. Greet {owner_name} by name, in "
        f"your own voice, in at most 3 short sentences. Your installed skills: {skills}. "
        f"Integrations not yet connected: {unconnected}. If any are unconnected, say you "
        "are ready the moment they're connected — connecting is the very next page of "
        "the studio. Reference only what is actually installed and promise nothing "
        "else: no schedules, no automatic runs, no tools you don't have. This is "
        "non-interactive; do not ask questions and do not use tools."
    )


def build_first_breath_argv(claude_bin: str, prompt: str, empty_mcp: Path) -> list[str]:
    return [claude_bin, "-p", prompt,
            "--output-format", "stream-json", "--verbose",
            "--include-partial-messages",
            "--allowed-tools", "",
            "--strict-mcp-config", "--mcp-config", str(empty_mcp)]


async def first_breath(home: Path, prompt: str, budget: float = BUDGET_S) -> AsyncIterator[dict]:
    claude_bin = resolve_claude()
    if not claude_bin:
        yield {"type": "error", "message": "`claude` CLI not found on PATH"}
        return
    # gate-2 R5: the empty MCP config lives under the studio's own gitignored cache,
    # never the SHARED OS temp dir (two studios on one machine must not clobber it).
    empty_mcp = _HERE / ".cache" / "first-breath-empty-mcp.json"
    empty_mcp.parent.mkdir(parents=True, exist_ok=True)
    empty_mcp.write_text('{"mcpServers": {}}', encoding="utf-8")
    argv = build_first_breath_argv(claude_bin, prompt, empty_mcp)
    try:
        proc = await asyncio.create_subprocess_exec(
            *argv, cwd=str(home),
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    except (FileNotFoundError, OSError) as e:
        yield {"type": "error", "message": f"couldn't start claude: {e}"}
        return
    loop = asyncio.get_running_loop()
    deadline = loop.time() + budget
    saw_delta = False
    try:
        while True:
            remaining = deadline - loop.time()
            if remaining <= 0:
                raise asyncio.TimeoutError
            raw = await asyncio.wait_for(proc.stdout.readline(), timeout=remaining)
            if not raw:
                break
            event = sp.parse_line(raw.decode("utf-8", "replace"))
            if not event or sp.is_system(event):
                continue
            text, saw_delta = dedup_text(event, saw_delta)
            if text:
                yield {"type": "token", "text": text}
            if sp.is_turn_end(event):
                break
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        yield {"type": "error", "message": f"first breath exceeded the {budget:.0f}s budget"}
        return
    try:
        # gate-2 R5: the exit wait rides the SAME budget — a claude that streamed its
        # turn but won't exit must not hang the ceremony either.
        await asyncio.wait_for(proc.wait(), timeout=max(deadline - loop.time(), 0.5))
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        yield {"type": "done"}   # the greeting already streamed — a slow exit isn't a failure
        return
    if proc.returncode not in (0, None):
        yield {"type": "error", "message": f"claude exited {proc.returncode}"}
        return
    yield {"type": "done"}
