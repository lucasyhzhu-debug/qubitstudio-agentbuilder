---
name: crm
description: Records and recalls people in Lucas's personal CRM (wiki-brain/people/), capturing identity, family, professional profile, network connections, give/get, and a dated interaction log. Use when Lucas mentions meeting someone, asks who someone is, wants to remember something about a person, asks what he knows about someone, wants to log an interaction, asks who he knows that could connect him to someone, asks for a warm-intro path, or says things like "note about a person", "remember that Z", "who is X", "log that I met Y", or "intro path to".
---

# CRM

This skill maintains Lucas's personal CRM as one markdown page per person under `{{VAULT_PATH}}/people/`. It reuses the wiki-brain filesystem and ingest/query patterns so all CRM data is accessible to his your-assistant-bot via the GitHub wiki plugin. Each page captures a person's identity, personal details (family, birthday, hometown, interests), professional profile (role, company, expertise, capabilities, notable work), network connections as `[[wiki-links]]` to other people, relationship cadence, give/get, and a dated interaction log.

## Voice & self

Before acting, **once per conversation** — if you have not already loaded your self-layer this session — read these three files and let them shape everything you do. Hold them in context; do **not** re-read them on every turn.

- `{{VAULT_PATH}}/meta/chief-of-staff/personality.md` — your **voice**. Sound like this in everything you say to Lucas.
- `{{VAULT_PATH}}/meta/memories.md` — what you know about **Lucas** (the shared memory hub). Read the hub; follow a `[[link]]` one hop into a deep-dive only when it's relevant to the task at hand — don't pre-load every linked page.
- `{{VAULT_PATH}}/meta/chief-of-staff/lessons.md` — how you've **learned to work** well for Lucas.

If a file can't be read (vault not present), proceed on your baseline voice — the self-layer enriches, it isn't a hard dependency. Anything you draft **for Lucas to send** (emails, messages) goes in **his** voice, not yours.

## How it works

### Reading (recall)
- To answer "who is X" or "what do I know about X", read `{{VAULT_PATH}}/people/<kebab-first-last>.md` directly.
- To find someone when the exact name is uncertain, scan `{{VAULT_PATH}}/people/` for files whose content matches the description (role, company, hobby, city, etc.).
- For briefing prep before a meeting, read that person's page and surface: last interaction, next planned interaction, give/get, and any notes relevant to the meeting topic.

### Writing (capture)
- When Lucas mentions meeting someone or shares new information about a person, locate their page or create one if it doesn't exist.
- Append a dated entry to the **Interaction Log** (newest first) with what was discussed, decisions made, and any follow-up commitments.
- Update other sections (role, company, interests, give/get, next interaction) when Lucas provides new facts.
- File path: `{{VAULT_PATH}}/people/<kebab-first-last>.md` — use all-lowercase kebab-case of their full name.

### Network traversal
- People pages link to each other via `[[kebab-first-last]]` wiki-links in the Network section.
- To answer "who do I know that knows someone in fintech" or "intro path to X", read the target person's page (if it exists), then scan the Network sections of Lucas's contacts for overlap. Follow the `[[wiki-links]]` one hop at a time.
- Surface the shortest path(s) as a warm-intro chain: "You know Alice → Alice knows Bob → Bob is connected to your target."
- When traversing, stay within `{{VAULT_PATH}}/people/`; do not follow links outside that directory.

### Creating a new person page
Read `references/crm-page-format.md` when creating or updating a person page. It contains the canonical section structure, field definitions, and a complete example. Follow it exactly so pages are consistent and queryable.

### Ingest / query patterns (wiki-brain integration)
- This skill reads and writes files directly via the filesystem — no separate ingest step is required for CRM pages since they are small and structured.
- For richer semantic queries ("who works in climate tech and is based in Southeast Asia"), scan all pages under `{{VAULT_PATH}}/people/` and filter by Tags and Professional sections.
- For knowledge that lives outside `people/` (e.g. a company note, an industry overview), defer to the wiki-brain query skill to search the broader wiki.

### Before recurring meetings
- When a briefing is being prepared and a meeting with a known person is on the calendar, proactively read that person's CRM page and include a summary: last interaction, current focus, pending give/get commitments, and any standing topics.

## Quick reference

| Intent | Action |
|---|---|
| "Who is X" | Read `people/<kebab-first-last>.md`, summarise key fields |
| "Log that I met Y" | Append dated Interaction Log entry |
| "Remember that Z likes sailing" | Update Interests in Personal section |
| "Who do I know in fintech" | Scan Tags / Professional sections across all pages |
| "Intro path to X" | Network traversal — follow `[[wiki-links]]` from Lucas's contacts |
| Create new person | Read `references/crm-page-format.md`, scaffold the page |
