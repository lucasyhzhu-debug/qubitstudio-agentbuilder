<!-- CANDIDATE -->

# Capture finalize — reference transcript

Quality-bar reference for the capture skill (DT2). Covers:
- Reconstructing the notes buffer from a Discord thread (bot messages filtered out)
- Resolving the meeting via Priority 1 (thread already wired to meeting page)
- Finalize gate satisfied by Lucas's bare "done" cue
- Writing all four Phase-D sections with correct attribution split
- CRM fan-out: Phase B seed line REPLACED with enriched Phase-D interaction line (three-way dedup REPLACE arm)
- Linear todo creation with meeting sentinel lines and dedup keys
- `capture_status: filed` + Discord thread summary post

Not a runnable fixture — a calibrated human-readable reference.

---

## Initial state

**Meeting page:** `{{VAULT_PATH}}/meetings/2026-06-30-frollie-strategy.md`

```yaml
---
date: 2026-06-30
attendees:
  - "[[people/sarah-chen]]"
  - "[[people/tom-park]]"
calendar_event_id: "abc123frollie"
account: work
discord_thread: "https://discord.com/channels/9876543210987654321/1385000000000000400"
capture_status: open
---
```

**Phase B seed line in `people/sarah-chen.md` (body, written by Phase B briefing fan-out):**

```
- 2026-06-30 — first appeared as co-attendee with Lucas at [[meetings/2026-06-30-frollie-strategy]] (Frollie strategy).
```

**No existing `people/tom-park.md`** — Tom Park is a new contact; no page exists.

**Discord thread `1385000000000000400` messages (chronological):**

| id | author.id | content |
|----|-----------|---------|
| `1385000000000000401` | `285000000000000001` (OWNER_USER_ID) | "okay so we covered three things today. first go-to-market timing — we think Q3 is too early, pushed to Q4" |
| `1385000000000000402` | `285000000000000001` (OWNER_USER_ID) | "second was pricing. Tom wants to anchor at 299 per seat. I said let's look at comp first before we lock in" |
| `1385000000000000403` | `285000000000000001` (OWNER_USER_ID) | "third was hiring. they need a senior PM by August. I offered to loop in my recruiter contact" |
| `1385000000000000404` | `999000000000000001` (BOT_ID) | "Got it, added to your Frollie strategy notes. Say 'done' when you're ready to file." |
| `1385000000000000405` | `285000000000000001` (OWNER_USER_ID) | "done" |

---

## Step 1 — Reconstruct notes buffer

**Bot ID resolution:**

```
GET /users/@me
Authorization: Bot <DISCORD_BOT_TOKEN>
User-Agent: DiscordBot (https://github.com/lucasyhzhu-debug/Consulting-Agents, 0.7.0)
```

Response: `{ "id": "999000000000000001" }` → `DISCORD_BOT_ID = "999000000000000001"`

**Fetch thread messages:**

```
GET /channels/1385000000000000400/messages?limit=100
Authorization: Bot <DISCORD_BOT_TOKEN>
User-Agent: DiscordBot (https://github.com/lucasyhzhu-debug/Consulting-Agents, 0.7.0)
```

**Filter:** exclude message `1385000000000000404` (`author.id == DISCORD_BOT_ID`). Messages `401`, `402`, `403`, `405` pass.

**Chronological notes buffer (after bot-filter):**

1. "okay so we covered three things today. first go-to-market timing — we think Q3 is too early, pushed to Q4"
2. "second was pricing. Tom wants to anchor at 299 per seat. I said let's look at comp first before we lock in"
3. "third was hiring. they need a senior PM by August. I offered to loop in my recruiter contact"
4. "done"

---

## Step 2 — Resolve meeting

**Priority 1 — Thread already wired:** meeting page `2026-06-30-frollie-strategy.md` has `discord_thread` containing thread id `1385000000000000400`. Meeting resolved immediately. No heuristic matching needed.

---

## Step 3 — Finalize gate

| Condition | Met? |
|-----------|------|
| Meeting resolved (Priority 1) | YES |
| Notes buffer non-empty (3 Lucas content messages) | YES |
| Explicit finalize cue (message `405`: "done" from OWNER_USER_ID) | YES |

**Gate open. Proceed to Step 4.**

---

## Step 4 — File

### 4a — Meeting page exists

No creation needed. Page `2026-06-30-frollie-strategy.md` already exists from Phase B.

### 4b — Write Phase-D sections

**Attribution guard check (before writing):**

Every sentence in the proposed `## Minutes` is traceable to a Lucas thread message with transcription/grammar tidying only:
- "Covered three things today." — message 401 (capitalised sentence opener; "okay so" dropped as filler).
- "First, go-to-market timing — we think Q3 is too early; pushed to Q4." — message 401 (capitalised, full-stop, semicolon added; wording unchanged).
- "Second, pricing. Tom wants to anchor at $299 per seat." — message 402 (capitalised; `299` → `$299` for clarity).
- "I said let's look at comp first before we lock in." — message 402 (capitalised; unchanged).
- "Third, hiring — they need a senior PM by August." — message 403 (capitalised, grammar tidy).
- "I offered to loop in my recruiter contact." — message 403 (capitalised; unchanged).

No agent analysis in `## Minutes`. `## Synthesis` contains only agent framing — not lifted from Lucas's words.

**Phase-D sections written to `2026-06-30-frollie-strategy.md`:**

```markdown
## Minutes

Covered three things today. First, go-to-market timing — we think Q3 is too early; pushed to Q4. Second, pricing. Tom wants to anchor at $299 per seat. I said let's look at comp first before we lock in. Third, hiring — they need a senior PM by August. I offered to loop in my recruiter contact.

## Synthesis

*Agent synthesis*

Three decisions in motion from this session. (1) **Go-to-market timing:** Q4 is now the target — Q3 ruled out. Risk: Q4 is tight if the PM hire slips. (2) **Pricing:** no anchor confirmed yet. Lucas's condition is a comp review first; open question is who owns that research and by when. (3) **Hiring:** senior PM needed by August (five weeks out). Lucas's recruiter lead is live but not yet confirmed. The pricing and hiring threads are interdependent — a slip on either could push Q4 launch.

## Takeaways

- Q3 go-to-market ruled out — Q4 is the new target
- Pricing anchor ($299/seat) not confirmed pending comp research
- Senior PM hire needed by August — Lucas to connect recruiter contact

## Todos

- [ ] Research seat-based pricing comps for SaaS PM tools — Lucas (Linear: LAG-51)
- [ ] Connect Tom Park with recruiter contact for senior PM role — Lucas (Linear: LAG-52)
```

**Section order:** `## Minutes` → `## Synthesis` → `## Takeaways` → `## Todos`. Fixed; not reordered.

### 4c — CRM fan-out

**Attendees (external only):** `[[people/sarah-chen]]`, `[[people/tom-park]]`

---

**Sarah Chen (`people/sarah-chen.md`):**

Scan body for `[[meetings/2026-06-30-frollie-strategy]]` — found. Line shape contains `"first appeared as co-attendee"` → **REPLACE arm** (Phase B seed → enriched).

Before:
```
- 2026-06-30 — first appeared as co-attendee with Lucas at [[meetings/2026-06-30-frollie-strategy]] (Frollie strategy).
```

After (REPLACE in place — no append):
```
- 2026-06-30 — met at [[meetings/2026-06-30-frollie-strategy]] (Frollie strategy). Pricing and Q4 go-to-market timing discussed; comp review required before anchor is confirmed.
```

---

**Tom Park (`people/tom-park.md`):**

No existing page → create `meeting-auto` stub:

```yaml
---
identity:
  name: Tom Park
  email: tom@frollie.com
source: meeting-auto
created: 2026-06-30
tags:
  - stub
---
```

Body (enriched interaction line written directly as sole content — no seed line created then replaced in a single Phase D run):

```
- 2026-06-30 — met at [[meetings/2026-06-30-frollie-strategy]] (Frollie strategy). Championing $299/seat pricing anchor; senior PM hire needed by August.
```

---

**Vault commit:**

```powershell
git -C "{{VAULT_PATH}}" add meetings/2026-06-30-frollie-strategy.md people/sarah-chen.md people/tom-park.md
git -C "{{VAULT_PATH}}" commit -m "cos: finalize capture 2026-06-30 frollie-strategy"
```

Named files only — never `git add -A` against the vault.

### 4d — Linear todos

**Todo 1:** "Research seat-based pricing comps for SaaS PM tools"

Normalized: `research seat-based pricing comps for saas pm tools`

Sentinel search — no existing LAG issue with `meeting: meetings/2026-06-30-frollie-strategy` + this normalized title → `issueCreate`:

```graphql
mutation {
  issueCreate(input: {
    title:       "Research seat-based pricing comps for SaaS PM tools"
    description: "meeting: meetings/2026-06-30-frollie-strategy\n\nFrom Frollie strategy session 2026-06-30. Pricing anchor ($299/seat proposed by Tom Park) not confirmed — comp review is the prerequisite before the team agrees to lock in."
    teamId:      "{{LINEAR_TEAM_ID}}"
    projectId:   "{{LINEAR_PROJECT_ID}}"
    labelIds:    ["<meeting-todo-label-id>", "<needs-agent-label-id>"]
    assigneeId:  "<LUCAS_ASSIGNEE_ID>"
  }) { issue { id identifier } }
}
```

**Response:** `{ "identifier": "LAG-51" }`

---

**Todo 2:** "Connect Tom Park with recruiter contact for senior PM role"

Normalized: `connect tom park with recruiter contact for senior pm role`

No existing match → `issueCreate`:

```graphql
mutation {
  issueCreate(input: {
    title:       "Connect Tom Park with recruiter contact for senior PM role"
    description: "meeting: meetings/2026-06-30-frollie-strategy\n\nFrom Frollie strategy session 2026-06-30. Frollie needs a senior PM by August. Lucas offered to loop in his recruiter contact during the session."
    teamId:      "{{LINEAR_TEAM_ID}}"
    projectId:   "{{LINEAR_PROJECT_ID}}"
    labelIds:    ["<meeting-todo-label-id>", "<needs-agent-label-id>"]
    assigneeId:  "<LUCAS_ASSIGNEE_ID>"
  }) { issue { id identifier } }
}
```

**Response:** `{ "identifier": "LAG-52" }`

### 4e — Set `capture_status: filed` and post thread summary

**Patch frontmatter:** `capture_status: filed`

**Discord thread post:**

```
POST /channels/1385000000000000400/messages
Authorization: Bot <DISCORD_BOT_TOKEN>
User-Agent: DiscordBot (https://github.com/lucasyhzhu-debug/Consulting-Agents, 0.7.0)
Content-Type: application/json

{
  "content": "Filed: Frollie strategy (2026-06-30)\n• Minutes: 68 words from your notes\n• CRM: updated 2 people pages (Sarah Chen — enriched, Tom Park — new stub)\n• Linear: 2 todos created (LAG-51, LAG-52)\nReply with any correction to re-open."
}
```

---

## End state

### Meeting page — `meetings/2026-06-30-frollie-strategy.md` (final)

```yaml
---
date: 2026-06-30
attendees:
  - "[[people/sarah-chen]]"
  - "[[people/tom-park]]"
calendar_event_id: "abc123frollie"
account: work
discord_thread: "https://discord.com/channels/9876543210987654321/1385000000000000400"
capture_status: filed
---
```

```markdown
## Minutes

Covered three things today. First, go-to-market timing — we think Q3 is too early; pushed to Q4. Second, pricing. Tom wants to anchor at $299 per seat. I said let's look at comp first before we lock in. Third, hiring — they need a senior PM by August. I offered to loop in my recruiter contact.

## Synthesis

*Agent synthesis*

Three decisions in motion from this session. (1) **Go-to-market timing:** Q4 is now the target — Q3 ruled out. Risk: Q4 is tight if the PM hire slips. (2) **Pricing:** no anchor confirmed yet. Lucas's condition is a comp review first; open question is who owns that research and by when. (3) **Hiring:** senior PM needed by August (five weeks out). Lucas's recruiter lead is live but not yet confirmed. The pricing and hiring threads are interdependent — a slip on either could push Q4 launch.

## Takeaways

- Q3 go-to-market ruled out — Q4 is the new target
- Pricing anchor ($299/seat) not confirmed pending comp research
- Senior PM hire needed by August — Lucas to connect recruiter contact

## Todos

- [ ] Research seat-based pricing comps for SaaS PM tools — Lucas (Linear: LAG-51)
- [ ] Connect Tom Park with recruiter contact for senior PM role — Lucas (Linear: LAG-52)
```

### CRM line — `people/sarah-chen.md` (enriched, Phase B seed REPLACED)

```
- 2026-06-30 — met at [[meetings/2026-06-30-frollie-strategy]] (Frollie strategy). Pricing and Q4 go-to-market timing discussed; comp review required before anchor is confirmed.
```

### CRM line — `people/tom-park.md` (new meeting-auto stub, enriched line as sole body)

```
- 2026-06-30 — met at [[meetings/2026-06-30-frollie-strategy]] (Frollie strategy). Championing $299/seat pricing anchor; senior PM hire needed by August.
```

| Surface | State |
|---------|-------|
| Meeting page | `capture_status: filed`; all four Phase-D sections present in fixed order |
| `people/sarah-chen.md` | Phase B seed line REPLACED with enriched Phase-D interaction line |
| `people/tom-park.md` | New `meeting-auto` stub; enriched interaction line as sole body content |
| Linear LAG-51 | Created: "Research seat-based pricing comps for SaaS PM tools"; sentinel in description |
| Linear LAG-52 | Created: "Connect Tom Park with recruiter contact for senior PM role"; sentinel in description |
| Discord thread `1385000000000000400` | Filed summary posted (4 lines) |
| drain-state.json | Watermarks-only; no capture key added |

---

## Notes on attribution guard

`## Minutes` passes the guard: every sentence is traceable to messages 401–403, tidied for grammar only (capitalisation, full-stops, `299` → `$299`). No sentence is agent framing.

`## Synthesis` is visibly agent-authored via the mandatory `*Agent synthesis*` italic marker. It contains analysis (decisions, risks, open questions) that does not exist in Lucas's words. None of his verbatim phrases appear there.

A `## Minutes` section reading "The meeting covered go-to-market, pricing, and hiring decisions" would be a violation — that is agent synthesis, not Lucas's words.

---

## Notes on CRM dedup (REPLACE arm)

Sarah Chen's page was created by Phase B when the meeting appeared on Lucas's calendar. Phase B wrote a seed line containing `"first appeared as co-attendee"`. DT2 detects the seed shape via the `[[meetings/2026-06-30-frollie-strategy]]` wikilink scan, applies the **REPLACE arm**, and upgrades that single line in place to the enriched Phase-D line. No second line is appended.

Tom Park had no prior `people/` page. DT2 creates a `meeting-auto` stub and writes the enriched line directly as the sole body content — there is no seed line to replace in a single Phase D run.
