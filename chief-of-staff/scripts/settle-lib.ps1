# chief-of-staff/scripts/settle-lib.ps1
#
# Shared "settle window" logic for the drain (v0.9.0, upgrade feature #6).
#
# A *source* — an #inbox channel, or an issue's Discord thread — is processed only once it is
# SETTLED: quiet long enough that a multi-message dictation burst is complete. This is the ONE
# shared implementation, dot-sourced by scripts/drain-precheck.ps1 and mirrored (as prose) by the
# drain SKILL via references/settle-window.md — never a second divergent copy. When you tune the
# constants below, change references/settle-window.md in the same commit.
#
# PowerShell 5.1 note: snowflakes exceed Int32, so all id math is [long] (Int64). The 'L'/'D'
# numeric-literal suffixes are PowerShell 6.0+ only — this file uses explicit [long] casts so it
# runs unchanged on the Windows-bundled 5.1.

# ── Tunable constants (seconds). Keep in sync with references/settle-window.md. ────────────────
$script:SettleSingleSec   = 30    # a lone new non-bot message: settle this long after it
$script:SettleBurstSec    = 90    # two or more new non-bot messages: settle this long after newest
$script:SettleMaxDeferSec = 600   # ceiling: a perpetually active source can't starve forever

$script:DiscordEpochMs = [long]1420070400000   # 2015-01-01T00:00:00Z — the Discord snowflake epoch

function Get-SnowflakeCreatedMs {
    # createdMs = (id >> 22) + epoch. Parse and shift as [long]; an [int] cast would overflow.
    param([Parameter(Mandatory = $true)][string]$Id)
    $snowflake = [long]::Parse($Id)
    return ($snowflake -shr 22) + $script:DiscordEpochMs
}

function Test-SourceSettled {
    # Decide whether a source is settled, given the ids of the NON-BOT messages newer than the
    # source's watermark. The caller does the non-bot + after-watermark filtering (bot
    # identification differs by context — author.bot in the precheck, author.id == botUserId in
    # the SKILL). Returns $true/$false. Order-independent: "newest" = smallest age (largest id),
    # "oldest un-processed" = largest age (smallest id) — computed from ages, never array order.
    param(
        [string[]]$NonBotMessageIds,
        [long]$NowMs,
        [int]$SingleSec   = $script:SettleSingleSec,
        [int]$BurstSec    = $script:SettleBurstSec,
        [int]$MaxDeferSec = $script:SettleMaxDeferSec
    )

    $ids = @($NonBotMessageIds | Where-Object { $_ })   # drop nulls / empties
    $count = $ids.Count
    if ($count -eq 0) { return $false }                 # 0 non-bot messages → nothing to settle

    $ages = @($ids | ForEach-Object { $NowMs - (Get-SnowflakeCreatedMs $_) })
    $newestAgeMs = ($ages | Measure-Object -Minimum).Minimum   # newest message = smallest age
    $oldestAgeMs = ($ages | Measure-Object -Maximum).Maximum   # oldest message = largest age

    # Max-defer ceiling first: an old-enough oldest message settles the source regardless of churn.
    if ($oldestAgeMs -ge ([long]$MaxDeferSec * 1000)) { return $true }

    if ($count -eq 1) {
        return $newestAgeMs -ge ([long]$SingleSec * 1000)
    }
    # 2+ messages = a burst: wait the longer quiet window after the newest.
    return $newestAgeMs -ge ([long]$BurstSec * 1000)
}
