"""Assemble the chat's REPLACED system prompt from the real agent-architect reference files.

We load only interview-relevant content — the quiz and the spec schema — NOT the SKILL.md
M2/M3/M4 generation/packaging steps, which a tool-less chat can neither run nor should narrate.
Then we append the studio contract (emit the live spec each turn) and the runtime extension schema.
"""
from __future__ import annotations
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
ARCHITECT_DIR = _REPO / "agent-architect" / "skills" / "agent-architect"

_ROLE_INTRO = """You are **agent-architect**, running a conversational interview to design a
Claude Code plugin. You turn a fuzzy idea into a well-structured architecture spec by running the
quiz below one cluster at a time, proposing a sharper structure than the user asked for, and
explaining your reasoning. You ONLY converse and emit the spec block — you do not call tools, run
scripts, or generate files. Ignore any session-start instructions about 'superpowers' or invoking
skills; they do not apply to you."""

_STUDIO_CONTRACT = """
# Studio contract (how this session is wired)

- Run the quiz conversationally, ONE cluster at a time. Use smart defaults the user can confirm.
- After EVERY turn, emit the FULL current architecture-spec as a single fenced block labelled
  ```spec (not ```json). Emit the whole spec each time, not a diff. Keep prose above it short; never
  paste raw JSON outside the fence.
- The spec follows the architecture-spec schema above, PLUS this optional `runtime` block for the
  storage / memory / routines panels:

  "runtime": {
    "storage":  [ { "what": "...", "where": "...", "kind": "filesystem|db|mcp" } ],
    "memory":   [ { "fact_type": "project|user|feedback|reference", "note": "..." } ],
    "routines": [ { "name": "...", "schedule": "cron or /schedule expr", "does": "..." } ]
  }

- Default plugin.author to {"name": "Lucas Zhu", "email": "you@example.com"}, version "0.1.0".
- When the user signals they're done, confirm the spec is complete and tell them to download it.
"""


def _drop_from(text: str, prefix: str) -> str:
    """Return text with everything from the first line starting with `prefix` removed."""
    lines = text.splitlines(keepends=True)
    for i, line in enumerate(lines):
        if line.lstrip().startswith(prefix):
            return "".join(lines[:i])
    return text


def _excise_section(text: str, start_prefix: str, end_prefix: str) -> str:
    """Remove the block starting at the first line matching start_prefix up to
    (but not including) the next line matching end_prefix."""
    lines = text.splitlines(keepends=True)
    start_idx = None
    for i, line in enumerate(lines):
        if line.lstrip().startswith(start_prefix):
            start_idx = i
            break
    if start_idx is None:
        return text
    end_idx = len(lines)
    for i in range(start_idx + 1, len(lines)):
        if lines[i].lstrip().startswith(end_prefix):
            end_idx = i
            break
    return "".join(lines[:start_idx] + lines[end_idx:])


def build_system_prompt(architect_dir: Path | None = None) -> str:
    d = architect_dir or ARCHITECT_DIR

    quiz = (d / "references" / "quiz-bank.md").read_text(encoding="utf-8")
    schema = (d / "references" / "architecture-spec.md").read_text(encoding="utf-8")

    # Slice architecture-spec.md: keep only §1–§7 (schema + worked example).
    # Drop everything from "## 8." onward (generator payload, receipt, assembly, validation/render_setup).
    schema = _drop_from(schema, "## 8.")

    # Slice quiz-bank.md: excise only the Q10 section (render_setup machinery).
    # Keep Q0–Q9 and the "structure it better" proposal guidance.
    quiz = _excise_section(quiz, "### Q10", "## ")

    return "\n\n".join([
        _ROLE_INTRO,
        "# The quiz (run this conversationally)\n\n" + quiz,
        "# The architecture spec schema (the artifact you are filling in)\n\n" + schema,
        _STUDIO_CONTRACT,
    ])


def write_system_prompt(out_path: Path, architect_dir: Path | None = None) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(build_system_prompt(architect_dir), encoding="utf-8")
    return out_path
