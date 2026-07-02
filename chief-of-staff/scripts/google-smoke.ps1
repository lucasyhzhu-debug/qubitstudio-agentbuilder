# chief-of-staff/scripts/google-smoke.ps1
# Phase-A exit check: for each account in GOOGLE_ACCOUNTS, mint an access token
# (per chief-of-staff/references/google-auth.md) and call calendarList + Gmail profile.
# pending: needs live env (provisioned GOOGLE_* env vars) — NOT run in headless CI.
$ErrorActionPreference = "Stop"
$cid  = [Environment]::GetEnvironmentVariable('GOOGLE_OAUTH_CLIENT_ID','User')
$csec = [Environment]::GetEnvironmentVariable('GOOGLE_OAUTH_CLIENT_SECRET','User')
$accts = ([Environment]::GetEnvironmentVariable('GOOGLE_ACCOUNTS','User') -split ',') | Where-Object { $_ }
if (-not $accts) { "GOOGLE_ACCOUNTS not set (e.g. 'personal,work')"; exit 1 }

# Gate OAuth client-id/secret: only required if at least one label uses the refresh flow
$needsOAuth = $false
foreach ($a in $accts) {
    $L2 = $a.Trim().ToUpper()
    $k2 = [Environment]::GetEnvironmentVariable("GOOGLE_AUTH_KIND_$L2", 'User')
    if ((-not $k2) -or ($k2 -eq 'refresh')) { $needsOAuth = $true; break }
}
if ($needsOAuth -and -not ($cid -and $csec)) { "GOOGLE_OAUTH_CLIENT_ID / _SECRET not set"; exit 1 }

# Resolve venv Python for SA token minting
$venvPython = Join-Path $PSScriptRoot '..\..\.venv\Scripts\python.exe'
if (-not (Test-Path $venvPython)) { $venvPython = 'python' }

$fail = 0
foreach ($label in $accts) {
    $L    = $label.Trim().ToUpper()
    $kind = [Environment]::GetEnvironmentVariable("GOOGLE_AUTH_KIND_$L", 'User')
    if (-not $kind) { $kind = 'refresh' }

    # --- mint per auth-kind ---
    $access = $null
    if ($kind -eq 'refresh') {
        $rt = [Environment]::GetEnvironmentVariable("GOOGLE_REFRESH_TOKEN_$L", 'User')
        if (-not $rt) { "  [$label] MISSING GOOGLE_REFRESH_TOKEN_$L"; $fail++; continue }
        try {
            $body = "grant_type=refresh_token&client_id=$cid&client_secret=$csec&refresh_token=$rt"
            $tok  = Invoke-RestMethod -Method Post -Uri "https://oauth2.googleapis.com/token" `
                      -ContentType "application/x-www-form-urlencoded" -Body $body
            $access = $tok.access_token
        } catch {
            $code = $null; if ($_.Exception.Response) { $code = [int]$_.Exception.Response.StatusCode }
            "  [$label] FAIL (HTTP $code) $($_.Exception.Message)"; $fail++; continue
        }
    } elseif ($kind -eq 'service_account') {
        $saPath = [Environment]::GetEnvironmentVariable("GOOGLE_SA_KEY_PATH_$L", 'User')
        if (-not $saPath -or -not (Test-Path $saPath)) {
            "  [$label] MISSING GOOGLE_SA_KEY_PATH_$L"; $fail++; continue
        }
        $access = (& $venvPython (Join-Path $PSScriptRoot 'mint-sa-token.py') --label $L | Out-String).Trim()
        if ($LASTEXITCODE -ne 0) {
            "  [$label] FAIL mint-sa-token exited $LASTEXITCODE - $access"; $fail++; continue
        }
    } else {
        "  [$label] UNKNOWN auth kind '$kind'"; $fail++; continue
    }

    # --- shared API calls (both paths) ---
    try {
        $H    = @{ Authorization = "Bearer $access" }
        $cal  = Invoke-RestMethod -Headers $H -Uri "https://www.googleapis.com/calendar/v3/users/me/calendarList"
        $prof = Invoke-RestMethod -Headers $H -Uri "https://gmail.googleapis.com/gmail/v1/users/me/profile"
        "  [$label] OK  email=$($prof.emailAddress)  calendars=$($cal.items.Count)"
    } catch {
        $code = $null; if ($_.Exception.Response) { $code = [int]$_.Exception.Response.StatusCode }
        "  [$label] FAIL (HTTP $code) $($_.Exception.Message)"; $fail++
    }
}
if ($fail -gt 0) { "SMOKE FAILED ($fail account(s))"; exit 1 } else { "SMOKE OK" }
