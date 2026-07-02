# The Dossier Journey — D0 Raw-Skills Packaging + D1 Living Document + D2 Connect Chapters + D3 Intake — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the workshop chat with a **dossier** — a single scrolling document the architect writes chapter by chapter, where the participant's answers fossilize as serif quotations — and make the destination real first: the composer emits a raw-skills **agent home** (`cd <dir> && claude`), so the finale's sign → bind → assemble → **first breath** → launch-card sequence runs on a real agent.

**Architecture:** The existing ` ```studio ` block gains an optional `chapter` field (title + phase + typed `blocks`); `dossier.js` renders beats (one per `claude -p` turn) into numbered chapters with live-edge staging, a blended writing line, inline choice cards, and a journey rail. The server accumulates beats on `ChatSession` and replays them on reload. D0 rewrites `composer.py`'s output tree to the lean-spec §5 agent-home form, which `POST /api/first-breath` later boots for one real greeting turn. Architect mode and the `?ui=chat` escape hatch keep the old skins on the same backend.

**Tech Stack:** FastAPI + vanilla JS (no build step), pytest, `claude` CLI subprocess, SapphireOS CSS tokens.

**Spec:** `docs/specs/2026-07-02-studio-dossier-journey-design.md` (shipshape-reviewed; read it first).
**Review:** `docs/reviews/shipshape-studio-dossier-journey-spec-2026-07-02.md`.
**Visual truth:** `docs/mockups/dossier-journey/v1b-dossier-journey.html` (journey) + `v1c-finale.html` (finale) — open both in a browser before touching `dossier.css`/`dossier.js`.
**D0 design authority:** `docs/specs/2026-07-02-workshop-lean-distribution-design.md` §5.

**Flagged deviations (deliberate, not omissions — each is a spec-vs-code truth found while grounding this plan):**

1. **Docs checkpoints ride each slice's landing PR** (spec §9), not tasks here — EXCEPT the substrate README/INSTALL rewrite (a D0 task, Task 4) and the FACILITATOR/SETUP + GUI install-copy updates (D1a tasks, Task 11), which the spec explicitly makes implementation work.
2. **Vault default vs compose ordering.** Spec §7.0 wants the vault at the resolved `vault_dir` with `<home>/vault/` default. Reality: `server.py:166-169` defaults to a SIBLING `dist/<slug>-vault`, and `composer.compose` scaffolds the vault in the *generate* stage (composer.py:165) BEFORE the *package* stage `rmtree`s + moves `final` (composer.py:180-182) — a naïve in-home vault would be destroyed by its own build. Resolution (Task 3): when `vault_dir` is the in-home form, compose scaffolds into `staging/vault` so the vault rides the move; external vaults (the onboarding second brain) scaffold in place, unchanged. Event order is preserved (`component: vault` still first).
3. **The reference-path invariant needs a rewrite pass.** Lean §5 left the mechanism open ("decided at plan time by reading what the SKILL.md files actually say"). Read: the substrate speaks in FOUR forms — `chief-of-staff/skills/<sk>/references/…` (briefing:110,126,141), `chief-of-staff/references/…` (briefing:203), bare `references/…` meaning *this* skill's dir (crm:40, drain:8), and the cross-skill shorthand `<sk>/references/…` (capture:164). Decision: the substrate keeps its layout; `copy_home` rewrites mentions in **copied SKILL.md files** to agent-home-root-relative via a deterministic regex pass (same class as `delucas()`), enforced by the invariant test (Task 1). (`capture` cross-references `crm`'s bare `references/…` in a way only correct in-place — harmless: `capture` is not on the shelf and its SKILL.md never ships.)
4. **Beat shape carries the user message.** Spec §4.1 defines a beat as `{prose, studio}`, but replay must restore the fossilized answers, which come from the participant's messages. Beats are `{user, prose, studio}` (Task 7); seed / `[studio event]` texts are suppressed at render time, `[card]` texts re-fossilize their answer part.
5. **`wireKeyRow` gains an optional 4th arg.** The spec names the seam `wireKeyRow(rowEl, integration, tree)` (§7.2); both consumers also need the pass/fail outcome (wizard install-gate, dossier launch-card chips), so the extraction is `wireKeyRow(rowEl, integration, tree, onResult)` — the named 3-arg seam preserved, the callback additive (Task 17).
6. **There is no explicit render throttle in app.js.** Spec §4.1/§11.4 says streaming "reuses the existing per-turn render throttle"; reality: `send()` re-renders on every SSE token event (app.js:134-137). The dossier does the same — same cost profile as the shipped chat, nothing new to build.
7. **`FACILITATOR.md` does not exist yet.** Task 11 creates it at the repo root (the lean-spec §3 layout position). Root `README.md` carries no `/plugin` wording (grep-verified), so the "SETUP fix" reduces to the GUI `installLineHtml` copy + a README launch-line touch-up.
8. **`v1c-finale.html` shows integration chips green** — already flagged stale in the spec header; the launch card here renders chips **pending** and fills them as connect completes (Tasks 16/18).
9. **"Byte-identical" architect mode** is enforced where the spec's tests enforce it: `build_system_prompt()` and its tests untouched, `?mode=architect` behavior unchanged. `index.html` does gain hidden, inert dossier nodes (exactly as the landed onboarding overlay did) — architect mode never activates them.
10. **The finale's "identity organ"** maps to compose's `assemble` stage event (the `delucas` owner/vault substitution that actually runs at build time) — the spec's phrase "the tweak pass's identity/vault substitution stage" names the same substitution class; the tweak endpoint itself is the optional post-build voice form and emits nothing during the ceremony. Caption says only what runs: "owner + vault substitutions applied".

## Global Constraints

- Branch: `feat/studio-dossier-journey` (this worktree). Commit per task. Any future parallel session re-creates the branch-collision risk — sync `main` first (spec §11.1).
- Repo is PUBLIC — no real keys/tokens/ids/emails/personal values in any commit. Placeholder-contract scan on every substrate-touching diff.
- `chief-of-staff/` and `agent-architect/` are NOT touched by D1–D3. **D0's scoped substrate cleanup (Task 4: `.claude-plugin/`, `marketplace.json`, README/INSTALL install wording) is the sole, deliberate exception** (spec §7.0/§8). Commit order: composer stops reading those files first (Tasks 1–3), then the removal commit (Task 4); revert path is the reverse order.
- Architect mode stays byte-identical: `build_system_prompt()` and its tests unchanged; `?mode=architect` renders the existing two-pane chat.
- **`?ui=chat` is the same-journey escape hatch** (spec §1): the current workshop chat skin stays reachable on the same backend (same session, same extractor, same endpoints) until dossier parity is proven at a dress rehearsal. Do not remove any chat-skin code path in this plan.
- No new deps, no build step — vanilla-JS IIFEs + CSS; stdlib-only server additions (existing FastAPI/pytest only).
- Fence discipline: `chapter` lives INSIDE the existing ` ```studio ` block — no new fence; the spec/json/studio disjointness rules are untouched.
- All pytest runs use the repo venv: `.venv/Scripts/python -m pytest studio/tests …` (Windows dev box; participant-facing code stays cross-platform — `pathlib`, forward-slash paths in generated files).
- **Tolerant parsing** (the standing rule): malformed `chapter` → `None` and picks/name/ready/ask still sync; unknown phase → chapter treated as absent; malformed `blocks` → `[]` with the chapter title still landing; unknown block `type` or unknown `key-field` `integration` → that block skipped, the rest render.
- Bracketed message conventions: `[studio event] …` (UI → agent, never displayed) and `[card] …` (answers, never displayed) — unchanged from onboarding-cards.
- Frontend tasks (no JS test runner in this repo): every task ends with `node --check` on each touched JS file + the backend suite green + a NAMED manual browser checklist (spec §10's per-slice checklists, distributed to the task that completes each slice).

---

# Slice D0 — raw-skills packaging (Tasks 1–4)

**What ships at this cut:** the composer emits an agent home (`.claude/skills/`, `.claude/agents/`, root `.mcp.json`, generated `CLAUDE.md`, in-home default vault) instead of a plugin; `install` becomes `cd <dir> && claude`; the substrate loses its vestigial plugin manifests and its docs teach the new launch. Participants type `cd dist/<name>-cos && claude` and talk to what they built. **No frontend files are touched** (the stale GUI install copy is the accepted D0→D1a gap, spec §7.0). ROADMAP item 3 closes in this slice's landing PR.

### Task 1: `composer.copy_home` — the agent-home tree + reference-path rewrite

**Files:**
- Modify: `studio/composer.py` (replace `copy_plugin` at lines 50–70; keep everything else)
- Test: `studio/tests/test_composer_copy.py` (rewrite), `studio/tests/test_composer_delucas.py` (rename call)

**Interfaces:**
- Consumes: `_COS` / `_ALL_SKILLS` (composer.py:11,51 — unchanged).
- Produces: `copy_home(tree: Path, picks: list[str]) -> None` (replaces `copy_plugin`) and `_rewrite_reference_paths(text: str, skill_id: str) -> str`. Task 3's `compose()` and Task 2's tests consume `copy_home`; the tree shape is: `.claude/skills/<pick>/SKILL.md`, `.claude/agents/context-gatherer.md`, root `.mcp.json`, root `references/`, `skills/<all>/references/`. NO `.claude-plugin/`, NO `marketplace.json`.

- [ ] **Step 1: Write the failing tests** — replace the body of `studio/tests/test_composer_copy.py` with:

```python
import re
from pathlib import Path
from studio import composer

def test_copy_home_agent_form(tmp_path):
    tree = tmp_path / "home"
    composer.copy_home(tree, ["crm"])
    # agent-home form (lean spec §5)
    assert (tree / ".claude/skills/crm/SKILL.md").exists()
    assert (tree / ".claude/agents/context-gatherer.md").exists()
    assert (tree / ".mcp.json").exists()
    assert (tree / "references/google-auth.md").exists()
    # a NON-picked skill's SKILL.md absent, but its references still ship (inert, hard-dep safe)
    assert not (tree / ".claude/skills/drain").exists()
    assert (tree / "skills/drain/references/linear-api.md").exists()
    # the plugin form is GONE
    assert not (tree / ".claude-plugin").exists()
    assert not (tree / "marketplace.json").exists()
    assert not (tree / "skills/crm/SKILL.md").exists()   # SKILL.md lives under .claude/ only

def test_reference_prefixes_rewritten_root_relative(tmp_path):
    tree = tmp_path / "home"
    composer.copy_home(tree, ["briefing"])
    text = (tree / ".claude/skills/briefing/SKILL.md").read_text(encoding="utf-8")
    assert "chief-of-staff/skills/" not in text
    assert "chief-of-staff/references/" not in text

def test_rewrite_reference_paths_forms():
    out = composer._rewrite_reference_paths(
        "read `references/crm-page-format.md` and `chief-of-staff/references/google-auth.md` "
        "and `chief-of-staff/skills/drain/references/linear-api.md` "
        "and `briefing/references/meeting-page.md` "
        "and follow `chief-of-staff/skills/crm/SKILL.md`.", "crm")
    assert "`skills/crm/references/crm-page-format.md`" in out
    assert "`references/google-auth.md`" in out
    assert "`skills/drain/references/linear-api.md`" in out
    assert "`skills/briefing/references/meeting-page.md`" in out
    assert "`.claude/skills/crm/SKILL.md`" in out

_REF_RE = re.compile(r"(?:[\w.\-]+/)*references/(?:[\w.\-]+/)*[\w.\-]+\.md")

def test_reference_path_invariant_all_shelf_picks(tmp_path):
    """The lean §5 invariant: every reference mentioned in a shipped SKILL.md resolves
    from the agent-home root."""
    picks = ["crm", "briefing", "scheduling", "tasks", "intake", "drain"]
    tree = tmp_path / "home"
    composer.copy_home(tree, picks)
    missing = []
    for sk in picks:
        text = (tree / ".claude/skills" / sk / "SKILL.md").read_text(encoding="utf-8")
        for ref in sorted(set(_REF_RE.findall(text))):
            if not (tree / ref).exists():
                missing.append(f"{sk}: {ref}")
    assert not missing, f"unresolvable reference paths from the agent-home root: {missing}"
```

And in `studio/tests/test_composer_delucas.py` line 11, change `composer.copy_plugin(tree, ["crm", "drain"])` to `composer.copy_home(tree, ["crm", "drain"])`.

- [ ] **Step 2: Run to verify failure**

Run: `.venv/Scripts/python -m pytest studio/tests/test_composer_copy.py studio/tests/test_composer_delucas.py -v`
Expected: FAIL — `AttributeError: module 'studio.composer' has no attribute 'copy_home'`.

- [ ] **Step 3: Implement.** In `studio/composer.py`, replace lines 50–70 (the `_SHELL` constant and `copy_plugin`) — currently:

```python
_SHELL = [".claude-plugin", ".mcp.json", "marketplace.json", "agents", "references"]
_ALL_SKILLS = ["briefing", "capture", "crm", "drain", "intake", "scheduling", "tasks"]

def copy_plugin(tree: Path, picks: list[str]) -> None:
    ...
```

with:

```python
_ALL_SKILLS = ["briefing", "capture", "crm", "drain", "intake", "scheduling", "tasks"]


def _rewrite_reference_paths(text: str, skill_id: str) -> str:
    """Rewrite path mentions in a copied SKILL.md to be AGENT-HOME-ROOT-relative (the
    lean spec §5 invariant). The substrate speaks in four forms (grep-verified):
    `chief-of-staff/skills/<sk>/references/…`, `chief-of-staff/references/…`, bare
    `references/…` meaning THIS skill's dir, and the cross-skill shorthand
    `<sk>/references/…`. In the home, substrate refs live under `skills/<sk>/references/`
    and shared refs under `references/`; SKILL.md bodies live under `.claude/skills/`.
    Deterministic string pass — same class as delucas(). Order matters: the bare form
    first (the lookbehind keeps it off the prefixed forms), prefixes after."""
    # 1. bare `references/…` (start of a path) → this skill's substrate dir
    text = re.sub(r"(?<![\w/\-.])references/", f"skills/{skill_id}/references/", text)
    # 2. cross-skill shorthand `briefing/references/…` → `skills/briefing/references/…`
    for sk in _ALL_SKILLS:
        text = re.sub(rf"(?<![\w/\-.]){sk}/references/", f"skills/{sk}/references/", text)
    # 3. full substrate prefixes drop their chief-of-staff/ root
    text = text.replace("chief-of-staff/skills/", "skills/")
    text = text.replace("chief-of-staff/references/", "references/")
    # 4. cross-skill SKILL.md mentions live under .claude/ in the home
    text = re.sub(r"(?<![\w/\-.])skills/([\w\-]+)/SKILL\.md", r".claude/skills/\1/SKILL.md", text)
    return text


def copy_home(tree: Path, picks: list[str]) -> None:
    """Copy the substrate into an AGENT HOME (lean spec §5), not a plugin: picked
    SKILL.md under .claude/skills/, agents under .claude/agents/, .mcp.json + shared
    references/ at the root. EVERY skill's references/ ships (inert markdown, kills the
    hard-dep class) at its unchanged `skills/<sk>/references/` location; only PICKED
    skills' SKILL.md ship (what Claude actually triggers on), reference mentions
    rewritten home-root-relative."""
    tree = Path(tree)
    (tree / ".claude" / "skills").mkdir(parents=True, exist_ok=True)
    shutil.copy2(_COS / ".mcp.json", tree / ".mcp.json")
    shutil.copytree(_COS / "agents", tree / ".claude" / "agents")
    shutil.copytree(_COS / "references", tree / "references")
    for sk in _ALL_SKILLS:
        refs = _COS / "skills" / sk / "references"
        if refs.exists():
            shutil.copytree(refs, tree / "skills" / sk / "references")
    for sk in picks:
        dst = tree / ".claude" / "skills" / sk
        dst.mkdir(parents=True, exist_ok=True)
        text = (_COS / "skills" / sk / "SKILL.md").read_text(encoding="utf-8")
        (dst / "SKILL.md").write_text(_rewrite_reference_paths(text, sk), encoding="utf-8")
```

Then update the one internal caller: composer.py:167 `copy_plugin(staging, picks)` → `copy_home(staging, picks)`.

NOTE: `compose()` and `assemble_manifests` still write/edit `plugin.json`/`marketplace.json` paths that no longer exist in the tree — `test_composer_package.py` will FAIL after this step. That is expected mid-slice; Tasks 2–3 rewrite them. Run only the two test files below at this step.

- [ ] **Step 4: Run to verify pass**

Run: `.venv/Scripts/python -m pytest studio/tests/test_composer_copy.py studio/tests/test_composer_delucas.py -v`
Expected: all pass. If `test_reference_path_invariant_all_shelf_picks` lists a miss, fix `_rewrite_reference_paths` (add the missing form) — NEVER edit substrate SKILL.md content (outside D0's cleanup scope).

- [ ] **Step 5: Commit**

```bash
git add studio/composer.py studio/tests/test_composer_copy.py studio/tests/test_composer_delucas.py
git commit -m "feat(studio): copy_home — agent-home tree + home-root reference rewrite (lean §5)"
```

---

### Task 2: Generated `CLAUDE.md` + manifest assembly without plugin manifests

**Files:**
- Modify: `studio/composer.py` (replace `assemble_manifests` at lines 119–143; add `write_claude_md`)
- Test: `studio/tests/test_composer_package.py` (rewrite)

**Interfaces:**
- Produces: `write_claude_md(tree: Path, owner_name: str, vault_dir: Path, picks: list[str]) -> None` — deterministic per lean §5: identity, owner name, resolved vault path (forward-slash), picked-skill roster, **nothing more** (no personalization claim — review F10). And `assemble_manifests(tree: Path, integrations: set[str]) -> None` — ONLY the `.mcp.json` discord-trim survives. Task 3's `compose()` consumes both.

- [ ] **Step 1: Write the failing tests** — replace the body of `studio/tests/test_composer_package.py` with:

```python
import asyncio, json
from pathlib import Path
from studio import composer

def _run(agen):
    async def drain():
        return [ev async for ev in agen]
    return asyncio.run(drain())

def test_claude_md_carries_exactly_the_lean_fields(tmp_path):
    tree = tmp_path / "home"; tree.mkdir()
    composer.write_claude_md(tree, "Sam Rivera", tmp_path / "vault", ["crm", "tasks"])
    text = (tree / "CLAUDE.md").read_text(encoding="utf-8")
    assert "sam-rivera-cos" in text                       # identity
    assert "Sam Rivera" in text                           # owner name
    assert str(tmp_path / "vault").replace("\\", "/") in text   # resolved vault path
    assert "crm" in text and "tasks" in text              # picked-skill roster
    assert "drain" not in text                            # roster is the PICKS, not the shelf
    assert "personaliz" not in text.lower()               # no personalization claim (review F10)

def test_assemble_trims_mcp_when_no_discord(tmp_path):
    tree = tmp_path / "home"
    composer.copy_home(tree, ["crm"])
    composer.assemble_manifests(tree, set())              # crm needs no discord
    mcp = json.loads((tree / ".mcp.json").read_text(encoding="utf-8"))
    assert mcp.get("mcpServers", {}) == {}

def test_assemble_keeps_discord_when_needed(tmp_path):
    tree = tmp_path / "home"
    composer.copy_home(tree, ["drain"])
    composer.assemble_manifests(tree, {"discord", "linear", "scheduler"})
    mcp = json.loads((tree / ".mcp.json").read_text(encoding="utf-8"))
    assert "discord" in mcp["mcpServers"]

def test_assemble_writes_no_plugin_manifests(tmp_path):
    tree = tmp_path / "home"
    composer.copy_home(tree, ["crm"])
    composer.assemble_manifests(tree, set())
    assert not (tree / ".claude-plugin").exists()
    assert not (tree / "marketplace.json").exists()
```

(The old `test_compose_streams_done_with_installable_tree` moves to Task 3's rewrite — `compose()` is still plugin-form until then.)

- [ ] **Step 2: Run to verify failure**

Run: `.venv/Scripts/python -m pytest studio/tests/test_composer_package.py -v`
Expected: FAIL — `AttributeError: ... no attribute 'write_claude_md'` / `TypeError: assemble_manifests() takes 4 positional arguments` variants.

- [ ] **Step 3: Implement.** In `studio/composer.py`, replace `assemble_manifests` (lines 119–143, the version that `_edit_json`s `.claude-plugin/plugin.json` and `marketplace.json`) with:

```python
def write_claude_md(tree: Path, owner_name: str, vault_dir: Path, picks: list[str]) -> None:
    """The generated agent-home CLAUDE.md — deterministic per lean spec §5: identity,
    owner name, resolved vault path, picked-skill roster, and NOTHING more. No
    personalization claim — personalization lives in the tweak pass, not this file
    (review F10). Absorbs plugin.json's identity role; greets with identity so a
    correct `cd <home> && claude` launch is self-confirming."""
    cat = _catalog()
    by_id = {it["id"]: it for it in cat["shelf"]["items"]}
    slug = f"{_slug(owner_name)}-cos"
    roster = "\n".join(
        f"- **{p}** ({by_id[p]['name']}): {by_id[p]['what']}"
        for p in picks if p in by_id) or "- (baseline only)"
    vault = str(vault_dir).replace("\\", "/")
    (tree / "CLAUDE.md").write_text(f"""# {slug}

You are **{slug}** — {owner_name}'s personal chief of staff, composed at the QubitStudio
workshop. This folder is your home: your skills live in `.claude/skills/`, their shared
reference material under `skills/` and `references/`.

## Owner

- {owner_name}

## Your memory (the vault)

- Your wiki-brain vault lives at: `{vault}`
- People pages, meeting pages, and your `meta/` self-layer (personality, memories,
  lessons) live there. Read it before you act; write what you learn back.

## Your skills

{roster}
""", encoding="utf-8")


def assemble_manifests(tree: Path, integrations: set[str]) -> None:
    """Agent-home form (lean §5): no plugin.json / marketplace.json — the generated
    CLAUDE.md absorbs their identity role. Only the .mcp.json discord-trim behaviour
    survives the rewrite: keep discord only if a Discord-needing integration was picked."""
    mcp_path = tree / ".mcp.json"
    if mcp_path.exists():
        def _mcp(mcp):
            if "discord" not in integrations:
                mcp["mcpServers"] = {k: v for k, v in mcp.get("mcpServers", {}).items()
                                     if k != "discord"}
        _edit_json(mcp_path, _mcp)
```

Then update the internal caller composer.py:174 `assemble_manifests(staging, owner_name, picks, res.integrations)` → (temporarily, until Task 3's full rewrite) `assemble_manifests(staging, res.integrations)`.

- [ ] **Step 4: Run to verify pass**

Run: `.venv/Scripts/python -m pytest studio/tests/test_composer_package.py studio/tests/test_composer_copy.py -v`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add studio/composer.py studio/tests/test_composer_package.py
git commit -m "feat(studio): generated agent-home CLAUDE.md (lean §5 fields) + manifest assembly drops plugin/marketplace"
```

---

### Task 3: `compose()` — shell event, `cd` install field, in-home default vault

**Files:**
- Modify: `studio/composer.py` (the `compose` async generator, lines 148–190), `studio/server.py` (`compose_endpoint`, lines 165–169)
- Test: `studio/tests/test_composer_package.py` (append), `studio/tests/test_server.py` (append)

**Interfaces:**
- Consumes: Task 1 `copy_home`, Task 2 `write_claude_md` / `assemble_manifests(tree, integrations)`.
- Produces: `compose()`'s event stream gains `{"type": "component", "key": "shell", "status": "ok"}` (the finale's shell organ, spec §7.0/§6.3); `done.install == f"cd {final} && claude"`; an in-home `vault_dir` scaffolds into staging and rides the package move (flagged deviation 2). Server default vault becomes `dist/<slug>-cos/vault`. Tasks 14/16 consume `done.plugin_path`/`done.install`/`component` events.

- [ ] **Step 1: Write the failing tests.** Append to `studio/tests/test_composer_package.py`:

```python
# --- D0 compose stream (dossier spec §7.0 / lean §5) ---

def test_compose_emits_shell_event_and_cd_install(tmp_path):
    evs = _run(composer.compose(["crm"], "Sam Rivera", tmp_path / "dist", tmp_path / "vault"))
    keys = [e.get("key") for e in evs if e.get("type") == "component"]
    assert keys[0] == "vault" and "shell" in keys and "skill:crm" in keys
    done = evs[-1]
    assert done["type"] == "done"
    assert done["install"] == f"cd {done['plugin_path']} && claude"
    assert "/plugin" not in done["install"]
    out = Path(done["plugin_path"])
    assert (out / ".claude/skills/crm/SKILL.md").exists()
    assert (out / "CLAUDE.md").exists()
    assert not (out / ".claude-plugin").exists() and not (out / "marketplace.json").exists()

def test_compose_in_home_vault_survives_package(tmp_path):
    # The <home>/vault/ default (spec §7.0): scaffolded into staging, rides the move —
    # NOT destroyed by the package step's rmtree of a pre-existing final tree.
    home_vault = tmp_path / "dist" / "sam-rivera-cos" / "vault"
    (tmp_path / "dist" / "sam-rivera-cos").mkdir(parents=True)   # simulate a rebuild over an old home
    evs = _run(composer.compose(["crm"], "Sam Rivera", tmp_path / "dist", home_vault))
    done = evs[-1]
    assert done["type"] == "done"
    assert done["vault_path"] == str(home_vault)
    assert (home_vault / "meta/chief-of-staff/personality.md").exists()
    text = (home_vault / "meta/chief-of-staff/personality.md").read_text(encoding="utf-8")
    assert "Sam Rivera" in text

def test_compose_external_vault_unchanged(tmp_path):
    # The onboarding second brain stays an in-place scaffold outside the home.
    sb = tmp_path / "second-brain"
    evs = _run(composer.compose(["crm"], "Sam Rivera", tmp_path / "dist", sb))
    assert evs[-1]["type"] == "done"
    assert (sb / "meta/chief-of-staff/personality.md").exists()
    assert not (Path(evs[-1]["plugin_path"]) / "vault").exists()
```

Append to `studio/tests/test_server.py` (below `test_compose_uses_second_brain_vault`):

```python
def test_compose_default_vault_is_in_home(monkeypatch, tmp_path):
    # No completed onboarding → the default vault is INSIDE the agent home (lean §5),
    # not the old dist/<slug>-vault sibling.
    _ob(monkeypatch, tmp_path)
    seen = {}
    async def fake_compose(picks, name, outdir, vault_dir):
        seen["vault"] = Path(vault_dir)
        yield {"type": "done", "grade": "composed", "plugin_path": "x", "vault_path": str(vault_dir)}
    monkeypatch.setattr(server._composer, "compose", fake_compose)
    c = TestClient(server.app)
    with c.stream("POST", "/api/compose", json={"picks": ["crm"], "name": "my cos"}) as r:
        "".join(r.iter_text())
    assert seen["vault"] == server._composer._REPO / "dist" / "my-cos-cos" / "vault"
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/Scripts/python -m pytest studio/tests/test_composer_package.py studio/tests/test_server.py -v`
Expected: new tests FAIL (`KeyError: 'install'` / old `/plugin marketplace add` form / old sibling default); existing pass.

- [ ] **Step 3: Implement.** In `studio/composer.py`, replace the body of `compose()` (lines 148–190) with:

```python
async def compose(picks, owner_name, outdir, vault_dir) -> AsyncIterator[dict]:
    outdir, vault_dir = Path(outdir), Path(vault_dir)
    try:
        yield _stage("preflight", "running")
        res = resolve(picks)
        for w in res.warnings:
            yield {"type": "log", "text": "⚠ " + w}
        yield _stage("preflight", "ok")

        base = _slug(owner_name)
        slug = f"{base}-cos"
        final = outdir / slug
        staging = _HERE / ".cache" / "compose" / slug
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
        staging.mkdir(parents=True, exist_ok=True)

        yield _stage("generate", "running")
        # An in-home vault (the <home>/vault/ default, lean §5) must ride the
        # staging→final move — scaffolding it at its final path would be destroyed by
        # the package step's rmtree below. External vaults (the onboarding second
        # brain) scaffold in place, exactly as before.
        in_home = vault_dir.resolve() == (final / "vault").resolve()
        scaffold_vault(staging / "vault" if in_home else vault_dir, owner_name, picks)
        yield {"type": "component", "key": "vault", "status": "ok"}
        copy_home(staging, picks)
        yield {"type": "component", "key": "shell", "status": "ok"}
        for sk in picks:
            yield {"type": "component", "key": f"skill:{sk}", "status": "ok"}
        yield _stage("generate", "ok")

        yield _stage("assemble", "running")
        delucas(staging, owner_name, vault_dir)
        write_claude_md(staging, owner_name, vault_dir, picks)
        assemble_manifests(staging, res.integrations)
        yield _stage("assemble", "ok")

        yield _stage("package", "running")
        outdir.mkdir(parents=True, exist_ok=True)
        if final.exists():
            # a rebuild rmtree's the home INCLUDING its .env — documented consequence (spec §6.1)
            shutil.rmtree(final, ignore_errors=True)
        shutil.move(str(staging), str(final))
        yield _stage("package", "ok")
        yield {"type": "done", "grade": "composed", "plugin_path": str(final),
               "vault_path": str(vault_dir), "integrations": sorted(res.integrations),
               "install": f"cd {final} && claude"}
    except UnknownPickError as e:
        yield {"type": "error", "stage": "preflight", "message": str(e)}
    except Exception as e:  # filesystem etc. — never leave a half-agent silently
        yield {"type": "error", "stage": "package", "message": f"{type(e).__name__}: {e}"}
```

In `studio/server.py` `compose_endpoint`, replace the vault default (lines 165–169) — currently:

```python
        state = _onboarding.load_state()
        if state.get("completed_at") and state.get("second_brain"):
            vault = Path(state["second_brain"])       # spec §5.3: the second brain IS the vault
        else:
            vault = _composer._REPO / "dist" / f"{slug}-vault"
```

with:

```python
        state = _onboarding.load_state()
        if state.get("completed_at") and state.get("second_brain"):
            vault = Path(state["second_brain"])       # onboarding: the second brain IS the vault
        else:
            vault = _composer._REPO / "dist" / f"{slug}-cos" / "vault"   # lean §5: <home>/vault/ default
```

- [ ] **Step 4: Run to verify pass, then the whole backend suite**

Run: `.venv/Scripts/python -m pytest studio/tests/test_composer_package.py studio/tests/test_server.py -v` → all pass.
Run: `.venv/Scripts/python -m pytest studio/tests -q -m "not integration"` → all pass (the composer is now fully off the plugin manifests — nothing in `studio/` reads them any more).

- [ ] **Step 5: Commit**

```bash
git add studio/composer.py studio/server.py studio/tests/test_composer_package.py studio/tests/test_server.py
git commit -m "feat(studio): compose emits an agent home — shell event, cd install line, in-home default vault"
```

---

### Task 4: Substrate cleanup — remove plugin manifests, rewrite README/INSTALL (D0 docs checkpoint)

**Files:**
- Delete: `chief-of-staff/.claude-plugin/plugin.json`, `chief-of-staff/marketplace.json`
- Modify: `chief-of-staff/INSTALL.md` (install section), `chief-of-staff/README.md` (4 plugin-wording lines)

This is D0's **sole substrate exception** (spec §7.0/§8) and MUST land as a separate commit AFTER Tasks 1–3 (the composer no longer reads those files — proven by the green suite in Task 3 Step 4). Revert path: revert this commit first, then the composer commits (the reverse order).

- [ ] **Step 1: Confirm nothing reads the manifests any more**

```bash
grep -rn "claude-plugin\|marketplace" studio --include="*.py"
```
Expected: no code hits (comments/docstrings only, if any). If a code hit appears, STOP — a Task 1–3 step was missed.

- [ ] **Step 2: Remove the manifests**

```bash
git rm -r chief-of-staff/.claude-plugin chief-of-staff/marketplace.json
```

- [ ] **Step 3: Rewrite `chief-of-staff/INSTALL.md`.** Replace the section from the heading `## Install (from this repo's marketplace)` down to (not including) `## Required environment variables` — it currently teaches `claude "/plugin install chief-of-staff@consulting-agents"` and `claude "/plugin marketplace add D:\Claude\Consulting-Agents"` + "Then restart Claude Code." — with this exact section:

~~~markdown
## Install (composed agent home)

This substrate is not installed directly — the QubitStudio studio **composes** it into a
personal agent home under `dist/<name>-cos/` (run `python -m studio` and follow the
journey). The composed agent is a raw-skills directory: `.claude/skills/`, a generated
`CLAUDE.md` identity, and a root `.mcp.json`. To launch it:

```powershell
cd dist/<name>-cos
claude
```

Your agent lives in that folder — skills trigger when Claude Code runs there. No
marketplace, no `/plugin install`, no restart step.
~~~

- [ ] **Step 4: Rewrite the four plugin-wording lines in `chief-of-staff/README.md`** (line numbers as read for this plan):
  - line 92: `The only server the plugin runs itself is **Discord**, configured with the env vars below.` → `The only server the agent runs itself is **Discord**, configured with the env vars below.`
  - line 110: `4. The plugin exposes the bot's tools as` … → `4. The root .mcp.json exposes the bot's tools as` … (rest of the line unchanged)
  - lines 151–157: replace the `### 3. Install the plugin` block (heading + the `/plugin install chief-of-staff@consulting-agents` fence + the marketplace/restart sentence) with:

~~~markdown
### 3. Launch your composed agent

```powershell
cd dist/<name>-cos
claude
```

Your agent lives in that folder — launch Claude Code there and the skills load.
~~~

  - line 214: `This plugin persists facts under` … → `The agent persists facts under` … (rest unchanged)

- [ ] **Step 5: Placeholder-contract scan + suite**

```bash
git diff main -- chief-of-staff | grep -iE "lin_api|xoxb|AIza|@gmail|d885fd34|504fb62b|ikigaiventures"
```
Expected: empty output. Then run: `.venv/Scripts/python -m pytest studio/tests -q -m "not integration"` → all pass.

- [ ] **Step 6: Commit (the removal commit, after the composer commits — spec §7.0 commit order)**

```bash
git add chief-of-staff
git commit -m "chore(substrate): drop vestigial plugin manifests + plugin-install wording — raw-skills form (D0 docs checkpoint)"
```

**CUT LINE — D0 ships here.** ROADMAP item 3 → shipped + CHANGELOG updates ride the landing PR (spec §9). The GUI still shows the old-style install copy in `installLineHtml` — accepted and flagged (spec §7.0); Task 11 (D1a owns that surface) fixes it.

---

# Slice D1a — the dossier shell (Tasks 5–11)

**What ships at this cut:** workshop mode renders as the dossier — numbered chapters with live-edge staging, fossilized serif answers, inline choice cards + the writing line (baton rules intact), the journey rail, picks-diff skill cards, brass error lines, and beats replay on reload — with `?ui=chat` as the same-backend escape hatch and the C3 onboarding walk mounted as a floating dock until D3. Building still happens through the kept shelf drawer (the signature close is D1c). `ready: true` is accepted and ignored by the renderer until Task 15. ROADMAP item 2 gets a status note in the landing PR.

### Task 5: Extractor — `chapter` field + typed-blocks validation

**Files:**
- Modify: `studio/studio_extractor.py`
- Test: `studio/tests/test_studio_extractor.py` (append + update equality asserts)

**Interfaces:**
- Produces: `extract_studio(...)` returns a FIFTH key `"chapter": dict | None`. Validated shape: `{"title": str (stripped, ≤80), "phase": str (one of the fixed 7), "blocks": list[dict]}` — `blocks` always a list (possibly empty), each entry one of the closed vocabulary with per-type required fields. Tasks 7 (beats/SSE), 9 (renderer), 18 (blocks renderer) rely on this exact shape. D1a ships with `blocks` accepted-and-ignored by the renderer (spec §3.2) so D2 is purely additive.

- [ ] **Step 1: Write the failing tests** (append to `studio/tests/test_studio_extractor.py`)

```python
# --- chapter field (dossier spec §3.1/§3.2) ---

def test_valid_chapter_extracted():
    out = extract_studio(_block(
        '{"picks": ["tasks"], "chapter": {"title": "Taming the inbox", "phase": "skills"}}'), IDS)
    assert out["chapter"] == {"title": "Taming the inbox", "phase": "skills", "blocks": []}

def test_chapter_absent_is_none():
    assert extract_studio(_block('{"picks": []}'), IDS)["chapter"] is None

def test_chapter_malformed_none_picks_and_ask_survive():
    # the standing tolerant rule: a broken chapter must never kill the picks/ask sync
    out = extract_studio(_block(
        '{"picks": ["crm"], "ask": {"title": "t", "options": [{"label": "x"}, {"label": "y"}]},'
        ' "chapter": "skills"}'), IDS)
    assert out["chapter"] is None and out["picks"] == ["crm"] and out["ask"] is not None

def test_chapter_unknown_phase_treated_absent():
    out = extract_studio(_block(
        '{"picks": [], "chapter": {"title": "t", "phase": "epilogue"}}'), IDS)
    assert out["chapter"] is None

def test_chapter_title_over_80_dropped():
    out = extract_studio(_block(
        '{"picks": [], "chapter": {"title": "' + "x" * 81 + '", "phase": "skills"}}'), IDS)
    assert out["chapter"] is None

def test_chapter_blocks_valid_vocabulary():
    out = extract_studio(_block(
        '{"picks": ["tasks"], "chapter": {"title": "Connect Linear", "phase": "connect",'
        ' "blocks": ['
        '{"type": "step", "n": 1, "text": "Open linear.app"},'
        '{"type": "key-field", "integration": "linear", "label": "Paste your key"},'
        '{"type": "checklist", "items": ["Key created", "Smoke green"]},'
        '{"type": "note", "text": "Keys stay local"},'
        '{"type": "skill-card", "id": "tasks"}]}}'), IDS)
    types = [b["type"] for b in out["chapter"]["blocks"]]
    assert types == ["step", "key-field", "checklist", "note", "skill-card"]
    assert out["chapter"]["blocks"][0] == {"type": "step", "n": 1, "text": "Open linear.app"}
    assert out["chapter"]["blocks"][1]["integration"] == "linear"

def test_chapter_unknown_block_type_skipped_rest_render():
    out = extract_studio(_block(
        '{"picks": [], "chapter": {"title": "t", "phase": "connect", "blocks": ['
        '{"type": "hologram", "text": "x"}, {"type": "note", "text": "kept"}]}}'), IDS)
    assert [b["type"] for b in out["chapter"]["blocks"]] == ["note"]

def test_chapter_malformed_blocks_empty_title_lands():
    out = extract_studio(_block(
        '{"picks": [], "chapter": {"title": "t", "phase": "build", "blocks": "steps"}}'), IDS)
    assert out["chapter"] == {"title": "t", "phase": "build", "blocks": []}

def test_step_without_text_skipped():
    out = extract_studio(_block(
        '{"picks": [], "chapter": {"title": "t", "phase": "build", "blocks": ['
        '{"type": "step", "n": 1}, {"type": "step", "n": 2, "text": "real"}]}}'), IDS)
    assert [b["text"] for b in out["chapter"]["blocks"]] == ["real"]

def test_key_field_unknown_integration_skipped():
    out = extract_studio(_block(
        '{"picks": [], "chapter": {"title": "t", "phase": "connect", "blocks": ['
        '{"type": "key-field", "integration": "fax-machine"},'
        '{"type": "key-field", "integration": "linear"}]}}'), IDS)
    assert [b["integration"] for b in out["chapter"]["blocks"]] == ["linear"]

def test_skill_card_unknown_id_skipped():
    out = extract_studio(_block(
        '{"picks": [], "chapter": {"title": "t", "phase": "build", "blocks": ['
        '{"type": "skill-card", "id": "hallucinated"}]}}'), IDS)
    assert out["chapter"]["blocks"] == []
```

- [ ] **Step 2: Update the existing full-dict equality asserts** — `test_extracts_valid_block` (test_studio_extractor.py:10) becomes:

```python
    assert out == {"picks": ["crm", "briefing"], "name": "my-cos", "ready": False,
                   "ask": None, "chapter": None}
```

Run the suite to find any other full-dict equality assert and give it `"chapter": None` the same way.

- [ ] **Step 3: Run to verify failure**

Run: `.venv/Scripts/python -m pytest studio/tests/test_studio_extractor.py -v`
Expected: new tests FAIL (`KeyError: 'chapter'`); the updated equality assert FAILs until implementation.

- [ ] **Step 4: Implement.** In `studio/studio_extractor.py`, add below `_valid_ask` (after line 44):

```python
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
```

And change `extract_studio`'s final return (lines 62–63) to:

```python
    return {"picks": picks, "name": name, "ready": bool(obj.get("ready")),
            "ask": _valid_ask(obj.get("ask")),
            "chapter": _valid_chapter(obj.get("chapter"), catalog_ids)}
```

- [ ] **Step 5: Run to verify pass**

Run: `.venv/Scripts/python -m pytest studio/tests/test_studio_extractor.py studio/tests/test_chat_session.py -v`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add studio/studio_extractor.py studio/tests/test_studio_extractor.py
git commit -m "feat(studio): chapter field in the studio block — title/phase + typed blocks, tolerant"
```

---

### Task 6: Workshop prompt — the "writing the page" contract

**Files:**
- Modify: `studio/system_prompt.py`
- Test: `studio/tests/test_system_prompt.py` (append)

**Interfaces:**
- Consumes: `build_workshop_prompt(catalog_path=None, participant=None, onboarding=False)` (system_prompt.py:222).
- Produces: the workshop prompt gains a `_CHAPTER_CONTRACT` section (spec §3.3) — always present in workshop mode, never in architect mode. No signature change. The `?ui=chat` skin shares this prompt (same backend); the chat skin simply never renders `chapter`.

- [ ] **Step 1: Write the failing tests** (append to `studio/tests/test_system_prompt.py`)

```python
# --- dossier spec §3.3: the chapter contract ---
_PHASE_SET = ("welcome", "baseline", "skills", "personalize", "name", "build", "connect")

def test_workshop_chapter_contract_present():
    p = build_workshop_prompt()
    assert '"chapter"' in p
    for phase in _PHASE_SET:
        assert phase in p
    assert "REUSE the current title" in p
    assert "Do NOT restate the chapter title" in p

def test_chapter_contract_in_every_workshop_variant():
    for kw in ({}, {"onboarding": True}, {"participant": _P}):
        assert '"chapter"' in build_workshop_prompt(**kw)

def test_architect_has_no_chapter_contract():
    from studio.system_prompt import build_system_prompt
    assert '"chapter"' not in build_system_prompt()

def test_architect_mode_byte_identical_after_chapter(tmp_path):
    from studio.system_prompt import write_system_prompt, build_system_prompt
    out = write_system_prompt(tmp_path / "sp.md")
    assert out.read_text(encoding="utf-8") == build_system_prompt()
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/Scripts/python -m pytest studio/tests/test_system_prompt.py -v`
Expected: the two new workshop tests FAIL (`assert '"chapter"' in p` → False); the architect tests pass.

- [ ] **Step 3: Implement.** In `studio/system_prompt.py`, add below `_ASK_CONTRACT` (after line 181):

```python
_CHAPTER_CONTRACT = """
# Writing the page (the dossier)

- You are writing a DOCUMENT, not chatting. The participant sees your words as the body
  text of a numbered chapter on a single scrolling page about the agent they're building.
- EVERY turn, include a "chapter" object in the studio block (same fence):
  "chapter": { "title": "Taming the inbox", "phase": "skills" }
- `title` = the section you are writing. REUSE the current title to continue the open
  section; give a NEW title to open a new one. Open a new chapter when the topic
  genuinely turns (a new skill area, naming, building); continue for follow-ups and
  acknowledgements. Keep titles short and human ("Taming the inbox", never "Skills
  recommendation phase") — at most 80 characters.
- `phase` = where the journey is, exactly one of:
  welcome | baseline | skills | personalize | name | build | connect
- Do NOT restate the chapter title in your prose — the page draws the heading itself.
"""
```

And in `build_workshop_prompt` (lines 222–235), insert the new part after `_ASK_CONTRACT`:

```python
    parts.append(_WORKSHOP_CONTRACT)
    parts.append(_ASK_CONTRACT)
    parts.append(_CHAPTER_CONTRACT)
    if onboarding:
        parts.append(_ONBOARDING_CONTRACT)
```

- [ ] **Step 4: Run to verify pass**

Run: `.venv/Scripts/python -m pytest studio/tests/test_system_prompt.py -v`
Expected: all pass (the landed brevity/style rules stay untouched — they are what makes chapters readable).

- [ ] **Step 5: Commit**

```bash
git add studio/system_prompt.py studio/tests/test_system_prompt.py
git commit -m "feat(studio): workshop prompt writes the page — chapter contract, fixed phase set"
```

---

### Task 7: Beats — `ChatSession.beats`, `GET /api/session/{id}/beats`, SSE chapter passthrough

**Files:**
- Modify: `studio/chat_session.py`, `studio/server.py`
- Test: `studio/tests/test_chat_session.py` (append), `studio/tests/test_server.py` (append), `studio/tests/test_smoke_integration.py` (append)

**Interfaces:**
- Produces: `ChatSession.beats: list[dict]` — one entry per completed turn, appended at `done`: `{"user": str, "prose": str (raw, fences included), "studio": dict | None (the post-extract snapshot)}`. `GET /api/session/{session_id}/beats -> {"session_id", "beats"}`, unknown id → 404. The `done` SSE event already carries `chapter` transparently (it rides `session.studio`); a test pins that. Task 9's `tryReplay` consumes the endpoint; Task 10's `startWorkshopSession` stores the session id.

- [ ] **Step 1: Write the failing tests.** Append to `studio/tests/test_chat_session.py`:

```python
# --- beats accumulation (dossier spec §4.1: reload survival) ---
import asyncio as _aio
import json as _json


class _StreamProc:
    """Fake claude proc: replays canned stream-json lines, then a result event."""
    returncode = 0
    stderr = None
    def __init__(self, lines):
        self._lines = list(lines)
        self.stdout = self
    def __aiter__(self):
        return self
    async def __anext__(self):
        if not self._lines:
            raise StopAsyncIteration
        return self._lines.pop(0)
    async def wait(self):
        return 0


def _turn_lines(text):
    msg = {"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}}
    return [(_json.dumps(msg) + "\n").encode(), (_json.dumps({"type": "result"}) + "\n").encode()]


async def test_beats_accumulate_per_turn(tmp_path, monkeypatch):
    turns = [
        _turn_lines('Welcome.\n```studio\n{"picks": ["crm"], '
                    '"chapter": {"title": "Welcome", "phase": "welcome"}}\n```'),
        _turn_lines('Onward.\n```studio\n{"picks": ["crm", "tasks"]}\n```'),
    ]
    async def fake_exec(*argv, **kw):
        return _StreamProc(turns.pop(0))
    monkeypatch.setattr(_aio, "create_subprocess_exec", fake_exec)
    sp_file = tmp_path / "sp.md"; sp_file.write_text("prompt", encoding="utf-8")
    s = ChatSession(session_id="22222222-2222-2222-2222-222222222222",
                    system_prompt_path=sp_file, catalog_ids={"crm", "tasks"})
    async def drain(msg):
        return [ev async for ev in s.send(msg)]
    evs1 = await drain("Begin the workshop interview.")
    evs2 = await drain("[card] Where do tasks live? → Linear")
    assert evs1[-1]["type"] == "done" and evs2[-1]["type"] == "done"
    assert len(s.beats) == 2
    assert s.beats[0]["user"] == "Begin the workshop interview."
    assert "Welcome." in s.beats[0]["prose"]
    assert s.beats[0]["studio"]["chapter"] == {"title": "Welcome", "phase": "welcome", "blocks": []}
    assert s.beats[1]["user"].startswith("[card]")
    assert s.beats[1]["studio"]["picks"] == ["crm", "tasks"]
    assert s.beats[1]["studio"]["chapter"] is None   # whole-state snapshot of THAT turn
```

Append to `studio/tests/test_server.py`:

```python
# --- beats replay endpoint (dossier spec §4.1/§10) ---

def test_beats_endpoint_unknown_session_404():
    c = TestClient(server.app)
    assert c.get("/api/session/not-a-session/beats").status_code == 404

def test_beats_endpoint_returns_accumulated():
    c = TestClient(server.app)
    sid = c.post("/api/session/new").json()["session_id"]
    server.SESSIONS[sid].beats = [
        {"user": "Begin the workshop interview.",
         "prose": 'Welcome to the studio.\n```studio\n{"picks": []}\n```',
         "studio": {"picks": [], "name": None, "ready": False, "ask": None,
                    "chapter": {"title": "Welcome", "phase": "welcome", "blocks": []}}},
        {"user": "I drown in email.",
         "prose": 'Noted.\n```studio\n{"picks": ["tasks"]}\n```',
         "studio": {"picks": ["tasks"], "name": None, "ready": False, "ask": None,
                    "chapter": None}},
    ]
    out = c.get(f"/api/session/{sid}/beats").json()
    assert out["session_id"] == sid and len(out["beats"]) == 2
    # prose + studio state sufficient to re-render the document (spec §10)
    assert "Welcome to the studio." in out["beats"][0]["prose"]
    assert out["beats"][0]["studio"]["chapter"]["phase"] == "welcome"
    assert out["beats"][1]["studio"]["picks"] == ["tasks"]

def test_chat_done_carries_chapter_through_sse(monkeypatch):
    class _FakeChapterSession:
        spec = None
        async def send(self, msg):
            yield {"type": "done", "spec": None,
                   "studio": {"picks": [], "name": None, "ready": False, "ask": None,
                              "chapter": {"title": "Taming the inbox", "phase": "skills",
                                          "blocks": []}}}
    c = TestClient(server.app)
    sid = c.post("/api/session/new").json()["session_id"]
    server.SESSIONS[sid] = _FakeChapterSession()
    with c.stream("POST", "/api/chat", json={"session_id": sid, "message": "hi"}) as r:
        body = "".join(r.iter_text())
    assert '"chapter"' in body and "Taming the inbox" in body
```

Append to `studio/tests/test_smoke_integration.py` (the spec §10 integration smoke — fresh uuid4 per the landed convention):

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_workshop_turn_emits_chapter(tmp_path):
    # The chapter contract must make a REAL claude turn emit a parseable chapter
    # with a valid phase (dossier spec §10).
    sp = write_system_prompt(tmp_path / "wp.md", mode="workshop")
    ids = {"crm", "briefing", "scheduling", "tasks", "intake", "drain"}
    s = ChatSession(session_id=str(uuid.uuid4()),
                    system_prompt_path=sp, catalog_ids=ids)
    events = [ev async for ev in s.send(
        "I drown in email and track work in Linear. Begin the interview.")]
    done = events[-1]
    assert done["type"] == "done" and done.get("studio") is not None
    ch = done["studio"].get("chapter")
    assert ch is not None, "no parseable chapter in a real turn"
    assert ch["phase"] in {"welcome", "baseline", "skills", "personalize",
                           "name", "build", "connect"}
    assert s.beats and s.beats[-1]["studio"] == done["studio"]
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/Scripts/python -m pytest studio/tests/test_chat_session.py studio/tests/test_server.py -v`
Expected: `test_beats_accumulate_per_turn` FAILs (`AttributeError: 'ChatSession' object has no attribute 'beats'`); `test_beats_endpoint_*` FAIL with 404s; `test_chat_done_carries_chapter_through_sse` PASSES already (the studio dict rides the done event untouched) — it pins the contract.

- [ ] **Step 3: Implement.** In `studio/chat_session.py` `__init__` (after line 53 `self.studio: dict | None = None`) add:

```python
        # Every completed turn accumulates here (dossier spec §4.1): the page replays
        # GET /api/session/{id}/beats on reload to re-render the whole document.
        # A beat also carries the USER message — the fossilized answers come from it.
        self.beats: list[dict] = []
```

In `send()`, change the turn tail (lines 118–120) — currently:

```python
            self.started = True
            self._extract("".join(full_text))
            yield {"type": "done", "spec": self.spec, "studio": self.studio}
```

to:

```python
            self.started = True
            prose = "".join(full_text)
            self._extract(prose)
            self.beats.append({"user": user_msg, "prose": prose, "studio": self.studio})
            yield {"type": "done", "spec": self.spec, "studio": self.studio}
```

In `studio/server.py`, add below the `chat` endpoint (after line 109):

```python
@app.get("/api/session/{session_id}/beats")
async def session_beats(session_id: str) -> JSONResponse:
    """Beats replay (dossier spec §4.1): the accumulated turns of a live session so a
    page reload re-renders the whole document. Survives reloads, NOT studio restarts
    (sessions are in-memory — spec §8 non-goal)."""
    session = SESSIONS.get(session_id)
    if session is None:
        return JSONResponse({"error": "unknown session"}, status_code=404)
    return JSONResponse({"session_id": session_id,
                         "beats": getattr(session, "beats", [])})
```

- [ ] **Step 4: Run to verify pass**

Run: `.venv/Scripts/python -m pytest studio/tests -q -m "not integration"` → all pass.
(The integration smoke runs with the full suite at the D1a close, Task 11 — it needs a live `claude`.)

- [ ] **Step 5: Commit**

```bash
git add studio/chat_session.py studio/server.py studio/tests/test_chat_session.py studio/tests/test_server.py studio/tests/test_smoke_integration.py
git commit -m "feat(studio): beats — per-turn accumulation on ChatSession + replay endpoint (reload survival)"
```

---

### Task 8: `dossier.css` + `index.html` — the document skin

**Files:**
- Create: `studio/static/dossier.css`
- Modify: `studio/static/index.html`

**Interfaces:**
- Produces: the `#dossier` root (rail + doc column + `#dz-chapters` + `#dz-live` staging + `#dz-writeline`); all dossier styling scoped under `body.dossier` / `dz-` classes so architect mode and `?ui=chat` render untouched. Class vocabulary lifted from `v1b-dossier-journey.html` (measurements preserved; `.card`/`.cards`/`.chip` renamed `dz-card`/`dz-cards`/`dz-chip` to avoid colliding with `cards.css`; the mockup's `--serif` is the repo's existing `--wordmark` token — Crimson Pro, both faces already self-hosted in `studio/static/fonts/`). Tasks 9/10 consume every id/class named here. No pytest — Task 10's checklist exercises it.

- [ ] **Step 1: `index.html` — the dossier root + stylesheet + script slots.** Add the stylesheet link after the `cards.css` link (index.html:7):

```html
<link rel="stylesheet" href="/static/dossier.css">
```

Add the dossier root immediately after the `#onboard-overlay` closing `</div>` (index.html:22), before `<header>`:

```html
  <!-- The dossier — workshop mode's document skin (dossier spec §4). Hidden and inert
       unless dossier.js activates it; architect mode and ?ui=chat never touch it. -->
  <div id="dossier" hidden>
    <div id="dz-rail" class="dz-rail"></div>
    <main class="dz-doc">
      <div class="dz-kicker">qubit agent studio · session dossier</div>
      <h1 class="dz-h1">The agent you're building.</h1>
      <p class="dz-lede">This page <b>is</b> the conversation. Your architect writes
        sections into it; your answers become part of the record.</p>
      <div id="dz-chapters"></div>
      <div id="dz-live"></div>
      <form id="dz-writeline" class="writeline held"><span class="bar"></span>
        <input id="dz-input" autocomplete="off" placeholder="write your line…" disabled></form>
    </main>
  </div>
```

And the script tag between `onboard.js` and `app.js` (index.html:73-74):

```html
  <script src="/static/dossier.js"></script>
```

(`dossier.js` is Task 9 — a missing file 404s harmlessly in the browser until then, and nothing references `window.dossier` before Task 10 wires app.js. Create an empty `studio/static/dossier.js` with just the IIFE shell `(function () { window.dossier = {}; })();` in THIS task so the page stays console-clean.)

- [ ] **Step 2: Write `studio/static/dossier.css`** (lifted from v1b/v1c; SapphireOS tokens only — no new hex values; rgba() shadows/rings carried over from the mockup are ink/sapphire-derived, same as styles.css already uses):

```css
/* ── The dossier — the workshop page as a living document (dossier spec §2/§4). ──
   Lifted from docs/mockups/dossier-journey/v1b-dossier-journey.html + v1c-finale.html.
   Every rule is scoped under body.dossier or a dz-/dossier class: architect mode and
   ?ui=chat never activate any of this. Serif = the existing --wordmark token
   (Crimson Pro, regular + italic faces already self-hosted). */

/* page takeover: the document scrolls; the old panes hide; header stays */
html.dossier, body.dossier { overflow: auto; height: auto; }
body.dossier main { display: block; height: 0; overflow: visible; }
body.dossier #chat { display: none; }
body.dossier .rightrail { display: none; }
body.dossier #advanced { display: none; }  /* Load/Download/evals/Export → architect mode only (§4.4) */
body.dossier #dossier { display: block; }

/* the C3 onboarding walk mounts as a floating dock above the document until D3 (§7.1) */
body.dossier.onboarding .rightrail {
  display: flex; flex-direction: column; position: fixed; right: 24px; top: 86px;
  width: 380px; max-height: calc(100vh - 120px); z-index: 40; overflow: auto;
  background: var(--canvas); border: 1px solid var(--rule); border-radius: var(--r-card);
  box-shadow: var(--sh-lg); padding: 16px;
}

#dossier .dz-doc { max-width: 760px; margin: 0 auto; padding: 64px 32px 30vh;
  position: relative; font-size: 17px; line-height: 1.55; }
.dz-kicker { font-family: var(--mono); font-size: 11px; letter-spacing: .16em;
  text-transform: uppercase; color: var(--ink-3); }
.dz-h1 { font-family: var(--display); font-weight: 640; font-size: 44px; line-height: 1.06;
  letter-spacing: -.025em; color: var(--ink); margin: 10px 0 6px; }
.dz-lede { font-size: 18px; color: var(--ink-3); margin: 0 0 56px; max-width: 52ch; }
.dz-lede b { color: var(--ink-2); font-weight: 600; }

/* ── journey rail (v1b .rail/.node) ── */
.dz-rail { position: fixed; left: calc(50% - 380px - 52px); top: 10vh; bottom: 10vh;
  width: 2px; background: var(--rule); }
.dz-rail > i { position: absolute; top: 0; left: 0; width: 2px; height: 0;
  background: var(--sapphire); transition: height .8s ease; }
.dz-rail .node { position: absolute; left: -5.5px; cursor: pointer; }
.dz-rail .node b { display: block; width: 11px; height: 11px; border-radius: 50%;
  background: var(--canvas); border: 2px solid var(--ink-4); transition: all .3s ease; }
.dz-rail .node span { position: absolute; right: 20px; top: -3px; white-space: nowrap;
  font-family: var(--mono); font-size: 10px; letter-spacing: .13em; text-transform: uppercase;
  color: var(--ink-4); transition: color .3s ease; }
.dz-rail .node.done b { background: var(--sapphire); border-color: var(--sapphire); }
.dz-rail .node.done span { color: var(--ink-3); }
.dz-rail .node.now b { border-color: var(--sapphire);
  box-shadow: 0 0 0 4px rgba(48,111,168,.16); animation: dz-ring 1.8s ease-in-out infinite; }
.dz-rail .node.now span { color: var(--sapphire); font-weight: 500; }
.dz-rail .node.stale b { border-color: var(--brass); background: var(--brass-tint);
  box-shadow: none; animation: none; }
.dz-rail .node.stale span { color: var(--brass); }
@keyframes dz-ring { 50% { box-shadow: 0 0 0 7px rgba(48,111,168,.08); } }
@media (max-width: 900px) { .dz-rail { display: none; } #dossier .dz-doc { padding-top: 40px; } }

/* ── chapters (v1b section/.sec-head) ── */
.dz-sec { margin: 0 0 60px; position: relative; transition: opacity .4s ease; }
.dz-sec.settle { animation: dz-settle .5s ease both; }
@keyframes dz-settle { from { opacity: 0; transform: translateY(14px); }
  to { opacity: 1; transform: none; } }
.dz-sec .sec-head { display: flex; align-items: baseline; gap: 14px;
  border-bottom: 1px solid var(--rule-strong); padding-bottom: 10px; margin-bottom: 22px; }
.dz-sec .sec-head .no { font-family: var(--mono); font-size: 12px; color: var(--brass); }
.dz-sec h2 { font-family: var(--display); font-weight: 600; font-size: 24px;
  letter-spacing: -.015em; color: var(--ink); margin: 0; }
.dz-sec .sec-head .why { margin-left: auto; font-family: var(--mono); font-size: 11px;
  color: var(--ink-4); letter-spacing: .08em; text-transform: uppercase; }
.dz-prose { color: var(--ink-2); }
.dz-prose p, #dz-live p { margin: 0 0 10px; }
#dz-live { color: var(--ink-2); margin: 0 0 18px; }
.dz-error { margin: 14px 0 0; padding: 10px 14px; border: 1px dashed var(--brass);
  border-radius: 10px; background: var(--brass-tint); font-family: var(--mono);
  font-size: 12px; color: var(--brass); }

/* ── skill cards (v1b .cards/.card → dz-) ── */
.dz-cards { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin: 0 0 18px; }
@media (max-width: 640px) { .dz-cards { grid-template-columns: 1fr; } }
.dz-card { background: var(--canvas); border: 1px solid var(--rule);
  border-radius: var(--r-card); box-shadow: var(--sh-sm); padding: 20px 22px; position: relative; }
.dz-card .tag { position: absolute; top: 16px; right: 16px; font-family: var(--mono);
  font-size: 10px; letter-spacing: .12em; text-transform: uppercase; color: var(--ink-4); }
.dz-card h3 { font-family: var(--display); font-weight: 620; font-size: 18.5px;
  color: var(--ink); margin: 0 0 6px; }
.dz-card p { margin: 0; font-size: 15.5px; color: var(--ink-3); line-height: 1.5; }
.dz-card .price { display: inline-block; margin-top: 12px; font-family: var(--mono);
  font-size: 11px; padding: 3px 10px; border-radius: 999px;
  background: var(--warn-t); color: var(--warn); }
.dz-receipt { font-family: var(--mono); font-size: 11px; color: var(--ink-4); margin: 0 0 10px; }

/* ── inline asks + choice cards (v1b .ask/.choices) ── */
.dz-ask { margin: 26px 0 0; }
.dz-ask .ask { padding-left: 18px; border-left: 3px solid var(--sapphire); }
.dz-ask .who { font-family: var(--mono); font-size: 10.5px; letter-spacing: .14em;
  text-transform: uppercase; color: var(--sapphire); margin-bottom: 6px; }
.dz-ask .ask p { margin: 0; font-size: 17.5px; color: var(--ink); }
.choices { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin: 18px 0 0 18px; }
@media (max-width: 640px) { .choices { grid-template-columns: 1fr; } }
.choice { background: var(--canvas); border: 1.5px solid var(--rule); border-radius: 12px;
  padding: 14px 16px; cursor: pointer; text-align: left; font-family: var(--body);
  transition: border-color .15s, box-shadow .15s, transform .15s; }
.choice:hover { border-color: var(--sapphire); box-shadow: var(--sh-sm); transform: translateY(-2px); }
.choice b { display: block; font-size: 15.5px; color: var(--ink); font-weight: 650; margin-bottom: 4px; }
.choice span { font-size: 13.5px; color: var(--ink-3); line-height: 1.4; }
.choice.picked { border-color: var(--sapphire); background: var(--tint);
  box-shadow: 0 0 0 3px rgba(48,111,168,.12); }
.choice.dim { opacity: .42; }
.choice:disabled { cursor: default; }
.dz-ask .or { margin: 12px 0 0 18px; font-family: var(--mono); font-size: 10.5px;
  letter-spacing: .1em; text-transform: uppercase; color: var(--ink-4); }

/* ── fossilized answers (v1b .answer) — the human is the serif ── */
.answer { margin: 18px 0 0 18px; font-family: var(--wordmark); font-style: italic;
  font-size: 21px; line-height: 1.5; color: var(--ink-2); position: relative; padding-right: 90px; }
.answer::before { content: '— '; color: var(--brass); }

/* ── the writing line (v1b .writeline) ── */
.writeline { margin: 14px 0 0 18px; display: flex; align-items: flex-start; gap: 12px; }
.writeline .bar { width: 3px; align-self: stretch; background: var(--brass);
  border-radius: 2px; animation: dz-breathe 1.6s ease-in-out infinite; }
@keyframes dz-breathe { 50% { opacity: .35; } }
.writeline input { flex: 1; border: 0; outline: 0; background: transparent;
  font-family: var(--wordmark); font-style: italic; font-size: 21px; color: var(--ink);
  padding: 2px 0; border-bottom: 1px dashed var(--rule-strong); }
.writeline input::placeholder { color: var(--ink-4); }
.writeline input:focus { border-bottom-color: var(--brass); }
.writeline.held { opacity: .45; }
.writeline.held .bar { animation: none; opacity: .3; }

@media (prefers-reduced-motion: reduce) {
  .dz-sec.settle { animation: none; }
  .writeline .bar { animation: none; }
  .dz-rail .node.now b { animation: none; }
  .dz-rail > i { transition: none; }
  .choice, .choice:hover { transition: none; transform: none; }
}
```

- [ ] **Step 3: Create the placeholder `studio/static/dossier.js`**

```js
// The dossier renderer lands in the next task; this shell keeps index.html's script
// tag console-clean in the interim.
(function () { window.dossier = {}; })();
```

- [ ] **Step 4: Syntax + regression guard**

Run: `node --check studio/static/dossier.js` → no output (ok).
Run: `.venv/Scripts/python -m pytest studio/tests -q -m "not integration"` → all pass.
Manual spot-check: `python -m studio`, open `/?mode=architect` and the plain workshop page — both render exactly as before (the dossier root is `hidden` and no class activates the CSS).

- [ ] **Step 5: Commit**

```bash
git add studio/static/dossier.css studio/static/dossier.js studio/static/index.html
git commit -m "feat(studio): dossier skin — document column, rail, chapter/answer/writeline vocabulary (v1b measurements)"
```

---

### Task 9: `dossier.js` — the document engine (beats → chapters, staging, asks, rail, replay)

**Files:**
- Modify: `studio/static/dossier.js` (replace the Task 8 shell with the full engine)

**Interfaces:**
- Consumes: `window.renderMarkdown` / `window.stripSpec` / `window.queueSend` / `window.startWorkshopSession` / `window.resumeSession` / `window.shelfSync` (exposed by Task 10), `GET /api/session/{id}/beats` (Task 7), `GET /api/catalog`.
- Produces: `window.dossier = { activate, tryReplay, onToken, onError, onDone }` — the exact hooks Task 10 routes `send()` events into. Internal state (`chapters`, `open`, `pendingTarget`, `lastStudio`, `lastDone`) is extended in-file by Tasks 13/15/16/18/20. No pytest (no JS runner — spec §10): `node --check` + backend guard here; the full **D1a manual checklist** runs in Task 10 once app.js routes to these hooks.

- [ ] **Step 1: Replace `studio/static/dossier.js` with the full engine**

```js
// The dossier — the workshop page as a living document (dossier spec §4).
// app.js routes chat-stream events here when the dossier skin is active; every beat is
// still one `claude -p` turn under the hood. Rendering model (§4.1): tokens stream into
// the headless #dz-live staging block at the document's live edge; the `chapter` field
// settles heading + placement at done (same title continues the open section, new title
// opens a numbered one, no valid chapter folds into the open section).
(function () {
  const $ = (s) => document.querySelector(s);
  const esc = (s) => String(s == null ? '' : s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  const norm = (t) => String(t || '').trim().toLowerCase();
  const PHASES = ['welcome', 'baseline', 'skills', 'personalize', 'name', 'build', 'connect'];

  let chapters = [];        // [{ n, title, phase, el, bodyEl }] in document order
  let open = null;          // the open (last) chapter record
  let prevPicks = [];       // previous beat's picks — drives the picks-diff (§4.1.1)
  let lastStudio = null;    // last settled whole-state studio block
  let catalog = null;
  let pendingAsk = null;    // the unanswered ask at the tail, if any
  let acc = '';             // this turn's accumulated raw prose (fences included)
  let replaying = false;
  // Set by the D1b revision verbs; consumed by exactly ONE settle (§5 pending-target
  // override): { rec, mode: 'append' | 'replace' }.
  let pendingTarget = null;
  let rwSettle = null;      // D1b: deferred re-settle to run on the rewrite beat's done

  // ── activation ──────────────────────────────────────────────────────────
  function activate() {
    window.dossierActive = true;
    document.documentElement.classList.add('dossier');
    document.body.classList.add('dossier');
    $('#dossier').hidden = false;
    buildRail();
    getCatalog();
  }

  async function getCatalog() {
    if (!catalog) {
      try { catalog = await (await fetch('/api/catalog')).json(); }
      catch { catalog = { baseline: { items: [] }, shelf: { items: [] } }; }
    }
    return catalog;
  }
  const shelfById = () => new Map((((catalog || {}).shelf || {}).items || []).map((i) => [i.id, i]));

  // ── beats replay (spec §4.1: a reload against a live server restores the page) ──
  async function tryReplay() {
    const sid = sessionStorage.getItem('dossier-session');
    if (!sid) return false;
    let out;
    try {
      const r = await fetch(`/api/session/${sid}/beats`);
      if (!r.ok) throw new Error('gone');
      out = await r.json();
    } catch { sessionStorage.removeItem('dossier-session'); return false; }
    if (!out.beats || !out.beats.length) { sessionStorage.removeItem('dossier-session'); return false; }
    await getCatalog();
    window.resumeSession(sid);
    replaying = true;
    out.beats.forEach((b, i) => replayBeat(b, i === out.beats.length - 1));
    replaying = false;
    if (lastStudio && typeof window.shelfSync === 'function') window.shelfSync(lastStudio);
    return true;
  }

  function replayBeat(b, isLast) {
    const u = String(b.user || '');
    // seeds and [studio event]s are the machine channel — never part of the record;
    // a [card] message re-fossilizes its answer part (flagged deviation 4)
    if (!/^\[studio event\]/.test(u) && !/^Begin /.test(u)) {
      if (/^\[card\] /.test(u)) {
        const m = u.match(/^\[card\] [\s\S]* → ([\s\S]*)$/);
        fossilize((m ? m[1] : u.slice(7)).replace(/^\(custom\) /, ''));
      } else {
        fossilize(u);
      }
    }
    acc = b.prose || '';
    $('#dz-live').innerHTML = window.renderMarkdown(window.stripSpec(acc));
    // asks/writeline render only on the LAST beat — earlier asks are already answered
    // (their fossil is the record); the pending one re-arms live.
    onDone({ studio: b.studio || {} }, !isLast);
  }

  // ── streaming: the live edge (§4.1) ─────────────────────────────────────
  function onToken(fullText) {
    acc = fullText;
    holdWriteline();
    $('#dz-live').innerHTML = window.renderMarkdown(window.stripSpec(fullText));
    nudgeScroll();
  }

  // §4.1 errors: a brass error line in the open chapter, the writing line re-arms,
  // any card-held baton releases — the participant can always continue.
  function onError(message) {
    const line = document.createElement('div');
    line.className = 'dz-error';
    line.textContent = '⚠ ' + String(message || 'something went wrong — write to continue');
    ((open && open.bodyEl) || $('#dz-live')).appendChild(line);
    $('#dz-live').innerHTML = '';
    acc = '';
    pendingTarget = null;          // a verb's target clears on its beat, success or error (§5)
    armWriteline(pendingAsk, true);
    nudgeScroll();
  }

  // ── the settle: one done event = one beat (§4.1) ────────────────────────
  function onDone(ev, quiet) {
    const studio = (ev && ev.studio) || lastStudio || {};
    const rec = settle(studio.chapter);
    if (studio.chapter && studio.chapter.blocks && studio.chapter.blocks.length) {
      renderBlocks(rec, studio.chapter.blocks);   // D1a: parser validates, renderer renders none (§3.2)
    }
    diffPicks(studio.picks || []);
    pendingAsk = studio.ask || null;
    if (studio.ask && !quiet) renderAsk(studio.ask);
    lastStudio = studio;
    if (rwSettle) { rwSettle(); rwSettle = null; }   // D1b: honest re-settle after a rewrite beat
    if (!quiet) armWriteline(pendingAsk, true);
    updateRail();
    if (!quiet) nudgeScroll();
  }

  function settle(chapter) {
    const staged = $('#dz-live');
    let target;
    if (pendingTarget) {
      // §5 pending-target override: the verb's beat routes to the requested chapter
      // regardless of the emitted title, consuming exactly one beat.
      target = pendingTarget;
      pendingTarget = null;
    } else if (chapter && open && norm(chapter.title) === norm(open.title)) {
      target = { rec: open, mode: 'append' };        // same title → the staging is invisible
    } else if (chapter) {
      target = { rec: newSection(chapter), mode: 'append' };
    } else {
      // §3.1 fallback: no valid chapter → staged prose folds into the open chapter;
      // the very first beat with no chapter still opens the welcome section.
      target = { rec: open || newSection({ title: 'Welcome', phase: 'welcome' }), mode: 'append' };
    }
    if (staged.innerHTML.trim()) {
      if (target.mode === 'replace') {
        // regenerate (§5): agent prose only, in place — fossils/asks/cards untouched
        target.rec.bodyEl.querySelectorAll('.dz-prose, .dz-error').forEach((n) => n.remove());
      }
      const prose = document.createElement('div');
      prose.className = 'dz-prose';
      prose.innerHTML = staged.innerHTML;
      target.rec.bodyEl.appendChild(prose);
    }
    target.rec.el.classList.remove('dz-regenerating');
    staged.innerHTML = '';
    acc = '';
    return target.rec;
  }

  function newSection(ch) {
    const n = chapters.length + 1;
    const sec = document.createElement('section');
    sec.className = 'dz-sec settle';
    sec.dataset.phase = ch.phase;
    sec.dataset.n = n;
    sec.innerHTML = `
      <div class="sec-head"><span class="no">${String(n).padStart(2, '0')}</span>
        <h2>${esc(ch.title)}</h2><span class="why">${esc(ch.phase)}</span></div>
      <div class="dz-body"></div>`;
    $('#dz-chapters').appendChild(sec);
    const rec = { n, title: ch.title, phase: ch.phase, el: sec,
                  bodyEl: sec.querySelector('.dz-body') };
    chapters.push(rec);
    open = rec;
    return rec;
  }

  // D2 renders the typed vocabulary; D1a accepts-and-ignores (§3.2).
  function renderBlocks(rec, blocks) {}

  // ── picks-diff → skill cards (§4.1.1) ───────────────────────────────────
  function skillCardHtml(it, tag) {
    return `<div class="dz-card" data-skill="${esc(it.id)}"><span class="tag">${esc(tag)}</span>
      <h3>${esc(it.name)}</h3><p>${esc(it.what)}</p>
      <span class="price">${esc((it.cost && it.cost.label) || '')}</span></div>`;
  }

  function diffPicks(picks) {
    const byId = shelfById();
    const added = picks.filter((id) => !prevPicks.includes(id) && byId.has(id));
    const removed = prevPicks.filter((id) => !picks.includes(id));
    if (added.length && open) {
      const grid = document.createElement('div');
      grid.className = 'dz-cards';
      grid.innerHTML = added.map((id) => skillCardHtml(byId.get(id), '✓ added')).join('');
      open.bodyEl.prepend(grid);       // top of the open chapter (§4.1)
    }
    removed.forEach((id) => {
      const card = document.querySelector(`.dz-card[data-skill="${CSS.escape(id)}"]`);
      if (card) {
        const r = document.createElement('div');
        r.className = 'dz-receipt';
        r.textContent = `– ${id} set aside`;
        card.replaceWith(r);           // fold to a receipt line
      }
    });
    prevPicks = picks.slice();
  }

  // ── inline asks: the ask channel as dossier material (§4.1.2) ───────────
  function renderAsk(ask) {
    if (!open) newSection({ title: 'Welcome', phase: 'welcome' });
    if (open.bodyEl.querySelector(`.dz-ask[data-ask-id="${CSS.escape(ask.id)}"]:not([data-answered])`)) return;
    const wrap = document.createElement('div');
    wrap.className = 'dz-ask';
    wrap.dataset.askId = ask.id;
    wrap.innerHTML = `
      <div class="ask"><div class="who">architect asks</div><p>${esc(ask.title)}</p></div>
      <div class="choices">${ask.options.map((o) => `
        <button type="button" class="choice" data-oid="${esc(o.id)}">
          <b>${esc(o.label)}</b><span>${esc(o.why || '')}</span></button>`).join('')}</div>
      <div class="or">or write your own ↓</div>`;
    open.bodyEl.appendChild(wrap);
    wrap.querySelectorAll('.choice').forEach((c) => c.addEventListener('click', () => {
      if (wrap.dataset.answered) return;
      const o = ask.options.find((x) => x.id === c.dataset.oid);
      if (o) answerAsk(ask, wrap, o.label, c.dataset.oid);
    }));
  }

  // One hot surface (the onboarding-cards baton rule, §4.1.2): the cards and the
  // writing line together are the ask's answer surface; answering by either
  // fossilizes, sends the [card] message, and holds the line until the next done.
  function answerAsk(ask, wrap, text, oid) {
    wrap.dataset.answered = '1';
    wrap.querySelectorAll('.choice').forEach((c) => {
      c.classList.toggle('picked', c.dataset.oid === oid);
      c.classList.toggle('dim', c.dataset.oid !== oid);
      c.disabled = true;
    });
    fossilize(text, ask.title);
    pendingAsk = null;
    holdWriteline();
    window.queueSend(`[card] ${ask.title} → ${oid ? text : `(custom) ${text}`}`);
    nudgeScroll();
  }

  // ── fossilized answers: the human is the serif (§4.1.3) ─────────────────
  function fossilize(text, q) {
    const a = document.createElement('div');
    a.className = 'answer';
    if (q) a.dataset.q = q;
    a.textContent = text;              // the brass dash is CSS ::before
    ((open && open.bodyEl) || $('#dz-live')).appendChild(a);
    return a;
  }

  // ── the writing line — the document's next line ─────────────────────────
  function armWriteline(ask, hot) {
    if (hot && window.onboardingActive) hot = false;   // the C3 walk holds the baton
    const wl = $('#dz-writeline');
    const inp = $('#dz-input');
    wl.classList.toggle('held', !hot);
    inp.disabled = !hot;
    inp.placeholder = ask ? 'or write your own…' : 'write your line…';
    if (hot && !replaying) inp.focus({ preventScroll: true });
  }
  function holdWriteline() { armWriteline(pendingAsk, false); }

  $('#dz-writeline').addEventListener('submit', (e) => {
    e.preventDefault();
    const inp = $('#dz-input');
    const v = inp.value.trim();
    if (!v || inp.disabled) return;
    inp.value = '';
    if (pendingAsk && open) {
      const wrap = open.bodyEl.querySelector(
        `.dz-ask[data-ask-id="${CSS.escape(pendingAsk.id)}"]:not([data-answered])`);
      if (wrap) { answerAsk(pendingAsk, wrap, v, null); return; }
    }
    fossilize(v);
    holdWriteline();
    window.queueSend(v);
    nudgeScroll();
  });

  // ── the journey rail — derived, never stored (§4.2) ─────────────────────
  function buildRail() {
    $('#dz-rail').innerHTML = '<i id="dz-railfill"></i>' + PHASES.map((p, i) =>
      `<div class="node" data-phase="${p}" style="top:${6 + i * 14.5}%"><b></b><span>${p}</span></div>`
    ).join('');
    document.querySelectorAll('#dz-rail .node').forEach((n) => n.addEventListener('click', () => {
      if (!n.classList.contains('done') && !n.classList.contains('now')) return;
      const sec = document.querySelector(`.dz-sec[data-phase="${n.dataset.phase}"]`);
      if (sec) sec.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }));
  }

  function updateRail() {
    const seen = chapters.map((c) => PHASES.indexOf(c.phase)).filter((i) => i >= 0);
    const cur = open ? PHASES.indexOf(open.phase) : -1;
    document.querySelectorAll('#dz-rail .node').forEach((n) => {
      const i = PHASES.indexOf(n.dataset.phase);
      n.classList.remove('done', 'now');   // .stale is owned by the D1b rewrite flow
      if (seen.some((s) => s > i)) n.classList.add('done');      // a later phase was seen
      else if (i === cur) n.classList.add('now');
    });
    const fill = $('#dz-railfill');
    if (fill && cur >= 0) fill.style.height = (6 + cur * 14.5) + '%';
  }

  // follow the live edge only when the reader is already near it (scrollytell-safe)
  function nudgeScroll() {
    const nearBottom = window.innerHeight + window.scrollY > document.body.scrollHeight - 260;
    if (nearBottom) window.scrollTo({ top: document.body.scrollHeight, behavior: 'auto' });
  }

  window.dossier = { activate, tryReplay, onToken, onError, onDone };
})();
```

- [ ] **Step 2: Syntax + regression guard**

Run: `node --check studio/static/dossier.js` → no output (ok).
Run: `.venv/Scripts/python -m pytest studio/tests -q -m "not integration"` → all pass (no backend surface touched).

- [ ] **Step 3: Commit**

```bash
git add studio/static/dossier.js
git commit -m "feat(studio): dossier engine — live-edge staging, chapter settle, inline asks, fossils, rail, beats replay"
```

---

### Task 10: `app.js` routing — `?ui=chat`, dossier hooks, C3 dock, shelf event sync

**Files:**
- Modify: `studio/static/app.js`, `studio/static/shelf.js`

**Interfaces:**
- Consumes: `window.dossier.{activate, tryReplay, onToken, onError, onDone}` (Task 9), `/api/onboarding` (existing).
- Produces: `const UI` (`'dossier'` in workshop mode unless `?ui=chat`; always `'chat'` in architect mode); `window.renderMarkdown` / `window.stripSpec` / `window.streamBuild` / `window.setStatus` / `window.resumeSession` exposed; `startWorkshopSession` stores the session id in `sessionStorage` for replay; shelf.js reports manual add/remove as `[studio event]`s (spec §4.4). Tasks 15/16/18 consume `streamBuild`/`setStatus`.

- [ ] **Step 1: The UI switch + exposed helpers.** In `studio/static/app.js`, after the `MODE`/`SEED` block (lines 5–7) add:

```js
// The dossier is the workshop skin (dossier spec §1); ?ui=chat keeps the old workshop
// chat reachable on the SAME backend (same session, extractor, endpoints) — the
// in-room escape hatch until dossier parity is proven at a dress rehearsal.
const UI = (MODE === 'workshop' && new URLSearchParams(location.search).get('ui') !== 'chat')
  ? 'dossier' : 'chat';
```

After `renderMarkdown`'s definition (app.js:93-95) add `window.renderMarkdown = renderMarkdown;`; after `stripSpec` (app.js:111-117) add `window.stripSpec = stripSpec;`; after `setStatus` (app.js:52-56) add `window.setStatus = setStatus;`; after `streamBuild`'s closing brace (app.js:464) add `window.streamBuild = streamBuild;`.

- [ ] **Step 2: Session id plumbing.** In `window.startWorkshopSession` (app.js:63-72), after `sessionId = (await r.json()).session_id;` add:

```js
  if (UI === 'dossier') sessionStorage.setItem('dossier-session', sessionId);
```

And below the function add:

```js
// Beats replay (dossier spec §4.1): dossier.js restores a stored session on reload.
window.resumeSession = function (sid) { sessionId = sid; setStatus('ready'); };
```

- [ ] **Step 3: Route `send()`'s events.** Replace the body of `send()` (app.js:119-156) with:

```js
async function send(message) {
  const inDossier = UI === 'dossier';
  if (!inDossier && message !== lastSeed && !HIDDEN_MSG.test(message)) addBubble('user', message);
  const bubble = inDossier ? null : addBubble('assistant', '');
  const r = await fetch('/api/chat', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, message }),
  });
  const reader = r.body.getReader(); const dec = new TextDecoder(); let buf = '', acc = '';
  while (true) {
    const { value, done } = await reader.read(); if (done) break;
    buf += dec.decode(value, { stream: true });
    let i; while ((i = buf.indexOf('\n\n')) >= 0) {
      const line = buf.slice(0, i).replace(/^data: /, ''); buf = buf.slice(i + 2);
      if (!line) continue;
      const ev = JSON.parse(line);
      if (ev.type === 'token') {
        if (!agentLive) { agentLive = true; setStatus('agent live', true); }  // verifiable handshake
        acc += ev.text;
        if (inDossier) window.dossier.onToken(acc);
        else { bubble.innerHTML = renderMarkdown(stripSpec(acc)); scrollLog(); }
      }
      else if (ev.type === 'error') {
        if (inDossier) window.dossier.onError(ev.message);
        else { acc += '\n\n**[error]** ' + ev.message; bubble.innerHTML = renderMarkdown(stripSpec(acc)); }
      }
      else if (ev.type === 'done') {
        // The shelf drawer stays truthful in BOTH skins (§4.4: it's the kept overlay).
        if (ev.studio && typeof window.shelfSync === 'function') window.shelfSync(ev.studio);
        if (inDossier) {
          window.dossier.onDone(ev);
          continue;
        }
        // ?ui=chat / architect: the landed behavior, byte-for-byte.
        if (ev.spec && !window.onboardingActive) renderBlueprint(ev.spec);
        if (MODE === 'workshop' && !window.onboardingActive) renderAgentPanel(ev.studio);
        if (ev.studio && ev.studio.ask) {
          if (!window.onboardingActive) renderAskCard(ev.studio.ask);
          else window._pendingAsk = ev.studio.ask;
        }
      }
    }
  }
}
```

- [ ] **Step 4: Boot routing + the C3 dock.** Replace `start()` (app.js:74-88) with:

```js
async function start() {
  if (UI === 'dossier') {
    window.dossier.activate();
    if (await window.dossier.tryReplay()) return;   // reload mid-journey: document restored
  }
  // Onboarding gate: first launch (or ?onboard=1) hands the boot to the walk — it
  // creates the session and seeds the first turn itself. In dossier mode the C3 walk
  // mounts as a floating dock above the document until D3 re-skins it (spec §7.1).
  if (MODE === 'workshop') {
    const ob = await (await fetch('/api/onboarding')).json();
    const force = new URLSearchParams(location.search).get('onboard') === '1';
    if ((force || !ob.completed) && window.onboardWalk) {
      if (UI === 'dossier') document.body.classList.add('onboarding');
      window.onboardWalk.begin(ob);
      return;                          // the walk calls startWorkshopSession itself
    }
  }
  if (MODE === 'workshop' && UI === 'chat' && !window.onboardingActive) renderAgentPanel(null);
  return window.startWorkshopSession(SEED);
}
```

And extend the baton hook (app.js:25-29) so the dock retires when the walk hands back:

```js
if (window.cards) {
  window.cards.onBaton((holder) => {
    $('#composer').classList.toggle('asleep', holder === 'card');
    // dossier + C3: the floating dock retires when the walk hands the baton back
    if (holder === 'composer' && !window.onboardingActive) document.body.classList.remove('onboarding');
  });
}
```

- [ ] **Step 5: Shelf event sync (spec §4.4).** In `studio/static/shelf.js`, replace `toggle` (shelf.js:89-94) with:

```js
  function toggle(id) {
    const it = (catalog.shelf.items || []).find((x) => x.id === id);
    if (!it) return;
    let verb;
    if (selected.has(id)) { selected.delete(id); verb = 'removed'; }
    else { selected.set(id, { it, origin: 'user' }); verb = 'added'; }
    // Dossier §4.4: report manual shelf changes to the agent, which re-asserts
    // whole-state picks — the signed manifest can then never diverge from the shelf.
    if (document.body.classList.contains('dossier') && typeof window.queueSend === 'function') {
      window.queueSend(`[studio event] participant ${verb} ${id} via the shelf`);
    }
    renderBody();  // re-render so on/recommended states stay truthful
  }
```

- [ ] **Step 6: Syntax + backend guard**

Run: `node --check studio/static/app.js && node --check studio/static/shelf.js && node --check studio/static/dossier.js` → ok.
Run: `.venv/Scripts/python -m pytest studio/tests -q -m "not integration"` → all pass.

- [ ] **Step 7: D1a MANUAL BROWSER CHECKLIST** (spec §10 D1a, named steps — real `claude`, `python -m studio`; delete `studio/.cache/onboarding.json` first for the walk item)

1. **Scrollytell end to end:** complete onboarding, interview through several topics — the page reads as one document top to bottom; answers are serif with the brass dash; agent prose is markdown-rendered with no ` ```studio ` fence ever visible (mid-stream included).
2. **Same-title continuation:** a follow-up turn reusing the chapter title continues the open section — NO new heading appears (the staging is invisible).
3. **New-title break:** a topic turn opens a new numbered section (`02`, `03`…) with the settle motion, phase eyebrow on the right.
4. **Rail states:** milestones colour in as later phases are seen; the current phase pulses; clicking a done milestone scrolls to that phase's first chapter; rail hidden below 900px width.
5. **Inline ask + baton:** an agent ask renders choice cards in the open chapter + "or write your own"; clicking a card marks it picked, dims the others, fossilizes the label, and the writing line holds until the next turn settles; typing a custom answer into the line does the same; no `[card]` text ever renders.
6. **Picks-diff:** a recommended skill renders its card at the top of the open chapter; talking the agent out of a pick folds the card to a receipt line; the shelf drawer badge mirrors both.
7. **Shelf event sync:** open the shelf drawer, manually add a skill — the agent's next turn acknowledges it and re-asserts picks including it; remove it — same in reverse.
8. **Forced error:** kill `claude` mid-turn (or disconnect network) — a brass error line renders in the open chapter, the writing line re-arms, a card-held baton releases, and the next message works.
9. **Beats replay:** mid-journey, hard-reload the page — the whole document re-renders (chapters, fossils, cards) and the conversation continues in the same session.
10. **`?ui=chat`:** renders the OLD workshop chat (bubbles, right panel, ask rail) on the same backend — complete a turn to prove the session works.
11. **C3 dock:** with onboarding state cleared, the walk's overlay + cards run in the floating dock while the agent's narration writes the document behind it; after handback the dock disappears and the interview continues in the document.
12. **Reduced motion:** DevTools emulate `prefers-reduced-motion` — no settle/breathe/ring animation.
13. **`?mode=architect`:** the classic two-pane chat, blueprint, advanced controls — unchanged.
14. **Legibility:** on a shared-screen zoom (~1280×800), body 17px / answers 21px / h2 24px read from the back of a room.

- [ ] **Step 8: Commit**

```bash
git add studio/static/app.js studio/static/shelf.js
git commit -m "feat(studio): dossier routing — ?ui=chat escape hatch, event hooks, C3 dock, shelf event sync"
```

---

### Task 11: D1a docs checkpoints — FACILITATOR runbook + GUI install copy (deferred from D0)

**Files:**
- Create: `FACILITATOR.md` (repo root — the lean §3 layout position)
- Modify: `studio/static/app.js` (`installLineHtml`, lines 283-286), `README.md` (launch line)

- [ ] **Step 1: Fix the GUI install copy.** In `studio/static/app.js`, replace `installLineHtml` (lines 283–286) — currently:

```js
function installLineHtml(ev) {
  return `<pre class="install">${ev.install.split(' ; ').join('\n')}</pre>
    <p>Restart Claude Code after installing.</p>`;
}
```

with:

```js
function installLineHtml(ev) {
  // D0's raw-skills form: one command, no marketplace, no restart (lean spec §5).
  return `<pre class="install">${ev.install}</pre>
    <p>Your agent lives in that folder — run this in a terminal and talk to it.</p>`;
}
```

- [ ] **Step 2: Root README launch-line touch-up.** In `README.md`, find the journey description's final-step wording (search for `install` / `dist/`); ensure the participant-facing outcome line reads the raw-skills form, e.g. append/adjust to:

```markdown
The journey ends with a working agent in `dist/<name>-cos/` — launch it with
`cd dist/<name>-cos && claude`.
```

(If the README already says exactly this, no edit — it carries no `/plugin` wording as of this plan.)

- [ ] **Step 3: Create `FACILITATOR.md`** (repo root):

```markdown
# FACILITATOR — running the room

The in-room runbook for the QubitStudio "Build Your Own Chief of Staff" workshop.
Participant pre-work lives in `README.md`; this file is for whoever is driving the room.

## Recovery moves (dossier journey)

| Symptom | Move |
|---|---|
| A chapter rendered mangled (broken markdown, wrong content) | Hover the chapter head → **⟳ regenerate** — the architect rewrites that chapter's prose in place; the participant's answers and cards are preserved. This is the "try that again" button. |
| A participant answered wrong / changed their mind | Hover the answer → **↺ rewrite** — the answer melts back into the writing line; chapters below go stale until the architect re-settles. |
| Page looks stuck / browser hiccup | **Reload the page.** The dossier replays its beats from the live server and re-renders fully (same session, nothing lost). A studio RESTART starts fresh — don't restart `python -m studio` unless the server itself is dead. |
| The dossier misbehaves and the room can't wait | **`?ui=chat`** on the same URL — the classic workshop chat on the same session backend. Same journey, plainer skin. Kept until dossier parity is proven at a dress rehearsal. |
| First breath (the agent's first words) shows the "offline greeting" card | Expected fallback when the one-turn greeting errors or exceeds its ~20s budget. The composed agent is fine — the launch command below the card is real; have the participant run it. |
| Architect chat needed (generic plugin design, spec download) | `?mode=architect` — the original two-pane interview, untouched. |

## Standing facts

- Every visible agent word is real model output (one `claude -p` turn per beat) — there
  is no scripted narration to fall back on except the flagged first-breath card.
- The launch command is real from the moment the launch card renders — integration
  chips fill in as keys connect; keys are never required to build or to talk locally.
- A REBUILD (pressing Build again) recreates `dist/<name>-cos/` from scratch, including
  its `.env` — connected keys must be re-entered. Documented consequence, not a bug.
- Google connect: primary path = participant's own OAuth client (pre-work); escape
  hatch = the shared client (see ROADMAP research item before the room).
```

- [ ] **Step 4: Guard + FULL suite including integration (needs live `claude` — closes D1a)**

Run: `node --check studio/static/app.js` → ok.
Run: `.venv/Scripts/python -m pytest studio/tests -q` → all pass, including `test_real_workshop_turn_emits_chapter` (Task 7).
Manual: compose once via the shelf drawer → the build result shows the one-line `cd … && claude` install copy with the new caption.

- [ ] **Step 5: Commit**

```bash
git add FACILITATOR.md README.md studio/static/app.js
git commit -m "docs(studio): FACILITATOR runbook + raw-skills GUI install copy (D1a checkpoint, deferred from D0)"
```

**CUT LINE — D1a ships here.** The dossier is the workshop journey; `?ui=chat` is the fallback; building runs through the kept shelf drawer until D1c's signature close. ROADMAP item-2 status note + CHANGELOG ride the landing PR.

---

# Slice D1b — the revision verbs (Tasks 12–13)

**What ships at this cut:** every fossilized answer is rewritable (↺ — cards reopen, downstream goes stale, honest re-settle with "written before your rewrite" marks) and every chapter is regenerable (⟳ — prose replaced in place, fossils and cards preserved). The pending-target override guarantees a retitled verb turn can never open a duplicate section.

### Task 12: Prompt — the rewrite/regenerate contract

**Files:**
- Modify: `studio/system_prompt.py`
- Test: `studio/tests/test_system_prompt.py` (append)

**Interfaces:**
- Produces: `_REVISION_CONTRACT` appended to the workshop prompt (spec §5's prompt-contract addition). Task 13's `[studio event] rewrite` / `[studio event] regenerate` messages rely on the agent having this contract.

- [ ] **Step 1: Write the failing tests** (append to `studio/tests/test_system_prompt.py`)

```python
# --- dossier spec §5: the revision verbs ---

def test_workshop_revision_contract_present():
    p = build_workshop_prompt()
    assert "[studio event] rewrite" in p
    assert "[studio event] regenerate" in p
    assert "do not advance the interview" in p.lower()
    assert "drop picks that no longer fit" in p

def test_architect_has_no_revision_contract(tmp_path):
    from studio.system_prompt import build_system_prompt, write_system_prompt
    assert "[studio event] rewrite" not in build_system_prompt()
    out = write_system_prompt(tmp_path / "sp.md")
    assert out.read_text(encoding="utf-8") == build_system_prompt()
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/Scripts/python -m pytest studio/tests/test_system_prompt.py -v`
Expected: `test_workshop_revision_contract_present` FAILs; architect test passes.

- [ ] **Step 3: Implement.** In `studio/system_prompt.py`, add below `_CHAPTER_CONTRACT`:

```python
_REVISION_CONTRACT = """
# Revisions (the page's rewrite ⟲ and regenerate ⟳ verbs)

- Messages starting with `[studio event] rewrite` or `[studio event] regenerate` come
  from the PAGE, not the participant's voice. Never quote them back.
- On `[studio event] rewrite — question: "…" — previous answer: "…" — new answer: "…"`:
  treat the new answer as the participant's real answer to that question. Re-assert the
  FULL studio state consistent with it — drop picks that no longer fit (the whole-state
  rule does the rest) — and continue the interview from that chapter, reusing the SAME
  chapter title you are revisiting.
- On `[studio event] regenerate chapter "…" — rewrite it fresh, same facts`: rewrite
  that chapter's body text only, from the same facts. Do not advance the interview, do
  not change picks or name, reuse the same chapter title and phase, and do not ask a
  new question unless that chapter ended on one.
"""
```

And in `build_workshop_prompt`, insert it after `_CHAPTER_CONTRACT`:

```python
    parts.append(_CHAPTER_CONTRACT)
    parts.append(_REVISION_CONTRACT)
    if onboarding:
        parts.append(_ONBOARDING_CONTRACT)
```

- [ ] **Step 4: Run to verify pass**

Run: `.venv/Scripts/python -m pytest studio/tests/test_system_prompt.py -v` → all pass.

- [ ] **Step 5: Commit**

```bash
git add studio/system_prompt.py studio/tests/test_system_prompt.py
git commit -m "feat(studio): prompt revision contract — rewrite re-asserts state, regenerate rewrites in place"
```

---

### Task 13: `dossier.js` — rewrite ⟲, regenerate ⟳, pending-target override, stale marks

**Files:**
- Modify: `studio/static/dossier.js`, `studio/static/dossier.css` (append)

**Interfaces:**
- Consumes: `pendingTarget` / `rwSettle` (declared in Task 9), Task 12's prompt contract.
- Produces: `beginRewrite(answerEl)` (wired onto every fossil), the ⟳ head button on every section, and the one-beat pending-target consumption already coded into `settle()` (Task 9). One rewrite in flight at a time.

- [ ] **Step 1: Give fossils the rewrite affordance.** In `dossier.js`, replace `fossilize` (Task 9's version) with:

```js
  function fossilize(text, q, rewritten) {
    const a = document.createElement('div');
    a.className = 'answer';
    if (q) a.dataset.q = q;
    a.textContent = text;              // the brass dash is CSS ::before
    if (rewritten) {
      const chip = document.createElement('span');
      chip.className = 'redone';
      chip.textContent = 'rewritten ↺';
      a.appendChild(chip);             // revision is part of the record (§2)
    }
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'rewrite';
    btn.textContent = '↺ rewrite';
    btn.addEventListener('click', () => beginRewrite(a));
    a.appendChild(btn);
    ((open && open.bodyEl) || $('#dz-live')).appendChild(a);
    return a;
  }
```

- [ ] **Step 2: The rewrite flow.** Add below `fossilize`:

```js
  // ── D1b: rewrite ⟲ (spec §5) — one in flight at a time ──────────────────
  let rw = null;

  function beginRewrite(ans) {
    if (rw || pendingTarget) return;          // finish the open revision first
    const sec = ans.closest('.dz-sec');
    const rec = chapters.find((c) => c.el === sec);
    if (!rec) return;
    const later = chapters.filter((c) => c.n > rec.n);
    later.forEach((c) => c.el.classList.add('stale'));
    document.querySelectorAll('#dz-rail .node').forEach((n) => {
      if (later.some((c) => c.phase === n.dataset.phase)) n.classList.add('stale');
    });
    const note = document.createElement('div');
    note.className = 'stale-note';
    note.textContent = `⟲ rewriting §${String(rec.n).padStart(2, '0')}` +
      ' — the architect will reconsider everything below';
    sec.after(note);
    // choice sections reopen their cards, re-choosable
    const grp = ans.closest('.dz-ask');
    if (grp) grp.querySelectorAll('.choice').forEach((c) => {
      c.disabled = false;
      c.classList.remove('dim');
    });
    // the fossil melts back into a writing line, pre-filled with the old words
    const old = (ans.firstChild && ans.firstChild.textContent || '').trim();
    const q = ans.dataset.q || '';
    const wl = document.createElement('form');
    wl.className = 'writeline';
    wl.innerHTML = '<span class="bar"></span><input autocomplete="off">';
    const inp = wl.querySelector('input');
    inp.value = old;
    ans.replaceWith(wl);
    inp.focus(); inp.select();
    holdWriteline();                          // the rewrite holds the baton
    rw = {
      rec, grp, note, later, wl, q, old,
      finish(text) {
        const marker = document.createElement('div');
        this.wl.replaceWith(marker);
        fossilAt(marker, text, this.q);        // re-fossilize in place, with the chip
        marker.remove();
        this.note.remove();
        if (this.grp) {
          this.grp.querySelectorAll('.choice').forEach((c) => {
            const label = c.querySelector('b') ? c.querySelector('b').textContent : '';
            c.disabled = true;
            c.classList.toggle('picked', label === text);
            c.classList.toggle('dim', label !== text);
          });
        }
        // §5 pending-target override: the NEXT done beat routes to this chapter,
        // regardless of the emitted title, consuming exactly one beat.
        pendingTarget = { rec: this.rec, mode: 'append' };
        const later = this.later, n = this.rec.n;
        rwSettle = () => {
          later.forEach((c) => {
            c.el.classList.remove('stale');
            // honest scope (§5): downstream prose is NOT rewritten — it keeps its
            // text with a quiet mark until the participant regenerates it (⟳)
            if (c.bodyEl.querySelector('.dz-prose') && !c.bodyEl.querySelector('.dz-stale-mark')) {
              const m = document.createElement('div');
              m.className = 'dz-stale-mark';
              m.textContent = `written before your rewrite of §${String(n).padStart(2, '0')}` +
                ' — ⟳ regenerate to refresh';
              c.bodyEl.prepend(m);
            }
            // deterministic card re-settle: a still-unanswered downstream ask folds
            c.bodyEl.querySelectorAll('.dz-ask:not([data-answered])').forEach((w) => {
              w.dataset.answered = 'folded';
              w.querySelectorAll('.choice').forEach((x) => { x.disabled = true; x.classList.add('dim'); });
            });
          });
          document.querySelectorAll('#dz-rail .node.stale').forEach((x) => x.classList.remove('stale'));
        };
        window.queueSend(`[studio event] rewrite — question: "${this.q}"` +
          ` — previous answer: "${this.old}" — new answer: "${text}"`);
        rw = null;
      },
    };
    inp.addEventListener('keydown', (ev) => {
      if (ev.key === 'Enter' && inp.value.trim()) { ev.preventDefault(); rw.finish(inp.value.trim()); }
    });
  }

  // build a re-fossilized answer (with the rewritten chip) at a placeholder position
  function fossilAt(placeholder, text, q) {
    const host = placeholder.parentNode;
    const before = placeholder.nextSibling;
    const saveOpen = open;
    open = { bodyEl: host };            // fossilize appends to open — retarget briefly
    const a = fossilize(text, q, true);
    open = saveOpen;
    host.insertBefore(a, before);
    return a;
  }

  // re-choosing during a rewrite: a delegated handler (the per-card listeners are
  // guarded by data-answered and stay inert on reopened cards)
  document.addEventListener('click', (e) => {
    const ch = e.target.closest('.choice');
    if (!ch || !rw || !rw.grp || !rw.grp.contains(ch)) return;
    const label = ch.querySelector('b') ? ch.querySelector('b').textContent : '';
    if (label) rw.finish(label);
  });
```

(`fossilAt` briefly retargets `open` so `fossilize` appends into the melted answer's own
position, then restores it — the re-fossil lands exactly where the old answer stood, not
at the document tail.)

- [ ] **Step 3: The regenerate verb.** In `newSection` (Task 9), add the quiet head button — change the `sec.innerHTML` block to:

```js
    sec.innerHTML = `
      <div class="sec-head"><span class="no">${String(n).padStart(2, '0')}</span>
        <h2>${esc(ch.title)}</h2>
        <button type="button" class="dz-regen" title="rewrite this chapter fresh">⟳</button>
        <span class="why">${esc(ch.phase)}</span></div>
      <div class="dz-body"></div>`;
```

and after the `rec` is created (before `return rec;`) add:

```js
    sec.querySelector('.dz-regen').addEventListener('click', () => {
      if (pendingTarget || rw) return;        // one revision in flight at a time
      pendingTarget = { rec, mode: 'replace' };   // §5: replaces agent prose ONLY, in place
      sec.classList.add('dz-regenerating');
      holdWriteline();
      window.queueSend(`[studio event] regenerate chapter "${rec.title}" — rewrite it fresh, same facts`);
    });
```

(`settle()` from Task 9 already consumes `mode: 'replace'` — it removes `.dz-prose`/`.dz-error` nodes and preserves fossils, asks, and cards — and `onError` already clears `pendingTarget`, so the target is consumed on that beat, success or error.)

- [ ] **Step 4: D1b styles** — append to `studio/static/dossier.css`:

```css
/* ── D1b: revision verbs (v1b .rewrite/.redone/.stale) ── */
.answer .rewrite { position: absolute; right: 0; top: 4px; font-family: var(--mono);
  font-style: normal; font-size: 10.5px; letter-spacing: .08em; color: var(--ink-4);
  background: none; border: 1px solid var(--rule); border-radius: 999px; padding: 4px 11px;
  cursor: pointer; opacity: 0; transition: opacity .15s, color .15s, border-color .15s; }
.answer:hover .rewrite { opacity: 1; }
.answer .rewrite:hover { color: var(--brass); border-color: var(--brass); }
.answer .redone { font-family: var(--mono); font-style: normal; font-size: 10px;
  letter-spacing: .1em; color: var(--brass); background: var(--brass-tint);
  border-radius: 999px; padding: 3px 9px; margin-left: 10px; vertical-align: middle; }
.dz-sec.stale { opacity: .38; pointer-events: none; filter: saturate(.6); }
.stale-note { margin: 0 0 60px; padding: 12px 18px; border: 1px dashed var(--brass);
  border-radius: 10px; background: var(--brass-tint); font-family: var(--mono);
  font-size: 11.5px; letter-spacing: .06em; color: var(--brass); text-transform: uppercase; }
.dz-stale-mark { font-family: var(--mono); font-size: 10.5px; letter-spacing: .08em;
  color: var(--brass); margin: 0 0 10px; }
.sec-head .dz-regen { background: none; border: none; color: var(--ink-4);
  font-size: 14px; cursor: pointer; opacity: 0; transition: opacity .15s, color .15s; }
.dz-sec:hover .dz-regen { opacity: 1; }
.sec-head .dz-regen:hover { color: var(--brass); }
.dz-sec.dz-regenerating .dz-body { opacity: .5; }
```

- [ ] **Step 5: Syntax + backend guard**

Run: `node --check studio/static/dossier.js` → ok.
Run: `.venv/Scripts/python -m pytest studio/tests -q -m "not integration"` → all pass.

- [ ] **Step 6: D1b MANUAL BROWSER CHECKLIST** (spec §10 D1b — real `claude`)

1. **Rewrite round-trip:** hover a fossilized answer mid-journey → ↺ — the answer melts into a pre-filled writing line; that ask's choice cards (if any) wake re-choosable; every chapter below dims stale; the matching rail milestones go brass; the note bar reads "⟲ rewriting §NN…".
2. Submit a different answer (Enter) → the answer re-fossilizes with the `rewritten ↺` chip; the agent's next beat lands in the SAME chapter (no duplicate section, even though the agent may retitle); stale sections un-dim and each carries the quiet "written before your rewrite of §NN — ⟳ regenerate to refresh" mark; picks/cards re-settle from the beat's whole state (a dropped pick folds its card to a receipt; a downstream unanswered ask folds).
3. Re-choose via a reopened card instead of typing — same round-trip.
4. **One in flight:** while a rewrite is open, other fossils' ↺ and all ⟳ buttons are inert.
5. **Regenerate:** hover a chapter head → ⟳ — the chapter's agent prose is replaced in place on the next beat; its fossils and choice cards are untouched; a retitled regenerate turn does NOT open a duplicate section; the interview does not advance (no new question beyond what the chapter ended on).
6. **Reduced motion + `?mode=architect`:** both unaffected.

- [ ] **Step 7: Commit**

```bash
git add studio/static/dossier.js studio/static/dossier.css
git commit -m "feat(studio): rewrite ⟲ + regenerate ⟳ — pending-target override, honest re-settle, stale marks"
```

**CUT LINE — D1b ships here.** Revision is part of the record; ⟳ is the in-room recovery documented in FACILITATOR.md.

---

# Slice D1c — signature close + the finale (Tasks 14–16) — GATED ON D0

**What ships at this cut:** `ready: true` renders the signature close as the final chapter; Build runs the sign → bind → assemble → first breath → launch-card ceremony (spec §6) over the REAL compose stream and a REAL one-turn greeting from the composed agent home; the launch card carries the real `cd … && claude` command with pending integration chips. Must not start before D0 lands — the first breath and launch command are only real in raw-skills form (spec §7.1).

### Task 14: `studio/first_breath.py` + `POST /api/first-breath`

**Files:**
- Create: `studio/first_breath.py`
- Modify: `studio/server.py`
- Test: Create `studio/tests/test_first_breath.py`; append to `studio/tests/test_server.py` and `studio/tests/test_smoke_integration.py`

**Interfaces:**
- Consumes: `stream_parser.parse_line`/`is_system`/`is_turn_end` + `chat_session.dedup_text`/`resolve_claude` (the §6.4 reuse seam — NOT `ChatSession`), `server.LAST_COMPOSE` (set by `compose_endpoint` from its own done event — path provenance is server-side, never the request body).
- Produces: `build_greeting_prompt(owner_name, picks, integrations, catalog) -> str`; `build_first_breath_argv(claude_bin, prompt, empty_mcp: Path) -> list[str]`; `async first_breath(home: Path, prompt: str, budget: float = 20) -> AsyncIterator[dict]` yielding `token`/`done`/`error` events; `POST /api/first-breath` (SSE). Task 16's ceremony consumes the endpoint.

- [ ] **Step 1: Write the failing tests.** Create `studio/tests/test_first_breath.py`:

```python
# studio/tests/test_first_breath.py
import asyncio
import pytest
from pathlib import Path

from studio.first_breath import build_first_breath_argv, build_greeting_prompt, first_breath

_CAT = {"shelf": {"items": [
    {"id": "tasks", "name": "Task list"}, {"id": "crm", "name": "CRM"}]}}


def test_argv_loads_the_homes_claude_md():
    argv = build_first_breath_argv("claude", "hello", Path("empty-mcp.json"))
    # the §6.4 flag set: the agent home's OWN CLAUDE.md must load —
    # no prompt-replacement flags, tool-less, MCP fenced to an empty config
    assert "--system-prompt-file" not in argv
    assert "--exclude-dynamic-system-prompt-sections" not in argv
    i = argv.index("--allowed-tools")
    assert argv[i + 1] == ""
    assert "--strict-mcp-config" in argv
    j = argv.index("--mcp-config")
    assert argv[j + 1].endswith("empty-mcp.json")
    assert argv[:2] == ["claude", "-p"]
    assert "--output-format" in argv and "stream-json" in argv


def test_greeting_prompt_constrained_to_composed_reality():
    p = build_greeting_prompt("Ada", ["tasks"], ["linear"], _CAT)
    assert "Ada" in p                       # greets the participant by name
    assert "Task list" in p                 # references actual picks
    assert "linear" in p                    # hands into the connect chapters
    assert "promise nothing" in p.lower()   # no unbuilt claims (no scheduling until r1-A)
    assert "do not ask questions" in p.lower()


def test_greeting_prompt_no_integrations_case():
    p = build_greeting_prompt("Ada", ["crm"], [], _CAT)
    assert "none" in p.lower()


class _Proc:
    returncode = 0
    stderr = None
    def __init__(self, lines, stall=0.0):
        self._lines = list(lines)
        self._stall = stall
        self.stdout = self
    async def readline(self):
        if self._stall:
            await asyncio.sleep(self._stall)
        return self._lines.pop(0) if self._lines else b""
    async def wait(self):
        return 0
    def kill(self):
        pass


def _lines():
    import json
    return [
        (json.dumps({"type": "assistant", "message": {"content": [
            {"type": "text", "text": "Morning, Ada. I'm atlas."}]}}) + "\n").encode(),
        (json.dumps({"type": "result"}) + "\n").encode(),
    ]


async def test_stream_yields_tokens_then_done(tmp_path, monkeypatch):
    async def fake_exec(*argv, **kw):
        assert kw.get("cwd") == str(tmp_path)     # cwd IS the agent home
        return _Proc(_lines())
    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)
    monkeypatch.setattr("studio.first_breath.resolve_claude", lambda: "claude")
    evs = [e async for e in first_breath(tmp_path, "greet")]
    assert any(e["type"] == "token" and "atlas" in e["text"] for e in evs)
    assert evs[-1]["type"] == "done"


async def test_budget_exceeded_yields_error_never_hangs(tmp_path, monkeypatch):
    async def fake_exec(*argv, **kw):
        return _Proc(_lines(), stall=60)
    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)
    monkeypatch.setattr("studio.first_breath.resolve_claude", lambda: "claude")
    evs = [e async for e in first_breath(tmp_path, "greet", budget=0.05)]
    assert evs[-1]["type"] == "error" and "budget" in evs[-1]["message"]
```

Append to `studio/tests/test_server.py`:

```python
# --- first breath (dossier spec §6.4) ---

def test_first_breath_preflight_no_compose_never_spawns(monkeypatch):
    server.LAST_COMPOSE = None
    called = {}
    async def never(home, prompt, budget=20):
        called["spawned"] = True
        yield {"type": "token", "text": "x"}
    monkeypatch.setattr(server._first_breath, "first_breath", never)
    c = TestClient(server.app)
    with c.stream("POST", "/api/first-breath") as r:
        body = "".join(r.iter_text())
    assert '"type": "error"' in body and "build" in body
    assert not called                       # preflight negative: error event, never a spawn

def test_first_breath_streams_tokens(monkeypatch, tmp_path):
    _ob(monkeypatch, tmp_path, name="Ada")
    server.LAST_COMPOSE = {"plugin_path": str(tmp_path), "integrations": ["linear"],
                           "picks": ["tasks"], "install": f"cd {tmp_path} && claude"}
    seen = {}
    async def fake_breath(home, prompt, budget=20):
        seen["home"], seen["prompt"] = home, prompt
        yield {"type": "token", "text": "Morning, Ada."}
        yield {"type": "done"}
    monkeypatch.setattr(server._first_breath, "first_breath", fake_breath)
    c = TestClient(server.app)
    with c.stream("POST", "/api/first-breath") as r:
        body = "".join(r.iter_text())
    assert "Morning, Ada." in body and '"type": "done"' in body
    assert seen["home"] == Path(str(tmp_path))     # derived server-side from LAST_COMPOSE
    assert "Ada" in seen["prompt"] and "linear" in seen["prompt"]

def test_compose_done_captured_for_first_breath(monkeypatch, tmp_path):
    _ob(monkeypatch, tmp_path)
    server.LAST_COMPOSE = None
    async def fake_compose(picks, name, outdir, vault_dir):
        yield {"type": "done", "grade": "composed", "plugin_path": str(tmp_path),
               "vault_path": "v", "integrations": ["linear"], "install": "cd x && claude"}
    monkeypatch.setattr(server._composer, "compose", fake_compose)
    c = TestClient(server.app)
    with c.stream("POST", "/api/compose", json={"picks": ["tasks"], "name": "atlas"}) as r:
        "".join(r.iter_text())
    assert server.LAST_COMPOSE["plugin_path"] == str(tmp_path)
    assert server.LAST_COMPOSE["picks"] == ["tasks"]
```

(`from pathlib import Path` is needed at the top of test_server.py if not already imported — it is not today; add it with this task.)

Append to `studio/tests/test_smoke_integration.py`:

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_first_breath_over_composed_home(tmp_path):
    # Compose is deterministic (no LLM) — build a real home, then run one REAL
    # tool-less greeting turn with cwd = the home (dossier spec §10).
    import json as _json
    from studio import composer
    from studio.first_breath import build_greeting_prompt, first_breath
    evs = [e async for e in composer.compose(
        ["crm"], "Ada Smoke", tmp_path / "dist", tmp_path / "dist" / "ada-smoke-cos" / "vault")]
    done = evs[-1]
    assert done["type"] == "done"
    cat = _json.loads((Path(__file__).parent.parent / "catalog.json").read_text(encoding="utf-8"))
    prompt = build_greeting_prompt("Ada", ["crm"], [], cat)
    out = [e async for e in first_breath(Path(done["plugin_path"]), prompt, budget=60)]
    assert any(e["type"] == "token" for e in out), "first breath streamed nothing"
    assert out[-1]["type"] in ("done", "error")
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/Scripts/python -m pytest studio/tests/test_first_breath.py studio/tests/test_server.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'studio.first_breath'`; server tests FAIL on missing route (404)/attr.

- [ ] **Step 3: Implement `studio/first_breath.py`**

```python
# studio/first_breath.py
"""One REAL greeting turn from the freshly composed agent (dossier spec §6 beat 4).

Reuse seam (§6.4): stream_parser.parse_line + chat_session.dedup_text + the wait_for
budget idiom — NOT ChatSession. Its cwd/tempdir, --system-prompt-file, and
exclude-dynamic flags are exactly what first breath must not use: cwd IS the agent
home so its own CLAUDE.md loads (D0's raw-skills form is what makes that possible).
Tool-less via --allowed-tools ""; --strict-mcp-config with an EMPTY MCP config so no
MCP server can spawn without keys. No integration keys are needed for this turn.

The caller (server endpoint) derives `home` from its own compose result — never from
a request body — so a localhost POST can never spawn claude in an arbitrary directory.
Any error or budget overrun yields an `error` event; the page falls back to the static
first-words card (the ceremony never hangs the room).
"""
from __future__ import annotations
import asyncio
import tempfile
from pathlib import Path
from typing import AsyncIterator

from studio import stream_parser as sp
from studio.chat_session import dedup_text, resolve_claude

BUDGET_S = 20.0


def build_greeting_prompt(owner_name: str, picks: list[str],
                          integrations: list[str], catalog: dict) -> str:
    """Constrained to composed reality (§6.4): the participant's name, the actual
    picks, and the still-unconnected integrations — and nothing unbuilt. No scheduling
    promises until r1-A ships the always-on scheduler."""
    by_id = {it["id"]: it for it in catalog.get("shelf", {}).get("items", [])}
    skills = ", ".join(by_id[p]["name"] for p in picks if p in by_id) or "your baseline"
    unconnected = ", ".join(integrations) or "none"
    return (
        f"You have just been composed at the workshop. Greet {owner_name} by name, in "
        f"your own voice, in at most 3 short sentences. Your installed skills: {skills}. "
        f"Integrations not yet connected: {unconnected}. If any are unconnected, say you "
        "are ready the moment they're connected — connecting is the very next page of "
        "the studio. Reference only what is actually installed and promise nothing "
        "else: no schedules, no automatic runs, no tools you don't have. This is "
        "non-interactive; do not ask questions and do not use tools."
    )


def build_first_breath_argv(claude_bin: str, prompt: str, empty_mcp: Path) -> list[str]:
    return [claude_bin, "-p", prompt,
            "--output-format", "stream-json", "--verbose",
            "--include-partial-messages",
            "--allowed-tools", "",
            "--strict-mcp-config", "--mcp-config", str(empty_mcp)]


async def first_breath(home: Path, prompt: str, budget: float = BUDGET_S) -> AsyncIterator[dict]:
    claude_bin = resolve_claude()
    if not claude_bin:
        yield {"type": "error", "message": "`claude` CLI not found on PATH"}
        return
    empty_mcp = Path(tempfile.gettempdir()) / "studio-empty-mcp.json"
    empty_mcp.write_text('{"mcpServers": {}}', encoding="utf-8")
    argv = build_first_breath_argv(claude_bin, prompt, empty_mcp)
    try:
        proc = await asyncio.create_subprocess_exec(
            *argv, cwd=str(home),
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    except (FileNotFoundError, OSError) as e:
        yield {"type": "error", "message": f"couldn't start claude: {e}"}
        return
    loop = asyncio.get_running_loop()
    deadline = loop.time() + budget
    saw_delta = False
    try:
        while True:
            remaining = deadline - loop.time()
            if remaining <= 0:
                raise asyncio.TimeoutError
            raw = await asyncio.wait_for(proc.stdout.readline(), timeout=remaining)
            if not raw:
                break
            event = sp.parse_line(raw.decode("utf-8", "replace"))
            if not event or sp.is_system(event):
                continue
            text, saw_delta = dedup_text(event, saw_delta)
            if text:
                yield {"type": "token", "text": text}
            if sp.is_turn_end(event):
                break
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        yield {"type": "error", "message": f"first breath exceeded the {budget:.0f}s budget"}
        return
    await proc.wait()
    if proc.returncode not in (0, None):
        yield {"type": "error", "message": f"claude exited {proc.returncode}"}
        return
    yield {"type": "done"}
```

- [ ] **Step 4: Wire the server.** In `studio/server.py`:

Add the import (with the other `from studio import …` lines):

```python
from studio import first_breath as _first_breath
```

Add module state below `_DISTILL_TASK` (line 43):

```python
LAST_COMPOSE: dict | None = None   # this studio run's last successful compose done event
```

In `compose_endpoint`'s `stream()` (inside the `async for ev in _composer.compose(...)` loop, line 170-171), capture the done event:

```python
        async for ev in _composer.compose(picks, name, _composer._REPO / "dist", vault):
            if ev.get("type") == "done":
                global LAST_COMPOSE
                LAST_COMPOSE = {**ev, "picks": list(picks)}
            yield _sse(ev)
```

(Python requires the `global` declaration once at the top of `stream()` — place `global LAST_COMPOSE` as the function's first line instead of inline if the linter complains; either form, the assignment must rebind the module global.)

Add the endpoint below `keys_test`:

```python
@app.post("/api/first-breath")
async def first_breath_endpoint() -> StreamingResponse:
    """One real greeting turn from the composed agent (dossier spec §6.4). The agent
    home comes from OUR OWN compose result — never the request body."""
    async def stream():
        done = LAST_COMPOSE
        if not done or not Path(done.get("plugin_path", "")).is_dir():
            yield _sse_preflight_error("no composed agent yet — build first")
            return
        owner = _onboarding.load_state().get("name") or "there"
        try:
            catalog = json.loads(_CATALOG.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            catalog = {"shelf": {"items": []}}
        prompt = _first_breath.build_greeting_prompt(
            owner, done.get("picks", []), done.get("integrations", []), catalog)
        async for ev in _first_breath.first_breath(Path(done["plugin_path"]), prompt):
            yield _sse(ev)

    return StreamingResponse(stream(), media_type="text/event-stream")
```

- [ ] **Step 5: Run to verify pass**

Run: `.venv/Scripts/python -m pytest studio/tests/test_first_breath.py studio/tests/test_server.py -v` → all pass.
Run: `.venv/Scripts/python -m pytest studio/tests -q -m "not integration"` → all pass.

- [ ] **Step 6: Commit**

```bash
git add studio/first_breath.py studio/server.py studio/tests/test_first_breath.py studio/tests/test_server.py studio/tests/test_smoke_integration.py
git commit -m "feat(studio): first breath — one real greeting turn from the composed home, budgeted, preflight-gated"
```

---

### Task 15: `dossier.js` — the signature close + embedded build panel

**Files:**
- Modify: `studio/static/dossier.js`, `studio/static/dossier.css` (append), `studio/static/index.html` (skip button)

**Interfaces:**
- Consumes: `window.streamBuild` (Task 10) with a new additive `opts.onEvent` observer (added to app.js here); `lastStudio` (Task 9).
- Produces: `renderClose(studio)` — the signature close as the final chapter (manifest from **studio picks only**, §4.4); `beginBuild()` — gates mirrored (non-empty picks AND name), the existing `#buildpanel` node physically relocated into the closing chapter (§4.3's morph — hosted, not re-implemented); `lastDone` captured for Tasks 16/18; `unsign(ev)` — the §6.1 failure path. Task 16 rewrites `beginBuild`'s interior into the full ceremony; this task lands the working skeleton (sign → embedded build → wizard rows → done).

- [ ] **Step 1: `streamBuild` gains an event observer.** In `studio/static/app.js`, inside `streamBuild`'s SSE loop, immediately after `const ev = JSON.parse(line);` (app.js:409) add:

```js
      if (opts.onEvent) opts.onEvent(ev);   // additive observer — default rendering unchanged
```

- [ ] **Step 2: The close + build embed.** In `studio/static/dossier.js`, add module state near the top (with the other `let`s):

```js
  let closeRec = null;      // the signature-close chapter record (D1c)
  let lastDone = null;      // last compose done event — install/plugin_path/integrations
  let building = false;
  let signed = false;
```

Extend `onDone` — after the `lastStudio = studio;` line insert:

```js
    if (studio.ready && studio.name && (studio.picks || []).length && !closeRec) renderClose();
    if (closeRec && !signed) refreshManifest();
```

Add the close renderer + build skeleton below `diffPicks`:

```js
  // ── D1c: the signature close (§4.1 step 4) ──────────────────────────────
  function renderClose() {
    closeRec = newSection({ title: 'Sign & build', phase: 'build' });
    closeRec.el.classList.add('closing');
    closeRec.bodyEl.innerHTML = `
      <div class="manifest" id="dz-manifest"></div>
      <div class="sig-row">
        <div class="sigline"><div class="name" id="dz-signame"></div>
          <div class="cap">signed — this is the agent I want</div></div>
        <button type="button" class="buildbtn" id="dz-build">Build my agent<i>▶</i></button>
      </div>
      <div id="dz-stagebox"><div id="dz-beat-host"></div>
        <details class="dz-buildlog-wrap" id="dz-rawlog" hidden>
          <summary>raw build log</summary></details></div>`;
    refreshManifest();
    $('#dz-build').addEventListener('click', beginBuild);
    nudgeScroll();
  }

  // §4.4: the manifest renders from STUDIO PICKS ONLY — the shelf event sync keeps the
  // agent's whole-state picks truthful, so the signed manifest cannot diverge.
  function refreshManifest() {
    const el = $('#dz-manifest');
    if (!el || !lastStudio) return;
    const byId = shelfById();
    const base = (((catalog || {}).baseline || {}).items || []);
    el.innerHTML =
      base.map((b) => `<span class="m lock">🔒 ${esc(b.name)}</span>`).join('') +
      (lastStudio.picks || []).map((id) => {
        const it = byId.get(id);
        return it ? `<span class="m">${esc(it.name)}${it.cost && it.cost.label ? ' · ' + esc(it.cost.label) : ''}</span>` : '';
      }).join('');
    const nm = $('#dz-signame');
    if (nm) nm.textContent = lastStudio.name || '';
    const btn = $('#dz-build');
    // §6.1 gating: non-empty picks AND a name — mirrors the existing gates; the
    // server preflight still sits behind it.
    if (btn) btn.disabled = !(lastStudio.name && (lastStudio.picks || []).length);
  }

  // ── D1c: build — the existing panel embeds as the final chapter (§4.3) ──
  async function beginBuild() {
    if (building || !lastStudio) return;
    const picks = (lastStudio.picks || []).slice();
    const name = lastStudio.name;
    if (!picks.length || !name) return;
    building = true; signed = true;
    const btn = $('#dz-build');
    btn.disabled = true; btn.textContent = '✓ signed';
    holdWriteline();                    // the document is closed for edits (§6.1)
    // the EXISTING build panel physically relocates into the chapter — a morph, not a
    // re-implementation: streamBuild's fixed ids now paint inside the document.
    const panel = $('#buildpanel');
    panel.hidden = false;
    const raw = $('#dz-rawlog');
    raw.hidden = false; raw.open = true;
    raw.appendChild(panel);
    let doneEv = null, failedEv = null;
    await window.streamBuild('/api/compose', { picks, name }, {
      onEvent: (ev) => {
        if (ev.type === 'done') doneEv = ev;
        if (ev.type === 'error') failedEv = ev;
      },
    });
    if (failedEv) { unsign(failedEv); return; }
    lastDone = doneEv;
    building = false;
  }

  // §6.1: a composer error renders INSIDE the ceremony with an un-sign/retry — the
  // signature un-inks and the document reopens for edits.
  function unsign(ev) {
    building = false; signed = false;
    const panel = $('#buildpanel');
    document.querySelector('.rightrail').appendChild(panel);   // give the node back
    panel.hidden = true;
    closeRec.el.classList.remove('signing');
    $('#dz-rawlog').hidden = true;
    $('#dz-beat-host').innerHTML =
      `<div class="dz-error">⚠ ${esc(ev.stage || 'build')}: ${esc(ev.message || 'failed')}` +
      ` — un-signed. Fix it (rewrite an answer, reopen the shelf) and build again.</div>`;
    const btn = $('#dz-build');
    btn.textContent = 'Build my agent ▶';
    refreshManifest();                  // re-enables per the gates
    armWriteline(pendingAsk, true);     // the document reopens
  }
```

- [ ] **Step 3: D1c close styles** — append to `studio/static/dossier.css` (v1b `.closing`/`.manifest`/`.sigline`/`.buildbtn` + v1c `.signing`):

```css
/* ── D1c: the signature close (v1b §05 / v1c beat 0) ── */
.dz-sec.closing { border-top: 2px solid var(--ink); padding-top: 26px; }
.dz-sec.closing .sec-head { border-bottom: none; }
.manifest { display: flex; flex-wrap: wrap; gap: 8px; margin: 0 0 26px; }
.manifest .m { font-family: var(--mono); font-size: 11.5px; padding: 5px 12px;
  border-radius: 999px; background: var(--tint); border: 1px solid var(--tint-2);
  color: var(--sapphire); }
.manifest .m.lock { background: var(--band); border-color: var(--rule); color: var(--ink-3); }
.sig-row { display: flex; align-items: flex-end; gap: 26px; flex-wrap: wrap; }
.sigline { flex: 1; min-width: 240px; }
.sigline .name { font-family: var(--wordmark); font-style: italic; font-size: 30px;
  color: var(--ink); padding: 0 4px 8px; border-bottom: 1.5px solid var(--ink);
  min-height: 44px; position: relative; overflow: hidden; }
.sigline .cap { font-family: var(--mono); font-size: 10px; letter-spacing: .14em;
  text-transform: uppercase; color: var(--ink-4); margin-top: 7px; }
.buildbtn { border: 0; border-radius: 12px; background: var(--sapphire); color: #fff;
  font-family: var(--display); font-weight: 620; font-size: 18px; letter-spacing: -.01em;
  padding: 16px 30px; cursor: pointer; box-shadow: var(--sh-md);
  transition: background .15s, transform .15s; }
.buildbtn:hover { background: var(--sapphire-hover); transform: translateY(-2px); }
.buildbtn:disabled { background: var(--tint-2); color: var(--ink-4); box-shadow: none;
  cursor: default; transform: none; }
.buildbtn i { font-style: normal; margin-left: 8px; }
/* signing: the name inks itself across the line (v1c) */
.dz-sec.signing .name b { font-weight: 400; color: var(--ink);
  animation: dz-inkin 1.4s cubic-bezier(.2,.7,.2,1) both; display: inline-block; }
@keyframes dz-inkin { from { clip-path: inset(0 100% 0 0); } to { clip-path: inset(0 0 0 0); } }
/* the embedded raw build log (§4.3/§6.3: truth under the theater) */
.dz-buildlog-wrap { margin-top: 22px; }
.dz-buildlog-wrap summary { font-family: var(--mono); font-size: 10.5px;
  letter-spacing: .1em; text-transform: uppercase; color: var(--ink-4); cursor: pointer; }
body.dossier #buildpanel { display: block; background: var(--canvas);
  border: 1px solid var(--rule); border-radius: var(--r-card); padding: 14px; margin-top: 10px; }
@media (prefers-reduced-motion: reduce) { .dz-sec.signing .name b { animation: none; } }
```

- [ ] **Step 4: The SKIP affordance (used by Task 16, parked hidden now).** In `studio/static/index.html`, inside the `#dossier` div after `</main>`:

```html
    <button type="button" class="dz-skipper" id="dz-skip" hidden>SKIP ▸▸</button>
```

And append to `dossier.css`:

```css
.dz-skipper { position: fixed; bottom: 18px; right: 20px; font-family: var(--mono);
  font-size: 10.5px; letter-spacing: .1em; color: var(--ink-4); background: var(--canvas);
  border: 1px solid var(--rule); border-radius: 999px; padding: 6px 13px; cursor: pointer; z-index: 45; }
```

- [ ] **Step 5: Syntax + backend guard**

Run: `node --check studio/static/dossier.js && node --check studio/static/app.js` → ok.
Run: `.venv/Scripts/python -m pytest studio/tests -q -m "not integration"` → all pass.
Manual spot-check (real `claude`): reach `ready: true` with a name — the closing chapter renders with manifest chips + the signature line; Build runs the compose embedded in the chapter (stepper/log/wizard rows visible inside the disclosure); a forced preflight error (empty a pick via the shelf first) un-signs and reopens the document.

- [ ] **Step 6: Commit**

```bash
git add studio/static/dossier.js studio/static/dossier.css studio/static/app.js studio/static/index.html
git commit -m "feat(studio): signature close — manifest from studio picks, gated Build, embedded build panel, un-sign on failure"
```

---

### Task 16: `dossier.js` — the finale: sign · bind · assemble · first breath · launch card

**Files:**
- Modify: `studio/static/dossier.js` (rewrite `beginBuild`'s interior into the ceremony), `studio/static/dossier.css` (append)

**Interfaces:**
- Consumes: Task 15's skeleton (`closeRec`, `unsign`, the relocated panel, `opts.onEvent`), `POST /api/first-breath` (Task 14), `done.install`/`done.integrations` (Task 3), catalog `brief`/`deliverable` fields.
- Produces: the five-beat ceremony (spec §6), organ ticks **event-driven, never timed** (§6.3 mapping: spine ← `component: vault`, shell ← `component: shell`, each pick ← `skill:<id>`, identity ← `stage assemble ok` — flagged deviation 10), the launch card with pending chips + `fillChip(integration)` (Task 18 rewires its trigger). SKIP always visible during the ceremony; `prefers-reduced-motion` collapses every beat to a cut.

- [ ] **Step 1: Ceremony helpers.** In `dossier.js`, add near the top (below the `norm` helper):

```js
  const REDUCED = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  let skipping = false;
  const beatWait = async (ms) => { if (!skipping && !REDUCED) await sleep(ms); };
```

- [ ] **Step 2: Replace `beginBuild` (Task 15's skeleton) with the full ceremony:**

```js
  async function beginBuild() {
    if (building || !lastStudio) return;
    const picks = (lastStudio.picks || []).slice();
    const name = lastStudio.name;
    if (!picks.length || !name) return;
    building = true; signed = true; skipping = false;
    const byId = shelfById();
    const skipBtn = $('#dz-skip');
    skipBtn.hidden = false;
    skipBtn.onclick = () => { skipping = true; };
    holdWriteline();                    // the document is closed for edits (§6.1)

    // ── BEAT 1: the signing — the name inks itself across the line ──
    const nm = $('#dz-signame');
    nm.innerHTML = `<b>${esc(name)}</b>`;
    closeRec.el.classList.add('signing');
    const btn = $('#dz-build');
    btn.disabled = true; btn.textContent = '✓ signed';
    await beatWait(1600);

    // ── BEAT 2: the binding — the dossier compresses to a ToC card ──
    // Honest theater: these fragments are the participant's real answers, and they
    // genuinely feed the personalize pass (their profile seeded the session).
    const host = $('#dz-beat-host');
    const rows = chapters.filter((c) => c !== closeRec).map((c) => {
      const a = c.bodyEl.querySelector('.answer');
      const frag = a && a.firstChild ? a.firstChild.textContent.trim() : '';
      return `<div class="row"><b>§${String(c.n).padStart(2, '0')} ${esc(c.title.toUpperCase())}</b>` +
        `<i>${frag ? esc('"' + (frag.length > 44 ? frag.slice(0, 41) + '…' : frag) + '"') : ''}</i></div>`;
    }).join('');
    const nAnswers = document.querySelectorAll('#dossier .answer').length;
    host.innerHTML = `
      <div class="dz-beat on">
        <div class="beatcap">■ binding your dossier — everything you told me becomes its memory</div>
        <div class="toc"><h3>The ${esc(name)} dossier</h3>${rows}
          <div class="stamp">${chapters.length - 1} chapters · ${nAnswers} answers · signed ${new Date().toISOString().slice(0, 10)}</div>
        </div></div>`;
    host.scrollIntoView({ behavior: 'smooth', block: 'center' });
    await beatWait(2200);

    // ── BEAT 3: the assembly — organs tick on REAL compose events, never timers (§6.3) ──
    const organs = [
      { key: 'vault', ic: '🧠', name: 'wiki-brain spine', sub: 'its memory — seeded, yours' },
      { key: 'shell', ic: '⚙️', name: 'chief-of-staff shell', sub: 'identity, your voice, read→decide→act' },
      ...picks.map((id) => ({ key: `skill:${id}`, ic: '🧩',
        name: (byId.get(id) || { name: id }).name, sub: (byId.get(id) || {}).what || '' })),
      // what Assembly does NOT claim: per-answer skill personalization is r1-B — the
      // identity organ's caption says only what actually runs (§6.3)
      { key: 'stage:assemble', ic: '✍️', name: 'identity',
        sub: 'owner name + vault path written into every file' },
    ];
    host.innerHTML = `
      <div class="dz-beat on">
        <div class="beatcap">■ assembling ${esc(name)}</div>
        <div class="anatomy">${organs.map((o) => `
          <div class="organ" data-key="${esc(o.key)}"><span class="ic">${o.ic}</span>
            <div><b>${esc(o.name)}</b><span>${esc(o.sub)}</span></div>
            <span class="tick">✓</span></div>`).join('')}</div>
        <div class="dz-blog" id="dz-blog"></div></div>`;
    const panel = $('#buildpanel');
    panel.hidden = false;
    const raw = $('#dz-rawlog');
    raw.hidden = false;
    raw.appendChild(panel);             // truth under the theater — the raw stream stays reachable
    const tick = (key, cap) => {
      const o = host.querySelector(`.organ[data-key="${CSS.escape(key)}"]`);
      if (o) o.classList.add('in');
      if (cap) $('#dz-blog').insertAdjacentHTML('afterbegin', `<div>$ ${esc(cap)}</div>`);
    };
    let doneEv = null, failedEv = null;
    await window.streamBuild('/api/compose', { picks, name }, {
      onEvent: (ev) => {
        if (ev.type === 'component') tick(ev.key, `${ev.key} → ok`);
        if (ev.type === 'stage' && ev.name === 'assemble' && ev.status === 'ok') {
          tick('stage:assemble', 'owner + vault substitutions applied');
        }
        if (ev.type === 'log') $('#dz-blog').insertAdjacentHTML('afterbegin', `<div>$ ${esc(ev.text)}</div>`);
        if (ev.type === 'done') doneEv = ev;
        if (ev.type === 'error') failedEv = ev;
      },
    });
    if (failedEv) { skipBtn.hidden = true; unsign(failedEv); return; }
    lastDone = doneEv;
    await beatWait(900);

    // ── BEAT 4: first breath — the status chip hands over, the agent speaks (§6.4) ──
    host.innerHTML = `
      <div class="dz-beat on dz-breath">
        <span class="dz-chip" id="dz-chip"><i class="dot"></i><span id="dz-chiptext">architect</span></span>
        <div class="firstwords" id="dz-fw"><span id="dz-tw"></span><span class="caret"></span></div>
      </div>`;
    await beatWait(900);
    $('#dz-chiptext').textContent = `${name} · live`;
    $('#dz-chip').classList.add('alive');
    window.setStatus(`${name} · live`, true);           // the header chip hands over too
    const tw = $('#dz-tw');
    let words = '', fbFailed = false;
    try {
      const r = await fetch('/api/first-breath', { method: 'POST' });
      const reader = r.body.getReader(); const dec = new TextDecoder(); let buf = '';
      while (true) {
        const { value, done } = await reader.read(); if (done) break;
        buf += dec.decode(value, { stream: true });
        let i; while ((i = buf.indexOf('\n\n')) >= 0) {
          const line = buf.slice(0, i).replace(/^data: /, ''); buf = buf.slice(i + 2);
          if (!line) continue;
          const ev = JSON.parse(line);
          if (ev.type === 'token') { words += ev.text; tw.textContent = words; }
          if (ev.type === 'error') fbFailed = true;
        }
      }
    } catch { fbFailed = true; }
    if (fbFailed || !words.trim()) {
      // flagged fallback (§6.4): the ceremony never hangs the room
      $('#dz-fw').innerHTML = `<div class="dz-fw-fallback">“I'm ${esc(name)} — your chief of staff.` +
        ` Run the launch command below and say hello.”` +
        `<span class="dz-fw-flag">offline greeting — the live one meets you in the terminal</span></div>`;
    } else {
      const caret = $('#dz-fw .caret'); if (caret) caret.remove();
    }
    await beatWait(1800);

    // ── BEAT 5: the launch card — real command, chips PENDING (§6.5) ──
    // The old wizard rule gating the install line on connected keys is retired in
    // dossier mode: the command is real from first render; chips carry connect state.
    const ints = (lastDone && lastDone.integrations) || [];
    const base = (((catalog || {}).baseline || {}).items || []);
    const tryLines = picks.slice(0, 3).map((id) => {
      const it = byId.get(id) || {};
      const ask = ((it.brief || '').split('—')[1] || it.what || id).trim().split('.')[0];
      return `<div>“${esc(ask)}” — makes ${esc(it.deliverable || 'its first move')}</div>`;
    }).join('');
    host.innerHTML = `
      <div class="dz-beat on">
        <div class="beatcap">■ your agent</div>
        <div class="launch">
          <div class="lk">agent · built ${new Date().toISOString().slice(0, 10)}</div>
          <h3>${esc(name)}</h3>
          <div class="parts">${base.map((b) => `<span class="m lock">🔒 ${esc(b.name)}</span>`).join('')}
            ${picks.map((id) => `<span class="m">${esc((byId.get(id) || { name: id }).name)}</span>`).join('')}</div>
          <div class="ints" id="dz-launch-ints">${ints.length
            ? ints.map((i) => `<span class="dz-int pending" data-int="${esc(i)}">${esc(i)} · pending</span>`).join(' ')
            : 'no integrations needed — fully local'}</div>
          <div class="cmd"><code>${esc((lastDone && lastDone.install) || '')}</code>
            <button type="button" id="dz-copy">COPY</button></div>
          <div class="try"><div class="t">three things to ask it first</div>${tryLines}</div>
        </div></div>`;
    $('#dz-copy').addEventListener('click', function () {
      if (navigator.clipboard && lastDone) navigator.clipboard.writeText(lastDone.install);
      this.textContent = 'COPIED ✓';
    });
    // chips fill live as the embedded connect rows pass their smoke tests. D1c watches
    // the wizard rows' class flips; D2's wireKeyRow onResult replaces this observer.
    const mo = new MutationObserver(() => {
      panel.querySelectorAll('.keyrow.kr-pass').forEach((row) => fillChip(row.dataset.int));
    });
    mo.observe(panel, { attributes: true, subtree: true, attributeFilter: ['class'] });
    skipBtn.hidden = true;
    skipping = false;
    building = false;
    nudgeScroll();
  }

  // a launch-card integration chip completes (§6.5) — shared with D2's key-field blocks
  function fillChip(integration) {
    const chip = document.querySelector(`.dz-int[data-int="${CSS.escape(integration)}"]`);
    if (chip && chip.classList.contains('pending')) {
      chip.classList.remove('pending');
      chip.classList.add('ok');
      chip.textContent = `${integration} ✓`;
    }
  }
```

- [ ] **Step 3: Finale styles** — append to `studio/static/dossier.css` (lifted from v1c):

```css
/* ── D1c: the finale (v1c beats 1–4) ── */
.dz-beat { transition: opacity .7s ease; }
.dz-beat .beatcap { text-align: center; font-family: var(--mono); font-size: 11px;
  letter-spacing: .15em; text-transform: uppercase; color: var(--ink-3); margin: 26px 0 18px; }
.toc { max-width: 420px; margin: 0 auto; background: var(--canvas); border: 1px solid var(--rule);
  border-radius: var(--r-card); box-shadow: var(--sh-md); padding: 22px 26px; }
.toc h3 { font-family: var(--display); font-size: 16px; color: var(--ink); margin: 0 0 12px; }
.toc .row { display: flex; justify-content: space-between; font-size: 13.5px; padding: 6px 0;
  border-top: 1px dashed var(--rule); }
.toc .row b { font-family: var(--mono); font-weight: 400; font-size: 11px; color: var(--brass); }
.toc .row i { font-family: var(--wordmark); color: var(--ink-3); white-space: nowrap;
  overflow: hidden; text-overflow: ellipsis; max-width: 230px; }
.toc .stamp { margin-top: 14px; font-family: var(--mono); font-size: 10px; letter-spacing: .13em;
  text-transform: uppercase; color: var(--ink-4); text-align: center; }
.anatomy { max-width: 440px; margin: 0 auto; }
.organ { display: flex; align-items: center; gap: 14px; background: var(--canvas);
  border: 1px solid var(--rule); border-radius: 12px; padding: 13px 18px; margin-bottom: 10px;
  opacity: .25; transform: translateX(-10px); transition: all .45s cubic-bezier(.2,.7,.2,1); }
.organ.in { opacity: 1; transform: none; border-color: var(--tint-2); box-shadow: var(--sh-sm); }
.organ .ic { width: 30px; height: 30px; border-radius: 8px; background: var(--tint);
  display: flex; align-items: center; justify-content: center; font-size: 15px; flex-shrink: 0; }
.organ b { font-family: var(--display); font-weight: 620; font-size: 15.5px; color: var(--ink); }
.organ span { font-size: 12.5px; color: var(--ink-3); display: block; }
.organ .tick { margin-left: auto; font-family: var(--mono); color: var(--ink-4); font-size: 13px; }
.organ.in .tick { color: var(--ok); }
.dz-blog { max-width: 440px; margin: 16px auto 0; font-family: var(--mono); font-size: 11px;
  color: var(--ink-4); max-height: 54px; overflow: hidden; line-height: 18px; }
.dz-blog div { animation: dz-logup .3s ease both; }
@keyframes dz-logup { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: none; } }
.dz-breath { text-align: center; padding-top: 30px; }
.dz-chip { display: inline-flex; align-items: center; gap: 8px; font-family: var(--mono);
  font-size: 12px; padding: 6px 14px; border-radius: 999px; background: var(--tint);
  border: 1px solid var(--tint-2); color: var(--ink-3); transition: all .5s ease; }
.dz-chip .dot { width: 7px; height: 7px; border-radius: 50%; background: var(--ink-4); }
.dz-chip.alive { color: var(--sapphire); border-color: var(--sapphire); }
.dz-chip.alive .dot { background: var(--sapphire); animation: dz-pulse 1.8s ease-in-out infinite; }
@keyframes dz-pulse { 50% { opacity: .4; transform: scale(.75); } }
.firstwords { margin: 36px auto 0; max-width: 560px; font-family: var(--display);
  font-weight: 520; font-size: clamp(21px, 3.4vw, 28px); line-height: 1.35;
  letter-spacing: -.015em; color: var(--ink); text-align: left; min-height: 150px;
  white-space: pre-wrap; }
.firstwords .caret { display: inline-block; width: 3px; height: 1em; background: var(--sapphire);
  vertical-align: -2px; animation: dz-blink 1s steps(1) infinite; margin-left: 2px; }
@keyframes dz-blink { 50% { opacity: 0; } }
.dz-fw-fallback { font-size: 19px; color: var(--ink-2); }
.dz-fw-flag { display: block; margin-top: 12px; font-family: var(--mono); font-size: 10px;
  letter-spacing: .12em; text-transform: uppercase; color: var(--brass); }
.launch { max-width: 480px; margin: 0 auto; background: var(--canvas);
  border: 1.5px solid var(--sapphire); border-radius: 16px; box-shadow: var(--sh-md);
  padding: 28px 30px; }
.launch .lk { font-family: var(--mono); font-size: 10px; letter-spacing: .15em;
  text-transform: uppercase; color: var(--sapphire); margin-bottom: 4px; }
.launch h3 { font-family: var(--wordmark); font-style: italic; font-weight: 400;
  font-size: 34px; color: var(--ink); margin: 0 0 16px; }
.launch .parts { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 16px; }
.launch .parts .m { font-size: 10.5px; padding: 4px 10px; }
.launch .ints { font-family: var(--mono); font-size: 11px; margin-bottom: 20px; }
.dz-int.pending { color: var(--warn); }
.dz-int.ok { color: var(--ok); }
.cmd { display: flex; align-items: center; gap: 10px; background: var(--ink);
  border-radius: 10px; padding: 12px 16px; margin-bottom: 18px; }
.cmd code { flex: 1; font-family: var(--mono); font-size: 13px; color: #E8EEF4;
  overflow-x: auto; white-space: nowrap; }
.cmd button { border: 0; border-radius: 7px; background: rgba(255,255,255,.14); color: #fff;
  font-family: var(--mono); font-size: 10.5px; padding: 6px 11px; cursor: pointer; }
.cmd button:hover { background: rgba(255,255,255,.26); }
.try { border-top: 1px dashed var(--rule); padding-top: 14px; }
.try .t { font-family: var(--mono); font-size: 10px; letter-spacing: .13em;
  text-transform: uppercase; color: var(--ink-4); margin-bottom: 8px; }
.try div { font-size: 14.5px; color: var(--ink-2); padding: 3px 0; }
.try div::before { content: '▸ '; color: var(--brass); }
@media (prefers-reduced-motion: reduce) {
  .organ, .dz-beat, .dz-chip { transition: none; }
  .dz-blog div, .dz-chip.alive .dot, .firstwords .caret { animation: none; }
}
```

- [ ] **Step 4: Syntax + backend guard**

Run: `node --check studio/static/dossier.js` → ok.
Run: `.venv/Scripts/python -m pytest studio/tests -q` → all pass, including the two D1c integration smokes (real `claude` — `test_real_first_breath_over_composed_home`).

- [ ] **Step 5: D1c MANUAL BROWSER CHECKLIST** (spec §10 D1c — real `claude`)

1. **The full finale:** journey to `ready` with a name → the closing chapter renders → Build → the name inks across the signature line, button flips to `✓ signed`, writing line retires → the ToC card binds real chapter titles + real answer fragments with the stamp → assembly organs tick as their REAL events arrive (vault, shell, each picked skill, identity on the assemble stage) with mono captions beneath → the chip hands over to `<name> · live` (page AND header) → the composed agent's REAL first words type in, greeting by name, referencing actual picks, handing into connect → the launch card renders with the REAL `cd … && claude` command (copy works) and PENDING integration chips.
2. **SKIP:** visible from the signing on; pressing it cuts every remaining wait and jumps the typing to done.
3. **First-breath fallback:** stop `claude` from resolving (temporarily rename the shim / disconnect) → the static "offline greeting" card renders with the brass flag; the launch card still completes with the real command.
4. **Failure inside the ceremony:** force a compose preflight error → the brass error line renders in the ceremony, the signature un-inks, the button re-arms, the document reopens for edits; fixing and rebuilding works.
5. **Connect completes the card:** paste a real Linear key in the embedded wizard row (raw-log disclosure), Test → green → the launch card's `linear` chip flips to `✓`.
6. **Rebuild after connect:** press Build again — connect rows re-run and the old `.env` is gone (documented consequence, FACILITATOR.md).
7. **Reduced motion:** every beat cuts (no ink-in, no organ slide, no typing cadence — text still arrives).
8. **`?ui=chat` + `?mode=architect`:** both unaffected (old wizard gate still rules the chat skin).

- [ ] **Step 6: Commit**

```bash
git add studio/static/dossier.js studio/static/dossier.css
git commit -m "feat(studio): the finale — sign/bind/assemble on real events, first breath, launch card with pending chips"
```

**CUT LINE — D1c ships here.** The journey ends in a ceremony over a real agent; connect still lives in the embedded wizard rows until D2 dissolves it into chapters.

---

# Slice D2 — build & connect as native chapters (Tasks 17–19)

**What ships at this cut:** the architect walks each integration as a `connect`-phase chapter — `step` lines, a live `key-field` hosting the real smoke-test row, checklists — and the launch-card chips fill from the chapter rows. The connect ROWS in the embedded wizard remain as the fallback surface (raw-log disclosure). **Guide content** (which steps for Discord/Linear/Google) stays ROADMAP item 7 — D2 is the rendering vehicle, not the content.

### Task 17: `wireKeyRow` extraction (the §7.2 named seam)

**Files:**
- Modify: `studio/static/app.js`

**Interfaces:**
- Produces: `window.wireKeyRow(rowEl, integration, tree, onResult)` — the connect-row wiring factored OUT of `wireWizard` (app.js:291-337), the google `persist_only` branch included; `onResult(ok: boolean)` fires after each non-save Test (flagged deviation 5). `window.keyRowHtml` and `window.KNOWN_INTEGRATIONS` exposed for the dossier's `key-field` blocks. `wireWizard` becomes a thin consumer. Task 18 is the second consumer.

- [ ] **Step 1: Extract.** In `studio/static/app.js`, replace `wireWizard` (lines 289–337) with:

```js
// Wire ONE connect row (§7.2's named extraction): paste-fields + Test/Save button →
// /api/keys/test, persisting into `tree` on success. The google row is persist-only
// (can never smoke-test with just a client id/secret). Consumed by BOTH the
// build-panel wizard below and the dossier's key-field blocks (D2).
// `onResult(ok)` fires after each non-save Test round trip.
function wireKeyRow(row, integration, tree, onResult) {
  const btn = row.querySelector('.kr-test, .kr-save');
  if (!btn) return;  // scheduler info row has no button
  const isSave = btn.classList.contains('kr-save');
  const idleLabel = isSave ? 'Save' : 'Test';
  btn.addEventListener('click', async () => {
    const values = {};
    row.querySelectorAll('input[data-key]').forEach((inp) => { values[inp.dataset.key] = inp.value.trim(); });
    const status = row.querySelector('.kr-status');
    btn.disabled = true; btn.textContent = isSave ? 'Saving…' : 'Testing…';
    let out = { ok: false };
    try {
      const r = await fetch('/api/keys/test', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(isSave
          ? { integration, values, tree, persist_only: true }
          : { integration, values, tree }),
      });
      out = await r.json();
      if (isSave) {
        // Save row is informational only — never the green "connected" state.
        row.classList.toggle('kr-saved', !!out.ok); row.classList.toggle('kr-fail', !out.ok);
        status.textContent = (out.ok ? 'ℹ️ ' : '❌ ') + (out.message || '');
      } else {
        row.classList.toggle('kr-pass', !!out.ok); row.classList.toggle('kr-fail', !out.ok);
        status.textContent = (out.ok ? '✅ ' : '❌ ') + (out.message || '');
      }
    } catch (e) {
      row.classList.remove('kr-pass', 'kr-saved'); row.classList.add('kr-fail');
      status.textContent = '❌ ' + e.message;
    } finally {
      btn.disabled = false; btn.textContent = idleLabel;
    }
    if (!isSave && onResult) onResult(!!out.ok);
  });
}
window.wireKeyRow = wireKeyRow;
window.keyRowHtml = keyRowHtml;
window.KNOWN_INTEGRATIONS = new Set([...Object.keys(WIZARD_FIELDS), 'scheduler']);

// Wires the Test buttons + the "finish at home" reveal inside a freshly-rendered
// #buildresult. `keyed` is every integration except scheduler and google (neither
// gates the install line).
function wireWizard(ev, keyed) {
  const passed = new Set();
  const unlock = () => {
    const gate = $('#wizard-gate'); if (gate) gate.hidden = false;
    const finish = $('#wizard-finish'); if (finish) finish.hidden = true;
  };
  if (!keyed.length) unlock();  // e.g. scheduler-only compose — nothing to test
  $('#buildresult').querySelectorAll('.keyrow[data-int]').forEach((row) => {
    const integration = row.dataset.int;
    wireKeyRow(row, integration, ev.plugin_path, (ok) => {
      if (ok) { passed.add(integration); if (keyed.every((i) => passed.has(i))) unlock(); }
    });
  });
  const finishBtn = $('#wizard-finish');
  if (finishBtn) finishBtn.addEventListener('click', unlock);
}
```

(Behavior preserved exactly: same fetch shapes, same class flips, same status glyphs, same gate logic — the loop's per-row body moved into `wireKeyRow`, the gate bookkeeping stayed in `wireWizard` via `onResult`.)

- [ ] **Step 2: Syntax + backend guard + manual check**

Run: `node --check studio/static/app.js` → ok.
Run: `.venv/Scripts/python -m pytest studio/tests -q -m "not integration"` → all pass.
Manual (real `claude`, `?ui=chat` skin for the plain wizard): compose with a Linear pick → Test with a bad key → ❌ red; Test with a real key → ✅ green and the install gate unlocks; google row Saves without a green state and never gates.

- [ ] **Step 3: Commit**

```bash
git add studio/static/app.js
git commit -m "refactor(studio): wireKeyRow extraction — one connect-row wiring for wizard and dossier (§7.2)"
```

---

### Task 18: `dossier.js` — typed-blocks rendering + connect chapters

**Files:**
- Modify: `studio/static/dossier.js` (fill the Task 9 `renderBlocks` stub), `studio/static/dossier.css` (append)

**Interfaces:**
- Consumes: `window.keyRowHtml` / `window.wireKeyRow` / `window.KNOWN_INTEGRATIONS` (Task 17), `lastDone` (Task 15/16), `fillChip` (Task 16), validated `chapter.blocks` (Task 5).
- Produces: the v1 vocabulary renders natively — `step`, `key-field` (hosting the REAL smoke-test row against `lastDone.plugin_path`), `checklist`, `note`, `skill-card`; unknown types/integrations skipped silently (the extractor already drops them; the renderer re-checks defensively). Launch chips fill via `wireKeyRow`'s `onResult` — replace Task 16's MutationObserver trigger comment accordingly (the observer stays for the embedded wizard fallback rows).

- [ ] **Step 1: Fill the stub.** In `studio/static/dossier.js`, replace `function renderBlocks(rec, blocks) {}` (Task 9) with:

```js
  // ── D2: the typed block vocabulary (§3.2), interleaved after the beat's prose ──
  function renderBlocks(rec, blocks) {
    (blocks || []).forEach((b) => {
      if (b.type === 'step') {
        rec.bodyEl.insertAdjacentHTML('beforeend',
          `<div class="dz-step"><b>${esc(String(b.n || '·'))}</b><span>${esc(b.text)}</span></div>`);
      } else if (b.type === 'note') {
        rec.bodyEl.insertAdjacentHTML('beforeend', `<div class="dz-note">${esc(b.text)}</div>`);
      } else if (b.type === 'checklist') {
        rec.bodyEl.insertAdjacentHTML('beforeend',
          `<div class="dz-checklist">${b.items.map((i) =>
            `<div class="dz-check">☐ ${esc(i)}</div>`).join('')}</div>`);
      } else if (b.type === 'skill-card') {
        const it = shelfById().get(b.id);
        if (it) rec.bodyEl.insertAdjacentHTML('beforeend',
          `<div class="dz-cards">${skillCardHtml(it, 'skill')}</div>`);
      } else if (b.type === 'key-field') {
        // hosts the EXISTING connect row (§3.2/§7.2) — never a reimplementation
        if (!window.KNOWN_INTEGRATIONS || !window.KNOWN_INTEGRATIONS.has(b.integration)) return;
        if (!lastDone || !lastDone.plugin_path) {
          rec.bodyEl.insertAdjacentHTML('beforeend',
            '<div class="dz-note">build first — keys connect after the signing</div>');
          return;
        }
        const host = document.createElement('div');
        host.className = 'dz-keyhost';
        host.innerHTML = window.keyRowHtml(b.integration);
        const row = host.firstElementChild;
        rec.bodyEl.appendChild(host);
        window.wireKeyRow(row, b.integration, lastDone.plugin_path,
          (ok) => { if (ok) fillChip(b.integration); });   // the launch card completes (§6.5)
      }
      // unknown types never reach here — the extractor drops them (§3.2); the
      // if/else chain skips anything unexpected anyway.
    });
  }
```

- [ ] **Step 2: D2 styles** — append to `studio/static/dossier.css`:

```css
/* ── D2: typed blocks (§3.2) ── */
.dz-step { display: flex; gap: 12px; align-items: baseline; margin: 10px 0 0 18px;
  font-size: 15.5px; color: var(--ink-2); }
.dz-step b { font-family: var(--mono); font-weight: 400; font-size: 11px; color: var(--brass);
  border: 1px solid var(--rule); border-radius: 999px; padding: 2px 8px; flex: none; }
.dz-note { margin: 14px 0 0 18px; padding: 10px 14px; border-left: 3px solid var(--tint-2);
  background: var(--tint); border-radius: 0 10px 10px 0; font-size: 14px; color: var(--ink-3); }
.dz-checklist { margin: 12px 0 0 18px; }
.dz-check { font-family: var(--mono); font-size: 12.5px; color: var(--ink-3); padding: 3px 0; }
.dz-keyhost { margin: 16px 0 0 18px; }
.dz-keyhost .keyrow { background: var(--canvas); border: 1px solid var(--rule);
  border-radius: var(--r-card); box-shadow: var(--sh-sm); padding: 14px 16px; }
```

(The `.keyrow`/`.kr-*` internals keep their existing `styles.css` rules — the host only frames the row as dossier material.)

- [ ] **Step 3: Syntax + backend guard**

Run: `node --check studio/static/dossier.js` → ok.
Run: `.venv/Scripts/python -m pytest studio/tests -q -m "not integration"` → all pass.

- [ ] **Step 4: D2 MANUAL BROWSER CHECKLIST** (spec §10 D2 — real `claude`, a real Linear key)

1. **A connect chapter end to end:** after the finale, prompt the architect toward connecting (e.g. "let's connect Linear") — a `connect`-phase chapter renders numbered `step` lines, then the real Linear key row, then a checklist; paste a real key → Test → ✅ green inside the document; the launch card's `linear` chip flips to `✓`; a wrong key → ❌ with the smoke's message.
2. **Persistence:** the `.env` lands in the composed home (open `dist/<name>-cos/.env`) exactly as the wizard path writes it — same endpoint, same tree.
3. **Unknown vocabulary skipped silently:** temporarily prompt the agent to emit a bogus block type and a `key-field` with a made-up integration (facilitator console: send a crafted message) — nothing renders for them, the rest of the chapter is intact, no console errors.
4. **Pre-build key-field:** force a connect chapter before any build — the quiet "build first" note renders instead of a dead row.
5. **Rail:** the `connect` milestone colours in.
6. **`?ui=chat`:** the old wizard-in-build-panel flow still works end to end (Task 17's refactor holds).

- [ ] **Step 5: Commit**

```bash
git add studio/static/dossier.js studio/static/dossier.css
git commit -m "feat(studio): typed blocks render — steps/notes/checklists/skill-cards + key-field hosting the real smoke row"
```

---

### Task 19: Prompt — the block-authoring contract (build/connect phases only)

**Files:**
- Modify: `studio/system_prompt.py`
- Test: `studio/tests/test_system_prompt.py` (append)

**Interfaces:**
- Produces: `_BLOCKS_CONTRACT` in the workshop prompt — the §3.2 vocabulary with the §7.2 rule (blocks only in build/connect phases; `integration` from the fixed id set).

- [ ] **Step 1: Write the failing tests** (append to `studio/tests/test_system_prompt.py`)

```python
# --- dossier spec §3.2/§7.2: block authoring ---

def test_workshop_blocks_contract_present():
    p = build_workshop_prompt()
    assert '"blocks"' in p
    for t in ('"step"', '"key-field"', '"checklist"', '"note"', '"skill-card"'):
        assert t in p
    assert "ONLY in build/connect phases" in p
    assert "google, discord, linear, scheduler" in p

def test_architect_has_no_blocks_contract(tmp_path):
    from studio.system_prompt import build_system_prompt, write_system_prompt
    assert '"key-field"' not in build_system_prompt()
    out = write_system_prompt(tmp_path / "sp.md")
    assert out.read_text(encoding="utf-8") == build_system_prompt()
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/Scripts/python -m pytest studio/tests/test_system_prompt.py -v`
Expected: `test_workshop_blocks_contract_present` FAILs; architect test passes.

- [ ] **Step 3: Implement.** In `studio/system_prompt.py`, add below `_REVISION_CONTRACT`:

```python
_BLOCKS_CONTRACT = """
# Build & connect chapters (typed blocks)

- ONLY in build/connect phases, the chapter may carry a "blocks" array the page renders
  natively, after your prose. Closed vocabulary — exactly these shapes:
  {"type": "step", "n": 1, "text": "Open linear.app → Settings → API → Personal API keys"}
  {"type": "key-field", "integration": "linear", "label": "Paste your Linear API key"}
  {"type": "checklist", "items": ["Key created", "Key pasted", "Smoke test green"]}
  {"type": "note", "text": "Keys stay on this machine — written into your agent's .env."}
  {"type": "skill-card", "id": "tasks"}
- "integration" must be one of: google, discord, linear, scheduler.
- Walk ONE integration per chapter: 2–4 short steps, then its key-field, then a
  checklist. The key-field renders a live paste-and-test row — after emitting it, tell
  the participant to paste and press Test, then wait for their word before moving on.
- Never emit blocks outside build/connect phases.
"""
```

And in `build_workshop_prompt`, insert after `_REVISION_CONTRACT`:

```python
    parts.append(_REVISION_CONTRACT)
    parts.append(_BLOCKS_CONTRACT)
    if onboarding:
        parts.append(_ONBOARDING_CONTRACT)
```

- [ ] **Step 4: Run to verify pass**

Run: `.venv/Scripts/python -m pytest studio/tests/test_system_prompt.py -v` → all pass.

- [ ] **Step 5: Commit**

```bash
git add studio/system_prompt.py studio/tests/test_system_prompt.py
git commit -m "feat(studio): block-authoring contract — connect chapters walk one integration at a time"
```

**CUT LINE — D2 ships here.** Connect is dossier material; the compose/tweak stream stays an embedded log permanently (a log is a machine process's honest form, §4.3). Guide CONTENT remains ROADMAP item 7.

---

# Slice D3 — intake as the opening chapter (Tasks 20–21)

**What ships at this cut:** the onboarding walk (welcome → introduce yourself → materials drop → second-brain choice) renders as `welcome`-phase dossier chapters — drop zone and name/path fields as chapter content — with the C3 overlay/dock retired in dossier mode. Same `onboarding.py` endpoints, state file, staging, and `[studio event]` completions — **zero backend change** (spec §7.3). `?ui=chat` keeps the C3 chat-card walk.

### Task 20: `dossier.js` — the dossier-native intake

**Files:**
- Modify: `studio/static/dossier.js`, `studio/static/app.js` (start() gate), `studio/static/dossier.css` (append), `studio/system_prompt.py` (one wording line) + `studio/tests/test_system_prompt.py` (no changes needed — verify)

**Interfaces:**
- Consumes: `/api/onboarding`, `/api/onboarding/name|materials|materials/done|second-brain|complete` (existing, unchanged), `window.startWorkshopSession`, `window.queueSend`, Task 9's `fossilize`/`newSection`/`open`.
- Produces: `window.dossier.intake(state)` — app.js routes first-launch dossier boots here instead of `onboardWalk`; the C3 overlay + floating dock never mount in dossier mode (retired); `?ui=chat` keeps `onboardWalk` unchanged. One prompt-wording tweak: the onboarding contract's "panel on their right" becomes surface-neutral (the fields are IN the page now; `?ui=chat` still shows a panel, so the neutral phrasing serves both).

- [ ] **Step 1: The intake flow.** In `studio/static/dossier.js`, add below the writing-line section:

```js
  // ── D3: intake as the opening chapter (§7.3 — zero backend change) ──────
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

  async function intake(state) {
    await getCatalog();
    window.onboardingActive = true;     // suppress chat-skin paints; dossier owns the page
    const rec = newSection({ title: 'Welcome', phase: 'welcome' });
    rec.bodyEl.innerHTML = `
      <p class="dz-prose">Before anything else — who are you? Your chief of staff should
      know its owner by name.</p>
      <form class="dz-intake-name"><input id="dz-ob-name" type="text" maxlength="60"
        placeholder="your name" autocomplete="off" value="${esc((state && state.name) || '')}">
        <button type="submit">→</button></form>`;
    updateRail();
    const form = rec.bodyEl.querySelector('.dz-intake-name');
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const inp = $('#dz-ob-name');
      const name = inp.value.trim();
      if (!name || inp.disabled) return;
      inp.disabled = true;
      const out = await post('/api/onboarding/name', { name });
      if (!out.ok) { alert(out.message); inp.disabled = false; return; }
      form.remove();
      fossilize(name, 'What should your chief of staff call you?');
      await window.startWorkshopSession('Begin onboarding.');   // agent greets by name
      materialsStep();
    });
  }

  function materialsStep() {
    const host = (open || newSection({ title: 'Welcome', phase: 'welcome' })).bodyEl;
    const registered = [];
    const wrap = document.createElement('div');
    wrap.className = 'dz-intake';
    wrap.innerHTML = `
      <div class="dz-drop" tabindex="0">⤓ drop your CV, LinkedIn screenshots, anything you've written
        <small>registered locally — nothing leaves your machine</small></div>
      <input type="file" class="dz-file-input" multiple hidden>
      <div class="dz-chips"></div>
      <label class="dz-field">or link a folder by path
        <input type="text" class="dz-folder" placeholder="e.g. ~/notes"></label>
      <div class="dz-intake-foot">
        <button type="button" class="dz-ob-skip">skip for now</button>
        <button type="button" class="dz-ob-go">That's everything →</button>
      </div>`;
    host.appendChild(wrap);
    const drop = wrap.querySelector('.dz-drop');
    const fileInput = wrap.querySelector('.dz-file-input');
    const chips = wrap.querySelector('.dz-chips');
    const addChip = (label, ok) => {
      const c = document.createElement('span');
      c.className = 'dz-mchip' + (ok ? ' ok' : '');
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
    const folder = wrap.querySelector('.dz-folder');
    folder.addEventListener('keydown', async (e) => {
      if (e.key !== 'Enter') return;
      e.preventDefault();
      const out = await post('/api/onboarding/materials', { folder: folder.value.trim() });
      if (!out.ok) { alert(out.message); return; }
      addChip(folder.value.trim(), true); registered.push(folder.value.trim());
      window.queueSend(`[studio event] linked folder: ${folder.value.trim()}`);
      folder.value = '';
    });
    let answered = false;
    const finishMaterials = async (skipped) => {
      if (answered) return; answered = true;
      wrap.querySelectorAll('button').forEach((b) => { b.disabled = true; });
      if (skipped) await window.queueSend('[studio event] participant skipped sharing materials');
      else await post('/api/onboarding/materials/done', {});    // distiller starts now
      wrap.replaceWith(Object.assign(document.createElement('div'),
        { className: 'dz-receipt', textContent: registered.length ? `${registered.length} shared ✓` : 'materials skipped' }));
      pathStep();
    };
    wrap.querySelector('.dz-ob-skip').addEventListener('click', () => finishMaterials(true));
    wrap.querySelector('.dz-ob-go').addEventListener('click', () => finishMaterials(false));
  }

  function pathStep() {
    const host = (open || newSection({ title: 'Welcome', phase: 'welcome' })).bodyEl;
    const wrap = document.createElement('div');
    wrap.className = 'dz-intake';
    wrap.innerHTML = `
      <label class="dz-field">Where should its memory live? One folder you own, plain
        files — everything it learns about you lives here.
        <input type="text" class="dz-path" value="~/second-brain"></label>
      <div class="dz-intake-foot">
        <button type="button" class="dz-ob-skip">skip for now</button>
        <button type="button" class="dz-ob-go">This is home →</button>
      </div>`;
    host.appendChild(wrap);
    let answered = false;
    const finish = async (skipped) => {
      if (answered) return; answered = true;
      wrap.querySelectorAll('button').forEach((b) => { b.disabled = true; });
      const path = skipped ? '~/second-brain'
        : (wrap.querySelector('.dz-path').value.trim() || '~/second-brain');
      const out = await post('/api/onboarding/second-brain', { path });
      if (!out.ok && !skipped) {
        alert(out.message);
        wrap.remove();
        return pathStep();               // fresh fields — same retry shape as C3
      }
      if (skipped) await window.queueSend('[studio event] participant skipped choosing — defaulted to ~/second-brain');
      const shown = out.ok ? (out.second_brain || path) : path;
      wrap.replaceWith(Object.assign(document.createElement('div'),
        { className: 'dz-receipt', textContent: `home chosen ✓ ${shown}` }));
      completeIntake();
    };
    wrap.querySelector('.dz-ob-skip').addEventListener('click', () => finish(true));
    wrap.querySelector('.dz-ob-go').addEventListener('click', () => finish(false));
  }

  async function completeIntake() {
    // Stream the distill, hand the profile to the live agent — same shape as C3's
    // completeStep, ending in the interview, never a stuck page (try/finally).
    try {
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
          if (ev.type === 'error') { onError(ev.message); return; }
        }
      }
      const state = await (await fetch('/api/onboarding')).json();
      const note = distilled ? 'Distilled profile:' : 'Materials registered but not yet distilled. Stub profile:';
      await window.queueSend(`[studio event] second brain created at ${state.second_brain}. ${note}\n${profile}`);
    } catch (e) {
      console.error('dossier intake complete failed', e);   // never strand the page
    } finally {
      window.onboardingActive = false;
      armWriteline(pendingAsk, true);       // the interview is live in the same document
    }
  }
```

And extend the export line at the bottom of the IIFE:

```js
  window.dossier = { activate, tryReplay, onToken, onError, onDone, intake };
```

- [ ] **Step 2: Retire the C3 mount in dossier mode.** In `studio/static/app.js` `start()` (Task 10's version), replace the onboarding gate body:

```js
    if ((force || !ob.completed)) {
      if (UI === 'dossier' && window.dossier.intake) {
        await window.dossier.intake(ob);   // D3: intake IS the opening chapter (§7.3)
        return;
      }
      if (window.onboardWalk) {
        window.onboardWalk.begin(ob);      // ?ui=chat keeps the C3 chat-card walk
        return;
      }
    }
```

(Delete the `if (UI === 'dossier') document.body.classList.add('onboarding');` line — the dock never mounts in dossier mode any more. The `body.dossier.onboarding` CSS stays: harmless, and `?ui=chat` never adds `dossier`.)

- [ ] **Step 3: Prompt wording (surface-neutral walk).** In `studio/system_prompt.py` `_ONBOARDING_CONTRACT` (line 189), change:

```python
- The walk, in order — narrate each step and point the participant to the panel on their
  right, ONE step at a time:
```

to:

```python
- The walk, in order — narrate each step and point the participant to the drop/choice
  controls the page is showing them, ONE step at a time:
```

Run: `.venv/Scripts/python -m pytest studio/tests/test_system_prompt.py -v` → all pass (no test pins the "panel on their right" phrasing — verified against test_system_prompt.py, which asserts only `"studio event"` presence for this contract).

- [ ] **Step 4: D3 styles** — append to `studio/static/dossier.css`:

```css
/* ── D3: intake as chapter content (§7.3) ── */
.dz-intake { margin: 16px 0 0 18px; }
.dz-intake-name { margin: 14px 0 0 18px; display: flex; gap: 10px; }
.dz-intake-name input { flex: 0 1 280px; font-family: var(--wordmark); font-style: italic;
  font-size: 21px; color: var(--ink); border: 0; outline: 0; background: transparent;
  border-bottom: 1px dashed var(--rule-strong); padding: 2px 0; }
.dz-intake-name input:focus { border-bottom-color: var(--brass); }
.dz-intake-name button { background: var(--sapphire); color: #fff; border: none;
  border-radius: 10px; padding: 4px 16px; font-size: 16px; cursor: pointer; }
.dz-drop { border: 1.5px dashed var(--sapphire); background: var(--tint); border-radius: 12px;
  padding: 22px 16px; text-align: center; color: var(--sapphire); font-size: 14.5px; cursor: pointer; }
.dz-drop.over { background: var(--tint-2); }
.dz-drop small { display: block; color: var(--ink-3); font-size: 11.5px; margin-top: 5px; }
.dz-chips .dz-mchip { display: inline-block; font-family: var(--mono); font-size: 10.5px;
  background: var(--tint); border: 1px solid var(--tint-2); color: var(--sapphire);
  border-radius: 999px; padding: 2px 8px; margin: 8px 4px 0 0; }
.dz-chips .dz-mchip.ok { background: var(--ok-t); border-color: var(--ok); color: var(--ok); }
.dz-field { display: block; font-size: 13.5px; color: var(--ink-3); margin-top: 12px; }
.dz-field input { display: block; width: 100%; margin-top: 6px; font-family: var(--mono);
  font-size: 13px; color: var(--ink); border: 1px solid var(--rule-strong);
  border-radius: 8px; padding: 8px 10px; background: var(--canvas); }
.dz-intake-foot { display: flex; justify-content: flex-end; gap: 12px; margin-top: 12px; }
.dz-intake-foot .dz-ob-go { background: var(--sapphire); color: #fff; border: none;
  border-radius: var(--r-btn); padding: 8px 16px; font-weight: 600; cursor: pointer; }
.dz-intake-foot .dz-ob-skip { background: none; border: none; color: var(--ink-4);
  font-size: 12.5px; cursor: pointer; }
```

- [ ] **Step 5: Syntax + backend guard**

Run: `node --check studio/static/dossier.js && node --check studio/static/app.js` → ok.
Run: `.venv/Scripts/python -m pytest studio/tests -q -m "not integration"` → all pass.

- [ ] **Step 6: D3 MANUAL BROWSER CHECKLIST** (spec §10 D3 — real `claude`; delete `studio/.cache/onboarding.json` first)

1. **Intake as the opening chapter:** first launch renders chapter `01 Welcome` with the name line IN the document (no full-screen overlay, no floating dock); submitting the name fossilizes it and the agent's REAL greeting streams into the same chapter.
2. **Materials drop:** drop 2 files + link a folder — chips flip green in the chapter; the agent acknowledges each `[studio event]` in its own words; "That's everything →" folds the drop zone to a receipt and the distiller starts.
3. **Second brain:** the path field renders as chapter content; confirming creates the home, streams the distill, and the agent reacts WITH SPECIFICS from the materials; the interview continues in the same document — no reset, writing line armed.
4. **Skip-all path:** `?onboard=1`, skip both steps → stub profile, graceful agent reaction, journey continues.
5. **Retired overlay:** `#onboard-overlay` and the dock never appear in dossier mode; `?ui=chat` + `?onboard=1` still runs the full C3 overlay walk unchanged.
6. **Reload mid-intake:** reload after the name step — beats replay restores the document and the session resumes (materials state is server-side; re-render shows the walk beats as chapters).
7. **Reduced motion + `?mode=architect`:** unaffected.

- [ ] **Step 7: Commit**

```bash
git add studio/static/dossier.js studio/static/app.js studio/static/dossier.css studio/system_prompt.py
git commit -m "feat(studio): intake as the opening chapter — drop zone + name/path as dossier material, C3 overlay retired in dossier mode"
```

---

### Task 21: QA close-out — full suite, doctor, placeholder scan, dress-rehearsal gate

**Files:** none (verification only).

- [ ] **Step 1: Full suite including integration** (needs live `claude`)

Run: `.venv/Scripts/python -m pytest studio/tests -q`
Expected: all pass — including `test_real_workshop_turn_emits_chapter`, `test_real_first_breath_over_composed_home`, and the pre-existing real-turn/distill smokes.

- [ ] **Step 2: Launcher preflight**

Run: `.venv/Scripts/python -m studio --doctor` → green (no launcher change was made; this guards against accidental import-time breakage).

- [ ] **Step 3: Placeholder-contract + boundary scan**

```bash
git diff main --stat -- chief-of-staff agent-architect
git diff main | grep -iE "lin_api|xoxb|AIza|@gmail|d885fd34|504fb62b|ikigaiventures"
```
Expected: the `chief-of-staff` diff contains ONLY Task 4's scope (deleted `.claude-plugin/`, deleted `marketplace.json`, README/INSTALL wording); `agent-architect` untouched; the grep is empty.

- [ ] **Step 4: Frontend syntax sweep**

```bash
node --check studio/static/app.js && node --check studio/static/dossier.js && node --check studio/static/shelf.js && node --check studio/static/cards.js && node --check studio/static/onboard.js
```
Expected: silence.

- [ ] **Step 5: Review + rehearsal gate**

1. `/code-review` on the branch; address every Critical + Improvement; re-run the suite.
2. Flag for the landing PR: the **fresh-machine dress rehearsal** (spec §11.2 — clone → `--doctor` → full dossier journey → `cd dist/<name>-cos && claude` → skill triggers) is the release gate for the packaging switch AND the `?ui=chat` retirement decision; it is run by a human before the room, not by this plan.

- [ ] **Step 6: Commit (only if review fixes landed)** — per-fix commits as usual; no omnibus commit.

**CUT LINE — D3 ships here.** One experience from first launch to working agent, entirely in the document. The later cleanup slice (post-rehearsal) removes `?ui=chat` — deliberately NOT in this plan.

---

## Self-review notes

**Spec-coverage map (spec § → tasks):**
- §1 thesis / `?ui=chat` escape hatch → Task 10 (UI switch, routing); §1 architect byte-identity → guarded in Tasks 6/12/19 tests + checklist items.
- §2 design language → Task 8 (dossier.css from v1b) + Tasks 13/15/16/18/20 (per-slice style appends); type scale in Task 10 checklist #14.
- §3.1 chapter field → Task 5 (extractor) + Task 7 (SSE passthrough pin); §3.2 blocks vocabulary → Task 5 (validation, D1a accepted-and-ignored), Task 18 (rendering), Task 19 (authoring contract); §3.3 prompt contract → Task 6.
- §4.1 beats→chapters, live-edge staging, picks-diff, asks+baton, fossils, ready step, errors, beats replay → Task 9 (engine) + Task 7 (server beats) + Task 15 (ready step); §4.2 rail → Task 9; §4.3 build embed → Task 15; §4.4 replacement table → Tasks 8/10 (takeover, advanced dropped, shelf kept + event sync, status chip kept).
- §5 rewrite/regenerate/pending-target/prompt addition → Tasks 12–13.
- §6 finale beats 1–5 (incl. gating/un-sign, honest assembly mapping, first-breath flags/provenance/fallback, launch-card pending chips, `done.install`) → Tasks 14–16 (+ Task 3 supplies `shell` event + install field; Task 18 completes the chips via `wireKeyRow`).
- §7.0 D0 → Tasks 1–4 (commit order honored; `installLineHtml` deferral honored to Task 11); §7.1 D1a/b/c composition → Tasks 5–11 / 12–13 / 14–16 (D1c gated after Task 4 by plan order); §7.2 D2 → Tasks 17–19; §7.3 D3 → Task 20; §7.4 reuse (ask channel, [card]/[studio event], cards.js, onboarding.py, tolerant parsing) → consumed, never rebuilt (Tasks 9/10/20).
- §8 non-goals: no persistence-across-restarts task, no guide-content task, no new deps, substrate untouched outside Task 4 — correct.
- §9 docs → Task 4 (substrate README/INSTALL), Task 11 (FACILITATOR + SETUP/GUI copy); ROADMAP/CHANGELOG ride each landing PR (flagged deviation 1).
- §10 testing → D0 composer tests (Tasks 1–3: tree form, install field, reference-path invariant, CLAUDE.md lean fields, shell event, mcp-trim survival, placeholder grep in Task 4); first breath incl. preflight negative (Task 14); beats replay + 404 (Task 7); extractor negatives incl. per-block field negatives + chapter-failure-never-kills-picks (Task 5); prompt tests (Tasks 6/12/19); SSE chapter (Task 7); integration smokes (Tasks 7/14, run in 11/16/21); named manual checklists D1a→Task 10, D1b→Task 13, D1c→Task 16, D2→Task 18, D3→Task 20.
- §11 risks: collision rule in Global Constraints; packaging-switch rehearsal in Task 21; contract-compliance fallback in Tasks 5/9 + ⟳; DOM-growth note (flagged deviation 6); fence discipline in Global Constraints.

**Cut-line preservation:** Tasks 1–4 = D0 (independently shippable, frontend untouched); 5–11 = D1a (ships with shelf-drawer builds and the C3 dock); 12–13 = D1b; 14–16 = D1c (gated on D0 by ordering); 17–19 = D2; 20–21 = D3. Each slice ends on a commit with the suite green and a named cut-line statement; no task reaches forward across a cut line (Task 9's `renderBlocks` stub and `pendingTarget` declaration are deliberate seams consumed later in the same file, inert until then).

**Type-consistency check:**
- `extract_studio` → `{picks, name, ready, ask, chapter}` (T5) = what `_extract` stores → what `done`/beats carry (T7) = what `dossier.onDone(ev.studio)` reads (T9) = what `renderBlocks` receives (T18).
- `chapter.blocks[*]` per-type shapes (T5) = exactly the keys T18 renders (`n/text`, `integration/label`, `items`, `text`, `id`).
- Beat `{user, prose, studio}` (T7 ChatSession) = the endpoint payload (T7 server) = `replayBeat`'s reads (T9).
- `compose` done `{plugin_path, vault_path, integrations, install, grade}` (T3) = `LAST_COMPOSE` (+`picks`) (T14) = `lastDone` reads in T15/T16/T18.
- `first_breath(home: Path, prompt: str, budget)` (T14 module) = the endpoint call = both fakes' signatures in tests.
- `wireKeyRow(rowEl, integration, tree, onResult)` (T17) = wireWizard's consumption (T17) = the dossier key-field's (T18); `keyRowHtml`/`KNOWN_INTEGRATIONS` exposed where consumed.
- `window.dossier.{activate, tryReplay, onToken(acc), onError(msg), onDone(ev)}` (T9) = app.js's exact call sites (T10); `intake(state)` added T20 = app.js's T20 gate.
- Extractor `_INTEGRATIONS` (T5) = prompt's id list (T19) = `WIZARD_FIELDS`+scheduler (`KNOWN_INTEGRATIONS`, T17).

**Placeholder scan:** every step carries complete code or a precise anchored edit; the only conditional step is Task 1 Step 4's invariant-miss remedy, which names the fix location (`_rewrite_reference_paths`) and the prohibition (never edit substrate content). No TBDs.
