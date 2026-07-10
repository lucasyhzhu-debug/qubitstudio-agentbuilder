# chief-of-staff

Your personal chief of staff — runs your day and week from your local wiki-brain knowledge base, Google Workspace (email + calendar), Discord, and Linear.

## What it does

- **Daily/weekly briefings** — asks what's on your plate, proposes priorities, surfaces CRM context before meetings
- **Scheduling** — interprets natural instructions ("meet so-and-so Tuesday") into confirm-gated calendar events
- **Task management** — captures to-dos from conversation into your Linear board and maintains them
- **Personal CRM** — records and recalls people in `wiki-brain/people/`, including network connections for warm-intro paths

## Self-layer

The agent has a persistent **self** in your wiki vault, read once per conversation before it acts:

| File | What it is |
|---|---|
| `meta\chief-of-staff\personality.md` | Its **voice** — warm & personable. The single living source; edit it to change how the agent sounds, no code change. |
| `meta\memories.md` | What it knows about **you** — a shared hub (the your-assistant-bot reads the same file), wiki-style: it links to deep-dives and grows by category. |
| `meta\chief-of-staff\lessons.md` | How it's **learned to work** for you. |

Voice is no longer hardcoded in the skills — they read `personality.md`. A future `cos-retro` skill will
refine the self-layer from real interactions (additive auto-apply; behavioural changes gated). The vault
path is the same one the CRM skill uses (`{{VAULT_PATH}}`); update it there if your vault moves.

## Skills

| Skill | Trigger |
|---|---|
| `briefing` | "what's my day", "brief me", "what should I focus on" |
| `scheduling` | "set up a meeting with X", "draft a reply to Z" |
| `tasks` | "add this to my list", "what's on my plate", "mark done" |
| `crm` | "who is X", "log that I met Y", "intro path to Z" |
| `intake` | you send/paste an image or screenshot, "what's this", "handle this", or tag it `task`/`crm`/`ingest`/`?` |

## Intake

Hand `chief-of-staff` an image — a screenshot of a Slack message, a photo of a business card, a snap of an article or slide — and it **views** it (transcribes the text, describes the visual), **classifies** intent, and **proposes** a routed action:

- **task(s)** → your Linear list (via `tasks`)
- **CRM** → a person page (via `crm`)
- **knowledge** → filed to wiki-brain (via `wiki-brain:ingest`)
- **answer** → read & answered inline

Classification is hybrid: it auto-classifies, asks **one** disambiguating question on a close call instead of guessing, and a one-word hint (`task` / `crm` / `ingest` / `?`) always overrides. It **proposes, never files** — nothing is created until you say yes. Images arrive two ways: attached live in conversation, or dropped in your Discord `#inbox` (where `context-gatherer` now downloads + transcribes them so they're real content, not just a filename, and `briefing` routes them through `intake`).

## Scheduling confirm grammar (v0.7.0, Lucas-only)

When the drain parks a scheduling proposal at `needs-owner` and posts candidate slots to the Discord thread, reply with a **bare confirm token** to authorize the calendar write:

| Reply | What happens |
|---|---|
| `confirm` or `yes` or `go` | Books the default slot (slot 1) |
| `confirm 2` / `yes 2` / `go 2` | Books slot 2 (1-based index) |
| `change the time to 3pm` | Triggers a draft edit — re-composes and re-posts, stays `needs-owner` |
| Anything else, or same words followed by prose | Treated as chatter — no action |

**Lucas-only:** the drain authenticates the confirm by `author.id == OWNER_USER_ID`. A reply from any other participant in the thread is always chatter, regardless of content. This is the sole write-authorization gate — the calendar write never executes without it.

> **Track-2 (`gmail.send` custom invite email) — NOT in v0.7.0.** An agent-sent custom invitation email is a planned fast-follow that needs re-consent for the `gmail.send` scope and an additional adversarial send-eval. For now, the calendar `sendUpdates=all` parameter delivers standard Google Calendar invites to attendees automatically when the event is written.

## Post-meeting capture (v0.7.0)

To file a meeting after it ends, dictate your notes into the meeting's Discord thread. When you're done, send a finalize cue:

| Cue | Effect |
|---|---|
| `done` | Files the meeting record and todos |
| `that's it` | Same as `done` |
| `file it` | Same as `done` |

On the cue, the `capture` skill:
- Writes a `## Minutes` section from your words (not rewritten — your voice, your attribution)
- Adds an agent `## Synthesis` section
- Fans out a CRM interaction line to each attendee's `people/` wiki page
- Creates a `meeting-todo` Linear issue (with `needs-agent`) for each identified action item

The `meeting-todo` Linear label is created automatically the first time capture runs. If you want to pre-create it, add it to the **Lucas Agents** project with any colour.

## Agents

| Agent | Purpose |
|---|---|
| `context-gatherer` | Sweeps Gmail, Calendar, Discord, Linear, and wiki-brain before each briefing (spawned by `briefing`, not invoked directly) |

## Setup

### 1. Install prerequisites

chief-of-staff reaches **Gmail, Google Calendar, and Linear** through **two transports**. **Interactive** Claude Code sessions use your **native claude.ai connectors** — connect the Gmail, Google Calendar, and Linear connectors in your Claude session (Settings → Connectors); the skills/agent call them via `mcp__claude_ai_Gmail__*`, `mcp__claude_ai_Google_Calendar__*`, and `mcp__claude_ai_Linear__*`. The **headless cron** (runs under `claude -p`, where the claude.ai connectors are absent) accesses each service directly via keys and tokens — `LINEAR_API_KEY` for Linear, `DISCORD_BOT_TOKEN` for Discord, and Google OAuth refresh tokens for Calendar + Gmail (configured below).

The only server the agent runs itself is **Discord**, configured with the env vars below.

**Discord** — served locally by the open-source [`mcp-discord`](https://github.com/barryyip0625/mcp-discord). There is **no endpoint to host**: `.mcp.json` launches `npx -y mcp-discord` over stdio and passes your bot token through. You only need Node 18+ (for `npx`) and a bot token.
```
DISCORD_BOT_TOKEN=<your discord bot token>
DISCORD_GUILD_ID=<your server/guild id>
DISCORD_CHANNEL_DAILY_BRIEFS=<channel id for #daily-briefs>
DISCORD_CHANNEL_INBOX=<channel id for #inbox>
DISCORD_CHANNEL_LONG_FORM=<channel id for #long-form>
OWNER_USER_ID=<your Discord user id>
```

`OWNER_USER_ID` is required for the v0.7.0 scheduling confirm gate: the drain authenticates every confirm reply by checking `author.id == OWNER_USER_ID` before granting write authorization. A reply from any other user — even containing `confirm 2` — is treated as chatter and never authorizes a calendar write. Find your Discord user id under **Settings → Advanced → Developer Mode** (enable it), then right-click your own name and **Copy User ID**. Set with `setx OWNER_USER_ID "<id>"`.

Set-up steps:
1. Create an application + bot at [discord.com/developers](https://discord.com/developers/applications) and copy the **bot token** into `DISCORD_BOT_TOKEN`.
2. Under **Bot → Privileged Gateway Intents**, enable **Message Content Intent** and **Server Members Intent** (`mcp-discord` requires both to read channel messages and resolve members).
3. Invite the bot to your server with the **View Channels**, **Send Messages**, **Read Message History**, **Create Public Threads**, and **Send Messages in Threads** permissions. (The v0.5.0 drain opens one thread per request and posts acks/results into it, so the thread permissions are required — not just the read/send ones the briefing flow used.)
4. The root .mcp.json exposes the bot's tools as `mcp__discord__*` (e.g. `discord_send`, `discord_read_messages`) — already wildcarded for the `context-gatherer` agent.

**Linear** — two transports are in play. **Interactive briefs** use the native claude.ai Linear connector (`mcp__claude_ai_Linear__*`) — keep it enabled in your Claude session. The **headless continuous drain** (runs under `claude -p` cron, where the claude.ai connectors are absent) reads and writes Linear directly via the GraphQL API:
```
LINEAR_API_KEY=<your linear personal api key>
```
The drain creates issues in the **Lucas Agents** project (id `{{LINEAR_PROJECT_ID}}`). It only processes messages from the **watched-channel allowlist** — a map of Discord channel ids to `ch:` labels configured in the drain skill. By default `#inbox` maps to `ch:inbox`; add channels to expand coverage.

**Google (Calendar + Gmail)** — the v0.6.0 meeting lifecycle reads your calendar + recent email and (with your Discord confirm) writes events. Like Linear/Discord, the **headless** path uses keys, not the interactive connector. One-time setup, per Google account you want connected:

1. **Google Cloud project** → [console.cloud.google.com](https://console.cloud.google.com) → enable the **Google Calendar API** and **Gmail API**.
2. **OAuth client** → APIs & Services → Credentials → Create OAuth client ID → **Desktop app**. Copy the **client ID + client secret**:
   ```
   setx GOOGLE_OAUTH_CLIENT_ID "<client id>"
   setx GOOGLE_OAUTH_CLIENT_SECRET "<client secret>"
   ```
3. **Publishing status → Production** (OAuth consent screen) — otherwise refresh tokens expire after 7 days. Gmail is a "restricted" scope, so you'll click past an "unverified app" warning (expected for your own single-user app).
4. **Consent, per account** (opens a browser; grants Calendar + Gmail):
   ```
   python chief-of-staff\scripts\google-consent.py --label personal
   ```
   It prints a `setx GOOGLE_REFRESH_TOKEN_PERSONAL "..."` line — run it, then set `GOOGLE_EMAIL_PERSONAL` and append the label to `GOOGLE_ACCOUNTS` (set this after you've consented every account you list):
   ```
   setx GOOGLE_EMAIL_PERSONAL "you@gmail.com"
   setx GOOGLE_ACCOUNTS "personal,work"
   ```
   Repeat with `--label work` for a second account.
5. **Verify** (new terminal so `setx` vars load):
   ```
   powershell -ExecutionPolicy Bypass -File chief-of-staff\scripts\google-smoke.ps1
   ```
   Expect `[<label>] OK  email=...  calendars=N` per account, then `SMOKE OK`.

Scopes requested: `calendar.readonly`, `calendar.events` (write), `gmail.readonly`. A Google password reset revokes the refresh token — re-run the consent step for that account. Tokens live **only** in your User environment variables (never in git or the OneDrive-synced vault).

> **Security note:** two commands paste sensitive credentials into your shell: `setx GOOGLE_OAUTH_CLIENT_SECRET "..."` (step 2) and `setx GOOGLE_REFRESH_TOKEN_* "..."` (step 4) both land in your PowerShell history (`ConsoleHost_history.txt`). After provisioning, clear both lines from history (or run `Clear-History` / delete the entries) so neither credential is left in plaintext on disk. The refresh token is also printed to terminal output by `google-consent.py` — scroll up and clear that scrollback too.

### 2. Configure wiki-brain path

The CRM skill reads and writes `{{VAULT_PATH}}/people/`. Update this path in `skills/crm/SKILL.md` if your wiki-brain lives elsewhere.

### 3. Launch your composed agent

```powershell
cd dist/<name>-cos
claude
```

Your agent lives in that folder — launch Claude Code there and the skills load.

### 4. Set up routines (optional)

Use `/schedule` to register the daily and weekly brief routines (see Scheduling section below).

### 5. Register the continuous drain (Task Scheduler)

The continuous drain polls Discord and routes new requests to Linear every 5 minutes. Register it once from an **elevated** PowerShell, run **from the repo root**:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File chief-of-staff\scripts\register-drain-task.ps1
```

This helper registers the `CoS Drain` task **hidden** (`-WindowStyle Hidden` + a non-interactive S4U principal, so no PowerShell window flashes up every 5 minutes), **non-overlapping** (`MultipleInstances IgnoreNew`), and **time-capped** (10-min limit so a wedged run can't hang). Re-run it any time to repair the task. After the first run, open Task Scheduler once and confirm the trigger reads *"Repeat every 5 minutes indefinitely."* Runs while the PC is on (KnowledgeBot parity); the pre-check skips idle cycles; laptop-off is out of scope.

> The helper registers under your local Windows account (`$env:USERNAME`) with an S4U logon. If you sign in with a **Microsoft / Azure AD** account and registration fails, register interactively in Task Scheduler instead, ticking *"Run whether user is logged on or not"* + *"Hidden"* — that yields the same no-popup behaviour.

> **Do not** register the task with a bare `schtasks /create ... /TR "powershell ... -File drain-precheck.ps1"`. Without `-WindowStyle Hidden` a console window pops up on every 5-minute run, and the drain's `claude -p` is invoked with `--strict-mcp-config` so it loads **zero** MCP servers — registering it any other way (or removing that flag) reintroduces the global-MCP-stack leak fixed in v0.5.1.

### 6. Register the morning brief (Task Scheduler)

The meeting-aware morning brief runs weekdays at 08:00 local, posting to `$DISCORD_CHANNEL_DAILY_BRIEFS`. Register it once from an **elevated** PowerShell, run **from the repo root**:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File chief-of-staff\scripts\register-brief-task.ps1
```

This helper registers the `CoS Morning Brief` task **hidden** (`-WindowStyle Hidden` + a non-interactive S4U principal, so no PowerShell window pops up every morning), **non-overlapping** (`MultipleInstances IgnoreNew`), and **time-capped** (15-min limit so a wedged run can't hang). Re-run it any time to repair the task. After the first run, open Task Scheduler once and confirm the trigger reads *"At 8:00 AM every Monday, Tuesday, Wednesday, Thursday, Friday."*

> The helper registers under your local Windows account (`$env:USERNAME`) with an S4U logon. If you sign in with a **Microsoft / Azure AD** account and registration fails, register interactively in Task Scheduler instead, ticking *"Run whether user is logged on or not"* + *"Hidden"* — that yields the same no-popup behaviour.

> **Do not** register the task with a bare `schtasks /create ... /TR "powershell ... -File brief-precheck.ps1"`. Without `-WindowStyle Hidden` a console window pops up every morning, and `brief-precheck.ps1` must be invoked with `--strict-mcp-config` so it loads **zero** MCP servers — registering it any other way (or removing that flag) reintroduces the global-MCP-stack leak fixed in v0.5.1.

The wrapper runs `claude -p --strict-mcp-config --mcp-config scripts\brief.mcp.json` with the briefing SKILL body piped via stdin. The `--strict-mcp-config` flag + the empty `brief.mcp.json` prevents the MCP stack from starting and leaking orphaned processes.

> **Work account (`you@example.com`) — service account + DWD (v0.8.0).** The work Google Workspace account uses a **service account with domain-wide delegation** — no browser consent required. Follow the one-time setup walkthrough at `chief-of-staff/references/google-workspace-sa-setup.md`, then set the three env vars:
> ```
> setx GOOGLE_AUTH_KIND_work "service_account"
> setx GOOGLE_SA_KEY_PATH_work "C:\path\to\service-account-key.json"
> setx GOOGLE_EMAIL_work "you@example.com"
> ```
> Token minting is handled by `scripts/mint-sa-token.py --label work` (called automatically by the precheck wrappers). Re-run `google-smoke.ps1` to confirm the work account returns `OK`. The personal account continues to use loopback OAuth (`google-consent.py --label personal`) — that path is unchanged.

### 7. Grant "Log on as a batch job" (one-time, elevated)

Both scheduled tasks above use an **S4U** logon (no stored password, no popup window). An S4U task can only start if the account holds the **"Log on as a batch job"** right (`SeBatchLogonRight`), which Windows does not always grant automatically. If a task fails to start with *"The operator or administrator has refused the request"* (HRESULT `0x800710E0` / decimal `-2147020576`) — and a busy drain can then silently stop processing with no other symptom — grant it once, from an **elevated** PowerShell, run **from the repo root**:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File chief-of-staff\scripts\grant-batch-logon-right.ps1
```

The helper is **idempotent and additive** — it appends your account's SID to the existing grantees (never overwriting the right, which would strip Administrators / IIS_IUSRS / others) and is a clean no-op if you already hold it. After granting, a `CoS Drain` run's *Last Result* should read `0`, not `-2147020576`.

## Verify installation

Once installed, try: **"What's my day look like?"**

The briefing skill should activate and begin gathering context.


## Storage
- `{{VAULT_PATH}}/people/ (markdown git repo)` — personal CRM (one rich page per person: identity, personal, professional, network links, give/get, interaction log, tags) (filesystem)
- `{{VAULT_PATH}} (markdown git repo)` — general knowledge (filesystem)
- `Linear` — task list (mcp)

## Memory
The agent persists facts under `memory/`:
- **user** — Lucas's priorities, working style, recurring commitments
- **reference** — people/CRM facts + network connections surfaced before meetings (from wiki-brain/people/)
- **feedback** — which proposals Lucas accepts/rejects, to tune future briefs

## Scheduling
Register these with `/schedule`:
- `daily-brief` (`cron: 0 8 * * 1-5 (weekday 8am)`) — compile the daily briefing + proposals and post to Discord #daily-briefs
- `weekly-brief` (`cron: 0 8 * * 1 (Monday 8am)`) — compile the week ahead + review last week, post to #daily-briefs
- `drain-inbox` (`every 3 min (default, adjustable)`) — read new requests in Discord #inbox, act on them (schedule/task/CRM), and reply in-channel
