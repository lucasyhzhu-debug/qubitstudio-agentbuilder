# Meeting Pages — vault schema reference

Defines `meetings/YYYY-MM-DD-<slug>.md` and `people/<kebab>.md` stubs created by the Phase B morning-brief skill and extended by Phase D post-meeting capture. Consumers must follow the idempotency rules below before writing.

Vault root: `{{VAULT_PATH}}`

---

## Idempotency rules (read before creating)

- **meetings/ pages**: look up an existing page by `calendar_event_id`, NOT by filename slug. A reschedule changes the date; the event ID does not. If a page with that `calendar_event_id` already exists, update it — do not create a duplicate.
- **people/ stubs**: people pages live in ONE namespace keyed by **name-kebab** (kebab of the display name; see filename rule below). A page is reconciled to an attendee by `identity.email` (primary) then name — so a stub created on a prior run is found and reused, never duplicated. A stub is also considered present if the file `people/<kebab-name>.md` exists; check that path before creating. Dedup interaction lines in an existing stub by the `[[meetings/<page>]]` wikilink — append only if that link is not already in the file.

---

## `meetings/` page

### Filename

```
meetings/YYYY-MM-DD-<slug>.md
```

- `slug` = kebab-cased event title, lowercased, punctuation stripped.
- On a same-day title collision (two events with the same slug on the same date), append `-<HHmm>` of the event start time: `meetings/2026-06-30-product-sync-0900.md`.

### Frontmatter

```yaml
---
date: YYYY-MM-DD
attendees:
  - "[[people/<kebab-name>]]"
  - "[[people/<kebab-name-2>]]"
calendar_event_id: <Google Calendar event id string>
account: <GOOGLE_ACCOUNTS label, e.g. "work">
discord_thread: ""
---
```

- `calendar_event_id` is the identity key. Never use the filename slug as a surrogate key.
- `discord_thread` is left empty by Phase B; the owning later phase writes the thread URL once a brief-thread is created.
- `attendees` lists only external attendees (omit Lucas's own account).

### Sections

```markdown
## Context

<!-- Phase B fills this section. Contents: agenda (from event description) + per-attendee
     summary drawn from recent emails and existing people pages. -->

## Minutes

<!-- Phase D fills this section. Raw or lightly cleaned meeting notes. -->

## Synthesis

<!-- Phase D fills this section. Key discussion points and decisions. -->

## Takeaways

<!-- Phase D fills this section. Outcomes and commitments reached. -->

## Todos

<!-- Phase D fills this section. Action items with owner and due date. -->
```

Sections `## Minutes`, `## Synthesis`, `## Takeaways`, and `## Todos` are **declared here but owned by Phase D**. Phase B writes only `## Context`; it must not populate or remove the D-owned section headers.

---

## `people/` stub

Created for each external attendee with a `name` who does not yet reconcile to an existing people page. **Email-only attendees (no name) are NOT stubbed** — an email alone cannot be keyed into the name namespace and is not a useful person page; mention them in the brief as an external email instead.

### Filename

```
people/<kebab-name>.md
```

`kebab-name` = **name-kebab**: the person's full display name lowercased, spaces → hyphens, apostrophes dropped, existing intra-name hyphens preserved (e.g. `Sarah Chen` → `sarah-chen`; `Sarah O'Brien` → `sarah-obrien` (drop apostrophes); `Jean-Pierre Moreau` → `jean-pierre-moreau` (intra-name hyphen kept)). This is IDENTICAL to the CRM convention in `chief-of-staff/skills/crm/references/crm-page-format.md` — there is ONE people namespace, not a separate meeting one. The email is the *reconciliation* key (carried in `identity.email`), never the filename.

### Frontmatter

```yaml
---
identity:
  name: <Display Name>
  email: <email address>   # carried so future runs reconcile this page by identity.email (the reconciliation key)
source: meeting-auto
created: YYYY-MM-DD
tags:
  - stub
---
```

### Body seed line

```markdown
- YYYY-MM-DD — first appeared as co-attendee with Lucas at [[meetings/YYYY-MM-DD-<slug>]] (<event title>).
```

Append this line to any existing stub rather than replacing it. If the stub does not exist, create the file with the frontmatter above and this line as the sole body content.

---

## Worked example

Event: "Product Sync" on 2026-06-30 at 09:00, Google Calendar ID `abc123xyz`, account `work`, attendee Sarah Chen (sarah@acme.com).

**`meetings/2026-06-30-product-sync.md`**

```markdown
---
date: 2026-06-30
attendees:
  - "[[people/sarah-chen]]"
calendar_event_id: abc123xyz
account: work
discord_thread: ""
---

## Context

**Agenda:** Quarterly roadmap review — align on Q3 priorities before board submission.

**Sarah Chen** — Last email 2026-06-25 re: milestone timeline. No existing people page; stub created.

## Minutes

## Synthesis

## Takeaways

## Todos
```

**`people/sarah-chen.md`** (new stub)

```markdown
---
identity:
  name: Sarah Chen
  email: sarah@acme.com
source: meeting-auto
created: 2026-06-30
tags:
  - stub
---

- 2026-06-30 — first appeared as co-attendee with Lucas at [[meetings/2026-06-30-product-sync]] (Product Sync).
```

> **Collision example:** If a second "Product Sync" event also started at 09:00 on 2026-06-30, its filename would be `meetings/2026-06-30-product-sync-0900.md`.

---

## Vault git discipline

The vault (`{{VAULT_PATH}}`) is a separate git repo. When committing new meeting pages or stubs, always name files explicitly:

```powershell
git -C "{{VAULT_PATH}}" add meetings/2026-06-30-product-sync.md people/sarah-chen.md
git -C "{{VAULT_PATH}}" commit -m "cos: add meeting page + stub for 2026-06-30 product-sync"
```

Never use `git add -A` or `git add .` against the vault.
