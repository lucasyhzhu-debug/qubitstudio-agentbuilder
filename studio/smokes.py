from __future__ import annotations
import json, urllib.request

_UA = "DiscordBot (https://qubitstudio.app, 0.1)"   # non-DiscordBot UA → cloudflare 403 (looks like auth fail)

def _request_for(integration: str, values: dict):
    if integration == "discord":
        tok = values.get("DISCORD_BOT_TOKEN", "")
        return ("GET", "https://discord.com/api/v10/users/@me",
                {"Authorization": f"Bot {tok}", "User-Agent": _UA}, None)
    if integration == "linear":
        key = values.get("LINEAR_API_KEY", "")
        return ("POST", "https://api.linear.app/graphql",
                {"Authorization": key, "Content-Type": "application/json"},
                json.dumps({"query": "{ viewer { id } }"}))
    if integration == "google":
        # google needs a minted access token (per google-auth.md); the wizard mints then calls calendarList.
        tok = values.get("_access_token", "")
        return ("GET", "https://www.googleapis.com/calendar/v3/users/me/calendarList",
                {"Authorization": f"Bearer {tok}"}, None)
    raise KeyError(integration)

def smoke(integration: str, values: dict) -> dict:
    try:
        method, url, headers, body = _request_for(integration, values)
    except KeyError:
        return {"ok": False, "message": f"unknown integration '{integration}'"}
    try:
        data = body.encode() if body else None
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=15) as resp:
            ok = 200 <= resp.status < 300
            return {"ok": ok, "message": "connected ✓" if ok else f"HTTP {resp.status}"}
    except Exception as e:  # HTTPError/URLError → surface to the wizard
        return {"ok": False, "message": f"{type(e).__name__}: {e}"}
