# Pester tests for the adaptive settle window (drain v0.9.0, upgrade feature #6).
#
# Targets the Windows-bundled Pester 3.4 on PowerShell 5.1 — legacy `Should Be` assertion syntax
# (not the Pester 5 `Should -Be` form). Run from the repo root:
#   Invoke-Pester -Path chief-of-staff/scripts/tests/settle.Tests.ps1

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $here '..\settle-lib.ps1')

Describe 'Test-SourceSettled' {

    $epoch = [long]1420070400000
    # A fixed reference "now" so every case is deterministic (no wall-clock dependence).
    $now = [long]1700000000000

    # Build a snowflake id for a message posted $ageMs before $now.
    function New-SnowflakeId([long]$ageMs) {
        return [string](((($now - $ageMs) - $epoch)) -shl 22)
    }

    It 'is not settled with zero non-bot messages' {
        Test-SourceSettled -NonBotMessageIds @() -NowMs $now | Should Be $false
    }

    It 'treats null/empty ids as zero messages (not settled)' {
        Test-SourceSettled -NonBotMessageIds @($null, '') -NowMs $now | Should Be $false
    }

    It 'is not settled: one message younger than 30s' {
        $ids = @(New-SnowflakeId 5000)
        Test-SourceSettled -NonBotMessageIds $ids -NowMs $now | Should Be $false
    }

    It 'is settled: one message exactly 30s old (>= boundary)' {
        $ids = @(New-SnowflakeId 30000)
        Test-SourceSettled -NonBotMessageIds $ids -NowMs $now | Should Be $true
    }

    It 'is settled: one message older than 30s' {
        $ids = @(New-SnowflakeId 45000)
        Test-SourceSettled -NonBotMessageIds $ids -NowMs $now | Should Be $true
    }

    It 'is not settled: two messages, newest younger than 90s' {
        $ids = @((New-SnowflakeId 120000), (New-SnowflakeId 40000))
        Test-SourceSettled -NonBotMessageIds $ids -NowMs $now | Should Be $false
    }

    It 'is settled: two messages, newest exactly 90s old (>= boundary)' {
        $ids = @((New-SnowflakeId 200000), (New-SnowflakeId 90000))
        Test-SourceSettled -NonBotMessageIds $ids -NowMs $now | Should Be $true
    }

    It 'is settled: two messages, newest older than 90s' {
        $ids = @((New-SnowflakeId 300000), (New-SnowflakeId 100000))
        Test-SourceSettled -NonBotMessageIds $ids -NowMs $now | Should Be $true
    }

    It 'max-defer: oldest >= 600s settles even a busy source with a fresh newest' {
        $ids = @((New-SnowflakeId 700000), (New-SnowflakeId 300000), (New-SnowflakeId 5000))
        Test-SourceSettled -NonBotMessageIds $ids -NowMs $now | Should Be $true
    }

    It 'max-defer boundary: oldest exactly 600s settles' {
        $ids = @((New-SnowflakeId 600000), (New-SnowflakeId 5000))
        Test-SourceSettled -NonBotMessageIds $ids -NowMs $now | Should Be $true
    }

    It 'is order-independent (newest listed first yields the same verdict)' {
        $forward = @((New-SnowflakeId 120000), (New-SnowflakeId 40000))
        $reverse = @((New-SnowflakeId 40000), (New-SnowflakeId 120000))
        $a = Test-SourceSettled -NonBotMessageIds $forward -NowMs $now
        $b = Test-SourceSettled -NonBotMessageIds $reverse -NowMs $now
        $a | Should Be $b
        $a | Should Be $false
    }

    It 'honours custom thresholds passed by the caller' {
        $ids = @(New-SnowflakeId 15000)
        Test-SourceSettled -NonBotMessageIds $ids -NowMs $now -SingleSec 10 | Should Be $true
        Test-SourceSettled -NonBotMessageIds $ids -NowMs $now -SingleSec 20 | Should Be $false
    }
}

Describe 'Get-SnowflakeCreatedMs' {

    $epoch = [long]1420070400000

    It 'parses a real 19-digit snowflake as Int64 without overflow' {
        # A representative Discord snowflake (well beyond Int32.MaxValue).
        $created = Get-SnowflakeCreatedMs '1234567890123456789'
        $created -gt $epoch | Should Be $true
    }

    It 'round-trips a constructed id back to its creation time' {
        $now = [long]1700000000000
        $ageMs = [long]45000
        $id = [string](((($now - $ageMs) - $epoch)) -shl 22)
        Get-SnowflakeCreatedMs $id | Should Be ($now - $ageMs)
    }
}
