"""Post-compose voice personalization: (1) ALWAYS-SAFE structured `{{OWNER_*}}` substitution across
the composed tree (whatever's nested under the passed root — plugin files, seeded vault identity
files, wherever), then (2) an OPTIONAL, non-fatal `claude -p` voice pass that rewrites the personality
tone block to match a pasted writing sample. Phase 1 alone always reaches `done`; phase 2 failure
(missing claude, timeout, nonzero exit) degrades to a `log` warning, never blocks completion."""
from __future__ import annotations
import asyncio
from pathlib import Path
from typing import AsyncIterator

from studio.chat_session import resolve_claude

# Only text-ish files are worth scanning for `{{KEY}}` placeholders — mirrors composer.py's
# delucas() extension set so we don't choke decoding binaries under the tree.
_TEXT_EXT = {".md", ".json", ".txt", ".py", ".ps1"}

# Single scoped edit turn (rewrite one tone block), not a full build — keep the non-fatal
# voice pass from hanging the SSE stream indefinitely if `claude` stalls.
_VOICE_TIMEOUT = 120


def _placeholder_fields(fields: dict) -> dict:
    """`voice_sample` is input to phase 2, not a `{{OWNER_*}}` placeholder value — never substitute it."""
    return {k: v for k, v in (fields or {}).items() if k != "voice_sample"}


def _substitute_roots(roots: list[Path], fields: dict) -> list[str]:
    """Walk every text file under each root in `roots` (recursively — placeholders can live
    anywhere under a passed root, e.g. a seeded vault nested inside a plugin tree, or a sibling
    vault passed separately) and replace `{{KEY}}` for each key in `fields`. Returns the relative
    paths (root-prefixed) of files actually changed. Callers must dedupe `roots` first (one
    root nested inside another would otherwise double-scan, though not double-write since the
    second pass would just find no more `{{KEY}}` left)."""
    subs = _placeholder_fields(fields)
    if not subs:
        return []
    touched: list[str] = []
    for root in roots:
        for f in Path(root).rglob("*"):
            if not (f.is_file() and f.suffix.lower() in _TEXT_EXT):
                continue
            try:
                text = f.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            new = text
            for key, val in subs.items():
                new = new.replace("{{" + key + "}}", str(val))
            if new != text:
                f.write_text(new, encoding="utf-8")
                touched.append(str(f.relative_to(root)))
    return touched


def _dedupe_roots(roots: list[Path]) -> list[Path]:
    """Drop any root that is nested inside another root in the list (would otherwise be
    scanned twice for no benefit)."""
    resolved = [r.resolve() for r in roots]
    keep: list[Path] = []
    for i, r in enumerate(resolved):
        if any(i != j and r != other and r.is_relative_to(other) for j, other in enumerate(resolved)):
            continue
        keep.append(r)
    return keep


def build_voice_argv(claude_bin: str, dirs: list[Path], owner_voice: str, voice_sample: str) -> list[str]:
    """--allowed-tools is VARIADIC: tools are SEPARATE argv tokens ("Read", "Edit"), never one
    space-joined string. Scoped tight: read/edit only, one `--add-dir` per root in `dirs` (the
    plugin tree — which carries the composed agent's root CLAUDE.md identity — and, when composed
    separately, the sibling vault holding `meta/chief-of-staff/personality.md`)."""
    dirs_str = " and ".join(str(d) for d in dirs)
    prompt = (
        "Rewrite ONLY the personality/voice/tone description block in the composed agent's identity "
        f"files under {dirs_str} (the '## Voice' section in the agent's root CLAUDE.md, and the "
        "'Voice' section in meta/chief-of-staff/personality.md) so "
        "its tone matches the writing sample below. Keep every other section, structure, and heading "
        "untouched — change tone language only. This is non-interactive; do not ask questions.\n\n"
        f"Voice description: {owner_voice or '(none given)'}\n\n"
        f"Writing sample:\n{voice_sample}\n"
    )
    argv = [claude_bin, "-p", prompt,
            "--permission-mode", "acceptEdits",
            "--allowed-tools", "Read", "Edit"]
    for d in dirs:
        argv += ["--add-dir", str(d)]
    return argv


async def _run_voice_pass(dirs: list[Path], fields: dict, voice_sample: str) -> None:
    claude_bin = resolve_claude()
    if not claude_bin:
        raise RuntimeError("`claude` CLI not found on PATH")
    argv = build_voice_argv(claude_bin, dirs, fields.get("OWNER_VOICE", ""), voice_sample)
    try:
        proc = await asyncio.create_subprocess_exec(
            *argv, cwd=str(dirs[0]),
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    except FileNotFoundError as e:
        raise RuntimeError(f"`claude` CLI not found: {e}")
    try:
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=_VOICE_TIMEOUT)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        raise RuntimeError(f"voice pass timed out after {_VOICE_TIMEOUT}s")
    if proc.returncode not in (0, None):
        err = stderr.decode("utf-8", "replace")[:300] if stderr else ""
        raise RuntimeError(f"claude exited {proc.returncode}: {err}")


async def tweak(tree: Path, fields: dict, vault_dir: Path | None = None) -> AsyncIterator[dict]:
    """`tree` is the composed plugin root. `vault_dir`, when given and existing, is the SIBLING
    vault output (composer.py writes them as two separate roots — the vault holds the seeded
    `meta/chief-of-staff/personality.md` identity file with the `{{OWNER_*}}` placeholders; the
    plugin tree has no personality file of its own). Phase 1 substitution walks BOTH roots;
    phase 2's voice pass gets `--add-dir` for both so it can find and edit the real file."""
    tree = Path(tree)
    fields = dict(fields or {})
    voice_sample = (fields.get("voice_sample") or "").strip()

    dirs = [tree]
    if vault_dir is not None and Path(vault_dir).exists():
        dirs.append(Path(vault_dir))
    dirs = _dedupe_roots(dirs)

    # Phase 1 — ALWAYS-SAFE structured substitution. Ends in `done` even if phase 2 below is
    # skipped or fails; only a genuine filesystem error here (not expected — pure text swap)
    # short-circuits before `done`.
    try:
        yield {"type": "stage", "name": "substitute", "status": "running"}
        touched = _substitute_roots(dirs, fields)
        for rel in touched:
            yield {"type": "log", "text": f"filled placeholders in {rel}"}
        if not touched:
            yield {"type": "log", "text": "no {{OWNER_*}} placeholders found to fill"}
        yield {"type": "stage", "name": "substitute", "status": "ok"}
    except Exception as e:
        yield {"type": "stage", "name": "substitute", "status": "fail"}
        yield {"type": "error", "stage": "substitute", "message": f"{type(e).__name__}: {e}"}
        return

    # Phase 2 — OPTIONAL voice pass. Non-fatal by design: any failure degrades to a log
    # warning, never blocks the overall `done`.
    if voice_sample:
        yield {"type": "stage", "name": "voice", "status": "running"}
        try:
            await _run_voice_pass(dirs, fields, voice_sample)
            yield {"type": "stage", "name": "voice", "status": "ok"}
        except Exception as e:
            yield {"type": "stage", "name": "voice", "status": "fail"}
            yield {"type": "log", "text": f"⚠ voice pass skipped (non-fatal): {type(e).__name__}: {e}"}

    yield {"type": "done"}
