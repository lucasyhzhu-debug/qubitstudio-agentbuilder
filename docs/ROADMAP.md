# Roadmap

Workshop is **Friday 2026-07-03**. Build order is risk-sorted with hard cut lines — each item
lands independently; a cut anywhere still leaves a working workshop (floor = v1 as migrated).
Authority for design detail: `docs/specs/2026-07-02-workshop-lean-distribution-design.md` (this
migration + raw skills) and `docs/specs/2026-07-02-workshop-studio-r1-personalize-own-infra-always-on-design.md` (r1).

## Tonight (pre-workshop), in order

1. ~~Migrate to this repo~~ — **done** (v0.1.0, incl. `agent-architect/` — the core conversation
   agent; its absence originally failed 13/98 tests, all fixed by migrating it).
   - **Known failure:** `test_smoke_integration.py::test_one_real_turn` (a REAL `claude -p`
     round-trip) failed in the migration session's sandboxed environment. This is exactly the
     "first-run GUI↔agent handshake" requirement below — verify live (`python -m studio`, watch
     the first chat stream) as the first act in this repo.
2. **Raw-skills packaging** — composer emits an agent-home dir (`.claude/skills/`,
   `.claude/agents/`, root `.mcp.json`, generated `CLAUDE.md`, `vault/`, `.env`); final step
   becomes `cd <dir> && claude`. Kill plugin.json/marketplace.json emission + the `/plugin`
   install copy in GUI/README. Includes the **reference-path invariant** test (every reference
   mentioned in a shipped SKILL.md resolves from the agent-home root). Lean spec §5.
3. **r1-A: always-on** — `studio/scheduler.py` + `POST /api/schedule` + wizard step; per-OS task
   (schtasks S4U hidden / launchd / cron) with the safe headless flags (`--strict-mcp-config` +
   empty MCP config), cwd = the agent home. r1 spec §4.
4. **r1-B: per-skill personalize** — catalog `personalize` questions per skill, deterministic
   substitution into SKILL.md personalization blocks + vault `memories.md`, Q&A cards in UI.
   r1 spec §2.
5. **r1-C: per-skill AI tailoring passes** — sequential scoped `claude -p` per picked skill,
   non-fatal per skill. r1 spec §2.
6. **Own-infra wizard guides** — Discord server+bot / Linear workspace+key / Google Cloud OAuth
   walkthroughs wired into the connect rows, Test after every paste. r1 spec §3. (Content work —
   parallelizable with 3–5.)

## Product requirements (from Lucas, 2026-07-02 — refine here)

- **Custom vault location.** Participants choose where the agent's local wiki-brain vault lives
  (default `<agent-home>/vault/`, always local to their machine). A compose/personalize field;
  every `{{VAULT_PATH}}` substitution honors it.
- **First-run GUI↔agent handshake.** The first agent a participant ever uses is the agent-builder
  itself, via the GUI talking to `claude -p`. On first studio start the UI must *verifiably* show
  it is talking to the agent (surfaced handshake/echo, not a silent spinner).
- **Conversation-context persistence.** The journey's conversation context (compose →
  personalize → connect → schedule) must be stored in the right place for the whole workflow —
  one continuous session/state, not per-request amnesia. Decide the store (session id resume vs
  transcript file in the agent home) and make it survive a studio restart.

## Research / open

- **Google connect blocker (before the room):** confirm whether anything beats "own GCP project +
  OAuth client, guided" for Gmail/Calendar — device flow, `gcloud` ADC shortcuts, 2026 console
  publish friction. Escape hatch if the room stalls: shared OAuth client (technically sound —
  each consent mints the participant's own token; ownership caveat documented, "migrate to your
  own client later"). Output lands in `studio/FACILITATOR.md`. Lean spec §9.
- r1 open questions resolved to recommended defaults unless overridden: Google client creation is
  pre-work; scheduler auto-registers (printed fallback); drain 15 min / briefing weekdays 07:30;
  room Discord = help only; tailoring passes uncapped, sequential.

## Cleanup / later

- Remove `chief-of-staff/.claude-plugin/`, `marketplace.json`, and plugin-install wording in
  `chief-of-staff/README.md` + `INSTALL.md` once raw-skills packaging lands (they're vestigial
  here).
- Prune vestigial Lucas-form entries from `composer._subs` once the substrate is verified fully
  placeholder-form (tests currently encode the original contract).
- E2E dress rehearsal after the cut line: fresh clone on a second machine/profile → `--doctor` →
  full journey → agent home → skill triggers → one real drain tick.
