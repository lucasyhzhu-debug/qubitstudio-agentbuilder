# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

The **QubitStudio Agent Builder** — the participant-facing home of the "Build Your Own Chief of
Staff" workshop, and the **permanent development home** for the workshop / agent-builder
experience. It was surgically migrated from the private `Consulting-Agents` mono-repo on
2026-07-02 (see `CHANGELOG.md` for provenance); the mono-repo keeps the consulting plugins and
Lucas's live personal cos runtime — **development of the studio and the workshop cos substrate
happens HERE from now on**.

Three top-level units:

- **`agent-architect/`** — the meta-agent whose references power the studio's **core conversation**:
  `server.py:/api/session/new` builds the chat system prompt from
  `agent-architect/skills/agent-architect/references/` (quiz bank, architecture menu, spec schema).
  The participant is talking to this agent from the first moment of the journey. Do not remove it
  or "hide" the chat — it is load-bearing (13 tests fail without it).
- **`studio/`** — a local FastAPI + vanilla-JS browser app, launched with `python -m studio`
  (stdlib-only bootstrap: creates `.venv`, installs deps, runs a preflight doctor, opens the
  browser). It walks a participant from skill shelf → compose (deterministic copy, no LLM) →
  personalize (`claude -p` passes) → connect integrations (live smoke tests) → a working agent in
  `dist/<name>-cos/`.
- **`chief-of-staff/`** — the skill substrate the composer copies from: 7 skills (briefing,
  capture, crm, drain, intake, scheduling, tasks) + `agents/context-gatherer.md` + shared
  `references/`.

## The placeholder contract (critical)

The substrate here is **pre-scrubbed to placeholders** — never reintroduce real personal values:

| Placeholder | Filled by | At |
| --- | --- | --- |
| `{{VAULT_PATH}}` | composer `_subs` | compose time (participant's vault location) |
| `{{LINEAR_TEAM_ID}}` / `{{LINEAR_PROJECT_ID}}` | connect step | key wizard |
| `{{OWNER_USER_ID}}` / `OWNER_USER_ID` env | connect step | key wizard |
| `you@example.com`, `your-assistant-bot` | tweaker | personalize |
| `Lucas` / `Lucas Zhu` in prose | `delucas()` | compose time (author name is fine in docs) |

`composer.delucas()` retains the original Lucas-form substitutions as no-op safety; do not remove
them without checking the substrate is fully placeholder-form.

## Commands

| Task | Command |
| --- | --- |
| Launch the studio | `python -m studio` |
| Preflight only (participant pre-work) | `python -m studio --doctor` |
| Run studio tests | `.venv` python: `python -m pytest studio/tests` (pytest.ini in `studio/`) |
| Take a phase from intent to a landed plan | `/spec-plan-pipeline <phase>` (alias `/spec-pipeline`) |
| Review a spec or plan (Staff+Principal) | `/shipshape <doc-path>` |

## Conventions

- **No real keys, tokens, ids, or emails anywhere** — this repo is public. `.env` files are
  gitignored and written only by the studio's connect step into `dist/` (also gitignored).
- `studio/.cache/` is gitignored (per-user build transcripts).
- The composed agent is a **raw-skills agent home** (`.claude/skills/` + `CLAUDE.md` + root
  `.mcp.json`), installed by `cd <dir> && claude` — NOT a plugin/marketplace install. See
  `docs/specs/2026-07-02-workshop-lean-distribution-design.md` §5.
- Design specs live in `docs/specs/`; the roadmap in `docs/ROADMAP.md`. Spec-first for
  non-trivial changes, matching the lifecycle the specs themselves followed. The lifecycle is
  automated by `/spec-plan-pipeline` (spec → shipshape → plan → shipshape → land → handoff);
  reviews land in `docs/reviews/`, plans in `docs/plans/`, execution handoffs in
  `.claude/handoff/` (gitignored).
- Windows + PowerShell is the reference dev environment, but everything participant-facing must be
  cross-platform (the launcher/doctor is the guard).

## Current state & roadmap

`docs/ROADMAP.md` is the authority. Headline: v1 compose+tweak is shipped and working; the r1
scope (per-skill personalize, own-infra guided wizard, always-on scheduler) plus the raw-skills
packaging switch are **specced but not yet built** — specs in `docs/specs/`.
