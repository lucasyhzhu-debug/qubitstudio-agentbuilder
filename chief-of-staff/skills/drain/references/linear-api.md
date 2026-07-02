# Linear API (GraphQL) — drain helpers

Endpoint: `https://api.linear.app/graphql` · Header: `Authorization: <LINEAR_API_KEY>` (no "Bearer").
Team `{{LINEAR_TEAM_ID}}` · Project `{{LINEAR_PROJECT_ID}}`.

## Find or create a label
`<ch:label>` is the processed message's channel label — `drain-state.channels[channelId].label` (e.g. `ch:inbox`), never hardcoded.
query: `{ issueLabels(filter:{name:{eq:"<ch:label>"}}){ nodes{ id name } } }`
mutation: `mutation{ issueLabelCreate(input:{name:"<ch:label>", teamId:"<team>"}){ issueLabel{ id } } }`

## Create an issue
`mutation{ issueCreate(input:{ title:"<t>", description:"<md>", teamId:"<team>", projectId:"<proj>", labelIds:["<chLabel>","<needsAgentLabel>"] }){ issue{ id identifier url } } }`

## Add a comment
`mutation{ commentCreate(input:{ issueId:"<id>", body:"<md>" }){ comment{ id } } }`

## List actionable issues (needs-agent in the project) + their comments
`{ issues(filter:{ project:{id:{eq:"<proj>"}}, labels:{name:{in:["needs-agent"]}} }){ nodes{ id identifier title description labels{nodes{name}} comments{nodes{ id body createdAt user{name} }} } } }`

## Move lifecycle (swap labels) — fetch current labelIds, then:
`mutation{ issueUpdate(id:"<id>", input:{ labelIds:[<new set>] }){ success } }`
