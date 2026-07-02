# CANDIDATE — quality bar human-calibrated, not a ratified golden

## Scenario: Single `#inbox` message → Linear issue → thread → mirror → act → done

This transcript walks one complete drain cycle for a single message. It illustrates
the expected behaviour at each of the five drain steps, including the exact mutations,
REST calls, and state transitions. It is a quality-bar reference — not a runnable fixture.

---

### Setup (drain-state.json before this run)

```json
{
  "channels": {
    "1234567890123456789": { "label": "ch:inbox", "watermark": "1385000000000000001" }
  },
  "issues": {}
}
```

---

## Step 1 — Gather context (drain mode)

CoS spawns `context-gatherer` in drain mode.

**context-gatherer returns:**

```
new #inbox messages (channel 1234567890123456789, after watermark 1385000000000000001):
  [
    {
      "id":        "1385000000000000099",
      "author":    "lucas_malostudio",
      "timestamp": "2026-06-28T09:14:22.000Z",
      "content":   "Can you check whether Frollie's Notion workspace has a product roadmap page and, if so, pull the key milestones into a Linear project summary for me?"
    }
  ]

open Linear needs-agent issues: []       (queue empty before this run)
thread replies since lastSeen: n/a       (no tracked issues yet)
```

---

## Step 2 — Triage new `#inbox` message

### 2a — intake classification

CoS passes the message to the `intake` skill.

**intake returns:**

```
classification:  knowledge/research
proposed action: Search Frollie Notion workspace for a roadmap page; if found, extract
                 key milestones and draft a Linear project summary for Lucas to review.
urgency:         normal
```

### 2b — create Linear issue

**GraphQL mutation (curl):**

```graphql
mutation {
  issueCreate(input: {
    title: "Frollie Notion roadmap → Linear summary"
    description: "**Original #inbox message (lucas_malostudio, 2026-06-28T09:14:22Z):**\n\nCan you check whether Frollie's Notion workspace has a product roadmap page and, if so, pull the key milestones into a Linear project summary for me?\n\n---\n**Intake classification:** knowledge/research\n**Proposed action:** Search Frollie Notion workspace for a roadmap page; extract key milestones; draft Linear project summary for Lucas to review."
    teamId:    "{{LINEAR_TEAM_ID}}"
    projectId: "{{LINEAR_PROJECT_ID}}"
    labelIds:  ["<ch:inbox-label-id>", "<needs-agent-label-id>"]
  }) {
    issue { id identifier url }
  }
}
```

**Linear response:**

```json
{
  "data": {
    "issueCreate": {
      "issue": {
        "id":         "a1b2c3d4-0001-0001-0001-000000000001",
        "identifier": "LUC-123",
        "url":        "https://linear.app/lucas-agents/issue/LUC-123/frollie-notion-roadmap-linear-summary"
      }
    }
  }
}
```

### 2c — start Discord thread

**REST call:**

```
POST /channels/1234567890123456789/messages/1385000000000000099/threads
Authorization: Bot <DISCORD_BOT_TOKEN>
Content-Type: application/json

{ "name": "LUC-123 Frollie Notion roadmap", "auto_archive_duration": 10080 }
```

**Discord response (thread channel object):**

```json
{ "id": "1385000000000000200", "name": "LUC-123 Frollie Notion roadmap" }
```

`threadId = 1385000000000000200`

### 2d — post ack into thread

**REST call:**

```
POST /channels/1385000000000000200/messages
Authorization: Bot <DISCORD_BOT_TOKEN>
Content-Type: application/json

{
  "content": "Got it — tracking as **LUC-123**.\nhttps://linear.app/lucas-agents/issue/LUC-123/frollie-notion-roadmap-linear-summary\n\nI'll search the Frollie Notion workspace now and post back here when I have the milestone list."
}
```

### 2e — patch issue description with thread URL

**GraphQL mutation:**

```graphql
mutation {
  issueUpdate(
    id: "a1b2c3d4-0001-0001-0001-000000000001"
    input: {
      description: "**Original #inbox message (lucas_malostudio, 2026-06-28T09:14:22Z):**\n\nCan you check whether Frollie's Notion workspace has a product roadmap page and, if so, pull the key milestones into a Linear project summary for me?\n\n---\n**Intake classification:** knowledge/research\n**Proposed action:** Search Frollie Notion workspace; extract key milestones; draft Linear project summary.\n\n---\n**Discord thread:** https://discord.com/channels/9876543210987654321/1385000000000000200"
    }
  ) { success }
}
```

**State (in-memory, not written yet):**

```
channel watermark advanced: 1385000000000000099
issues map added: {
  "a1b2c3d4-0001-0001-0001-000000000001": {
    "threadId": "1385000000000000200",
    "lastSeen": "0",
    "lastActed": "0"
  }
}
```

---

## Step 3 — Mirror thread replies

**REST call (fetch replies since lastSeen=0):**

```
GET /channels/1385000000000000200/messages?after=0&limit=100
Authorization: Bot <DISCORD_BOT_TOKEN>
```

**Discord response:**

```json
[
  {
    "id":      "1385000000000000201",
    "author":  { "username": "lucas_malostudio" },
    "content": "Also check if there's a separate 'Q3 goals' page — grab that too if it exists."
  }
]
```

**Mirror to Linear (commentCreate):**

```graphql
mutation {
  commentCreate(input: {
    issueId: "a1b2c3d4-0001-0001-0001-000000000001"
    body:    "**[Discord reply — lucas_malostudio]** Also check if there's a separate 'Q3 goals' page — grab that too if it exists."
  }) { comment { id } }
}
```

**Linear response:**

```json
{ "data": { "commentCreate": { "comment": { "id": "cmt-0001" } } } }
```

**State (in-memory):** `lastSeen` for this issue advances to `1385000000000000201`.

---

## Step 4 — Act on `needs-agent` issues

LUC-123 carries `needs-agent`. CoS fetches full issue detail + comments.

**Routing decision:** knowledge/research → `wiki-brain:ingest` skill (search Notion, surface milestones).

**wiki-brain:ingest returns:**

```
Found page: "Frollie Product Roadmap" (Notion ID: abc123)
  Key milestones:
  - Q2 2026: Beta launch — consumer iOS app
  - Q3 2026: B2B pilot (3 anchor clients)
  - Q4 2026: Monetisation v1 (subscription + referral)
  - Q1 2027: Series A raise

Found page: "Q3 Goals" (Notion ID: def456)
  Q3 OKR headline: "Sign 3 paying B2B clients and hit 1 000 MAU"
  Key results: client pipeline (6 prospects), MAU tracking dashboard live by July 15.
```

### 4a — post result as Linear comment

**GraphQL mutation:**

```graphql
mutation {
  commentCreate(input: {
    issueId: "a1b2c3d4-0001-0001-0001-000000000001"
    body:    "**Frollie Notion roadmap — key milestones**\n\n| Milestone | Quarter |\n|---|---|\n| Beta launch — consumer iOS app | Q2 2026 |\n| B2B pilot (3 anchor clients) | Q3 2026 |\n| Monetisation v1 (subscription + referral) | Q4 2026 |\n| Series A raise | Q1 2027 |\n\n**Q3 Goals (separate page)**\n> OKR headline: Sign 3 paying B2B clients and hit 1 000 MAU\n> Key results: 6-prospect client pipeline; MAU dashboard live by Jul 15.\n\n→ Marking **done** — let me know if you want this turned into a Linear project plan."
  }) { comment { id } }
}
```

**Linear response:** `{ "data": { "commentCreate": { "comment": { "id": "cmt-0002" } } } }`

### 4b — post result into Discord thread

**REST call:**

```
POST /channels/1385000000000000200/messages
Authorization: Bot <DISCORD_BOT_TOKEN>
Content-Type: application/json

{
  "content": "Done — found both pages.\n\n**Roadmap milestones:** Q2 iOS beta → Q3 B2B pilot → Q4 monetisation v1 → Q1 2027 Series A.\n**Q3 goal:** 3 paying B2B clients + 1 000 MAU (pipeline: 6 prospects; MAU dashboard Jul 15).\n\nFull breakdown in LUC-123 comments. Want me to build a Linear project plan from this?"
}
```

### 4c — move lifecycle: `needs-agent` → `done`

Fetch current labelIds for LUC-123: `["<ch:inbox-label-id>", "<needs-agent-label-id>"]`

**GraphQL mutation:**

```graphql
mutation {
  issueUpdate(
    id: "a1b2c3d4-0001-0001-0001-000000000001"
    input: { labelIds: ["<ch:inbox-label-id>", "<done-label-id>"] }
  ) { success }
}
```

**State (in-memory):** `lastActed` for this issue advances to `cmt-0002`.

---

## Step 5 — Persist drain-state.json

CoS writes the updated state:

```json
{
  "channels": {
    "1234567890123456789": { "label": "ch:inbox", "watermark": "1385000000000000099" }
  },
  "issues": {
    "a1b2c3d4-0001-0001-0001-000000000001": {
      "threadId": "1385000000000000200",
      "lastSeen":   "1385000000000000201",
      "lastActed":  "cmt-0002"
    }
  }
}
```

Written to: `{{VAULT_PATH}}\meta\chief-of-staff\drain-state.json`

---

## End state summary

| Surface | State |
|---|---|
| Linear LUC-123 | Labels: `ch:inbox` + `done`; description has thread URL; 2 comments (mirror + result) |
| Discord thread `1385000000000000200` | Ack + result posted; Lucas's follow-up question mirrored to Linear |
| drain-state.json | Channel watermark advanced; issue tracked with `lastSeen` + `lastActed` |

---

## Notes on `needs-lucas` path (not illustrated above)

If the action had required Lucas's approval (e.g., "draft a reply email to the Frollie CEO"),
Step 4c would instead swap `needs-agent` → `needs-lucas` and the result comment would read:
> "Drafted — parked at needs-lucas. Approve + I'll queue the send."
The issue stays open in the queue; on the next drain it is skipped (no `needs-agent` label)
until Lucas moves it back or closes it.
