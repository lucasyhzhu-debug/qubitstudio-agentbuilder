# QubitStudio Journey — Reskin + Conversation-Driven Shelf — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the workshop chat chief-of-staff-aware so it drives the skill shelf, and reskin the studio to qubit-site's SapphireOS design system.

**Architecture:** A new workshop system prompt (catalog-aware interview) makes the tool-less `claude -p` chat emit a ` ```studio ` fenced block each turn; a new extractor parses it server-side and the SSE `done` event carries it to the browser, which syncs the shelf selection and a new "Your agent" panel. The reskin is a token-level swap of `studio/static/` CSS to the SapphireOS palette/fonts lifted from `qubit-site/app/globals.css`.

**Tech Stack:** FastAPI + vanilla JS (no build step), pytest, self-hosted OFL fonts.

**Spec:** `docs/specs/2026-07-02-studio-qubitstudio-journey-design.md` (shipshape-reviewed; read it first).

**Flagged deviations (deliberate, not omissions):**
- ROADMAP/CHANGELOG updates are NOT a task here — they ride the pipeline's landing PR (spec-plan-pipeline step 6).
- If the work cuts after Task 5 (slice B1 only), `.sc-rec` renders unstyled and the status chip has no pulse animation — those styles land in Task 7. Functional, just plain; not a bug.

## Global Constraints

- Branch: `feat/qubitstudio-journey` (already exists with the spec). Commit per task.
- Repo is PUBLIC — no real keys/tokens/ids/emails in any commit. Fonts are OFL (allowed).
- `chief-of-staff/` and `agent-architect/` are NOT touched by any task.
- Architect mode must stay byte-identical: `build_system_prompt()` and its 5 tests unchanged.
- All pytest runs use the repo venv: `.venv/Scripts/python -m pytest …` (Windows dev box) — cross-platform participants are unaffected (static/server changes only).
- No new third-party imports anywhere (`python -m studio` bootstrap constraint doesn't apply to these modules, but keep to stdlib + existing deps).
- The studio block label is ` ```studio ` — never ` ```json ` (that's the spec extractor's fallback).

---

### Task 1: `studio_extractor.py` — parse the workshop studio block

**Files:**
- Create: `studio/studio_extractor.py`
- Test: `studio/tests/test_studio_extractor.py`

**Interfaces:**
- Produces: `extract_studio(assistant_text: str, catalog_ids: set[str]) -> dict | None` — returns `{"picks": list[str], "name": str | None, "ready": bool}` or `None`. Task 3 (ChatSession) consumes this exact signature.

- [ ] **Step 1: Write the failing tests**

```python
# studio/tests/test_studio_extractor.py
from studio.studio_extractor import extract_studio

IDS = {"crm", "briefing", "scheduling", "tasks", "intake", "drain"}

def _block(inner):
    return f"Some prose.\n```studio\n{inner}\n```\nMore prose."

def test_extracts_valid_block():
    out = extract_studio(_block('{"picks": ["crm", "briefing"], "name": "my-cos", "ready": false}'), IDS)
    assert out == {"picks": ["crm", "briefing"], "name": "my-cos", "ready": False}

def test_absent_block_returns_none():
    assert extract_studio("no fences here", IDS) is None

def test_malformed_json_returns_none():
    assert extract_studio(_block('{"picks": [oops'), IDS) is None

def test_missing_picks_returns_none():
    # picks-as-list is what structurally identifies a studio block
    assert extract_studio(_block('{"name": "x", "ready": true}'), IDS) is None

def test_unknown_ids_dropped_valid_kept():
    out = extract_studio(_block('{"picks": ["crm", "hallucinated", "tasks"]}'), IDS)
    assert out["picks"] == ["crm", "tasks"]

def test_last_block_wins():
    text = _block('{"picks": ["crm"]}') + "\n" + _block('{"picks": ["tasks"]}')
    assert extract_studio(text, IDS)["picks"] == ["tasks"]

def test_ready_and_name_coercion():
    out = extract_studio(_block('{"picks": [], "name": "", "ready": 1}'), IDS)
    assert out["name"] is None and out["ready"] is True

def test_spec_fence_not_matched():
    # a ```spec block must never parse as a studio block, and vice versa
    text = '```spec\n{"plugin": {"name": "x"}, "components": [], "picks": ["crm"]}\n```'
    assert extract_studio(text, IDS) is None

def test_json_fence_not_matched():
    # no ```json fallback — that fence belongs to the spec extractor
    text = '```json\n{"picks": ["crm"]}\n```'
    assert extract_studio(text, IDS) is None
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/Scripts/python -m pytest studio/tests/test_studio_extractor.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'studio.studio_extractor'`

- [ ] **Step 3: Implement**

```python
# studio/studio_extractor.py
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
    name = obj.get("name")
    if not isinstance(name, str) or not name.strip():
        name = None
    return {"picks": picks, "name": name, "ready": bool(obj.get("ready"))}
```

- [ ] **Step 4: Run to verify pass**

Run: `.venv/Scripts/python -m pytest studio/tests/test_studio_extractor.py -v`
Expected: 9 passed

- [ ] **Step 5: Commit**

```bash
git add studio/studio_extractor.py studio/tests/test_studio_extractor.py
git commit -m "feat(studio): studio-block extractor for the workshop journey"
```

---

### Task 2: Workshop system prompt builder

**Files:**
- Modify: `studio/system_prompt.py` (add-only — existing functions untouched)
- Test: `studio/tests/test_system_prompt.py` (append tests)

**Interfaces:**
- Consumes: `studio/catalog.json` (shape: `{"baseline": {"items": [{id,name,what,cost}]}, "shelf": {"items": [{id,name,what,deliverable,cost,requires,needs_skills,brief}]}}`).
- Produces: `build_workshop_prompt(catalog_path: Path | None = None) -> str` and `write_system_prompt(out_path, architect_dir=None, mode="architect", catalog_path=None) -> Path`. Task 4 (server) consumes both. `mode="architect"` default keeps every existing caller working unchanged.

- [ ] **Step 1: Write the failing tests** (append to `studio/tests/test_system_prompt.py`)

```python
# --- workshop mode (QubitStudio journey spec §4.2) ---
from studio.system_prompt import build_workshop_prompt

def test_workshop_includes_catalog_and_contract():
    p = build_workshop_prompt()
    for skill_id in ("crm", "briefing", "scheduling", "tasks", "intake", "drain"):
        assert skill_id in p                  # every shelf id injected
    assert "wiki-brain" in p                  # baseline injected
    assert "```studio" in p                   # emit-the-block instruction
    assert "superpowers" in p.lower()         # ignore-skill-injection guard kept

def test_workshop_excludes_architect_machinery():
    p = build_workshop_prompt()
    assert "Q0" not in p                      # no quiz
    assert "```spec" not in p                 # no spec contract
    assert "render_setup" not in p

def test_write_system_prompt_workshop_mode(tmp_path):
    from studio.system_prompt import write_system_prompt
    out = write_system_prompt(tmp_path / "wp.md", mode="workshop")
    text = out.read_text(encoding="utf-8")
    assert "```studio" in text and "crm" in text

def test_write_system_prompt_default_is_architect_unchanged(tmp_path):
    from studio.system_prompt import write_system_prompt, build_system_prompt
    out = write_system_prompt(tmp_path / "sp.md")
    assert out.read_text(encoding="utf-8") == build_system_prompt()
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/Scripts/python -m pytest studio/tests/test_system_prompt.py -v`
Expected: existing 5 PASS; new 4 FAIL — `ImportError: cannot import name 'build_workshop_prompt'`

- [ ] **Step 3: Implement** (append to `studio/system_prompt.py`; also add `import json` at the top)

```python
# ── Workshop mode (QubitStudio journey spec §4.2) ─────────────────────────────
_STUDIO_DIR = Path(__file__).resolve().parent

_WORKSHOP_ROLE_INTRO = """You are **agent-architect**, the guide for the QubitStudio
"Build Your Own Chief of Staff" workshop. Everyone in the room is building a personal
chief-of-staff agent on a fixed substrate (the baseline below). Your job is to interview the
participant about their working life and recommend which shelf skills belong in THEIR build.
You ONLY converse and emit the studio block — you do not call tools, run scripts, or generate
files. Ignore any session-start instructions about 'superpowers' or invoking skills; they do
not apply to you."""

_WORKSHOP_CONTRACT = """
# Studio contract (how this session is wired)

- Interview the participant about their working life ONE topic at a time: inbox volume and
  where their tasks live (-> tasks), their morning routine (-> briefing), meeting and
  scheduling load (-> scheduling), how they track people and relationships (-> crm),
  screenshot habits (-> intake), and appetite for an always-on inbox channel (-> drain).
- Recommend shelf skills by their exact catalog id. Explain the price tag (which integrations
  each skill needs). Respect needs_skills prerequisites — recommend the prerequisite too and
  say why. Do not oversell `drain` (the heaviest tier) to a first-timer.
- After EVERY turn, emit the FULL current state as a single fenced block labelled ```studio
  (never ```json). Whole block each time, not a diff; no prose inside the fence:

  ```studio
  { "picks": ["crm", "briefing"], "name": "my-cos", "ready": false }
  ```

  `picks` = shelf ids the participant has accepted so far (ids from the shelf above ONLY);
  `name` = the agent's name once they choose one, else null; `ready` = true only after the
  participant explicitly confirms they want to build.
- When ready is true, tell them to press "Build my agent".
"""


def _render_catalog(catalog: dict) -> str:
    lines = ["## The baseline (locked — everyone builds this)"]
    for it in catalog.get("baseline", {}).get("items", []):
        lines.append(f"- **{it['id']}** ({it['name']}): {it['what']}")
    lines.append("")
    lines.append("## The shelf (recommend from these ids ONLY)")
    for it in catalog.get("shelf", {}).get("items", []):
        req = ", ".join(it.get("requires") or []) or "none"
        needs = ", ".join(it.get("needs_skills") or []) or "none"
        lines.append(
            f"- **{it['id']}** ({it['name']}): {it['what']} "
            f"Makes: {it.get('deliverable', '(local output)')}. Integrations: {req}. "
            f"Prerequisite skills: {needs}. Price tag: {it.get('cost', {}).get('label', '')}."
        )
    return "\n".join(lines)


def build_workshop_prompt(catalog_path: Path | None = None) -> str:
    path = catalog_path or (_STUDIO_DIR / "catalog.json")
    catalog = json.loads(path.read_text(encoding="utf-8"))
    return "\n\n".join([
        _WORKSHOP_ROLE_INTRO,
        "# The substrate & the shelf\n\n" + _render_catalog(catalog),
        _WORKSHOP_CONTRACT,
    ])
```

And change `write_system_prompt` to:

```python
def write_system_prompt(out_path: Path, architect_dir: Path | None = None,
                        mode: str = "architect", catalog_path: Path | None = None) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    content = (build_workshop_prompt(catalog_path) if mode == "workshop"
               else build_system_prompt(architect_dir))
    out_path.write_text(content, encoding="utf-8")
    return out_path
```

- [ ] **Step 4: Run to verify pass**

Run: `.venv/Scripts/python -m pytest studio/tests/test_system_prompt.py -v`
Expected: 9 passed (5 existing + 4 new)

- [ ] **Step 5: Commit**

```bash
git add studio/system_prompt.py studio/tests/test_system_prompt.py
git commit -m "feat(studio): chief-of-staff-aware workshop system prompt (catalog-injected)"
```

---

### Task 3: ChatSession carries the studio block

**Files:**
- Modify: `studio/chat_session.py`
- Test: `studio/tests/test_chat_session.py` (append tests)

**Interfaces:**
- Consumes: `extract_studio` from Task 1.
- Produces: `ChatSession(session_id, system_prompt_path, claude_bin=None, catalog_ids: set[str] | None = None)`; `self.studio: dict | None`; `send()`'s final event becomes `{"type": "done", "spec": self.spec, "studio": self.studio}`. Task 4 and the frontend rely on the `studio` key existing on every done event (may be None).

- [ ] **Step 1: Write the failing tests** (append to `studio/tests/test_chat_session.py`)

```python
def test_catalog_ids_default_none_and_studio_none(tmp_path):
    s = _sess(tmp_path)
    assert s.catalog_ids is None and s.studio is None

def test_extract_pass_architect_mode_skips_studio(tmp_path):
    # catalog_ids None -> studio extraction never runs, even on a studio-looking text
    s = _sess(tmp_path)
    s._extract('```studio\n{"picks": ["crm"]}\n```')
    assert s.studio is None

def test_extract_pass_workshop_mode_sets_studio(tmp_path):
    sp_path = tmp_path / "sp.md"; sp_path.write_text("p", encoding="utf-8")
    from studio.chat_session import ChatSession
    s = ChatSession(session_id="11111111-1111-1111-1111-111111111111",
                    system_prompt_path=sp_path, catalog_ids={"crm", "tasks"})
    s._extract('hi\n```studio\n{"picks": ["crm"], "name": "my-cos", "ready": false}\n```')
    assert s.studio == {"picks": ["crm"], "name": "my-cos", "ready": False}

def test_extract_pass_keeps_prior_studio_on_garbage(tmp_path):
    sp_path = tmp_path / "sp.md"; sp_path.write_text("p", encoding="utf-8")
    from studio.chat_session import ChatSession
    s = ChatSession(session_id="11111111-1111-1111-1111-111111111111",
                    system_prompt_path=sp_path, catalog_ids={"crm"})
    s._extract('```studio\n{"picks": ["crm"]}\n```')
    s._extract('no block this turn')
    assert s.studio == {"picks": ["crm"], "name": None, "ready": False}
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/Scripts/python -m pytest studio/tests/test_chat_session.py -v`
Expected: existing PASS; new 4 FAIL (`AttributeError: ... no attribute 'catalog_ids'` / `'_extract'`)

- [ ] **Step 3: Implement.** In `studio/chat_session.py`: import `extract_studio`, extend `__init__`, factor the end-of-turn extraction into `_extract` (testable without a subprocess), and call it from `send()`.

```python
from studio.studio_extractor import extract_studio
```

```python
    def __init__(self, session_id: str, system_prompt_path: Path, claude_bin: str | None = None,
                 catalog_ids: set[str] | None = None):
        self.session_id = session_id
        self.system_prompt_path = str(system_prompt_path)
        self.claude_bin = claude_bin or resolve_claude() or "claude"
        self.started = False
        self.spec: dict | None = None
        # Workshop sessions get the shelf ids; None means architect mode — the studio
        # extractor never runs (QubitStudio journey spec §4.3).
        self.catalog_ids = catalog_ids
        self.studio: dict | None = None

    def _extract(self, text: str) -> None:
        """End-of-turn extraction pass: spec always, studio only for workshop sessions.
        Either extractor returning None keeps the prior state."""
        new_spec = extract_spec(text)
        if new_spec is not None:
            self.spec = new_spec
        if self.catalog_ids is not None:
            new_studio = extract_studio(text, self.catalog_ids)
            if new_studio is not None:
                self.studio = new_studio
```

In `send()`, replace the tail (currently lines 96-100):

```python
        self.started = True
        self._extract("".join(full_text))
        yield {"type": "done", "spec": self.spec, "studio": self.studio}
```

- [ ] **Step 4: Run to verify pass**

Run: `.venv/Scripts/python -m pytest studio/tests/test_chat_session.py -v`
Expected: all pass (existing + 4 new)

- [ ] **Step 5: Commit**

```bash
git add studio/chat_session.py studio/tests/test_chat_session.py
git commit -m "feat(studio): ChatSession extracts the studio block for workshop sessions"
```

---

### Task 4: Server session modes

**Files:**
- Modify: `studio/server.py` (`new_session`, new `_WORKSHOP_PROMPT` constant, new `_catalog_ids` helper)
- Test: `studio/tests/test_server.py` (append tests; also update `_FakeSession` — see step 1)

**Interfaces:**
- Consumes: `write_system_prompt(..., mode=...)` (Task 2), `ChatSession(..., catalog_ids=...)` (Task 3).
- Produces: `POST /api/session/new` accepts optional `{"mode": "workshop"|"architect"}`, tolerant of absent/empty/invalid body, **default workshop**; response gains `"mode"`. Workshop sessions get `catalog_ids`; prompt caches split (`.cache/workshop-system-prompt.md` / `.cache/architect-system-prompt.md`). `/api/session/load` stays architect (spec upload is an architect artifact).

- [ ] **Step 1: Write the failing tests** (append to `studio/tests/test_server.py`; also add `"studio": None` to `_FakeSession.send`'s done event so it mirrors the real shape)

```python
def test_new_session_defaults_to_workshop():
    c = TestClient(server.app)
    r = c.post("/api/session/new")               # bare POST, no body — must keep working
    assert r.status_code == 200 and r.json()["mode"] == "workshop"
    sid = r.json()["session_id"]
    assert server.SESSIONS[sid].catalog_ids       # shelf ids wired in
    assert "crm" in server.SESSIONS[sid].catalog_ids

def test_new_session_architect_mode():
    c = TestClient(server.app)
    r = c.post("/api/session/new", json={"mode": "architect"})
    assert r.json()["mode"] == "architect"
    assert server.SESSIONS[r.json()["session_id"]].catalog_ids is None

def test_new_session_junk_mode_falls_back_to_workshop():
    c = TestClient(server.app)
    r = c.post("/api/session/new", json={"mode": "banana"})
    assert r.json()["mode"] == "workshop"

def test_chat_done_carries_studio(monkeypatch):
    class _FakeStudioSession:
        spec = None
        async def send(self, msg):
            yield {"type": "token", "text": "hi"}
            yield {"type": "done", "spec": None, "studio": {"picks": ["crm"], "name": None, "ready": False}}
    c = TestClient(server.app)
    sid = c.post("/api/session/new").json()["session_id"]
    server.SESSIONS[sid] = _FakeStudioSession()
    with c.stream("POST", "/api/chat", json={"session_id": sid, "message": "hi"}) as r:
        body = "".join(r.iter_text())
    assert '"picks"' in body and '"crm"' in body
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/Scripts/python -m pytest studio/tests/test_server.py -v`
Expected: new tests FAIL (`KeyError: 'mode'` / missing `catalog_ids`); existing tests PASS

- [ ] **Step 3: Implement.** In `studio/server.py` add below `_SYSTEM_PROMPT`:

```python
_WORKSHOP_PROMPT = _HERE / ".cache" / "workshop-system-prompt.md"


def _catalog_ids() -> set[str]:
    try:
        data = json.loads(_CATALOG.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()
    return {it["id"] for it in data.get("shelf", {}).get("items", [])
            if isinstance(it, dict) and it.get("id")}
```

Replace `new_session`:

```python
@app.post("/api/session/new")
async def new_session(req: Request) -> JSONResponse:
    # Tolerant body parse: absent/empty/invalid body -> workshop default (spec §4.1).
    try:
        body = await req.json()
    except Exception:
        body = {}
    mode = body.get("mode") if isinstance(body, dict) else None
    if mode not in ("workshop", "architect"):
        mode = "workshop"
    sid = str(uuid.uuid4())
    if mode == "architect":
        write_system_prompt(_SYSTEM_PROMPT)  # idempotent; refreshes from current architect refs
        SESSIONS[sid] = ChatSession(session_id=sid, system_prompt_path=_SYSTEM_PROMPT)
    else:
        write_system_prompt(_WORKSHOP_PROMPT, mode="workshop")
        SESSIONS[sid] = ChatSession(session_id=sid, system_prompt_path=_WORKSHOP_PROMPT,
                                    catalog_ids=_catalog_ids())
    return JSONResponse({"session_id": sid, "mode": mode})
```

(`/api/session/load` is untouched — it already writes the architect prompt.)

- [ ] **Step 4: Run to verify pass**

Run: `.venv/Scripts/python -m pytest studio/tests/test_server.py -v`
Expected: all pass

- [ ] **Step 5: Run the whole backend suite** (guard against cross-module fallout)

Run: `.venv/Scripts/python -m pytest studio/tests -q -m "not integration"`
Expected: all pass

- [ ] **Step 6: Commit**

```bash
git add studio/server.py studio/tests/test_server.py
git commit -m "feat(studio): session modes — workshop default, architect kept"
```

---

### Task 5: Frontend B1 — mode, seed, handshake chip, chat→shelf sync

**Files:**
- Modify: `studio/static/app.js` (start/send/stripSpec/done-handler)
- Modify: `studio/static/shelf.js` (origin-tagged selection + `shelfSync`)

**Interfaces:**
- Consumes: `/api/session/new` `{mode}` body + `mode` in response (Task 4); `ev.studio` on done events (Task 3/4).
- Produces: `window.shelfSync({picks, name, ready})` (called by app.js); `selected` map values become `{it, origin}` where origin ∈ `'user'|'agent'`.

- [ ] **Step 1: app.js — mode + seed + status.** Replace the top of the file (lines 1–9) with:

```js
const $ = (s) => document.querySelector(s);
let sessionId = null, currentSpec = null, agentLive = false;

// ?mode=architect keeps the generic plugin-design interview reachable (spec §4.1/§4.7).
const MODE = new URLSearchParams(location.search).get('mode') === 'architect' ? 'architect' : 'workshop';
const SEED = MODE === 'architect' ? 'Begin the agent-architect interview.' : 'Begin the workshop interview.';

function setStatus(text, live) {
  const el = $('#status');
  el.textContent = text;
  el.classList.toggle('live', !!live);
}

async function start() {
  const r = await fetch('/api/session/new', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mode: MODE }),
  });
  sessionId = (await r.json()).session_id;
  setStatus('ready');
  send(SEED);  // seed the first turn
}
```

- [ ] **Step 2: app.js — seed suppression, stripSpec, first-token handshake, studio sync.** In `send()`: change line 41 to `if (message !== SEED) addBubble('user', message);`. Extend both stripSpec regexes to include `studio`:

```js
function stripSpec(text) {
  return text
    .replace(/```(?:spec|json|studio)[\s\S]*?```/g, '')  // closed blocks
    .replace(/```(?:spec|json|studio)[\s\S]*$/, '')       // an unclosed trailing block (mid-stream)
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}
```

In the SSE loop, extend the token and done branches:

```js
      if (ev.type === 'token') {
        if (!agentLive) { agentLive = true; setStatus('agent live', true); }  // verifiable handshake
        acc += ev.text; bubble.innerHTML = renderMarkdown(stripSpec(acc)); scrollLog();
      }
      else if (ev.type === 'error') { acc += '\n\n**[error]** ' + ev.message; bubble.innerHTML = renderMarkdown(stripSpec(acc)); }
      else if (ev.type === 'done') {
        if (ev.spec) renderBlueprint(ev.spec);
        if (ev.studio && typeof window.shelfSync === 'function') window.shelfSync(ev.studio);
      }
```

Also update the spec-upload handler's status line (near line 368): `$('#status').textContent = 'loaded';` → `setStatus('loaded');`.

- [ ] **Step 3: shelf.js — origin-tagged selection.** The `selected` map now stores `{it, origin}`. Apply these changes inside the IIFE:

```js
  const selected = new Map();   // id -> { it, origin: 'user' | 'agent' }
```

`shelfCard` (recommended eyebrow on agent-sourced picks):

```js
  function shelfCard(it) {
    const v = selected.get(it.id);
    const on = !!v;
    const rec = v && v.origin === 'agent';
    return `<div class="shelf-card ${on ? 'on' : ''} ${rec ? 'recommended' : ''}" data-id="${esc(it.id)}">
      <div class="sc-head"><span class="sc-name">${esc(it.name)}</span>${tag(it.cost)}</div>
      ${rec ? '<div class="sc-rec">✓ recommended</div>' : ''}
      <p class="sc-what">${esc(it.what)}</p>
      ${it.deliverable ? `<div class="sc-deliv">makes <b>${esc(it.deliverable)}</b></div>` : ''}
      <button class="sc-add" data-id="${esc(it.id)}">${on ? '✓ Added' : 'Add to agent'}</button>
    </div>`;
  }
```

`renderFoot` first line becomes `const items = [...selected.values()].map((v) => v.it);` (rest unchanged). `toggle` becomes:

```js
  function toggle(id) {
    const it = (catalog.shelf.items || []).find((x) => x.id === id);
    if (!it) return;
    if (selected.has(id)) selected.delete(id); else selected.set(id, { it, origin: 'user' });
    renderBody();  // re-render so on/recommended states stay truthful
  }
```

(`renderBody()` already calls `renderFoot()` + `updateBtn()`; the per-card DOM patching in the old `toggle` is superseded by the re-render. NOTE: `renderBody` rebuilds `.shelf-foot`, wiping the name input — preserve it: capture `const keep = sel('.shelf-foot .shelf-name')?.value` at the top of `renderBody` and restore it after `renderFoot()` runs: `const nf = sel('.shelf-foot .shelf-name'); if (nf && keep) nf.value = keep;`.)

- [ ] **Step 4: shelf.js — `shelfSync`.** Add inside the IIFE (before `init()`), and expose it:

```js
  // Chat→shelf sync (spec §4.4): the agent's studio block re-asserts ITS picks only.
  // User-added picks are never removed by a sync; agent picks no longer recommended drop.
  function shelfSync(studio) {
    if (!catalog || !studio) return;
    const picks = new Set(studio.picks || []);
    for (const [id, v] of [...selected]) {
      if (v.origin === 'agent' && !picks.has(id)) selected.delete(id);
    }
    for (const id of picks) {
      if (!selected.has(id)) {
        const it = (catalog.shelf.items || []).find((x) => x.id === id);
        if (it) selected.set(id, { it, origin: 'agent' });
      }
    }
    renderBody();
    const nameField = sel('.shelf-foot .shelf-name');
    if (studio.name && nameField && !nameField.value.trim()) nameField.value = studio.name;
  }
  window.shelfSync = shelfSync;
```

- [ ] **Step 5: Manual verification** (real `claude` required)

Run: `.venv/Scripts/python -m studio` — then in the browser:
1. Status chip goes `starting…` → `ready` → `agent live` when the first greeting token streams (the handshake).
2. The greeting talks about the chief-of-staff workshop (not "what plugin do you want").
3. Answer one interview question so the agent recommends a skill → open the shelf: the card is on with `✓ recommended`; header badge counts it.
4. Manually add a different skill, answer another question → your manual pick survives the next sync.
5. No ` ```studio ` JSON ever flashes in the chat log.
6. `http://127.0.0.1:8000/?mode=architect` still runs the old interview and fills the blueprint.

- [ ] **Step 6: Backend suite still green**

Run: `.venv/Scripts/python -m pytest studio/tests -q -m "not integration"`
Expected: all pass

- [ ] **Step 7: Commit**

```bash
git add studio/static/app.js studio/static/shelf.js
git commit -m "feat(studio): conversation drives the shelf — mode-aware seed, handshake chip, shelfSync"
```

---

### Task 6: Reskin part 1 — fonts + design tokens

**Files:**
- Create: `studio/static/fonts/` (7 files copied from qubit-site)
- Modify: `studio/static/styles.css` (`@font-face` + `:root` + token rename), `studio/static/shelf.css` (token rename), `studio/README.md` (font provenance line)

**Interfaces:**
- Produces: the SapphireOS token set (`--canvas --band --sapphire --sapphire-hover --tint --tint-2 --teal --brass --brass-tint --ink --ink-2 --ink-3 --ink-4 --rule --rule-strong --ok --warn --err --r-card --r-btn --r-pill --sh-sm --sh-md --sh-lg --display --body --mono --wordmark`). Tasks 7–8 style against these names.

- [ ] **Step 1: Fetch the fonts**

```bash
git clone --depth 1 https://github.com/Nicegarrry/qubit-site /tmp/qubit-site-fonts
mkdir -p studio/static/fonts
cp /tmp/qubit-site-fonts/public/fonts/BricolageGrotesque.ttf \
   /tmp/qubit-site-fonts/public/fonts/HankenGrotesk.ttf \
   /tmp/qubit-site-fonts/public/fonts/HankenGrotesk-Italic.ttf \
   /tmp/qubit-site-fonts/public/fonts/JetBrainsMono-Regular.woff2 \
   /tmp/qubit-site-fonts/public/fonts/JetBrainsMono-Medium.woff2 \
   /tmp/qubit-site-fonts/public/fonts/CrimsonPro-Regular.woff2 \
   /tmp/qubit-site-fonts/public/fonts/CrimsonPro-Italic.woff2 \
   studio/static/fonts/
```

Expected: 7 files, ~756 KB total (`du -sh studio/static/fonts`).

- [ ] **Step 2: Replace the head of `styles.css`.** Delete the current `:root` block (lines 1–17) and put this at the top of the file:

```css
/* SapphireOS — lifted from qubit-site app/globals.css (white-canvas recast). Light-only. */
@font-face { font-family: 'Bricolage Grotesque'; src: url('/static/fonts/BricolageGrotesque.ttf') format('truetype'); font-weight: 200 800; font-display: swap; }
@font-face { font-family: 'Hanken Grotesk'; src: url('/static/fonts/HankenGrotesk.ttf') format('truetype'); font-weight: 100 900; font-display: swap; }
@font-face { font-family: 'Hanken Grotesk'; src: url('/static/fonts/HankenGrotesk-Italic.ttf') format('truetype'); font-weight: 100 900; font-style: italic; font-display: swap; }
@font-face { font-family: 'JetBrains Mono'; src: url('/static/fonts/JetBrainsMono-Regular.woff2') format('woff2'); font-weight: 400; font-display: swap; }
@font-face { font-family: 'JetBrains Mono'; src: url('/static/fonts/JetBrainsMono-Medium.woff2') format('woff2'); font-weight: 500; font-display: swap; }
@font-face { font-family: 'Crimson Pro'; src: url('/static/fonts/CrimsonPro-Regular.woff2') format('woff2'); font-weight: 400; font-display: swap; }
@font-face { font-family: 'Crimson Pro'; src: url('/static/fonts/CrimsonPro-Italic.woff2') format('woff2'); font-weight: 400; font-style: italic; font-display: swap; }

:root {
  --canvas:#FFFFFF; --band:#F7FAFC;
  --sapphire:#306FA8; --sapphire-hover:#1E4C80; --tint:#EEF4FA; --tint-2:#DBE8F3;
  --teal:#347890; --brass:#C2791A; --brass-tint:#F6EDDC;
  --ink:#141A21; --ink-2:#3A4550; --ink-3:#6B7681; --ink-4:#9AA4AD;
  --rule:rgba(20,26,33,0.10); --rule-strong:rgba(20,26,33,0.20);
  --ok:#2E7D5B; --warn:#B5852B; --err:#B6463C;
  --ok-t:rgba(46,125,91,0.12); --warn-t:rgba(181,133,43,0.14); --err-t:rgba(182,70,60,0.12);
  --r-card:14px; --r-btn:10px; --r-pill:999px;
  --sh-sm:0 1px 2px rgba(20,26,33,.04),0 2px 8px rgba(20,26,33,.05);
  --sh-md:0 2px 6px rgba(20,26,33,.06),0 10px 28px rgba(20,26,33,.09);
  --sh-lg:0 12px 40px rgba(20,26,33,.11);
  --display:'Bricolage Grotesque',system-ui,sans-serif;
  --body:'Hanken Grotesk',system-ui,sans-serif;
  --mono:'JetBrains Mono',ui-monospace,'Cascadia Code',monospace;
  --wordmark:'Crimson Pro',Georgia,serif;
}
```

- [ ] **Step 3: Mechanical token rename** across `styles.css` AND `shelf.css` — every occurrence, no alias layer:

| old | new |
|---|---|
| `var(--bg)` | `var(--band)` (page background) |
| `var(--panel)` | `var(--canvas)` (cards/panels are white) |
| `var(--panel2)` | `var(--band)` |
| `var(--line)` | `var(--rule)` |
| `var(--ink)` | `var(--ink)` (value changed, name kept) |
| `var(--mut)` | `var(--ink-3)` |
| `var(--dim)` | `var(--ink-4)` |
| `var(--acc)` | `var(--sapphire)` |
| `var(--acc2)` | `var(--sapphire)` |
| `var(--pink)` | `var(--err)` |
| `var(--sans)` | `var(--body)` |
| `var(--ok)` / `var(--warn)` | names kept (values changed in `:root`) |

- [ ] **Step 4: Hardcoded-color fixes** (spec §3.4):
- `styles.css` `#composer button[type="submit"]`: `color:#04060c` → `color:#fff`
- `shelf.css` `.brief-btn`: `color:#04060c` → `color:#fff`
- `shelf.css` `.shelf-card.on`: `background:#1d2235` → `background:var(--tint); border:1.5px solid var(--sapphire)`
- `styles.css` `.bubble.assistant strong`: `color:#fff` → `color:var(--ink)`

- [ ] **Step 5: Verify the rename left nothing behind**

```bash
grep -nE "var\(--(bg|panel2?|line|mut|dim|acc2?|pink|sans)\)" studio/static/styles.css studio/static/shelf.css
```

Expected: no output. Also add to `studio/README.md` (fonts section or footer): `Fonts in studio/static/fonts/ are OFL-licensed (Bricolage Grotesque, Hanken Grotesk, JetBrains Mono, Crimson Pro), copied from the qubit-site repo.`

- [ ] **Step 6: Visual sanity check.** Run `.venv/Scripts/python -m studio`: the app renders light (colors will look rough until Task 7 — that's expected; check nothing is white-on-white illegible in chat, shelf, and the build panel).

- [ ] **Step 7: Commit**

```bash
git add studio/static/fonts studio/static/styles.css studio/static/shelf.css studio/README.md
git commit -m "feat(studio): SapphireOS tokens + self-hosted OFL fonts (light-only)"
```

---

### Task 7: Reskin part 2 — header/nav, chat, buttons, cards, shelf

**Files:**
- Modify: `studio/static/index.html` (header markup), `studio/static/styles.css`, `studio/static/shelf.css`

**Interfaces:**
- Consumes: Task 6 tokens. Task 5's `setStatus(text, live)` toggles `.live` on `#status`.
- Produces: `.eyebrow`, `.status-chip`, `.qmark`, `.wordmark` classes; header structure Task 8 extends with the advanced disclosure.

- [ ] **Step 1: Header markup.** In `index.html`, replace the `<header>…</header>` block with (all existing ids kept — app.js listeners depend on them):

```html
<header>
  <span class="qmark"><i></i><i></i><i></i><i class="fill"></i></span>
  <span class="wordmark">qubit</span>
  <span class="brand-eyebrow">Agent Studio</span>
  <span id="status" class="status-chip"><i class="dot"></i><span class="st"></span>starting…</span>
  <button id="shelfbtn" title="Browse the skill shelf, add capabilities, and build your installable agent">Skill shelf ▦<span class="count">0</span></button>
  <input id="loadfile" type="file" accept="application/json" hidden>
  <button id="load">Load spec.json</button>
  <button id="download" disabled>Download spec.json</button>
  <label id="evalstoggle" title="M3 evals fan out many nested claude runs and are slow. Off → grade 'validated'; on → 'verified'."><input id="runevals" type="checkbox"> evals</label>
  <button id="export" disabled>Export .plugin ▶</button>
</header>
```

NOTE: `setStatus` writes `el.textContent = text`, which would wipe the `<i class="dot">` child — change `setStatus` in app.js to:

```js
function setStatus(text, live) {
  const el = $('#status');
  el.innerHTML = '<i class="dot"></i>' + text.replace(/[<>&]/g, '');
  el.classList.toggle('live', !!live);
}
```

- [ ] **Step 2: Header + signature styles.** Replace the current `header`/`#status`/header-button rules in `styles.css` with:

```css
header {
  position: sticky; top: 0; z-index: 20;
  display: flex; align-items: center; gap: 12px;
  height: 62px; padding: 0 20px;
  background: rgba(255,255,255,.92);
  backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px);
  border-bottom: 1px solid var(--rule);
}
.qmark { display: grid; grid-template-columns: 1fr 1fr; gap: 2px; width: 22px; height: 22px; }
.qmark i { border: 1.5px solid var(--sapphire); border-radius: 3px; }
.qmark i.fill { background: var(--sapphire); }
.wordmark { font-family: var(--wordmark); font-size: 21px; color: var(--ink); }
.brand-eyebrow, .eyebrow {
  font-family: var(--mono); font-size: 10.5px; font-weight: 500;
  text-transform: uppercase; letter-spacing: .14em; color: var(--ink-3);
}
.status-chip {
  display: inline-flex; align-items: center; gap: 6px;
  font-family: var(--mono); font-size: 11px; color: var(--ink-3);
  padding: 4px 10px; border: 1px solid var(--tint-2); border-radius: var(--r-pill);
  background: var(--tint);
}
.status-chip .dot { width: 6px; height: 6px; border-radius: 50%; background: var(--ink-4); }
.status-chip.live { color: var(--sapphire); }
.status-chip.live .dot { background: var(--sapphire); animation: pulse 1.8s ease-in-out infinite; }
@keyframes pulse { 0%,100% { opacity: 1; transform: scale(1); } 50% { opacity: .45; transform: scale(.8); } }
@media (prefers-reduced-motion: reduce) { .status-chip.live .dot { animation: none; } }
```

- [ ] **Step 3: Body/typography/buttons/cards/chat.** Apply across `styles.css`:

```css
body { background: var(--band); color: var(--ink-2); font-family: var(--body); font-size: 16px; line-height: 1.45; }
h1,h2,h3,h4 { font-family: var(--display); color: var(--ink); letter-spacing: -0.02em; }

button, .brief-btn {
  font-family: var(--body); font-weight: 600; border-radius: var(--r-btn);
  transition: background .15s ease, transform .18s ease, border-color .15s ease;
}
#composer button[type="submit"], .brief-btn { background: var(--sapphire); color: #fff; border: none; }
#composer button[type="submit"]:hover, .brief-btn:hover { background: var(--sapphire-hover); }
header button, #load, #download, #export {
  background: var(--canvas); border: 1.5px solid var(--rule-strong); color: var(--ink-2);
}
header button:hover { border-color: var(--sapphire); color: var(--sapphire); }

.bp-card, .keyrow, .personalize, .wizard {
  background: var(--canvas); border: 1px solid var(--rule);
  border-radius: var(--r-card); box-shadow: var(--sh-sm);
}
.bp-card h3 { font-family: var(--mono); font-size: 10.5px; font-weight: 500;
  text-transform: uppercase; letter-spacing: .14em; color: var(--ink-3); }

#log { background: var(--band); }
.bubble.user { background: var(--sapphire); color: #fff; border-radius: 12px; border-bottom-right-radius: 4px; }
.bubble.assistant { background: var(--canvas); color: var(--ink-2); border: 1px solid var(--rule);
  border-radius: 12px; border-bottom-left-radius: 4px; box-shadow: var(--sh-sm); }

:focus-visible { outline: none; box-shadow: 0 0 0 3px rgba(48,111,168,.35); border-radius: 4px; }
input:focus, textarea:focus { border-color: var(--sapphire); box-shadow: 0 0 0 3px rgba(48,111,168,.15); }
```

Adapt the existing selectors in place (keep layout/grid rules; this task changes surfaces, spacing stays). Every remaining rule that sets a color must use a token from Task 6 — no new hex values outside this plan's blocks.

- [ ] **Step 4: Shelf translation** in `shelf.css`:

```css
#shelf-drawer { background: var(--canvas); box-shadow: var(--sh-lg); border-left: 1px solid var(--rule); }
.shelf-body { background: var(--band); }
.shelf-card { background: var(--canvas); border: 1px solid var(--rule); border-radius: var(--r-card);
  box-shadow: var(--sh-sm); transition: transform .18s ease, box-shadow .18s ease; }
.shelf-card:not(.locked):hover { transform: translateY(-3px); box-shadow: var(--sh-md); }
.shelf-card.on { background: var(--tint); border: 1.5px solid var(--sapphire); }
.sc-rec { font-family: var(--mono); font-size: 10.5px; font-weight: 500;
  text-transform: uppercase; letter-spacing: .14em; color: var(--sapphire); }
.price-tag { border-radius: var(--r-pill); font-family: var(--mono); }
.price-tag.t-free { background: var(--ok-t); color: var(--ok); border: 1px solid var(--ok-t); }
.price-tag.t-one  { background: var(--warn-t); color: var(--warn); border: 1px solid var(--warn-t); }
.price-tag.t-many { background: var(--err-t); color: var(--err); border: 1px solid var(--err-t); }
.int-chip { background: var(--tint); border: 1px solid var(--tint-2); color: var(--sapphire);
  border-radius: var(--r-pill); font-family: var(--mono); }
```

(The backdrop scrim `rgba(4,6,12,.55)` stays dark — conventional in both themes.)

- [ ] **Step 5: Manual verification checklist.** `.venv/Scripts/python -m studio`, then walk every surface:
1. Header: qmark + serif "qubit" + eyebrow + status chip with pulsing dot when live.
2. Chat: sapphire user bubbles / white assistant bubbles on band, links & `strong` legible.
3. Shelf: white drawer, band body, cards lift on hover, `.on` = tint + sapphire border, price pills green/amber/red.
4. Compose a real agent → build panel: stepper, components, log, wizard rows, personalize form, install gate — all legible; test a failing key row (`.kr-fail` state readable).
5. `?mode=architect` → blueprint cards with mono eyebrows.
6. DevTools → emulate `prefers-reduced-motion: reduce` → no pulse/lift animation.

- [ ] **Step 6: Commit**

```bash
git add studio/static/index.html studio/static/styles.css studio/static/shelf.css studio/static/app.js
git commit -m "feat(studio): QubitStudio reskin — nav, chat, cards, shelf, wizard"
```

---

### Task 8: B2 — "Your agent" panel + advanced demotion

**Files:**
- Modify: `studio/static/app.js` (renderAgentPanel + done-handler), `studio/static/shelf.js` (expose `shelfBuild`), `studio/static/index.html` (advanced disclosure), `studio/static/styles.css` (panel + details styles)

**Interfaces:**
- Consumes: `ev.studio` (Task 3/4), catalog via `/api/catalog`, `window.shelfSync` (Task 5), tokens (Task 6/7).
- Produces: `renderAgentPanel(studio)` (app.js), `window.shelfBuild(name?: string)` (shelf.js).

- [ ] **Step 1: shelf.js — expose the build path.** Inside the IIFE, after `buildAgent` is defined:

```js
  // Called by the Your-agent panel (app.js). Fills the drawer's name field if the
  // panel supplied one, then runs the same buildAgent() path.
  window.shelfBuild = function (name) {
    const f = sel('.shelf-foot .shelf-name');
    if (name && f && !f.value.trim()) f.value = name;
    buildAgent();
  };
```

- [ ] **Step 2: app.js — the panel.** Add after `renderBlueprint`:

```js
// ── "Your agent" panel (workshop mode) — the conversation's live mirror ──
let catalogCache = null;
async function getCatalog() {
  if (!catalogCache) {
    try { catalogCache = await (await fetch('/api/catalog')).json(); }
    catch { catalogCache = { baseline: { items: [] }, shelf: { items: [] } }; }
  }
  return catalogCache;
}

async function renderAgentPanel(studio) {
  const cat = await getCatalog();
  const byId = new Map((cat.shelf?.items || []).map((i) => [i.id, i]));
  const picks = (studio?.picks || []).map((id) => byId.get(id)).filter(Boolean);
  const ints = [...new Set(picks.flatMap((i) => i.requires || []))];
  const row = (name, tagLabel, locked) =>
    `<div class="ya-row ${locked ? 'locked' : ''}"><span>${name}</span><span class="ya-tag">${tagLabel}</span></div>`;
  $('#blueprint').innerHTML = DOMPurify.sanitize(`
    <div class="bp-card ya">
      <h3>Your agent</h3>
      ${(cat.baseline?.items || []).map((b) => row(b.name, '🔒 baseline', true)).join('')}
      ${picks.length
        ? picks.map((p) => row(p.name, p.cost?.label || '', false)).join('')
        : '<p class="ya-empty">Talk to the architect — your agent takes shape here.</p>'}
      <h3>Integrations</h3>
      <div class="ya-ints">${ints.length ? ints.map((i) => `<span class="int-chip">${i}</span>`).join('') : '<span class="ya-empty">none yet</span>'}</div>
      <label class="kr-field">Agent name
        <input id="ya-name" type="text" maxlength="60" value="${escAttr(studio?.name || '')}" placeholder="e.g. my-cos"></label>
      <button type="button" id="ya-build" ${picks.length ? '' : 'disabled'}>Build my agent ▶</button>
    </div>`);
  const build = $('#ya-build');
  if (build) build.addEventListener('click', () => {
    if (typeof window.shelfBuild === 'function') window.shelfBuild($('#ya-name').value.trim());
  });
}
```

Change the done branch in `send()`:

```js
      else if (ev.type === 'done') {
        if (ev.spec) renderBlueprint(ev.spec);
        if (ev.studio && typeof window.shelfSync === 'function') window.shelfSync(ev.studio);
        if (MODE === 'workshop') renderAgentPanel(ev.studio);
      }
```

And in `start()`, after `setStatus('ready')`: `if (MODE === 'workshop') renderAgentPanel(null);` (paints the empty state instead of "The blueprint fills in as you chat.").

- [ ] **Step 3: Advanced disclosure.** In `index.html`, wrap the four architect-path controls:

```html
  <details id="advanced">
    <summary class="brand-eyebrow">advanced</summary>
    <input id="loadfile" type="file" accept="application/json" hidden>
    <button id="load">Load spec.json</button>
    <button id="download" disabled>Download spec.json</button>
    <label id="evalstoggle" title="M3 evals fan out many nested claude runs and are slow. Off → grade 'validated'; on → 'verified'."><input id="runevals" type="checkbox"> evals</label>
    <button id="export" disabled>Export .plugin ▶</button>
  </details>
```

In app.js top-level (after MODE): `if (MODE === 'architect') { const a = $('#advanced'); if (a) a.open = true; }`

Styles (`styles.css`):

```css
#advanced { margin-left: auto; position: relative; }
#advanced summary { cursor: pointer; list-style: none; padding: 6px 10px; border-radius: var(--r-btn); }
#advanced summary:hover { color: var(--sapphire); }
#advanced[open] { display: flex; align-items: center; gap: 8px; }
.ya-row { display: flex; justify-content: space-between; align-items: center;
  padding: 8px 0; border-top: 1px solid var(--rule); font-family: var(--body); color: var(--ink); }
.ya-row .ya-tag { font-family: var(--mono); font-size: 10.5px; color: var(--ink-3); }
.ya-empty { color: var(--ink-4); font-size: 13.5px; }
#ya-build { background: var(--sapphire); color: #fff; border: none; width: 100%;
  padding: 10px 0; margin-top: 10px; }
#ya-build:disabled { background: var(--tint-2); color: var(--ink-4); }
```

- [ ] **Step 4: Manual verification.** `.venv/Scripts/python -m studio`:
1. Fresh load (workshop): right panel shows Your agent with the two locked baseline rows + empty-state line; header shows only shelf button + collapsed `advanced ▸`.
2. Interview until the agent recommends 2 skills → panel rows appear with price labels, integrations chips fill, name fills when agreed.
3. Press the panel's Build → same compose flow as the drawer (build panel streams).
4. `?mode=architect` → advanced starts open; Export path works (existing behavior).

- [ ] **Step 5: Backend suite + full integration run**

Run: `.venv/Scripts/python -m pytest studio/tests -q`
Expected: all pass, including `test_one_real_turn` and the Task 9 workshop smoke if already added.

- [ ] **Step 6: Commit**

```bash
git add studio/static/app.js studio/static/shelf.js studio/static/index.html studio/static/styles.css
git commit -m "feat(studio): Your-agent panel + advanced-path demotion"
```

---

### Task 9: Workshop real-turn smoke + QA close-out

**Files:**
- Test: `studio/tests/test_smoke_integration.py` (append)

- [ ] **Step 1: Add the workshop smoke** (append to `studio/tests/test_smoke_integration.py`)

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_one_real_workshop_turn(tmp_path):
    # The workshop prompt must make a REAL claude turn emit a parseable ```studio block.
    from studio.studio_extractor import extract_studio
    sp = write_system_prompt(tmp_path / "wp.md", mode="workshop")
    ids = {"crm", "briefing", "scheduling", "tasks", "intake", "drain"}
    s = ChatSession(session_id="33333333-3333-3333-3333-333333333333",
                    system_prompt_path=sp, catalog_ids=ids)
    events = [ev async for ev in s.send(
        "I get maybe 50 emails a day and track my todos in Linear. What should I add?")]
    assert any(e["type"] == "token" for e in events)
    done = events[-1]
    assert done["type"] == "done"
    assert done.get("studio") is not None, "no parseable ```studio block in a real turn"
    assert isinstance(done["studio"]["picks"], list)
```

- [ ] **Step 2: Run the full suite (integration included — needs live `claude`)**

Run: `.venv/Scripts/python -m pytest studio/tests -q`
Expected: all pass — 120 total (98 baseline + 9 T1 + 4 T2 + 4 T3 + 4 T4 + 1 T9)

- [ ] **Step 3: QA close-out (repo pipeline)**
1. `.venv/Scripts/python -m studio --doctor` — preflight green.
2. Placeholder-contract scan: `git diff main --stat` touches nothing under `chief-of-staff/`; `git diff main | grep -iE "lin_api|xoxb|AIza|@gmail|d885fd34|504fb62b"` → empty.
3. `/code-review` on the branch; address every Critical + Improvement; re-run tests.

- [ ] **Step 4: Commit**

```bash
git add studio/tests/test_smoke_integration.py
git commit -m "test(studio): real-turn workshop smoke — studio block parses from a live claude turn"
```

---

## Self-review notes

- Spec coverage: §3.1–3.4 → Tasks 6–7; §4.1 → Task 4; §4.2 → Task 2; §4.3 → Tasks 1+3; §4.4 → Task 5; §4.5 + §4.7 → Task 8; §4.6 → Task 5; §6 tests → Tasks 1–4, 9 + manual checklists in 5, 7, 8. Non-goals (vault path, persistence, r1-B, packaging) have no tasks — correct.
- Cut lines preserved: Tasks 1–5 = slice B1 (floor), 6–7 = slice A, 8 = slice B2 — each ends committed and testable.
- Type consistency: `extract_studio(text, catalog_ids)` (T1) = what `ChatSession._extract` calls (T3); `catalog_ids: set[str] | None` (T3) = what `new_session` passes (T4); `window.shelfSync(studio)` (T5) = what app.js calls (T5/T8); `window.shelfBuild(name)` (T8) consumed in T8 only.
