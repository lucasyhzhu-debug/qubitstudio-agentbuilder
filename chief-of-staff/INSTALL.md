# Installation — chief-of-staff

## Connectors model

chief-of-staff reaches **Gmail, Google Calendar, and Linear** through your **native claude.ai connectors** —
not through plugin-hosted MCP servers. Make sure those three connectors are connected in your Claude
session. The only server the plugin runs itself is **Discord** (locally, via `npx -y mcp-discord`).

## Install (composed agent home)

This substrate is not installed directly — the QubitStudio studio **composes** it into a
personal agent home under `dist/<name>-cos/` (run `python -m studio` and follow the
journey). The composed agent is a raw-skills directory: `.claude/skills/`, a generated
`CLAUDE.md` identity, and a root `.mcp.json`. To launch it:

```powershell
cd dist/<name>-cos
claude
```

Your agent lives in that folder — skills trigger when Claude Code runs there. No
marketplace, no `/plugin install`, no restart step.

## Required environment variables

Only Discord needs configuration (Gmail/Calendar/Linear go through claude.ai connectors). Set these as
**user environment variables** so `.mcp.json`'s `${VAR}` expansion resolves on every launch:

```env
# Discord MCP — served locally by the OSS `mcp-discord` (run via npx, needs Node 18+).
# No MCP URL/endpoint to host: .mcp.json launches `npx -y mcp-discord` over stdio
# and passes DISCORD_BOT_TOKEN through as the server's DISCORD_TOKEN.
DISCORD_BOT_TOKEN=
DISCORD_GUILD_ID=
DISCORD_CHANNEL_DAILY_BRIEFS=
DISCORD_CHANNEL_INBOX=
DISCORD_CHANNEL_LONG_FORM=
```

Set them on Windows (one-time, persists across sessions):

```powershell
setx DISCORD_BOT_TOKEN "your-token"
setx DISCORD_GUILD_ID "your-guild-id"
setx DISCORD_CHANNEL_DAILY_BRIEFS "channel-id"
setx DISCORD_CHANNEL_INBOX "channel-id"
setx DISCORD_CHANNEL_LONG_FORM "channel-id"
```

`setx` only affects new shells — restart Claude Code afterward. See `README.md` for the full Discord
bot-creation walkthrough (application, intents, invite, channel IDs).

## Verify installation

Once installed, try: **"What's my day look like?"**

The briefing skill should activate and begin gathering context.
