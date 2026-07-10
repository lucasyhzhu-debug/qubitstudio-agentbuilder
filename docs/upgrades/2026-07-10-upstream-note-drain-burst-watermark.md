# Upstream feedback — F8 `#inbox` burst grouping: once-per-run watermark can duplicate issues

**Direction:** feedback flowing **back upstream** (QubitStudio Agent Builder → private
`Consulting-Agents` mono-repo). This file is a note to relay, not an upgrade package — its filename
deliberately does **not** match the `YYYY-MM-DD-cos-vX.Y.Z-upgrade.md` pattern, so the in-home
`cos-update` skill ignores it.

**Date:** 2026-07-10
**Raised by:** code review of the v0.9.0 port on branch `feat/v0.9.0-studio-doors-selfupdate`
(PR #14), commit `7d34a34`.
**Concerns:** `docs/upgrades/2026-07-02-cos-v0.9.0-upgrade.md` → **F8 (`#inbox` burst grouping)**,
and the matching upstream drain `SKILL.md` Step 2.

---

## The defect

F8 as specified advances the channel watermark **once per run** — "after all issue-groups from the
run are handled" — as a crash barrier, on the reasoning that a mid-run crash "leaves the whole run
'new' so a retry re-groups it identically." The drain `SKILL.md` invariants also claim the design is
crash-safe with **"never double-posting."**

That claim holds only when a run yields **exactly one** issue-group. When `intake` splits a settled
run into **more than one** issue-group and the drain crashes mid-run — after group 1's
`issueCreate` (+ thread + ack + `## Meta`) has committed but before the once-per-run watermark
advances — the next cycle re-fetches the **entire** run (watermark un-advanced), re-groups it
identically, and calls `issueCreate` again for the **already-filed** group(s). `issueCreate` has no
dedup guard, so this **re-creates duplicate issues**. The "never double-posting" prose is therefore
false for any multi-group run.

## The fix applied downstream (recommended for upstream)

Advance the channel watermark **per committed issue-group**, not once per run:

- After an issue-group's writes (`issueCreate` + thread + ack + `## Meta` patch) **all** succeed,
  advance the watermark to the newest message id such that that message **and every earlier new
  message** now belong to a committed group; persist `drain-state.json` immediately.
- Process the run's groups in message-id order so this simply steps the watermark forward
  group-by-group, never past an un-committed message.
- A crash mid-run then leaves only the **un-committed** groups "new", so a retry re-does only those
  (re-grouping their messages identically) — preserving burst grouping while making a multi-group
  run idempotent. The committed group becomes the retry unit.

This keeps F8's crash-barrier intent (an accreting thought is never split across cycles, because the
watermark only ever advances at a settle-complete group boundary) while removing the duplicate-issue
hole.

### Residual + optional belt-and-suspenders

A **within-group** crash — after `issueCreate` but before that group's watermark advance — can still
re-file that one group next cycle. To close it fully, add the package's own **Alt** guard: before
`issueCreate`, search Linear for an existing issue keyed to the group's **anchor message id** (e.g.
carried in the seeded `## Meta` block) and skip creation if found. The downstream port did **not**
add this guard (the per-group watermark was the package's preferred fix); it's noted here so upstream
can decide whether the residual window warrants the extra Linear read per group.

## Suggested upstream edits

1. F8 spec: change "watermark advances **once per run**" → "**once per committed issue-group**", with
   the id-ordered, commit-each-group-before-the-next wording above.
2. Correct the drain `SKILL.md` crash-safety prose: multi-group runs are only duplicate-free with the
   per-group watermark (and fully duplicate-free only with the anchor-id dedup guard).
3. Optionally adopt the anchor-id dedup guard to make "never double-posting" literally true.

## Downstream references

- Fix: this repo, `chief-of-staff/skills/drain/SKILL.md` Step 2 ("Commit each group before the
  next") + the invariants list; `references/drain-state.md`; the golden trace
  `evals/golden/drain-dictation-context.md`.
- Commit `7d34a34` ("fix(review): resolve code-review findings (drain + studio)").
