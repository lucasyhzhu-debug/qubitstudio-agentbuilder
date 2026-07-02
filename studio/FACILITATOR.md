# FACILITATOR.md — shared-infra runbook (do this before Friday)

Twenty participants each compose their own chief-of-staff in the studio, on their own laptop, with
their own `claude` login (§2 of the design spec). The one thing that does **not** scale to twenty
people is provisioning: nobody should be creating a GCP project or a Discord application live in the
room. You pre-create **one** shared Discord server + bot, **one** shared Linear workspace, and **one**
shared Google OAuth client, then hand out the resulting values. Participants only **paste** shared
values and **mint their own** Google refresh token (their calendar, their mail, their token) — see
spec §2.1 lever #1 and §9.5 for the full env contract this runbook is grounded in.

> **Never commit real values.** Fill in the blanks below in a local, untracked copy (or a password
> manager entry) — this file in the repo stays a template. Same discipline as every other secret in
> this project: flat env vars / local files, never git, never the vault.

Total setup time: ~30–45 minutes, once, a few days before the workshop.

---

## Step 1 — Discord: one server, one bot

The only skill that needs Discord is **Inbox drain** (`requires: ["discord","linear","scheduler"]` in
`studio/catalog.json`) — it watches one channel and turns messages into Linear issues. Everything else
on the shelf is Google- or Linear-only, so this step only matters for participants who pick Drain.

1. Create a new Discord server (or reuse a workshop server) — this is the shared **guild**.
2. Create an application + bot at [discord.com/developers/applications](https://discord.com/developers/applications).
   Copy the **bot token** — this is the shared `DISCORD_BOT_TOKEN`.
3. Under **Bot → Privileged Gateway Intents**, enable **Message Content Intent** and **Server Members
   Intent** (the drain's `mcp-discord` server needs both to read channel messages and resolve members).
4. Invite the bot to the guild with: **View Channels**, **Send Messages**, **Read Message History**,
   **Create Public Threads**, **Send Messages in Threads**.
5. Record the **guild id** (right-click the server icon → Copy Server ID, Developer Mode on) — this is
   the shared `DISCORD_GUILD_ID`.
6. Create one **`#inbox-<participant-name>`** channel per registered participant who is likely to pick
   Drain (use the signup roster). Record each channel id — these are **per-person**, not shared
   (`DISCORD_CHANNEL_INBOX`). If someone picks Drain on the day without a pre-made channel, create their
   channel live — it's a 30-second add, don't block the room for it.
7. **Testing the bot token headless:** every Discord REST call needs
   `User-Agent: DiscordBot (<url>, <version>)`. Without it, Discord's Cloudflare edge returns an
   **empty-body 403** — looks like a bad token/permissions problem, isn't. `studio/smokes.py` already
   sets this UA; if you test manually with `curl`, set it yourself:
   ```
   curl -H "Authorization: Bot $DISCORD_BOT_TOKEN" -H "User-Agent: DiscordBot (https://qubitstudio.app, 0.1)" \
        https://discord.com/api/v10/users/@me
   ```
   A real permission error carries a JSON `code` field; an empty body + `Server: cloudflare` is the UA
   gotcha, not a permissions problem.

## Step 2 — Linear: one workspace, one team, one project

Every participant's composed **Task list** or **Inbox drain** skill points at one shared team id and
project id (`chief-of-staff/skills/drain/references/linear-api.md` hardcodes these for Lucas's own
build; the composer templates them to `{{LINEAR_TEAM_ID}}` / `{{LINEAR_PROJECT_ID}}` for the workshop).

1. Create (or reuse) the workshop's Linear workspace.
2. Create one team (e.g. "Workshop") and one project inside it (e.g. "Workshop Agents"). Record the
   **team id** and **project id** (Linear → Settings → API, or from the GraphQL `teams`/`projects`
   query) — these are baked into each participant's composed drain skill at build time, not a runtime
   env var. Supply them alongside the handout below (§4) so whoever wires the composer's Linear
   templating has them.

**Auth: invite-per-participant (default) vs. one shared key (fallback)**

| | Invite-per-participant | Shared key |
|---|---|---|
| What | Each participant joins the workspace with their own free Linear account, generates their own **personal API key** from their own settings | Facilitator generates **one** API key, pastes it into every handout |
| Pro | Real per-user auth; issues in the shared project are attributable to their creator; revoke one person without breaking the room; teaches correct key hygiene | Zero signup friction — works in seconds, no invite-acceptance lag |
| Con | Signup + invite-accept + key-gen costs each participant a couple of minutes | One key held by 20 laptops; a leak or revoke takes the whole room down; no attribution — every issue looks like it came from the facilitator's account |
| Default | **Yes — use this unless invite/signup is visibly eating the room's time** | Fallback only, and only announced live if invite friction bites |

Either way, `LINEAR_API_KEY` is the **only** runtime env var Linear needs (raw key in the
`Authorization` header — no `Bearer`). Send workspace invites (or generate the fallback key) a few
days out so acceptance lag doesn't cost workshop time.

## Step 3 — Google OAuth client: one client, Testing mode

Every Google-needing skill (**Daily debrief**, **Scheduling & email**) uses one shared **Desktop OAuth
client** across every participant's `refresh`-kind account; each participant mints their **own**
refresh token from it via the consent flow, during the workshop.

1. Create (or reuse) a Google Cloud project → enable the **Google Calendar API** and **Gmail API**.
2. **APIs & Services → Credentials → Create OAuth client ID → Desktop app.** Copy the **client ID** and
   **client secret** — these are the shared `GOOGLE_OAUTH_CLIENT_ID` / `GOOGLE_OAUTH_CLIENT_SECRET`.
3. **OAuth consent screen → keep Publishing status at "Testing."** Do **not** push to Production for
   the workshop: Testing mode needs no Google verification review (Gmail's scopes are "restricted" and
   verification takes weeks — a non-starter for a one-day event) at the cost of refresh tokens expiring
   after 7 days, which is irrelevant since the workshop is one day.
4. Add the scopes: `calendar.readonly`, `calendar.events`, `gmail.readonly`.
5. **Add every participant's Google account email as a test user** (OAuth consent screen → Test users
   — up to 100). Collect these emails on the signup roster ahead of time; without this, a participant's
   consent flow hard-blocks on Google's "app not verified, and you're not a tester" screen with no way
   past it in the room.
6. Each participant mints their own token **at the workshop**. The wizard's google row only **saves**
   the pasted shared client id/secret (there's no live Test for google — a client id/secret alone can't
   be smoke-tested, it needs a minted access token the wizard never has); the actual token mint happens
   in the separate consent step, not in the wizard.

---

## Step 4 — credentials handout template

Give participants this block at check-in (facilitator-provided rows filled in from steps 1–3; the
rest they fill in live). It matches the env-var contract in spec §9.5 and the `/api/keys/test` field
names in `studio/smokes.py` exactly — paste, don't rename.

```env
# --- facilitator-provided: paste exactly as given, same for everyone ---
DISCORD_BOT_TOKEN=
DISCORD_GUILD_ID=
LINEAR_API_KEY=            # only if we're on the shared-key fallback (§2) — otherwise generate your own
GOOGLE_OAUTH_CLIENT_ID=
GOOGLE_OAUTH_CLIENT_SECRET=

# --- yours: fill in during the workshop ---
DISCORD_CHANNEL_INBOX=     # your #inbox-<name> channel id, assigned at check-in
OWNER_USER_ID=             # your Discord user id — Settings > Advanced > Developer Mode, right-click your name > Copy User ID
LINEAR_API_KEY=            # your own personal key, if we're on invite-per-participant (§2 default)
GOOGLE_ACCOUNTS=personal
GOOGLE_EMAIL_PERSONAL=     # your Gmail address
GOOGLE_REFRESH_TOKEN_PERSONAL=   # printed by the studio's Google consent step — paste, don't retype
WIKI_ROOT=                 # your local vault path, e.g. ~/wiki-brain or C:\Users\<you>\wiki-brain
```

Only two rows can be genuinely secret-sensitive to hand out broadly: `DISCORD_BOT_TOKEN` and the
shared-fallback `LINEAR_API_KEY`. Both live only in each participant's own local `.env` (per
`studio/keys.py`'s persistence, not the studio repo) — never paste them into a shared doc that
outlives the room; rotate/revoke both after the workshop.

## `WORKSHOP_DEFAULTS` — what the wizard pre-seeds

`studio/static/app.js`'s connect-integrations wizard pre-seeds paste fields from a `WORKSHOP_DEFAULTS`
object (Task 13) so participants don't retype shared values by hand. Feed it exactly the
**facilitator-provided** rows above — nothing per-person:

| Key | Value | Why shared |
|---|---|---|
| `DISCORD_BOT_TOKEN` | from Step 1.2 | one bot for the room |
| `DISCORD_GUILD_ID` | from Step 1.5 | one server for the room, but the wizard has no input field for it — it's handout-only, participants don't paste it anywhere |
| `GOOGLE_OAUTH_CLIENT_ID` | from Step 3.2 | one Desktop OAuth client shared across every `refresh`-kind account |
| `GOOGLE_OAUTH_CLIENT_SECRET` | from Step 3.2 | same client as above |
| `LINEAR_API_KEY` | from Step 2, **only if** shared-key fallback is in effect | omit entirely on the invite-per-participant default — leave the row blank so each participant pastes their own |

Leave every per-person row (`DISCORD_CHANNEL_INBOX`, `OWNER_USER_ID`, `GOOGLE_EMAIL_PERSONAL`,
`GOOGLE_REFRESH_TOKEN_PERSONAL`, `WIKI_ROOT`) **out** of `WORKSHOP_DEFAULTS` — those must stay blank
paste fields, one per participant, or the wizard will silently point twenty agents at one person's
calendar/channel.

---

## Step 5 — pre-Friday checklist

| What | Where recorded | Done when |
|---|---|---|
| Discord application + bot created | Step 1.2 → `DISCORD_BOT_TOKEN` | Token copied into your local credentials file |
| Message Content + Server Members intents enabled | Discord Developer Portal → Bot | Both toggles green |
| Bot invited to guild with the 5 permissions | Step 1.4 | Bot shows Online in the server's member list |
| Guild id recorded | Step 1.5 → `DISCORD_GUILD_ID` | Copied into your local credentials file |
| Per-participant `#inbox-<name>` channels created | Step 1.6 | One channel per roster entry, ids recorded |
| Discord bot token smoke-tested | Step 1.7 | `curl` call with the `DiscordBot` UA returns 200, not an empty-body 403 |
| Linear workspace + team + project created | Step 2 | Team id + project id recorded |
| Linear auth strategy decided (invite vs. shared key) | Step 2 | Invites sent, or fallback key generated |
| Google Cloud project created, Calendar + Gmail APIs enabled | Step 3.1 | Both APIs show "Enabled" in the console |
| OAuth Desktop client created | Step 3.2 → `GOOGLE_OAUTH_CLIENT_ID`/`_SECRET` | Both copied into your local credentials file |
| Consent screen kept in Testing, scopes added | Step 3.3–3.4 | Publishing status = "Testing"; 3 scopes listed |
| Every participant's Google email added as a test user | Step 3.5 | Roster count == test user count on the consent screen |
| Credentials handout filled in (facilitator rows only) | Step 4 | Ready to hand out at check-in — not committed anywhere |
| `WORKSHOP_DEFAULTS` values ready to inject into the studio | Step 4 (table) | Same 4–5 values as the handout's facilitator rows, nothing per-person |
