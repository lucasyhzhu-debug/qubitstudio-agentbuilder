from studio import smokes

def test_discord_request_uses_discordbot_user_agent():
    m, url, headers, _ = smokes._request_for("discord", {"DISCORD_BOT_TOKEN": "abc"})
    assert url.endswith("/users/@me")
    assert headers["Authorization"] == "Bot abc"
    assert headers["User-Agent"].startswith("DiscordBot")   # the cloudflare-403 gotcha

def test_linear_request_is_viewer_probe():
    m, url, headers, body = smokes._request_for("linear", {"LINEAR_API_KEY": "lin_x"})
    assert "graphql" in url and headers["Authorization"] == "lin_x" and "viewer" in body

def test_smoke_maps_unknown_integration():
    r = smokes.smoke("nope", {})
    assert r["ok"] is False and "unknown" in r["message"].lower()
