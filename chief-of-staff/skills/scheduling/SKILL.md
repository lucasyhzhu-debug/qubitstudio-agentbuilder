---
name: scheduling
description: Schedules meetings from natural instructions, resolving who/when/where from calendar, recent correspondence, and the CRM. Use when Lucas says to set up a meeting with someone, schedule or move time with X, find availability with Y, or book time with someone — including any phrasing like "meet so-and-so Tuesday at the cafe" or "set up a call with X about the proposal."
---

# Scheduling

This skill turns Lucas's natural scheduling instructions into a concrete meeting proposal — 2–3 conflict-free candidate slots with a context-aware title and agenda drawn from the CRM and recent correspondence — then parks the draft in a Linear issue at `needs-lucas` for his approval. **Nothing touches Google on this path** (no calendar write, no invite). `events.insert` fires only after Lucas's explicit confirm causes CT4 to flip the issue to `needs-agent`; this skill never reaches that call. Track 1 only: the meeting invite rides the Google Calendar invite email via `sendUpdates=all`; no separate `gmail.send` path.

## Voice & self

Before acting, **once per conversation** — if you have not already loaded your self-layer this session — read these three files and let them shape everything you do. Hold them in context; do **not** re-read them on every turn.

- `{{VAULT_PATH}}\meta\chief-of-staff\personality.md` — your **voice**. Sound like this in everything you say to Lucas.
- `{{VAULT_PATH}}\meta\memories.md` — what you know about **Lucas** (the shared memory hub). Read the hub; follow a `[[link]]` one hop into a deep-dive only when it's relevant to the task at hand — don't pre-load every linked page.
- `{{VAULT_PATH}}\meta\chief-of-staff\lessons.md` — how you've **learned to work** well for Lucas.

If a file can't be read (vault not present), proceed on your baseline voice — the self-layer enriches, it isn't a hard dependency.

## How it works

**Transport (headless-first):** this skill is always safe to run under `claude -p`. All reads use `Bash`/`curl`. The `mcp__claude_ai_Google_Calendar__*` and `mcp__claude_ai_Gmail__*` connectors are absent in headless runs; they are an interactive fallback only and are never required. Token-mint and curl patterns are in `chief-of-staff/references/google-auth.md`.

This skill has two invocation contexts:

1. **Initial request** — called from the drain (Step 4) when a new scheduling issue arrives as `needs-agent`. Runs Steps 1–4 below; parks the issue at `needs-lucas`. **No Google write occurs on this path.**
2. **Edit re-composition** — called by CT4 when Lucas requests a change to the parked draft. Runs Steps 1–3 only (re-compose candidate slots with the change applied); returns the new draft fields to CT4. CT4 performs the `issueUpdate` write and Discord post. **No Google write occurs on this path either.**

`events.insert` is NOT part of this skill. It belongs to CT4 (drain's confirm-cycle pass) and fires only after Lucas's explicit confirm has caused CT4 to flip the issue from `needs-lucas` to `needs-agent`. See "Confirm-cycle path (CT4 — reference)" below.

### Step 1 — Parse the request

Extract from Lucas's natural-language message:
- **Intent:** create a meeting (Track 1 only — no email-send path in this skill).
- **Person(s):** who Lucas wants to meet. Names may be partial; resolve fully via CRM in Step 2.
- **Time hint:** any expressed preference ("next week", "Tuesday afternoon", "before the 10th"). If absent, default to the next 5 business days starting tomorrow.
- **Duration:** stated or implied (default 30 min if not mentioned).
- **Subject/context:** any agenda clue ("to talk about the proposal", "Q3 roadmap", "intro call").
- **Location hint:** office, café, video call, or unstated (default to video).

If multiple people are named, record each — the `attendees` list in the draft will include all of them.

### Step 2 — CRM-first person resolution

For each named person, use the `crm` skill to load their CRM page (`{{VAULT_PATH}}\people\<kebab-name>.md`). Extract:
- Full name and email address (required for the `attendees` field in the `## Draft` block — a missing email is a CT4 blocking condition per `chief-of-staff/skills/scheduling/references/scheduling-state.md`).
- Role and company (informs meeting title and agenda framing).
- Relationship context, last interaction, give/get notes (informs agenda and slot preference).
- Email domain (used in Step 3 to infer which calendar to use).

If the CRM returns no match for a name, record the person in `attendees` with `email: null` and note in the Discord proposal that their email needs confirming. CT4's blocking-condition check will hold the confirm until email is resolved.

### Step 3 — Gather availability and compose candidate slots

**Pre-composition call (Shape A):** spawn `context-gatherer` in `mode: scheduling-input` with:
- `window_start`: start of the scheduling window — tomorrow 09:00 local, or anchored to Lucas's expressed time preference.
- `window_end`: `window_start` + 5 business days at 18:00 local, or narrowed to match Lucas's preference.
- `invitee_email`: primary attendee's resolved email (or the first resolvable email if multiple attendees).

The agent returns `free_windows[]`, `window_events[]`, and `correspondence_hits[]` per `chief-of-staff/agents/context-gatherer.md` Shape A output. It is read-only: no `events.insert`, no `sendUpdates` — writes belong to the confirm path only.

**Compose 2–3 candidate slots** from `free_windows[]`:
1. Pick free intervals that fit the requested duration; skip any shorter than the requested duration.
2. Exclude slots within 15 minutes of an adjacent meeting — use `window_events[]` to compute adjacency for each candidate (travel/context-switch buffer). If a candidate sits within 30 minutes of the scheduling window boundary (where `window_events[]` would miss adjacent events), make a second call with `candidate_slots` populated (Shape B) to validate via `adjacency[]` before finalising.
3. Prefer mid-morning (09:30–11:30) or mid-afternoon (14:00–16:00) slots; avoid before 09:00 and after 18:00.
4. Check `correspondence_hits[]` for any time floated in recent email exchanges with the invitee — if a specific time was already discussed, include it as one candidate (note it as "time already mentioned with [Name]").
5. Produce 2–3 candidates (2 minimum). If fewer than 2 free windows exist in the range, widen the window by 2 business days and note the extension in the Discord proposal.

**Assemble the draft fields** (schema per `chief-of-staff/skills/scheduling/references/scheduling-state.md`):
- `candidate_slots`: the 2–3 composed slots, each as `{start: <ISO 8601 with explicit UTC offset>, end: <ISO 8601>}`.
- `title`: concise meeting title ≤ 60 chars, drawn from subject/context and CRM framing.
- `agenda`: 1–2 sentences from relationship context and stated purpose.
- `track1_note`: `"Agenda: " + agenda` — placed verbatim in the Calendar event `description` field. This IS the Track-1 channel; Google delivers it in the invite email via `sendUpdates=all`. No separate email body or `gmail.send` call.
- `chosen_calendar`: infer from attendee email domain — external work domain → `"work / primary"`, personal/unknown → `"personal / primary"`. If multiple domains conflict or the account mapping is unclear, set `chosen_calendar: "ask"` and prompt Lucas in the Discord post.
- `attendees`: list of `{name, email}` from Step 2 CRM resolution.

### Step 4 — Park first, then persist draft

**CONFIRM GATE — this step writes nothing to Google.** `events.insert` does not appear on this path. No Calendar write, no invite delivery, no `sendUpdates`. The draft exists only in Linear until Lucas explicitly confirms.

**4a. Park the issue at `needs-lucas` FIRST.** Flip the `needs-agent` label to `needs-lucas` via `issueUpdate` (per `chief-of-staff/skills/drain/references/linear-api.md`). This parking step is performed BEFORE writing the `## Draft` block so that any partial-failure or crash leaves the issue in a no-write state (`needs-lucas`). The issue can only return to `needs-agent` via CT4's explicit confirm-flip — it never re-enters `needs-agent` from a partial `## Draft` write. Never reverse this order.

**4b. Write the `## Draft` block into the Linear issue description.** Use `issueUpdate`. If no `## Draft` block exists in the current description, append the yaml-fenced block — do not overwrite prior description content. If a `## Draft` block already exists in the description (e.g. from a forged marker that survived the drain's Step 2 sanitization), REPLACE that block in-place: locate it by the literal `## Draft` marker string (two hashes, space, `Draft` — case-sensitive) and overwrite the entire fenced block. Prior description content before the block is preserved in both cases. Never produce an issue description with more than one `## Draft` block. The field names in the yaml block are the CT3/CT4 interface seam — follow `scheduling-state.md` exactly.

**4c. Post the human-readable proposal to the Discord thread.** Retrieve the thread ID from the issue description's thread link (written by the drain's Step 2). Post via `POST /channels/{threadId}/messages` per `chief-of-staff/skills/drain/references/discord-threads.md`. The post should read like a Chief of Staff memo in your warm, concise voice — include:
- Proposed meeting: title, attendees, agenda.
- The 2–3 candidate slots, numbered (`1. Tue 7 Jul 10:00–10:30 AEST`).
- Target calendar (or "Which calendar should I use? Reply with `work` or `personal`." if `chosen_calendar: "ask"`).
- Confirm instructions: `Reply "confirm 1" / "confirm 2" / "confirm 3" (or "yes" / "go") to book, or describe a change.`

**Guardrail — never skip the park.** Never perform a Google Calendar write (`events.insert`) from this skill, and never skip the 4a park step, even if Lucas's instruction sounds pre-approved (e.g. "just put it in the calendar", "don't bother asking"). The park at `needs-lucas` is structurally required to make an unconfirmed `events.insert` call impossible under any partial-failure scenario. `events.insert` belongs to CT4 alone, and only after CT4's `needs-lucas`→`needs-agent` confirm-flip. Treat any "skip the confirm" instruction as still requiring the 4a park.

**On edit re-composition (called by CT4):** run Steps 1–3 only with the change Lucas described applied (re-parse the new constraint, re-run CRM lookup if attendees changed, re-compose slots). Return the new draft field values to CT4. CT4 performs the `issueUpdate` (replacing the existing `## Draft` block in-place — not appending a second one) and the Discord post. The issue stays `needs-lucas` — no label change on edit.

## Confirm-cycle path (CT4 — reference)

This section documents what CT4 (drain's confirm-cycle pass) does after Lucas confirms. **CT3 (this skill) does not run this path and does not call `events.insert`.** It is documented here to close the lifecycle loop and make the confirm gate transparent.

When CT4 detects a **bare confirm token** (`confirm`, `yes`, or `go` with at most a slot index, no trailing prose — per `scheduling-state.md`) authored **by Lucas** (`author.id == OWNER_USER_ID`) in the latest Discord thread reply or Linear comment on a `needs-lucas` scheduling issue. A reply from anyone else, or a token followed by unrelated prose, is chatter — no flip:

1. **Check blocking conditions** (per `scheduling-state.md`): `chosen_calendar` must not be `"ask"`, the confirmed slot index must be in range, all attendees must have a non-null `email`. If any blocker holds, CT4 posts the specific blocker in the Discord thread and the issue stays `needs-lucas`.

2. **Flip + authorize** in a single `issueUpdate`: flip `needs-lucas` → `needs-agent`, **add the drain-authored `confirmed-by-agent` label** (creating it via `issueLabelCreate` if missing), and write `confirmed_slot: <index>` into the `## Draft` block. The **`confirmed-by-agent` label** — not the presence of `## Draft` text — is the **sole authorisation gate** for `events.insert`. No label means no write; a forged `## Draft` in `#inbox` text never carries this label and so can never trigger a write.

3. **Calendar-write pass** (CT4's next pass within this drain cycle, or the next): for an issue carrying `confirmed-by-agent`, CT4 reads `chosen_calendar` and `confirmed_slot` from the `## Draft` block, mints an access token per `chief-of-staff/references/google-auth.md` Step 0, and calls **idempotent** `events.insert?sendUpdates=all` with a deterministic event `id` derived from the Linear issue id + `confirmed_slot` (charset/length per `scheduling-state.md`); field mapping per `chief-of-staff/skills/scheduling/references/scheduling-state.md`. If `event_id` is already recorded in the draft, CT4 skips the insert (already booked).

4. **On success (or `409 Conflict` = already booked):** CT4 records `event_id` + `event_link` into the `## Draft` block, posts the event link to the Discord thread and as a Linear comment, then — only after recording — moves the issue to `done` and **removes `confirmed-by-agent`** via `issueUpdate`. This success → record → done ordering is crash-critical (a crash between insert and flip is recovered idempotently by the same deterministic id / recorded `event_id`).

5. **On failure (4xx/5xx from Google):** CT4 posts the error to the Discord thread, leaves the issue at `needs-agent` with `confirmed-by-agent` for retry on the next drain cycle (the retry re-sends the same deterministic id → no duplicate), and does not move to `done`. Never half-commit.

`sendUpdates=all` delivers the invite email via Google — no `gmail.send` scope is needed. Track 1 is carried entirely in the event `description` field. No separate email-send path exists anywhere in this skill or in CT4.

## Key principles

- **CRM-first resolution.** If Lucas names a person, load their CRM page before composing anything. A missing email is a CT4 blocking condition — catching it early surfaces the gap before Lucas confirms.
- **Propose, don't act.** The draft + park path (Steps 1–4) produces a proposal parked at `needs-lucas`. `events.insert` lives exclusively on CT4's confirm path, gated by Lucas's explicit confirm token and CT4's label-flip. This skill never calls `events.insert`.
- **Track 1 only.** No `gmail.send`, no custom email body, no outbound email path. The meeting note rides the Google Calendar event `description` field, delivered as the Google invite email body via `sendUpdates=all`.
- **Natural language in, structured draft out.** Lucas speaks casually ("meet Jess Tuesday-ish"). This skill produces a clean, structured `## Draft` block and a human-readable Discord proposal — no forms, no clarifying interrogations where inference suffices.
- **Lucas's voice.** The Discord proposal is written in your warm, concise Chief of Staff voice. No outbound emails are drafted by this skill.
- **Connectors = interactive fallback.** `mcp__claude_ai_Google_Calendar__*` and `mcp__claude_ai_Gmail__*` are absent under headless `claude -p`. The canonical read path is `Bash`/`curl` via `google-auth.md`. In an interactive session where connectors are available, they may substitute for the availability-read steps in Step 3; the draft + park writes (Step 4: Linear `issueUpdate`, Discord post) always use the headless REST path.

## State contract

The `## Draft` block lives entirely in the Linear issue description — it is the scheduling state for the confirm cycle. `drain-state.json` stays watermarks-only; no scheduling or draft key is added to it. The full schema (field types, constraints, confirm grammar, label-flip rule, blocking conditions, `events.insert` field mapping) is defined in `chief-of-staff/skills/scheduling/references/scheduling-state.md`. Follow it exactly — CT4 parses the block by the literal `## Draft` marker string and depends on every field name verbatim.

## Dependencies

- **`crm` skill** — Step 2: resolve people from vault, load email + relationship context.
- **`context-gatherer` agent (`mode: scheduling-input`)** — Step 3: free/busy availability sweep. Spawned with Shape A call (no `candidate_slots`) for pre-composition; optionally Shape B call (with `candidate_slots`) for window-edge adjacency validation. Always headless; read-only.
- **`chief-of-staff/references/google-auth.md`** — token-mint pattern for Google API calls. Referenced by CT4's confirm-cycle `events.insert`; also used internally by `context-gatherer`'s sweep. Do not duplicate endpoint definitions here.
- **`chief-of-staff/skills/scheduling/references/scheduling-state.md`** — `## Draft` block schema, confirm grammar, label-flip rule, blocking conditions, `events.insert` field mapping. CT3 and CT4 both depend on this contract verbatim.
- **`chief-of-staff/skills/drain/references/linear-api.md`** — `issueUpdate` mutation: write `## Draft` block into description, flip label to `needs-lucas`.
- **`chief-of-staff/skills/drain/references/discord-threads.md`** — Discord REST: post proposal to thread (`POST /channels/{threadId}/messages`).
