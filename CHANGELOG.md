# Changelog

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
