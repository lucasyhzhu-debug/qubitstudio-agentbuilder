"""Distill the participant's materials into a markdown owner profile.

One scoped `claude -p` pass with Read only (argv shape live-probed during spec review:
reads markdown AND genuinely views images). Mirrors tweaker._run_voice_pass: subprocess +
timeout + nonzero-exit -> RuntimeError. The CALLER treats every failure as non-fatal
(spec §5.6) — onboarding always completes, worst case with the stub profile.
"""
from __future__ import annotations
import asyncio
import tempfile
from pathlib import Path

from studio.chat_session import resolve_claude

_TIMEOUT = 180


def _prompt(source_dirs: list[Path]) -> str:
    dirs = " and ".join(str(d) for d in source_dirs)
    return (
        f"Read the files under {dirs} — a participant's CV (often PDF), LinkedIn "
        "screenshots (images), and writing samples. Then return a concise markdown owner "
        "profile with these sections: identity & career arc; current focus; people & "
        "organizations in their orbit; working style & voice; notable specifics worth "
        "remembering. For large folders, read a representative sample (about 30 files, "
        "prefer recent/top-level) and say what was sampled vs read fully; note unreadable "
        "files rather than failing. Return ONLY the profile markdown, no preamble, at most "
        "about 150 lines. This is non-interactive; do not ask questions."
    )


def build_distill_argv(claude_bin: str, source_dirs: list[Path]) -> list[str]:
    argv = [claude_bin, "-p", _prompt(source_dirs), "--allowed-tools", "Read"]
    for d in source_dirs:
        argv += ["--add-dir", str(d)]
    return argv


async def distill(source_dirs: list[Path], timeout: int = _TIMEOUT) -> str:
    claude_bin = resolve_claude()
    if not claude_bin:
        raise RuntimeError("`claude` CLI not found on PATH")
    argv = build_distill_argv(claude_bin, [Path(d) for d in source_dirs])
    cwd = next((str(d) for d in source_dirs if Path(d).is_dir()), tempfile.gettempdir())
    try:
        proc = await asyncio.create_subprocess_exec(
            *argv, cwd=cwd,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    except FileNotFoundError as e:
        raise RuntimeError(f"`claude` CLI not found: {e}")
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        raise RuntimeError(f"distill pass timed out after {timeout}s")
    if proc.returncode not in (0, None):
        err = stderr.decode("utf-8", "replace")[:300] if stderr else ""
        raise RuntimeError(f"claude exited {proc.returncode}: {err}")
    return (stdout or b"").decode("utf-8", "replace").strip()
