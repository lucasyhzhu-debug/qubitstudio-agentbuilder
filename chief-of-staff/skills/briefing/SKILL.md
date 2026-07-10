---
name: briefing
description: Gives Lucas his daily or weekly briefing with proposed priorities, pulling live context from email, calendar, Discord, Linear, and the wiki-brain knowledge base (including CRM). Use whenever Lucas asks what's happening today, what his week looks like, what he should focus on, wants to plan his day or week, says "brief me", asks what's coming up, or wants situational awareness before a meeting or decision.
---

# Briefing

This is Lucas's daily chief-of-staff briefing skill. It assembles situational awareness across every surface Lucas tracks — Gmail, Google Calendar, Discord (mentions + inbox channel), Linear tasks, and the wiki-brain knowledge base (including his personal CRM) — and produces a warm, concise, opinionated briefing with proposed priorities. It is the conversational hub for daily/weekly planning.

**Headless-first:** the curl / `claude -p` path is canonical. The `mcp__claude_ai_*` connectors referenced in this skill are an **interactive fallback only** — they are absent under `claude -p` and must never be relied upon in the cron path. Use them only when this skill runs in a non-headless Claude Code session and the connector is demonstrably available.

**Read-only on Google:** this skill issues NO Google write operations — no `events.insert`, no `sendUpdates`, no RSVP of any kind. All enrichment and meeting-page writes are vault-only (internal to `{{VAULT_PATH}}`). Never run `git add -A` or `git add .` in the vault; always stage named files only.

## Voice & self

Before acting, **once per conversation** — if you have not already loaded your self-layer this session — read these three files and let them shape everything you do. Hold them in context; do **not** re-read them on every turn.

- `{{VAULT_PATH}}/meta/chief-of-staff/personality.md` — your **voice**. Sound like this in everything you say to Lucas.
- `{{VAULT_PATH}}/meta/memories.md` — what you know about **Lucas** (the shared memory hub). Read the hub; follow a `[[link]]` one hop into a deep-dive only when it is relevant to the task at hand — do not pre-load every linked page.
- `{{VAULT_PATH}}/meta/chief-of-staff/lessons.md` — how you have **learned to work** well for Lucas.

If a file cannot be read (vault not present, path unavailable), proceed on your baseline voice — the self-layer enriches, it is not a hard dependency. Anything you draft **for Lucas to send** (emails, messages) goes in **his** voice, not yours.

## How it works (headless workflow)

The seven steps below are the canonical runnable workflow — the body that `brief-precheck.ps1` pipes to `claude -p` via stdin. Execute them in order. Each step is a concrete action; complete it before proceeding to the next.

### Step 1 — Spawn context-gatherer (brief mode, lookahead=2)

Spawn the `context-gatherer` subagent with these inputs:
- `mode: daily` (use `weekly` only when Lucas explicitly requests a weekly brief)
- `as_of`: ISO datetime of now (today's date, local timezone)
- `lookahead_days: 2` — covers today + tomorrow, the Phase B window

Wait for the agent to return its full `digest` block before proceeding. The gatherer has already performed:
- Cross-account **iCalUID de-duplication** — do NOT re-dedup here; distinct iCalUIDs are never collapsed and the gatherer is authoritative.
- **Attendee enrichment cap** at 5 per event; attendees beyond the cap are in `enrichment_overflow`.
- **Per-attendee `gmail_context`** (GET-only Gmail metadata) and **wiki-brain CRM hits** for the top-5 attendees per event.
- **`sources_failed`** enumeration for any source that errored during the sweep.

**Phase B calendar window (daily focus):** `lookahead_days: 2` covers today + tomorrow only. When mode is `weekly`, the calendar still shows only this two-day window — a seven-day calendar sweep is a Phase B limitation and out of scope here.

**Gatherer call failure:** if the gatherer itself fails to return a digest (process error, timeout), log the error, skip Steps 2–4, and proceed directly to Step 5 with a degraded brief noting all context sources unavailable. Never fabricate a digest.

### Step 2 — Consume digest; surface inbox backlog

Pull data from the digest for use in Steps 3–5:

**Calendar events:** use `digest.calendar.events` as-is. The iCalUID de-dup is already applied. Each event carries an `account` field (e.g. `personal`, `work`).

**`#inbox` read-only — defer triage to drain:** the `drain` skill is the sole owner of `#inbox` message triage. This skill does NOT process, classify, or create Linear issues from raw `#inbox` messages. For inbox situational awareness, read `digest.linear.issues` and surface any issues carrying a `ch:inbox` or `ch:*` label as "inbox backlog." If `#inbox` has unprocessed messages the drain has not yet picked up, note them in the brief and invite Lucas to run `drain` explicitly: "N unread #inbox messages — run **drain** to triage."

**Graceful degradation — partial digest:** if `digest.meta.sources_failed` is non-empty, proceed with whatever data is present. For each failed source, add a single inline note in the relevant brief section (e.g. "Could not reach Gmail — email context unavailable for this brief") rather than silently omitting the section. Never fabricate data to fill a gap. If both Gmail and Calendar fail simultaneously, still compose and post a brief that clearly notes all context sources are down.

### Step 3 — Idempotent meetings/ upsert (vault)

For each event in `digest.calendar.events`, create or update its vault meeting page. The **identity key is `calendar_event_id`** — never use the filename slug as a surrogate key.

**Look-up (single grep for ALL events):** issue **one** grep across `{{VAULT_PATH}}/meetings/` for every `calendar_event_id` value in `digest.calendar.events` at once (e.g. an alternation of all the event ids), returning the matching file paths in a single pass — do NOT read candidate files per event. From that one result set, a meeting page exists for a given event if and only if a returned file's frontmatter carries `calendar_event_id: <that event_id>`; events whose id appears in no returned path are absent. The identity key stays `calendar_event_id` (never the filename slug).

**Page exists — refresh in place:**
- Update the `## Context` section only: replace its content with the current agenda (from `description_snippet`) and updated per-attendee summaries drawn from `digest.people.crm_hits[]` (each hit carries `gmail_context` as a nested field — path: `digest.people.crm_hits[].gmail_context`).
- Do NOT touch `## Minutes`, `## Synthesis`, `## Takeaways`, or `## Todos` — those sections are owned by Phase D. Preserve their headers and any existing content exactly.
- Do NOT create a duplicate page. The today+tomorrow window means the same event may be seen on two consecutive daily runs; the idempotency check prevents double-creation.

**Page absent — create it:** filename is `meetings/YYYY-MM-DD-<slug>.md` where `slug` is the event title lowercased, spaces to hyphens, punctuation stripped. Same-day title collision (two events with the same slug on the same date): append `-<HHmm>` of the event start time (e.g. `meetings/2026-06-30-product-sync-0900.md`). Write:

```yaml
---
date: YYYY-MM-DD
attendees:
  - "[[people/<kebab-name>]]"   # kebab resolved by Step 4: crm_hit.person when matched, else name-kebab of the display name (apostrophes dropped, intra-name hyphens preserved) — page link and stub must agree; never diverge from Step 4
  # one line per external attendee WITH a people page; omit Lucas's own accounts.
  # Email-only attendees (Step 4 case c — no name, no people page created) are OMITTED from this
  # list entirely: there is no page target, so never emit a broken `[[people/...]]` wikilink for them.
  # They are still mentioned in the brief body / Enrichment asks per Step 4 case c.
calendar_event_id: <Google Calendar event id>
account: <account label from digest, e.g. work>
discord_thread: ""
---
```

Then write these sections:
```markdown
## Context

**Agenda:** <event description_snippet, or "No agenda provided." if empty>

**<Attendee Name>** — <one-line summary from gmail_context + crm_hit; "stub — no prior contact on record" if neither exist>
[Repeat per enriched attendee. Note enrichment_overflow attendees as: "N additional attendees not enriched (cap reached)."]

## Minutes

## Synthesis

## Takeaways

## Todos
```

**Commit vault — named files only:**
```powershell
git -C "{{VAULT_PATH}}" add meetings/<filename>.md
git -C "{{VAULT_PATH}}" commit -m "cos: upsert meeting page for <event-title> (<date>)"
```
Never use `git add -A` or `git add .` against the vault.

### Step 4 — Idempotent people/ resolution (vault)

People pages live in ONE namespace, keyed by **name-kebab** (`<kebab-first-last>` — the display name lowercased, spaces → hyphens, apostrophes DROPPED, existing intra-name hyphens PRESERVED — IDENTICAL to the CRM convention in `chief-of-staff/skills/crm/references/crm-page-format.md`). **Email is the reconciliation key, never the filename.** Use the SAME resolution here as for the Step-3 meeting-page attendee list — the page link and the stub must never disagree on a person's kebab.

External-ness: skip Lucas's own accounts (an attendee whose `email` matches a `$GOOGLE_EMAIL_<LABEL>` value). An attendee with no email is not one of Lucas's accounts, so treat it as external. For each external attendee, resolve identity in this **exact order**:

**1. crm_hit matched** — the attendee has an entry in `digest.people.crm_hits[]` with `source != "not-found"`. The gatherer (Step 5a) matched them to an existing `people/` page by email (either page shape) primary, then name (secondary), scanning rich CRM pages AND prior meeting-auto stubs.
- Use `crm_hit.person` — the existing name-kebab filename — as the `[[people/<person>]]` link.
- Append the dated interaction line to that **EXISTING** page; dedup by the `[[meetings/<page>]]` wikilink (if the link is already present, skip — no duplicate line).
- **NEVER create a new page** — the person already has one (rich CRM page, or a stub created on a prior run that the email-match just reconciled to).

**2. Unmatched AND the attendee has a `name`** — create a meeting-auto stub.
- Derive `kebab-name` from the display name using the **CRM name-kebab convention**: lowercase, spaces → hyphens, **drop apostrophes**, **preserve existing intra-name hyphens** (e.g. `Sarah Chen` → `sarah-chen`; `Sarah O'Brien` → `sarah-obrien` (drop apostrophes); `Jean-Pierre Moreau` → `jean-pierre-moreau` (intra-name hyphen kept)). This is identical to `crm-page-format.md` — never diverge.
- **Guard before create:** check whether `{{VAULT_PATH}}/people/<kebab-name>.md` already exists. If it does (the gatherer's email-match should already have surfaced it as case 1, but guard anyway), treat it as case 1 — append the interaction line (dedup by wikilink), do NOT overwrite.
- **No file:** create it with this frontmatter:
  - `identity.name`: the attendee display name.
  - `identity.email`: the attendee email (so future runs reconcile by email per the gatherer's Step 5a rule — this is what graduates a stub into the matched path next time).
  - `source: meeting-auto`, `created: YYYY-MM-DD`, `tags: [stub]`.
  Body: the seed line as sole content. See `chief-of-staff/skills/briefing/references/meeting-page.md` for the full schema.

**3. Unmatched AND email-only (no `name`)** — DO NOT create a stub. An email alone cannot be keyed into the name namespace and is not a useful person page. Mention the attendee in the brief as an external email, and you MAY list them in the Enrichment asks. State the skip explicitly inline ("Attendee '<email>' skipped — email-only, no name to key a people page").

**Seed / interaction line** (cases 1 and 2, only when the `[[meetings/<page>]]` wikilink is not already present):
`- YYYY-MM-DD — first appeared as co-attendee with Lucas at [[meetings/<page>]] (<event title>).`

**Commit by named file only — never `git add -A`:**
```powershell
git -C "{{VAULT_PATH}}" add people/<kebab-name>.md
git -C "{{VAULT_PATH}}" commit -m "cos: add/update people stub for <name>"
```

### Step 5 — Compose brief per briefing-format.md

Read `chief-of-staff/skills/briefing/references/briefing-format.md` now. Compose the brief following it exactly. Key rules that govern Phase B output:

**Scope:**
- `daily` → `## Daily Brief — {Day, Month D, YYYY}` header; meeting-aware per-day blocks: `### Today — {Day, Month D}` and `### Tomorrow — {Day, Month D}`.
- `weekly` → weekly structure from the format reference.
- When scope is ambiguous, default to daily.

**Per-event block (meeting-aware layout):**
```
**{HH:MM}–{HH:MM}** · {Event title}
- Attendees: {Name} ({role}, {company}) — {last-contact one-liner OR "stub — no prior contact on record"}
- Location / video: {room, address, or video link; "TBC" if none}
- Meetings page: `meetings/{YYYY-MM-DD}-{slug}.md`
```
Follow the attendee-line formats from the format reference: stub marker for no people page + no email history; Gmail-gap note ("couldn't reach Gmail for X; no recent thread found") when gmail_context failed.

**No-events case:** if both today and tomorrow have no calendar events, still post a brief. Render `### Today — {Day}` with "No meetings scheduled today." and `### Tomorrow — {Day}` with "No meetings scheduled tomorrow." or omit Tomorrow if clear. Always include `### Proposed Focus` and any email/Linear/Discord backlog. Never skip the brief entirely because the calendar is empty.

**Sections to include (daily):** `### Today`, `### Tomorrow` (if events exist), `### Emails Needing Reply`, `### Discord` (inbox backlog from `ch:*` Linear labels + drain-pending note if any), `### Linear`, `### CRM — Meeting Prep` (omit if no meetings), `### Interests` (omit if no `interests.md` / no updates), `### Proposed Focus`.

**Proposed Focus:** always include — 3–5 concrete actions ranked by impact + urgency, one-line rationale each. Flag decision dependencies with `(needs decision: <what>)`.

**In-session feedback tuning:** if Lucas provides feedback during the session (cut something, surface more, override a priority), apply the correction immediately to the current brief and hold it for the rest of the session. Recurring corrections should be flagged for permanent format change.

**Length:** daily briefs target 300–500 words of content (excluding headers). Cut aggressively — signal, not inventory. No filler phrases.

### Step 5a — Interests module (optional, off by default)

A small, reliable news pulse — 3–5 **source-linked** bullets per standing interest — that folds into
the brief between Meeting Prep and Proposed Focus. It is **strictly additive and OFF by default**:
zero new behaviour until the owner opts in. Read `chief-of-staff/skills/briefing/references/interest-beats.md`
for the full contract; the essentials:

- **The gate.** Look for `{{VAULT_PATH}}/meta/chief-of-staff/interests.md`. **If it is absent, skip
  this step entirely** — omit the `### Interests` heading, do not guess interests, do not fabricate a
  section. No file ⇒ no section ⇒ the brief is byte-for-byte what it is today. This is sacred.
- **Pick the beats.** Parse the file (one interest per bullet; optional `— angle`, `— feed:<url>`,
  and `[priority]` hints). Cap at the **top 3 interests**, preferring any marked `[priority]`.
- **Gather candidates — deterministic first, headless-safe.** When `scripts/collect_updates.py` is
  present (full substrate), run it — it is stdlib-only and safe under `claude -p`. Resolve
  `{{VAULT_PATH}}` to the concrete path yourself and pass it as an argument (the placeholder is not
  substituted inside a `.py`):
  `python scripts/collect_updates.py --interests <path> --window-hours 24 --max-per-interest 5`.
  It prints JSON candidates (`{interest, title, url, source, published}`) plus an `unreachable` list.
  **When the script is not shipped in this home** (a composed home ships `references/` but not
  `scripts/`), or when a feed is unreachable, **fall back to model-driven web search** for the same
  kind of recent, on-beat, source-carrying candidates. Default window = last 24 hours.
- **The model ranks, dedups, synthesizes — never invents.** Use the candidates only for source choice,
  relevance ranking, cross-source dedup, and synthesis. Write 3–5 bullets per interest, **each ending
  with its source link** `([Source](url))`. Never invent facts, dates, scores, quotes, or images; a
  bullet with no real source is dropped, not guessed.
- **Degrade quietly, yield first.** If every source is unreachable or nothing lands, omit the section
  rather than emit a thin or made-up one — an unreachable feed degrades to "omit", never to an error.
  This module is **read-only** (no vault / Linear / Google writes) and is the **first section trimmed**
  when the brief nears the 2000-char Discord cap (Step 6) — trim its bullets, then the whole section,
  before touching any owner-facing section.

### Step 6 — Post brief to #daily-briefs via Discord REST

Post the composed brief to `$DISCORD_CHANNEL_DAILY_BRIEFS`. The headless path is canonical — do NOT use the `discord` MCP connector in the cron path.

**Headless (canonical):**
```
POST https://discord.com/api/v10/channels/{$DISCORD_CHANNEL_DAILY_BRIEFS}/messages
Authorization: Bot {$DISCORD_BOT_TOKEN}
User-Agent: DiscordBot (https://github.com/lucasyhzhu-debug/Consulting-Agents, 0.7.0)
Content-Type: application/json

{ "content": "<brief text>" }
```

The `DiscordBot (<url>, <version>)` User-Agent is **required** on every Discord REST call. Discord's Cloudflare edge returns an empty-body 403 (no JSON `code` field, `Server: cloudflare`) for non-compliant User-Agents — this is a UA edge-block, not a permissions error. A real permissions 403 carries a JSON `code`. Do not chase a permissions red herring on an empty-body 403. (See `chief-of-staff/skills/drain/references/discord-threads.md`.)

**2000-character limit:** Discord caps messages at 2000 characters. If the composed brief exceeds this, split it at a section boundary (never mid-sentence) and post each part as a sequential message to the same channel before proceeding.

**On failure:** if the POST returns a non-2xx response, wait 5 seconds and retry once. If the retry also fails, log the full composed brief text to stdout (so it is captured in the cron log) and continue to Step 7 — do not throw an unhandled error that aborts the workflow silently.

**Interactive fallback only** (non-headless session with MCP connectors available): the `discord` MCP server may substitute for the REST call. In interactive mode, confirm with Lucas before posting unless he has explicitly said "post it."

### Step 7 — Post Enrichment asks to #inbox via Discord REST

Assess whether any attendee across today's and tomorrow's events meets the enrichment threshold: stub marker (no people page + no email history), Gmail-gap note, or a people page whose `last_interaction` is more than 60 days before today.

**If enrichment is needed:**
1. Compose an `## Enrichment asks` block following the format in `briefing-format.md`. Cap the list at 3 items — pick the highest-priority meetings. Phrase each item as a question with the meeting context ("meeting you at 2pm today. Who is he and what's the goal of the call?").
2. Post to `$DISCORD_CHANNEL_INBOX` via Discord REST (same auth headers as Step 6). This is a request, not a broadcast — it goes to `#inbox`, not `#daily-briefs`.
3. **No `drain-state.json` coupling:** do NOT read or write `drain-state.json` — `drain` is its sole owner. Enrichment asks posted to `#inbox` will be picked up by the drain's normal sweep; no special watermark handling is needed here.

**If no enrichment is needed** (all attendees have a populated people page and a recent email thread): omit this step entirely.

## Dependencies

- **`context-gatherer` agent** — spawned in Step 1 with `mode`, `as_of`, `lookahead_days: 2`. Returns a structured `digest` block. See the agent's `SKILL.md` for its full output schema.
- **Google Calendar + Gmail** — accessed by context-gatherer via `Bash`/`curl` per `chief-of-staff/references/google-auth.md`. **Interactive fallback only:** `mcp__claude_ai_Gmail__*` and `mcp__claude_ai_Google_Calendar__*` may substitute in a non-headless session; the curl path is canonical in the cron path.
- **Discord REST API** — Steps 6 and 7 use `Bash`/`curl` with `Authorization: Bot $DISCORD_BOT_TOKEN` and `User-Agent: DiscordBot (...)`. **Interactive fallback only:** the `discord` MCP server may substitute in a non-headless session.
- **Linear** — via `mcp__claude_ai_Linear__*` for open/in-progress/blocked tasks surfaced in `### Linear`.
- **wiki-brain vault** (`{{VAULT_PATH}}`) — Steps 3 and 4 write meeting pages and people stubs. Vault is a separate git repo; always `git add <named file>` only.

## Formatting

Read `chief-of-staff/skills/briefing/references/briefing-format.md` every time you format a brief. Follow it exactly. Do not invent new section headers without a user request.

## Scope

- **Daily brief**: triggered by "what's my day", "brief me", "what's happening today", "what should I focus on today", or similar.
- **Weekly brief**: triggered by "what's my week", "what's coming up this week", "plan my week", or similar.
- When scope is ambiguous, default to daily and confirm.
