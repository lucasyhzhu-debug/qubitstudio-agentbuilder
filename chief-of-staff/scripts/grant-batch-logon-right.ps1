# chief-of-staff/scripts/grant-batch-logon-right.ps1
#
# Grants the current user the "Log on as a batch job" right (SeBatchLogonRight).
#
# Why this exists:
#   register-drain-task.ps1 and register-brief-task.ps1 both register their scheduled
#   tasks with LogonType S4U *specifically* so no PowerShell console window flashes up
#   every cycle. An S4U task can only start if the account holds SeBatchLogonRight - and
#   that right is NOT always granted automatically at task-registration time. When it is
#   missing, every run fails at the very start with:
#       "The operator or administrator has refused the request"
#       (HRESULT 0x800710E0 / decimal -2147020576)
#   which looks like a credentials or permissions bug but is actually a missing Windows
#   local-security-policy grant. A busy drain can then silently stop processing entirely
#   with no other symptom. Run this ONCE, elevated, on any new machine - alongside the two
#   register-*-task.ps1 scripts.
#
# This script is IDEMPOTENT and ADDITIVE: it appends the current user's SID to the existing
# SeBatchLogonRight grantees, never overwriting the line (overwriting would silently strip
# Administrators / IIS_IUSRS / any other existing grantee from the right). Re-running after
# the grant is a clean no-op.
#
# Run from an ELEVATED PowerShell (editing user-rights policy requires admin).

$ErrorActionPreference = 'Stop'
$RightName = 'SeBatchLogonRight'

# -- 1. Require elevation. secedit /configure silently no-ops (or partially applies) without it.
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltinRole]::Administrator)) {
    throw "Run this from an ELEVATED PowerShell (Administrator) - granting a user right edits local security policy."
}

# The SID we are granting. Match by SID token, never by account name (names are ambiguous /
# localized; the policy file stores '*<SID>').
$mySid   = $identity.User.Value
$myToken = "*$mySid"
Write-Host "Current user: $($identity.Name)  ($mySid)"

# -- 2. Unique per-run temp paths so a stale export can never be merged back in. Each secedit
#       call uses /overwrite as well (belt and suspenders).
$stamp      = [guid]::NewGuid().ToString('N')
$exportInf  = Join-Path $env:TEMP "cos-sebatch-export-$stamp.inf"
$mergeInf   = Join-Path $env:TEMP "cos-sebatch-merge-$stamp.inf"
$seceditDb  = Join-Path $env:TEMP "cos-sebatch-$stamp.sdb"
$seceditLog = Join-Path $env:TEMP "cos-sebatch-$stamp.log"

# secedit is a NATIVE exe - its failures are NOT caught by $ErrorActionPreference, so every
# call's exit code is checked explicitly.
function Invoke-Secedit {
    param([string[]]$SeceditArgs, [string]$What)
    & secedit.exe @SeceditArgs | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "secedit $What failed (exit code $LASTEXITCODE). See log: $seceditLog"
    }
}

try {
    # -- 3. Export the current USER_RIGHTS policy so the merge is additive on top of it.
    Invoke-Secedit -What "export" -SeceditArgs @(
        '/export', '/areas', 'USER_RIGHTS', '/cfg', $exportInf, '/log', $seceditLog, '/quiet'
    )

    # secedit writes the .inf as UTF-16 (Unicode). Read the current SeBatchLogonRight grantees.
    $lines = Get-Content -LiteralPath $exportInf -Encoding Unicode
    $current = $lines | Where-Object { $_ -match "^\s*$RightName\s*=" } | Select-Object -First 1

    $existingTokens = @()
    if ($current) {
        # Right side of '=' is a comma-separated list of '*<SID>' (and occasionally bare names).
        $value = ($current -split '=', 2)[1]
        $existingTokens = @(
            $value -split ',' | ForEach-Object { $_.Trim() } | Where-Object { $_ }
        )
    }

    # -- 4. Idempotent: exact SID-token match (not substring - one SID can be a prefix of another).
    if ($existingTokens -contains $myToken) {
        Write-Host "'$($identity.Name)' already has $RightName - nothing to do." -ForegroundColor Green
        exit 0
    }

    # -- 5. Additive merge: keep every existing grantee, append our SID. Never emit a bare
    #       'SeBatchLogonRight = *<mySid>' that would drop Administrators / IIS_IUSRS / etc.
    $newTokens = @($existingTokens + $myToken)
    $newValue  = ($newTokens -join ',')

    $mergeContent = @(
        '[Unicode]'
        'Unicode=yes'
        '[Version]'
        'signature="$CHICAGO$"'
        'Revision=1'
        '[Privilege Rights]'
        "$RightName = $newValue"
    ) -join "`r`n"
    # Write as Unicode - secedit expects a UTF-16 .inf.
    Set-Content -LiteralPath $mergeInf -Value $mergeContent -Encoding Unicode

    Write-Host "Granting $RightName to $($identity.Name) (keeping $($existingTokens.Count) existing grantee(s))..."
    Invoke-Secedit -What "configure" -SeceditArgs @(
        '/configure', '/db', $seceditDb, '/cfg', $mergeInf,
        '/areas', 'USER_RIGHTS', '/overwrite', '/log', $seceditLog, '/quiet'
    )

    # Verify the grant actually landed (re-export and check the token is present now).
    Invoke-Secedit -What "verify-export" -SeceditArgs @(
        '/export', '/areas', 'USER_RIGHTS', '/cfg', $exportInf, '/log', $seceditLog, '/quiet', '/overwrite'
    )
    $after = Get-Content -LiteralPath $exportInf -Encoding Unicode |
        Where-Object { $_ -match "^\s*$RightName\s*=" } | Select-Object -First 1
    $afterTokens = @()
    if ($after) {
        $afterTokens = @(($after -split '=', 2)[1] -split ',' | ForEach-Object { $_.Trim() } | Where-Object { $_ })
    }
    if ($afterTokens -contains $myToken) {
        Write-Host "Done - $RightName granted. A CoS Drain run's Last Result should now be 0 (not -2147020576)." -ForegroundColor Green
    } else {
        throw "secedit reported success but $RightName still lacks $myToken after re-export. Check $seceditLog."
    }
}
finally {
    foreach ($f in @($exportInf, $mergeInf, $seceditDb, $seceditLog)) {
        if ($f -and (Test-Path -LiteralPath $f)) { Remove-Item -LiteralPath $f -Force -ErrorAction SilentlyContinue }
    }
}
