# Settle window — when a source is ready to drain

A **source** is either an `#inbox` channel or an issue's Discord thread. The drain processes a
source only once it is **settled** — quiet long enough that a multi-message dictation burst (someone
thinking out loud across several messages) is complete. This is what lets the drain treat a burst as
**one accreting conversation** instead of acting mid-thought.

The rule below is the single contract. `scripts/settle-lib.ps1` (`Test-SourceSettled`) is the
executable copy used by `scripts/drain-precheck.ps1`; the drain SKILL applies the same rule where it
**gates** — Step 2 (an `#inbox` channel; watermark = the channel watermark) and Step 4 (an issue's
thread; watermark = **`lastActed`**, the act-boundary). Step 3 only *mirrors* replies to Linear and
does **not** gate — mirroring is always safe, and it advances `lastSeen`, which is exactly why Step 4's
gate must measure against `lastActed`, not the already-advanced `lastSeen`. Keep the thresholds here
and in `settle-lib.ps1` identical — change both together.

## The rule (count-based, non-bot-scoped)

Consider **only non-bot messages newer than the source's watermark** — the drain's own ack /
proposal / result posts never count and never reset the clock (otherwise the drain would keep itself
perpetually un-settled). Let their ages be measured from now:

| New non-bot messages | Settled when |
| --- | --- |
| **0** | never — nothing to do |
| **1** | the newest message's age ≥ **30s** |
| **2 or more** | the newest message's age ≥ **90s** |

**Max-defer ceiling.** Regardless of the above, if the **oldest un-processed** non-bot message's
age ≥ **600s**, the source is settled — a perpetually active thread cannot starve forever.

An un-settled source is **skipped with its watermark un-advanced**, so a later cycle handles it once
it goes quiet.

## Message age from the Discord snowflake

Every Discord message `id` is a snowflake encoding its creation time:

```
createdMs = ([long]id >> 22) + 1420070400000     # 1420070400000 = 2015-01-01T00:00:00Z
ageMs     = nowMs - createdMs
```

Parse the id as **Int64** (`[long]`) — snowflakes exceed Int32, and PowerShell 5.1 shifts `[long]`
correctly. Determine "newest" and "oldest" by **id / computed age**, never by array order: newest =
largest id (smallest age), oldest un-processed = smallest id after the watermark (largest age).

## Thresholds (authoritative copy)

`SettleSingleSec = 30` · `SettleBurstSec = 90` · `SettleMaxDeferSec = 600`. These live in
`scripts/settle-lib.ps1` and here; both files change in the same commit when tuned.
