# Changelog

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
