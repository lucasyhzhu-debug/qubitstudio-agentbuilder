# drain-state.json — CoS drain run state

Path: `{{VAULT_PATH}}/meta/chief-of-staff/drain-state.json` (gitignored — local runtime state).

```json
{
  "channels": {
    "<discordChannelId>": { "label": "ch:inbox", "watermark": "<lastProcessedMessageId>" }
  },
  "issues": {
    "<linearIssueId>": {
      "threadId": "<discordThreadId>",
      "lastSeen": "<lastMirroredThreadMessageId>",
      "lastActed": "<lastActedCommentId>",
      "lengthNudged": false
    }
  }
}
```

Rules:
- **Watermark** = the newest Discord message id the drain has turned into (or skipped past) for that channel. Step 1 of the cycle reads only messages with id > watermark; advance it after each issue-group commits — **once per committed issue-group**, never per message (Step 2 burst grouping is the crash barrier: a crash mid-run leaves only the un-committed groups "new" so a retry re-does just those, re-grouping their messages identically and never re-creating a filed issue).
- **lastSeen** = newest thread reply already mirrored to the issue's comments; advance after mirroring.
- **lastActed** = newest issue comment the drain has acted on; advance after acting. Step 4 uses it as the **new-vs-old boundary**: a comment whose id > `lastActed` is NEW since the drain last acted; everything at or before it is prior context (the drain has no memory between cycles — the thread is its memory).
- **lengthNudged** (per issue, default `false`) = whether the one-shot ~50-comment "start a fresh ticket?" nudge has been posted for this issue. Set `true` after posting so it never repeats.
- All markers advance **only after the corresponding write succeeds** (crash-safe; no double-post).
- If the file is missing, treat all watermarks as "last 24h" on first run, then persist.
- If the file is present but **unparseable** (corrupt JSON), copy it to `drain-state.bak` and
  reinitialise from the 24h fallback — a corrupt state file must never wedge every future drain.

## Issue `## Meta` block (wiki-entity linkage)

Separately from `drain-state.json`, the drain seeds a `## Meta` block into every Linear issue's
**description** (patched in place, never duplicated) so later cycles can reload the wiki pages an
issue touched:

```
## Meta
discord_thread: https://discord.com/channels/<guildId>/<threadId>
wiki_ref: people/<kebab-first-last>.md
wiki_ref: meetings/<slug>.md
```

- Seeded at issue creation with `discord_thread`. When a Step-4 route resolves a wiki page
  (`crm` → `people/<kebab-first-last>.md`, `capture` → the `meetings/` page, `wiki-brain:ingest`
  → whatever it filed), append a `wiki_ref` line.
- On later cycles each `wiki_ref` is loaded as extra context — **only after vault-validation**: the
  path must resolve under `{{VAULT_PATH}}` and is **rejected** (skipped, never read) if it contains
  `..`, an absolute path, a drive letter, or a UNC prefix. Wiki context enriches; a missing/moved
  page is skipped silently — it is never a hard dependency.
