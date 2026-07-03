# Design: `daily-interest-brief` shelf skill

**Date:** 2026-07-03
**Status:** design — pending Lucas review, then plan (`/spec-plan-pipeline`)
**Author:** agent-architect studio work (Lucas + Claude)

## 1. Problem

The dossier journey lets a participant assemble a chief-of-staff from a fixed shelf of 7
skills. Nothing on the shelf gives them an **outward-looking daily pulse** — a
newsletter-style update on the topics they follow (news, a sport, a company, a market, a
policy area). Participants who want "a daily newsletter from my agent" have no pick for it.

We want to add one shelf skill that fills this gap, sourced from the MIT-licensed
`daily-interest-brief` skill in `github.com/Nicegarrry/claude-skills`.

## 2. Provenance & licence

- **Source:** `Nicegarrry/claude-skills` → `daily-interest-brief/`
  (`SKILL.md` + `scripts/collect_updates.py` + `agents/openai.yaml`).
- **Licence:** MIT, © 2026 Nick Pinidiya. Permissive; reuse/modify allowed **provided the
  copyright + permission notice is retained**. We keep the notice in any vendored file and
  credit the origin in `CHANGELOG.md` (matching this repo's provenance discipline).
- This is third-party code entering a **public** repo — it must be vetted before it ships,
  and it must obey the placeholder contract (no real personal values).

## 3. Review of the vendored skill

Reviewed statically (the studio's permission classifier correctly **refused to execute** the
freshly-cloned script — untrusted-until-vetted — which is the posture we want).

| # | Finding | Severity | Resolution |
|---|---|---|---|
| R1 | Foreign idiom: `SKILL.md` description says "when **Codex** needs to…"; script `USER_AGENT` points at `openai.com`; `agents/openai.yaml` is an OpenAI-runtime file. | cosmetic / fit | Rewrite `SKILL.md` front-matter + body to Claude Code idiom; neutralise `USER_AGENT`; **drop `agents/openai.yaml`** entirely. |
| R2 | Stateless/generic: the skill knows nothing about a wiki-brain vault — it takes an interest as an argument. Our substrate skills read/write the vault. | fit (main work) | Author a "read interests from the vault, write the brief back" layer: interests live in the vault self-layer (`meta/chief-of-staff/interests.md`), briefs delivered in chat and optionally filed to the vault. |
| R3 | `scripts/collect_updates.py` parses untrusted RSS/XML with stdlib `xml.etree.ElementTree`, which Python's own docs flag as vulnerable to "billion laughs"/quadratic-blowup entity expansion. | low (local, single-user; feeds are mostly Google News; worst case is self-DoS) | Accept for a local personal tool (adding `defusedxml` would break the zero-dependency property). Note the risk in the SKILL.md; the script stays an **optional** helper, not the primary path. |
| R4 | Script fetches arbitrary URLs (`--feed`, Google News RSS). | low (runs as the owner, on their own machine) | No change; documented. |
| R5 | Cross-platform: script hard-codes `python3`; our reference dev env is Windows/PowerShell where it's `python`. | correctness on Windows | Lead the SKILL.md with **native `WebSearch`/`WebFetch`** (which a Claude Code agent has and which cover the whole job); present the script as an offline/deterministic fallback invoked with the platform's Python. |
| R6 | Insight depth: bullets carry a one-line "why it matters" and cross-check high-impact claims against ≥2 sources — decent but shallow by default. | product (per Lucas: "leave to the participant") | Give each interest an optional `angle`/depth in the vault interests file so the participant dials in insight. No heavier machinery. |

**Verdict:** good fit, low risk, high value. The real work is R1 (de-Codex) + R2 (vault
wiring); everything else is a note or a deletion.

## 4. Locked scope (from brainstorm)

- **Lean, keyless, on-demand, standalone.** `requires: []`, `needs_skills: []`, **free** tier.
- Composes with `briefing` when both are picked (interest section folds into the morning
  brief) but never **requires** it — that would drag in `briefing`'s Google key and kill the
  keyless property.
- **Out of scope:** genuine always-on daily automation. That needs the r1 always-on scheduler
  (specced, not built — `docs/ROADMAP.md`). "Daily" here = the participant asks each morning,
  or it rides the `briefing` sweep, exactly as `briefing` works today.

## 5. Changes

### 5.1 New substrate skill — `chief-of-staff/skills/daily-interest-brief/`

- `SKILL.md` — Claude-idiom rewrite. Reads followed topics from the vault
  (`meta/chief-of-staff/interests.md`; each entry may carry an `angle`), produces **3–5
  sourced, link-rich bullets** via native `WebSearch`/`WebFetch` first, each with a
  "why it matters" clause; cross-checks high-impact claims against ≥2 sources; writes any new
  interests it learns back to the vault (wiki-brain read-before-act / write-what-you-learn).
  Placeholder-clean; retains the MIT notice reference.
- `references/collect_updates.py` — the vendored stdlib RSS helper, kept as an **optional**
  deterministic fallback (zero-dependency, so it ships cleanly). `USER_AGENT` neutralised;
  MIT header retained. Lives under `references/` because the composer copies every skill's
  `references/` tree verbatim (see 5.2).
- **Not vendored:** `agents/openai.yaml` (OpenAI-runtime artefact).

### 5.2 Composer — `studio/composer.py`

- Add `"daily-interest-brief"` to `_ALL_SKILLS` (line 50) so its `references/` ships and the
  cross-skill path-rewriter covers it. (A picked skill's `SKILL.md` already ships regardless.)
- No other composer change: free tier ⇒ `assemble_manifests`/`.mcp.json`/keys untouched.

### 5.3 Catalog — `studio/catalog.json`

New shelf item (name is the one open bikeshed — see §8):

```json
{
  "id": "daily-interest-brief",
  "name": "Interest radar",
  "what": "A daily, newsletter-style pulse on the topics you follow — 3–5 sourced, link-rich bullets on news, a sport, a company, a market, or a policy area.",
  "deliverable": "a sourced daily interest brief",
  "cost": { "label": "local · no keys · web", "tier": "free" },
  "requires": [],
  "needs_skills": [],
  "brief": "Interest radar — each morning, pull 3–5 sourced, link-rich bullets on the topics I follow (news, a sport, a company, a market, a policy area) using free RSS + web search, and fold them into my brief. No paid data, no keys."
}
```

### 5.4 Interview — `studio/system_prompt.py` (`_WORKSHOP_CONTRACT`)

Add one interview topic to the one-at-a-time list: *"the beats they follow and want a daily
pulse on (news, a sport, a company, a market, a policy area) → `daily-interest-brief`."*
The catalog entry surfaces automatically to the interviewer via `_render_catalog`.

### 5.5 Provenance — `CHANGELOG.md`

Add an entry crediting `Nicegarrry/claude-skills` (MIT) as the origin of the skill + script.

## 6. Testing

- Extend `test_composer_copy.py::test_reference_path_invariant_all_shelf_picks` — add
  `"daily-interest-brief"` to its `picks` list so any `references/*.md` it mentions must
  resolve from the agent-home root.
- Add a small `test_catalog.py` assertion: the new item is keyless/free-tier
  (`requires == []`, `cost.tier == "free"`).
- Full suite green: `python -m pytest studio/tests`.
- The composed agent's own runtime behaviour (actually pulling a brief) is exercised by the
  participant, not the studio test suite — consistent with how the other shelf skills are
  tested (studio tests cover composition, not the skills' live behaviour).

## 7. Out of scope / non-goals

- No scheduler / cron / always-on push (r1).
- No new integration, key wizard, or smoke test.
- No change to the dossier front-end (`dossier.js`) — a new free shelf item flows through the
  existing picks-diff and manifest with zero UI work.
- No deepening of the brief's "insight" beyond the per-interest `angle` hook (per Lucas:
  leave depth to the participant).

## 8. Open items

- **Shelf name.** "Interest radar" avoids collision with `briefing`'s "Daily debrief".
  Alternatives: "Daily digest", "Topic radar", "Signal". Trivially changeable.
