---
name: shipshape
description: Review a design spec or implementation plan from the perspective of two senior engineers (Staff and Principal) to catch issues before a single line of code gets written. Customized for the QubitStudio Agent Builder repo.
---

# Skill: /shipshape (QubitStudio Agent Builder edition)

> Vendored from https://github.com/lucasyhzhu-debug/shipshape and customized for this repo
> (studio FastAPI app + workshop cos substrate + agent-architect, public repo). Upstream
> structure preserved; customized sections are marked `[QS]`.

## Purpose

Simulate a rigorous review where two senior engineers examine a **design spec** (`docs/specs/`) or an **implementation plan** (`docs/plans/`). Assume the document was written by a junior developer (or an AI agent) and provide constructive, thorough feedback to catch issues BEFORE implementation begins.

### Review Personas

1. **10x Staff Developer** — implementation elegance, code patterns, duplication avoidance, practical execution
2. **10x Principal Developer** — architecture, participant-journey flows, logic correctness, system-wide implications

## When to Use

- Before starting implementation of any plan
- After writing a new spec or plan (self-review)
- At the spec-first gate (CLAUDE.md: spec-first for non-trivial changes)
- User explicitly requests a plan/spec review

## Two review modes `[QS]`

Detect the document type first; it changes Step 0 and how Sections 6–8 of the report are interpreted:

- **Spec mode** — target is a design spec (brainstorming output, `docs/specs/`). Review the *design*: decisions, architecture, boundaries, parity/inventory completeness, build order, risks. Git/commit mechanics are assessed against the repo lifecycle, not per-commit.
- **Plan mode** — target is an implementation plan (writing-plans output). Full upstream behavior: waves, commits, test checkpoints.

## Workflow

### Step 0: Mandatory Validation (FIRST)

**Spec mode checklist `[QS]`:**

```
SPEC VALIDATION CHECKLIST
═════════════════════════
□ Status + owner + date present? Committed to git (spec-first gate)?
□ Decisions recorded (what was chosen AND what was rejected)?
□ Non-goals / scope boundary explicit?
□ Architecture: components with one clear purpose + defined interfaces?
□ Inventory/parity checklist if replacing an existing system?
□ Build order in committable slices?
□ Test approach: pytest cases per slice (studio/tests), violation cases,
  doctor/smoke coverage where the participant journey changes?
□ Placeholder contract respected — no design that requires real personal
  values in the substrate?
□ Risks / open items named?
═════════════════════════
```

**Plan mode checklist (upstream):** Git Workflow section (branch name, checkpoints) · Implementation Waves (owners, file paths, PARALLEL/SEQUENTIAL) · Documentation Updates (CHANGELOG, ROADMAP) · Success Criteria (tests, doctor, smoke).

**If the document is INCOMPLETE:** silently draft the missing sections in your review output under "Structure Additions", and continue — do NOT stop or ask permission.
**If COMPLETE:** note "✅ Structure validated" and proceed.

### Step 1: Document Discovery & Initial Read

- Path argument provided → read it directly.
- No argument → list `docs/specs/` and `docs/plans/` (if present), present a numbered list, wait for selection.
- Read the selected document completely before proceeding.

### Step 2: Gather Project Context `[QS]`

Ground the review in *this repo's* rules. Read (skip any that don't exist):

1. **`CLAUDE.md`** — repo model, the three top-level units, the placeholder contract, conventions (public repo, cross-platform, spec-first)
2. **`docs/ROADMAP.md`** — the authority on current state; what is shipped vs specced-not-built
3. **`docs/specs/`** — standing design decisions; flag any contradiction with a committed spec as Critical (especially the lean-distribution raw-skills packaging decision)
4. **`CHANGELOG.md`** — migration provenance and what has already landed
5. **For studio work:** `studio/README.md`, `studio/SETUP.md`, and the module the document touches (`composer.py`, `tweaker.py`, `exporter.py`, `keys.py`, `smokes.py`, `server.py`)

### Step 3: Staff Developer Review

#### 3.1 Duplication Check
Search the repo for existing implementations the document should reuse instead of rebuilding:
- `studio/` — composer (deterministic copy + `_subs`/`delucas`), tweaker (`claude -p` passes), exporter, keys wizard, smokes, doctor, stream parser
- `agent-architect/skills/agent-architect/references/` — quiz bank, architecture menu, spec schema (powers the core conversation)
- `chief-of-staff/` — the skill substrate; prompts and contracts to port, not rewrite
- `studio/templates/vault/` — the vault scaffold

#### 3.2 Implementation Elegance
- Simpler solution available? Unnecessary abstractions? Complexity matched to the problem?
- Deep-module test: few verbs on the surface, complexity hidden inside; can a consumer use each unit without reading its internals?

#### 3.3 Pattern Consistency `[QS]`
- **Bootstrap constraint:** `python -m studio` must stay stdlib-only until the venv exists — no new top-level imports of third-party packages in the bootstrap path
- **Studio stack:** FastAPI + vanilla JS (no framework creep); server builds prompts from agent-architect references
- **Placeholder contract:** substrate stays placeholder-form (`{{VAULT_PATH}}`, `{{LINEAR_TEAM_ID}}`, `you@example.com`, …); values are filled at compose/connect/personalize time, never committed
- **Cross-platform:** everything participant-facing runs on Windows AND macOS/Linux; the launcher/doctor is the guard — no PowerShell-only or Unix-only participant steps
- **Packaging:** composed agents are raw-skills agent homes (`.claude/skills/` + `CLAUDE.md` + root `.mcp.json`), NOT plugin/marketplace installs

#### 3.4 Code Reuse Opportunities
Name specific files/components to extend rather than recreate.

#### 3.5 Practical Execution Assessment
Step/slice ordering sensible? Dependencies clear? Each slice independently committable and verifiable? Scope realistic?

#### 3.6 Testing Plan Review `[QS]`

Tests here = **pytest under `studio/tests/` + the preflight doctor + live smokes**. Inadequate test planning is Critical, not a Refinement.

- Does each build slice have pytest coverage planned (there is an established test-per-module pattern — `test_composer_*.py`, `test_tweaker.py`, `test_server_*.py`)?
- Are violation/negative cases planned, not just happy paths (bad input, missing keys, partial compose, dead `claude -p`)?
- If the participant journey changes: is there a doctor/smoke check so a participant machine fails fast, not mid-workshop?
- Does anything need a fixture under `studio/tests/fixtures/`?
- Placeholder-contract regression: does the plan keep/extend the vault-template and delucas tests if it touches the substrate?

**Verdict: Adequate / Insufficient / Missing** — if Insufficient or Missing, raise as Critical with specific cases to add.

#### 3.7 Git Workflow Compliance `[QS]`
- Feature branch (`feat/<slug>`), PR into `main`, review-gated; atomic commits at natural boundaries
- CHANGELOG + ROADMAP updates planned where applicable
- **Public repo:** no real keys, tokens, ids, or emails in any planned commit — designs that would put one in git are Critical

### Step 4: Principal Developer Review

#### 4.1 Participant-Journey Flow Validation
For studio changes: does the shelf → compose → personalize → connect → dist flow stay coherent? Does any step now depend on state a previous step doesn't guarantee? Does the core conversation (agent-architect chat) remain load-bearing and intact?

#### 4.2 Logic Correctness
Calculations sound? State transitions valid (session, compose, connect steps)? Race conditions (concurrent studio sessions, parallel `claude -p` passes)? Aligned with documented behavior in the specs?

#### 4.3 Architecture Fit `[QS]`
- Respects the **three-unit boundary** — studio orchestrates, chief-of-staff is substrate, agent-architect powers conversation; no unit reaches around another's surface
- Respects the **placeholder contract** mechanically, not honor-system (subs at compose/connect time)
- Respects the **raw-skills packaging decision** (`docs/specs/2026-07-02-workshop-lean-distribution-design.md` §5)
- Replacement work: does the parity inventory cover everything the replaced system provided? What silently disappears?
- Scale check: does it hold for a room of 20 participants on mixed OSes with flaky wifi?

#### 4.4 Edge Cases
Process crash mid-compose · `claude -p` timeout/garbage output · missing/invalid keys at connect · partial `dist/` writes · re-running a step (idempotency) · participant machine without prerequisites.

#### 4.5 Performance Implications
Slow `claude -p` passes in the workshop hot path? Redundant file copies? Anything that makes the doctor or launcher noticeably slower?

#### 4.6 Security Considerations
`.env` written only into gitignored `dist/`? No secrets in logs/transcripts (`studio/.cache/` is per-user)? Nothing outward-facing or destructive ungated? Public-repo hygiene on every artifact the plan commits?

#### 4.7 Documentation Checkpoints
CLAUDE.md (if conventions change) · `docs/ROADMAP.md` · `CHANGELOG.md` · `studio/SETUP.md`/`FACILITATOR.md` if the participant or facilitator experience changes · new spec needed for any standing design decision the document makes?

#### 4.8 Rollback & Operability `[QS]`
- Can each slice be reverted cleanly (additive, superseded-not-deleted)?
- Local-process operability: what must be running (studio server, `claude` CLI)? What happens when one dies mid-workshop? Is recovery documented?
- Is the old flow kept working until parity is proven (no premature retirement)?

### Step 5: Generate Consolidated Report

Use the upstream report skeleton with severity tables (Critical / Improvement / Refinement), plus:
- **Section 6** = Build-order/slice accuracy (spec mode) or Phase/Wave accuracy (plan mode)
- **Section 7** Specialist recommendations — use agents that exist locally: `feature-dev:code-architect`, `feature-dev:code-explorer`, `feature-dev:code-reviewer`, `Explore`, `claude-code-guide` (SDK/CLI questions), `general-purpose`
- **Section 8** = Lifecycle & git assessment (spec-first gate, ROADMAP, CHANGELOG, branch) rather than CI/CD pipelines (none here — everything is local)
- **Section 10** = Test & doctor/smoke assessment (per 3.6)

### Step 6: Save Report

Write to `docs/reviews/shipshape-{document-name}-{YYYY-MM-DD}.md` (create `docs/reviews/` if needed). Inform the user of the location.

### Step 7: Present Summary

1. Overall assessment (Approve / Revise / Major Rework)
2. Counts of Critical / Improvement / Refinement
3. Top 3 findings
4. Next-step recommendation

## Review Severity Definitions

| Severity | Definition | Action Required |
|----------|------------|-----------------|
| **Critical** | Would cause implementation failure, a placeholder-contract breach, a secret in the public repo, a broken participant journey, or a contradiction of a committed spec | Must fix before implementation |
| **Improvement** | Significantly improves quality, performance, or maintainability | Strongly recommended |
| **Refinement** | Minor enhancement, style, nice-to-have | Optional |

## Review Mindset

**Staff Developer thinks:** "How would I actually build this on a participant's machine (Windows AND Mac, fresh venv, flaky wifi)?" · "What in studio/ or agent-architect references already does this?" · "Where are the natural commit boundaries?" · "What's NOT being tested?"

**Principal Developer thinks:** "Does this contradict a committed spec?" · "What breaks live in a room of 20 participants?" · "Can we roll back each slice?" · "Is the deep module actually deep, or is complexity leaking out of its surface?" · "Does anything real leak into the public substrate?"

## Common Issues to Watch For `[QS additions]`

Upstream lists (implementation, architecture, testing, documentation, git) still apply. Repo-specific traps:

- Reintroducing real personal values into the placeholder-form substrate
- Committing anything with a real key, token, id, or email (public repo)
- Breaking the stdlib-only bootstrap path of `python -m studio`
- Windows-only (or Unix-only) participant steps — cross-platform is a hard rule
- Removing or bypassing the agent-architect core conversation (load-bearing; 13 tests fail)
- Drifting back toward plugin/marketplace packaging after the raw-skills decision
- Forgetting ROADMAP/CHANGELOG updates on ship
- Retiring a working flow before parity is demonstrated
