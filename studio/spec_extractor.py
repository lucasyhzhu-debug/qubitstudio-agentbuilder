"""Pull the live agent blueprint (architecture-spec JSON) out of an assistant turn.

The chat is instructed to emit the full current spec each turn inside a ```spec fenced
block. We take the LAST such block (the most recent state), and accept a ```json fence
as a fallback. Returns None on anything malformed so the caller keeps the prior blueprint.
"""
from __future__ import annotations
import json
import re

_FENCE = re.compile(r"```(?:spec|json)\s*\n(.*?)```", re.DOTALL)


def extract_spec(assistant_text: str) -> dict | None:
    matches = _FENCE.findall(assistant_text or "")
    if not matches:
        return None
    raw = matches[-1].strip()
    try:
        obj = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return None
    if not _is_valid_blueprint(obj):
        return None
    return obj


def _is_valid_blueprint(obj: object) -> bool:
    return (
        isinstance(obj, dict)
        and isinstance(obj.get("plugin"), dict)
        and isinstance(obj["plugin"].get("name"), str)
        and obj["plugin"]["name"].strip() != ""
        and isinstance(obj.get("components"), list)
    )
