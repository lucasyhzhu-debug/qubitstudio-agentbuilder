# Interests Module — reference

The optional `### Interests` block turns the owner's standing interests into a small, reliable
news pulse inside the daily brief: **3–5 source-linked bullets per interest**, capped at the
**top 3 interests**. It is the outward-looking counterpart to the rest of the brief — the brief
sweeps the owner's own inbox / calendar / queues; this scans the wider world for the beats they
follow.

**Off by default — this is sacred.** The module is **strictly additive**: it adds zero new
behaviour until the owner opts in by creating an interest list. **No `interests.md` ⇒ no
`### Interests` heading ⇒ the brief is byte-for-byte identical to today.** Never guess interests,
never fabricate a section, never emit a placeholder heading.

---

## Where interests live (the gate)

The standing-interest list lives in the vault at:

```
{{VAULT_PATH}}/meta/chief-of-staff/interests.md
```

**If this file is absent, the module is OFF** — omit `### Interests` entirely. Do not create the
file, do not ask mid-brief, do not guess topics. The file's existence is the entire opt-in.

### File format

One interest per **bullet**, with optional inline hints:

```markdown
# Interests

- AI regulation — angle: business + policy impact for founders — feed:https://example.com/policy/rss [priority]
- Formula 1 — angle: race results and driver-market moves
- Our category — competitor moves
```

- **Interest text** — the beat to follow (the part before the first ` — ` hint). Used verbatim to
  build a Google News query when no feed is given.
- **`— angle: <text>`** *(optional)* — what the owner cares about for this beat. The model uses it
  to rank candidates and to write the one-line "why it matters" clause. A sharper angle earns a
  sharper bullet. The collector captures it but does not act on it.
- **`— feed:<url>`** *(optional)* — a known-good RSS/Atom feed to poll directly. When present it is
  **authoritative** for that interest (no Google News fallback for that beat).
- **`[priority]`** *(optional)* — marks an interest as preferred when capping to the top 3.

A lone top-level `# Interests` line is a title, not an interest. The collector also tolerates the
sibling `daily-interest-brief` shape (one interest per `##` heading with `angle:` / `feeds:`
continuation lines) so both skills can share this one file without conflict — but the bullet form
above is canonical for this module.

---

## Placement

When active, `### Interests` sits **after `### CRM — Meeting Prep`** and **before
`### Proposed Focus`**:

```
### CRM — Meeting Prep
...
### Interests
...
### Proposed Focus
...
```

Cap at the **top 3 interests** by default, preferring any marked `[priority]`. Within each
interest, at most **5 source-linked bullets**.

---

## Sourcing discipline (deterministic-first, model-second)

Candidate sourcing is **deterministic-first and headless-safe**. Two paths, in order:

1. **Collector path (full substrate).** When `scripts/collect_updates.py` is present, run it — it is
   stdlib-only (no third-party deps) and safe under `claude -p`:

   ```
   python scripts/collect_updates.py --interests <resolved interests.md path> --window-hours 24 --max-per-interest 5
   ```

   Resolve `{{VAULT_PATH}}` to the concrete path yourself before calling — the placeholder is **not**
   substituted inside a `.py`, so the path must be passed as the `--interests` argument. The script
   parses `interests.md`, fetches each interest's `feed:` URL (or a Google News RSS query built from
   the interest text), filters to the window, and prints JSON:
   `{"interests_found": N, "candidates": [{interest, title, url, source, published}], "unreachable": [...]}`.
   It only **collects** — it never summarises, scores, or invents.

2. **Web-search fallback (lean home).** A composed participant "home" ships each skill's `SKILL.md`
   + `references/` but **not** `scripts/`. When `collect_updates.py` is **not present in this home**,
   fall back to model-driven **web search** to gather the same kind of candidates per interest
   (recent, on-beat, source-carrying). Also use web search when the collector runs but a feed is
   unreachable and you need to fill an interest.

Either way, the model's job is **only** source choice, relevance ranking, cross-source dedup, and
synthesis. **Never invent** facts, dates, scores, quotes, or images. Cross-check any high-impact or
surprising claim against at least two sources. Default recency window is the **last 24 hours**.

---

## Bullet format

Per interest, up to **5 bullets**, each carrying its **source link**:

```
### Interests

**AI regulation** — business + policy impact for founders
- EU AI Act enforcement timeline moved up — first obligations bite in Q3. ([Reuters](https://…))
- New US executive order on model reporting thresholds. ([The Verge](https://…))

**Formula 1** — race results and driver-market moves
- Sprint result + championship implication in one line. ([BBC Sport](https://…))
```

- Every bullet ends with an inline source link `([Source](url))`. A bullet with no source is dropped,
  not guessed.
- One clear update per bullet, plus at most one clause on why it matters to the stated `angle`.
- Keep it skimmable — this is a pulse, not a research memo.

---

## Degradation rules (yield under pressure)

- **No `interests.md`** ⇒ omit the section. (The gate.)
- **Every source unreachable / no candidates** ⇒ omit the section rather than emit a thin or
  fabricated one. A degraded interest is silently dropped; a degraded *module* simply does not appear.
- **A single unreachable feed** ⇒ the collector lists it under `unreachable` and continues; fill that
  interest via web search if you can, else drop just that interest. Never surface an error or a
  made-up bullet.
- **2000-char Discord cap.** The brief respects the cap (see `../SKILL.md` Step 6). `### Interests` is
  the **first section trimmed** when a brief runs long — trim its bullets, then the whole section,
  before touching any owner-facing section (Today/Tomorrow, Emails, Linear, Proposed Focus).

---

## Guarantees

- **Read-only.** No vault, Linear, or Google writes. This module never creates meeting pages, people
  stubs, or issues — it only reads `interests.md` and public feeds and composes bullets.
- **First trimmed.** Under the length cap it yields before every other section.
- **Never fabricates.** Absent a real, source-linked candidate, the bullet (or the whole section) is
  omitted — the module fails silent, never loud.
- **Placeholder discipline.** The interests path is `{{VAULT_PATH}}/meta/chief-of-staff/interests.md`
  everywhere in prose; never a concrete personal vault path. No real ids, emails, or keys.
