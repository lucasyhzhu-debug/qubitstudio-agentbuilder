# Shipshape review — onboarding-cards implementation plan

**Document:** `docs/plans/onboarding-cards.md`
**Mode:** Plan
**Date:** 2026-07-02
**Reviewers:** Staff Developer persona · Principal Developer persona
**Verdict:** **Revise** — 1 Critical, 5 Improvements, 3 Refinements. Task decomposition,
interfaces, and TDD shape are solid; the Critical is a frontend race at the walk's
climactic hand-off.

## 0. Structure validation

✅ Structure validated — branch + per-task commits; exact file paths; sequential tasks with
Consumes/Produces interface blocks; docs-updates deviation explicitly flagged (rides the
landing PR); success criteria per task + Task 10 QA close-out; Task 0 is a hard gate on the
in-flight journey dependency.

## 1. Assumptions verified against real code

| Plan assumption | Evidence | Result |
|---|---|---|
| `_sess(tmp_path)` helper exists for chat-session tests | `studio/tests/test_chat_session.py:34` | ✅ |
| Async tests run under pytest | `studio/pytest.ini`: `asyncio_mode = auto` | ✅ (markers redundant — R1) |
| `Path.is_relative_to` available | venv Python 3.13.7 | ✅ |
| `server._composer` monkeypatch target | `server.py` imports `composer as _composer` | ✅ |
| Distiller argv works against real CLI | Live probe from spec review (md + png read) | ✅ carried forward |
| Journey interfaces (`MODE`, `shelfSync`, `renderAgentPanel`, tokens) | **Not verifiable yet** — implementation in flight | ✅ correctly gated by Task 0 (STOP-and-reconcile) |

## 2. Critical

### C1 — Task 9 `completeStep`: the morph race wipes the Your-agent panel
`cards.morph('')` (Task 7) sets `root.innerHTML = ''` inside a 220 ms `setTimeout`;
`completeStep` calls it and then immediately paints `renderAgentPanel(null)` into the same
`#blueprint` element. 220 ms later the deferred timeout **erases the freshly painted
panel** — at the exact hand-off moment the whole walk builds toward, in front of the room.
**Required fix:** `morph()` returns a `Promise` resolved after the swap; `completeStep`
awaits it before repainting and waking the composer.

## 3. Improvements

### I1 — Vacuous assert in Task 6's inline-distill test
`assert "engines" in body and '"type": "done"' in body.replace(...) or "done" in body`
parses as `(A and B) or C` — `C` ("done" appears in any SSE close) makes the assert pass
regardless. Replace with separate asserts on `"engines"` and `'"type": "profile"'`.

### I2 — Ask cards mounted in `#blueprint` are wiped by panel repaints
Task 8 mounts ask cards into `#blueprint`, but workshop mode repaints that element on
EVERY `done` (`renderAgentPanel(ev.studio)`) — a pending ask the participant is still
reading, and every folded receipt, vanish on the agent's next turn. Violates spec §3.3
("history stays visible in the rail"). **Fix:** add a dedicated `<div id="askrail"></div>`
above `#blueprint` inside the aside; the ask producer mounts there. Onboarding keeps the
`#blueprint` mount (its repaints are gated by `onboardingActive`).

### I3 — Name form `{ once: true }` bricks the wizard on an empty submit
Task 9 registers the submit handler with `{ once: true }`; submitting an empty name
consumes the listener while returning early — every later submit is dead, the participant
is stuck on screen one. Use a persistent listener with a re-entrancy guard
(disable the input while the POST is in flight).

### I4 — `pathStep` failure recursion duplicates the hot card
On a rejected path (e.g. repo-interior), the answer callback alerts and calls `pathStep()`
again — a second `ob-path` card rises while the first sits mid-state. Fold the failed card
to a `✗ try again` receipt before re-showing (prepend order keeps `fold()` targeting the
new hot card thereafter).

### I5 — Windows-fragile path asserts
`test_register_folder_must_exist` asserts by substring on a `resolve()`d string — drive-
letter case (`C:` vs `c:`) makes this flaky. Compare `Path` objects:
`Path(out["materials"]["folders"][0]) == d.resolve()`.

## 4. Refinements

- R1: `@pytest.mark.asyncio` markers are redundant under `asyncio_mode = auto`; house
  style omits them (harmless either way).
- R2: skip-path default (`~/second-brain`) POST failure is unhandled in the skip branch —
  an alert-and-stay matches the non-skip branch.
- R3: `CSS.escape` is fine for the participant browser floor (all evergreen).

## 5. Staff-persona notes

- Reuse is right: send-queue over `send()` rather than a parallel transport; distiller
  mirrors `tweaker._run_voice_pass`; endpoints are thin wrappers over `onboarding.py`
  logic (composer/tweaker layering); cards.css uses tokens **with fallbacks** so a
  pre-reskin cut still renders — good insurance given the in-flight dependency.
- Interface blocks are complete and mutually consistent (spot-checked
  `extract_studio → done event → renderAskCard`; `onboarding.* → server wrappers`;
  `cards.* → onboard.js`). No placeholders found.
- Prompt work correctly landed in ONE task (Task 3) — removes the two-edits-one-file
  rebase friction flagged in the spec review.

## 6. Phase/wave accuracy

Task ordering respects the spec's cut lines: Tasks 1–3+7–8 = C1 (ask channel ships alone),
4–6 = C2 (backend, API-testable headless), 9 = C3 (the walk), 10 = integration + close-out.
Each task ends committed and testable. Task 0's STOP gate is the right response to writing
a plan against an in-flight dependency.

## 7. Specialist recommendations

- `feature-dev:code-explorer` at execution start (part of Task 0 spirit): diff the landed
  journey `app.js`/`shelf.js` against the shapes this plan assumes; reconcile before Task 8.
- `feature-dev:code-reviewer` after Task 9 (the two biggest JS files land there).

## 8. Lifecycle & git assessment

Branch `feat/onboarding-cards` exists with spec + gate-1 review; per-task commits at
natural boundaries; ROADMAP/CHANGELOG deferred to the landing PR (flagged, per pipeline);
public-repo scan in Task 10 close-out. ✅

## 9. Placeholder-contract check

No task touches `chief-of-staff/` or `agent-architect/`; fixtures are fictional (Ada
Lovelace); all runtime participant data in gitignored or user-external paths. ✅

## 10. Test & doctor/smoke assessment

**Verdict: Adequate** once I1/I5 land. Violation cases present across modules (caps,
traversal, repo-interior, missing-sb degrade, restart-lost-task, concurrency); one real
integration smoke (distiller) plus the PDF verify-first probe with both outcomes specified;
manual choreography checklist covers reduced-motion, skip-all, and returning-user paths.
Doctor untouched (no launcher change) — correct.
