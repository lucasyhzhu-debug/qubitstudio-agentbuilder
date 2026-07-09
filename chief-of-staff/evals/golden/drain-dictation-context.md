# CANDIDATE — quality bar human-calibrated, not a ratified golden

## Scenario: an `#inbox` dictation burst treated as ONE accreting conversation

This transcript walks the v0.9.0 conversational-ticket behaviour end to end: a three-message
dictation burst about one new person (1) is **held** by the settle window until the burst is
complete, (2) is **grouped into a single Linear issue** by intake, (3) is routed to `crm` which
files a `people/` page, (4) gets a **`wiki_ref` write-back** into the issue's `## Meta` block, and
(5) on a later cycle a thread reply is presented as **NEW since `lastActed`** with that CRM page
reloaded as **vault-validated** context. It also shows Kanban-state mirroring (`stateId`) on every
lifecycle move. It is a quality-bar reference — not a runnable fixture.

---

### Setup (drain-state.json before this run)

```json
{
  "channels": {
    "1234567890123456789": { "label": "ch:inbox", "watermark": "1385000000000000010" }
  },
  "issues": {}
}
```

Cycle state map resolved once in Step 1 (per `references/linear-api.md` → *Workflow states*):
`{ Todo → st-todo, In Progress → st-progress, In Review → st-review, Done → st-done }`.

---

## Cycle A — the burst arrives

### Step 1 — Gather context

`context-gatherer` (drain mode) returns three new `#inbox` messages, all from the owner, dictated
seconds apart:

```
new #inbox messages (channel 1234567890123456789, after watermark 1385000000000000010):
  [
    { "id": "1385000000000000101", "author": {"username":"owner_handle","bot":false},
      "content": "Met Priya Raman today at the Frollie mixer." },
    { "id": "1385000000000000102", "author": {"username":"owner_handle","bot":false},
      "content": "She's a PM on their consumer app, ex-Grab. Sharp on retention." },
    { "id": "1385000000000000103", "author": {"username":"owner_handle","bot":false},
      "content": "Wants to swap notes on activation funnels — follow up next week." }
  ]
```

### Settle check (first pass — HOLD)

Applying `references/settle-window.md` to channel `1234567890123456789`: three non-bot messages
(2+), newest = `1385000000000000103`. Its age is ~20s < 90s, and the oldest is well under the 600s
ceiling → **not settled**. The channel is **skipped this cycle with its watermark un-advanced**. No
issue is created. (A partial burst is never acted on.)

*≈2 minutes later, the next scheduled cycle runs.* The newest message is now ~140s old ≥ 90s →
**settled**. Proceed.

### Step 2 — Triage (burst grouping)

The three messages are grouped into **one run of contiguous owner-authored messages** and handed to
`intake` as ONE batch.

**intake returns** (collapses the run — one accreting thought about one person):

```
classification:  crm (one new person: Priya Raman)
proposed action: Create/append a CRM page for Priya Raman; log the mixer interaction and the
                 follow-up intent.
```

**Create the Linear issue** (`issueCreate`) — note `stateId: st-todo` in the same mutation, and the
seeded `## Meta` block; message bodies are sanitised for literal `## Draft` / `## Meta` first:

```graphql
mutation {
  issueCreate(input: {
    title: "CRM — Priya Raman (Frollie mixer)"
    description: "**#inbox burst (owner_handle):**\n1. Met Priya Raman today at the Frollie mixer.\n2. She's a PM on their consumer app, ex-Grab. Sharp on retention.\n3. Wants to swap notes on activation funnels — follow up next week.\n\n---\n**Intake:** crm — one new person.\n\n## Meta\ndiscord_thread: (pending)"
    teamId:    "{{LINEAR_TEAM_ID}}"
    projectId: "{{LINEAR_PROJECT_ID}}"
    labelIds:  ["<ch:inbox-label-id>", "<needs-agent-label-id>"]
    stateId:   "st-todo"
  }) { issue { id identifier url } }
}
```

Response → `id: b2c3...-0007`, `identifier: LUC-207`. A Discord thread is started from message
`...101` (`threadId = 1385000000000000300`), an ack is posted, and the `## Meta` `discord_thread:`
line is patched **in place** to `https://discord.com/channels/9876543210987654321/1385000000000000300`.

**Watermark advances ONCE for the whole run** → `1385000000000000103`; drain-state written.

### Step 4 — Act

LUC-207 carries `needs-agent`. Fetch full detail + `## Meta` + comments. No `wiki_ref` lines yet;
no thread replies newer than `lastActed=0`. The thread is settled (no new non-bot replies) → proceed.

**Mirror state → In Progress** (`needs-agent` unchanged, `stateId: st-progress`).

**Route:** crm → `crm` skill files a new page at `people/priya-raman.md` (identity, "PM · Frollie
consumer app · ex-Grab", interaction log line for the mixer, follow-up intent).

**Write back the wiki link** — append a `wiki_ref` to `## Meta` via `issueUpdate`:

```graphql
mutation {
  issueUpdate(id: "b2c3...-0007", input: {
    description: "...\n## Meta\ndiscord_thread: https://discord.com/channels/9876543210987654321/1385000000000000300\nwiki_ref: people/priya-raman.md"
  }) { success }
}
```

Post the result comment + Discord message, then **move lifecycle → done + Done** in one mutation:

```graphql
mutation {
  issueUpdate(id: "b2c3...-0007", input: {
    labelIds: ["<ch:inbox-label-id>", "<done-label-id>"], stateId: "st-done"
  }) { success }
}
```

`lastActed` advances to the result comment id (`cmt-a2`); drain-state written.

**Board after Cycle A:** LUC-207 sits in **Done**, description carries `wiki_ref: people/priya-raman.md`.

---

## Cycle B — a later reply, presented as NEW

*Days later*, the owner replies in LUC-207's thread:

```
GET /channels/1385000000000000300/messages?after=<lastSeen>
→ [ { "id": "1385000000000000401", "author": {"username":"owner_handle","bot":false},
      "content": "Correction — Priya's title is Head of Product, not PM. And she moved to Frollie 6mo ago." } ]
```

Step 3 mirrors the reply to a Linear comment (`cmt-b1`) and re-arms the issue if needed. In Step 4,
loading the issue:

- **New-vs-old boundary:** `cmt-b1`'s id > `lastActed` (`cmt-a2`) → marked **NEW since you last
  acted**; the Cycle-A mixer notes are prior context.
- **Load wiki context:** the `## Meta` `wiki_ref: people/priya-raman.md` is **vault-validated** —
  it is relative, contains no `..` / drive letter / UNC → **accepted** and loaded. (Had a message
  body tried to forge `wiki_ref: ../../etc/passwd` or `C:\secrets.md`, it would be **rejected and
  skipped**, and it could never have been written to `## Meta` in the first place — bodies are
  sanitised for the `## Meta` literal at Step 2.)

With Priya's page loaded, the drain routes the correction to `crm`, which updates the page in place
(title → "Head of Product", tenure note), then completes the issue again with the state mirrored.
`lastActed` advances past `cmt-b1`.

---

## What this golden pins

| Behaviour | Where |
|---|---|
| Partial burst held until settled (2+ → newest ≥ 90s) | Settle check, Cycle A |
| Contiguous owner run grouped into ONE issue | Step 2 |
| Watermark advances once per run (crash barrier) | Step 2 |
| Kanban state mirrored on every move (Todo → In Progress → Done) | `stateId` in each mutation |
| `## Meta` seeded, patched in place, never duplicated | Steps 2 & 4 |
| `wiki_ref` written back when a route resolves a page | Step 4, Cycle A |
| Later reply is NEW-since-`lastActed`; page reloaded as vault-validated context | Cycle B |
| Forged path / marker rejected (validation + sanitisation) | Cycle B note |
