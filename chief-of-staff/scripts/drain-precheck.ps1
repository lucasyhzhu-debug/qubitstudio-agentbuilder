# chief-of-staff/scripts/drain-precheck.ps1
#
# Windows Task Scheduler target: runs every ~5 min, does a cheap REST pre-check,
# and only spins up `claude -p` when there is actual work to drain.
#
# Prior art: wiki-brain/worker/instant-worker.mjs + run-worker.ps1
#   Key lesson (instant-worker.mjs:26-31): do NOT pass a slash command — pipe the
#   workflow body via stdin instead.  Strip YAML frontmatter first, then prepend an
#   execute-now instruction so the piped content is a clean runnable prompt.
#
param([string]$StatePath = "{{VAULT_PATH}}\meta\chief-of-staff\drain-state.json")
$ErrorActionPreference = "Stop"

# ── 1. Lockfile guard ────────────────────────────────────────────────────────
# Fetch the lock once (TOCTOU-safe): a concurrent run's finally can delete it
# between a Test-Path and a Get-Item, which would throw outside the try block.
$lock = Join-Path $env:TEMP "cos-drain.lock"
$existing = Get-Item $lock -ErrorAction SilentlyContinue
if ($existing -and ((Get-Date) - $existing.LastWriteTime).TotalMinutes -lt 15) {
    exit 0
}

try {
    # Create the lock as the FIRST statement inside try so finally unconditionally
    # owns its cleanup regardless of future edits.
    New-Item $lock -Force | Out-Null

    # ── 2. Load state (missing file → nothing to check) ───────────────────────
    $state = if (Test-Path $StatePath) {
        Get-Content $StatePath -Raw | ConvertFrom-Json
    } else {
        $null
    }

    $work = $false

    # ── 3. Discord pre-check ──────────────────────────────────────────────────
    # For each allowlisted channel in drain-state.json, fetch 1 message after the
    # stored watermark.  Any result → work exists.
    if ($state -and $state.channels) {
        # Discord's Cloudflare edge 403s requests without a compliant User-Agent
        # (PowerShell's default UA is blocked on guild/channel endpoints). Discord
        # requires the DiscordBot (<url>, <version>) form on every REST call.
        $dh = @{
            Authorization = "Bot $($env:DISCORD_BOT_TOKEN)"
            "User-Agent"  = "DiscordBot (https://github.com/lucasyhzhu-debug/Consulting-Agents, 0.7.0)"
        }
        foreach ($cid in $state.channels.PSObject.Properties.Name) {
            $wm  = $state.channels.$cid.watermark
            $url = "https://discord.com/api/v10/channels/$cid/messages?limit=1" + $(if ($wm) { "&after=$wm" } else { "" })
            $msgs = Invoke-RestMethod -Headers $dh -Uri $url
            if ($msgs.Count -gt 0) { $work = $true; break }
        }
    }

    # ── 4. Linear pre-check ───────────────────────────────────────────────────
    # Existence check only: is there >=1 "needs-agent" issue in the Lucas Agents
    # project? (project id canonical: skills/drain/references/linear-api.md).
    # `first:1` caps the payload to one node regardless of queue depth.
    # Uses the raw API key header (no "Bearer" prefix) as Linear requires.
    if (-not $work) {
        $q = '{"query":"{ issues(first:1, filter:{project:{id:{eq:\"{{LINEAR_PROJECT_ID}}\"}},labels:{name:{in:[\"needs-agent\"]}}}){ nodes{ id } } }"}'
        $lr = Invoke-RestMethod -Method Post -Uri "https://api.linear.app/graphql" `
                -Headers @{ Authorization = $env:LINEAR_API_KEY } `
                -ContentType "application/json" `
                -Body $q
        # Linear returns HTTP 200 with {"errors":[...],"data":null} on permission/schema
        # problems; ErrorActionPreference="Stop" won't catch that and .nodes.Count null-chains
        # to 0 — silently hiding actionable issues. Surface it explicitly.
        if ($lr.errors) { throw "Linear GraphQL error: $($lr.errors | ConvertTo-Json -Compress)" }
        if ($lr.data.issues.nodes.Count -gt 0) { $work = $true }
    }

    # ── 5. Idle path ──────────────────────────────────────────────────────────
    # finally removes the lock — no duplicate Remove-Item here.
    if (-not $work) { exit 0 }

    # ── 6. Work exists: pipe drain workflow body to claude -p via stdin ───────
    # Matches the wiki-brain pattern (instant-worker.mjs:29-31):
    #   a) Read SKILL.md
    #   b) Strip YAML frontmatter (--- ... ---)
    #   c) Prepend an execute-now instruction
    # Script lives in chief-of-staff/scripts/; the skill is a sibling in skills/drain/.
    $skillPath = Join-Path $PSScriptRoot "..\skills\drain\SKILL.md"
    $raw  = Get-Content $skillPath -Raw
    $body = $raw -replace '(?s)^---.*?---\s*', ''   # strip frontmatter
    $prompt = "Execute this chief-of-staff drain workflow now, then stop:`n`n" + $body
    # Windows PowerShell 5.1 defaults $OutputEncoding to ASCII, which corrupts the skill
    # body's non-ASCII chars (em-dashes, arrows) to '?' before reaching claude's stdin.
    $OutputEncoding = [System.Text.Encoding]::UTF8
    # The headless drain reaches every surface via curl (Discord REST + Linear
    # GraphQL), so it needs ZERO MCP servers. --strict-mcp-config makes `claude -p`
    # ignore ALL filesystem-discovered MCP config — the user's GLOBAL servers AND
    # this plugin's (drain-unused) discord server — and load only drain.mcp.json,
    # which is empty. Without it, every 5-min run booted the full global MCP stack
    # (chrome-devtools-mcp + its watchdog + a Chrome, context7, convex, ...), and
    # those children orphaned instead of exiting with claude -p — leaking dozens of
    # node processes and gigabytes of RAM over a day. See CHANGELOG v0.5.1.
    $mcpConfig = Join-Path $PSScriptRoot "drain.mcp.json"
    $prompt | & claude -p --strict-mcp-config --mcp-config $mcpConfig
    if ($LASTEXITCODE -ne 0) { throw "claude -p exited $LASTEXITCODE" }

} finally {
    Remove-Item $lock -Force -ErrorAction SilentlyContinue
}
