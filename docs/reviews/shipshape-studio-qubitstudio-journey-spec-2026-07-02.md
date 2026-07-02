# Shipshape review — spec: QubitStudio reskin + conversation-driven journey

**Target:** `docs/specs/2026-07-02-studio-qubitstudio-journey-design.md` (spec mode)
**Date:** 2026-07-02 · **Reviewers:** Staff + Principal personas · **Verdict:** REVISE → fixes applied inline same session

✅ Structure validated — status/owner/date, decisions with rejections, non-goals, build order
with cut lines, test approach, placeholder-contract statement, risks all present.

Evidence artifacts captured during review (not inferred):
- `chat_session.py:49-62` — real `claude -p` argv (`--system-prompt-file`, `--allowed-tools ""`,
  `--session-id`/`--resume`); `send()` always yields `{"type":"done","spec":self.spec}` (line 100).
- `spec_extractor.py:11` — `_FENCE` matches ` ```spec|```json ` only; a ` ```studio ` fence does
  NOT match it (regex requires `\s*\n` right after the label), so no crosstalk into the blueprint.
- `test_smoke_integration.py:9-15` — `test_one_real_turn` calls `write_system_prompt` directly
  (architect builder), NOT the server default; flipping the session default to workshop cannot
  break it. Suite baseline: 98/98 green including this test (run this session, 457s).
- `qubit-site/public/fonts/` — 7 files, **~756 KB total** (not ~1.5 MB as drafted).
- `test_system_prompt.py` — all 5 tests call `build_system_prompt()` directly; adding a separate
  workshop builder leaves them untouched.

## Findings

### Critical

**C1 — Studio-block extraction interface is ambiguous (two readings possible).**
§4.3 gave `extract_studio(assistant_text, catalog_ids)` but did not say (a) whether the
` ```json ` fallback applies (in architect mode ` ```json ` is the *spec* fallback — a shared
fallback would create cross-mode ambiguity), or (b) how `ChatSession` obtains `catalog_ids`
or knows when to run the studio extractor at all.
**Fix applied:** extract_studio matches ONLY ` ```studio ` fences (no json fallback) and
requires `picks` present as a list; `ChatSession` gains `catalog_ids: set[str] | None = None`
(constructor), server passes it for workshop sessions only; `None` → studio extraction skipped
entirely (architect sessions never run it).

### Improvement

**I1 — shelfSync clobbered user-added picks.** §4.4 replaced the whole `selected` map each
sync; a participant who manually added a skill in the drawer would silently lose it on the
agent's next turn. **Fix applied:** picks carry an origin tag (`user` | `agent`); a sync
replaces only agent-sourced picks and never removes user-sourced ones.

**I2 — `/api/session/new` body handling unspecified.** The endpoint currently takes no body;
`await req.json()` on an empty POST raises. **Fix applied:** §4.1 now requires tolerant
parsing (absent/empty/invalid body → workshop default).

**I3 — Font payload figure wrong.** ~1.5 MB → measured **~756 KB**. Fixed in §3.2 and §7.

**I4 — Smoke-test impact overstated risk.** Spec should state (so the plan doesn't "fix" a
non-issue) that `test_one_real_turn` bypasses the server default. **Fix applied** in §6.

**I5 — Status-chip state machine undefined.** `#status` already has `ready` and `loaded`
states; §4.6 added `agent live` without defining the full set. **Fix applied:** explicit
states: `starting…` → `ready` → (first token) `agent live` · `loaded` (spec upload) ·
error states unchanged.

### Refinement

**R1 — Fence-boundary note.** ` ```studio ` cannot false-match `_FENCE` (verified above);
noted in §4.3 so the plan doesn't add defensive complexity. No action beyond the note.

## Assessment

- Build order / slices: sound — B1 floor, A parallel, B2 stretch; cut anywhere leaves a
  working workshop. index.html contention called out with ownership.
- Test & doctor/smoke: **Adequate** after fixes — extractor negatives, prompt-mode tests,
  server-mode tests, real-turn workshop variant; manual checklist for the no-JS-runner frontend.
- Lifecycle & git: spec committed on `feat/qubitstudio-journey` (spec-first gate met);
  ROADMAP/CHANGELOG refresh scheduled as pipeline step 6; public-repo gate — fonts are OFL,
  no personal values introduced.

**Overall: Approve after inline fixes (applied this session, same commit series).**
Top 3: C1 (interface ambiguity), I1 (user-pick clobber), I2 (empty-body 500).
Next step: write the implementation plan.
