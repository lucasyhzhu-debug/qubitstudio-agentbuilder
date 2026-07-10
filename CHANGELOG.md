# Changelog

## 0.7.0 — 2026-07-10 — Studio three doors, self-updating homes, substrate v0.10.0

Reconciled onto `main`'s substrate-wide `needs-lucas` → `needs-owner` label rename, and bundled the
three landed workstreams below with the newly-published v0.10.0 substrate port and a code-review pass.

- **Studio de-restricted into three doors.** A launch chooser now fronts the studio: **Door A** —
  the guided chief-of-staff workshop (dossier journey), behaviour-identical to before; **Door B** —
  architect any agent from a description (net-new `architect_journey.js`, generalized blueprint
  cards, add-a-skill, a compose-only build ceremony over `/api/export`); **Door C** — a single-skill
  builder. New `static/{chooser,architect_journey}.js` + `{chooser,journey}.css`; `exporter.py` gains
  a workspace `output_root`. All new logic sits behind the chooser/journey branches — Door A is
  untouched.
- **Composed agents are self-updating, own-repo homes.** Each `dist/<name>-cos/` is `git init`-ed as
  its own repo with a recorded `SUBSTRATE_VERSION` and a `.cos-update.json` (upstream repo/branch/
  packages path, auto-detected from the git remote). A new always-shipped **`cos-update`** skill
  pulls any `docs/upgrades/*` package newer than the home's version, applies it to the home's own
  personalized skills (preserving name/vault/ids), bumps the version, and commits — a true "update
  me" that survives personalization. `.git` and the vault are preserved across rebuilds.
- **Substrate ported to upstream v0.10.0** (`docs/upgrades/2026-07-04-cos-v0.10.0-upgrade.md`,
  items 14–18): drain scheduled-task `ExecutionTimeLimit` 10 → 20 min (busy-cycle headroom); new
  idempotent, additive **`grant-batch-logon-right.ps1`** (grants `SeBatchLogonRight` so the S4U
  drain/brief tasks can start); a documented **calendar-write live-authorization limitation** (the
  `confirmed-by-agent` gate is sufficient within the plugin, but Claude Code's own product-safety
  check may still require a live, same-turn OK); an optional, **off-by-default `### Interests`**
  daily-brief module (source-linked news beats gated on a vault `interests.md`, with a stdlib
  `collect_updates.py` collector and a web-search fallback in lean homes); and an **intake media-link
  fast path** (YouTube / video URLs are recognized and routed to ingest, or a forward-hook when no
  knowledge base is wired up). `SUBSTRATE_VERSION` → **0.10.0**.
- **Code-review hardening.** Drain: the Step-4 **settle-gate now measures thread quiet against
  `lastActed`** (Step 3's mirroring had already advanced `lastSeen` past the burst, defeating the
  gate); the channel **watermark advances per committed issue-group**, not once per run, so a mid-run
  crash on a multi-group run no longer re-files already-created issues; calendar crash-recovery also
  mirrors `stateId → Done`; the Kanban re-arm table row was corrected. Studio: the Door-B journey no
  longer renders later Q&A **inside the build section** (the open section is released after close);
  `?onboard=1` forces onboarding instead of the chooser; a stored architect-session on a bare URL now
  **resumes the journey** instead of dropping into the workshop; and the transient `output_root` no
  longer leaks into the failure handoff spec.

## 0.6.0 — 2026-07-07 — Drain conversational-ticket intelligence (substrate → upstream v0.9.0)

- **The drain now treats an `#inbox` dictation burst as one accreting conversation.** Ported the
  upstream chief-of-staff v0.8.1→v0.9.0 upgrade package (`docs/upgrades/2026-07-02-cos-v0.9.0-upgrade.md`)
  into the placeholder-form substrate:
  - **Adaptive settle window** — a source (channel or thread) is processed only once quiet
    (0 → nothing; 1 → newest ≥ 30s; 2+ → newest ≥ 90s; oldest un-processed ≥ 600s ceiling). One
    shared implementation: `chief-of-staff/scripts/settle-lib.ps1` (`Test-SourceSettled`, Int64
    snowflake math) with a Pester suite (`scripts/tests/settle.Tests.ps1`, 14 tests green on
    PowerShell 5.1 / Pester 3.4) and the prose contract `skills/drain/references/settle-window.md`.
    Consumed by the precheck and the SKILL (settle gates both ingestion and action).
  - **Kanban state mirroring** — every lifecycle label change also sets the matching Linear
    workflow `stateId` in the same mutation (Todo → In Progress → In Review → Done); state ids are
    resolved at runtime by name/type per `skills/drain/references/linear-api.md` (never hardcoded
    UUIDs — substrate-safe).
  - **`#inbox` burst grouping** (contiguous owner-authored runs handed to `intake` as one batch;
    watermark advances once per run), **new-vs-old comment boundary** (`> lastActed` = NEW),
    **auto wiki-entity linkage** (a drain-authored `## Meta` block + `wiki_ref` write-back, loaded
    on later cycles only after vault-validation; bodies sanitised for the `## Meta` literal), and a
    **one-shot ~50-comment length nudge** (`lengthNudged`).
  - **Anti-stale-context hardening** — verify-before-assert (newest verified statement wins; never
    assert an unverified status) and Google auth-contract precedence + the UPPERCASE env-var-suffix
    case rule (`references/google-auth.md`).
  - **Golden trace** `evals/golden/drain-dictation-context.md` (settle hold → grouped issue → CRM
    page → `wiki_ref` write-back → later reply as NEW-since-`lastActed` with the page reloaded).

## 0.5.0 — 2026-07-03 — The dossier journey + raw-skills agent homes

- **The workshop surface is now a dossier** — a single living document the architect writes
  chapter by chapter. Participant answers fossilize as serif quotations; a blended writing
  line replaces the chat box; a journey rail tracks the seven phases; reloads replay the
  whole document from server-side beats (same session, verbs included). The old chat skin
  stays reachable at `?ui=chat` (same-session escape hatch) until the dress rehearsal proves
  parity; `?mode=architect` is byte-identical.
- **Composed agents are now raw-skills agent homes** (lean spec §5): `dist/<name>-cos/` gets
  `.claude/skills/` + `.claude/agents/`, a generated `CLAUDE.md` identity (agent slug, owner
  from onboarding, vault path, skill roster), root `.mcp.json`, and reference paths rewritten
  home-root-relative (invariant-tested). Launch is `cd dist/<name>-cos` then `claude` — no
  marketplace, no `/plugin install`, no restart. The default vault lives IN the home and
  **survives rebuilds** (only `.env` is lost); a rebuild that can't clear the old home fails
  closed with a "close the terminal in your agent's folder" error instead of nesting.
  The substrate's vestigial plugin manifests are removed.
- **Revision is part of the record:** rewrite ⟲ on any fossilized answer re-asserts the full
  agent state from the new answer; regenerate ⟳ rewrites a chapter in place. Both replay
  faithfully after a reload.
- **The finale is a ceremony over a real agent:** sign the manifest → organs bind as real
  compose events stream → assemble → **first breath** (one tool-less, budgeted `claude -p`
  turn from inside the composed home via `POST /api/first-breath` — real streamed tokens,
  static fallback if offline) → launch card with the two-line install command and pending
  integration chips that fill as keys connect. The launch card survives reloads.
- **Connect and intake live in the document:** typed chapter blocks (step / key-field /
  checklist / note / skill-card) render inline; key-field blocks host the real smoke-test
  rows (`wireKeyRow` seam, one wiring for wizard and dossier); the first-launch intake
  (name, materials drop, second-brain path) opens the dossier itself — the C3 overlay is
  retired in dossier mode.
- **Docs:** `studio/FACILITATOR.md` gains a "Running the room" section (recovery moves:
  ⟳ / ↺ / reload replay / `?ui=chat` / first-breath fallback); substrate README/INSTALL
  teach the agent-home launch.
- **Tests:** 209 green including live-claude integration smokes (real workshop turn emits a
  chapter; real first breath over a composed home). Release gate before the room: the
  fresh-machine dress rehearsal (spec §11.2).

## 0.4.0 — 2026-07-03 — Interest radar shelf skill

- **New free-tier shelf skill: `daily-interest-brief` ("Interest radar").** A keyless,
  newsletter-style daily pulse on the topics a participant follows — 3–5 sourced, link-rich
  bullets on news, a sport, a company, a market, or a policy area — using the composed agent's
  native `WebSearch`/`WebFetch` (with an optional, zero-dependency Google-News-RSS helper
  script). Reads/writes the owner's followed topics in the vault self-layer
  (`meta/chief-of-staff/interests.md`); each topic carries an optional `angle` that dials the
  brief's depth. Standalone (no keys, no prerequisite skills) but folds an `### In the world`
  section into the `briefing` sweep when both are composed. Wired through the composer
  (`_ALL_SKILLS`), the shelf catalog, and the workshop interview; no connect-step, key-wizard,
  smoke-test, or dossier-UI change. Out of scope: unattended scheduled delivery (arrives with
  the r1 always-on scheduler).
- **Provenance:** adapted from the MIT-licensed `daily-interest-brief` skill by Nick Pinidiya
  (github.com/Nicegarrry/claude-skills); the collector script retains its MIT notice. The
  OpenAI-runtime `agents/openai.yaml` was not vendored; the skill was rewritten to Claude Code
  idiom and wiki-brain conventions.
- **Tests:** reference-path invariant extended to the new skill; a catalog assertion pins it
  keyless/free-tier.

## 0.3.0 — 2026-07-03 — Onboarding journey + guided cards

- **First-launch onboarding walk (workshop mode).** Fade-in name screen → "Welcome, {name}." →
  the studio reveals with the live agent narrating: a files card takes CV/LinkedIn
  screenshots/writing (drag-drop staged into gitignored `studio/.cache/`, or folders linked in
  place; 20 MB/file / 40 files / 100 MB caps), then a mind-palace card picks the **second
  brain** — one participant-owned folder (repo-interior rejected) that receives the materials,
  a distilled `profile.md`, and later becomes compose's `vault_dir`: one memory, two readers.
  A scoped `claude -p --allowed-tools Read` distiller (`studio/distiller.py`) writes the
  profile; every failure is non-fatal (stub profile — onboarding always completes; every card
  has "skip for now"). Returning launches inject the participant profile into the workshop
  prompt (head-capped at 6,000 chars) so the agent greets you knowing you.
- **Guided card framework + visual ask channel.** New `cards.js`/`cards.css` primitive
  (rise/fold/baton/morph; question/files/path kinds; reduced-motion safe) in a dedicated right
  rail. The workshop agent can now pose choices as an `ask` object in its ` ```studio ` block —
  rendered as a clickable card (options + open text + skip) whose answer returns as a `[card]`
  message; `[card]`/`[studio event]` messages never render as user bubbles. One
  `claude -p --resume` per session is now enforced twice: a frontend send queue and a
  per-session `asyncio.Lock`.
- **Tests:** suite grows 121 → 162 (onboarding module, distiller, server endpoints, ask
  extractor, turn serialization, skip-all regression), including a live distill smoke over
  fictional fixtures. Verified live: PDFs are read by the distiller (probe), doctor green.

## 0.2.0 — 2026-07-02 — QubitStudio journey

- **Conversation-driven journey (workshop mode, now the default).** The studio chat is
  chief-of-staff-aware: a catalog-injected workshop system prompt interviews the participant
  about their working life and emits the build state each turn in a ` ```studio ` fenced block
  (`{picks, name, ready}`). A new server-side extractor (`studio/studio_extractor.py`) parses it,
  the SSE `done` event carries it, and the browser syncs the skill shelf (agent picks tagged
  "✓ recommended"; manual picks always survive syncs) and a new **"Your agent" panel** — the
  conversation's live mirror with baseline rows, price tags, integration chips, and a Build
  button. `?mode=architect` keeps the original plugin-design interview unchanged.
- **SapphireOS reskin.** Studio restyled to qubit-site's design system: light-only token set,
  qubit wordmark header with a live status chip (pulses "agent live" on the first streamed
  token — the verifiable first-run handshake), and 7 self-hosted OFL fonts (Bricolage Grotesque,
  Hanken Grotesk, JetBrains Mono, Crimson Pro; licenses in `studio/static/fonts/LICENSES.md`).
  Architect-path controls (spec load/export) demoted to a collapsed "advanced" disclosure.
- **Tests:** suite grows 98 → 120, including a real-turn workshop smoke (a live `claude` turn
  must emit a parseable ` ```studio ` block). Integration smokes now use fresh session ids
  (`claude --session-id` permanently consumes an id).

## 0.1.0 — 2026-07-02 — Migration

- Surgically migrated from the private `Consulting-Agents` mono-repo (source commit `4bf4142`):
  `studio/` (as shipped in PR #27, v1 compose+tweak), `chief-of-staff/` substrate,
  `agent-architect/` (the studio's core conversation agent — its references build the chat system
  prompt), `requirements.txt`, and the three workshop design specs (`docs/specs/`).
- **Scrub pass applied to the substrate** — Linear UUIDs → `{{LINEAR_TEAM_ID}}` /
  `{{LINEAR_PROJECT_ID}}`, `LUCAS_USER_ID` → `OWNER_USER_ID`, personal emails →
  `you@example.com`, vault paths → `{{VAULT_PATH}}`, bot name → `your-assistant-bot`.
  `composer._subs` gained a live `{{VAULT_PATH}}` entry; original substitutions retained as no-ops.
- Excluded from migration: consulting plugins, agent-architect, wiki-brain, registry, dashboard,
  sandbox, per-user `studio/.cache/`.
- This repo is now the permanent development home for the workshop / agent-builder experience.
