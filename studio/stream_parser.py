"""Pure helpers over claude-CLI `--output-format stream-json` lines.

Newline-delimited JSON. We drop every `type:"system"` event (the user's global
SessionStart hooks flood the stream with these), accumulate text from `type:"assistant"`
(full message) and `type:"stream_event"` (partial token deltas), and treat `type:"result"`
as end-of-turn. Field paths verified against studio/tests/fixtures/ (Task 0).
"""
from __future__ import annotations
import json


def parse_line(line: str) -> dict | None:
    line = (line or "").strip()
    if not line:
        return None
    try:
        obj = json.loads(line)
    except (json.JSONDecodeError, ValueError):
        return None
    return obj if isinstance(obj, dict) else None


def is_system(event: dict) -> bool:
    return event.get("type") == "system"


def is_turn_end(event: dict) -> bool:
    return event.get("type") == "result"


def assistant_text(event: dict) -> str:
    etype = event.get("type")
    if etype == "assistant":
        content = (event.get("message") or {}).get("content") or []
        return "".join(
            part.get("text", "") for part in content if part.get("type") == "text"
        )
    if etype == "stream_event":
        inner = event.get("event") or {}
        if inner.get("type") == "content_block_delta":
            return (inner.get("delta") or {}).get("text", "") or ""
    return ""


def session_id(event: dict) -> str | None:
    return event.get("session_id")
