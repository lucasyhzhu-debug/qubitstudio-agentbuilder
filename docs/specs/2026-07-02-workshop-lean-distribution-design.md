# Workshop Lean Distribution — `qubitstudio-agentbuilder` (export · raw skills · full r1)

**Date:** 2026-07-02
**Status:** Draft — awaiting Lucas review + shipshape gate 1
**Target:** QubitStudio "Build Your Own Chief of Staff" workshop, **tomorrow** (Friday 2026-07-03)
**Author:** Claude, from Lucas's brainstorm answers this session
**Depends on:** v1 compose+tweak (shipped, PR #27) · r1 spec
(`2026-07-02-workshop-studio-r1-personalize-own-infra-always-on-design.md`, draft)
**Revises:** r1 §4's install half — **plugins are replaced by a raw-skills agent-home directory**
(the always-on half of r1 c3 stands, and gets simpler).

> **Revision r2 (same day, pre-migration):** the new repo is a **permanent development home**, not
> a build artifact — see §12. §4's exporter-as-ongoing-sync and §7's "no hand edits" are
> superseded by a **one-time surgical migration**; workshop/agent-experience development continues
> in `qubitstudio-agentbuilder` from then on. §12 also adds two product requirements from Lucas:
> a custom (still-local) vault location, and first-run GUI↔agent connectivity + conversation-context
> persistence across the journey.

---

## 1. Problem

Participants currently need this entire mono-repo to run the studio: seven consulting plugins,
agent-architect, wiki-brain, specs, sandbox, dashboards — none of which they touch, all of which is
IP, clone weight, and confusion. And the journey's final step (`/plugin marketplace add` +
`/plugin install` + restart + trust prompt) is three failure points × twenty laptops, plus the known
split-brain gotcha: cron reads SKILL.md from the working tree while the interactive Skill loader
reads the installed plugin cache.

This phase produces a **lean, participant-facing repo** containing only the GUI, the journey, and
the substrate — and swaps the plugin install for a **raw skills + md agent-home directory**.

## 2. Locked decisions (from brainstorm)

| Decision | Choice | Why |
|---|---|---|
| **Delivery** | Export script → new **public GitHub repo `qubitstudio-agentbuilder`** | One clone URL on a slide; mid-workshop fixes ship via `git pull`; regenerable from this repo so it never drifts |
| **Install mechanism** | **Raw skills agent-home dir** — no marketplace, no `/plugin install` | Kills the split-brain; final step collapses to `cd <dir> && claude`; a folder of editable md IS the workshop artifact |
| **Journey scope** | **Full r1** (per-skill personalize · own-infra wizard · always-on) ships in the new repo | Lucas's pick; risk managed by the cut-line build order (§8) |
| **Repo name** | `qubitstudio-agentbuilder` | Lucas's pick |
| **GCP research** | Flagged follow-up, after migration (§9) | Gmail/Calendar connect is the #1 room-blocker risk; shared-OAuth-client is the proven escape hatch |

## 3. Unit: the lean repo layout

```
qubitstudio-agentbuilder/
  studio/              ← as-is: launcher+doctor, server, static GUI, composer, tweaker,
  │                       smokes, (r1: scheduler), catalog.json, templates/vault/
  chief-of-staff/      ← the compose substrate: skills/, agents/, references/, .mcp.json
  requirements.txt
  README.md            ← participant pre-work (today's studio/SETUP.md promoted to root,
  │                       rewritten for the clone-first flow)
  FACILITATOR.md       ← r1's guide-prep + room-support runbook
```

- **Same relative layout** (`studio/` sibling of `chief-of-staff/`) — `composer.py`'s
  `_HERE.parent / "chief-of-staff"` style paths need **zero changes**.
- **Excluded:** all consulting plugins, wiki-brain, registry/, dashboard/, docs/,
  sandbox/, templates/, scripts/ (repo-dev tooling), evals/, studio tests + PERF.md, eval-runs/.
- ~~**Advanced generate-from-scratch mode is hidden**~~ — **superseded (r3, same day):**
  `agent-architect/` **migrates too** (scrubbed). Lucas: the architect chat is the **core
  conversation agent** the participant talks to from the first moment of the journey — the studio
  literally builds its chat system prompt from agent-architect's references
  (`server.py:/api/session/new` → `system_prompt.py` → `quiz-bank.md`), which the 13/98 test
  failures at v0.1.0 confirmed: without it the GUI's first conversation 500s. Nothing is hidden;
  the conversation is the spine, compose is a tool the conversation drives.

## 4. Unit: exporter (`scripts/export-workshop.py`, this repo)

**Purpose:** deterministically produce the lean tree from this repo's working state, so the lean
repo is a build artifact, never a fork.

- `python scripts/export-workshop.py --out <dir>` — copies an **allowlist** (§3 layout), never a
  denylist of the mono-repo.
- **Scrub pass — fails loudly (non-zero, listing every hit) on:**
  - Linear team/project UUIDs (`d885fd34-…`, `504fb62b-…`)
  - `OWNER_USER_ID` / the raw Discord user id `{{OWNER_USER_ID}}`
  - personal emails (`you@example.com`, `you@example.com`), `your-assistant-bot`
  - absolute vault paths (`{{VAULT_PATH}}` and forward-slash form)
  - a CRM-name denylist file (`scripts/export-denylist.txt`, facilitator-maintained) for real
    people quoted in `references/`
  - any `.env`, token-shaped string (`lin_api_`, `xoxb`-style, `AIza`, OAuth client secrets)
- Scrub hits are **fixed in this repo's source** (genericize the example / move the value behind a
  placeholder), then re-export — the exporter never rewrites content itself, so the two repos can't
  silently diverge.
- Also emits `--zip <path>` — a no-git fallback for stragglers, hosted on the hub.
- Writes `EXPORTED-FROM` (source commit sha) into the lean repo root so provenance is always known.
- **Publish flow:** exporter output is committed + pushed to `qubitstudio-agentbuilder` by the
  facilitator (manual `git add -A && commit && push` in the export dir — no automation tonight).

## 5. Unit: raw-skills packaging (revises r1 c3's install half)

`composer.py`'s package step stops emitting a plugin and emits an **agent home directory**:

```
dist/<name>-cos/
  .claude/
    skills/<picked>/SKILL.md         ← was skills/<picked>/SKILL.md
    agents/context-gatherer.md       ← was agents/
  .mcp.json                          ← unchanged (project-root .mcp.json loads the Discord MCP)
  CLAUDE.md                          ← NEW: generated — agent identity, owner name, vault path,
  │                                     picked-skill roster; absorbs plugin.json's role
  skills/<sk>/references/            ← substrate: every skill's references/, unchanged location*
  references/                        ← top-level substrate, unchanged
  vault/                             ← scaffolded vault, unchanged
  .env                               ← written by the connect step, unchanged
```

\* **Reference-path invariant:** SKILL.md files address their references relatively (e.g.
`skills/<sk>/references/…` from the plugin root). Moving SKILL.md under `.claude/skills/` breaks
that base. Resolution: the substrate keeps its current paths and the composer rewrites reference
mentions in copied SKILL.md files to be **agent-home-root-relative** (deterministic string pass,
same class as `delucas()`), OR references move under `.claude/skills/<sk>/references/` wholesale —
**decided at plan time by reading what the SKILL.md files actually say**; the invariant is "every
reference mentioned in a shipped SKILL.md resolves from the agent home root", enforced by a
composer test.

Dropped entirely: `.claude-plugin/plugin.json`, `marketplace.json`, the `/plugin marketplace add ;
/plugin install` instruction. The GUI's final card, README, and the r1 wizard's install step say:

```
cd dist/<name>-cos
claude
```

**Always-on gets simpler (r1 c3's other half, unchanged in intent):** `scheduler.py` registers the
per-OS task with the agent home as cwd — `claude -p` there loads the same `.claude/skills/` the
interactive session uses. Working-tree-vs-installed-plugin ceases to exist as a concept. The safe
headless flags (`--strict-mcp-config` + empty MCP config + hidden S4U / launchd / cron) are
unchanged from the r1 spec §4.

**Trade-offs accepted:** skills only trigger with Claude Code running in the agent home (framed in
the UI/README as "your agent lives in this folder"); no plugin update channel (right: a
personalized agent should not be clobbered by upstream updates — improvements arrive as new guides
or a re-compose).

## 6. Journey scope: full r1

The r1 spec's three changes (per-skill personalize · own-infra live wizard · always-on) ship **in
the lean repo**, built in this repo and exported. This spec does not restate them — r1 remains the
authority for those units — with two deltas:

1. **r1 §4 "Install stays plugins" is superseded** by §5 above.
2. r1's open questions §7.1–7.5 are resolved at plan time with the recommended answers unless Lucas
   objects at spec review: pre-work the Google project/OAuth creation (7.1 yes), scheduler
   auto-registers with printed fallback (7.2), drain 15 min / briefing weekdays 07:30 (7.3), room
   Discord = help only (7.4), AI tailoring passes uncapped but sequential (7.5).

## 7. What changes in THIS repo vs the lean repo

| Surface | Where the change lives |
|---|---|
| `scripts/export-workshop.py` + denylist | this repo only |
| `composer.py` raw-skills packaging + CLAUDE.md template + reference-path invariant test | this repo, exported |
| GUI final card / README / SETUP install copy | this repo, exported |
| r1 units (tweaker per-skill, scheduler, wizard guides, catalog `personalize`/`schedule`) | this repo, exported |
| Advanced-mode suppression (`.workshop-dist` marker check) | code in this repo; marker written only by exporter |
| `update-workshop` skill gains the lean repo as a third sync surface | **post-workshop follow-up** — tomorrow only needs the script to run |

The lean repo receives no hand edits except its own README badge/links; every content change flows
source-repo → export → push.

## 8. Build order tonight (risk-sorted, hard cut lines)

Each step lands independently; a cut anywhere leaves a working workshop.

1. **Exporter + repo push** — v1 journey works in `qubitstudio-agentbuilder` immediately. *Floor.*
2. **Raw-skills packaging** (§5) + install-copy rewire.
3. **r1-A: always-on** (`scheduler.py`, `/api/schedule`, wizard step) — now targeting the agent home.
4. **r1-B: per-skill personalize** (catalog `personalize`, tweaker mechanism 2, Q&A cards).
5. **r1-C: per-skill AI tailoring passes** (mechanism 3).
6. **r1 own-infra wizard guides** (Discord/Linear/Google walkthrough content wired into connect
   rows) — content work, parallelizable with 3–5, and the piece §9's research feeds.

If the evening ends mid-list: re-run the exporter at the cut line; tomorrow runs on what landed.

## 9. Flagged research: the GCP / Google-connect blocker

**Risk statement (Lucas):** if participants can't actually connect Gmail/Calendar tomorrow, that's
a huge blocker; if it's merely painful via GCP, that's acceptable.

Known ground truth going in:
- There is **no API path to a user's Gmail/Calendar without OAuth consent** — some GCP touchpoint
  is unavoidable for personal accounts.
- A **shared OAuth client is technically sound** (each consent mints a token to the participant's
  own account/data) — rejected in r1 for ownership only, **not correctness**. It is the proven
  in-room escape hatch: facilitator hands out client id/secret, participant only clicks consent.
- Service accounts (cos v0.8.0 enabler) help only Workspace-domain accounts, not personal Gmail.
- Testing-status OAuth apps: add-self-as-test-user + ~7-day refresh-token expiry (guide must
  cover the publish path or weekly re-consent).

**Research task (after the repo migration, before the room):** confirm whether anything beats
"own GCP project, guided" — device authorization flow, `gcloud` ADC shortcuts, OAuth app publish
friction in 2026 consoles. Output lands in `FACILITATOR.md` as: primary path = own client (guided,
pre-worked per r1 §7.1), escape hatch = shared client with the ownership caveat documented and a
"migrate to your own client later" note.

## 10. Risks (delta from v1 §11 / r1 §8)

| Risk | Mitigation |
|---|---|
| Public repo leaks IP/PII from cos references | Exporter scrub pass fails loudly; fixes land in source; denylist file grows as hits appear (§4) |
| Reference paths break when SKILL.md moves under `.claude/skills/` | Explicit invariant + composer test; resolution picked at plan time from actual SKILL.md contents (§5) |
| Raw-skills agent doesn't trigger because participant launches `claude` elsewhere | UI/README frame "your agent lives in this folder"; CLAUDE.md greets with identity so a correct launch is self-confirming |
| Full r1 unbuilt with one evening left | Cut-line build order (§8); floor = v1 in the new repo; exporter re-runs at any cut |
| Google connect stalls the room | §9: pre-worked own-client path + shared-client escape hatch in FACILITATOR.md |
| Two repos drift | Lean repo is a pure build artifact (EXPORTED-FROM sha, no hand edits); `update-workshop` learns the surface post-workshop |

## 11. Testing

- **Exporter:** allowlist copy is exact (no stray top-level dirs); scrub pass catches every seeded
  denylist token in a fixture tree; `EXPORTED-FROM` present; `.workshop-dist` marker written.
- **Composer (raw-skills):** packaged tree has `.claude/skills/<picks>/SKILL.md`,
  `.claude/agents/`, root `.mcp.json`, generated `CLAUDE.md` with owner/vault/roster; **no**
  `.claude-plugin/` or `marketplace.json`; every reference path mentioned in shipped SKILL.md files
  resolves from the agent-home root (the §5 invariant).
- **Advanced-mode gate:** with `.workshop-dist` present, the architect-chat entry point is absent
  from the served UI; without it, unchanged.
- **r1 units:** test plan unchanged from r1 spec §9, retargeted at the agent home (scheduler cwd,
  no plugin-install assertions).
- **E2E dress rehearsal (tonight, after the cut line):** clone `qubitstudio-agentbuilder` fresh on
  a second machine/profile → `python -m studio --doctor` → full journey → `cd dist/<name>-cos &&
  claude` → skill triggers → (if r1-A landed) one real drain tick fires.

## 12. Revision r2 — migration, not export (same day)

Lucas's direction on review: development of the workshop / agent-builder experience **continues in
the new repo permanently**. This supersedes §4 (exporter as ongoing sync) and §7 ("lean repo
receives no hand edits"):

- **One-time surgical migration** this session, not a repeatable exporter: copy `studio/` (minus
  `.cache/`, `__pycache__`) + `chief-of-staff/` + `requirements.txt` into
  `qubitstudio-agentbuilder`, **pre-applying the `delucas()` substitution class to the source
  itself** (Linear UUIDs → `{{LINEAR_TEAM_ID}}`/`{{LINEAR_PROJECT_ID}}`, `OWNER_USER_ID` →
  `OWNER_USER_ID`, personal emails → `you@example.com`, vault paths → `{{VAULT_PATH}}`,
  `your-assistant-bot` → `your-assistant-bot`). `_subs` entries stay as no-ops; `{{VAULT_PATH}}`
  gains a live `_subs` entry so compose still lands the participant's vault path. Personal names
  in prose stay (Lucas is the public author); compose-time `delucas()` still personalizes them.
- **Studio tests migrate too** (reversing §3's exclusion) — it's a dev home now.
- **Meta-docs transferred:** a tailored `CLAUDE.md` (repo model, setup, lifecycle-lite), a seeded
  `CHANGELOG.md` (provenance: source repo + sha), the three workshop specs (v1, r1, this — scrubbed
  on copy), and a `docs/ROADMAP.md` carrying §8's build order, §9's GCP research, and the two new
  requirements below. **This repo keeps** the consulting agents and Lucas's live cos runtime
  (the drain cron keeps reading `D:\Claude\Consulting-Agents\chief-of-staff` — untouched).
- **New requirement — custom vault location:** participants choose where the agent's local
  wiki-brain vault lives (default `<agent-home>/vault/`, always local). A compose/personalize
  field; all vault-path substitutions honor it. Built in the new repo.
- **New requirement — first-run agent connectivity + context persistence:** the first agent a
  participant uses is the agent-builder itself, via the GUI backed by `claude -p`. On first GUI
  start the studio must *verifiably* be talking to the agent (surfaced handshake, not a silent
  spinner), and the conversation's context must persist in the right store across the entire
  journey (compose → personalize → connect → schedule), not per-request amnesia. Refined and built
  in the new repo.
