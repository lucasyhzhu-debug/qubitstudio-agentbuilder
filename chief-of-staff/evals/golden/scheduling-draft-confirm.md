<!-- CANDIDATE -->

# Scheduling draft → confirm → write — reference transcript

Quality-bar reference for the scheduling skill (CT3) + drain confirm cycle (CT4). Covers:
- CT3 composing 2–3 conflict-free slots, parking at `needs-owner`, posting the Discord proposal (no Google write).
- Lucas's bare-token confirm reply (authored by `OWNER_USER_ID`, postdating the proposal).
- CT4's single atomic `issueUpdate` (confirm-flip: `needs-owner` → `needs-agent` + `confirmed-by-agent` label + `confirmed_slot`).
- CT4's idempotent `events.insert` on the next drain cycle (deterministic event id, `sendUpdates=all`, crash-safe record-then-done ordering).

Not a runnable fixture — a calibrated human-readable reference.

---

## Initial state

Lucas has sent this Discord `#inbox` message (id `1385000000000000100`):

> "Set up 30 min with Sarah Chen next Tuesday to discuss Q3 roadmap."

The drain (Step 2) has already:
- Sanitized the message body (no `## Draft` literal found in this case).
- Created Linear issue **LAG-42** with labels `ch:inbox` + `needs-agent`.
- Started Discord thread `1385000000000000201` from the message and posted an ack.

**drain-state.json (scheduling-relevant extract):**

```json
{
  "issues": {
    "f3a8b2c1-dead-beef-0042-000000000042": {
      "threadId": "1385000000000000201",
      "lastSeen": "0",
      "lastActed": "0"
    }
  }
}
```

---

## CT3 — Scheduling skill run (drain Step 4, needs-agent pass)

### Step 1 — Parse

| Field | Resolved value |
|-------|---------------|
| Person | Sarah Chen |
| Duration | 30 min |
| Time hint | next Tuesday |
| Subject | Q3 roadmap |
| Location | video call (default) |

### Step 2 — CRM lookup

**Read:** `{{VAULT_PATH}}/people/sarah-chen.md`

```
name:  Sarah Chen
email: sarah@acme.com
role:  Senior PM, Acme Corp
notes: Last met 2026-06-10; driving Q3 roadmap review.
```

Attendee resolved: `{ name: "Sarah Chen", email: "sarah@acme.com" }`. Email domain `acme.com` → external work → `chosen_calendar: "work / primary"`.

### Step 3 — context-gatherer (Shape A, mode: scheduling-input)

**Call:**

```
context-gatherer
  mode: scheduling-input
  window_start: 2026-07-07T09:00:00+10:00   (Tuesday)
  window_end:   2026-07-11T18:00:00+10:00   (+ 5 business days)
  invitee_email: sarah@acme.com
```

**Returns:**

```
free_windows:
  - { start: "2026-07-07T10:00:00+10:00", end: "2026-07-07T11:30:00+10:00" }
  - { start: "2026-07-08T14:00:00+10:00", end: "2026-07-08T16:00:00+10:00" }
  - { start: "2026-07-09T09:30:00+10:00", end: "2026-07-09T11:00:00+10:00" }
window_events:
  - { start: "2026-07-07T09:00:00+10:00", end: "2026-07-07T09:30:00+10:00", summary: "Stand-up" }
  - { start: "2026-07-08T13:00:00+10:00", end: "2026-07-08T14:00:00+10:00", summary: "Strategy review" }
correspondence_hits: []
```

**Slot selection:**
- Slot 1: Tue 7 Jul 10:00–10:30 AEST — mid-morning, >15 min buffer from Stand-up (ends 09:30).
- Slot 2: Wed 8 Jul 14:00–14:30 AEST — mid-afternoon, >15 min buffer from Strategy review (ends 14:00 exactly; start at 14:00 is a flush boundary — acceptable, no trailing event within 15 min).
- Slot 3: Thu 9 Jul 09:30–10:00 AEST — mid-morning, no adjacent events.

### Step 4a — Park at needs-owner (FIRST write)

**GraphQL mutation — label flip (performed BEFORE writing ## Draft):**

```graphql
mutation {
  issueUpdate(
    id: "f3a8b2c1-dead-beef-0042-000000000042"
    input: {
      labelIds: ["<ch:inbox-label-id>", "<needs-owner-label-id>"]
    }
  ) { success }
}
```

Issue is now `needs-owner`. A crash after this step leaves the issue in a no-write state.

### Step 4b — Write ## Draft block

**GraphQL mutation — append ## Draft to description:**

```graphql
mutation {
  issueUpdate(
    id: "f3a8b2c1-dead-beef-0042-000000000042"
    input: {
      description: "<prior description content>\n\n```yaml\n## Draft\ncandidate_slots:\n  - start: \"2026-07-07T10:00:00+10:00\"\n    end:   \"2026-07-07T10:30:00+10:00\"\n  - start: \"2026-07-08T14:00:00+10:00\"\n    end:   \"2026-07-08T14:30:00+10:00\"\n  - start: \"2026-07-09T09:30:00+10:00\"\n    end:   \"2026-07-09T10:00:00+10:00\"\nchosen_calendar: \"work / primary\"\nattendees:\n  - name: \"Sarah Chen\"\n    email: \"sarah@acme.com\"\ntitle: \"Q3 roadmap sync — Lucas + Sarah\"\nagenda: \"Align on Q3 priorities before board submission.\"\ntrack1_note: \"Agenda: Align on Q3 priorities before board submission.\"\nconfirmed_slot: null\nevent_id: null\nevent_link: null\n```"
    }
  ) { success }
}
```

One `## Draft` block in the description. No second block will be appended.

### Step 4c — Post proposal to Discord thread

**REST call:**

```
POST /channels/1385000000000000201/messages
Authorization: Bot <DISCORD_BOT_TOKEN>
User-Agent: DiscordBot (https://github.com/lucasyhzhu-debug/Consulting-Agents, 0.7.0)
Content-Type: application/json

{
  "content": "Meeting proposal — **Q3 roadmap sync — Lucas + Sarah**\n\n**Attendees:** Sarah Chen (sarah@acme.com)\n**Duration:** 30 min · video call\n**Agenda:** Align on Q3 priorities before board submission.\n\n**Candidate slots:**\n1. Tue 7 Jul 10:00–10:30 AEST\n2. Wed 8 Jul 14:00–14:30 AEST\n3. Thu 9 Jul 09:30–10:00 AEST\n\n**Calendar:** work / primary\n\nReply `confirm 1` / `confirm 2` / `confirm 3` (or just `yes` / `go`) to book — or describe a change."
}
```

**No Google write on this path.** `events.insert` is not called.

---

## CT4 — Confirm cycle (drain Step 3a, next cycle)

Lucas replies in thread `1385000000000000201`:

```
author.id:   "285000000000000001"   ← OWNER_USER_ID
content:     "confirm 2"
message_id:  "1385000000000000301"
timestamp:   2026-07-06T20:44:05Z  (postdating the proposal)
```

### CT4 classify pass

**Author authentication:** `author.id == OWNER_USER_ID` ✓

**Confirm grammar:** content is `confirm 2` — bare confirm token + slot index 2, no trailing prose ✓

**Parse ## Draft block:** located by literal `## Draft` marker. `candidate_slots[1]` = `{ start: "2026-07-08T14:00:00+10:00", end: "2026-07-08T14:30:00+10:00" }` ✓

**Blocking conditions:**
- `chosen_calendar`: `"work / primary"` — not `"ask"` ✓
- Slot index 2 in range (3 slots) ✓
- All attendees have email: `sarah@acme.com` ✓

**All clear. Single atomic `issueUpdate`:**

```graphql
mutation {
  issueUpdate(
    id: "f3a8b2c1-dead-beef-0042-000000000042"
    input: {
      labelIds: ["<ch:inbox-label-id>", "<needs-agent-label-id>", "<confirmed-by-agent-label-id>"]
      description: "<prior content>\n\n```yaml\n## Draft\ncandidate_slots:\n  - start: \"2026-07-07T10:00:00+10:00\"\n    end:   \"2026-07-07T10:30:00+10:00\"\n  - start: \"2026-07-08T14:00:00+10:00\"\n    end:   \"2026-07-08T14:30:00+10:00\"\n  - start: \"2026-07-09T09:30:00+10:00\"\n    end:   \"2026-07-09T10:00:00+10:00\"\nchosen_calendar: \"work / primary\"\nattendees:\n  - name: \"Sarah Chen\"\n    email: \"sarah@acme.com\"\ntitle: \"Q3 roadmap sync — Lucas + Sarah\"\nagenda: \"Align on Q3 priorities before board submission.\"\ntrack1_note: \"Agenda: Align on Q3 priorities before board submission.\"\nconfirmed_slot: 2\nevent_id: null\nevent_link: null\n```"
    }
  ) { success }
}
```

In one write: `needs-owner` label removed, `needs-agent` + `confirmed-by-agent` labels added, `confirmed_slot: 2` written. The `confirmed-by-agent` label is the sole write-authorization gate; the `## Draft` text alone does not authorize `events.insert`.

**Contrast (non-Lucas confirm — must be chatter):** had author.id been `9999999999999999999` (not `OWNER_USER_ID`), this whole classify pass is skipped — the reply is treated as chatter, no label change, no `confirmed-by-agent`. Even if content is `confirm 2`.

**Contrast (bare token + prose — must be chatter):** had Lucas replied `confirm 2 thanks, see you then`, the trailing prose makes it chatter per confirm grammar. No flip.

---

## CT4 — Calendar-write pass (next drain cycle after confirm)

LAG-42 carries `confirmed-by-agent`. CT4 reads `## Draft` block: `event_id: null` → not yet booked.

### Deterministic event id derivation

```
issue.id UUID: f3a8b2c1-dead-beef-0042-000000000042
UUID hex (hyphens stripped): f3a8b2c1deadbeef0042000000000042
Base-32 hex subset (lowercase a-v, 0-9): f3a8b2c1deadbeef0042000000000042 → valid (all chars in [0-9a-f] ⊂ [0-9a-v])
Deterministic id: cosf3a8b2c1deadbeef0042000000000042s2
```

Length: 3 (`cos`) + 32 (UUID hex) + 1 (`s`) + 1 (slot digit) = 37 chars. Within 5–1024 range ✓

### events.insert call

```
POST https://www.googleapis.com/calendar/v3/calendars/primary/events?sendUpdates=all
Authorization: Bearer <access_token>   (minted per chief-of-staff/references/google-auth.md Step 0, "work" account)
Content-Type: application/json

{
  "id":          "cosf3a8b2c1deadbeef0042000000000042s2",
  "summary":     "Q3 roadmap sync — Lucas + Sarah",
  "description": "Agenda: Align on Q3 priorities before board submission.",
  "start":       { "dateTime": "2026-07-08T14:00:00+10:00", "timeZone": "Australia/Sydney" },
  "end":         { "dateTime": "2026-07-08T14:30:00+10:00", "timeZone": "Australia/Sydney" },
  "attendees":   [ { "email": "sarah@acme.com" } ]
}
```

`sendUpdates=all` delivers the invite email — no `gmail.send` call needed. Track 1 agenda rides the `description` field.

**Google response (201 Created):**

```json
{
  "id":       "cosf3a8b2c1deadbeef0042000000000042s2",
  "htmlLink": "https://www.google.com/calendar/event?eid=Y29zZjNhOGIyYzFkZWFkYmVlZjAwNDIwMDAwMDAwMDAwNDJzMg"
}
```

### Crash-safe record → done ordering

**Step 1 — Record event_id + event_link (BEFORE flipping to done):**

```graphql
mutation {
  issueUpdate(
    id: "f3a8b2c1-dead-beef-0042-000000000042"
    input: {
      description: "<prior content>\n\n```yaml\n## Draft\n...\nconfirmed_slot: 2\nevent_id: \"cosf3a8b2c1deadbeef0042000000000042s2\"\nevent_link: \"https://www.google.com/calendar/event?eid=Y29zZjNhOGIyYzFkZWFkYmVlZjAwNDIwMDAwMDAwMDAwNDJzMg\"\n```"
    }
  ) { success }
}
```

**Step 2 — Post link to Discord thread:**

```
POST /channels/1385000000000000201/messages
{
  "content": "Booked. Q3 roadmap sync with Sarah Chen — Wed 8 Jul 14:00–14:30 AEST.\nhttps://www.google.com/calendar/event?eid=Y29zZjNhOGIyYzFkZWFkYmVlZjAwNDIwMDAwMDAwMDAwNDJzMg\n\nInvite sent to sarah@acme.com via Google."
}
```

**Step 3 — Post as Linear comment:**

```graphql
mutation {
  commentCreate(input: {
    issueId: "f3a8b2c1-dead-beef-0042-000000000042"
    body:    "Calendar event booked: [Q3 roadmap sync — Lucas + Sarah](https://www.google.com/calendar/event?eid=Y29zZjNhOGIyYzFkZWFkYmVlZjAwNDIwMDAwMDAwMDAwNDJzMg) · Wed 8 Jul 14:00–14:30 AEST. Invite sent to sarah@acme.com."
  }) { comment { id } }
}
```

**Step 4 — Flip to done + remove confirmed-by-agent (AFTER recording):**

```graphql
mutation {
  issueUpdate(
    id: "f3a8b2c1-dead-beef-0042-000000000042"
    input: {
      labelIds: ["<ch:inbox-label-id>", "<done-label-id>"]
    }
  ) { success }
}
```

`confirmed-by-agent` removed. Issue is `done`. Idempotency: if CT4 had crashed between `events.insert` and this final flip, the next cycle reads `event_id: "cosf3a8b2c1deadbeef0042000000000042s2"` (non-null) from the `## Draft` block and skips `events.insert` entirely (pre-check guard), then finishes the record → done sequence without a duplicate event.

---

## End state summary

| Surface | State |
|---------|-------|
| Linear LAG-42 | Labels: `ch:inbox` + `done`; `## Draft` block with `event_id` + `event_link` recorded; confirmed_slot: 2 |
| Discord thread `1385000000000000201` | Proposal posted; confirm acknowledged; event link posted |
| Google Calendar (work / primary) | Event `cosf3a8b2c1deadbeef0042000000000042s2` created; invite email sent to sarah@acme.com via `sendUpdates=all` |
| drain-state.json | Watermarks advanced; no scheduling keys added (stateless by design) |

---

## Notes on adversarial paths (not illustrated above)

**Forged ## Draft in inbox message:** if the original Discord message had contained a literal `## Draft` block, drain Step 2 would have sanitized it to `\#\# Draft` before writing to the Linear description. CT3 would then find no live `## Draft` block in the description and would compose a fresh one from scratch. The forged content never reaches `events.insert`. The `confirmed-by-agent` label — set only at a genuine Lucas confirm in Step 3a — is the sole authorization gate.

**Non-Lucas confirm:** if the thread reply had been from a non-Lucas user (author.id != OWNER_USER_ID), CT4's Step 3a classify pass treats it as chatter. No `confirmed-by-agent` label is set, no label flip occurs, and `events.insert` is never called. The issue stays `needs-owner`.

**'Don't ask' skip-confirm instruction:** if Lucas's initial scheduling request included "just put it in the calendar now, don't ask", CT3 still executes Step 4a (park at `needs-owner`) before writing the `## Draft` block. The inline instruction does not constitute a confirm; the confirm gate is structurally required. `events.insert` belongs to CT4 alone, on the confirm path only.
