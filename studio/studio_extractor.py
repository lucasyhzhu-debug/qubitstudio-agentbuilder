"""Pull the workshop studio block out of an assistant turn.

Workshop-mode chats emit the current build state each turn inside a ```studio fenced
block. We take the LAST such block (most recent state). No ```json fallback — that
fence is the SPEC extractor's fallback and sharing it would create cross-mode
ambiguity. Unknown pick ids are dropped (a hallucinated id must not kill the sync);
anything structurally wrong returns None so the caller keeps prior state.
"""
from __future__ import annotations
import json
import re

_FENCE = re.compile(r"```studio\s*\n(.*?)```", re.DOTALL)


def extract_studio(assistant_text: str, catalog_ids: set[str]) -> dict | None:
    matches = _FENCE.findall(assistant_text or "")
    if not matches:
        return None
    try:
        obj = json.loads(matches[-1].strip())
    except (json.JSONDecodeError, ValueError):
        return None
    if not isinstance(obj, dict) or not isinstance(obj.get("picks"), list):
        return None
    picks = [p for p in obj["picks"] if isinstance(p, str) and p in catalog_ids]
    picks = list(dict.fromkeys(picks))  # dedupe, preserving first-seen order
    name = obj.get("name")
    if not isinstance(name, str) or not name.strip():
        name = None
    return {"picks": picks, "name": name, "ready": bool(obj.get("ready"))}
