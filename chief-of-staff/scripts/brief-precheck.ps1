# chief-of-staff/scripts/brief-precheck.ps1
#
# Windows Task Scheduler target: runs weekdays ~08:00 local, always fires the
# morning brief (no idle/work-gate — the brief is time-triggered, not queue-
# triggered).
#
# Register (user-gated — run once in an elevated prompt; substitute real install path):
#   schtasks /create /tn "cos-morning-brief" /tr "powershell -NonInteractive -File <absolute-path-to-plugin>\chief-of-staff\scripts\brief-precheck.ps1" /sc WEEKLY /d MON,TUE,WED,THU,FRI /st 08:00 /f
#
# Required env vars (set via setx in User scope):
#   GOOGLE_OAUTH_CLIENT_ID        — OAuth client ID for Google APIs
#   GOOGLE_OAUTH_CLIENT_SECRET    — OAuth client secret
#   GOOGLE_REFRESH_TOKEN_*        — one var per account (suffix matches GOOGLE_ACCOUNTS entry)
#   GOOGLE_ACCOUNTS               — comma-separated account identifiers (e.g. "lucas,work")
#   DISCORD_BOT_TOKEN             — bot token for posting the brief
#   DISCORD_CHANNEL_DAILY_BRIEFS  — channel ID where the brief is posted
#   DISCORD_CHANNEL_INBOX         — channel ID for inbox context (read by the SKILL)
#
$ErrorActionPreference = "Stop"

# ── 1. Lockfile guard ────────────────────────────────────────────────────────
# Fetch the lock once (TOCTOU-safe): a concurrent run's finally can delete it
# between a Test-Path and a Get-Item, which would throw outside the try block.
$lock = Join-Path $env:TEMP "cos-brief.lock"
$existing = Get-Item $lock -ErrorAction SilentlyContinue
if ($existing -and ((Get-Date) - $existing.LastWriteTime).TotalMinutes -lt 15) {
    exit 0
}

try {
    # Create the lock as the FIRST statement inside try so finally unconditionally
    # owns its cleanup regardless of future edits.
    New-Item $lock -Force | Out-Null

    # ── 2. Pipe briefing workflow body to claude -p via stdin ─────────────────
    # No work-gate: the brief is time-triggered and always runs.
    # Matches the wiki-brain / drain pattern (instant-worker.mjs:29-31):
    #   a) Read SKILL.md
    #   b) Strip YAML frontmatter (--- ... ---)
    #   c) Prepend an execute-now instruction
    # Script lives in chief-of-staff/scripts/; the skill is at skills/briefing/.
    $skillPath = Join-Path $PSScriptRoot "..\skills\briefing\SKILL.md"
    $raw  = Get-Content $skillPath -Raw
    $body = $raw -replace '(?s)^---.*?---\s*', ''   # strip frontmatter
    $prompt = "Execute this chief-of-staff morning brief now, then stop:`n`n" + $body
    # Windows PowerShell 5.1 defaults $OutputEncoding to ASCII, which corrupts the skill
    # body's non-ASCII chars (em-dashes, arrows) to '?' before reaching claude's stdin.
    $OutputEncoding = [System.Text.Encoding]::UTF8
    # --strict-mcp-config scopes claude to an empty MCP server set, preventing the global
    # MCP stack (chrome-devtools, context7, convex) from spawning orphaned node/Chrome
    # child processes under Task Scheduler. drain-precheck.ps1 applies the same guard
    # via its own drain.mcp.json.
    $mcpConfig = Join-Path $PSScriptRoot "brief.mcp.json"
    $prompt | & claude -p --strict-mcp-config --mcp-config $mcpConfig
    if ($LASTEXITCODE -ne 0) { throw "claude -p exited $LASTEXITCODE" }

} finally {
    Remove-Item $lock -Force -ErrorAction SilentlyContinue
}
