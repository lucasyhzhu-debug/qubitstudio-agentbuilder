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
      "lastActed": "<lastActedCommentId>"
    }
  }
}
```

Rules:
- **Watermark** = the newest Discord message id the drain has turned into (or skipped past) for that channel. Step 1 of the cycle reads only messages with id > watermark; advance it after a successful sweep.
- **lastSeen** = newest thread reply already mirrored to the issue's comments; advance after mirroring.
- **lastActed** = newest issue comment the drain has acted on; advance after acting.
- All markers advance **only after the corresponding write succeeds** (crash-safe; no double-post).
- If the file is missing, treat all watermarks as "last 24h" on first run, then persist.
- If the file is present but **unparseable** (corrupt JSON), copy it to `drain-state.bak` and
  reinitialise from the 24h fallback — a corrupt state file must never wedge every future drain.
