# Workshop Studio r1 — per-skill personalize · own infra live · always-on

**Date:** 2026-07-02
**Status:** Draft — awaiting Lucas review (next session) + shipshape gate 1
**Author:** Claude, from Lucas's proofing round r1 + follow-up answers
**Revises:** `2026-07-01-workshop-studio-compose-tweak-design.md` (v1, shipped as PR #27) — three
decisions change; everything not named here stands as v1 shipped it.
**Source notes:** `proofing-participant-journey-r1-2026-07-02T06-52-35-902Z.json` (3 comments on the
participant-journey mockups) + AskUserQuestion answers in the same session.

> **Superseded in part (2026-07-02, lean-distribution brainstorm):** §4's "install stays plugins"
> is REVERSED — the composer now emits a raw-skills **agent home directory** (`.claude/skills/` +
> `CLAUDE.md` + root `.mcp.json`), installed by `cd <dir> && claude`. The always-on half of c3
> stands (scheduler targets the agent home). This spec's r1 changes ship in the new public
> **`qubitstudio-agentbuilder`** repo. See
> **`2026-07-02-workshop-lean-distribution-design.md`**.

---

## 1. What changed and why — the three notes

| # | Lucas's note (verbatim) | Decision |
|---|---|---|
| c1 | "more time should be spent here personalising each of the skills to their specificity and use cases" | **Per-skill personalization becomes a studio step** — each picked skill gets its own use-case Q&A + a scoped tailoring pass. Replaces v1's single global voice pass (v1 §6 "YAGNI" stance reversed). |
| c2 | "they need to do this live i think, each of their keys etc. because they will need to set up their own discord servers" | **Participants create their OWN infrastructure, live, guided** — own Discord server + bot, own Linear workspace, own Google Cloud OAuth client. Reverses v1 §2.1 lever #1 (facilitator-shared infra + credentials handout). |
| c3 | "is plugins still the best way to install these agents? How does it have persistent on? Is that part of this?" | **Plugins stay the install mechanism** (marketplace add + install is correct and shipped). **Always-on enters scope**: the studio registers the per-OS scheduled task — Lucas's own reasoning: "otherwise how can the drain even pull out the discord/linear messages?" |

### 1.1 The Google OAuth question, answered (from Lucas's c2 follow-up)

> "I don't understand what you mean when you say GCP is shared… unless you mean having 1 gcp oauth
> (i.e. my personal one) is enough for them to mint tokens to their own emails?"

**Yes — exactly that.** An OAuth client id/secret identify the *application*, not any account. Each
participant's consent click mints a refresh token to **their own** Google account and data, even
against a shared client. v1 leaned on this to keep GCP-console work out of the room.

**r1 rejects the shared client anyway — for ownership, not correctness.** A token minted against the
facilitator's client leaves a permanent dependency: revocation, quotas, and the test-user list all
live in Lucas's GCP project. Since the agent's long-term home is the participant's infrastructure,
each participant creates their **own** Cloud project + OAuth client.

**Gotcha the guide must encode:** an OAuth app left in **Testing** status (a) requires the
participant to add *themselves* as a test user, and (b) expires refresh tokens after ~7 days. The
guide shows the publish path (or documents weekly re-consent as the lazy alternative).

## 2. Change 1 — per-skill personalization (c1)

**Catalog (additive):** each `shelf.items[*]` gains a `personalize` array — 2–3 concrete use-case
questions per skill:

| Skill | Example questions |
|---|---|
| crm | "Who do you track — clients, investors, team?" · "What matters about them — last contact, commitments, personal details?" |
| intake | "Where do screenshots go by default — tasks, notes, wiki?" |
| briefing | "Which channel and what time?" · "What do you want first — conflicts, priorities, news?" |
| scheduling | "Default meeting length + preferred slots?" |
| tasks | "Which project is your default?" |
| drain | "What counts as urgent for you?" |

Each entry: `{key, question, hint, targets}` where `targets` names the substitution block
(SKILL.md personalization section and/or vault `memories.md`).

**Tweaker (signature change):** `tweak(tree, fields, skill_answers: dict[str, dict]) ->
AsyncIterator[event]`. Three mechanisms, strictly ordered:
1. **Owner substitution** — unchanged from v1 (`{{OWNER_*}}`, deterministic, always safe).
2. **Per-skill Q&A → deterministic substitution (new).** Answers land in a personalization block in
   that skill's SKILL.md + seed the vault's `memories.md`. No LLM; cannot fail; this alone already
   gives a personalized agent.
3. **Per-skill tailoring pass (new — replaces the single voice pass).** One scoped `claude -p` per
   picked skill: given that skill's answers + the participant's voice sample, rewrite the skill's
   guidance/examples/tone. Scoping unchanged (`--allowed-tools Read Edit` as SEPARATE variadic
   tokens; `--add-dir <tree>`). Passes run **sequentially** (one laptop, one quota), each
   **independent and non-fatal**: a failed pass leaves that ONE skill generic; every other skill
   keeps its tuning. Streams per-skill `component` events so the participant watches each skill
   become theirs.

**UI:** the personalize step renders one Q&A card per picked skill + the voice textarea; the build
panel shows per-skill progress. This is now a headline agenda block, not a 30-second form.

## 3. Change 2 — own infrastructure, created live, guided (c2)

**Reverses v1 §2.1 lever #1.** No shared Discord bot, no shared Linear workspace, no shared OAuth
client, no credentials handout. Each participant creates, in the room:
1. **Their Discord server + bot** (~10 min guided) — this server is the agent's permanent inbox.
2. **Their Linear workspace + API key** (~5 min guided).
3. **Their Google Cloud project + OAuth client + consent token** (~15 min guided; see §1.1 gotcha).

**What makes 20× live provisioning survive the room:**
- **Walkthrough guides baked into the wizard.** Each Connect row leads with its creation steps
  ("open discord.com/developers → New Application → Bot → Reset Token → …"), sourced from the wiki
  setup guides already written from real setups with real friction points (the agent-builder
  walkthroughs directive). Paste fields follow; **Test** after every paste so a failure surfaces at
  the step that caused it (smokes unchanged from v1, incl. the DiscordBot User-Agent 403 gotcha).
- **Hard per-integration time-box** in the agenda + **"finish at home" uses the same guides** — the
  degrade path is identical work, later, not different work.
- `WORKSHOP_DEFAULTS` shrinks to non-secret suggestions only (channel names, task names).

**FACILITATOR.md is repurposed** from shared-infra runbook → **guide-prep + room-support runbook**:
verify the guides against the live consoles before Friday, wire them into the wizard, set the
per-integration time-boxes, prepare the troubleshooting cheat-sheet (DiscordBot UA 403, OAuth
Testing expiry, `setx` history caveat), and stand up a **room Discord as help/demo channel only** —
never anyone's agent infra.

## 4. Change 3 — always-on (c3)

**Install stays plugins** — `/plugin marketplace add <dist/<slug>-cos>` → `/plugin install` →
restart, exactly as shipped. But install only makes skills *available when chatting*. Drain and
briefing are cron-style: without a heartbeat they never fire.

**New unit `studio/scheduler.py`:** `schedule(tree, picks) -> {registered, cmds}`.
- **Catalog (additive):** shelf items gain `schedule` (nullable): drain `every 15 min`, briefing
  `weekdays 07:30` (defaults — open question §7.3).
- **Per-OS registration:** Windows → hidden S4U `schtasks` task; macOS → launchd plist; Linux →
  cron entry. All bake the known-safe headless flags: `--strict-mcp-config` + an empty MCP config +
  hidden window (the canonical `claude -p` MCP-leak/popup fix from cos v0.5.1).
- **`POST /api/schedule {tree, picks}`** (plain JSON) + a wizard step after install: **"Run it on a
  schedule"** — registers directly, and always prints the exact commands as the manual fallback.
- **Expectation set in the UI + README:** the heartbeat runs while the laptop is on; a sleeping
  laptop pauses the agent, it doesn't break it.

## 5. Architecture delta

```
   personalize ──►  POST /api/tweak     ─►  studio/tweaker.py    (owner subst + per-skill Q&A subst
                          │                                       + sequential scoped claude -p per skill)
                          ▼
   connect     ──►  POST /api/keys/test ─►  studio/smokes.py     (unchanged — validate what YOU created)
   integrations             │  guided create-your-own → paste YOUR values → Test → ✅/❌
                          ▼
   always-on   ──►  POST /api/schedule  ─►  studio/scheduler.py  (register per-OS task, safe headless flags)
                          ▼
                    installed plugin + registered heartbeat  ──►  runs proactively, laptop-on
   (participants CREATE their own Discord+Linear+Google infra live, guided by baked-in walkthroughs;
    facilitator preps guides + troubleshoots — owns nothing the agent depends on)
```

New/changed surfaces: `studio/scheduler.py` ✚ · `studio/tweaker.py` (per-skill) · `studio/server.py`
(`/api/schedule`) · `studio/catalog.json` (`personalize`, `schedule` — additive; `update-workshop`
sync invariants must learn both) · wizard UI (guided-create rows, always-on step, per-skill Q&A
cards) · `studio/FACILITATOR.md` (repurposed) · `studio/SETUP.md` (see §7.1).

## 6. Scope & sequencing (Friday is 2 days out)

- **R1-A — Friday run-of-day critical:** guided-create wizard content (guides wired into rows) +
  `scheduler.py` + `/api/schedule` + the always-on step. Without A, the c2/c3 flow doesn't exist on
  the day. Degrade: scheduler falls back to printing commands from a guide page — never silent.
- **R1-B — Friday-strong:** per-skill Q&A cards + deterministic substitution (catalog `personalize`
  + tweaker mechanism 2). Degrade: v1's shipped personalize (name + voice) still works.
- **R1-C — enhancement:** per-skill AI tailoring passes (mechanism 3, replaces the single voice
  pass). Degrade: Q&A tuning already landed deterministically; that skill's prose stays generic.

## 7. Open questions — feedback wanted here

1. **Pre-work the slow one?** Google project + OAuth client creation could move into the emailed
   `SETUP.md` pre-work (done at home, days before), leaving only consent + Test in-room.
   *Recommended: yes* — it's the slowest, most console-fiddly creation, and it parallelizes to
   home-time; Discord + Linear stay live (fast, and the Discord server is the demo moment).
2. **Scheduler auto-run vs print-only?** *Recommended: auto-register* (user-level `schtasks`/launchd
   needs no admin) with the printed commands always shown as fallback/receipt.
3. **Default cadences:** drain every 15 min, briefing weekdays 07:30 local — confirm or change.
4. **Room Discord** = help/demo channel only, never agent infra — confirm.
5. **Per-skill pass runtime:** sequential passes ≈ 30–60 s per skill on the participant's quota;
   with 4–5 picks that's a few minutes of watching the panel. Acceptable, or cap AI passes to the
   2–3 skills the participant flags as "most mine"?

## 8. Risks (delta from v1 §11)

| Risk | Mitigation |
|---|---|
| 20× live self-provisioning eats the room | Guides with real friction points baked into wizard rows; Test after every paste; hard time-boxes; "finish at home" = same guides (§3); optionally pre-work Google (§7.1) |
| Google OAuth app in Testing status silently breaks in a week | Guide covers add-self-as-test-user + publish path (or weekly re-consent); smoke confirms the minted token before they leave (§1.1) |
| Scheduled task leaks MCP servers / RAM or pops windows | `scheduler.py` bakes `--strict-mcp-config` + empty MCP config + hidden S4U — the shipped cos v0.5.1 fix (§4) |
| A per-skill AI pass fails mid-room | Non-fatal + independent per skill; deterministic Q&A tuning already landed (§2) |
| "My agent stopped working at home" (laptop off) | Expectation set in UI + README: heartbeat = laptop-on; not a bug (§4) |

## 9. Testing (delta)

- **Catalog:** every shelf item has `personalize: []` (may be empty) and `schedule` (nullable);
  `update-workshop` invariants extended to both.
- **Tweaker:** each picked skill's answers land in its own personalization block + `memories.md`;
  a failed pass yields a per-skill warning event while other skills' events complete; passes are
  sequential.
- **Scheduler:** generated registration per OS is well-formed and includes the safe headless flags
  (assert `--strict-mcp-config` + hidden/S4U args present); actual registration + live cadence stay
  in the manual/integration lane.
- **Wizard:** rows render the walkthrough steps from the guide source; Test wiring unchanged from
  v1; the always-on step appears iff a pick has a non-null `schedule`.
- **E2E manual (Friday dress rehearsal):** one full run — compose → per-skill personalize → create
  own Discord/Linear/Google following only the on-screen guides → all Tests green → install →
  register schedule → watch one real drain tick fire.
