# Shipshape review — plan: qubitstudio-journey

**Target:** `docs/plans/qubitstudio-journey.md` (plan mode)
**Date:** 2026-07-02 · **Reviewers:** Staff + Principal personas · **Verdict:** APPROVE with minor fixes (applied inline)

✅ Structure validated — header with goal/architecture/constraints, exact file paths, complete
code in every step, per-task commits, interfaces blocks, cut lines preserved (T1–5 = B1 floor,
T6–7 = A, T8 = B2), success criteria per task.

## Assumptions verified against real code (the gate's core job)

| Plan assumption | Verified against | Result |
|---|---|---|
| ` ```studio ` cannot match `spec_extractor._FENCE` (and vice versa) | `spec_extractor.py:11` regex requires `\s*\n` after `spec|json`; "studio" fails at char 2 | ✓ disjoint both ways |
| Empty-body `await req.json()` raises (needs try/except) | FastAPI/Starlette `Request.json()` → `json.JSONDecodeError` on empty body; plan catches broad `Exception` | ✓ |
| `_sess(tmp_path)` helper exists for Task 3 tests | `test_chat_session.py:34-36` | ✓ |
| `escAttr` available to `renderAgentPanel` | `app.js:122` | ✓ |
| `.sc-add` clicks survive `renderBody()` re-renders | delegation is on `drawer` (`shelf.js:134-137`), not per-card | ✓ |
| `catalog.json` is a sibling of `system_prompt.py` | both in `studio/` | ✓ |
| `@pytest.mark.integration` registered | already used by `test_smoke_integration.py:7` | ✓ |
| Existing `test_new_session_returns_id` (bare POST) keeps passing after mode change | plan's tolerant parse defaults to workshop; response still carries `session_id` | ✓ |
| `buildAgent` still works with the new `{it, origin}` map shape | plan updates `renderFoot`/`toggle`/`shelfCard` consistently; `[...selected.keys()]` unchanged | ✓ |
| Done-branch ordering in workshop mode | `renderAgentPanel` runs after `renderBlueprint`, so the panel wins the `#blueprint` innerHTML even if a stray spec parses | ✓ |

## Findings

### Critical
None.

### Improvement

**P1 — ROADMAP/CHANGELOG not in any task.** Correct for this pipeline (they ride the landing
PR as pipeline step 6), but the plan must say so explicitly — a flagged deviation, never a
silent one. **Fix applied:** note added to the plan header.

**P2 — Task 9 expected test count wrong.** 98 baseline + 9 (T1) + 4 (T2) + 4 (T3) + 4 (T4) +
1 (T9) = **120**, not "~115+". **Fix applied.**

### Refinement

**P3 — Partial-slice degradation documented.** If the evening cuts after Task 5, `.sc-rec`
renders unstyled and the `.live` chip has no pulse (styles land in Task 7) — functional, just
plain. Noted in the plan header so an executor doesn't chase it as a bug. **Fix applied.**

**P4 — `<title>` still "agent-studio"** — optional copy touch in Task 7; left as-is (YAGNI).

## Assessment

- Waves/ordering: sequential T1→T5 (each consumes the previous interface), T6–7 parallelizable
  with T1–5 except the shared `index.html` (ownership already assigned in the spec's risk
  table). Sensible.
- Tests: **Adequate** — TDD per backend task with negative cases (malformed JSON, junk mode,
  garbage turns); real-turn workshop smoke; manual checklists where no JS runner exists.
- Git/lifecycle: feature branch exists, per-task commits, QA close-out task includes doctor +
  placeholder scan + /code-review. Public-repo gate: only OFL fonts enter; scan step present.

**Overall: Approve.** Next: refresh ROADMAP/CHANGELOG, land the PR, write the handoff.
