# Briefing Format Reference

This document defines the structure, section order, formatting conventions, and tone for all daily and weekly briefs produced by the `briefing` skill. Follow it exactly when assembling a brief. Do not add or reorder sections without a user instruction.

---

## Daily Brief

### Structure

```
## Daily Brief — {Day, Month D, YYYY}

### Today's Calendar
- {HH:MM} — {Event title} ({duration})
  - Attendees: {names or "just you"}
  - CRM note: {one line from their people page, e.g. last met, give/get, what to watch for — omit if no people page}
[Repeat for each event. If no events: "No meetings scheduled."]

### Emails Needing Reply
- **{Sender name}** — {Subject line} ({received time or "yesterday"})
  - {One sentence on what they need and suggested action}
[List up to 5. If none: "Inbox clear."]

### Discord
- **#inbox**: {N} new requests — {brief list of topics or "none"}
- **Mentions**: {list any @Lucas mentions with channel and topic, or "none"}

### Linear
- **Due today**: {task title} [{issue ID}]
- **In progress**: {task title} [{issue ID}]
- **Blocked**: {task title — why blocked} [{issue ID}]
[If no tasks match: "No tasks due or in progress today."]

### CRM — Meeting Prep
[One block per person in today's calendar. Omit section if no meetings.]

**{Person name}** ({role}, {company})
- Last interaction: {date + one-line summary}
- Cadence: {target cadence, e.g. "monthly"}
- Give/get: {what Lucas can offer | what they can offer Lucas}
- Network note: {any relevant connection paths, e.g. "knows {X} at {company}"}

### Proposed Focus
1. {Action} — {one-line rationale}
2. {Action} — {one-line rationale}
3. {Action} — {one-line rationale}
[3–5 items, ordered by impact + urgency. Flag decision dependencies with "(needs decision: {what)"."]
```

---

## Weekly Brief

### Structure

```
## Weekly Brief — Week of {Month D, YYYY}

### This Week's Calendar
[Group by day. For each day list events in HH:MM order. Include CRM notes for key meetings as in daily format.]

Mon {D}: {event list or "clear"}
Tue {D}: {event list or "clear"}
Wed {D}: ...
Thu {D}: ...
Fri {D}: ...

### Email Themes
[Instead of individual threads, summarize the top 2–3 email themes or conversations requiring attention this week.]
- {Theme}: {what it is and suggested action}

### Discord
- **#inbox backlog**: {N} items — {topics summary}
- **Notable threads**: {any #long-form threads active this week}

### Linear — This Week
- **Due this week**: {list of tasks with due dates}
- **In progress**: {list}
- **Upcoming (next 2 weeks)**: {brief list}
[Group by project if more than 5 tasks total.]

### CRM — This Week's Meeting Prep
[One block per person with a meeting this week. Same format as daily CRM block.]

### Proposed Focus — This Week
1. {Initiative or action} — {rationale}
2. {Initiative or action} — {rationale}
3. {Initiative or action} — {rationale}
[3–5 items. Flag anything that needs a decision before progress is possible.]

### On the Radar (Optional)
[Include only if there is something notable 1–3 weeks out that warrants early action — e.g. a deadline, a person to re-engage, a decision window closing. Omit if nothing material.]
- {Item}: {why it matters now}
```

---

## Formatting Conventions

- **Date/time**: use `Day, Month D, YYYY` for headers (e.g. `Thursday, June 26, 2025`); use 24-hour `HH:MM` for event times. Times render in Lucas's local timezone; append the tz abbreviation (e.g. AEDT) when he's travelling.
- **People names**: use the name exactly as it appears in their CRM people page (`wiki-brain/people/<kebab-name>.md`). If no CRM page exists, use the name as it appears in the calendar/email.
- **Issue IDs**: always include Linear issue IDs in square brackets (e.g. `[COS-12]`) so Lucas can navigate directly.
- **Bold for names and statuses**: bold sender names in email sections, bold day labels in weekly calendar, bold channel names in Discord section.
- **Bullet depth**: maximum two levels. If a bullet needs a sub-bullet, keep the sub-bullet to one line.
- **Length**: daily briefs target 300–500 words of content (excluding headers). Weekly briefs target 500–800 words. Cut aggressively — Lucas wants signal, not inventory.
- **No filler phrases**: do not open sections with "Here are your…", "Below you'll find…", or similar. Start each section directly with its content.
- **Omit empty sections**: if a section has nothing to show, either omit it or write a single short "none" line — do not leave a section header with blank space.

---

## Tone & brief behaviour

**Voice lives in `{{VAULT_PATH}}\meta\chief-of-staff\personality.md`** — the skill's "Voice & self" block reads it; sound like it in every brief. This section keeps only **brief-specific behaviour**, not the personality:

- **First-person on Lucas's behalf.** Propose actions as imperatives owned by Lucas — "Reply to X", "Follow up with Y", "Decide on Z".
- **Proposed Focus is a ranked recommendation, not a menu.** Order it by impact + urgency; if something is clearly the priority, say so. Flag decision dependencies with "(needs decision: …)".
- A brief may open with one short, friendly line before the sections (see `personality.md`), then get to the signal.

---

## CRM Proactive Surface Rules

Surface a CRM block for a person when any of the following is true:
1. They appear in a calendar event today/this week.
2. Their cadence target is overdue (last interaction was more than the cadence interval ago) and Lucas has a touchpoint coming up.
3. A give/get item has become newly relevant based on other brief content (e.g. Lucas is working on something this person could help with).
4. A network connection path is relevant to an active goal or meeting (e.g. Lucas needs an intro the person can provide).

Do NOT surface a CRM block for someone just because they sent an email — only include them in the CRM section if one of the four conditions above is met.

---

## Posting to Discord (#daily-briefs)

The brief posts to `$DISCORD_CHANNEL_DAILY_BRIEFS` via the Discord REST API (Bot token + `DiscordBot` User-Agent) on the headless/scheduled path — see `../SKILL.md` Step 6. The `discord` MCP connector is an interactive fallback only.
- Use the full brief text as the message body.
- Prefix the message with the brief header (e.g. `## Daily Brief — Thursday, June 26, 2025`) so it is visually distinct in the channel.
- Discord does not render all markdown identically to SKILL.md previews — bold (`**text**`) and bullet lists work; complex table formatting may not. Keep the posted version to bold + bullets only.
- On the scheduled cron the brief posts autonomously; in an interactive session, confirm with Lucas before posting unless he explicitly said "post it".

---

## Meeting-aware daily brief

When Google Calendar data is available, replace the flat `### Today's Calendar` list with a per-day grouped layout. Each event renders as a self-contained block. Carry the same layout into the weekly brief's `### This Week's Calendar` day groups.

### Per-day layout format

```
### Today — {Day, Month D}

**{HH:MM}–{HH:MM}** · {Event title}
- Attendees: {Name} ({role}, {company}) — {last-contact one-liner or "stub — no prior contact"}
- Attendees: [Repeat this line per attendee. If solo: "Just you."]
- Location / video: {room name, address, or video link; "TBC" if none set}
- Meetings page: `meetings/{YYYY-MM-DD}-{kebab-title}.md` *(create if absent)*

[Repeat block per event in chronological order. If no events: "No meetings scheduled today."]

### Tomorrow — {Day, Month D}

[Same block format as Today. Include only if at least one event exists tomorrow; omit section if calendar is clear.]
```

### Graceful Gmail gap

When the skill could not retrieve Gmail context for a specific attendee, surface a single inline note rather than silently omitting their context:

```
- Attendees: Sarah Chen (Partner, Blackbird VC) — couldn't reach Gmail for Sarah; no recent thread found
```

Do not drop the attendee line. Show the name and role (from the calendar invite) and flag the gap so Lucas knows the CRM context is incomplete.

### Stub / new-contact marker

When an attendee has no wiki-brain people page (`wiki-brain/people/<kebab>.md`) and no prior email thread, mark them explicitly:

```
- Attendees: Jordan Watts (TBC — stub; no prior contact on record)
```

This is the signal to prompt Enrichment asks (see below).

### Worked example

```
### Today — Monday, June 30

**09:00–09:30** · Catch-up — Sarah Chen
- Attendees: Sarah Chen (Partner, Blackbird VC) — last met 2025-05-14, discussed portfolio co introductions; give: QubitStudio workshop access, get: warm intro to Atlassian Ventures
- Location / video: Zoom — https://zoom.us/j/123456789
- Meetings page: `meetings/2025-06-30-catch-up-sarah-chen.md`

**14:00–15:00** · Intro call — Jordan Watts
- Attendees: Jordan Watts (TBC — stub; no prior contact on record)
- Attendees: Marcus Liu (Principal, Airtree) — couldn't reach Gmail for Marcus; no recent thread found
- Location / video: Google Meet — calendar invite link
- Meetings page: `meetings/2025-06-30-intro-call-jordan-watts.md`

### Tomorrow — Tuesday, July 1

**10:00–10:30** · Weekly sync — Frollie team
- Attendees: Priya Nair (CEO, Frollie) — last met 2025-06-23, sprint planning; on track for July pilot launch
- Location / video: Gather Town — frollie.gather.town
- Meetings page: `meetings/2025-07-01-weekly-sync-frollie.md`
```

---

## Enrichment asks

When the brief is thin on context for one or more attendees (stub marker, Gmail gap, or people page more than 60 days stale), append an `## Enrichment asks` block at the end of the brief and post it to `#inbox` so Lucas can reply inline.

### Format

```
## Enrichment asks

I'm light on context for a few people you're meeting this week. A one-line reply or a LinkedIn screenshot for any of these would help:

- **Jordan Watts** — meeting you at 2pm today. Who is he and what's the goal of the call?
- **Marcus Liu (Airtree)** — attending today's 2pm intro call; couldn't pull recent email context. Anything I should know before the call?

Reply here or drop a LinkedIn screenshot into #inbox.
```

### Rules

- List only people the brief is genuinely thin on — do not ask about people who have a populated people page and a recent email thread.
- Phrase each item as a question with the reason ("meeting you at 2pm") so the ask is actionable.
- Cap the list at 3 items per brief — if more people are thin, pick the highest-priority meetings.
- Post to `#inbox`, not `#daily-briefs` — this is a request, not a broadcast.
- Omit the section entirely if no enrichment is needed.
