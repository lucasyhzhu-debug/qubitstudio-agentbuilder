# Shipshape review — studio-dossier-journey plan (gate 2)

**Date:** 2026-07-03 · **Target:** `docs/plans/studio-dossier-journey.md` (3,614 lines, 21 tasks)
**Mode:** Plan · **Personas:** Staff + Principal (parallel, grounded in post-PR#7 worktree code)
**Verdicts:** Staff **Revise (minor)** · Principal **Revise** → consolidated **Revise**
**Testing verdict:** Adequate (with the two contradicting checklist items corrected).
**Anchor/deviation audit:** all 10 of the plan's flagged deviations verified TRUE against code
except #7 (half-wrong: `studio/FACILITATOR.md` exists) and #2 (true but smuggled a data-loss
consequence — adjudicated below). ~20 spot-checked line anchors all exact.
**Resolution:** every Critical + Improvement (and the cheap Refinements) applied to the plan
in the same branch; decisions taken by the controller are marked ▸DECISION.

## Critical

| id | Finding | Resolution in plan |
|---|---|---|
| C1 | **`?ui=chat` restarts the journey** — the chat-skin boot path mints a new session, contradicting the spec's "same session" escape-hatch promise (a silent reinterpretation of gate-1 C4). | Task 10: in workshop+chat mode, read `sessionStorage['dossier-session']`, resume that session (skip re-seeding) and replay beats as plain bubbles via the existing `GET /beats`; FACILITATOR row stays truthful. |
| C2 | **D1a/D1b ship with invisible builds** — the takeover CSS hides `.rightrail`, which contains `#buildpanel`; the drawer's Build streams into a `display:none` subtree until D1c relocates it. Two shippable cut lines contradicted their own CSS. | ▸DECISION (a): when a build starts under the dossier skin pre-D1c, float `#buildpanel` as a fixed dock reusing the exact onboarding-dock pattern Task 8 already builds; D1c's relocation then replaces the dock. Cut-line statements + Task 11's manual check updated. |
| C3 | **Beats replay corrupts the document after D1b's revision verbs** — replay re-fossilizes the OLD answer (the `[studio event]` rewrite is suppressed), loses the `rewritten ↺` chip, duplicates sections on retitled rewrite turns, and doubles regenerated chapters. Reload is the documented recovery move; its composition with the verbs was broken as written. | Task 9/13: `replayBeat` is now verb-aware — it parses `[studio event] rewrite/regenerate …` user text, re-fossilizes the NEW answer with the chip, and sets a one-beat replace/append target for the following beat, mirroring live `settle()`. D1b checklist gains "reload after a rewrite and after a regenerate". |

## Improvement

| id | Finding | Resolution |
|---|---|---|
| S1/I7 | First-turn error invisible: `onError` appends the brass line to `#dz-live` then wipes `#dz-live` when no chapter is open (claude-missing-at-boot — the likeliest room failure). | `onError` opens the Welcome section first when `open` is null, then appends; checklist item added for a boot-time failure. |
| S2/I2 | Rebuild unexecutable from the ceremony: `#dz-build` stays `✓ signed`+disabled after success; D1c checklist #6 and the FACILITATOR row asserted a path the code can't deliver. | Ceremony end flips the button to an enabled "Rebuild" (resets `signed`), with the .env/vault warning beside it. |
| S3/I9 | Reload mid-intake strands onboarding: `tryReplay` returns before the onboarding gate; the walk never re-mounts, `/api/onboarding/complete` unreachable. | After a successful replay in workshop mode, re-fetch `/api/onboarding`; if incomplete, resume `intake(state)` at the step the state file indicates. D3 checklist #6 reworded to test continuation. |
| S4 | `cd <dir> && claude` is a parse error in Windows PowerShell 5.1 — the reference platform's default shell, at the journey's climactic moment. | ▸DECISION: `install` field becomes `cd <final> ; claude` (parses in PS 5.1, pwsh, bash, zsh); UI renders it as two lines via the existing `' ; '` split. Flagged as a deliberate deviation from lean §5's literal `&&` (reason: PS 5.1). Tests updated. |
| S5/R3 | Plan's flagged deviation 7 half-wrong: `studio/FACILITATOR.md` already exists (shared-infra runbook); creating a second root FACILITATOR.md invites the wrong-file failure in the room. | ▸DECISION: no new root file — Task 11 adds a "Running the room" section to the EXISTING `studio/FACILITATOR.md` (recovery moves, ⟳, first-breath fallback, reload, `?ui=chat`). |
| S6 | `lastDone` doesn't survive reload — replayed connect chapters degrade to "build first"; FACILITATOR "nothing lost" oversold. | The beats-replay payload piggybacks the server's `LAST_COMPOSE` (+install/plugin_path); `tryReplay` restores `lastDone`. |
| I1 | Pending-target can be consumed by the wrong beat: verbs clickable while a turn is in flight; the in-flight `done` eats the override. | Verbs gated on a turn-in-flight `busy` flag (set in `onToken`/send, cleared in `onDone`/`onError`). |
| I3 | D0's generated CLAUDE.md "Owner" was the AGENT's name ("Owner: atlas"), contradicting the first-breath greeting that uses the onboarding participant name. | `compose` threads `onboarding.load_state().get("name")` (fallback: agent name) as a distinct `owner` argument to `write_claude_md`; slug still derives from the agent name. Test updated to pin the distinction. |
| I4 | **Rebuild destroys the in-home vault** (agent memory) via the package-stage rmtree — a data-loss consequence the spec never accepted (the one flagged deviation that was a scope change needing the human). | ▸DECISION: preserve `final/vault` across the rmtree (move aside → restore after the staging move); rebuild loses `.env` only (already documented). Test added: vault content written post-build survives a rebuild. Surfaced in the handoff for Lucas's awareness. |
| I5 | Reference-path invariant only enforced for SKILL.md — `.claude/agents/context-gatherer.md` ships broken `chief-of-staff/...` paths (baseline machinery for briefing/drain). | `_rewrite_reference_paths` also runs over copied `agents/*.md`; the invariant test globs them too. |
| I6 | Server death mid-turn wedges the dossier: send() failure is swallowed (`queueSend`'s `.catch(()=>{})`), writing line stays dead, and reload-while-down CLEARS `sessionStorage`, making the session unrecoverable after the server returns. | Dossier path of `send()` wrapped — thrown errors route to `dossier.onError` (re-arms the line); the stored session id is cleared only on a definitive 404, never on network failure. |
| I8 | Error during a rewrite leaves three-way incoherence: `rwSettle` fires later for a rewrite the agent never received; the fossil shows an unsent answer; `.dz-sec.stale`/`.dz-regenerating` strand. | On a verb-turn error: clear `rwSettle` and `pendingTarget`, mark the fossil "unsent — retry" (revert affordance), remove `dz-regenerating`, un-stale sections. |

## Refinement (all applied — one-liners)

S7/R4 second "panel on the right" wording in `_ONBOARDING_CONTRACT` step 1 fixed in the same
Task 20 edit · S8 D1c checklist SKIP item reworded (cuts staged pauses; live greeting still
streams) + `words` render instantly once skipping · S9 replay seed filter matches the two
known seeds exactly (not `/^Begin /`) · S10 finale MutationObserver disconnected in `unsign`
and re-created per build · R1 `.dz-stale-mark` added to regenerate's replacement selector ·
R2 FACILITATOR reload row reworded (replay restores the document; answered choice-cards
render as fossils only; error turns aren't replayed) · R5 first-breath empty MCP config
written under `studio/.cache/` (not shared temp) and `proc.wait()` wrapped in the remaining
budget · R6 `renderAsk` gated on `!window.onboardingActive` (one hot surface during the C3
dock; pending ask renders on handback) · R7 `activate()` awaits the catalog before processing
the first `onDone` (re-diff on arrival) · R8 note added: the welcome chapter's heading lands
at first `done`, not first token — §4.4's table read accordingly for the dress rehearsal.

## Deviation adjudication (plan's 10 flags)

1, 4, 5, 6, 8, 9, 10 — legitimate truth-corrections. 3 — legitimate but incomplete (fixed by
I5). 2 — correct but carried the I4 data-loss consequence (now resolved by preservation).
7 — half-wrong (fixed by S5/R3). Not flagged but should have been: C1's same-session
reinterpretation (now fixed).

## Verified sound (no action)

D0 commit order + reverse revert; the reference-rewrite regex order; first-breath server-side
path provenance + tool-less/strict-MCP flags; organ↔event mapping matches Task 3's compose
stream; `wireKeyRow` extraction behavior-preserving (google `persist_only` included); beat
shape `{user, prose, studio}` consistent end to end; CSS class vocabulary consistent T8↔T9/
T13/T15/T16/T18; placeholder scans at both substrate touchpoints; XSS posture; no new deps;
architect byte-identity pinned in T6/T12/T19; dress-rehearsal human gate (T21); `?ui=chat`
removal correctly deferred.
