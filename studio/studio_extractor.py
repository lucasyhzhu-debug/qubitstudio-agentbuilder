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


def _valid_ask(obj) -> dict | None:
    """Validate the optional ask field (spec §4.1). Tolerant: anything structurally
    wrong returns None — a malformed ask must never kill the shelf sync."""
    if not isinstance(obj, dict):
        return None
    title = obj.get("title")
    opts = obj.get("options")
    if not isinstance(title, str) or not title.strip():
        return None
    if not isinstance(opts, list) or len(opts) < 2:
        return None
    out_opts = []
    for i, o in enumerate(opts):
        if not isinstance(o, dict):
            return None
        label = o.get("label")
        if not isinstance(label, str) or not label.strip():
            return None
        oid = o.get("id")
        if not (isinstance(oid, str) and oid.strip()):
            oid = chr(ord("a") + i)                      # positional default: a, b, c…
        why = o.get("why") if isinstance(o.get("why"), str) else ""
        out_opts.append({"id": oid, "label": label.strip(), "why": why})
    aid = obj.get("id")
    if not (isinstance(aid, str) and aid.strip()):
        aid = "ask"
    why = obj.get("why") if isinstance(obj.get("why"), str) else ""
    return {"id": aid, "title": title.strip(), "why": why, "options": out_opts,
            "multi": bool(obj.get("multi")), "allow_custom": True}


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
    return {"picks": picks, "name": name, "ready": bool(obj.get("ready")),
            "ask": _valid_ask(obj.get("ask"))}
