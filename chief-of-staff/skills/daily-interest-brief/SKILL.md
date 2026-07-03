---
name: daily-interest-brief
description: Produces a concise, sourced, newsletter-style pulse on the topics the owner follows — news, a sport, a company, a market, a policy area, a product, a cultural niche. Use whenever the owner asks "what's new in X", "brief me on <topic>", wants their daily/morning interest update, asks to follow a new beat, or wants 3–5 timely, link-rich bullets on something they care about. Uses free RSS + web search only — no paid data tools, no API keys.
---

# Daily Interest Brief

Turn the topics the owner follows into a small, reliable, newsletter-style module: **3–5
timely bullets** with embedded source links, a short source note, and optionally one useful
image — not a full research memo. This is the outward-looking counterpart to the `briefing`
skill: `briefing` sweeps the owner's own inbox/calendar/queues; this scans the wider world for
the beats they care about, and folds cleanly into the morning brief when both are present.

## Voice & self (once per conversation)

If you have not already loaded your self-layer this session, read `meta/chief-of-staff/personality.md`
from your vault so the brief sounds like you. If the vault or file is absent, proceed on your
baseline voice — the self-layer enriches, it is not a hard dependency.

## Where the owner's interests live (the vault)

Followed topics live in your vault at **`meta/chief-of-staff/interests.md`** — read it before
you brief, and write back anything new you learn (wiki-brain read-before-act / write-what-you-learn).

Format — one topic per `##` heading, with optional tuning lines:

```markdown
# Interests — topics to brief on

## AI regulation
angle: business + policy impact for founders
feeds: https://example.com/policy/rss   # optional known RSS/Atom feed(s)

## Formula 1
angle: race results and driver-market moves
```

- `angle` (optional) — what the owner cares about for this topic; use it to rank and to write
  the "why it matters" clause. This is the dial for **depth/insight**: a sharper angle earns a
  sharper brief. If a topic has no angle, ask the owner once and record their answer.
- `feeds` (optional) — known good feeds to poll directly.
- If `interests.md` does not exist, ask the owner what they'd like a daily pulse on, then
  create the file with their answers before briefing.

## Operating principles

1. Prefer deterministic, free sources before model judgment: official RSS feeds, Google News
   RSS, public schedules/results pages, agency feeds, standards bodies, reputable specialist
   outlets, broad wires.
2. Use the model for source choice, relevance ranking, dedup, and synthesis. Do **not** invent
   facts, dates, scores, quotes, or images.
3. Cross-check high-impact or surprising claims against **at least two** sources.
4. Keep it skimmable: 3–5 bullets, each one clear update plus one sentence on why it matters to
   the owner's stated `angle`.

## Workflow

### 1. Define the beat

For each interest to brief, extract: the `interest` itself, the `angle` (from `interests.md`,
else infer or ask), a `window` (default: overnight / last 24h for a morning brief; widen only
for slow-moving topics), and `region/language` from the owner's locale.

### 2. Collect candidate updates

**Native tools first (canonical path).** Use `WebSearch` and `WebFetch` directly:
1. Find official sources and feeds: `"<interest>" official news RSS`, `"<interest>" schedule
   results official`, or the topic-specific equivalent.
2. Search for overnight developments, using the date and region when useful.
3. Poll any `feeds` listed for the interest and open the strongest sources; record title, URL,
   source, publish time, and the key fact.

**Optional offline helper.** When you want deterministic, keyless Google-News-RSS polling (or
web search is unavailable), a no-dependency collector ships with this skill at
`references/collect_updates.py`. Run it with the platform's Python:

```
python references/collect_updates.py "<interest>" --days 1        # add --feed <rss-url> per known feed
```

It builds a Google News RSS query, optionally fetches known feeds, dedups by URL/title, and
emits JSON for you to rank and synthesize. **It is a helper, not the whole skill** — still
cross-check important claims with web search. Caveat: it parses untrusted feed XML with the
Python stdlib, so only point `--feed` at feeds you trust, and treat its output as candidate
material to verify, never as ground truth.

### 3. Filter and rank

Keep an item only if it is fresh for the window (or still consequential today), relevant to
the owner's angle, credibly sourced, and not a duplicate of a stronger item. Rank by
relevance, novelty, source quality, and practical usefulness. Prefer primary sources for the
final facts; use news outlets for interpretation and context.

### 4. Write the brief module

Default format, one block per interest:

```markdown
### <Interest>

- **<Update headline>** — <one sentence on what changed>, with links embedded naturally
  ([Source](https://...)). <One short clause on why it matters for the owner's angle.>
- **<Update headline>** — …

Sources checked: <short list of source names or categories>.
Image: <markdown image link or source page, only if genuinely useful and embeddable>.
```

Rules: 3–5 bullets unless asked otherwise; embed links (never dump bare URLs); state
uncertainty and conflicts plainly; include an image only when it adds real context (a match
photo, map, chart, product shot, official graphic) and prefer official/open-licence images;
keep each bullet to 1–2 sentences.

**Folding into the morning brief:** if the `briefing` skill is also composed and the owner is
running their daily brief, append these interest blocks under an `### In the world` section of
that brief rather than posting separately.

## Dependencies

- **`WebSearch` + `WebFetch`** (native) — the canonical collection path. No keys.
- **Python (optional)** — only to run `references/collect_updates.py`; stdlib-only, no pip
  installs. Invoke with the platform's interpreter (`python` on Windows, `python3` elsewhere).
- **wiki-brain vault** — reads/writes `meta/chief-of-staff/interests.md`. Absent vault ⇒ ask
  the owner for topics this session and proceed; the skill degrades, it does not fail.

## Scope

- Triggered by "what's new in X", "brief me on <topic>", "my daily interest update", "follow
  <beat>", or a request to add interest updates to the morning brief.
- Out of scope: automated unattended delivery on a schedule (that arrives with the always-on
  scheduler). Today, the owner asks each morning, or it rides the `briefing` sweep.

---

*Provenance: adapted from the MIT-licensed `daily-interest-brief` skill by Nick Pinidiya
(github.com/Nicegarrry/claude-skills). The collector script retains its MIT notice.*
