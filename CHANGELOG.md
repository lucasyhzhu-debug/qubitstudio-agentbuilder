# Changelog

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
