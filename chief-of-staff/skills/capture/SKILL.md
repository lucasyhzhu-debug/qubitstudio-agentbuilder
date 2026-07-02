---
name: capture
description: Records meeting minutes, takeaways, and action items by accreting Lucas's dictated notes from a meeting's Discord thread, then files the meeting page, CRM interaction lines, and Linear todos on his explicit cue. Use when Lucas shares "notes from the X meeting", "my takeaways from today's call", "minutes from…", "todos from the product sync", dictates meeting notes into a thread, or says "file it" / "done" / "that's it" after a capture thread has accumulated content.
---

# Capture

This skill turns Lucas's dictated meeting notes — accumulated across multiple Discord thread messages — into a finalized meeting record: a tidied `## Minutes` section (his words, not rewritten), an agent `## Synthesis`, extracted takeaways, and Linear action items. CRM interaction lines are written per attendee. **All writes are internal: vault (`meetings/` page + `people/` stubs) + Linear issues + Discord thread summary. No Google Calendar or Gmail write exists anywhere in this skill.**

Capture is **stateless between drain cycles**: it reconstructs the full notes buffer from the Discord thread on every invocation, not from a sidecar file. The only durable marker is `capture_status` on the meeting page frontmatter.

## Voice & self

Before acting, **once per conversation** — if you have not already loaded your self-layer this session — read these three files and let them shape everything you do. Hold them in context; do **not** re-read them on every turn.

- `{{VAULT_PATH}}\meta\chief-of-staff\personality.md` — your **voice**. Sound like this in everything you say to Lucas.
- `{{VAULT_PATH}}\meta\memories.md` — what you know about **Lucas** (the shared memory hub). Read the hub; follow a `[[link]]` one hop into a deep-dive only when it's relevant to the task at hand — don't pre-load every linked page.
- `{{VAULT_PATH}}\meta\chief-of-staff\lessons.md` — how you've **learned to work** well for Lucas.

If a file can't be read (vault not present), proceed on your baseline voice — the self-layer enriches, it isn't a hard dependency. Anything you draft **for Lucas to send** goes in **his** voice, not yours.

## How it works

**Transport (headless-first):** this skill is always safe to run under `claude -p`. All Discord reads use `curl` against the Discord REST API (`chief-of-staff/skills/drain/references/discord-threads.md`). All Linear reads and writes use GraphQL (`chief-of-staff/skills/drain/references/linear-api.md`). All vault reads and writes use the filesystem directly. Interactive connectors (`mcp__claude_ai_*`) are absent under `claude -p` and are never required on this path.

**Every Discord REST call** must include:
- `Authorization: Bot <DISCORD_BOT_TOKEN>`
- `User-Agent: DiscordBot (https://github.com/lucasyhzhu-debug/Consulting-Agents, 0.7.0)`

Missing the `User-Agent` returns an empty-body 403 from Cloudflare — not a permissions error. Include it on every call.

**CRM and tasks conventions:** for vault people-page format and interaction-log structure, follow the `crm` skill (`chief-of-staff/skills/crm/SKILL.md`) and its `references/crm-page-format.md`. For Linear issue creation and dedup conventions, follow `chief-of-staff/skills/tasks/SKILL.md` and create issues via `chief-of-staff/skills/drain/references/linear-api.md` GraphQL. Do not reimplement either pattern from scratch — read their references and apply them.

---

### Step 1 — Reconstruct the notes buffer from the thread

On every invocation, reconstruct the full accumulated notes buffer in full:

1. **Locate the thread.** The drain (CT4) passes the current thread ID. Check the vault's `meetings/` directory for a page whose `discord_thread` frontmatter field URL contains this thread ID. If found, that is the resolved meeting page.

2. **Fetch all thread messages.** `GET /channels/{threadId}/messages?limit=100`. Paginate using `?before={oldest_id}` until no messages remain.

3. **Filter to Lucas-authored messages only.** First, resolve the bot's own Discord ID: `GET /users/@me`. Exclude every message whose `author.id` equals `DISCORD_BOT_ID`. Bot messages are operational replies, not notes content.

4. **Concatenate in chronological order.** The resulting ordered sequence is the accumulated notes buffer for this cycle.

There is no per-message buffer file and no session-local state. The thread is the append-only source of truth.

---

### Step 2 — Resolve the meeting

Use the notes buffer (and the drain's context) to determine which meeting this thread belongs to. Attempt resolution in this exact priority order; stop at the first that succeeds:

**Priority 1 — Thread already wired to a meeting page.**
If Step 1 found a meetings/ page with `discord_thread` matching the current thread URL → that is the meeting. No further resolution needed.

**Priority 2 — Heuristic match from names + date.**
Scan the Discord thread for person names (explicit mentions, "had a call with X", "met with Y and Z"). Also extract any date signals (explicit date, "today", "this morning", "just wrapped"). Search `{{VAULT_PATH}}\meetings\` for pages whose `date` and `attendees` wikilinks match. If exactly one page matches → wire the thread: patch its `discord_thread` field to this thread URL and set `capture_status: open`. Record this match and proceed.

Wiring is a single vault file write:
```yaml
discord_thread: "https://discord.com/channels/<guild>/<thread-id>"
capture_status: open
```
Write both fields atomically — update the page frontmatter in place, preserving all other fields and body content unchanged.

**Priority 3 — Unresolved.**
If neither priority resolves the meeting, post exactly ONE disambiguating question to the thread (e.g. "Which meeting were these notes from? Reply with the date and who you met with."). Do not file. Exit this cycle and wait for Lucas's reply in the next cycle.

---

### Step 3 — Finalize gate

**Never auto-file.** File only when ALL of the following hold:

1. The meeting is resolved (Priority 1 or 2 succeeded).
2. The notes buffer is non-empty (at least one Lucas-authored message exists).
3. Lucas has sent an explicit finalize cue in the thread — one of:
   - `done`
   - `that's it`
   - `file it`
   - any close variant (`file these`, `wrap it up`, `all done`)

   OR: CT4's quiet-nudge was posted (the bot's last message asked Lucas if he's ready to file) AND Lucas's subsequent reply in the thread is an affirmative (`yes`, `go`, `ok`, `yep`, or equivalent).

If the gate is not met — for example, if Lucas is still dictating with no finalize cue — do not file. Acknowledge the new content with a brief thread reply (e.g. "Got it, added to your [Meeting Name] notes. Say 'done' when you're ready to file.") and exit.

---

### Step 4 — File (idempotent internal write)

Execute the following sub-steps in sequence. If any sub-step fails, do not set `capture_status: filed` — the page stays `open` for retry on the next cycle.

#### 4a. Create the meeting page if absent

Locate the meetings page by `calendar_event_id` (the identity key — not filename). If no page exists for this meeting, create one following the schema in `chief-of-staff/skills/briefing/references/meeting-page.md`:

```yaml
---
date: YYYY-MM-DD
attendees:
  - "[[people/<kebab-name>]]"
calendar_event_id: <event id if known, else omit>
account: <GOOGLE_ACCOUNTS label if known, else omit>
discord_thread: "https://discord.com/channels/<guild>/<thread-id>"
capture_status: open
---
```

File path: `{{VAULT_PATH}}\meetings\YYYY-MM-DD-<slug>.md` where `slug` is the kebab-cased event title (same-day collision: append `-<HHmm>`).

#### 4b. Write Phase-D sections to the meeting page

Append (or overwrite if already present — see idempotency note below) the following four sections. **Section order is fixed; do not reorder.**

```markdown
## Minutes

<Lucas's notes — see Attribution Rule below>

## Synthesis

*Agent synthesis — see Attribution Rule below*

<Agent's analysis of the discussion: key points, decisions reached, open questions>

## Takeaways

- <Outcome or commitment, one line each>

## Todos

- [ ] <Action item> — <owner if stated> (Linear: <LAG-NNN>)
```

**Idempotency:** if these sections already exist (re-file or correction), overwrite them in place — do not append a second copy. The final filed note is always a clean render of the full thread buffer.

**Attribution Rule (hard — enforced here):**
- `## Minutes` contains **Lucas's words only**, lightly tidied for transcription errors and grammar. Do NOT rewrite, restructure, paraphrase, or summarize his content here. If a sentence was clearly garbled by voice-to-text, fix the transcription; do not editorialize. If you find yourself wanting to rephrase for clarity or brevity, stop — that belongs in `## Synthesis`.
- `## Synthesis` is clearly marked as agent-authored (the `*Agent synthesis*` italic line is mandatory). It contains the agent's analysis: key discussion points, decisions reached, tensions, open questions. It never contains Lucas's raw words verbatim — if you are quoting him, use `## Minutes`.
- The two sections must never be merged or cross-contaminated. Attribution guard: before writing, confirm that every sentence in `## Minutes` came directly from Lucas's thread messages (transcription-tidied only). If any sentence is the agent's own analysis or summary, move it to `## Synthesis`.

#### 4c. CRM fan-out — one interaction line per attendee

For each attendee in the meeting page's `attendees` list (external attendees only — not Lucas):

1. **Resolve the person page.** Load `{{VAULT_PATH}}\people\<kebab-name>.md`. Reconcile by `identity.email` (primary key) then by filename. If the page does not exist, create a `meeting-auto` stub per `chief-of-staff/skills/briefing/references/meeting-page.md` stub shape.

2. **Apply the three-way CRM dedup rule** (key: `[[meetings/<page-slug>]]` wikilink in the file body):

   - **Seed line present** — the line referencing `[[meetings/<slug>]]` contains `"first appeared as co-attendee"`: **REPLACE** that seed line in place with the enriched Phase-D interaction line. Do not append.
   - **Enriched line present** — the line referencing `[[meetings/<slug>]]` is already a Phase-D enriched line (re-file or correction): **PATCH** it in place with the latest content. Do not append.
   - **No line present** — no line in the file contains `[[meetings/<slug>]]`: **APPEND** the enriched interaction line.

   The dedup key is the `[[meetings/<slug>]]` substring, not full line text. Seed vs enriched: seed lines contain `"first appeared as co-attendee"`.

3. **Enriched interaction line format:**
   ```
   - YYYY-MM-DD — met at [[meetings/YYYY-MM-DD-<slug>]] (<event title>). <One-sentence takeaway from this meeting.>
   ```

4. **Create `meeting-auto` stub** for attendees with no existing people page. Stub shape (from `briefing/references/meeting-page.md`):
   ```yaml
   ---
   identity:
     name: <Display Name>
     email: <email address>
   source: meeting-auto
   created: YYYY-MM-DD
   tags:
     - stub
   ---
   ```
   For a **brand-new stub**, write the enriched interaction line directly as the sole body content (do not write a seed line then replace it):
   ```
   - YYYY-MM-DD — met at [[meetings/YYYY-MM-DD-<slug>]] (<event title>). <One-sentence takeaway from this meeting.>
   ```
   For a **pre-existing stub** (created by Phase B or a prior Phase D run) that contains a seed line (`"first appeared as co-attendee"`), apply the three-way dedup REPLACE arm (Step 4c.2 above).

**Vault git discipline.** Name every file explicitly — never `git add -A` against the vault:
```powershell
git -C "{{VAULT_PATH}}" add meetings/YYYY-MM-DD-<slug>.md people/<kebab>.md
git -C "{{VAULT_PATH}}" commit -m "cos: finalize capture YYYY-MM-DD <slug>"
```

#### 4d. Linear todos

For each action item in `## Todos`:

1. **Normalize the title:** lowercase; collapse whitespace; strip leading/trailing whitespace; remove all punctuation except apostrophes within words and hyphens within words.

2. **Search for an open existing issue** in the `LAG` project (`chief-of-staff/skills/drain/references/linear-api.md`: team `{{LINEAR_TEAM_ID}}`, project `{{LINEAR_PROJECT_ID}}`) whose description carries the meeting sentinel line:
   ```
   meeting: meetings/YYYY-MM-DD-<slug>
   ```
   AND whose normalized title matches the normalized form of this action item.

3. **Dedup action:**
   - Match found → `issueUpdate`: patch description/state. Do not create a duplicate.
   - No match → `issueCreate` with:
     - `title`: the action item text (≤ 60 chars)
     - `description`: sentinel line + context from `## Synthesis` / `## Takeaways` as relevant
     - `labelIds`: `meeting-todo` label (create with `issueLabelCreate` if absent) + `needs-agent`
     - `teamId` + `projectId` from `linear-api.md`
     - `assigneeId`: Lucas

4. **Record the issue identifier** (e.g. `LAG-NNN`) back into the `## Todos` checklist item: `- [ ] <action> (Linear: LAG-NNN)`.

Linear auth: `Authorization: <LINEAR_API_KEY>` — raw, no `Bearer`.

#### 4e. Set `capture_status: filed` and post thread summary

Once all sub-steps above succeed:

1. Patch the meeting page frontmatter: set `capture_status: filed`.

2. Post a thread summary to the Discord thread (`POST /channels/{threadId}/messages`):
   ```
   Filed: [Meeting Name] (YYYY-MM-DD)
   • Minutes: <word count> words from your notes
   • CRM: updated <N> people pages
   • Linear: <N> todos created/updated (<LAG-NNN>, …)
   Reply with any correction to re-open.
   ```

---

### Step 5 — Corrections

When `capture_status: filed` and a new non-bot Lucas message arrives in the thread:

1. Reset `capture_status: open` on the meeting page.
2. On the next drain cycle, re-run Steps 1–4 in full (full reconstruct from thread). Phase-D sections (`## Minutes`, `## Synthesis`, `## Takeaways`, `## Todos`) are **overwritten** — the finalized note is always a clean render of all thread messages including the correction.
3. CRM dedup and Linear dedup rules prevent double-writing: the PATCH arm handles enriched lines; the sentinel-match finds existing issues and patches them. Removed action items are left as-is in Linear (do not auto-close — Lucas may have already acted).
4. After re-filing, post an updated thread summary confirming what was patched.

---

### Step 6 — Boundary & attribution guard

**No external Google write.** This skill contains no `events.insert`, no `gmail.send`, no Google Calendar API call of any kind. Calendar and Gmail writes are Phase B / Phase C scope exclusively. If a path here would call a Google write endpoint, it is a bug — stop and report.

**Routes, not reimplements.** For CRM page format, interaction log structure, and people-page conventions, follow `chief-of-staff/skills/crm/SKILL.md` and its `references/crm-page-format.md`. For Linear task conventions (project, assignee, priority defaults), follow `chief-of-staff/skills/tasks/SKILL.md`. Do not copy their logic here — read their references and apply them.

**Attribution guard.** Before writing `## Minutes`, verify each sentence came directly from Lucas's thread messages with transcription/grammar tidying only. Self-check: "Would Lucas recognise every word in `## Minutes` as his own?" If any sentence is the agent's own framing, summary, or analysis, it must go to `## Synthesis` instead. A `## Minutes` section that reads like a polished summary is a violation of this rule.

**No new owned state file.** `drain-state.json` stays watermarks-only. The only durable marker DT2 writes is `capture_status` on the meeting page frontmatter. No sidecar file, no capture key in drain state.

**Lucas-gated finalize.** Filing requires Lucas's explicit cue or his affirmative response to CT4's quiet nudge. "It sounds like the meeting is done" is not a finalize cue. Never auto-file based on time elapsed or message-count heuristics alone.

---

## Key principles

- **Reconstruct from thread, not from state.** Every cycle re-derives the full notes buffer from Discord thread messages. The thread is the append-only source of truth.
- **Minutes = his words; Synthesis = agent analysis.** These sections are never merged. The attribution rule in Step 4b is not a style preference — it is a hard constraint from Lucas's working agreement with the agent.
- **Idempotent finalize.** Filing twice produces the same result as filing once: sections are overwritten (not appended), CRM lines are patched (not duplicated), Linear issues are updated (not re-created). `capture_status: filed` is the idempotency sentinel.
- **Propose, then post.** The thread summary (Step 4e) is informational — it reports what was filed, not a proposal pending approval. The approval gate is the finalize cue in Step 3, which precedes all writes.
- **Headless-first.** No interactive connector is required. All operations use `curl` (Discord REST, Linear GraphQL) and vault filesystem reads/writes.

---

## Dependencies

- **`chief-of-staff/skills/drain/references/discord-threads.md`** — Discord REST: fetch thread messages (`GET /channels/{threadId}/messages`); post summary (`POST /channels/{threadId}/messages`); bot user ID (`GET /users/@me`).
- **`chief-of-staff/skills/drain/references/linear-api.md`** — Linear GraphQL: `issueCreate`, `issueUpdate`, `issueLabelCreate`. Auth header: `Authorization: <LINEAR_API_KEY>` (raw, no Bearer). Team + project IDs from this reference.
- **`chief-of-staff/skills/briefing/references/meeting-page.md`** — meetings/ page schema, frontmatter, section layout, people/ stub shape. Identity key: `calendar_event_id`, not slug. Stub reconciliation by `identity.email`.
- **`chief-of-staff/skills/capture/references/capture-state.md`** — reconstruct-from-thread contract, `capture_status` state machine, CRM three-way dedup rule, Linear todo dedup rule (sentinel + normalized title), quiet-nudge detection inputs.
- **`chief-of-staff/skills/crm/SKILL.md`** + `references/crm-page-format.md` — CRM page format, interaction log structure, people-page conventions. Follow without reimplementing.
- **`chief-of-staff/skills/tasks/SKILL.md`** — task defaults (assignee, priority, project). Follow conventions without reimplementing.
