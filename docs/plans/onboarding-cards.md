# Onboarding Journey + Guided Card Framework — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** First-launch onboarding — cinematic welcome, agent-guided intake of the participant's materials, a participant-chosen "second brain" that seeds the shared wiki memory — plus a reusable guided-card UI framework with a visual ask-question channel for the tool-less chat.

**Architecture:** A vanilla-JS card primitive (`cards.js`) renders guided steps in the right-panel rail; the live workshop `claude -p` session narrates the walk, driven by UI-sent `[studio event]` messages and answering through a new `ask` field in the existing ` ```studio ` block. A distiller (`claude -p --allowed-tools Read`, mirroring the tweaker) turns dropped materials into `<second-brain>/profile.md`; the second brain becomes compose's `vault_dir`, so architect and composed chief-of-staff read one memory.

**Tech Stack:** FastAPI + vanilla JS (no build step), pytest, `claude` CLI subprocess.

**Spec:** `docs/specs/2026-07-02-studio-onboarding-cards-design.md` (shipshape-reviewed; read it first).
**Review:** `docs/reviews/shipshape-studio-onboarding-cards-spec-2026-07-02.md`.

**Flagged deviations (deliberate, not omissions):**
- ROADMAP/CHANGELOG updates ride the pipeline's landing PR (spec-plan-pipeline step 6), not a task here.
- This plan was written while the QubitStudio journey slice was still executing on `feat/qubitstudio-journey-impl`. **Task 0 verifies the landed journey code before anything else runs**; if any Task 0 check fails, STOP and reconcile against the merged code instead of coding on assumptions.

## Global Constraints

- Branch: `feat/onboarding-cards` (exists, holds the spec + review). Rebase onto `main` AFTER the journey slice merges; commit per task.
- Repo is PUBLIC — no real keys/tokens/ids/emails/personal values in any commit. All participant data lives in gitignored `studio/.cache/` or the user-chosen second brain (rejected if inside the repo).
- `chief-of-staff/` and `agent-architect/` are NOT touched by any task.
- Architect mode stays byte-identical: `build_system_prompt()` and its tests unchanged.
- No new third-party imports (stdlib + existing FastAPI/pytest only; frontend stays vanilla-JS IIFE).
- All pytest runs use the repo venv: `.venv/Scripts/python -m pytest …` (Windows dev box; participant-facing code stays cross-platform — `pathlib`, `expanduser`, no shell-outs).
- Caps (spec §5.2): 20 MB/file, 40 files, ~100 MB total per onboarding run; profile injection head-capped at 6,000 chars.
- Bracketed message conventions: `[studio event] …` (UI → agent, never displayed) and `[card] …` (card answers, never displayed as user bubbles).

---

### Task 0: Verify the landed journey base (no code — gate)

**Files:** none (read-only verification).

- [ ] **Step 1: Confirm the journey slice is merged and the branch is rebased**

```bash
git -C . fetch origin
git log origin/main --oneline -5   # expect the qubitstudio-journey implementation merge
git rebase origin/main             # on feat/onboarding-cards
```

- [ ] **Step 2: Verify the interfaces this plan builds on** (all must hold; if any fails, STOP and reconcile)

```bash
grep -n "def extract_studio" studio/studio_extractor.py          # (assistant_text, catalog_ids) -> dict | None
grep -n "catalog_ids" studio/chat_session.py                     # ChatSession(..., catalog_ids=None), self.studio
grep -n "_extract" studio/chat_session.py                        # end-of-turn extraction hook
grep -n "workshop" studio/server.py                              # _WORKSHOP_PROMPT + mode branch in new_session
grep -n "build_workshop_prompt" studio/system_prompt.py          # (catalog_path=None)
grep -n "const MODE" studio/static/app.js                        # workshop/architect mode + SEED
grep -n "shelfSync" studio/static/shelf.js                       # window.shelfSync
grep -n "renderAgentPanel" studio/static/app.js                  # workshop right panel
grep -n -- "--sapphire" studio/static/styles.css                 # SapphireOS tokens (reskin landed)
```

- [ ] **Step 3: Full suite green before starting**

Run: `.venv/Scripts/python -m pytest studio/tests -q -m "not integration"`
Expected: all pass.

---

### Task 1: Extractor — `ask` support in the studio block

**Files:**
- Modify: `studio/studio_extractor.py`
- Test: `studio/tests/test_studio_extractor.py` (append + update equality asserts)

**Interfaces:**
- Produces: `extract_studio(assistant_text: str, catalog_ids: set[str]) -> dict | None` now returns `{"picks": list[str], "name": str|None, "ready": bool, "ask": dict|None}`. The validated ask dict is `{"id": str, "title": str, "why": str, "options": [{"id","label","why"}...], "multi": bool, "allow_custom": True}`. Tasks 6 (server passthrough) and 8 (frontend) rely on this exact shape.

- [ ] **Step 1: Write the failing tests** (append to `studio/tests/test_studio_extractor.py`)

```python
# --- ask channel (onboarding-cards spec §4.1) ---

def test_valid_ask_extracted():
    out = extract_studio(_block(
        '{"picks": [], "ask": {"id": "triage", "title": "How deep should triage go?",'
        ' "why": "sets drafting", "options": ['
        '{"id": "a", "label": "Summarize only", "why": "you act"},'
        '{"label": "Draft replies"}], "multi": false}}'), IDS)
    assert out["ask"]["title"] == "How deep should triage go?"
    assert out["ask"]["options"][0] == {"id": "a", "label": "Summarize only", "why": "you act"}
    assert out["ask"]["options"][1]["id"] == "b"          # positional default
    assert out["ask"]["allow_custom"] is True             # forced in v1
    assert out["ask"]["multi"] is False

def test_ask_absent_is_none():
    assert extract_studio(_block('{"picks": []}'), IDS)["ask"] is None

def test_ask_single_option_dropped_picks_kept():
    out = extract_studio(_block(
        '{"picks": ["crm"], "ask": {"title": "t", "options": [{"label": "only one"}]}}'), IDS)
    assert out["ask"] is None and out["picks"] == ["crm"]

def test_ask_missing_title_dropped():
    out = extract_studio(_block(
        '{"picks": [], "ask": {"options": [{"label": "x"}, {"label": "y"}]}}'), IDS)
    assert out["ask"] is None

def test_ask_non_dict_dropped():
    assert extract_studio(_block('{"picks": [], "ask": "what?"}'), IDS)["ask"] is None

def test_ask_multi_coerced():
    out = extract_studio(_block(
        '{"picks": [], "ask": {"title": "t", "multi": 1,'
        ' "options": [{"label": "x"}, {"label": "y"}]}}'), IDS)
    assert out["ask"]["multi"] is True
```

- [ ] **Step 2: Update the existing equality asserts** — the journey tests compare the full returned dict; they gain `"ask": None`:

In `test_extracts_valid_block`: `assert out == {"picks": ["crm", "briefing"], "name": "my-cos", "ready": False, "ask": None}`.
Any other test asserting full-dict equality gets the same `"ask": None` addition (run the suite to find them).

- [ ] **Step 3: Run to verify failure**

Run: `.venv/Scripts/python -m pytest studio/tests/test_studio_extractor.py -v`
Expected: new tests FAIL (`KeyError: 'ask'`); updated equality tests FAIL until implementation.

- [ ] **Step 4: Implement** — append to `studio/studio_extractor.py` and extend the return:

```python
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
```

In `extract_studio`, change the final return to:

```python
    return {"picks": picks, "name": name, "ready": bool(obj.get("ready")),
            "ask": _valid_ask(obj.get("ask"))}
```

- [ ] **Step 5: Run to verify pass**

Run: `.venv/Scripts/python -m pytest studio/tests/test_studio_extractor.py studio/tests/test_chat_session.py -v`
Expected: all pass (chat-session tests exercise the extractor return via `_extract` — any full-dict asserts there also gain `"ask": None`).

- [ ] **Step 6: Commit**

```bash
git add studio/studio_extractor.py studio/tests/test_studio_extractor.py studio/tests/test_chat_session.py
git commit -m "feat(studio): ask field in the studio block — visual questions from the tool-less chat"
```

---

### Task 2: ChatSession turn serialization (review Critical C1)

**Files:**
- Modify: `studio/chat_session.py`
- Test: `studio/tests/test_chat_session.py` (append)

**Interfaces:**
- Produces: `ChatSession.send()` guarded by a per-instance `asyncio.Lock` — a second concurrent caller awaits the first turn's completion. No signature change; Tasks 8/9's programmatic sends rely on this backstop.

- [ ] **Step 1: Write the failing test** (append to `studio/tests/test_chat_session.py`)

```python
@pytest.mark.asyncio
async def test_concurrent_sends_serialize(tmp_path, monkeypatch):
    # Two overlapping send() calls must not run two `claude -p --resume` subprocesses
    # at once (onboarding-cards spec §5.4.8): spawn/finish pairs must not interleave.
    import asyncio as aio
    order = []

    class _FakeProc:
        returncode = 0
        stderr = None
        def __init__(self):
            self.stdout = self
        def __aiter__(self):
            return self
        async def __anext__(self):
            raise StopAsyncIteration
        async def wait(self):
            return 0

    async def fake_exec(*argv, **kw):
        order.append("spawn")
        await aio.sleep(0.05)      # long enough for the other task to try to enter
        order.append("live")
        return _FakeProc()

    monkeypatch.setattr(aio, "create_subprocess_exec", fake_exec)
    s = _sess(tmp_path)

    async def drain(msg):
        async for _ in s.send(msg):
            pass

    await aio.gather(drain("a"), drain("b"))
    assert order == ["spawn", "live", "spawn", "live"]   # serialized, not interleaved
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/Scripts/python -m pytest studio/tests/test_chat_session.py::test_concurrent_sends_serialize -v`
Expected: FAIL — `order == ["spawn", "spawn", "live", "live"]` (interleaved).

- [ ] **Step 3: Implement.** In `ChatSession.__init__` add:

```python
        # One `claude -p --resume` per session at a time (onboarding-cards spec §5.4.8):
        # programmatic [studio event] sends must never fork a concurrent subprocess on
        # the same session id.
        self._lock = asyncio.Lock()
```

In `send()`, wrap the ENTIRE existing body:

```python
    async def send(self, user_msg: str) -> AsyncIterator[dict]:
        async with self._lock:
            argv = self.build_argv(user_msg)
            # …existing body unchanged, indented one level…
```

- [ ] **Step 4: Run to verify pass**

Run: `.venv/Scripts/python -m pytest studio/tests/test_chat_session.py -v`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add studio/chat_session.py studio/tests/test_chat_session.py
git commit -m "fix(studio): serialize ChatSession turns — one claude --resume per session"
```

---

### Task 3: Workshop prompt — ask contract, participant section, onboarding walk

**Files:**
- Modify: `studio/system_prompt.py` (workshop builder only)
- Test: `studio/tests/test_system_prompt.py` (append)

**Interfaces:**
- Consumes: existing `build_workshop_prompt(catalog_path=None)` and `write_system_prompt(out_path, architect_dir=None, mode="architect", catalog_path=None)`.
- Produces: `build_workshop_prompt(catalog_path=None, participant: dict | None = None, onboarding: bool = False) -> str` and `write_system_prompt(..., participant=None, onboarding=False)`. `participant = {"name": str, "second_brain": str, "profile_text": str, "materials_index": str}`. Task 6 (server) passes both.

- [ ] **Step 1: Write the failing tests** (append to `studio/tests/test_system_prompt.py`)

```python
# --- onboarding-cards spec §4.3 + §5.5 ---
_P = {"name": "Ada", "second_brain": "C:/tmp/sb",
      "profile_text": "# Ada\n\nAnalyst at Babbage & Co.", "materials_index": "cv.pdf"}

def test_workshop_ask_contract_always_present():
    for kw in ({}, {"onboarding": True}, {"participant": _P}):
        p = build_workshop_prompt(**kw)
        assert '"ask"' in p and "[card]" in p

def test_participant_section_injected():
    p = build_workshop_prompt(participant=_P)
    assert "The participant" in p and "Ada" in p and "Babbage" in p and "C:/tmp/sb" in p

def test_participant_profile_capped():
    big = dict(_P, profile_text="x" * 20000)
    p = build_workshop_prompt(participant=big)
    assert "x" * 6000 in p and "x" * 6001 not in p

def test_onboarding_contract_only_when_flagged():
    assert "studio event" in build_workshop_prompt(onboarding=True)
    assert "studio event" not in build_workshop_prompt()

def test_write_system_prompt_threads_kwargs(tmp_path):
    from studio.system_prompt import write_system_prompt
    out = write_system_prompt(tmp_path / "wp.md", mode="workshop", participant=_P, onboarding=False)
    assert "Ada" in out.read_text(encoding="utf-8")

def test_architect_mode_still_byte_identical(tmp_path):
    from studio.system_prompt import write_system_prompt, build_system_prompt
    out = write_system_prompt(tmp_path / "sp.md")
    assert out.read_text(encoding="utf-8") == build_system_prompt()
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/Scripts/python -m pytest studio/tests/test_system_prompt.py -v`
Expected: new tests FAIL (`TypeError: unexpected keyword argument 'participant'`); existing pass.

- [ ] **Step 3: Implement.** Append to `studio/system_prompt.py`:

```python
_ASK_CONTRACT = """
# Asking questions (the card UI)

- Whenever you offer the participant a small closed set of choices, ALSO emit it as an
  "ask" object inside the studio block (same fence). Shape:
  "ask": { "id": "triage-depth", "title": "How aggressive should inbox triage be?",
           "why": "one line of context",
           "options": [ {"id": "a", "label": "Summarize only", "why": "daily digest, you act"},
                        {"id": "b", "label": "Draft replies",  "why": "it writes, you send"} ],
           "multi": false }
- Give every option a one-line consequence in "why". At most ONE pending ask at a time;
  omit "ask" entirely when nothing is pending.
- The participant's answer arrives as a normal message starting with [card] — a clicked
  choice, a custom-typed answer, or a skip. After emitting an ask, keep the prose above it
  short and do NOT restate the options in text.
"""

_ONBOARDING_CONTRACT = """
# The onboarding walk (this session starts BEFORE the interview)

- Messages starting with [studio event] come from the studio itself, not the participant.
  Never quote them back; react to what they report.
- The walk, in order — narrate each step and point the participant to the panel on their
  right, ONE step at a time:
  1. Greet the participant warmly by name. Ask them to drop their CV, LinkedIn
     screenshots, and anything they've written into the panel on the right. Reassure them:
     everything stays on their machine.
  2. As [studio event] messages report registered files/folders, acknowledge briefly and
     invite more or tell them to continue when ready.
  3. When asked where the mind-palace should live, explain it in one breath: one folder
     they own, plain files — everything you'll learn about them, their people, and your
     own lessons lives there.
  4. When a [studio event] delivers the distilled profile, react WITH SPECIFICS — name
     real details you learned (roles, orgs, themes). This is the proof you actually read
     their materials. If the event says materials were registered but not distilled, say
     you'll read them as you work together instead.
  5. If an event says the participant skipped a step, accept it gracefully and move on.
  6. Then flow straight into the normal interview (one topic at a time). Same
     conversation, no reset.
- Keep emitting the full studio block every turn throughout (picks stays [] until the
  interview produces recommendations).
"""


def _participant_section(p: dict) -> str:
    profile = (p.get("profile_text") or "")[:6000]
    return (
        "# The participant\n\n"
        f"- Name: {p.get('name', '')} — greet and refer to them by name.\n"
        f"- Their second brain (your mind-palace) lives at: {p.get('second_brain', '')}\n"
        f"- Materials they shared: {p.get('materials_index', '') or '(none)'}\n\n"
        "Their standing profile (distilled from their own materials — treat as ground truth):\n\n"
        f"{profile}\n"
    )
```

Change `build_workshop_prompt` to:

```python
def build_workshop_prompt(catalog_path: Path | None = None,
                          participant: dict | None = None,
                          onboarding: bool = False) -> str:
    path = catalog_path or (_STUDIO_DIR / "catalog.json")
    catalog = json.loads(path.read_text(encoding="utf-8"))
    parts = [_WORKSHOP_ROLE_INTRO]
    if participant:
        parts.append(_participant_section(participant))
    parts.append("# The substrate & the shelf\n\n" + _render_catalog(catalog))
    parts.append(_WORKSHOP_CONTRACT)
    parts.append(_ASK_CONTRACT)
    if onboarding:
        parts.append(_ONBOARDING_CONTRACT)
    return "\n\n".join(parts)
```

And `write_system_prompt` to thread the kwargs:

```python
def write_system_prompt(out_path: Path, architect_dir: Path | None = None,
                        mode: str = "architect", catalog_path: Path | None = None,
                        participant: dict | None = None, onboarding: bool = False) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    content = (build_workshop_prompt(catalog_path, participant=participant, onboarding=onboarding)
               if mode == "workshop" else build_system_prompt(architect_dir))
    out_path.write_text(content, encoding="utf-8")
    return out_path
```

- [ ] **Step 4: Run to verify pass**

Run: `.venv/Scripts/python -m pytest studio/tests/test_system_prompt.py -v`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add studio/system_prompt.py studio/tests/test_system_prompt.py
git commit -m "feat(studio): workshop prompt — ask contract, participant memory, onboarding walk"
```

---

### Task 4: `studio/onboarding.py` — state, staging, second brain

**Files:**
- Create: `studio/onboarding.py`
- Test: `studio/tests/test_onboarding.py`

**Interfaces:**
- Produces (all consumed by Task 6's endpoints):
  - `load_state() -> dict` / `save_state(state: dict) -> dict`
  - `completed() -> bool`
  - `set_name(name: str) -> dict` — raises `ValueError` on empty/oversized
  - `stage_file(filename: str, b64: str) -> dict` — raises `ValueError` on bad b64 / caps
  - `register_folder(folder: str) -> dict` — raises `ValueError` if not an existing dir
  - `set_second_brain(path: str) -> dict` — creates, moves staging, writes `materials.md`; raises `ValueError` for repo-interior/invalid paths
  - `materials_sources() -> list[Path]` — staging dir (if it has files) + registered folders
  - `write_profile(text: str | None) -> Path` — writes `profile.md` (stub when `None`), stamps `completed_at`
- Module constants monkeypatchable in tests: `STATE_PATH`, `STAGING`, `MAX_FILE_BYTES = 20*2**20`, `MAX_FILES = 40`, `MAX_TOTAL_BYTES = 100*2**20`, `_REPO`.

- [ ] **Step 1: Write the failing tests**

```python
# studio/tests/test_onboarding.py
import base64
import json
import pytest
from pathlib import Path

from studio import onboarding as ob


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    monkeypatch.setattr(ob, "STATE_PATH", tmp_path / "cache" / "onboarding.json")
    monkeypatch.setattr(ob, "STAGING", tmp_path / "cache" / "onboarding-inbox")
    monkeypatch.setattr(ob, "_REPO", tmp_path / "repo")
    (tmp_path / "repo").mkdir()
    yield


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def test_state_roundtrip_and_empty_default():
    assert ob.load_state() == {}
    ob.save_state({"name": "Ada"})
    assert ob.load_state()["name"] == "Ada"
    assert ob.completed() is False


def test_set_name_validates():
    assert ob.set_name("  Ada  ")["name"] == "Ada"
    with pytest.raises(ValueError):
        ob.set_name("")
    with pytest.raises(ValueError):
        ob.set_name("x" * 61)


def test_stage_file_sanitizes_and_writes():
    ob.stage_file("../../evil.md", _b64(b"hello"))
    assert (ob.STAGING / "evil.md").read_bytes() == b"hello"   # basename only


def test_stage_file_caps():
    with pytest.raises(ValueError):
        ob.stage_file("big.bin", _b64(b"x" * (ob.MAX_FILE_BYTES + 1)))
    ob.save_state({"materials": {"copied": [f"f{i}" for i in range(ob.MAX_FILES)], "folders": []}})
    with pytest.raises(ValueError):
        ob.stage_file("one-too-many.md", _b64(b"x"))


def test_register_folder_must_exist(tmp_path):
    d = tmp_path / "essays"; d.mkdir()
    assert str(d) in ob.register_folder(str(d))["materials"]["folders"][0]
    with pytest.raises(ValueError):
        ob.register_folder(str(tmp_path / "nope"))


def test_second_brain_created_staged_moved(tmp_path):
    ob.set_name("Ada")
    ob.stage_file("cv.md", _b64(b"# cv"))
    sb = tmp_path / "second-brain"
    state = ob.set_second_brain(str(sb))
    assert Path(state["second_brain"]) == sb
    assert (sb / "inbox" / "onboarding" / "cv.md").read_bytes() == b"# cv"
    assert "cv.md" in (sb / "materials.md").read_text(encoding="utf-8")


def test_second_brain_rejects_repo_interior():
    with pytest.raises(ValueError):
        ob.set_second_brain(str(ob._REPO / "dist" / "sb"))


def test_materials_sources_staging_and_folders(tmp_path):
    d = tmp_path / "notes"; d.mkdir()
    ob.register_folder(str(d))
    ob.stage_file("cv.md", _b64(b"x"))
    src = ob.materials_sources()
    assert ob.STAGING in src and d in src


def test_materials_sources_folders_only_creates_staging(tmp_path):
    d = tmp_path / "notes"; d.mkdir()
    ob.register_folder(str(d))
    src = ob.materials_sources()          # staging empty -> not a source, but must exist
    assert ob.STAGING.exists() and ob.STAGING not in src and d in src


def test_write_profile_real_and_stub(tmp_path):
    ob.set_name("Ada")
    ob.set_second_brain(str(tmp_path / "sb"))
    p = ob.write_profile("# Ada\n\nBuilt engines.")
    assert "engines" in p.read_text(encoding="utf-8")
    assert ob.completed() is True
    p2 = ob.write_profile(None)           # stub fallback (distiller failed)
    text = p2.read_text(encoding="utf-8")
    assert "Ada" in text and "not yet distilled" in text


def test_write_profile_requires_second_brain():
    with pytest.raises(ValueError):
        ob.write_profile("text")
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/Scripts/python -m pytest studio/tests/test_onboarding.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'studio.onboarding'`.

- [ ] **Step 3: Implement**

```python
# studio/onboarding.py
"""Onboarding state + materials intake (onboarding-cards spec §5.1–5.3).

Everything is local: dropped files are staged under studio/.cache/ (gitignored) until the
participant chooses their second brain, then move into <sb>/inbox/onboarding/. The second
brain is the SAME directory compose later uses as the vault — one memory, two readers.
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
    if not fname:
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
        for f in sorted(STAGING.iterdir()):
            if f.is_file():
                (inbox / f.name).write_bytes(f.read_bytes())
                f.unlink()
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
```

- [ ] **Step 4: Run to verify pass**

Run: `.venv/Scripts/python -m pytest studio/tests/test_onboarding.py -v`
Expected: 11 passed.

- [ ] **Step 5: Commit**

```bash
git add studio/onboarding.py studio/tests/test_onboarding.py
git commit -m "feat(studio): onboarding state, staged intake, second-brain seeding"
```

---

### Task 5: `studio/distiller.py` — the profile pass

**Files:**
- Create: `studio/distiller.py`
- Test: `studio/tests/test_distiller.py`

**Interfaces:**
- Produces: `build_distill_argv(claude_bin: str, source_dirs: list[Path]) -> list[str]` and `async distill(source_dirs: list[Path], timeout: int = 180) -> str` (stdout markdown, stripped; raises `RuntimeError` on missing CLI / timeout / nonzero exit). Task 6 consumes `distill`; its failures are ALWAYS caught by the caller (non-fatal, spec §5.6).

- [ ] **Step 1: Write the failing tests**

```python
# studio/tests/test_distiller.py
import asyncio
import pytest
from pathlib import Path

from studio.distiller import build_distill_argv, distill


def test_argv_shape(tmp_path):
    a, b = tmp_path / "inbox", tmp_path / "notes"
    argv = build_distill_argv("claude", [a, b])
    assert argv[0] == "claude" and argv[1] == "-p"
    i = argv.index("--allowed-tools")
    assert argv[i + 1] == "Read"                      # Read only — no write surface
    assert argv.count("--add-dir") == 2
    assert str(a) in argv and str(b) in argv


def test_prompt_contents(tmp_path):
    argv = build_distill_argv("claude", [tmp_path / "inbox"])
    prompt = argv[2]
    assert str(tmp_path / "inbox") in prompt
    assert "sample" in prompt.lower()                 # large-folder sampling guidance (review I5)
    assert "profile" in prompt.lower()


@pytest.mark.asyncio
async def test_nonzero_exit_raises(tmp_path, monkeypatch):
    class _Proc:
        returncode = 3
        async def communicate(self):
            return b"", b"boom"
    async def fake_exec(*a, **k):
        return _Proc()
    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)
    monkeypatch.setattr("studio.distiller.resolve_claude", lambda: "claude")
    with pytest.raises(RuntimeError):
        await distill([tmp_path])


@pytest.mark.asyncio
async def test_timeout_raises(tmp_path, monkeypatch):
    class _Proc:
        returncode = None
        async def communicate(self):
            await asyncio.sleep(60)
        def kill(self):
            pass
        async def wait(self):
            return 0
    async def fake_exec(*a, **k):
        return _Proc()
    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)
    monkeypatch.setattr("studio.distiller.resolve_claude", lambda: "claude")
    with pytest.raises(RuntimeError):
        await distill([tmp_path], timeout=0.05)
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/Scripts/python -m pytest studio/tests/test_distiller.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'studio.distiller'`.

- [ ] **Step 3: Implement**

```python
# studio/distiller.py
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
```

- [ ] **Step 4: Run to verify pass**

Run: `.venv/Scripts/python -m pytest studio/tests/test_distiller.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add studio/distiller.py studio/tests/test_distiller.py
git commit -m "feat(studio): distiller — scoped Read-only claude pass over participant materials"
```

---

### Task 6: Server — onboarding endpoints, session injection, compose vault override

**Files:**
- Modify: `studio/server.py`
- Test: `studio/tests/test_server.py` (append)

**Interfaces:**
- Consumes: Task 3 `write_system_prompt(..., participant, onboarding)`; Task 4 `onboarding.*`; Task 5 `distiller.distill`.
- Produces: `GET /api/onboarding`; `POST /api/onboarding/name|materials|materials/done|second-brain`; `POST /api/onboarding/complete` (SSE). `new_session` workshop branch injects participant/onboarding. `/api/compose` uses the second brain as `vault_dir` once onboarding is complete. Frontend (Tasks 8–9) relies on these exact routes and event shapes.

- [ ] **Step 1: Write the failing tests** (append to `studio/tests/test_server.py`)

```python
# --- onboarding endpoints (onboarding-cards spec §5.2) ---
import base64 as _b64mod

def _iso_now():
    return "2026-07-02T00:00:00+00:00"

def _ob(monkeypatch, tmp_path, **state):
    from studio import onboarding as ob
    monkeypatch.setattr(ob, "STATE_PATH", tmp_path / "onboarding.json")
    monkeypatch.setattr(ob, "STAGING", tmp_path / "inbox")
    if state:
        ob.save_state(state)
    return ob

def test_onboarding_get_default(monkeypatch, tmp_path):
    _ob(monkeypatch, tmp_path)
    c = TestClient(server.app)
    r = c.get("/api/onboarding")
    assert r.status_code == 200 and r.json()["completed"] is False

def test_onboarding_name_and_file_and_folder(monkeypatch, tmp_path):
    ob = _ob(monkeypatch, tmp_path)
    c = TestClient(server.app)
    assert c.post("/api/onboarding/name", json={"name": "Ada"}).json()["ok"]
    b64 = _b64mod.b64encode(b"# cv").decode()
    assert c.post("/api/onboarding/materials", json={"file": {"name": "cv.md", "b64": b64}}).json()["ok"]
    d = tmp_path / "essays"; d.mkdir()
    assert c.post("/api/onboarding/materials", json={"folder": str(d)}).json()["ok"]
    assert c.post("/api/onboarding/materials", json={"folder": str(tmp_path / "no")}).json()["ok"] is False

def test_onboarding_complete_requires_second_brain(monkeypatch, tmp_path):
    _ob(monkeypatch, tmp_path, name="Ada")
    c = TestClient(server.app)
    with c.stream("POST", "/api/onboarding/complete") as r:
        body = "".join(r.iter_text())
    assert "second brain" in body and "preflight" in body

def test_onboarding_complete_inline_distill_and_profile(monkeypatch, tmp_path):
    ob = _ob(monkeypatch, tmp_path, name="Ada")
    c = TestClient(server.app)
    c.post("/api/onboarding/second-brain", json={"path": str(tmp_path / "sb")})
    async def fake_distill(sources, timeout=180):
        return "# Ada\n\nBuilt engines."
    monkeypatch.setattr(server._distiller, "distill", fake_distill)
    server._DISTILL_TASK = None                      # restart-lost-task path (review I1)
    with c.stream("POST", "/api/onboarding/complete") as r:
        body = "".join(r.iter_text())
    assert "engines" in body and '"type": "done"' in body.replace('","', '", "') or "done" in body
    assert (tmp_path / "sb" / "profile.md").exists()
    assert ob.completed() is True

def test_session_new_injects_participant(monkeypatch, tmp_path):
    sb = tmp_path / "sb"; sb.mkdir()
    (sb / "profile.md").write_text("# Ada\nBuilt engines.", encoding="utf-8")
    _ob(monkeypatch, tmp_path, name="Ada", second_brain=str(sb), completed_at=_iso_now(),
        materials={"copied": ["cv.md"], "folders": []})
    c = TestClient(server.app)
    r = c.post("/api/session/new")
    assert r.status_code == 200
    text = server._WORKSHOP_PROMPT.read_text(encoding="utf-8")
    assert "Ada" in text and "engines" in text and "studio event" not in text

def test_session_new_onboarding_contract_when_incomplete(monkeypatch, tmp_path):
    _ob(monkeypatch, tmp_path, name="Ada")
    c = TestClient(server.app)
    c.post("/api/session/new")
    text = server._WORKSHOP_PROMPT.read_text(encoding="utf-8")
    assert "studio event" in text

def test_session_new_degrades_when_sb_missing(monkeypatch, tmp_path):
    _ob(monkeypatch, tmp_path, name="Ada", second_brain=str(tmp_path / "gone"),
        completed_at=_iso_now())
    c = TestClient(server.app)
    r = c.post("/api/session/new")                   # must not 500 (review I4)
    assert r.status_code == 200
    text = server._WORKSHOP_PROMPT.read_text(encoding="utf-8")
    assert "The participant" not in text

def test_compose_uses_second_brain_vault(monkeypatch, tmp_path):
    sb = tmp_path / "sb"; sb.mkdir()
    (sb / "profile.md").write_text("x", encoding="utf-8")
    _ob(monkeypatch, tmp_path, name="Ada", second_brain=str(sb), completed_at=_iso_now())
    seen = {}
    async def fake_compose(picks, name, outdir, vault_dir):
        seen["vault"] = str(vault_dir)
        yield {"type": "done", "grade": "composed", "plugin_path": "x", "vault_path": str(vault_dir)}
    monkeypatch.setattr(server._composer, "compose", fake_compose)
    c = TestClient(server.app)
    with c.stream("POST", "/api/compose", json={"picks": ["crm"], "name": "my cos"}) as r:
        "".join(r.iter_text())
    assert seen["vault"] == str(sb)
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/Scripts/python -m pytest studio/tests/test_server.py -v`
Expected: new tests FAIL (404s / missing attrs); existing pass.

- [ ] **Step 3: Implement.** In `studio/server.py`:

Add imports + module state below the existing imports:

```python
from studio import distiller as _distiller
from studio import onboarding as _onboarding
```

```python
_DISTILL_TASK: asyncio.Task | None = None    # add `import asyncio` at the top
```

Add the endpoints (below the catalog endpoint):

```python
def _ok(state: dict) -> JSONResponse:
    return JSONResponse({"ok": True, **state, "completed": bool(state.get("completed_at"))})


def _bad(e: Exception) -> JSONResponse:
    return JSONResponse({"ok": False, "message": str(e)}, status_code=400)


@app.get("/api/onboarding")
async def onboarding_state() -> JSONResponse:
    return _ok(_onboarding.load_state())


@app.post("/api/onboarding/name")
async def onboarding_name(req: Request) -> JSONResponse:
    body = await req.json()
    try:
        return _ok(_onboarding.set_name(body.get("name", "")))
    except ValueError as e:
        return _bad(e)


@app.post("/api/onboarding/materials")
async def onboarding_materials(req: Request) -> JSONResponse:
    body = await req.json()
    try:
        if body.get("folder"):
            return _ok(_onboarding.register_folder(body["folder"]))
        f = body.get("file") or {}
        return _ok(_onboarding.stage_file(f.get("name", ""), f.get("b64", "")))
    except ValueError as e:
        return _bad(e)


@app.post("/api/onboarding/materials/done")
async def onboarding_materials_done() -> JSONResponse:
    global _DISTILL_TASK
    sources = _onboarding.materials_sources()
    if sources and _DISTILL_TASK is None:
        _DISTILL_TASK = asyncio.create_task(_distiller.distill(sources))
    mats = _onboarding.load_state().get("materials", {})
    return JSONResponse({"ok": True, "copied": mats.get("copied", []),
                         "folders": mats.get("folders", [])})


@app.post("/api/onboarding/second-brain")
async def onboarding_second_brain(req: Request) -> JSONResponse:
    body = await req.json()
    try:
        return _ok(_onboarding.set_second_brain(body.get("path", "")))
    except ValueError as e:
        return _bad(e)


@app.post("/api/onboarding/complete")
async def onboarding_complete() -> StreamingResponse:
    async def stream():
        global _DISTILL_TASK
        state = _onboarding.load_state()
        if not state.get("second_brain"):
            yield _sse_preflight_error("choose your second brain location first")
            return
        task = _DISTILL_TASK
        if task is None:
            # Studio restarted between materials/done and here (review I1): start inline.
            sources = _onboarding.materials_sources()
            task = asyncio.create_task(_distiller.distill(sources)) if sources else None
        yield _sse({"type": "stage", "name": "distill", "status": "running"})
        text = None
        if task is not None:
            try:
                text = await task
            except Exception:
                text = None                 # non-fatal (spec §5.6) — stub profile below
        _DISTILL_TASK = None
        yield _sse({"type": "stage", "name": "distill", "status": "ok" if text else "fail"})
        profile_path = _onboarding.write_profile(text)
        yield _sse({"type": "profile",
                    "text": profile_path.read_text(encoding="utf-8"),
                    "distilled": bool(text)})
        yield _sse({"type": "done"})

    return StreamingResponse(stream(), media_type="text/event-stream")
```

Replace the workshop branch of `new_session` (keep the architect branch as-is):

```python
    else:
        state = _onboarding.load_state()
        participant, onboarding_mode = None, False
        sb = Path(state["second_brain"]) if state.get("second_brain") else None
        if state.get("completed_at") and sb is not None and (sb / "profile.md").exists():
            mats = state.get("materials", {})
            participant = {
                "name": state.get("name", ""),
                "second_brain": str(sb),
                "profile_text": (sb / "profile.md").read_text(encoding="utf-8"),
                "materials_index": ", ".join(mats.get("copied", []) + mats.get("folders", [])),
            }
        elif not state.get("completed_at"):
            onboarding_mode = True
        # completed but second brain missing -> neither section (degrade, review I4)
        write_system_prompt(_WORKSHOP_PROMPT, mode="workshop",
                            participant=participant, onboarding=onboarding_mode)
        SESSIONS[sid] = ChatSession(session_id=sid, system_prompt_path=_WORKSHOP_PROMPT,
                                    catalog_ids=_catalog_ids())
```

In `compose_endpoint`, replace the vault line:

```python
        state = _onboarding.load_state()
        if state.get("completed_at") and state.get("second_brain"):
            vault = Path(state["second_brain"])       # spec §5.3: the second brain IS the vault
        else:
            vault = _composer._REPO / "dist" / f"{slug}-vault"
```

- [ ] **Step 4: Run to verify pass, then the whole backend suite**

Run: `.venv/Scripts/python -m pytest studio/tests/test_server.py -v` → all pass.
Run: `.venv/Scripts/python -m pytest studio/tests -q -m "not integration"` → all pass.

- [ ] **Step 5: Commit**

```bash
git add studio/server.py studio/tests/test_server.py
git commit -m "feat(studio): onboarding endpoints, participant-aware sessions, second-brain vault"
```

---

### Task 7: `cards.js` + `cards.css` — the guided card framework

**Files:**
- Create: `studio/static/cards.js`, `studio/static/cards.css`

**Interfaces:**
- Produces: `window.cards = { mount(el), show(card, onAnswer), queue(cards), fold(cardId, receipt), morph(html), baton(holder), onBaton(fn) }`. Card/answer shapes exactly per spec §3.1. Tasks 8–9 consume all of these. No pytest (no JS runner) — exercised by Task 8/9 manual checklists.

- [ ] **Step 1: Write `studio/static/cards.js`**

```js
// Guided card framework (onboarding-cards spec §3). One primitive, four producers:
// onboarding steps, the architect's asks, per-skill personalize (r1-B), connect keys.
// Motion vocabulary: rise / fold / baton / morph — all collapse under reduced motion.
(function () {
  const esc = (s) => String(s == null ? '' : s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

  let root = null;               // mount element (the right-panel rail)
  let batonFns = [];             // app.js registers composer sleep/wake here

  function mount(el) { root = el; root.classList.add('cards-rail'); }

  function baton(holder) { batonFns.forEach((fn) => fn(holder)); }
  function onBaton(fn) { batonFns.push(fn); }

  function bodyHtml(card) {
    if (card.kind === 'files') {
      return `<div class="card-drop" tabindex="0">⤓ drop files here
          <small>locations registered locally — nothing leaves your machine</small></div>
        <input type="file" class="card-file-input" multiple hidden>
        <div class="card-chips"></div>
        <label class="card-field">or link a folder by path
          <input type="text" class="card-folder" placeholder="e.g. ~/notes"></label>
        <div class="card-foot">
          ${card.skippable === false ? '' : '<button type="button" class="card-skip">skip for now</button>'}
          <button type="button" class="card-go">That's everything →</button>
        </div>`;
    }
    if (card.kind === 'path') {
      return `<label class="card-field">${esc(card.why || '')}
          <input type="text" class="card-path" value="${esc(card.default || '')}"></label>
        <div class="card-foot">
          ${card.skippable === false ? '' : '<button type="button" class="card-skip">skip for now</button>'}
          <button type="button" class="card-go">This is home →</button>
        </div>`;
    }
    // kind === 'question' (the visual AskUserQuestion). `keys` is reserved for the
    // connect slice — same shell, steps+paste+Test body (spec §3.1).
    const opts = (card.options || []).map((o) => `
      <div class="card-choice" data-oid="${esc(o.id)}" role="button" tabindex="0">
        <span class="card-key">${esc(o.id.toUpperCase())}</span>
        <span><b>${esc(o.label)}</b>${o.why ? `<i>${esc(o.why)}</i>` : ''}</span>
      </div>`).join('');
    return `${opts}
      <div class="card-orline">or in your own words</div>
      <textarea class="card-own" rows="2" placeholder="type your own answer…"></textarea>
      <div class="card-foot">
        ${card.skippable === false ? '' : '<button type="button" class="card-skip">skip</button>'}
        <button type="button" class="card-go" disabled>Answer →</button>
      </div>`;
  }

  function show(card, onAnswer) {
    if (!root) return;
    const el = document.createElement('div');
    el.className = 'card hot rise';
    el.dataset.cardId = card.id;
    el.innerHTML = `
      <div class="card-head"><span class="card-eyebrow">${esc(card.eyebrow || '')}</span>
        ${card.progress ? `<span class="card-prog">${card.progress.i} OF ${card.progress.n}</span>` : ''}</div>
      <h3>${esc(card.title || '')}</h3>
      ${card.kind === 'question' && card.why ? `<p class="card-why">${esc(card.why)}</p>` : ''}
      ${bodyHtml(card)}`;
    root.prepend(el);
    baton('card');

    const picked = new Set();
    const go = el.querySelector('.card-go');
    const own = el.querySelector('.card-own');
    const answer = (a) => { onAnswer({ card_id: card.id, choices: [...picked],
      custom: own && own.value.trim() ? own.value.trim() : null,
      skipped: false, payload: null, ...a }); };

    el.querySelectorAll('.card-choice').forEach((c) => {
      const pick = () => {
        const oid = c.dataset.oid;
        if (!card.multi) { picked.clear(); el.querySelectorAll('.card-choice').forEach((x) => x.classList.remove('picked')); }
        if (picked.has(oid)) { picked.delete(oid); c.classList.remove('picked'); }
        else { picked.add(oid); c.classList.add('picked'); }
        if (go) go.disabled = picked.size === 0 && !(own && own.value.trim());
      };
      c.addEventListener('click', pick);
      c.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); pick(); } });
    });
    if (own && go) own.addEventListener('input', () => { go.disabled = picked.size === 0 && !own.value.trim(); });
    if (go) go.addEventListener('click', () => answer({}));
    const skip = el.querySelector('.card-skip');
    if (skip) skip.addEventListener('click', () => answer({ skipped: true, choices: [], custom: null }));
    return el;
  }

  function queue(cardsList) {
    if (!root) return;
    (cardsList || []).forEach((c) => {
      const el = document.createElement('div');
      el.className = 'card ghost';
      el.innerHTML = `<div class="card-head"><span class="card-eyebrow">${esc(c.eyebrow || '')}</span></div>`;
      root.appendChild(el);
    });
  }

  function fold(cardId, receipt) {
    if (!root) return;
    const el = root.querySelector(`.card[data-card-id="${CSS.escape(cardId)}"]`);
    if (!el) return;
    const text = String(receipt || '✓').slice(0, 60);  // length-capped receipt (review R3)
    el.classList.remove('hot');
    el.classList.add('folded');
    el.innerHTML = `<div class="card-receipt">${esc(text)}</div>`;
  }

  function morph(html) {
    if (!root) return;
    root.classList.add('morphing');
    setTimeout(() => { root.innerHTML = html; root.classList.remove('morphing', 'cards-rail'); }, 220);
  }

  window.cards = { mount, show, queue, fold, morph, baton, onBaton };
})();
```

- [ ] **Step 2: Write `studio/static/cards.css`** (SapphireOS tokens with fallbacks so a pre-reskin cut still renders)

```css
/* Guided card framework — spec §3.3: rise / fold / baton / morph. */
.cards-rail { display: flex; flex-direction: column; gap: 10px; }
.card {
  background: var(--canvas, #fff); border: 1px solid var(--rule, rgba(20,26,33,.1));
  border-radius: var(--r-card, 14px); box-shadow: var(--sh-sm, 0 1px 2px rgba(20,26,33,.05));
  padding: 14px;
}
.card.hot { border: 1.5px solid var(--sapphire, #306FA8); box-shadow: var(--sh-md, 0 2px 6px rgba(20,26,33,.09)); }
.card.ghost { opacity: .38; }
.card.rise { animation: card-rise .3s cubic-bezier(.2,.7,.2,1) both; }
@keyframes card-rise { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: none; } }
.card.folded { opacity: .6; padding: 8px 14px; }
.card-receipt { font-family: var(--mono, monospace); font-size: 11px; color: var(--ink-3, #6B7681); }
.card-head { display: flex; justify-content: space-between; align-items: baseline; }
.card-eyebrow, .card-prog {
  font-family: var(--mono, monospace); font-size: 10px; font-weight: 500;
  text-transform: uppercase; letter-spacing: .13em;
}
.card-eyebrow { color: var(--sapphire, #306FA8); }
.card-prog { color: var(--ink-4, #9AA4AD); }
.card h3 { font-family: var(--display, sans-serif); font-size: 16px; margin: 4px 0 2px; color: var(--ink, #141A21); }
.card-why { font-size: 13px; color: var(--ink-3, #6B7681); margin: 0 0 8px; }
.card-choice {
  display: flex; gap: 10px; align-items: flex-start; cursor: pointer;
  border: 1px solid var(--rule, rgba(20,26,33,.1)); border-radius: 10px;
  padding: 8px 10px; margin-top: 7px;
  transition: border-color .15s ease, background .15s ease, transform .18s ease;
}
.card-choice:hover { border-color: var(--sapphire, #306FA8); transform: translateY(-1px); }
.card-choice.picked { border: 1.5px solid var(--sapphire, #306FA8); background: var(--tint, #EEF4FA); }
.card-choice .card-key {
  font-family: var(--mono, monospace); font-size: 10px; color: var(--sapphire, #306FA8);
  border: 1px solid var(--tint-2, #DBE8F3); background: var(--tint, #EEF4FA);
  border-radius: 6px; padding: 1px 7px; flex: none; margin-top: 1px;
}
.card-choice b { display: block; font-size: 13.5px; color: var(--ink, #141A21); }
.card-choice i { font-style: normal; font-size: 12px; color: var(--ink-3, #6B7681); }
.card-orline {
  display: flex; align-items: center; gap: 10px; margin: 10px 0 6px;
  font-family: var(--mono, monospace); font-size: 9px; letter-spacing: .14em;
  text-transform: uppercase; color: var(--ink-4, #9AA4AD);
}
.card-orline::before, .card-orline::after { content: ""; flex: 1; height: 1px; background: var(--rule, rgba(20,26,33,.1)); }
.card-own, .card-field input, .card-folder, .card-path {
  width: 100%; border: 1px solid var(--rule-strong, rgba(20,26,33,.2)); border-radius: 8px;
  padding: 7px 9px; font-family: var(--body, sans-serif); font-size: 13px; color: var(--ink, #141A21);
}
.card-field { display: block; font-size: 12px; color: var(--ink-3, #6B7681); margin-top: 8px; }
.card-drop {
  border: 1.5px dashed var(--sapphire, #306FA8); background: var(--tint, #EEF4FA);
  border-radius: 10px; padding: 16px 10px; text-align: center;
  color: var(--sapphire, #306FA8); font-size: 13px; cursor: pointer;
}
.card-drop.over { background: var(--tint-2, #DBE8F3); }
.card-drop small { display: block; color: var(--ink-3, #6B7681); font-size: 11px; margin-top: 4px; }
.card-chips .chip {
  display: inline-block; font-family: var(--mono, monospace); font-size: 10.5px;
  background: rgba(46,125,91,.1); border: 1px solid rgba(46,125,91,.25); color: var(--ok, #2E7D5B);
  border-radius: 999px; padding: 2px 8px; margin: 6px 4px 0 0;
}
.card-chips .chip.pending { background: var(--tint, #EEF4FA); border-color: var(--tint-2, #DBE8F3); color: var(--sapphire, #306FA8); }
.card-foot { display: flex; justify-content: flex-end; gap: 10px; margin-top: 10px; align-items: center; }
.card-go {
  background: var(--sapphire, #306FA8); color: #fff; border: none;
  border-radius: var(--r-btn, 10px); padding: 7px 14px; font-weight: 600; cursor: pointer;
}
.card-go:disabled { background: var(--tint-2, #DBE8F3); color: var(--ink-4, #9AA4AD); }
.card-skip { background: none; border: none; color: var(--ink-4, #9AA4AD); font-size: 12px; cursor: pointer; }
.cards-rail.morphing { opacity: 0; transition: opacity .2s ease; }
#composer.asleep textarea, #composer.asleep button { opacity: .5; pointer-events: none; }
#composer.asleep { position: relative; }
#composer.asleep::after {
  content: "the architect will ask for you in a moment…";
  position: absolute; inset: 0; display: flex; align-items: center; justify-content: center;
  font-size: 12.5px; color: var(--ink-4, #9AA4AD); font-style: italic;
}
@media (prefers-reduced-motion: reduce) {
  .card.rise { animation: none; }
  .card-choice:hover { transform: none; }
  .cards-rail.morphing { transition: none; }
}
```

- [ ] **Step 3: Commit**

```bash
git add studio/static/cards.js studio/static/cards.css
git commit -m "feat(studio): guided card framework — rise/fold/baton/morph, question/files/path kinds"
```

---

### Task 8: `app.js` wiring — send queue, suppression, ask producer, baton

**Files:**
- Modify: `studio/static/app.js`, `studio/static/index.html`

**Interfaces:**
- Consumes: `window.cards` (Task 7); `ev.studio.ask` (Tasks 1/6); post-journey `send()`/`MODE`/`SEED`/`renderAgentPanel`.
- Produces: `queueSend(message) -> Promise` (ALL sends go through it — spec §5.4.8); `window.startWorkshopSession(seed)` (Task 9 calls it); `HIDDEN_MSG` regex suppression; `cards.onBaton` composer hook; ask-card rendering. `window.onboardingActive` flag gates panel repaints (review I7).

- [ ] **Step 1: index.html — script/style tags.** Add BEFORE the `app.js` script tag:

```html
<link rel="stylesheet" href="/static/cards.css">
<script src="/static/cards.js"></script>
```

- [ ] **Step 2: app.js — send queue + suppression.** Below the `SEED` constant add:

```js
// ALL sends — participant, seed, [card] answers, [studio event]s — go through one
// queue so a programmatic send can never overlap an in-flight turn (spec §5.4.8).
let sendChain = Promise.resolve();
function queueSend(message) {
  sendChain = sendChain.then(() => send(message)).catch(() => {});
  return sendChain;
}
window.queueSend = queueSend;

// Bracketed messages are machine channel — never shown as user bubbles (spec §4.2).
const HIDDEN_MSG = /^\[(card|studio event)\]/;
window.onboardingActive = false;   // Task 9 flips this; gates the agent-panel repaints
```

In `send()`, change the user-bubble line to:

```js
  if (message !== SEED && !HIDDEN_MSG.test(message)) addBubble('user', message);
```

Change the composer submit handler and the seed call in `start()` to use `queueSend(v)` / `queueSend(SEED)` instead of `send(...)`.

- [ ] **Step 3: app.js — baton hook + ask producer.** After the `MODE` block add:

```js
if (window.cards) {
  window.cards.onBaton((holder) => {
    $('#composer').classList.toggle('asleep', holder === 'card');
  });
}

// The architect's ask (spec §4.2): render the card, send the answer as a [card] message.
function renderAskCard(ask) {
  if (!window.cards || document.querySelector(`.card[data-card-id="${CSS.escape(ask.id)}"]`)) return;
  window.cards.mount($('#blueprint'));
  window.cards.show({ ...ask, producer: 'ask', kind: 'question', eyebrow: 'the architect asks' },
    (a) => {
      let receipt, reply;
      if (a.skipped) { receipt = 'skipped'; reply = `[card] ${ask.title} → skipped`; }
      else {
        const labels = a.choices.map((id) => (ask.options.find((o) => o.id === id) || {}).label).filter(Boolean);
        const parts = [...labels, ...(a.custom ? [`(custom) ${a.custom}`] : [])];
        receipt = parts.join(' + ') || '—'; reply = `[card] ${ask.title} → ${parts.join('; ')}`;
      }
      window.cards.fold(ask.id, `${receipt} ✓`);
      window.cards.baton('composer');
      queueSend(reply);
    });
}
```

In the SSE `done` branch (post-journey shape), extend to:

```js
      else if (ev.type === 'done') {
        if (ev.spec) renderBlueprint(ev.spec);
        if (ev.studio && typeof window.shelfSync === 'function') window.shelfSync(ev.studio);
        if (MODE === 'workshop' && !window.onboardingActive) renderAgentPanel(ev.studio);
        if (ev.studio && ev.studio.ask) renderAskCard(ev.studio.ask);
      }
```

And gate the empty-state paint in `start()`:

```js
  if (MODE === 'workshop' && !window.onboardingActive) renderAgentPanel(null);
```

- [ ] **Step 4: app.js — expose session start for the walk.** Extract from `start()`:

```js
// Used by onboard.js after the reveal (Task 9): create the session, seed the walk.
window.startWorkshopSession = async function (seed) {
  const r = await fetch('/api/session/new', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mode: MODE }),
  });
  sessionId = (await r.json()).session_id;
  setStatus('ready');
  return queueSend(seed || SEED);
};
```

and have `start()` call `window.startWorkshopSession(SEED)` on its normal path.

- [ ] **Step 5: Manual verification** (real `claude`; onboarding not yet wired, so mark state complete-less and test the ask channel in a plain workshop chat)

Run: `.venv/Scripts/python -m studio`, then:
1. Interview normally; when the agent offers choices, a sapphire ask card rises in the right rail; the composer sleeps (dashed overlay text).
2. Click a choice → card folds to a receipt, composer wakes, the agent's next turn reflects the click. No `[card]` text ever appears as a user bubble.
3. Type in the open lane instead → custom text reaches the agent verbatim.
4. `?mode=architect` unaffected.

- [ ] **Step 6: Backend suite still green**

Run: `.venv/Scripts/python -m pytest studio/tests -q -m "not integration"` → all pass.

- [ ] **Step 7: Commit**

```bash
git add studio/static/app.js studio/static/index.html
git commit -m "feat(studio): send queue, ask cards, composer baton — C1 slice complete"
```

---

### Task 9: `onboard.js` — the guided walk (overlay, steps, events, morph)

**Files:**
- Create: `studio/static/onboard.js`
- Modify: `studio/static/index.html` (overlay root + script tag), `studio/static/styles.css` (overlay styles appended)

**Interfaces:**
- Consumes: every `/api/onboarding/*` route (Task 6), `window.cards` (Task 7), `window.queueSend` / `window.startWorkshopSession` / `window.onboardingActive` (Task 8), `renderAgentPanel` (journey).
- Produces: `window.onboardWalk.begin(state)`; `start()` in app.js gains the onboarding gate below.

- [ ] **Step 1: index.html.** Add inside `<body>` (first child) and a script tag after `cards.js`:

```html
<div id="onboard-overlay" hidden>
  <div id="ob-name" class="ob-screen">
    <span class="brand-eyebrow">QubitStudio · first launch</span>
    <h1>Welcome.</h1>
    <p>What should your chief of staff call you?</p>
    <form id="ob-name-form"><input id="ob-name-input" type="text" maxlength="60"
      placeholder="your name" autocomplete="off"><button type="submit">→</button></form>
  </div>
  <div id="ob-welcome" class="ob-screen" hidden>
    <h1 id="ob-welcome-title"></h1>
    <p class="ob-sub">let's get you onboarded — today you build your own chief of staff</p>
  </div>
</div>
```

```html
<script src="/static/onboard.js"></script>
```

- [ ] **Step 2: app.js gate.** At the top of `start()`:

```js
  if (MODE === 'workshop') {
    const ob = await (await fetch('/api/onboarding')).json();
    const force = new URLSearchParams(location.search).get('onboard') === '1';
    if ((force || !ob.completed) && window.onboardWalk) {
      window.onboardWalk.begin(ob);
      return;                          // the walk calls startWorkshopSession itself
    }
  }
```

- [ ] **Step 3: Write `studio/static/onboard.js`**

```js
// The onboarding walk (onboarding-cards spec §5.4): fade-in welcome, then the live agent
// narrates on the left while the right rail runs files -> path cards. Every visible
// bubble is real model output; the UI only sends [studio event] messages (suppressed).
(function () {
  const $ = (s) => document.querySelector(s);
  const REDUCED = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  async function post(url, body) {
    const r = await fetch(url, { method: 'POST',
      headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body || {}) });
    return r.json();
  }

  function readFileB64(file) {
    return new Promise((res, rej) => {
      const fr = new FileReader();
      fr.onload = () => res(String(fr.result).split(',')[1] || '');
      fr.onerror = rej;
      fr.readAsDataURL(file);
    });
  }

  function begin(state) {
    window.onboardingActive = true;
    $('#onboard-overlay').hidden = false;
    const nameInput = $('#ob-name-input');
    if (state && state.name) nameInput.value = state.name;
    nameInput.focus();
    $('#ob-name-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      const name = nameInput.value.trim();
      if (!name) return;
      const out = await post('/api/onboarding/name', { name });
      if (!out.ok) { alert(out.message); return; }
      welcome(name);
    }, { once: true });
  }

  function welcome(name) {
    $('#ob-name').hidden = true;
    const w = $('#ob-welcome');
    $('#ob-welcome-title').textContent = `Welcome, ${name}.`;   // textContent — no injection
    w.hidden = false;
    setTimeout(reveal, REDUCED ? 0 : 2200);
  }

  async function reveal() {
    const ov = $('#onboard-overlay');
    ov.classList.add('ob-slide-up');                            // one continuous motion
    setTimeout(() => { ov.hidden = true; }, REDUCED ? 0 : 650);
    window.cards.mount($('#blueprint'));
    window.cards.queue([{ eyebrow: 'mind-palace' }]);           // path step waits ghosted
    await window.startWorkshopSession('Begin onboarding.');     // agent greets by name
    filesStep();
  }

  function filesStep() {
    const registered = [];
    const el = window.cards.show({
      id: 'ob-files', producer: 'onboarding', kind: 'files',
      eyebrow: 'onboarding · know you', progress: { i: 1, n: 2 },
      title: 'Help me get to know you',
    }, async (a) => {
      if (a.skipped) await window.queueSend('[studio event] participant skipped sharing materials');
      else await post('/api/onboarding/materials/done', {});    // distiller starts now
      window.cards.fold('ob-files', registered.length ? `${registered.length} shared ✓` : 'skipped');
      pathStep();
    });

    const drop = el.querySelector('.card-drop');
    const fileInput = el.querySelector('.card-file-input');
    const chips = el.querySelector('.card-chips');
    const addChip = (label, ok) => {
      const c = document.createElement('span');
      c.className = 'chip' + (ok ? '' : ' pending');
      c.textContent = (ok ? '✓ ' : '') + label;
      chips.appendChild(c);
    };
    async function takeFiles(files) {
      const names = [];
      for (const f of files) {
        addChip(f.name, false);
        const out = await post('/api/onboarding/materials',
          { file: { name: f.name, b64: await readFileB64(f) } });
        chips.lastChild.remove();
        addChip(f.name, !!out.ok);
        if (out.ok) { names.push(f.name); registered.push(f.name); }
        else alert(out.message);
      }
      if (names.length) window.queueSend(`[studio event] materials registered: ${names.join(', ')}`);
    }
    drop.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', (e) => { takeFiles([...e.target.files]); e.target.value = ''; });
    drop.addEventListener('dragover', (e) => { e.preventDefault(); drop.classList.add('over'); });
    drop.addEventListener('dragleave', () => drop.classList.remove('over'));
    drop.addEventListener('drop', (e) => {
      e.preventDefault(); drop.classList.remove('over');
      takeFiles([...e.dataTransfer.files]);
    });
    const folder = el.querySelector('.card-folder');
    folder.addEventListener('keydown', async (e) => {
      if (e.key !== 'Enter') return;
      e.preventDefault();
      const out = await post('/api/onboarding/materials', { folder: folder.value.trim() });
      if (!out.ok) { alert(out.message); return; }
      addChip(folder.value.trim(), true); registered.push(folder.value.trim());
      window.queueSend(`[studio event] linked folder: ${folder.value.trim()}`);
      folder.value = '';
    });
  }

  function pathStep() {
    window.cards.show({
      id: 'ob-path', producer: 'onboarding', kind: 'path',
      eyebrow: 'onboarding · mind-palace', progress: { i: 2, n: 2 },
      title: 'Where should its memory live?',
      why: 'One folder you own, plain files — everything it learns about you lives here.',
      default: '~/second-brain',
    }, async (a) => {
      if (a.skipped) {
        // Skip-all path (review I6): default location, stub profile — never stall.
        await post('/api/onboarding/second-brain', { path: '~/second-brain' });
        await window.queueSend('[studio event] participant skipped choosing — defaulted to ~/second-brain');
      } else {
        const path = document.querySelector('.card[data-card-id="ob-path"] .card-path').value.trim();
        const out = await post('/api/onboarding/second-brain', { path: path || '~/second-brain' });
        if (!out.ok) { alert(out.message); return pathStep(); }
      }
      window.cards.fold('ob-path', 'home chosen ✓');
      completeStep();
    });
  }

  async function completeStep() {
    // Stream the distill; then hand the profile to the live agent as an event.
    const r = await fetch('/api/onboarding/complete', { method: 'POST' });
    const reader = r.body.getReader(); const dec = new TextDecoder();
    let buf = '', profile = '', distilled = false;
    while (true) {
      const { value, done } = await reader.read(); if (done) break;
      buf += dec.decode(value, { stream: true });
      let i; while ((i = buf.indexOf('\n\n')) >= 0) {
        const line = buf.slice(0, i).replace(/^data: /, ''); buf = buf.slice(i + 2);
        if (!line) continue;
        const ev = JSON.parse(line);
        if (ev.type === 'profile') { profile = ev.text; distilled = !!ev.distilled; }
        if (ev.type === 'error') { alert(ev.message); return; }
      }
    }
    const state = await (await fetch('/api/onboarding')).json();
    const note = distilled ? 'Distilled profile:' : 'Materials registered but not yet distilled. Stub profile:';
    await window.queueSend(`[studio event] second brain created at ${state.second_brain}. ${note}\n${profile}`);
    window.onboardingActive = false;
    window.cards.morph('');                       // clear the rail…
    if (typeof renderAgentPanel === 'function') renderAgentPanel(null);   // …hand back the panel
    window.cards.baton('composer');               // the interview is live
  }

  window.onboardWalk = { begin };
})();
```

- [ ] **Step 4: Overlay styles** — append to `studio/static/styles.css`:

```css
/* ── Onboarding overlay (onboarding-cards spec §5.4/§5.7) ── */
#onboard-overlay {
  position: fixed; inset: 0; z-index: 50; background: var(--canvas, #fff);
  display: flex; align-items: center; justify-content: center;
  transition: transform .6s cubic-bezier(.2,.7,.2,1);
}
#onboard-overlay.ob-slide-up { transform: translateY(-100%); }
.ob-screen { text-align: center; max-width: 560px; padding: 24px; }
.ob-screen h1 {
  font-family: var(--display, sans-serif); font-size: 56px; font-weight: 640;
  letter-spacing: -.02em; color: var(--ink, #141A21); margin: 14px 0 8px;
  animation: ob-rise .9s cubic-bezier(.2,.7,.2,1) both;
}
.ob-screen p, .ob-sub {
  font-family: var(--wordmark, serif); font-style: italic; font-size: 19px;
  color: var(--ink-3, #6B7681); animation: ob-rise .9s cubic-bezier(.2,.7,.2,1) .35s both;
}
@keyframes ob-rise { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: none; } }
#ob-name-form { margin-top: 22px; display: flex; gap: 10px; justify-content: center; }
#ob-name-input {
  font-size: 17px; padding: 10px 14px; width: 280px;
  border: 1px solid var(--rule-strong, rgba(20,26,33,.2)); border-radius: 10px;
}
#ob-name-form button {
  background: var(--sapphire, #306FA8); color: #fff; border: none;
  border-radius: 10px; padding: 0 18px; font-size: 17px; cursor: pointer;
}
@media (prefers-reduced-motion: reduce) {
  #onboard-overlay { transition: none; }
  .ob-screen h1, .ob-screen p, .ob-sub { animation: none; }
}
```

- [ ] **Step 5: Manual verification — the full walk** (real `claude`)

Delete `studio/.cache/onboarding.json`, run `.venv/Scripts/python -m studio`:
1. Name screen → type a name → "Welcome, {name}." rises → overlay slides up to reveal the studio.
2. The agent greets **by name** and points right; the files card is hot, the mind-palace card ghosted below; the composer shows the asleep overlay.
3. Drop 2 files + link a folder → chips turn green; the agent acknowledges each registration in its own words.
4. "That's everything →" → agent asks about the mind-palace while the distiller runs; card 2 goes hot.
5. Confirm the path → distill stage streams → the agent reacts **naming real details from the materials** → cards morph away, Your-agent panel returns, composer wakes, interview begins in the same conversation.
6. Skip path: reload with `?onboard=1`, skip both cards → onboarding completes with the stub profile; agent adapts gracefully.
7. Relaunch the studio (state complete): no wizard; the agent's greeting shows it knows you.
8. DevTools reduced-motion: overlay/cards cut instantly, no animation.
9. `?mode=architect`: untouched.

- [ ] **Step 6: Backend suite still green**

Run: `.venv/Scripts/python -m pytest studio/tests -q -m "not integration"` → all pass.

- [ ] **Step 7: Commit**

```bash
git add studio/static/onboard.js studio/static/index.html studio/static/styles.css studio/static/app.js
git commit -m "feat(studio): the onboarding walk — fade-in, agent-guided intake, second brain, morph"
```

---

### Task 10: Integration smoke + PDF probe + QA close-out

**Files:**
- Test: `studio/tests/test_smoke_integration.py` (append)
- Create: `studio/tests/fixtures/onboarding/cv.md`, `studio/tests/fixtures/onboarding/headshot.png` (tiny fictional fixtures — the png is a 1×1 pixel)

**Interfaces:** consumes `distiller.distill` (Task 5) end-to-end with the real CLI.

- [ ] **Step 1: Create the fixtures**

`studio/tests/fixtures/onboarding/cv.md`:

```markdown
# Ada Lovelace — CV

- Analyst, Babbage & Co (1838–1843)
- Wrote the first published algorithm
```

`headshot.png`: any 1×1 PNG (e.g. `python -c "import base64,pathlib; pathlib.Path('studio/tests/fixtures/onboarding/headshot.png').write_bytes(base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=='))"`).

- [ ] **Step 2: Add the integration smoke** (append to `studio/tests/test_smoke_integration.py`)

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_distill_returns_profile():
    # The distiller must produce non-empty markdown from real mixed materials.
    from studio.distiller import distill
    fixtures = Path(__file__).parent / "fixtures" / "onboarding"
    out = await distill([fixtures])
    assert out and "Lovelace" in out or "Ada" in out
```

- [ ] **Step 3: PDF verify-first probe (review I8 — capture the artifact, not an assumption).** Save any real one-page PDF (e.g. print this plan to PDF) into a scratch dir and run:

```bash
claude -p "Read every file under <scratch dir> and summarize each in one line, naming each file." --allowed-tools Read --add-dir "<scratch dir>"
```

If the PDF is read: no change. If NOT: edit the files-card copy in `onboard.js` (`card-drop` small text) to read "CVs work best as text or markdown; LinkedIn as screenshots", and note the outcome in the commit message.

- [ ] **Step 4: Full suite including integration (needs live `claude`)**

Run: `.venv/Scripts/python -m pytest studio/tests -q`
Expected: all pass.

- [ ] **Step 5: QA close-out (repo pipeline)**

1. `.venv/Scripts/python -m studio --doctor` — preflight green (no launcher change expected).
2. Placeholder-contract scan: `git diff main --stat` touches nothing under `chief-of-staff/` or `agent-architect/`; `git diff main | grep -iE "lin_api|xoxb|AIza|@gmail"` → empty.
3. `/code-review` on the branch; address every Critical + Improvement; re-run the suite.

- [ ] **Step 6: Commit**

```bash
git add studio/tests/test_smoke_integration.py studio/tests/fixtures/onboarding
git commit -m "test(studio): real distill smoke over fixture materials + QA close-out"
```

---

## Self-review notes

- **Spec coverage:** §3 (framework) → Task 7; §4.1 → Task 1; §4.2 → Task 8; §4.3 → Task 3; §5.1 → Task 4; §5.2 → Tasks 4+6; §5.3 → Tasks 4+6 (compose override); §5.4 → Task 9 (+Task 2 for beat 8); §5.5 → Tasks 3+6; §5.6 → Tasks 5+6; §5.7 → Tasks 8+9; §6 build order = C1 (Tasks 1–3, 7–8) / C2 (4–6) / C3 (9), Task 10 closes; §7 tests distributed per module. Non-goals have no tasks — correct.
- **Cut lines:** after Task 8 the ask channel ships alone (C1 floor); after Task 6 the backend is API-complete (C2); Task 9 is the full walk (C3). Task ordering interleaves C1/C2 only where the prompt module is shared (Task 3 does both sections at once — removes the two-edits-one-file rebase friction the review flagged).
- **Type consistency:** `extract_studio → {"picks","name","ready","ask"}` (T1) = what `_extract` stores and the `done` event carries (journey T3/T4) = what `renderAskCard(ev.studio.ask)` reads (T8). `onboarding.*` signatures (T4) = server wrappers (T6). `distill(sources, timeout)` (T5) = server call + monkeypatch target (T6) + smoke (T10). `cards.show/fold/queue/morph/baton/onBaton` (T7) = consumers in T8/T9. `startWorkshopSession`/`queueSend`/`onboardingActive` (T8) = T9 consumption.
- **No placeholders:** every code step carries complete code; the only deferred decision (PDF copy tweak) is an explicit either/or with both outcomes specified.
