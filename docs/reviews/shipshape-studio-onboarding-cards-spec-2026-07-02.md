# Shipshape review — studio onboarding journey + guided card framework (spec)

**Document:** `docs/specs/2026-07-02-studio-onboarding-cards-design.md`
**Mode:** Spec
**Date:** 2026-07-02
**Reviewers:** Staff Developer persona · Principal Developer persona
**Verdict:** **Revise** — 1 Critical, 8 Improvements, 4 Refinements. Design is sound and
well-evidenced; the Critical is a concurrency gap in the live-narration mechanic that would
break sessions mid-workshop.

## 0. Structure validation

✅ Structure validated — status/owner/date/committed; decisions with rejections; non-goals;
component interfaces; build order in cut-line slices; per-slice tests; placeholder contract;
risks.

## 1. Evidence captured during review (real artifacts, not inference)

| Assumption in spec | Evidence | Result |
|---|---|---|
| Scoped `claude -p --allowed-tools Read --add-dir <dir>` reads mixed materials | Live probe: fixture dir with `cv.md` + 1×1 `linkedin.png`; ran the exact argv shape §5.6 specifies | ✅ Both files read; the model **actually rendered the image** (described the 1×1 pink placeholder correctly) and named both files. Distiller mechanic confirmed |
| Vault template has no collision with seeded files | `find studio/templates/vault -type f` → `meetings/.gitkeep`, `meta/chief-of-staff/lessons.md`, `meta/chief-of-staff/personality.md`, `meta/memories.md`, `people/.gitkeep` | ✅ No `profile.md` / `materials.md` / `inbox/` collision |
| `studio/.cache/` is gitignored (state + staging never committable) | `.gitignore:8` `studio/.cache/` | ✅ |
| PDF CVs readable by the Read tool | Not probed (no real PDF fixture at review time) | ⚠ Deferred → **verify-first item for the plan** (Improvement I8) |
| Tweaker precedent for scoped non-fatal `claude -p` pass | `studio/tweaker.py:67-108` (variadic `--allowed-tools`, `--add-dir`, timeout, degrade-to-log) | ✅ Pattern exists and is shipped/tested |

## 2. Critical

### C1 — Concurrent `claude -p --resume` on one session can interleave/corrupt turns
§5.4's walk has the **UI programmatically sending `[studio event]` messages** while the
participant can also act on cards. `ChatSession.send()` spawns one subprocess per turn with
`--resume <session_id>` and has **no serialization**; `server.py:/api/chat` will happily run
two overlapping sends for the same session (e.g. the participant clicks "that's everything"
while the agent is still streaming its acknowledgment of the last file drop). Two concurrent
`--resume` processes on one session id race on session state — mid-workshop this yields
interleaved or lost turns, exactly during the highest-drama minutes. The card baton governs
*human* focus, not *programmatic* sends.
**Required fix:** the spec must mandate send serialization at both ends — (a) frontend: one
outbound queue, an event message is only dispatched after the in-flight turn's `done`;
(b) backend: `ChatSession` gains a per-session `asyncio.Lock` around `send()` so a second
caller awaits rather than forks. Cheap, testable (`test_chat_session`: two concurrent sends
→ sequential subprocess spawns).

## 3. Improvements

### I1 — `complete` endpoint ordering & restart resilience
`POST /api/onboarding/complete` must 400 cleanly when no second brain is set (order
violation), and must **start distillation inline if the background task is absent** (studio
restarted between `materials/done` and `complete`) instead of hanging on a task that no
longer exists. Add both as violation tests.

### I2 — Upload transport: per-file requests + total cap
20 MB × 40 files in one JSON body = an 800 MB+ request held in memory. Frontend should POST
**one file per request** (progress per chip falls out for free) and the server should
enforce the per-file 20 MB cap plus a running total (~100 MB) per onboarding run.

### I3 — Distiller with folders-only materials
If the participant only links folders and drops nothing, `studio/.cache/onboarding-inbox/`
may not exist — §5.6 sets `cwd` to the staging dir → subprocess spawn fails. Always create
the staging dir; `cwd` falls back to the system temp dir when it is empty/absent.

### I4 — Second brain missing at a later launch
§5.5 injects `profile.md` on every workshop session. If the participant moved/deleted the
second brain, `session/new` must degrade (skip the participant section, mark state
incomplete-ish, and let the UI offer the wizard again via the `?onboard=1` path), never 500.
Add a test: state complete + missing dir → prompt has no participant section.

### I5 — Distiller guidance for large linked folders
A linked notes vault can be thousands of files; unbounded Read fan-out blows the 180 s cap.
The fixed prompt must include sampling guidance: read everything staged, but for large
folders read a representative sample (cap ~30 files, prefer recent/top-level), and say in
the profile what was sampled vs read fully.

### I6 — Facilitator escape hatch (room operability)
Every onboarding card needs a visible "skip for now"; a skip-all path completes onboarding
with the stub profile (name only) so a stuck participant (or a misbehaving model) can never
stall the room. The agent is told via `[studio event]` what was skipped. This is the §8
"narration drifts" mitigation made concrete for the participant, not just the developer.

### I7 — Ownership of the `#blueprint` aside during onboarding
The journey slice's `start()` paints `renderAgentPanel(null)` into `#blueprint` in workshop
mode, and every `done` event repaints it. During the walk, `onboard.js` owns that aside;
the spec must state that app.js gates both calls on onboarding status until the morph
hands the panel back — otherwise the first `done` event wipes the hot card.

### I8 — PDF read: verify-first in the plan
The probe covered md + png. Before the plan's distiller task is written, run the same probe
with a real multi-page PDF CV; if PDF reading disappoints, the files card copy nudges toward
"export LinkedIn as screenshots / CV as text or PDF" and the distiller prompt says to note
unreadable files rather than fail.

## 4. Refinements

- R1: A participant literally typing `[card] …` into the composer is display-suppressed;
  harmless (message still reaches the model). Document, don't engineer around.
- R2: `?onboard=1` re-run with an existing second brain: overwrite semantics for
  `materials.md` and additive semantics for `inbox/onboarding/` should be stated in the plan.
- R3: Fold receipts should length-cap (~60 chars, ellipsis) so long custom answers don't
  bloat the rail.
- R4: The fade-in interpolates the participant's name into HTML — use the existing
  `escAttr`/escape idiom from app.js.

## 5. Staff-persona notes (reuse & elegance)

- Correctly reuses: `spec_extractor`/`studio_extractor` fenced-block pattern (ask rides the
  existing block, no new channel); `tweaker._run_voice_pass` subprocess idiom for the
  distiller; `scaffold_vault(dirs_exist_ok=True)` for the sb-is-vault merge; `keys.persist`/
  `smokes.smoke` reserved for the future `keys` card kind; SapphireOS tokens (no new hex).
- Deep-module test passes: `window.cards` exposes five verbs; producers own routing;
  onboarding logic lives in `onboarding.py` with thin server wrappers (matches
  composer/tweaker layering).
- b64-over-JSON beats `python-multipart` here (no new bootstrap dep) — right call for
  workshop-scale files, given I2.
- No framework creep: vanilla JS IIFE like `shelf.js`. ✅ bootstrap constraint untouched
  (all new deps: none).

## 6. Build-order / slice accuracy

C1 (cards + ask) → C2 (backend) → C3 (walk) is correctly risk-sorted; C1 alone is
independently shippable value (clickable interview questions), C2 is API-testable headless,
C3 is the integration. Cut lines hold. One sequencing note: C1's prompt ask-contract edit
and C2's participant/onboarding sections both touch `build_workshop_prompt` — additive,
but the plan should sequence the two edits explicitly to avoid rebase friction.

## 7. Specialist recommendations

- `feature-dev:code-explorer` before planning C3: trace the journey slice's final `app.js`
  `start()`/`send()`/panel flow **as landed** (it is in flight now) — the spec was written
  against the plan, not the merged code.
- `claude-code-guide` during planning: confirm current `claude -p` flag behavior for
  `--add-dir` + `--allowed-tools Read` on PDFs (I8) and whether `--resume` has any built-in
  concurrency guard (C1).

## 8. Lifecycle & git assessment

Spec-first ✅ (committed on `feat/onboarding-cards` in an isolated worktree — correct, since
the journey implementation occupies the main checkout). Public-repo hygiene ✅ (fixtures are
fictional; participant data confined to gitignored/state paths; sb repo-interior rejection).
ROADMAP/CHANGELOG updates deferred to the pipeline's landing step per convention ✅.
Dependency on the in-flight journey slice is explicitly declared with a do-not-implement
gate ✅.

## 9. Placeholder-contract check

`chief-of-staff/` and `agent-architect/` untouched; no personal values enter the repo; the
second brain lives outside the checkout by default and inside-checkout paths are rejected.
✅ No breach possible by design (mechanical, not honor-system).

## 10. Test & doctor/smoke assessment

**Verdict: Adequate** once C1/I1 cases land (concurrency test; complete-without-sb;
restart-lost-task). Per-module pattern followed; negative cases named; one real integration
smoke for the distiller mirrors the existing `test_smoke_integration` idiom; manual
choreography checklist belongs in the plan. Doctor: no launcher change, so no doctor delta —
correct to leave untouched.
