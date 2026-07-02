# Google Workspace — service-account + Domain-wide Delegation setup

One-time admin walkthrough for the `work` account (`you@example.com`). Run this when the personal loopback auth is working and you are ready to add the Workspace account. This also doubles as QubitStudio workshop material — the friction is real and documented below.

**Why a service account for `work` and not loopback OAuth?**
Consumer Gmail accounts use the loopback OAuth flow (personal refresh token). Workspace (Google Workspace / Google Apps) domains can instead grant a service account *domain-wide delegation* (DWD), which lets it impersonate any domain user without an interactive consent screen — the right fit for a headless cron agent.

---

## Step 1 — Enable the Gmail API + Google Calendar API

In the **existing cos GCP project** (the one already holding the Desktop OAuth client for the personal account):

1. Open [Google Cloud Console](https://console.cloud.google.com/) → your project.
2. Navigation menu → **APIs & Services → Library**.
3. Search for **Gmail API** → Enable.
4. Search for **Google Calendar API** → Enable.

Both must show "API enabled" before proceeding.

---

## Step 2 — Create a service account and record its IDs

1. Navigation menu → **IAM & Admin → Service Accounts → + Create Service Account**.
2. Name it something like `cos-chief-of-staff`; description is optional. Click **Create and Continue**.
3. Skip the optional role and user-access steps — DWD does not rely on IAM roles here. Click **Done**.
4. Click the new service account in the list to open its details.
5. Record two values from the **Details** tab:
   - **Email** (looks like `cos-chief-of-staff@<project-id>.iam.gserviceaccount.com`) — used in code as the SA identity.
   - **Unique ID** — a long **numeric** string (e.g. `118392847561029384756`). This is the **numeric Client ID** you will paste into the Admin Console in Step 4. It is NOT the email.

---

## Step 3 — Create and download the JSON key

1. Still on the service account page → **Keys** tab → **Add Key → Create new key → JSON** → **Create**.
2. The browser downloads a `.json` file. This is the only copy — Google does not store it.
3. Move it to a **local, non-synced path** — for example `C:\Users\<you>\.config\gcp\cos-sa-work.json`. The path you choose becomes `GOOGLE_SA_KEY_PATH_work`.

> **NEVER place this file anywhere under `{{VAULT_PATH}}` or any OneDrive-synced folder.** A service account JSON key is a persistent credential; putting it in the vault would sync it to the cloud and expose it in git history.

---

## Step 4 — Admin Console: grant Domain-wide Delegation

This step must be performed by a **Workspace super-admin** for `ikigaiventures.ai`.

1. Open [Google Admin Console](https://admin.google.com/) → **Security → Access and data control → API controls**.
2. Under **Domain-wide delegation** → **Manage Domain Wide Delegation → Add new**.
3. **Client ID field**: paste the **numeric Unique ID** from Step 2.
   - This is the numeric string (e.g. `118392847561029384756`), **not** the SA email address. The Admin Console will reject the email with a "service account not found" error.
4. **OAuth Scopes field**: paste these three scopes as a comma-separated list (no spaces):

   ```
   https://www.googleapis.com/auth/calendar.readonly,https://www.googleapis.com/auth/gmail.readonly,https://www.googleapis.com/auth/calendar.events
   ```
   > These three scopes must **exactly match** `SCOPES` in `chief-of-staff/scripts/mint-sa-token.py` — DWD token mints are all-or-nothing, so if you ever change the scope set, update **both** places together.

5. Click **Authorize**.

The delegation entry should now appear in the list showing the numeric Client ID and the three scopes.

---

## Step 5 — Set environment variables

```powershell
setx GOOGLE_AUTH_KIND_work    service_account
setx GOOGLE_SA_KEY_PATH_work  C:\Users\<you>\.config\gcp\cos-sa-work.json
setx GOOGLE_EMAIL_work        you@example.com
```

Then ensure `work` is in the accounts list (if it isn't already):

```powershell
setx GOOGLE_ACCOUNTS  personal,work
```

Restart any open PowerShell sessions so `[Environment]::GetEnvironmentVariable` picks up the new values.

---

## Step 6 — Verify

```powershell
.\chief-of-staff\scripts\google-smoke.ps1
```

Expected output — a per-account `OK` line for each label, then a global summary (the `[work]` line confirms the SA/DWD path is working):

```
[personal] OK  email=lucas.yh.zhu@gmail.com  calendars=4
[work] OK  email=you@example.com  calendars=6
SMOKE OK
```

A failure (`[work] FAIL …`) almost always means one of the friction points below.

---

## Friction box — known failure modes

**1. Numeric Client ID vs SA email in the DWD entry.**
The Admin Console entry must use the **numeric Unique ID**, not the service account email. Pasting the email produces a "service account not found" error or silently authorizes nothing useful. Re-check Step 4.

**2. Scope set must exactly match what the code mints — all-or-nothing.**
Google DWD is an exact-match gate. If the authorized scope set is `calendar.readonly,gmail.readonly` but the mint request includes `calendar.events`, the token request fails with `unauthorized_client`. The set in Step 4 (`calendar.readonly`, `gmail.readonly`, `calendar.events`) is the canonical list; any deviation requires updating both the DWD entry and the mint request in lockstep.

**3. `sub` / `GOOGLE_EMAIL_work` must be a real user in the domain.**
The service account impersonates a user via the `sub` claim in its JWT, which is `GOOGLE_EMAIL_work`. That address must exist as a live Workspace user in `ikigaiventures.ai`. A deleted, suspended, or non-existent user causes a `400 invalid_grant` on token mint. `you@example.com` is the intended subject.

**4. Consumer Gmail accounts cannot use DWD — this is why `personal` stays on the loopback flow.**
Domain-wide Delegation is a Workspace (paid/Google Apps) feature. A `@gmail.com` account has no Admin Console, so there is no way to authorize a DWD entry. The personal account must remain on the interactive OAuth + refresh-token path. Do not try to apply this walkthrough to a consumer account.

**5. Keep the JSON key off the vault.**
The key file is a long-lived credential. Placing it under `{{VAULT_PATH}}` (OneDrive-synced) would push it to the cloud. Keep it in a local path (`C:\Users\<you>\.config\gcp\`) and point `GOOGLE_SA_KEY_PATH_work` at that path. The vault and this repo's git history must never contain the key file.
