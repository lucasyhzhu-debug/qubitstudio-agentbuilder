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


_PHASES = {"welcome", "baseline", "skills", "personalize", "name", "build", "connect"}
# The connect-row integrations the studio can actually render (app.js WIZARD_FIELDS +
# the scheduler info row). Hardcoded on purpose: an unknown id must be skipped
# server-side too, not only by the renderer (spec §3.2).
_INTEGRATIONS = {"google", "discord", "linear", "scheduler"}


def _valid_block(obj, catalog_ids) -> dict | None:
    """One typed block from the closed vocabulary (spec §3.2). Unknown type or missing
    per-type required fields → None (skipped); the rest of the blocks still render."""
    if not isinstance(obj, dict):
        return None
    btype = obj.get("type")
    if btype == "step":
        text = obj.get("text")
        if not (isinstance(text, str) and text.strip()):
            return None
        n = obj.get("n")
        return {"type": "step", "n": n if isinstance(n, int) else 0, "text": text.strip()}
    if btype == "key-field":
        integ = obj.get("integration")
        if not (isinstance(integ, str) and integ.strip() in _INTEGRATIONS):
            return None
        label = obj.get("label") if isinstance(obj.get("label"), str) else ""
        return {"type": "key-field", "integration": integ.strip(), "label": label}
    if btype == "checklist":
        items = obj.get("items")
        if not (isinstance(items, list) and items
                and all(isinstance(i, str) and i.strip() for i in items)):
            return None
        return {"type": "checklist", "items": [i.strip() for i in items]}
    if btype == "note":
        text = obj.get("text")
        if not (isinstance(text, str) and text.strip()):
            return None
        return {"type": "note", "text": text.strip()}
    if btype == "skill-card":
        sid = obj.get("id")
        if not (isinstance(sid, str) and sid in catalog_ids):
            return None
        return {"type": "skill-card", "id": sid}
    return None  # unknown type — the vocabulary can grow without breaking old clients


def _valid_chapter(obj, catalog_ids) -> dict | None:
    """Validate the optional chapter field (spec §3.1). Tolerant: anything structurally
    wrong (including an unknown phase) returns None — the page falls back to appending
    prose to the open chapter; a malformed chapter must never kill picks/ask sync.
    Malformed `blocks` → [] with the chapter itself still landing."""
    if not isinstance(obj, dict):
        return None
    title, phase = obj.get("title"), obj.get("phase")
    if not (isinstance(title, str) and title.strip() and len(title.strip()) <= 80):
        return None
    if not (isinstance(phase, str) and phase in _PHASES):
        return None
    blocks = []
    raw = obj.get("blocks")
    if isinstance(raw, list):
        for b in raw:
            vb = _valid_block(b, catalog_ids)
            if vb is not None:
                blocks.append(vb)
    return {"title": title.strip(), "phase": phase, "blocks": blocks}


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
            "ask": _valid_ask(obj.get("ask")),
            "chapter": _valid_chapter(obj.get("chapter"), catalog_ids)}
