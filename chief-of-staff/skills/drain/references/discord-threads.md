# Discord REST — thread helpers (mcp-discord exposes only read/send, so threads use REST)

Base: `https://discord.com/api/v10`
Headers on **every** call:
- `Authorization: Bot <DISCORD_BOT_TOKEN>`
- `User-Agent: DiscordBot (https://github.com/lucasyhzhu-debug/Consulting-Agents, 0.7.0)` — **required**: Discord's Cloudflare edge returns an empty-body 403 for requests with a non-compliant User-Agent (e.g. PowerShell's default). `curl`'s default UA passes, but always send the `DiscordBot (...)` form to be safe.

## New channel messages since watermark
`GET /channels/{channelId}/messages?after={watermark}&limit=100`

## Start a thread FROM a message (1 thread per request)
`POST /channels/{channelId}/messages/{messageId}/threads`
body: `{ "name": "<=100 char summary", "auto_archive_duration": 10080 }`
→ returns the thread channel object; its `id` is the threadId.

## Read thread replies since lastSeen
`GET /channels/{threadId}/messages?after={lastSeen}&limit=100`

## Post into a thread (ack / result / reply)
`POST /channels/{threadId}/messages`  body: `{ "content": "<text, <=2000 chars>" }`

## Current bot user (echo-skip)
`GET /users/@me`  Header: `Authorization: Bot <DISCORD_BOT_TOKEN>`
→ returns the current bot user object; `id` is the bot's own Discord user id.
