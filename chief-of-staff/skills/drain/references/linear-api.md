# Linear API (GraphQL) — drain helpers

Endpoint: `https://api.linear.app/graphql` · Header: `Authorization: <LINEAR_API_KEY>` (no "Bearer").
Team `{{LINEAR_TEAM_ID}}` · Project `{{LINEAR_PROJECT_ID}}`.

## Find or create a label
`<ch:label>` is the processed message's channel label — `drain-state.channels[channelId].label` (e.g. `ch:inbox`), never hardcoded.
query: `{ issueLabels(filter:{name:{eq:"<ch:label>"}}){ nodes{ id name } } }`
mutation: `mutation{ issueLabelCreate(input:{name:"<ch:label>", teamId:"<team>"}){ issueLabel{ id } } }`

## Create an issue
`mutation{ issueCreate(input:{ title:"<t>", description:"<md>", teamId:"<team>", projectId:"<proj>", labelIds:["<chLabel>","<needsAgentLabel>"], stateId:"<todoStateId>" }){ issue{ id identifier url } } }`
Set `stateId` to the **Todo** state (see *Workflow states* below) in the **same** mutation — a freshly triaged issue belongs in Todo, never the board's Backlog.

## Add a comment
`mutation{ commentCreate(input:{ issueId:"<id>", body:"<md>" }){ comment{ id } } }`

## List actionable issues (needs-agent in the project) + their comments
`{ issues(filter:{ project:{id:{eq:"<proj>"}}, labels:{name:{in:["needs-agent"]}} }){ nodes{ id identifier title description labels{nodes{name}} comments{nodes{ id body createdAt user{name} }} } } }`

## Move lifecycle (swap labels **and** mirror the Kanban state) — fetch current labelIds, then:
`mutation{ issueUpdate(id:"<id>", input:{ labelIds:[<new set>], stateId:"<stateId>" }){ success } }`
The label and the workflow `stateId` move **together in one mutation** — never a second call. See *Workflow states* for which state pairs with which lifecycle label.

## Workflow states (Kanban mirroring)

The drain tracks lifecycle with labels (`needs-agent` / `needs-owner` / `done`) **and** mirrors the
board column via the issue's workflow `stateId`, so the Linear board shows what the agent is doing:

| Lifecycle moment | Label | Kanban state |
| --- | --- | --- |
| Triage creates the issue (queued for agent) | `needs-agent` | **Todo** |
| Step 4 starts acting on an issue | `needs-agent` | **In Progress** |
| Parked for the owner (proposal or blocker) | `needs-owner` | **In Review** |
| Re-armed (thread reply, or Step 3a confirm flip) | `needs-agent` | **Todo** |
| Completed | `done` | **Done** |

**Resolve state ids at runtime — never hardcode UUIDs.** Workflow-state ids are workspace-specific,
so fetch them once per cycle and map by name/type (they are not stored as placeholders):

`{ team(id:"{{LINEAR_TEAM_ID}}"){ states{ nodes{ id name type } } } }`

Map: **Todo** = the `unstarted` state named `Todo` · **In Progress** = the `started` state named
`In Progress` · **In Review** = the `started` state named `In Review` (fall back to any `started`
review state; if the workspace has none, reuse In Progress) · **Done** = the `completed` state named
`Done`. If an `issueUpdate` returns a state error, re-fetch with the query above and retry. Hold the
resolved `{name → id}` map in memory for the cycle; do not persist workspace ids into this file.
