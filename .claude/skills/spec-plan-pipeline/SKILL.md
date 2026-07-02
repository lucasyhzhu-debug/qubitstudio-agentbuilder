---
name: spec-plan-pipeline
description: Carry one phase of work from intent to a landed, executable plan for the QubitStudio Agent Builder repo — brainstorm a spec, shipshape it, plan it, shipshape the plan, land on main, and leave a post-/clear execution handoff. Use when the user says "spec the next phase, review it, plan it, review the plan, land it, and give me a prompt to run after I /clear", or "run my pipeline". Customized for this repo.
---

# Skill: /spec-plan-pipeline (QubitStudio Agent Builder edition)

> Localized from the Consulting-Agents `spec-plan-pipeline` and customized for this repo.
> Customized sections are marked `[QS]`. The Consulting-Agents machinery (registry/agents.json,
> marketplace.json, dashboard rebuild, `scripts/*.ps1` evals, `/agent-architect` generation)
> **does not exist here** and has been replaced with this repo's real gates: spec-first,
> `shipshape`, pytest + the preflight doctor, and ROADMAP/CHANGELOG as the index.

## Overview

Carries one slice of work from intent to an executable plan landed on `main`, with **two review
gates** (after the spec, after the plan), then hands a fresh session everything it needs to implement
after `/clear`. Defining trait: **planning and implementation are different sessions** — this pipeline
does planning, lands it, and leaves a self-contained handoff so the cleared session resumes with zero
context loss.

**[QS] This pipeline uses `superpowers` + this repo's `shipshape` review skill. It does NOT use GSD**
(`gsd-*`) and does NOT use any generic global `staffreview`/`spec-plan-pipeline`. If you reach for a
`gsd-*` skill, stop — that is the most common failure of this workflow.

**[QS] Know which of the three units the slice touches — it changes the gates that apply:**
- **`studio/`** (FastAPI app, participant journey) — pytest per slice is mandatory
  (`python -m pytest studio/tests`); doctor/smoke coverage if the journey changes; the
  stdlib-only bootstrap and cross-platform rules are hard constraints.
- **`chief-of-staff/`** (the workshop substrate) — the **placeholder contract is the #1 gate**:
  never reintroduce real personal values; keep `delucas()`/vault-template tests green.
- **`agent-architect/`** (core conversation) — load-bearing; changes to its references reshape the
  participant's chat, so smoke the studio conversation after touching them.

## The pipeline (run in order — do not skip a gate)

1. **Brainstorm the spec** — `superpowers:brainstorming`. It decomposes: if the phase is multiple
   subsystems, split it and spec the FIRST slice only. **[QS] Spec-first is this repo's stated rule
   for non-trivial changes** (CLAUDE.md). Terminal artifact:
   `docs/specs/YYYY-MM-DD-<slug>-design.md`.

2. **Isolate** — first **sync local `main` to `origin/main`** (`git fetch origin`, then fast-forward;
   fall back to `git update-ref refs/heads/main refs/remotes/origin/main` if a prior squash makes
   `pull --rebase` choke) so you branch off the real tip. Then create a fresh branch off synced
   `main`: **[QS] `feat/<slug>`**. A git worktree is optional and only worth it when isolating from
   an in-flight branch.

3. **Shipshape the spec** — **[QS]** invoke `shipshape <spec-path>` (this repo's two-persona
   Staff+Principal review). **Address every Critical + Improvement**, edit the spec inline, commit.
   Ground findings in real code: read the files the spec names, run the tool it depends on.
   **[QS] The highest-value catches here are evidence catches** — when a spec leans on inferred
   behavior of an external tool (`claude -p` flags, the `claude` CLI, an API), **capture a real
   artifact** (run the command, read the script) and fold the truth in. Save the review to
   `docs/reviews/shipshape-<slug>-spec-<date>.md`.

4. **Write the plan** — `superpowers:writing-plans`. Real signatures, TDD steps, no placeholders.
   Save to `docs/plans/<slug>.md`. **[QS]** Follow the existing test-per-module pattern
   (`studio/tests/test_<module>_*.py`); every slice names its pytest cases.

5. **Shipshape the plan** — **[QS]** invoke `shipshape <plan-path>`. **Verify the assumptions the plan
   flagged** against actual code (module APIs in `studio/`, reference formats in
   `agent-architect/.../references/`, substrate skill contracts). Address all issues, commit. Save to
   `docs/reviews/shipshape-<slug>-plan-<date>.md`.

6. **[QS] Refresh the index** — `docs/ROADMAP.md` is the authority: move/annotate the item this
   slice covers (specced → planned, or shipped when done later). Add a `CHANGELOG.md` entry if the
   slice lands anything user-visible. Update `CLAUDE.md` only if conventions change. Commit.

7. **Land on `main`** — push the branch, open a PR (plan + roadmap refresh), **[QS] squash-merge**.
   **[QS] Public-repo gate (mandatory): before any push, scan the full diff for real keys, tokens,
   ids, emails, or personal values** — the substrate must stay placeholder-form. A leak here is
   published; treat it as a hard stop.
   **Close out the git state (mandatory):** if a worktree was used, exit and remove it; then re-sync
   local `main` to `origin/main` (fetch + fast-forward, falling back to `git update-ref` after a
   squash). End on a clean, synced `main`.

8. **Write the execution prompt** — write `.claude/handoff/execute_<slug>.md` (untracked local
   artifact — `.claude/handoff/` is gitignored). A **plain prompt file the user pastes/references by
   hand** after `/clear` — no hook, no slash command, no skill wiring. Then print one line telling
   the user the path. The body must be self-contained (the cleared session has zero memory): a
   **sync-to-`origin/main`-first** instruction, the plan path on `main`, an instruction to dispatch a
   subagent to execute it task-by-task, a fresh-branch-off-synced-main instruction, the verify-first
   list from the reviews, **[QS] and this repo's post-implementation QA close-out** (see below).

## [QS] Post-/clear resume — the execution prompt file

`/clear` wipes context. The only resume artifact is a plain markdown prompt:
`.claude/handoff/execute_<slug>.md`. After `/clear` the user invokes it themselves — pasting it or
saying *"execute the plan in .claude/handoff/execute_<slug>.md"*. The slug lets multiple planned
phases coexist; overwrite per run, keep a dated copy for history.

Prompt-file shape (self-contained):

```markdown
# Execute: <slug>
Start from a synced remote main: `git fetch origin`, then make local `main` == `origin/main`
(fast-forward, or `git update-ref refs/heads/main refs/remotes/origin/main` if a prior squash-merge
makes `pull --rebase` choke). Confirm `git status` is clean before branching — do NOT build on a stale base.
Create a fresh branch `feat/<slug>` off that synced `main`, then dispatch a subagent to implement
the plan at `docs/plans/<slug>.md`, task-by-task.
Verify first (confirm against real code before coding): <verify-first list from the plan shipshape>.

When implementation is complete, run this repo's QA close-out before declaring done:
1. `python -m pytest studio/tests`            # full studio suite (in the repo .venv)
2. `python -m studio --doctor`                # preflight, if the launcher/journey changed
3. Placeholder-contract scan — grep the diff for real names/emails/ids if the substrate changed
4. `/code-review` (or `superpowers:requesting-code-review`) — address every Critical + Improvement
Re-run the tests after the fixes; only then is the phase done. Public repo: scan the final diff
for secrets/personal values before any push.
```

## [QS] Red flags — STOP

| Thought | Reality |
|---|---|
| "I'll use gsd-spec-phase / gsd-plan-phase" | NO. This pipeline is superpowers + shipshape only. |
| "I'll use a generic global staffreview" | Use this repo's `shipshape` — it knows the placeholder contract, the three units, and the public-repo rules. |
| "One review is enough" | Two gates: after the spec AND after the plan. Both mandatory. |
| "I'll update registry/marketplace/dashboard" | Those are Consulting-Agents machinery. Here the index is `docs/ROADMAP.md` + `CHANGELOG.md`. |
| "Spec leans on how `claude -p` / a script behaves — probably right" | Capture the real artifact (run it, read it) before planning on the assumption. |
| "Push now, scrub later" | The repo is PUBLIC. Scan the diff for real values BEFORE the push, every time. |
| "It works on my Windows box" | Participant-facing = cross-platform. The doctor is the guard, not your machine. |
| "Merge directly to main / plain merge" | Squash-PR per repo convention. |
| "Plan the whole multi-subsystem phase" | Brainstorming decomposes first; spec one slice. |
| "Shipshape found issues, I'll note them for later" | Address all Critical + Improvement now, before the next gate. |
| "Plan's landed, I'm done" | Three things outlive the merge: the ROADMAP/CHANGELOG refresh rode in the PR (step 6), the git state is closed out (step 7), and `.claude/handoff/execute_<slug>.md` is written (step 8). |
| "Branch off main — it's probably current" | Fetch and align local `main` to `origin/main` FIRST, both when isolating and at the top of every handoff. A stale base silently redoes merged work. |

## [QS] Common mistakes

- **Working on the user's current branch.** Always a fresh branch off synced `main`.
- **Plan assumptions unverified.** The plan shipshape confirms flagged module APIs / flag names /
  reference formats against the real `studio/` and `agent-architect/` files and the `claude` CLI —
  that's where the cheap wins are.
- **Substrate edits without the contract check.** Any change under `chief-of-staff/` re-runs the
  vault-template/delucas tests and a real-values grep before commit.
- **Handoff not self-contained.** The cleared session has zero memory; name the sync-first step, the
  plan path, the subagent-execution instruction, the verify-first list, and the QA close-out
  (pytest + doctor + contract scan + `/code-review`) explicitly.
- **Silently dropping a non-applicable step.** When a slice legitimately skips a gate (e.g. no
  substrate touched → no contract scan), *say so* — a flagged deviation, never a silent one.
