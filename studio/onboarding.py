"""Onboarding state + materials intake (onboarding-cards spec §5.1–5.3).

Everything is local: dropped files are staged under studio/.cache/ (gitignored) until the
participant chooses their second brain, then are COPIED into <sb>/inbox/onboarding/ —
staging is cleared by the server only after the distill settles, so an in-flight distill
never loses its inputs (final review C2). The second brain is the SAME directory compose
later uses as the vault — one memory, two readers.
State raises ValueError on bad input; the server maps that to a preflight error.
"""
from __future__ import annotations
import base64
import binascii
import json
from datetime import datetime, timezone
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_REPO = _HERE.parent
STATE_PATH = _HERE / ".cache" / "onboarding.json"
STAGING = _HERE / ".cache" / "onboarding-inbox"
MAX_FILE_BYTES = 20 * 2**20
MAX_FILES = 40
MAX_TOTAL_BYTES = 100 * 2**20


def load_state() -> dict:
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_state(state: dict) -> dict:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")
    return state


def completed() -> bool:
    return bool(load_state().get("completed_at"))


def _materials(state: dict) -> dict:
    return state.setdefault("materials", {"copied": [], "folders": []})


def set_name(name: str) -> dict:
    name = (name or "").strip()
    if not name or len(name) > 60:
        raise ValueError("name must be 1-60 characters")
    state = load_state()
    state["name"] = name
    return save_state(state)


def stage_file(filename: str, b64: str) -> dict:
    fname = Path(filename or "").name          # basename only — no traversal
    if not fname or fname in (".", ".."):
        raise ValueError("missing filename")
    try:
        data = base64.b64decode(b64 or "", validate=True)
    except (binascii.Error, ValueError):
        raise ValueError("file content is not valid base64")
    if len(data) > MAX_FILE_BYTES:
        raise ValueError(f"{fname} is over the {MAX_FILE_BYTES // 2**20} MB per-file limit")
    state = load_state()
    mats = _materials(state)
    if len(mats["copied"]) >= MAX_FILES:
        raise ValueError(f"more than {MAX_FILES} files — link a folder instead")
    STAGING.mkdir(parents=True, exist_ok=True)
    total = sum(f.stat().st_size for f in STAGING.iterdir() if f.is_file())
    if total + len(data) > MAX_TOTAL_BYTES:
        raise ValueError("total upload size limit reached — link a folder instead")
    (STAGING / fname).write_bytes(data)
    if fname not in mats["copied"]:
        mats["copied"].append(fname)
    return save_state(state)


def register_folder(folder: str) -> dict:
    p = Path(folder or "").expanduser()
    if not str(p).strip() or str(p) == ".":   # Path("") -> "." — never link the cwd
        raise ValueError("choose a folder to link")
    if not p.is_dir():
        raise ValueError(f"not a folder on this machine: {folder}")
    state = load_state()
    mats = _materials(state)
    sp = str(p.resolve())
    if sp not in mats["folders"]:
        mats["folders"].append(sp)
    return save_state(state)


def set_second_brain(path: str) -> dict:
    p = Path(path or "").expanduser()
    if not str(p).strip():
        raise ValueError("choose a folder for your second brain")
    p = p if p.is_absolute() else Path.home() / p
    p = p.resolve()
    if p.is_relative_to(_REPO.resolve()):
        raise ValueError("pick a home outside the studio repo — this one is public")
    inbox = p / "inbox" / "onboarding"
    inbox.mkdir(parents=True, exist_ok=True)
    if STAGING.exists():
        # COPY, don't move — a materials/done-started distill may still be reading
        # STAGING; the server clears it after the distill settles (final review C2).
        for f in sorted(STAGING.iterdir()):
            if f.is_file():
                (inbox / f.name).write_bytes(f.read_bytes())
    state = load_state()
    mats = _materials(state)
    index = ["# Materials", "", "## Copied into inbox/onboarding/"]
    index += [f"- {n}" for n in mats["copied"]] or ["- (none)"]
    index += ["", "## Linked folders (read in place)"]
    index += [f"- {n}" for n in mats["folders"]] or ["- (none)"]
    (p / "materials.md").write_text("\n".join(index) + "\n", encoding="utf-8")
    state["second_brain"] = str(p)
    return save_state(state)


def materials_sources() -> list[Path]:
    """Distiller inputs: the staging dir (only if it holds files) + linked folders.
    Always ensures STAGING exists so a folders-only run can still use it as cwd."""
    STAGING.mkdir(parents=True, exist_ok=True)
    sources: list[Path] = []
    if any(f.is_file() for f in STAGING.iterdir()):
        sources.append(STAGING)
    state = load_state()
    sources += [Path(f) for f in _materials(state)["folders"] if Path(f).is_dir()]
    return sources


def write_profile(text: str | None) -> Path:
    state = load_state()
    sb = state.get("second_brain")
    if not sb:
        raise ValueError("second brain not chosen yet")
    if not text:
        mats = _materials(state)
        listed = "\n".join(f"- {n}" for n in mats["copied"] + mats["folders"]) or "- (none)"
        text = (f"# {state.get('name', 'Owner')}\n\n"
                f"Materials registered but not yet distilled:\n{listed}\n")
    out = Path(sb) / "profile.md"
    out.write_text(text, encoding="utf-8")
    state["completed_at"] = datetime.now(timezone.utc).isoformat()
    save_state(state)
    return out
