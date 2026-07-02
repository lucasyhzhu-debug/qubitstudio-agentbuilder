# Workshop Studio — "anyone builds their agent in the room" (compose + tweak)

**Date:** 2026-07-01
**Status:** Draft (brainstorm output — pending shipshape gate 1)
**Target:** QubitStudio "Build Your Own Chief of Staff" workshop, Friday
**Author:** Lucas Zhu
**Depends on:** studio shelf baseline (catalog.json + shelf drawer + update-workshop), landed on main via #25

> **Revision r1 (2026-07-02, proofing round 1 on the participant-journey mockups):** three design
> changes from Lucas's review — (1) **Personalize is per-skill**, not a single voice pass: each picked
> skill carries its own use-case questions and a scoped tailoring pass (§6). (2) **Participants
> provision their OWN integrations live** — own Discord server + bot, own Linear workspace, own Google
> Cloud OAuth client — guided by walkthrough guides baked into the wizard; the facilitator prepares
> guides and troubleshoots instead of pre-building shared infra (§2.1, §7, §8). (3) **Always-on is in
> scope**: the studio registers the OS scheduled task that keeps cron-style skills (drain, briefing)
> running — install alone never wakes them. The v1 sections below are left **as-shipped** (PR #27);
> the full r1 design lives in
> **`docs/superpowers/specs/2026-07-02-workshop-studio-r1-personalize-own-infra-always-on-design.md`**
> — pending Lucas review + shipshape gate.

---

## 1. Problem

On Friday, a room of participants must each walk out with a **working, personalized chief-of-staff
agent** they built themselves through the `studio/` browser interface. Today the studio can only
**generate a brand-new plugin from scratch** via agent-architect — which is (a) slow, (b) variable
in quality, (c) able to fail mid-session, and (d) requires a Windows-only PowerShell launcher and a
fully pre-configured machine. None of that survives contact with a mixed room of twenty people on
their own laptops.

This phase closes the gap between the *local single-user demo* the studio is today and *anyone in
the room drives it to a guaranteed-working agent*.

## 2. Locked decisions (from brainstorm)

| Decision | Choice | Why |
|---|---|---|
| **Where builds run** | Each participant, **own laptop** | No hosting, no multi-user server, no shared state |
| **Auth** | **BYO local `claude` login** — no API key | App already shells to `claude -p`; zero shared secret, no single rate-limit, each build on its own quota |
| **Build output** | **Compose real skills, then tweak** | A guaranteed-working agent exists *before* any LLM step; personalization can fail without ruining the session |
| **Shelf model** | **Full à la carte incl. keyed skills, keys provisioned live in-room** — *journey engineered to succeed* | User pick: most faithful to the shelf; success comes from shared infra + a guided/validated key wizard, not from cutting scope. **Superseded by r1** — see the revision note above |
| **Setup stance** | **Assume worst** — mixed OS, not everyone has Claude Code | Cross-platform launcher + a loud pre-flight doctor + emailed pre-work |

### 2.1 "Journey engineered to succeed" — the three levers (grounded in §9)

Full à la carte with live keys is the most ambitious path; these three mechanisms are what make it
work for a room of twenty rather than collapsing on per-person provisioning:

1. **Shared workshop infrastructure — participants CONSUME, not CREATE.** The inventory (§9.5)
   confirms Discord bot/guild/channels and the Linear workspace are *shared*, and the Google OAuth
   client id/secret are shared across refresh labels. So the facilitator pre-creates **one** Discord
   server + bot, **one** Linear workspace, and **one** Google OAuth client. Each participant then only
   (a) pastes handed-out shared values, and (b) runs the Google *consent* flow to mint **their own**
   refresh token (their calendar/mail, their token). This removes the hardest, slowest, most
   failure-prone steps (GCP project + OAuth app creation, Discord bot creation) from the room entirely.
2. **Guided + validated key wizard in the studio.** Post-compose, a "Connect integrations" step lists
   exactly the integrations the picked skills need, with paste fields pre-seeded with the shared
   values, a **Test** button per integration that runs a real smoke check, and a ✅/❌ result. Reuses
   new cross-platform Python smokes (google/discord/linear; `google-smoke.ps1` = Windows reference,
   not the primary — review I1). Nobody leaves with a silently-broken agent — the wizard turns "set 12
   env vars from a README" into a validated flow.
3. **Transitive-dep-safe composer.** Copy the shared substrate (all skills' `references/` + `agents/`
   + top-level `references/`) wholesale so no pick ever hard-breaks on a missing file (§9.3); warn on
   soft skill→skill routing gaps rather than failing.

## 3. Architecture overview

Three new units, one UI rewire, one doc surface. Each has a single purpose and a clean interface.

```
python -m studio  ──►  studio/__main__.py     (stdlib-only launcher + doctor)
                          │  bootstrap venv, deps, preflight (claude auth!), open browser, run uvicorn
                          ▼
   shelf picks ──►  POST /api/compose  ──►  studio/composer.py   (DETERMINISTIC, no LLM)
                          │  scaffold starter vault (templates) + copy shared substrate + picked skills
                          │  de-Lucas placeholders → dist/<name>-cos/ ; emit build-panel SSE
                          ▼
   tweak form  ──►  POST /api/tweak    ──►  studio/tweaker.py    (structured subst + ONE claude -p voice pass)
                          │  fill owner placeholders; rewrite identity/voice
                          ▼
   connect     ──►  POST /api/keys/test ─►  studio/smokes.py     (per-integration validation)
   integrations             │  paste shared values → Test → ✅/❌ → write dist/<name>-cos/.env
                          ▼
                    working, connected plugin  ──►  /plugin marketplace add <dist/<name>-cos> ; /plugin install <name>@…
   (facilitator pre-builds shared Discord+Linear+Google infra → credentials handout: participants paste, not create)
```

The **generate-from-scratch** path (architect chat → `/api/export`) is **kept** as an "advanced"
mode but is no longer the workshop default. Compose is the default.

### Design-for-isolation contract

| Unit | Does | Interface | Depends on |
|---|---|---|---|
| `studio/__main__.py` | Bootstrap + preflight + launch | `python -m studio [--doctor] [--no-open] [--port N]` | stdlib only (must run *before* deps exist) |
| `studio/composer.py` | Scaffold vault + copy substrate + picks into a de-Lucas-ed plugin tree | `compose(picks, name, outdir) -> AsyncIterator[event]` | `catalog.json`, `chief-of-staff/`, `studio/templates/vault/` (read-only) |
| `studio/tweaker.py` | Apply owner fields + one voice pass to a composed tree | `tweak(tree, fields) -> AsyncIterator[event]` | `resolve_claude()`, the composed tree |
| `studio/smokes.py` | Validate a pasted key set against the live integration | `smoke(integration, values) -> {ok, message}` | google-smoke (reused) + discord/linear probes |
| shelf.js / server | Route "Build my agent" → compose → tweak → connect, reuse build panel | `/api/compose`, `/api/tweak`, `/api/keys/test` | composer/tweaker/smokes |
| `studio/SETUP.md` + `studio/FACILITATOR.md` + hub | Participant pre-work (verified by `--doctor`) + facilitator shared-infra runbook | docs | `update-workshop` skill (2nd repo) |

## 4. Unit: cross-platform launcher + doctor (`studio/__main__.py`)

**Purpose:** one command, any OS, that turns "assume worst" into "verified-ready", and fails loud
and early with copy-paste fixes for the one thing that actually breaks the room (missing/unauthed
`claude`).

- **Stdlib-only** — it must run on a machine with *no venv and no deps yet*, so it can create them.
  It uses only `sys`, `os`, `subprocess`, `shutil`, `venv`, `argparse`, `socket`, `urllib`.
- `python -m studio` (default): ensure `.venv` exists (create with `venv` if not), `pip install -r
  requirements.txt` **idempotently** (skip when an import-probe of `fastapi`+`uvicorn` in the venv
  already succeeds), run the doctor, open the browser, then `exec` uvicorn **from the venv
  interpreter**.
- `python -m studio --doctor`: run the preflight checks ONLY and exit non-zero on failure. This is
  the **pre-work command** participants run days before to confirm readiness.
- **Doctor checks** (each prints ✅/❌ + a fix line for the participant's OS):
  1. Python ≥ 3.10.
  2. `claude` on PATH (`shutil.which("claude")`). ❌ → print the install line + `claude auth login`.
  3. `claude` **authed** — best-effort smoke: `claude -p "reply READY" --max-turns 1` with a short
     timeout (≈25 s). Success/timeout-tolerant: a clean non-zero with an auth error string ⇒ ❌ "run
     `claude auth login`"; a timeout ⇒ ⚠️ "couldn't confirm — if builds hang, re-run `claude auth
     login`". (This is the single highest-value check — it catches the one failure that silently
     kills every build.)
  4. Deliverable deps importable in the venv (`fastapi`, `uvicorn`; compose itself needs no pptx).
  5. Port free (`socket` bind test; if taken, pick the next and report it).
  6. `git` on PATH (the composer `git init`s the vault and skills run `git -C` — review R2). ❌ →
     print the install line for their OS.
- `run.ps1` becomes a **thin shim** that calls `python -m studio` (keeps the muscle-memory command
  working on Windows); a sibling one-liner is documented for mac/Linux.

**Why not a static binary / Docker:** over-engineered for Friday; Python is a reasonable pre-req and
the venv pattern already exists in the repo. The doctor's job is to make the pre-req *visible*, not
to eliminate it.

## 5. Unit: composer (`studio/composer.py`) — the deterministic core

**Purpose:** given the shelf picks, assemble a **real, working, de-Lucas-ed** chief-of-staff plugin
with zero LLM calls, so it *always* succeeds. This is the guaranteed floor.

**Signature:** `async def compose(picks: list[str], owner_name: str, outdir: Path) ->
AsyncIterator[dict]` — yields the same event shapes the build panel already renders (`{"type":
"stage", ...}`, `{"type": "component", "key": "skill:crm", ...}`, `{"type": "log", ...}`,
`{"type": "done", "plugin_path": ...}` / `{"type": "error", ..., "handoff": ...}`).

**Steps:**
1. **Resolve** — read `catalog.json`; validate every pick id exists in `shelf.items`; union their
   `requires` to compute the integration set. Reject unknown ids with a clear error.
2. **Scaffold the starter vault** (§9.1) — the baseline is an *external vault*, not plugin files, so
   the composer seeds a fresh `<vault>/` from `studio/templates/vault/`: templated `personality.md`
   + `memories.md` (owner placeholders), empty `lessons.md`, empty `people/` + `meetings/`, and
   `drain-state.json` only if `drain` is picked. `git init` the vault (the skills expect git-backed).
   The composed plugin points at it via `WIKI_ROOT`. De-Lucas by construction — templates, not copies.
3. **Copy the shared substrate + picked skills** (§9.2, §9.3) — always copy the plugin shell
   (`plugin.json` renamed, `marketplace.json`, `agents/context-gatherer.md`, top-level `references/`)
   and **all skills' `references/` subdirs wholesale** (inert markdown when their SKILL.md is absent;
   eliminates the hard-break class). Then copy each picked skill's `SKILL.md`. Warn (don't fail) when
   a pick's soft `needs_skills` routing targets aren't among the picks.
4. **De-Lucas + de-Windows rewrite (the dominant composer task — see review C1)** — the vault path
   `{{VAULT_PATH}}` is **hardcoded in 72 places** across 6 of 7 skills, `context-gatherer.md`,
   and the references (only `intake` reads `WIKI_ROOT`). The composer must rewrite **every** occurrence
   — both prose paths and `git -C "{{VAULT_PATH}}" …` commands — to the participant's chosen
   vault path, OS-appropriate. This is a deterministic find-replace (no LLM) but the largest single
   piece of composer work, not a footnote. Alongside it: `OWNER_USER_ID`→`OWNER_USER_ID`, the hardcoded
   Linear team/project UUIDs (`d885fd34…`/`504fb62b…`) → `{{LINEAR_TEAM_ID}}`/`{{LINEAR_PROJECT_ID}}`,
   and `Lucas Zhu` author → the participant. Vault prose is fully substituted to a **real path** at
   compose time (not a placeholder — the agent won't work otherwise); structured ids the tweak fills.
5. **Assemble** — write `.claude-plugin/plugin.json` (participant's name/desc, composed skill list),
   a per-participant **`marketplace.json`** (cos's copied `marketplace.json` rewritten so `name`/`source`
   point at the composed plugin — required for install, see C2), a **merged `.mcp.json`** with only the
   servers the picks require, and a **README** listing exactly which keys/env vars to set (from
   `requires` + the env inventory §9) and the real two-step install.
6. **Package** — land the tree at `dist/<name>-cos/`. Install is the cos convention (C2): `/plugin
   marketplace add <abs path to dist/<name>-cos>` → `/plugin install <name>@<their-marketplace>` →
   restart. Emit `done`.

**Failure stance:** compose is pure file I/O over in-repo sources — it can only fail on a bad pick
id or a filesystem error, both reported immediately. It never leaves a half-agent: it builds into a
temp dir and moves into place on success (atomic-ish), else emits `error` with a handoff note.

## 6. Unit: tweaker (`studio/tweaker.py`) — personalization

**Purpose:** turn the composed generic-but-working agent into *theirs*, without regenerating logic.

**Signature:** `async def tweak(tree: Path, fields: dict) -> AsyncIterator[dict]`.

Two clearly separated mechanisms:
- **Structured fields → deterministic substitution.** `owner_name`, `discord_channel_id`,
  `google_account`, `linear_team`, `user_id` fill the `{{OWNER_*}}` placeholders the composer
  seeded. Pure string replacement across the tree. Always safe.
- **Voice → ONE tool-enabled `claude -p` pass.** Given a few sentences of the participant's writing,
  rewrite ONLY the identity/voice file's tone section to match. Scoped with `--allowed-tools Read Edit`
  (SEPARATE argv tokens — `--allowed-tools` is variadic; a space-joined `"Read Edit"` becomes one bogus
  tool, per the exporter.py warning) and `--add-dir <tree>` so it can touch only the composed tree.
  **Non-fatal:** on failure or
  timeout, the composed agent keeps its neutral default voice and tweak reports a soft warning — the
  agent still works. This preserves the "guaranteed floor": the fragile LLM step can fail without
  ruining the participant's result.

**Why one pass, not full conversational personalization of every skill:** YAGNI for Friday. The
structured ids + a single voice rewrite cover what a participant actually notices. Deep per-skill
conversational tailoring is deferred (it's the old generate path's territory).

## 7. UI rewire (`shelf.js`, `index.html`, `server.py`)

- The shelf's primary CTA changes from **"Brief the consultant ▶"** (which sends a chat message to
  the architect to *generate*) to **"Build my agent ▶"**, which:
  1. prompts for the participant's name (single field, inline),
  2. `POST /api/compose {picks, name}` and swaps in the **existing build panel** (reuse — the
     composer emits the same SSE protocol),
  3. on `done`, reveals a compact **tweak form** (name prefilled, voice textarea), which `POST
     /api/tweak` and streams the personalization,
  4. then a **"Connect integrations" wizard** (the §2.1 lever #2) — only shown if the picks require
     keys. It lists each required integration (google / discord / linear), with paste fields
     **pre-seeded** with the shared workshop values, a **Test** button per integration → `POST
     /api/keys/test {integration, values}` runs the smoke and returns ✅/❌ + message, and writes the
     validated values on success. Local-only picks (crm/intake) skip this entirely and are done.
  5. shows the real **two-step install** (C2) once each required integration is green (or explicitly
     "finish at home"): `/plugin marketplace add <abs path to dist/<name>-cos>` → `/plugin install
     <name>@<their-marketplace>` → restart Claude Code.
- `server.py` gains `/api/compose`, `/api/tweak`, and `/api/keys/test` (SSE where streaming;
  `/api/keys/test` may be plain JSON). Compose/tweak state keyed like builds (`BUILDING` guard
  reused/renamed to avoid double-runs).
- **Key persistence (cross-platform) — OS env, not `.env` (review C3):** the skills + `google-smoke.ps1`
  read **OS environment** (`google-smoke` reads Windows `User`-scope via `setx`); **nothing sources a
  `.env`**. So the wizard writes OS env the native way — `setx VAR value` on Windows (with the
  **clear-history caveat**: secrets like `GOOGLE_OAUTH_CLIENT_SECRET` / refresh tokens must not linger
  in PowerShell history), `export` lines appended to the shell profile on mac/Linux — and echoes a
  `dist/<name>-cos/.env` copy **for reference only** (not a runtime source unless a future loader is
  added). No claim that `.env` is read at runtime.
- **Smokes (new cross-platform Python — review I1):** google → a new Python probe taking the pasted
  values as input (mint token per `google-auth.md`, call calendarList), with `google-smoke.ps1` as the
  Windows reference only; discord → a REST `GET /users/@me` with the `DiscordBot` User-Agent (per the
  [[discord-rest-user-agent-cloudflare]] gotcha — a wrong UA 403s and
  looks like an auth error); linear → a GraphQL `viewer { id }` probe.
- The architect chat + `/api/export` remain wired for an "advanced: design from scratch" affordance,
  but the workshop run-of-day drives compose.

## 8. Doc surface: pre-work + hub (`studio/SETUP.md` + `update-workshop`)

- `studio/SETUP.md` — the participant pre-work, emailed 2–3 days out: (1) install Claude Code +
  `claude auth login`; (2) install Python 3.10+; (3) `git clone` the repo; (4) run `python -m studio
  --doctor` — green means ready. Cross-platform commands.
- Wire the same prerequisites into the **workshop hub** prerequisites section via the
  `update-workshop` skill (`qubit-site/app/workshop/page.tsx`). **`qubit-site` is a separate repo** —
  its change needs its own commit; flag in the plan.
- `studio/FACILITATOR.md` — the **shared-infra prep runbook** (the §2.1 lever #1), done by Lucas
  before Friday: create the workshop Discord server + bot (record token/guild/channel IDs), the Linear
  workspace (record team/project IDs + issue a key or invite), and the Google OAuth client (record
  client id/secret), then assemble the **credentials handout** participants paste into the wizard. This
  is what turns "20 people each create a GCP project + Discord bot" into "20 people paste + consent."

## 9. Composition inventory (grounded — read-only scan of the real tree)

### 9.1 The baseline is an EXTERNAL VAULT, not plugin files (key finding)

The catalog's "wiki-brain spine" + "cos shell" baseline is **not files inside `chief-of-staff/`**.
The agent's identity, voice, and memory live in an external git-backed markdown vault (Lucas's is at
`{{VAULT_PATH}}`), which the skills read on every invocation:

- `meta/chief-of-staff/personality.md` — the agent's voice (loaded once per conversation)
- `meta/memories.md` — owner facts + one-hop wiki links
- `meta/chief-of-staff/lessons.md` — learned behaviors (seed empty)
- `meta/chief-of-staff/drain-state.json` — runtime watermarks (gitignored; only if `drain` picked)
- `people/` — CRM pages (kebab-keyed) · `meetings/` — meeting records

**Implication:** "compose the baseline" = **scaffold a fresh starter vault from templates** (a new
`studio/templates/vault/` seed), NOT copy Lucas's vault. This is de-Lucas-by-construction and is a
first-class deliverable. The composed plugin's skills point at the participant's vault via `WIKI_ROOT`.

### 9.2 Plugin shell (always copied)

`.claude-plugin/plugin.json` (rename), `.mcp.json` (trim to required servers), `marketplace.json`,
`agents/context-gatherer.md` (the shared read-phase — **no skill functions without it**),
`references/google-auth.md`, `references/google-workspace-sa-setup.md`.

### 9.3 Skills are densely cross-coupled (key finding → needs a skill-dep graph)

Per-skill dependency map (from the scan):

| Skill | Tier | Cross-skill / shared deps it pulls in | Env/keys |
|---|---|---|---|
| **crm** | free | `crm/references/crm-page-format.md`; vault `people/` | none (filesystem) |
| **intake** | free | `intake/references/classification.md`; routes → tasks, crm, wiki-brain:ingest | `WIKI_ROOT` |
| **briefing** | google | `context-gatherer`; `references/google-auth.md`; `briefing/references/{briefing-format,meeting-page}.md` | Google\*, `DISCORD_BOT_TOKEN`, `DISCORD_CHANNEL_*` |
| **scheduling** | google | `context-gatherer`; crm skill; `google-auth.md`; `scheduling/references/scheduling-state.md`; `drain/references/{linear-api,discord-threads}.md` | Google\*, `LINEAR_API_KEY`, `DISCORD_BOT_TOKEN` |
| **tasks** | linear | Linear **connector** (`mcp__claude_ai_Linear__*`) — interactive, not headless | none (connector) |
| **capture** | (not on shelf) | `drain/references/{discord-threads,linear-api}.md`, `crm/references/crm-page-format.md`, `briefing/references/meeting-page.md`, `tasks/SKILL.md`, `capture/references/capture-state.md` | `DISCORD_BOT_TOKEN`, `LINEAR_API_KEY` |
| **drain** | many | `context-gatherer`; `drain/references/{drain-state,linear-api,discord-threads}.md`; routes → intake, tasks, crm, scheduling, wiki-brain:ingest | `LINEAR_API_KEY`, `DISCORD_BOT_TOKEN`, `OWNER_USER_ID`, Google\* |

Two kinds of dependency:
- **Hard (reference-file paths):** a SKILL.md points at `skills/<other>/references/*.md`. Missing ⇒
  broken. **Mitigation:** copy the shared substrate (all `references/` subdirs of *all* skills, plus
  `agents/` + top-level `references/`) wholesale — they're inert markdown when the owning SKILL.md
  isn't present, cheap to over-include, and eliminate the hard-break class entirely.
- **Soft (skill→skill routing):** e.g. `drain` routes to `intake`. Missing ⇒ graceful degrade (that
  route just doesn't fire). Encoded as a new **`needs_skills`** array per shelf item — an *additive*
  `catalog.json` schema change (review R1); the `update-workshop` skill's consistency invariants must
  learn about it so the three surfaces don't drift — so the composer can *warn* (not hard-fail) when a
  pick's routing targets aren't included.

### 9.4 De-Lucas substitution set

| Literal | Where | Becomes |
|---|---|---|
| voice, biographical facts | vault `personality.md`, `memories.md` | **template** (scaffolded, then tweak fills) |
| Linear team `d885fd34-…`, project `504fb62b-…` | `drain/references/linear-api.md` (line ~4) | `{{LINEAR_TEAM_ID}}` / `{{LINEAR_PROJECT_ID}}` |
| `OWNER_USER_ID` | drain confirm-gate (env-driven) | participant sets own `OWNER_USER_ID` |
| Google account emails, Discord channel IDs | env vars (`GOOGLE_EMAIL_*`, `DISCORD_CHANNEL_*`) | participant sets own; README lists them |
| author `Lucas Zhu <lucas@…>` | `plugin.json`, `marketplace.json` | participant name |

Skill *bodies* are mostly env-var-driven (config, not embedded "Lucas") — good. The concentrated
de-Lucas targets are the **vault identity templates** and the **hardcoded Linear UUIDs**.

### 9.5 MCP + env/key contract

`.mcp.json` declares only **discord** (`mcp-discord`, `DISCORD_TOKEN=${DISCORD_BOT_TOKEN}`). Linear &
Google are headless curl/GraphQL (no MCP). The composer trims `.mcp.json` to discord only if a
Discord-needing skill is picked. Full env contract the setup README must list, **filtered to picks**:
`GOOGLE_ACCOUNTS`, `GOOGLE_EMAIL_<LABEL>`, `GOOGLE_AUTH_KIND_<LABEL>`, `GOOGLE_OAUTH_CLIENT_ID/SECRET`,
`GOOGLE_REFRESH_TOKEN_<LABEL>` | `GOOGLE_SA_KEY_PATH_<LABEL>`, `DISCORD_BOT_TOKEN`, `DISCORD_GUILD_ID`,
`DISCORD_CHANNEL_{DAILY_BRIEFS,INBOX,LONG_FORM}`, `LINEAR_API_KEY`, `OWNER_USER_ID` (was `OWNER_USER_ID`),
`WIKI_ROOT`.

> The composer's correctness is defined by this section; the shipshape gate verifies it against the
> real tree. The two "key findings" (external vault, dense coupling) are the reason for the scope
> decision in §10.

## 10. Scope & sequencing (YAGNI)

The target is option 3 (full à la carte + live keys), engineered to succeed. To keep Friday safe, the
build is layered so there is a **working floor at every stage** — if a later layer slips, the room
still succeeds at the layer below.

**Layer 1 — everyone can start & compose (guaranteed floor):**
- Launcher + doctor (§4) — without it, nobody starts.
- Composer: transitive-dep-safe copy + starter-vault scaffold + de-Lucas templating (§5, §9) — the
  actual deliverable; produces a working local-only agent (crm/intake) with zero keys.
- Minimal shelf rewire to drive compose + show install line (§7 steps 1–3, 5).
- `SETUP.md` + hub prerequisites (§8).

**Layer 2 — keyed skills succeed in-room (the option-3 win):**
- `FACILITATOR.md` shared-infra runbook + credentials handout (§8, §2.1 lever #1).
- "Connect integrations" wizard with per-integration **Test/smoke** validation (§7 step 4, §2.1
  lever #2) + `.env` persistence.

**Layer 3 — enhancement (deferred-safe):**
- Voice `claude -p` pass (§6) — structured-field substitution ships in Layer 1; the LLM voice rewrite
  is the enhancement. If it slips, the agent still personalizes on structured fields.

> **Firm boundary (review I3):** Layer 1 is the **hard commitment** for Friday — the demoable floor is
> a composed, de-Lucas-ed, personalized **local-only** agent (crm/intake, zero keys). With C1 (the
> 72-occurrence vault rewrite + cross-platform paths) and C2 (marketplace install wiring) now correctly
> sized, **Layer 2 (keyed skills + wizard) is explicit stretch**, not a Friday guarantee. A Layer-2
> slip degrades to "compose now, finish keys at home" — never to "nothing works." The plan must treat
> this as a boundary, not just prose.

## 11. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Participant has no Claude Code / not authed | Doctor catches it at the door + pre-work `--doctor`; #1 failure, handled first |
| cos skills are heavily Lucas-coded → composed agent leaks "Lucas" | De-Lucas templating (§5.4) grounded in the inventory (§9); shipshape verifies the substitution set is complete |
| A copied skill references a helper not copied → broken agent | Copy the shared substrate wholesale (§9.3); soft routing gaps warn, not fail; verify by loading the composed plugin |
| LLM voice pass fails mid-workshop | Non-fatal by design (§6) — composed agent works without it |
| Mixed OS breaks the launcher | Stdlib-only, OS-detecting `__main__.py`; `run.ps1` shim keeps Windows muscle-memory |
| `qubit-site` change forgotten | Plan flags it as a separate repo/commit (per update-workshop skill) |
| 20× live key provisioning eats the room / silent failures | Shared infra so participants paste not create (§2.1 #1); per-integration Test/smoke so failures surface immediately (§2.1 #2); layered scope so keys can slip to take-home (§10) |
| Discord smoke 403s with a wrong User-Agent (looks like bad token) | Use the `DiscordBot (<url>,<ver>)` UA per [[discord-rest-user-agent-cloudflare]] |
| `setx` leaks secrets into PowerShell history | `.env` is the canonical persistence; `setx` offered only with the clear-history caveat (§7) |
| Google consent flow (per-person refresh token) stalls | Shared OAuth client removes GCP/app creation; only the consent script runs per person; smoke confirms the minted token before they leave |

## 12. Testing

- **Composer**: unit tests over fixture pick-sets — assert the output tree contains the scaffolded
  vault (templated identity, empty people/meetings, drain-state only when drain picked), the shared
  substrate (all `references/` + `context-gatherer.md`), each picked skill's `SKILL.md`, a `.mcp.json`
  trimmed to required servers, a `plugin.json` with the right skill list + participant author, and
  **no residual owner literals** — grep the tree for `Lucas`, `OWNER_USER_ID`, the hardcoded Linear
  UUIDs (`d885fd34…`, `504fb62b…`), and **the vault path** (`Documents.wiki-brain` — the 72-occurrence
  C1 surface) → must be zero. Assert soft `needs_skills` gaps emit a warning event, not an error, and
  that a per-participant `marketplace.json` with the composed `name`/`source` is written (C2).
  Deterministic, no `claude`.
- **Doctor**: unit tests over stubbed `shutil.which` / subprocess for the check branches (claude
  present/absent, authed/timeout, port free/taken, python version).
- **Tweaker**: unit test the structured substitution (placeholder → value across the tree); the voice
  `claude -p` pass is validated by the opt-in integration smoke (spawns real claude), like the exporter.
- **Smokes**: unit test that each probe builds the right request (esp. the discord `DiscordBot` UA)
  and maps success/failure JSON → `{ok, message}`; live validation is manual/integration-lane.
- **End-to-end**: `python -m studio --doctor` green on a clean checkout; a compose run on a fixture
  pick-set yields an installable tree that `/plugin install` accepts. Live browser + real-claude +
  real-key flows stay in the user-run manual QA / `pytest studio -m integration` lane (they can't run
  headless in the sandbox).
