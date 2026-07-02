# Google API (OAuth) — headless token mint + REST helpers

The **only** `Bearer`-header contract in this plugin (Linear = raw key, Discord = `Bot `). Every Google call is two steps: (1) mint an access token from the account's refresh token, (2) call Calendar/Gmail with `Authorization: Bearer <access_token>`.

**Credentials** (flat User env vars — never on disk / the vault):
- `GOOGLE_ACCOUNTS=personal,work` enumerates labels · `GOOGLE_EMAIL_<LABEL>` — the account's own email (**every label** — consumers like the brief use it to identify Lucas's own accounts / external-ness). For a `service_account` label it is ALSO the domain user the SA impersonates (the DWD subject).
- `GOOGLE_AUTH_KIND_<LABEL>` ∈ `refresh` | `service_account` — **defaults to `refresh` when unset** (personal label needs no new config).
- **`refresh` labels**: `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET` — one Desktop OAuth client, shared across `refresh` labels only · `GOOGLE_REFRESH_TOKEN_<LABEL>` per account.
- **`service_account` labels**: `GOOGLE_SA_KEY_PATH_<LABEL>` — local path to the SA JSON key (**never on the vault**).
- Example roster: `personal` = gmail (`refresh`), `work` = `you@example.com` (`service_account`).

**Scopes** (frozen at consent): `calendar.readonly` · `calendar.events` · `gmail.readonly`.

## Step 0 — mint an access token (once per run per account, then reuse)

Select by `GOOGLE_AUTH_KIND_<LABEL>` (default `refresh`):

**`refresh` (personal / gmail):**
`POST https://oauth2.googleapis.com/token` · `Content-Type: application/x-www-form-urlencoded`
body: `grant_type=refresh_token&client_id=$GOOGLE_OAUTH_CLIENT_ID&client_secret=$GOOGLE_OAUTH_CLIENT_SECRET&refresh_token=$GOOGLE_REFRESH_TOKEN_<LABEL>` (values are assumed URL-safe — Google `client_secret`/refresh tokens contain only `-._~/` and digits/letters; URL-encode if that ever changes).
→ parse `.access_token` (valid ~1h). **Never log or persist it.**

**`service_account` (work / domain):**
```
python chief-of-staff/scripts/mint-sa-token.py --label <label>
```
Capture **stdout only** as the access token (it is the token; no trailing newline). No `client_id`/`client_secret`/`refresh_token` used for these labels. On a non-zero exit the helper writes a `config:` or `dwd:` diagnostic to **stderr** (capture stderr separately to classify the failure — see error handling below).
→ token valid ~1h. **Never log or persist it.**

Both paths yield an `access_token` used identically as `Authorization: Bearer <access_token>`.

**Error handling — branch on the response BODY `error`, not the bare status** (Google returns `400` for several token errors):
- **HTTP `400` + `{"error":"invalid_grant"}`** → the refresh token is revoked/expired (e.g. a Google password reset) → post a **"reconnect `<account>`"** notice to Discord and skip that account.
- **HTTP `401` / `{"error":"invalid_client"}`** → bad `client_id`/`client_secret` (misconfig, not a per-account problem) → post a distinct **"check `GOOGLE_OAUTH_CLIENT_*`"** notice.
- Any other `400` (`invalid_request`, …) or transient **5xx / network** → retry/skip, **no** reconnect notice.
- **`mint-sa-token.py` exits non-zero, stderr prefix `config:`** (missing/!exist key path, or missing `GOOGLE_EMAIL_<LABEL>`) → post **"check `GOOGLE_SA_KEY_PATH_<label>` / config"** notice and skip that account.
- **`mint-sa-token.py` exits non-zero, stderr prefix `dwd:`** (DWD not authorized / `unauthorized_client` / `access_denied`) → post **"authorize DWD for `<account>`"** notice and skip that account.
- One account failing must not block the others.

## Read calendars + events (`calendar.readonly`)
`GET https://www.googleapis.com/calendar/v3/users/me/calendarList`
`GET https://www.googleapis.com/calendar/v3/calendars/{calendarId}/events?timeMin={ISO}&timeMax={ISO}&singleEvents=true&orderBy=startTime`

## Create an event + send invite (`calendar.events`)
`POST https://www.googleapis.com/calendar/v3/calendars/{calendarId}/events?sendUpdates=all`
body: `{ "summary": "...", "start": {"dateTime": "..."}, "end": {"dateTime": "..."}, "attendees": [{"email": "..."}] }`
`sendUpdates=all` emails the invite — **no `gmail.send` scope needed**.

## Read recent mail with a person (`gmail.readonly`)
`GET https://gmail.googleapis.com/gmail/v1/users/me/messages?q=from:{email}%20OR%20to:{email}&maxResults=10`
`GET https://gmail.googleapis.com/gmail/v1/users/me/messages/{id}?format=metadata` — headers + snippet.
`GET https://gmail.googleapis.com/gmail/v1/users/me/profile` — the account email (used by the smoke check).
