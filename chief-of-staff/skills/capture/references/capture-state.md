# Capture state — reconstruct-from-thread contract

Defines how DT2 (post-meeting capture skill) maintains working state and how CT4 (drain) detects stalled capture threads for quiet nudging. No new owned state file — the only durable marker is `capture_status` on the meeting's `meetings/` page. `drain-state.json` stays watermarks-only.

Consumers: **DT2** (writes `capture_status`, finalizes the page); **CT4 nudge pass** (reads `capture_status` + thread timestamps to decide whether to post a nudge).

---

## Reconstruct from thread

DT2 is **stateless between drain cycles**. On each invocation it reconstructs the current note in full:

1. Locate the meeting's Discord thread via the `discord_thread` URL in the meeting page's frontmatter. If the field is empty, DT2 cannot proceed — post a notice to Lucas and exit.
2. Fetch all messages in the thread from the Discord REST API (paginate if needed).
3. Filter to **Lucas-authored messages only** — exclude every message whose `author.id` matches `DISCORD_BOT_ID`. Bot messages are operational replies, not minutes content.
4. Concatenate the filtered messages in **chronological order** — this is the accumulated minutes buffer for this cycle.

**No per-message buffer file.** There is no sidecar file, no session-local state, no append log. The thread is the append-only source of truth; DT2 re-derives the full note on every cycle. A post-filed correction (a new Lucas message after finalize) is handled automatically: the next reconstruct cycle picks it up.

---

## `capture_status` frontmatter marker

`capture_status` is added to the meeting page frontmatter (`meetings/YYYY-MM-DD-<slug>.md`, as defined in `chief-of-staff/skills/briefing/references/meeting-page.md`) by DT2 on its first activation for that meeting.

### Augmented frontmatter shape

Phase B creates the page with `discord_thread: ""`. DT2 populates `discord_thread` and adds `capture_status` together in one `issueUpdate`-style patch to the vault page:

```yaml
---
date: YYYY-MM-DD
attendees:
  - "[[people/<kebab-name>]]"
calendar_event_id: <Google Calendar event id string>
account: <GOOGLE_ACCOUNTS label, e.g. "work">
discord_thread: "https://discord.com/channels/<guild>/<thread-id>"
capture_status: open
---
```

`capture_status` is always the last frontmatter field. DT2 writes it when wiring the thread; it stays on the page permanently.

### State machine

| Value | Meaning | Set by |
|-------|---------|--------|
| `open` | Capture is in progress — DT2 is accreting messages or a post-filed correction has arrived. | DT2 on first write; DT2 again when a new Lucas message arrives after a `filed` page. |
| `filed` | DT2 has finalized this page — all Phase-D sections written, CRM line appended, Linear todos created or patched. | DT2 on successful finalize. |

**Transition rules:**

- **→ `open`**: set when DT2 first wires the `discord_thread` on a page (field was empty) **or** when a new non-bot message is detected on a `filed` page (post-filed correction). A correction re-opens the note; the next drain cycle re-runs the full reconstruct + finalize.
- **→ `filed`**: set atomically with the finalize write — DT2 writes `## Minutes`, `## Synthesis`, `## Takeaways`, `## Todos`, appends the CRM interaction line, and creates/patches Linear todos in one pass, then sets `capture_status: filed`. If any step fails, DT2 does not set `filed` — the page stays `open` for retry.
- **No other transitions.** Do not delete `capture_status`; once present it persists.

**Correction semantics:** when `capture_status: filed` and a new Lucas message arrives, DT2 resets to `open` and on the next cycle re-runs reconstruct + finalize. The Phase-D sections (`## Minutes`, `## Synthesis`, `## Takeaways`, `## Todos`) are **overwritten, not appended** — the final finalized note is always a clean render of all thread messages. The CRM and Linear dedup rules (below) prevent double-writing.

---

## Finalize idempotency

DT2's finalize pass writes to two external places: vault `people/` stubs (CRM) and Linear issues (todos). Both are idempotent.

### CRM interaction line dedup (`people/` stubs)

Dedup key: the `[[meetings/<page-slug>]]` wikilink in the stub's body. Scan the file body for the substring `[[meetings/<page-slug>]]` to locate any existing line for this meeting.

**Three-way rule keyed on `[[meetings/<slug>]]` link presence and line shape:**

- **Seed line present** — the line containing `[[meetings/<slug>]]` matches the Phase B seed shape (contains `"first appeared as co-attendee"` and `[[meetings/<slug>]]`): **REPLACE** that seed line in place with the enriched Phase-D interaction line. Do not append a second line — upgrade the placeholder.
- **Enriched line present** — the line containing `[[meetings/<slug>]]` is already an enriched Phase-D interaction line (re-file or correction case): **PATCH** it in place with the latest content. Do not append.
- **No line present** — no line in the file references `[[meetings/<slug>]]`: **APPEND** the enriched interaction line.

**Phase B seed line shape** (for matching):

```
- YYYY-MM-DD — first appeared as co-attendee with Lucas at [[meetings/YYYY-MM-DD-<slug>]] (<event title>).
```

**Enriched Phase-D interaction line format:**

```
- YYYY-MM-DD — met at [[meetings/YYYY-MM-DD-<slug>]] (<event title>). <One-sentence takeaway from this meeting.>
```

The dedup key is the `[[meetings/<slug>]]` wikilink substring, not the full line text. The seed-vs-enriched distinction is by line shape: a seed line contains `"first appeared as co-attendee"`. This ensures that for first-time contacts, Phase B's stub-creation seed line is upgraded to the enriched Phase-D line rather than causing DT2 to skip writing the richer content.

### Linear todo dedup (meeting-link + normalized title)

Dedup key: **meeting sentinel + normalized title** (patch, not re-create).

Each todo produced by DT2 maps to a Linear issue in the `LAG` project. The issue description carries a sentinel line:

```
meeting: meetings/YYYY-MM-DD-<slug>
```

**Title normalization:** lowercase; collapse whitespace; strip leading/trailing whitespace; remove all punctuation except apostrophes within words and hyphens within words.

Before creating a Linear issue for a todo, DT2 searches existing open `LAG` issues for one matching **both**:
1. `meeting:` sentinel value = current meeting page slug.
2. Normalized issue title = normalized form of this action item.

| Match | Action |
|-------|--------|
| Both match | `issueUpdate` — patch description/state as needed. Do **not** create a duplicate. |
| No match | `issueCreate` — new issue with the sentinel in the description. |

On a post-filed correction that changes an action item, the sentinel-match finds the existing issue and patches it; changed items that no longer appear in the re-derived note are left as-is (do not auto-close — Lucas may have already acted).

---

## Quiet-nudge detection inputs

CT4's drain quiet-nudge pass reads these inputs to decide whether to post a nudge on an open capture thread.

### Input table

| Input | Source | Description |
|-------|--------|-------------|
| `capture_status` | Meeting page frontmatter | Only pages with `capture_status: open` are candidates. `filed` pages are skipped entirely. |
| `newest_non_bot_message_ts` | Discord thread — timestamp (UTC) of the most recent message whose `author.id` ≠ `DISCORD_BOT_ID` | Age anchor for the stale-thread check. Discord timestamps are UTC; compare in UTC. |
| `nudge_threshold_hours` | Constant — **48 hours** | If `now (UTC) − newest_non_bot_message_ts > 48 h` and `capture_status: open`, the thread is a nudge candidate. |
| `bot_last_message_flag` | Discord thread — whether the most recent message overall was posted by the bot | **Self-skip**: if the bot's message is newer than any Lucas message, CT4 does not nudge — the bot already posted a follow-up and the ball is in Lucas's court. |

### Self-skip rule (detail)

CT4 determines `newest_non_bot_message_ts` by scanning the thread backward:

1. Walk messages from newest to oldest.
2. Skip any message whose `author.id` = `DISCORD_BOT_ID`.
3. Use the timestamp of the first non-bot message encountered. This is `newest_non_bot_message_ts`.
4. If the bot's own message is chronologically newer than `newest_non_bot_message_ts`, set `bot_last_message_flag = true` → **do not nudge**.
5. If all messages in the thread are bot-authored (edge case: bot opened the thread but Lucas has not replied), skip nudging — there is no Lucas content to follow up on.

### Nudge preconditions (all must hold)

1. Meeting page exists and `capture_status: open`.
2. `newest_non_bot_message_ts` age exceeds 48 hours.
3. `bot_last_message_flag` is `false` (Lucas — not the bot — sent the last message).
4. CT4 has not already posted a nudge in this drain cycle for this thread (guard against double-post within one cycle).

CT4 posts the nudge to the **existing** Discord thread. Nudge content and phrasing are outside this contract's scope — see CT4's skill body.

---

## Implementation notes

- **`drain-state.json` stays watermarks-only.** Capture state lives entirely on the meeting page's `capture_status` field. Do not add a capture key to the drain watermarks object.
- **No Google Calendar or Gmail write in Phase D.** All DT2 writes are: vault `meetings/` page, vault `people/` stubs, Linear issues. Calendar and Gmail writes are Phase B / Phase C scope. This contract introduces no `events.insert` or `gmail.send` path.
- **Dictation split.** Lucas's voice messages / typed notes are tidied (transcription and grammar only) and placed in `## Minutes`. The agent's analysis of the discussion goes in `## Synthesis` as a separate attributed block. The two sections must not be merged. (DT2's SKILL body owns this split; this contract names the two sections only to confirm they are distinct.)
- **Vault git discipline.** When committing meeting pages or stubs, name files explicitly — never `git add -A` against the vault (`{{VAULT_PATH}}`). Example:
  ```powershell
  git -C "{{VAULT_PATH}}" add meetings/2026-06-30-product-sync.md people/sarah-chen.md
  git -C "{{VAULT_PATH}}" commit -m "cos: finalize capture 2026-06-30 product-sync"
  ```
