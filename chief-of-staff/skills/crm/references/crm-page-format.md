# CRM Page Format

This document defines the canonical format for every person page in Lucas's CRM. All pages live at:

```
{{VAULT_PATH}}/people/<kebab-first-last>.md
```

**File naming rule:** all-lowercase kebab-case of the person's full legal/preferred name. Examples:
- Alice Wong → `alice-wong.md`
- Jean-Pierre Moreau → `jean-pierre-moreau.md`
- Sarah O'Brien → `sarah-obrien.md` (drop apostrophes)

---

## Canonical section order

Every page follows this section order exactly. Omit a section only if genuinely unknown — use `_unknown_` as the placeholder value for required scalar fields so the page is still parseable.

```markdown
# <Full Name>

<!-- One-line summary: role @ company, or how Lucas knows them -->
_<Role> at <Company>. Met via <context>._

---

## Identity
- **Name:** <Full preferred name>
- **Pronouns:** <he/him | she/her | they/them | unknown>
- **Current role:** <Job title>
- **Company / org:** <Company name>
- **Email:** <primary email or _unknown_>
- **LinkedIn:** <profile URL or _unknown_>
- **Location:** <City, Country>

---

## Personal
- **Birthday:** <YYYY-MM-DD or month/day if year unknown, e.g. --03-14>
- **Hometown:** <City, Country>
- **Family:** <Partner name (if known), children count/names if shared, other relevant notes>
- **Interests / hobbies:** <comma-separated list>
- **Notes:** <anything personal worth remembering — health, preferences, conversation topics>

---

## Professional
- **Expertise areas:** <comma-separated list of domains>
- **Key capabilities:** <what they are distinctly good at — be specific>
- **Current focus:** <what they are working on right now>
- **Notable work / projects:** <past wins, publications, companies built, etc.>
- **Career background:** <2–3 sentence arc — where they came from, pivots, highlights>

---

## Network
<!-- Use [[kebab-first-last]] wiki-links for everyone they know well. -->
<!-- These links power network traversal for warm-intro paths. -->

Known connections:
- [[person-a]] — <how they know each other, e.g. "co-founded X together">
- [[person-b]] — <context>

Shared communities / circles:
- <e.g. "Southeast Asia VC community", "ex-McKinsey Singapore">

---

## Relationship
- **How met:** <event, introduction via [[person]], platform, date>
- **Cadence goal:** <e.g. "quarterly coffee", "ad hoc", "monthly check-in">
- **Last interaction:** <YYYY-MM-DD — <one-line summary>>
- **Next planned interaction:** <YYYY-MM-DD or "none scheduled">
- **Relationship strength:** <warm | familiar | acquaintance | cold>

---

## Give / Get
<!-- What Lucas can offer them, and what they can offer Lucas. Keep it honest and current. -->

**Lucas can give:**
- <specific value, introductions, expertise, visibility>

**They can give Lucas:**
- <specific value, introductions, expertise, market access>

---

## Interaction Log
<!-- Newest entry first. Date format: YYYY-MM-DD. -->

### YYYY-MM-DD — <brief headline>
<What was discussed. Decisions or commitments made. Follow-up items. Context that will matter next time.>

### YYYY-MM-DD — <brief headline>
<...>

---

## Tags
<!-- Space-separated tags for filtering. Use lowercase kebab-case. -->
<!-- Categories: industry, geography, relationship-type, topic, status -->

`fintech` `southeast-asia` `investor` `warm` `advisor-potential`
```

---

## Field guidance

### Identity
- **Email:** prefer the address they actually respond to, not a generic company one.
- **LinkedIn:** full URL (e.g. `https://linkedin.com/in/alice-wong`).
- Always fill **Current role** and **Company** — these are the most-queried fields.

### Personal
- **Birthday:** store as `YYYY-MM-DD`; if year unknown use `--MM-DD` (ISO 8601 partial). Never guess.
- **Family:** only record what was voluntarily shared. Do not infer.
- **Interests:** keep as a flat list; detail goes in Notes.

### Professional
- **Expertise areas** vs **Key capabilities:** expertise = domain knowledge (e.g. "B2B SaaS GTM"); capabilities = what they can distinctly *do* (e.g. "cold outbound at scale", "board-level storytelling").
- **Current focus:** update this on every interaction. Stale data here is worse than blank.

### Network
- **Only link people Lucas also has a page for** (or will have one for). Do not create ghost links to people not in the CRM.
- Add context for every link — bare `[[person]]` links without context are not traversable.
- **Shared communities** captures implicit connections (e.g. "both ex-Grab") even when there's no direct link yet.

### Relationship
- **Cadence goal** is aspirational. Update **Last interaction** on every logged contact.
- **Relationship strength:** `warm` = knows Lucas well and responds readily; `familiar` = has met multiple times; `acquaintance` = met once or twice; `cold` = no recent contact or never met.

### Give / Get
- Be concrete and self-interested on both sides — vague entries ("expertise") are useless.
- Update after every substantive interaction where the dynamic shifts.

### Interaction Log
- One entry per substantive contact (meeting, call, meaningful async exchange).
- Headline = what happened (not just "coffee chat"). Example: `2025-11-12 — Intro call, discussed his new fund thesis`.
- Body = enough context that Lucas can prep for the next interaction without re-reading a long thread.
- Keep entries to 3–6 lines. Link to external notes/docs if the conversation was long.

### Tags
- **Industry:** `fintech`, `climate`, `saas`, `healthtech`, `media`, `consumer`, `proptech`, etc.
- **Geography:** `singapore`, `indonesia`, `southeast-asia`, `us`, `uk`, etc.
- **Relationship type:** `investor`, `founder`, `operator`, `advisor`, `client`, `partner`, `friend`, `mentor`
- **Topic:** `fundraising`, `hiring`, `partnerships`, `product`, `strategy`
- **Status:** `warm`, `cold`, `to-follow-up`, `dormant`, `advisor-potential`

---

## Complete example

```markdown
# Alice Wong

_Partner at Vertex Ventures SEA. Met via Marcus Tan intro, Oct 2024._

---

## Identity
- **Name:** Alice Wong Mei Lin
- **Pronouns:** she/her
- **Current role:** Partner
- **Company / org:** Vertex Ventures SEA
- **Email:** alice@vertexventures.com
- **LinkedIn:** https://linkedin.com/in/alice-wong-vc
- **Location:** Singapore

---

## Personal
- **Birthday:** --09-22
- **Hometown:** Penang, Malaysia
- **Family:** Partner: David (architect). No kids mentioned.
- **Interests / hobbies:** trail running, specialty coffee, Mandopop
- **Notes:** Went to NUS Business. Very direct communicator. Prefers WhatsApp over email for quick exchanges.

---

## Professional
- **Expertise areas:** early-stage B2B SaaS, Southeast Asia market entry, enterprise sales motion
- **Key capabilities:** pattern-matching founder-market fit fast, connecting SEA founders to Japan/Korea expansion partners
- **Current focus:** deploying Fund IV (closed $305M, Oct 2024); thesis on vertical SaaS for SMEs in emerging SEA markets
- **Notable work / projects:** Led Series A in Xero SEA, early bet on Ninja Van, board at PolicyPal (acq. FWD 2021)
- **Career background:** Spent 5 years at BCG Singapore before moving to Vertex as principal in 2018. Made partner in 2022 after the PolicyPal exit.

---

## Network
Known connections:
- [[marcus-tan]] — introduced Lucas to Alice; they co-invested in PolicyPal
- [[priya-nair]] — both on the advisory board of Singapore Fintech Association
- [[james-lim]] — Alice led Ninja Van's Series A; James was CFO

Shared communities / circles:
- Singapore Fintech Association
- ex-BCG Singapore network

---

## Relationship
- **How met:** Introduced by [[marcus-tan]], coffee at Botanic Gardens, 2024-10-14
- **Cadence goal:** quarterly coffee or event overlap
- **Last interaction:** 2025-03-05 — Quick catch-up at Echelon; she flagged she's looking at vertical SaaS deals
- **Next planned interaction:** 2025-06-10 (tentative dinner, pending her travel schedule)
- **Relationship strength:** warm

---

## Give / Get

**Lucas can give:**
- Intro to Frollie team (vertical SaaS for beauty SMEs — fits her thesis exactly)
- SEA operator perspectives from Malo Studio client network
- Guest slot at Malo Studio's quarterly roundtable (senior operators, ~30 pax)

**They can give Lucas:**
- Warm intros to Series A-stage founders in her portfolio who need GTM help
- Signal on what LPs want to see in operator-led funds (she sits on two LP advisory boards)
- Possible co-investor for Lucas's angel deals

---

## Interaction Log

### 2025-03-05 — Echelon side event, brief catch-up
Ran into each other at the Echelon side event (VC mixer). ~15 min chat. She mentioned Vertex is actively looking at vertical SaaS for beauty/wellness SMEs — flagged Frollie as a potential fit. Said to send her a deck. Follow-up: send Frollie deck by EOW.

### 2024-10-14 — First coffee, Botanic Gardens
Intro via Marcus. Spent ~90 min. She walked through Fund IV thesis. I shared Malo Studio's work on GTM for emerging market SaaS. Good chemistry. She offered to make 2 intros: Priya Nair (fintech) and the Xero SEA country manager. I said I'd send a one-pager on Malo Studio's advisory model.

---

## Tags
`investor` `vc` `singapore` `southeast-asia` `fintech` `saas` `warm` `fundraising` `to-follow-up`
```
