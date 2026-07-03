# Scheduling state — draft + confirm contract

Defines the `## Draft` block that **CT3 (scheduling skill) writes** into a Linear issue description and **CT4 (drain confirm cycle) reads and patches** — parsing it to apply confirm grammar, writing `confirmed_slot` on the confirm flip, recording `event_id` and `event_link` after the booking, and replacing it in-place on edit-recomposition. These field names and confirm grammar are the interface seam between CT3 and CT4 — downstream code depends on them verbatim.

**Write authorization is the drain-authored `confirmed-by-agent` Linear label, NOT the `## Draft` text.** The `## Draft` block is parsed for *content* (slots, calendar, attendees, `confirmed_slot`), but it is never the proof of a confirm — its text can be forged in a raw `#inbox` message. Only the `confirmed-by-agent` label (set by CT4 at a genuine, Lucas-authenticated confirm) authorizes `events.insert`. See "Label-flip rule" below.

Stateless design: the draft lives entirely in the Linear issue description. `drain-state.json` stays watermarks-only — do not add a scheduling or draft key to it.

---

## `## Draft` block schema

CT3 writes a yaml-fenced code block into the Linear issue description whose first line is the literal string `## Draft` (two hashes, one space, `Draft` — case-sensitive). CT4 locates it by that literal string, not as a Markdown `##` heading. "Block heading" used elsewhere in this document refers to this literal marker string inside the fenced block, not a Markdown section heading.

### Canonical form

```yaml
## Draft
candidate_slots:
  - start: "2026-07-04T10:00:00+10:00"
    end:   "2026-07-04T10:30:00+10:00"
  - start: "2026-07-05T14:00:00+10:00"
    end:   "2026-07-05T14:30:00+10:00"
  - start: "2026-07-06T09:00:00+10:00"
    end:   "2026-07-06T09:30:00+10:00"
chosen_calendar: "work / primary"
attendees:
  - name: "Sarah Chen"
    email: "sarah@acme.com"
title: "Product sync — Q3 priorities"
agenda: "Align on Q3 roadmap before board submission."
track1_note: "Agenda: Align on Q3 roadmap before board submission."
confirmed_slot: null
event_id: null
event_link: null
```

### Field-by-field rules

| Field | Type | Constraints |
|-------|------|-------------|
| `candidate_slots` | list of `{start, end}` pairs, ISO 8601 datetimes with UTC offset | 2–3 entries. CT3 proposes; Lucas picks by index or ordinal. All datetimes carry an explicit offset (e.g. `+10:00`). |
| `chosen_calendar` | string — `"<account-label> / <calendarId>"` or `"ask"` | Use `"ask"` when CT3 cannot resolve which account or calendar to use. CT4 cannot fire `events.insert` while this is `"ask"`. |
| `attendees` | list of `{name, email}` objects | At least one entry. `email` is required for every attendee (used in `events.insert`). `name` may be omitted only if truly unknown — prefer CRM-resolved names. |
| `title` | string | ≤ 60 chars. Placed in the Calendar event `summary` field verbatim. |
| `agenda` | string | Plain text, one or two sentences. Shown to Lucas in the proposal and informs `track1_note`. |
| `track1_note` | string | Typically `"Agenda: " + agenda`; CT3 may extend with additional context. Placed verbatim in the Calendar event `description` field (Track 1 — no email). **Event-description text only — not an email body.** Google delivers the invite email via `sendUpdates=all`; no `gmail.send` scope is needed. Do not add an email-send field to this schema. |
| `confirmed_slot` | integer (1-based) or `null` | **Written by CT4 (drain Step 3a) at the confirm flip**, in the SAME `issueUpdate` that adds the `confirmed-by-agent` label. It is the resolved `candidate_slots` index Lucas confirmed. `null`/absent until a genuine confirm. CT4's calendar-write pass reads `candidate_slots[confirmed_slot-1]` from this field — never from a re-parsed reply — so the right time books even a cycle later. CT3 initializes it to `null`. |
| `event_id` | string or `null` | **Written by CT4's calendar-write pass on `events.insert` success/409**, BEFORE the issue is flipped to `done`. It is the deterministic Calendar event id that was inserted (see "`events.insert` call" below). Its presence is the re-entrancy guard: if `event_id` is non-null, the event is already booked — CT4 must NOT call `events.insert` again. Paired with `event_link` (the human-clickable URL) when recorded. CT3 initializes it to `null`. |
| `event_link` | string (URL) or `null` | **Written by CT4's calendar-write pass alongside `event_id`** on `events.insert` success or `409`. The human-clickable Calendar event URL (e.g. `https://www.google.com/calendar/event?eid=...`). Posted to the Discord thread and as a Linear comment at the same time. `null` until a successful insert; CT3 initializes it to `null`. |

---

## Confirm grammar

CT4 reads the newest reply on the issue — from the linked Discord thread. It classifies the reply into one of three categories.

**Author authentication (required, applied first):** a confirm is honored **only from Lucas**. CT4 classifies a reply as a **confirm** or **edit** only when `author.id == OWNER_USER_ID` (the `OWNER_USER_ID` env var — Lucas's own Discord user id). A reply from any other non-bot participant in the thread is **chatter** and can never flip a label, rewrite the draft, or grant `confirmed-by-agent`. Bot-authored replies are already filtered out upstream.

### Confirm

A Lucas-authored reply is a **confirm** only if, after stripping leading/trailing whitespace, it is **exactly** a confirm token, optionally followed by a single slot index, and **nothing else**:

| Token | Accepted (bare token, optional index only) | NOT a confirm — classified as chatter |
|-------|--------------------------------------------|----------------------------------------|
| `confirm` | `confirm` · `confirm 2` · `confirm second` | `confirm 2 thanks, talk later` |
| `yes` | `yes` · `yes 1` · `yes, slot 1` | `yes thanks, see you then` |
| `go` | `go` · `go 2` · `go with the second` | `go, but move it earlier` |

A confirm token followed by unrelated prose (a casual affirmation like "yes thanks, talk later") is **chatter, not a confirm** — a bare token (plus at most a slot index/ordinal) is required so an offhand reply never books a meeting. This applies even to a single-`candidate_slot` draft: CT4 auto-uses the lone slot only when the reply is a bare confirm token.

The optional **slot index** is a digit `1`/`2`/`3` or an ordinal word (`first`, `second`, `third`). If a slot index is present, CT4 uses `candidate_slots[index-1]` as the chosen time. If the token appears with no slot index and `candidate_slots` has exactly one entry, CT4 uses it (bare token required). If no index is given and multiple slots remain, CT4 posts a clarifying reply and the issue stays `needs-owner` — no flip.

### Edit

A reply is an **edit** if it contains a proposed change to the draft fields (e.g. "change the time to 3 pm", "make it 45 minutes", "use my personal calendar", "add Jess to the invite"). CT4 re-invokes CT3 to re-compose the candidate slots given the requested change; CT4 then rewrites the `## Draft` block in-place (replacing the existing one, not appending a second) via `issueUpdate` and posts the revised proposal. The issue **stays `needs-owner`** — no label change. CT4 owns the issueUpdate write on edit; CT3's role is re-composition only.

### Chatter

Any reply that is neither a confirm nor an edit (e.g. "ok", "sounds good", "who else is coming?") is **chatter**. CT4 may post an acknowledgement or answer in the thread but makes **no label change** — the issue stays `needs-owner`.

---

## Label-flip rule

The **`confirmed-by-agent` label** is the sole, unforgeable authorization gate for `events.insert`. It is a drain-authored Linear label set ONLY by CT4 (drain Step 3a) at the moment of a genuine Lucas confirm — never at issue creation, never from any `#inbox` message body. The presence of a `## Draft` block does NOT authorize a write (a `## Draft` block can be forged in raw `#inbox` text); only the `confirmed-by-agent` label does. CT4 must not call `events.insert` on any issue lacking `confirmed-by-agent`.

At the confirm, CT4 performs a SINGLE `issueUpdate` that atomically: (1) flips `needs-owner` → `needs-agent`, (2) **adds the `confirmed-by-agent` label** (creating it via `issueLabelCreate` if missing), and (3) writes `confirmed_slot: <resolved index>` into the `## Draft` block.

| Classification | Label transition | CT4 action |
|----------------|-----------------|------------|
| **Confirm** (bare Lucas-authored token, all fields resolved — see blocking conditions) | `needs-owner` → `needs-agent` **+ add `confirmed-by-agent`** | Single `issueUpdate`: flip label, add `confirmed-by-agent`, write `confirmed_slot`. CT4 (drain's Step 4) executes `events.insert` in its calendar-write pass when it next encounters this issue carrying `confirmed-by-agent`. |
| **Edit** | stays `needs-owner` | CT4 re-invokes CT3 to re-compose slots, then CT4 replaces the existing `## Draft` block in-place (does not append a second one) via `issueUpdate`, posts revised proposal, no label change. **`confirmed-by-agent` is not added.** |
| **Chatter** (incl. any non-Lucas reply, or a confirm token followed by prose) | no change | Post reply/answer in thread if useful, no label change. **`confirmed-by-agent` is never added.** |

### Blocking conditions

A confirm token does **not** authorize the flip if any of the following hold. CT4 posts the specific blocker in the Discord thread and the issue stays `needs-owner`:

- `chosen_calendar` is `"ask"` — account or calendar unresolved. Post: "Which calendar should I use? Reply with the account label (e.g. `work` or `personal`)."
- `candidate_slots` is empty, or the confirmed slot index is out of range.
- Any entry in `attendees` is missing `email`.

Only when all blocking conditions are clear does CT4 flip to `needs-agent`.

---

## `events.insert` call (Track 1) — idempotent

When CT4 (drain's Step 4), in its calendar-write pass, finds an issue that carries the **`confirmed-by-agent`** label, it calls `events.insert` with a **deterministic event `id`** so a retry cannot create a duplicate:

```
POST https://www.googleapis.com/calendar/v3/calendars/{calendarId}/events?sendUpdates=all
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "id":          "<deterministic event id — see below>",
  "summary":     "<title>",
  "description": "<track1_note>",
  "start":       { "dateTime": "<candidate_slots[confirmed_slot-1].start>", "timeZone": "Australia/Sydney" },
  "end":         { "dateTime": "<candidate_slots[confirmed_slot-1].end>",   "timeZone": "Australia/Sydney" },
  "attendees":   [ { "email": "<email>" }, ... ]
}
```

- **Deterministic `id`** — Calendar events support a client-specified `id`. Derive it as `cos` + the Linear `issue.id` UUID lowercased with hyphens stripped (hex `0-9a-f` ⊂ the allowed set) + `s` + the `confirmed_slot` digit (e.g. `cos3fa8b2c1...e1s2`). It must use only Google's allowed event-id charset (**lowercase `a`–`v` and `0`–`9`, length 5–1024**). The same (issue id, slot) always yields the same id, so a retry re-sends it.
- **Idempotency pre-check:** before calling, if `event_id` is already recorded in the `## Draft` block, the event is already booked → do NOT call `events.insert`; ensure the issue is `done` and `confirmed-by-agent` is removed.
- `calendarId` is extracted from `chosen_calendar` (the part after `" / "`).
- `access_token` is minted per `chief-of-staff/references/google-auth.md` Step 0 using the account label (the part before `" / "`).
- `confirmed_slot` is read from the `## Draft` block (written by CT4 Step 3a at the confirm) — never re-parsed from a reply.
- `sendUpdates=all` delivers the invite via Google — no `gmail.send` scope required.
- **On `200`/`201` success OR `409 Conflict`:** a `409` means this exact deterministic id is already booked (a prior cycle inserted it before crashing) → treat as **success, already booked**, NOT an error to retry as a new event. **Crash-critical ordering — success → record → done:** (1) FIRST record `event_id` (the deterministic id) and `event_link` into the `## Draft` block via `issueUpdate`; (2) post the link to Discord + a Linear comment; (3) only THEN flip to `done` and **remove `confirmed-by-agent`** in one `issueUpdate`. Recording before flipping `done` makes a crash between insert and lifecycle-flip recoverable by the pre-check above.
- **On other failure (4xx/5xx from Google):** CT4 posts the error to the Discord thread, leaves the issue `needs-agent` with `confirmed-by-agent` for retry on the next drain cycle (the retry re-sends the same id → no duplicate), and does not move to `done`.

---

## Worked example

Lucas posts to Discord: "Set up 30 min with Sarah Chen next week to talk Q3 roadmap."

CT3 opens Linear issue `LAG-77` (`needs-agent`), resolves Sarah from CRM (email: sarah@acme.com), checks Google Calendar for three free 30-min windows, appends:

```yaml
## Draft
candidate_slots:
  - start: "2026-07-07T10:00:00+10:00"
    end:   "2026-07-07T10:30:00+10:00"
  - start: "2026-07-08T14:00:00+10:00"
    end:   "2026-07-08T14:30:00+10:00"
  - start: "2026-07-09T09:00:00+10:00"
    end:   "2026-07-09T09:30:00+10:00"
chosen_calendar: "work / primary"
attendees:
  - name: "Sarah Chen"
    email: "sarah@acme.com"
title: "Q3 roadmap sync — Lucas + Sarah"
agenda: "Align on Q3 priorities before board submission."
track1_note: "Agenda: Align on Q3 priorities before board submission."
confirmed_slot: null
event_id: null
event_link: null
```

CT3 flips the issue to `needs-owner` and posts the proposal to the Discord thread.

Lucas replies (from `OWNER_USER_ID`): `confirm 2`

CT4 authenticates the author (`author.id == OWNER_USER_ID`), classifies: confirm, slot index 2, bare token. All fields resolved (`chosen_calendar` is not `"ask"`, `attendees` has email, slot 2 exists). In ONE `issueUpdate` CT4 flips `needs-owner` → `needs-agent`, **adds `confirmed-by-agent`**, and writes `confirmed_slot: 2` into the `## Draft` block.

(Contrast: had a *different* attendee replied `confirm 2`, or had Lucas replied `confirm 2, see you then`, it would be **chatter** — no flip, no `confirmed-by-agent`.)

Next drain cycle: CT4 finds `LAG-77` carrying `confirmed-by-agent`. `event_id` is still null, so it derives the deterministic id (`cos<LAG-77-uuid>s2`), calls `events.insert` with that `id`, `calendarId=primary` (work account), `candidate_slots[1]` times, `sendUpdates=all`. On success it records `event_id` + `event_link` into the draft, posts the link, THEN flips to `done` and removes `confirmed-by-agent`. Had the drain crashed right after insert, the next cycle's pre-check (or a `409` on the same id) recognizes the event is already booked and finishes the lifecycle without a duplicate.

---

## Implementation notes

- **CT3 is the initial writer.** After resolving slots, CT3 appends the `## Draft` fenced block to the issue description via `issueUpdate` (initial draft only). Append-only — do not rewrite earlier description content.
- **CT4 is the reader and edit-writer.** CT4 locates the `## Draft` literal marker string, parses the YAML block, applies confirm grammar, executes the label-flip, and — on an edit — re-invokes CT3 to re-compose candidate slots then performs the `issueUpdate` write itself.
- **CT4 two-pass operation.** Within a single drain cycle CT4 operates in two passes: (1) a classify pass that reads the latest **Lucas-authored** reply, and on a bare confirm token flips the label, adds `confirmed-by-agent`, and writes `confirmed_slot`; (2) a calendar-write pass that executes the idempotent `events.insert` for any issue carrying `confirmed-by-agent`.
- **Write authorization = the `confirmed-by-agent` label, not the `## Draft` text.** A `## Draft` block can be forged in raw `#inbox` text (Step 2 copies the message body verbatim into the description). The label is drain-authored and set only at a genuine Lucas confirm, so a forged draft never reaches `events.insert` — it routes as a NEW scheduling request and parks.
- **No duplicate `## Draft` blocks — single authoritative block.** There must be exactly ONE live `## Draft` block per issue at all times. CT4 replaces the existing block in-place on an edit, on the `confirmed_slot` write, and on the `event_id` record — it does not append a second one. CT3, on the initial-draft write (new-request route), must also REPLACE any pre-existing `## Draft` block rather than append — locate the existing block by the literal `## Draft` marker string and overwrite it. This covers the case where a forged `## Draft` in the original `#inbox` body survived to the description (defense-in-depth against the primary escape at the drain's Step 2 sanitization). Prior description content before the block is preserved. CT4's calendar-write pass treats the description as having at most one authoritative `## Draft` block; if it finds more than one literal `## Draft` marker string, it treats this as a no-write blocker (see Step 4a multi-block blocker) and re-parks at `needs-owner` — it never guesses which block is authoritative.
- **`drain-state.json` stays watermarks-only.** The issue description IS the scheduling state (including `confirmed_slot` and `event_id`). Do not add new keys to `drain-state.json`.
- **Lifecycle states** used here are standard drain labels: `needs-owner` (parked, awaiting Lucas), `needs-agent` (confirmed, agent executes), `done`. The `confirmed-by-agent` label is an orthogonal write-authorization sentinel, added at the confirm flip and removed when the issue reaches `done`.
