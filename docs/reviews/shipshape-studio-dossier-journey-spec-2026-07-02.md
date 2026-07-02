# Shipshape review — studio-dossier-journey spec (gate 1)

**Date:** 2026-07-02 · **Target:** `docs/specs/2026-07-02-studio-dossier-journey-design.md`
**Mode:** Spec · **Personas:** Staff + Principal (parallel, grounded in the worktree)
**Verdicts:** Staff **Revise** · Principal **Revise** → consolidated **Revise**
**Testing verdict (Staff §3.6):** Adequate — with required additions (folded below).
**Resolution:** every Critical + Improvement below was applied to the spec in the same
branch (commit referenced in git log); Refinements applied where one-line.

## Critical

| id | Finding | Resolution in spec |
|---|---|---|
| F1/C1 | **Chapter streaming + targeting state machine undefined/broken.** `chapter` arrives only at turn end (`done`), but §4.1 said tokens stream "into the open chapter" — on every new-chapter turn prose lands in the wrong section until done; and §3.1's open-chapter title rule makes rewrite/regenerate turns append duplicate sections instead of re-settling/replacing (regenerate-with-retitle makes the page worse). | §4.1 now specs the **live-edge staging** mechanism (tokens stream at the document's edge; heading + placement settle at done) and §5 defines a **pending-target override** (during rewrite/regenerate the next done beat routes to the requested chapter regardless of emitted title, consuming exactly one beat; fossils/choice cards preserved on regenerate — prose only). |
| C2 | **Page reload / server death destroys the whole dossier** — beats were client-only; app.js mints a new session per load. The spec's thesis makes the page "the permanent record", so the loss is the product. | D1a now includes **beat accumulation server-side** (`ChatSession.beats`), session id in `sessionStorage`, and `GET /api/session/{id}/beats` replay — reload with a live server re-renders the document. Cross-restart persistence stays a non-goal. FACILITATOR runbook entry added. |
| C3 | **The Assembly's personalization organ narrated machinery no slice builds** (per-answer skill personalization is r1-B; tweaker's voice pass is optional + manually triggered) — "honest theater" was false at its centerpiece. | §6.3 rescoped: organs tick on REAL events only (`vault`, new `shell` event added in D0, `skill:<id>`, and the identity/vault substitution stage); the "writes your dossier into it" language is explicitly deferred to r1-B; the organ's caption says what actually runs. |
| C4 | **No same-journey escape hatch** — `?mode=architect` is a different journey; if the dossier misbehaves in the room there is no fallback workshop chat. | D1a adds **`?ui=chat`** — the current workshop chat skin kept reachable on the same backend until dossier parity is proven at a dress rehearsal; removed in a later cleanup slice. |
| F2 | **§8 contradicted §7.0** ("chief-of-staff untouched" vs D0's substrate cleanup), and "docs-only" was false — `.claude-plugin/`/`marketplace.json` are composer *inputs* (`composer.py:50,119-135`; asserted by `test_composer_package.py`). | §8 reworded (untouched by D1–D3; D0's scoped cleanup is the sole exception); §7.0 relabels the cleanup as substrate-config removal **coupled** to the composer/test rewrite, with commit order + revert path defined (composer stops reading first, then removal; revert in reverse). |

## Improvement

| id | Finding | Resolution |
|---|---|---|
| F3 | Finale + `/api/first-breath` assigned to no slice; "same plumbing as ChatSession" wrong (ChatSession's cwd/tempdir + `--system-prompt-file` + `--exclude-dynamic…` are exactly what first breath must NOT use). | Finale → new slice **D1c**; reuse seam corrected to `stream_parser.parse_line` + `dedup_text` + the `wait_for` budget idiom; flags specified (`--allowed-tools ""`, `--strict-mcp-config` + empty MCP config, NO prompt-replacement flags — the home's CLAUDE.md must load). |
| F4 | D1 was 3-4× a healthy slice with no internal cut line. | Split into **D1a** (shell: extractor+prompt+chapters+writing line+asks+rail+beats replay+escape hatch), **D1b** (rewrite/regenerate), **D1c** (signature close + finale + first breath, gated on D0). |
| F5/I1 | Launch card showed "integrations green" pre-connect (mockup v1c:167 proves it); wizard install-gate silently inverted. | §6.5: integration chips render **pending** and fill live as connect chapters complete; explicit statement that the wizard-gate rule is retired in dossier mode; order fixed (assembly → first breath → connect chapters → launch card completes); mockup's green ticks flagged stale. |
| F6 | D2 `key-field` "hosts, not reimplements" needed a named refactor (wiring lives in `wireWizard`, app.js:217-263, coupled to build-panel DOM). | §3.2/§7.2 name the extraction: factor `wireKeyRow(rowEl, integration, tree)` consumed by both surfaces (google `persist_only` branch included); unknown `integration` id → block skipped (validation rule added). |
| F7/I7 | Manual shelf-drawer picks never enter studio state → the **signed manifest can lie** (participant signs one manifest, builds another). | §4.4: manual add/remove sends `[studio event] participant added/removed <id> via the shelf`; the agent re-asserts whole-state picks; manifest renders from studio picks only (which now can't diverge). |
| F8 | Regenerate title-match targeting underspecified. | Folded into the pending-target override (see F1/C1). |
| F9/I5 | Rewrite "re-settle" over-promised — downstream prose/fossils stand even when a pick they reference is dropped. | §5 scopes it honestly: picks/cards re-settle deterministically; downstream prose stands with a quiet "written before your rewrite of §NN" mark until regenerated; an ask referencing a dropped pick folds. |
| F10/I4 | D0 CLAUDE.md drifted from lean §5 (added "personalization"); `vault/` line collided with onboarding-cards' `vault_dir`; `installLineHtml` GUI copy contested. | §7.0: CLAUDE.md deterministic per lean §5 (identity, owner name, vault path, skill roster); vault written at **resolved `vault_dir`** (second brain when onboarding complete, `<home>/vault/` default) with the path in CLAUDE.md; GUI copy fix explicitly deferred to D1a (stale copy accepted in the gap, flagged). |
| I2 | Organ↔event mapping half-defined; no `shell` compose event; agent-home path plumbing unstated. | D0 adds a `component: shell` compose event; §6.3 maps each organ to its event; §6.4/§6.5 name `done.plugin_path`/`install` as the path/command source, server-side. |
| I3 | First-breath subprocess flags + path provenance (localhost POST could spawn claude in arbitrary dirs). | §6.4: endpoint derives the agent-home path **server-side** from its own compose result — never from the request body; headless flag set specified (see F3). |
| I6 | Failed-turn surfacing missing (today's `**[error]**` bubble path has no dossier equivalent). | §4.1: `type:error` renders as a brass error line in the open chapter, re-arms the writing line, releases any card-held baton; manual-checklist item added. |
| I8/R1 | Sign&build failure/re-entry undefined; re-Build `rmtree`s a connected `.env`; ready-gating unstated. | §6.1: Build enabled only with non-empty picks AND name (mirrors today's gates + server preflight); composer error renders inside the ceremony with an un-sign/retry affordance; post-connect rebuild re-runs connect chapters (documented consequence). |
| I9 | D1↔D3 gap: the C3 onboarding walk renders into surfaces D1's takeover removes — first-launch intake would break. | §7.1 (D1a): in dossier mode the C3 walk mounts as its existing overlay above/before the document until D3 re-skins it. |
| F11/I10 | No per-slice docs checkpoints (ROADMAP item 3 absorbed; substrate README/INSTALL still teach `/plugin install`; no FACILITATOR runbook). | New §9 "Docs checkpoints" (per slice): ROADMAP/CHANGELOG ride each slice's landing PR; substrate README/INSTALL rewrite in D0; FACILITATOR runbook (⟳, first-breath fallback, reload recovery, `?ui=chat`) + SETUP/GUI copy in D1a. |
| R2 | First-breath greeting promised unbuilt scheduling ("tomorrow 7:30 on its own" — r1-A). | §6.4: greeting prompt constrained to composed reality (no scheduling promises until r1-A). |

## Refinement (applied where one-line, else noted)

- R3 commit-order/revert for D0 → applied (see F2). R4 advanced-controls parity row → applied to §4.4. R5/F11 mockup name "Morning, Lucas." → noted in spec header as sample copy; genericize to "Ada" when mockups are next touched.
- Testing additions (Staff §3.6): first-breath preflight negative (no composed home → error event, never a spawn); per-block field negatives (`step` w/o `text`, `key-field` unknown integration); beats-replay endpoint tests; D2/D3 manual checklist items; explicit note that the chapter-grouping algorithm is manual-checklist-covered (no JS runner) with named steps.

## Verified-good (no action)

Every §7.4 reuse claim matches the onboarding spec/plan; §2's design table matches v1b line-for-line; D0's backend footprint has zero overlap with the onboarding plan's touched files; fence discipline intact; architect-mode byte-identity preserved; mockups public-safe (grep clean); the fresh-uuid4 session-id convention correctly avoided the consumed-id trap.
