# The dossier journey — the studio as a living document

**Date:** 2026-07-02
**Status:** Revised — shipshape gate 1 applied
(`docs/reviews/shipshape-studio-dossier-journey-spec-2026-07-02.md`)
**Owner:** Lucas
**Target:** QubitStudio "Build Your Own Chief of Staff" workshop ($1200/session outcome bar:
participants must feel value, EMPOWERED, MORE PRODUCTIVE, and the journey itself
engaging/energizing — this spec is that bar applied to the whole participant surface).
**Depends on:** the onboarding-cards slice (spec
`docs/specs/2026-07-02-studio-onboarding-cards-design.md`, plan
`docs/plans/onboarding-cards.md`) — **in flight on `feat/onboarding-cards-impl` at time of
writing**. This spec targets the tree AFTER that slice lands and reuses its contracts (§7.4);
it must not be planned into implementation until onboarding-cards merges (collision risk §11.1).
Also builds on the landed ` ```studio ` journey (PR #6: extractor, shelfSync, workshop mode),
and **absorbs ROADMAP item 3 (raw-skills packaging)** as slice D0 — implementing the design
already fixed in `docs/specs/2026-07-02-workshop-lean-distribution-design.md` §5, because the
finale's First Breath and launch command depend on it (§6).
**Proofing artifacts — COMMITTED at `docs/mockups/dossier-journey/` (open them in a browser
before implementing; they are the visual truth this spec describes):
`v1b-dossier-journey.html`** — the chosen direction, fully interactive (chapters, choice
cards, journey rail with phase milestones, rewrite ↺ with card-reopen, stale/re-settle);
**`v1c-finale.html`** — the approved finale sequence (§6: sign → bind → assemble → first
breath → launch card; click "Build my agent" to run it). `v1-dossier.html` is v1b's simpler
ancestor; `v2-canvas.html` / `v3-stage.html` are the explored alternatives Lucas reviewed
and passed on (kept for design rationale). `proofing-room.js` is the review-comment overlay
each mockup loads — not product code. Mockups load fonts from a running studio
(`http://127.0.0.1:8765`) and fall back to system faces without it. Note: v1c's
"Morning, Lucas." greeting is **sample copy** — genericize to "Ada" when the mockups are
next touched.

## 1. The thesis

**What "dossier" means here (definition for a fresh session):** the dossier is the workshop
studio's participant page rebuilt as a *living document about the agent being built* —
a single scrolling page of numbered, titled chapters that the architect (the `claude -p`
chat) writes as the interview progresses. It replaces the chat transcript: instead of
bubbles, the agent's words render as chapter body text, the participant's answers are
typeset into the page as permanent serif quotations, and the text input is a bare "writing
line" at the document's live edge. The page IS the conversation's rendered form — every
beat is still one chat turn under the hood. See `docs/mockups/dossier-journey/
v1b-dossier-journey.html` (the journey) and `v1c-finale.html` (the ending) — open them and
interact before writing any code.

Today the workshop journey is a chat: bubbles on the left, panels on the right. This spec
replaces it (workshop mode only) with **a document the participant authors with their
architect** — a single-column "dossier" page where:

- the architect **writes numbered chapters into the page** (baseline, skill recommendations,
  personalization, naming, building, connecting) rather than sending messages;
- the participant's answers **fossilize as serif quoted lines** — their words become part of
  the record, permanently visible, scrollable end to end (the scrollytell);
- the input is a **blended writing line** — the document's next line, not a chat box;
- a fixed **journey rail** carries named phase milestones that colour in as chapters close;
- any fossilized answer can be **rewritten** (↺) — choice sections reopen their cards, the
  chapters below go stale until the answer re-settles — and any chapter can be
  **regenerated** (⟳) if it rendered wrong;
- the journey ends with a **sign-&-build close**: the participant's agent name written on a
  signature line above the Build action — the dossier becomes an agent.

One experience from first launch to working agent: intake (introduce yourself, drop your
CV/screenshots) → interview → personalize → name → sign & build → connect keys. The chat
never disappears conceptually — every beat is still one `claude -p` turn — but the page stops
*looking* like chat and starts looking like a document being written about *your* agent.

`?mode=architect` keeps the existing two-pane chat UI **byte-identical**. The dossier is the
workshop skin only. And within workshop mode, **`?ui=chat` is the same-journey escape
hatch**: it keeps the current workshop chat skin reachable on the same backend (same
session, same extractor, same endpoints) — the in-room fallback if the dossier misbehaves.
It stays until dossier parity is proven at a dress rehearsal, then is removed in a later
cleanup slice.

## 2. Design language (SapphireOS, dossier register)

All styling uses the existing SapphireOS tokens — **no new hex values**. New CSS lives in
`studio/static/dossier.css` (+ `dossier.js`); the existing `styles.css` chat rules stay for
architect mode. The register, proofed in `v1b-dossier-journey.html`:

| Element | Treatment |
|---|---|
| Page | Single centered column (~760px) on `--band`; generous vertical rhythm |
| Chapter head | Brass mono number (`01`) + Bricolage h2 + mono "why" eyebrow, ruled underline |
| Agent prose | Body sans, streams into the open chapter (markdown-rendered, stripSpec'd) |
| Participant answers | **Crimson Pro italic, 21px, `— ` brass dash** — the human is the serif |
| Skill cards | Existing card surface (white, `--r-card`, `--sh-sm`), 🔒/✓/candidate tags, price pills |
| Choice cards | The ask channel rendered inline: label + one-line `why`, picked = sapphire ring + tint, others dim |
| Writing line | Borderless serif input, breathing brass caret-bar, dashed underline → brass on focus |
| Journey rail | Fixed 2px line, left margin; named mono milestones (dots) colour in; current pulses; brass while rewriting |
| Rewrite mark | `rewritten ↺` brass chip on re-fossilized answers — revision is part of the record |
| Signature close | Manifest chips, name on a ruled signature line, "Build my agent ▶" |
| Motion | Reuses onboarding-cards' vocabulary (rise/fold/baton/morph) + `settle` (section fade-up) and `stale` (dim + saturate-down); all cut under `prefers-reduced-motion` |

Type scale is workshop-room legible (body 17px, answers 21px, chapter h2 24px) — the same
bar as the chat-scale polish already landed.

## 3. Wire format — the `chapter` field (and, in D2, typed blocks)

### 3.1 D1: chapter + phase (`studio_extractor.py`)

The workshop studio block gains one optional field. **Whole state every turn**, as with
picks/name/ready/ask:

```studio
{ "picks": ["tasks"], "name": null, "ready": false,
  "ask": { ...unchanged (onboarding-cards §4)... },
  "chapter": { "title": "Taming the inbox", "phase": "skills" } }
```

- `phase` ∈ `welcome · baseline · skills · personalize · name · build · connect` — the fixed
  milestone set the rail renders. Unknown phase → treated as absent.
- `title` — non-empty str ≤ 80 chars; the h2 the page draws.
- **Tolerant parsing** (the standing rule): malformed `chapter` → `None`, and picks / name /
  ready / ask still sync. `extract_studio` returns a fifth key `chapter: dict | None`.
- **Fallback:** a turn with no valid `chapter` appends its prose to the **current open
  chapter**. The document never breaks; it just doesn't get a new heading.
- Same `title` (case-insensitive, trimmed) as the open chapter → same section continues.
  New title → new numbered section.

### 3.2 D2: the typed block vocabulary

For build/connect chapters, `chapter` gains an optional `blocks` array — a **closed
vocabulary** the page knows how to render, interleaved with the prose:

```studio
{ "picks": ["tasks","briefing"], "name": "atlas", "ready": true,
  "chapter": { "title": "Connect Linear", "phase": "connect",
    "blocks": [
      {"type":"step","n":1,"text":"Open linear.app → Settings → API → Personal API keys"},
      {"type":"step","n":2,"text":"Create a key named 'atlas' and copy it"},
      {"type":"key-field","integration":"linear","label":"Paste your Linear API key"},
      {"type":"checklist","items":["Key created","Key pasted","Smoke test green"]} ] } }
```

v1 vocabulary: `step` (numbered walkthrough line), `key-field` (renders the **existing**
connect-row input for that integration, wired to the existing smoke-test endpoint — the
dossier hosts it via the `wireKeyRow(rowEl, integration, tree)` extraction named in §7.2,
it does not reimplement it), `checklist` (progress ticks), `note`
(callout), `skill-card` (explicit card by catalog id, for when the picks-diff isn't enough).
**Unknown `type` → that block is skipped, the rest render** — the vocabulary can grow
without breaking old clients. Likewise a `key-field` whose `integration` id is unknown →
that block is skipped. Malformed `blocks` → `blocks: []`, chapter title still lands.
D1 ships with `blocks` accepted-and-ignored by the renderer (parser validates, renderer
renders none) so D2 is purely additive.

### 3.3 Prompt contract (`system_prompt.py`, workshop mode)

The workshop contract gains a "writing the page" section: *you are writing a document, not
chatting. Every turn, include `chapter` in the studio block — the title of the section you
are writing (reuse the current title to continue it, a new title to open a new one) and the
phase you are in (the fixed set). Keep titles short and human ("Taming the inbox", not
"Skills recommendation phase"). Do not restate the chapter title in your prose — the page
draws it.* Brevity/style rules already landed (≤2 sentences prose, bold skill names, one
question per turn) stay — they are what makes chapters readable.

## 4. Rendering model (`dossier.js`)

### 4.1 Beats → chapters (live-edge staging)

The page state is an ordered list of **beats** (one per agent turn: `{prose, studio}`)
grouped into **chapters** by §3.1's title rule. `chapter` arrives only on the `done`
event, so prose is never streamed "into" a chapter directly — it streams at the
**live edge** and settles at done:

- **During the turn:** tokens render (stripSpec'd, markdown, the existing per-turn
  throttle) into a headingless staging block at the document's live edge — visually
  the tail of the open chapter, because the live edge IS the end of the last section.
- **At done:** the `chapter` field settles heading and placement. Same title as the open
  chapter (case-insensitive, trimmed) → the staged prose already sits where it belongs;
  **the staging is invisible**. New title → the section head (number = count+1, `settle`
  motion) draws above the staged prose, which becomes the new chapter's body. No valid
  `chapter` → §3.1's fallback: the staged prose folds into the open chapter. A pending
  rewrite/regenerate target (§5) overrides placement for exactly that one beat.

The rest of the done event, in order:

1. **Picks-diff** vs the previous beat's picks → added ids render as skill cards (from the
   catalog) at the top of the open chapter; removed ids fold their card to a receipt line.
2. `ask` present → choice cards render inline at the chapter's tail + the writing line under
   them ("or write your own"); the **baton** rules from onboarding-cards apply unchanged
   (one hot surface — the cards OR the writing line).
3. Answer submitted (card click or line Enter) → sends the `[card]`-protocol message
   (unchanged); the answer **fossilizes** as the serif line; cards mark picked/dim.
4. `ready: true` → the **signature close** renders as the final chapter: manifest chips
   (baseline 🔒 + picks with price labels), the name on the signature line, Build.

**Errors:** a `type: error` SSE event renders as a **brass error line in the open
chapter** (the dossier's form of today's `**[error]**` bubble), re-arms the writing line,
and releases any card-held baton — the participant can always continue.

**Beats replay (reload survival):** the server accumulates every beat on the session
(`ChatSession.beats`); the page stores its session id in `sessionStorage` and, on load,
replays `GET /api/session/{id}/beats` to re-render the whole document before reconnecting.
A page reload with a live server therefore restores the dossier. Persistence across studio
restarts stays a non-goal (§8).

### 4.2 The journey rail

Derived, never stored: milestones = the fixed phase set; a milestone is *done* when a later
phase has been seen, *current* when it's the open chapter's phase, *upcoming* otherwise;
brass *stale* while a rewrite is in flight below it. Clicking a done milestone scrolls to
that phase's first chapter. Hidden < 900px (the column is the experience on small screens).

### 4.3 Build as the final chapter (D1c boundary)

Pressing Build routes through the existing `shelfBuild → buildAgent` path; the existing
build panel (compose stream, tweak log, connect rows, install gate) renders **embedded as
the final chapter's content** (a `morph` — the signature section becomes the build log), not
re-implemented. D2 then dissolves the connect rows into native `connect`-phase chapters with
`step`/`key-field` blocks; the compose/tweak stream stays an embedded log block permanently
(it is a machine process; a log is its honest form).

### 4.4 What replaces what

| Today (workshop mode) | Dossier |
|---|---|
| Chat pane + bubbles | The document column (chapters + fossilized answers) |
| Composer box | The blended writing line (baton-aware) |
| `#askrail` ask cards | Inline choice cards in the open chapter |
| "Your agent" panel | The signature close's manifest (+ rail = progress) |
| Build panel pane | Embedded final-chapter content (§4.3) |
| Shelf drawer | **Kept** — browse-the-catalog overlay, opened from a quiet header affordance. A manual add/remove sends `[studio event] participant added/removed <id> via the shelf`; the agent re-asserts whole-state picks; the manifest renders **from studio picks only** — the signed manifest cannot diverge from the shelf |
| Status chip handshake | Kept in the header; additionally the welcome chapter renders on first token (the verifiable handshake, dossier form) |
| Header advanced controls (Load/Download `spec.json`, evals toggle, Export) | **Dropped** in dossier mode — still reachable via `?mode=architect` |

## 5. Rewrite ⟲ and regenerate ⟳ (hidden `[studio event]` verbs)

Both reuse the onboarding-cards `[studio event]` protocol (suppressed from rendering; the
agent is prompted they exist):

- **Rewrite** (on every fossilized answer, hover ↺): the answer melts back into the writing
  line (pre-filled); choice sections **reopen their cards** re-choosable; chapters below go
  `stale` + rail milestones brass; note bar "⟲ rewriting §NN — the architect will reconsider
  everything below". Submitting sends
  `[studio event] rewrite — question: "<q>" — previous answer: "<old>" — new answer: "<new>"`.
  The agent re-emits full state; the beat re-fossilizes with the `rewritten ↺` chip.
  **Re-settle, honestly scoped:** picks and choice cards re-settle **deterministically**
  from that beat's whole state (cards may appear/fold; an ask whose options reference a
  now-dropped pick folds). Downstream **prose is not rewritten** — stale sections keep
  their text with a quiet "written before your rewrite of §NN" mark until the participant
  regenerates them (⟳). One rewrite in flight at a time (baton holds it).
- **Regenerate** (quiet ⟳ on each chapter head): sends
  `[studio event] regenerate chapter "<title>" — rewrite it fresh, same facts`. The next
  turn's beat **replaces that chapter's agent prose only, in place** (via the pending-target
  override below) — fossilized answers and choice cards in the chapter are preserved
  untouched. This is the recovery path for a mangled render and the facilitator's "try
  that again" button.
- **Pending-target override (targeting rule for both verbs):** sending either verb sets a
  pending target on the page; the NEXT done beat routes to the requested chapter
  **regardless of the `chapter.title` the agent emits**, consuming exactly one beat (the
  target clears on that beat, success or error). A retitled rewrite/regenerate turn can
  therefore never open a duplicate section; §4.1's normal settle rule resumes on the
  following beat.
- Prompt contract addition: *`[studio event] rewrite`/`regenerate` messages come from the
  page, not the participant's voice. On rewrite: re-assert the full studio state consistent
  with the new answer (drop picks that no longer fit — the whole-state rule does the rest)
  and continue from that chapter. On regenerate: re-write that chapter's content; do not
  advance the interview.*

## 6. The finale — sign · bind · assemble · first breath · launch

The close is where the outcome bar gets cashed; it must not be a progress bar. Five beats,
one orchestrated sequence (proofed in `v1c-finale.html`, approved by Lucas 2026-07-02;
SKIP affordance always visible; `prefers-reduced-motion` collapses every beat to a cut):

1. **The Signing.** Build clicked → the agent's name inks itself across the signature line
   (clip-path stroke-in), the writing line retires, the button flips to `✓ signed`. The
   document is closed for edits; everything after is consequence. **Gating & failure:**
   Build enables only with non-empty picks AND a name — mirroring the existing gates, with
   the existing server preflight still behind it. A composer error renders **inside the
   ceremony** as a brass error line with an **un-sign / retry** affordance: the signature
   un-inks and the document reopens for edits. Rebuilding after connect re-runs the
   connect chapters — the rebuild `rmtree`s the agent home including its `.env`, a
   documented consequence, not a bug.
2. **The Binding.** The dossier compresses into a small table-of-contents card — chapter
   numbers + the participant's own serif answer fragments — stamped "N chapters · M answers ·
   signed <date>". Honest theater: their answers genuinely feed the personalize pass.
3. **The Assembly.** The bound card slides into an *anatomy* view — organs slotting in
   with ticks while the REAL compose/tweak log lines run as mono captions beneath (the
   existing build stream, re-skinned; truth under the theater). **Ticks are event-driven,
   never timed**, and each organ is mapped to its real build-stream event: the wiki-brain
   spine ← the `component: vault` compose event; the shell ← the **new `component: shell`
   compose event added by D0** (§7.0); each picked skill ← its `skill:<id>` compose event;
   the identity organ ← the tweak pass's **identity/vault substitution stage**, whose
   caption shows the substitution lines that actually run. The copy beats land fast
   (compose is deterministic file copying — by design it cannot fail creatively). **What
   Assembly does NOT claim:** "writes your dossier answers into your skills" — per-answer
   skill personalization is r1-B, and that narration is **explicitly deferred to r1-B**;
   until then the identity organ's caption says only what actually runs. No fixed timers
   anywhere in the sequence. This replaces the raw build-panel log as the D1c §4.3 embed's
   visible face; the raw log stays reachable behind a disclosure.
4. **First Breath.** The page goes quiet; the status chip hands over — `architect` →
   `<name> · live` (sapphire pulse). Then the composed agent's first words stream in, typed:
   a REAL one-turn `claude -p` greeting run with cwd = the composed agent home (D0's
   raw-skills form is what makes the agent loadable this way), tool-less, prompted to greet
   the participant by name and reference their actual choices — one turn, new endpoint
   `POST /api/first-breath`, SSE-streaming tokens into the beat. **Reuse seam:** the
   endpoint reuses `stream_parser.parse_line` + `dedup_text` and the `wait_for` budget
   idiom — NOT `ChatSession`'s flag set (its cwd/tempdir, `--system-prompt-file`, and
   exclude-dynamic flags are exactly what first breath must not use). Flags:
   `--allowed-tools ""`, `--strict-mcp-config` with an empty MCP config, and **no
   prompt-replacement flags** — the agent home's own `CLAUDE.md` must load. **Path
   provenance:** the endpoint derives the agent-home cwd **server-side from its own
   compose result** (`done.plugin_path`) — never from the request body, so a localhost
   POST can never spawn `claude` in an arbitrary directory. **No integration keys are
   needed for this** — building and talking run on the participant's existing Claude Code
   auth; only service-touching skills need the connect step. First Breath therefore lands
   BEFORE connect, and the greeting prompt tells the agent which integrations are still
   unconnected so its first words can hand the participant into the connect chapters ("I'm
   ready to sweep your inbox as soon as we connect Linear — that's our next page"). The
   greeting prompt is **constrained to composed reality**: it may reference the
   participant's name, picks, and unconnected integrations, and must promise nothing
   unbuilt — no scheduling promises until r1-A ships the always-on scheduler. If the turn
   errors or exceeds a ~20s budget, the beat falls back to a static first-words card quoting
   the personalized identity (flagged fallback — the ceremony never hangs the room).
5. **The Launch Card.** The birth certificate: name in serif, parts manifest, **integration
   chips rendered pending** — they fill in live as each connect chapter completes. The
   sequence order is fixed: assembly → first breath → **connect chapters** → the launch
   card *completes* (it appears with the finale but finishes with connect). The old
   wizard rule that gated the install line on connected keys is **explicitly retired in
   dossier mode** — the launch command is real from first render; the chips carry the
   connect state. (`v1c-finale.html` shows the chips already green — stale relative to
   this revision.) The exact launch command — `cd dist/<name>-cos && claude` — is read
   from `done.install` (the composer's `install` field, server-side; never hardcoded; D0
   rewrites that field), with a copy button, and "three things to ask it first" derived
   from picks (each skill's `brief` supplies its line).

D0 makes beats 4–5 real; beats 1–3 + 5 re-skin surfaces the D1 slices already own. **D1c —
the slice that builds this sequence — is gated on D0 (§7.1)**, so the cut-line inversion
(the finale shipping before raw-skills) cannot occur by plan; the static first-words card
remains as the runtime fallback only.

## 7. Slices (each independently shippable, in order)

### 7.0 D0 — raw-skills packaging (the destination becomes real)

Implements `docs/specs/2026-07-02-workshop-lean-distribution-design.md` §5 — the design is
already fixed there; this slice is its execution, absorbed here because the finale depends
on it. The composer emits an **agent home** instead of a plugin: `.claude/skills/<id>/…`,
`.claude/agents/context-gatherer.md`, root `.mcp.json`, a generated `CLAUDE.md` —
**deterministic per lean §5**: identity, owner name, vault path, the picked-skill roster,
and nothing more (**no personalization claim** — personalization lives in the tweak pass,
not this file) — the vault written at the **resolved `vault_dir`** (the participant's
second brain when onboarding completed one, `<home>/vault/` default) with that path
written into `CLAUDE.md`, and `.env` — and **stops emitting** `.claude-plugin/plugin.json`
+ `marketplace.json`. `composer.py`'s `install` field becomes `cd <dir> && claude`;
`keys.py`/`server.py` `.env` mechanics unchanged (same tree, same file). D0 also adds a
**`component: shell` compose event** (the finale's shell organ ticks on it, §6 beat 3).
Includes the **reference-path invariant test**: every reference mentioned in a shipped
SKILL.md resolves from the agent-home root.

Substrate cleanup (ROADMAP "Cleanup / later": `chief-of-staff/.claude-plugin/`,
`marketplace.json`, plugin-install wording in the substrate README/INSTALL) rides along —
but it is **not docs-only**: `.claude-plugin/plugin.json` and `marketplace.json` are
composer *inputs* today (`composer.py` reads them; `test_composer_package.py` asserts
them), so their removal is **coupled to the composer/test rewrite**. Commit order: first
the commit in which the composer stops reading those files (tests rewritten alongside),
then the removal commit; the revert path is the reverse order. The `assemble_manifests`
`.mcp.json` discord-trim behaviour must survive the rewrite. Placeholder-contract scan
mandatory. One accepted gap: the GUI's install copy (`installLineHtml`) still shows the
plugin-form command after D0 — that fix is **deferred to D1a** (which owns that surface);
the stale copy in the D0→D1a window is accepted and flagged here. **D0 touches no
contested frontend files and is the ONE slice executable before onboarding-cards lands**
— it is also the highest-leverage slice for the workshop room (participants type
`cd <dir> && claude` and talk to what they built).

### 7.1 D1 — the dossier shell + interview journey (split: D1a → D1b → D1c)

**D1a — the document shell (the floor):** extractor `chapter` (+ `blocks`
parsed-not-rendered) · prompt contract §3.3 · `dossier.css`/`dossier.js` · full-page
takeover in workshop mode (chat UI stays for architect) · chapters + live-edge staging
(§4.1) · writing line · inline asks + baton · picks-diff cards · journey rail · **beats
replay** (`ChatSession.beats`, session id in `sessionStorage`,
`GET /api/session/{id}/beats` — §4.1) · **`?ui=chat` escape hatch** (§1: the current
workshop chat skin on the same backend, kept until dossier parity is proven at a dress
rehearsal, removed in a later cleanup slice) · in dossier mode the C3 onboarding walk
**mounts as its existing overlay above/before the document** until D3 re-skins it · the
GUI install-copy (`installLineHtml`) fix deferred from D0 (§7.0) · shelf drawer kept as
overlay (event sync per §4.4).

**D1b — the revision verbs:** rewrite ⟲ + regenerate ⟳ (§5: pending-target override,
honestly-scoped re-settle, `rewritten ↺` chips, stale marks) · the §5 prompt-contract
addition.

**D1c — signature close + finale (gated on D0):** the signature close (§4.1's `ready`
step) → embedded build panel (§4.3) · the finale beats (§6: sign · bind · assemble ·
first breath · launch card) · `POST /api/first-breath` (§6 beat 4). Must not start
before D0 lands — the first breath and launch command are only real in raw-skills form.

### 7.2 D2 — build & connect as native chapters

`blocks` rendering (`step`/`key-field`/`checklist`/`note`/`skill-card`) · connect rows
dissolve into `connect`-phase chapters (key wizard + smoke tests hosted in `key-field`
blocks, endpoints unchanged) — hosted via a **named extraction**: factor
`wireKeyRow(rowEl, integration, tree)` out of `wireWizard` (app.js), consumed by BOTH the
build-panel wizard and the dossier `key-field` block, the google `persist_only` branch
included; validation rule: a `key-field` with an unknown `integration` id → block skipped
(§3.2) · prompt contract gains the block-authoring section (only
emitted in build/connect phases). **Guide content** (which steps for Discord/Linear/Google)
remains ROADMAP item 7 — D2 is the rendering vehicle, not the content.

### 7.3 D3 — intake as the opening chapter

The onboarding walk (welcome → introduce yourself → materials drop CV/LinkedIn/screenshots →
second-brain choice) re-skins from chat-cards into `welcome`-phase dossier chapters: the
drop zone and name/path fields render as chapter content; same `onboarding.py` endpoints,
state file, staging, and `[studio event]` completions — **zero backend change**. C3's
chat-card walk remains the fallback until D3 lands.

### 7.4 Reused from onboarding-cards (not rebuilt)

Ask channel (`studio.ask`, §4 of that spec) · `[card]` / `[studio event]` message protocol +
bubble suppression · `cards.js` card primitive + rise/fold/baton/morph motion ·
`onboarding.py` + endpoints · the extractor's tolerant-parsing conventions.

## 8. Non-goals

- **Architect mode**: byte-identical, including `build_system_prompt()` and its tests.
- **Conversation persistence across studio restarts** (ROADMAP product requirement) — not
  this spec. Beats replay (§4.1) makes a page reload recover against a live server, but a
  studio restart still starts fresh. (The server-side beat list is the natural future
  persistence unit; noted, not built.)
- **Connect guide content** (ROADMAP item 7). (Raw-skills packaging is NO LONGER a
  non-goal — it is slice D0.)
- **No new deps, no build step** — vanilla JS + CSS, stdlib-only server additions.
- **`chief-of-staff/` and `agent-architect/` untouched by D1–D3.** D0's scoped substrate
  cleanup (§7.0: `.claude-plugin/`, `marketplace.json`, README/INSTALL install wording)
  is the sole, deliberate exception.

## 9. Docs checkpoints (per slice)

Docs ride each slice's landing PR — never a trailing docs pass:

- **Every slice:** `docs/ROADMAP.md` + `CHANGELOG.md` updated in the landing PR
  (D0: ROADMAP item 3 → shipped; D1a–D1c: a status note on ROADMAP item 2).
- **D0:** the substrate `README`/`INSTALL` rewritten from plugin-install wording to the
  raw-skills `cd <dir> && claude` form (coupled to §7.0's packaging switch, same PR).
- **D1a:** FACILITATOR runbook entries — ⟳ regenerate as the in-room recovery, the
  first-breath static fallback, reload recovery via beats replay, and the `?ui=chat`
  escape hatch — plus the SETUP/GUI install-copy fix (`installLineHtml`, deferred
  from D0, §7.0).

## 10. Testing

- **D0 composer** (`test_composer_*.py`): output tree is agent-home form (`.claude/skills/`
  present; `plugin.json`/`marketplace.json` ABSENT); `install` field is the `cd` form; the
  reference-path invariant (every reference named in a shipped SKILL.md resolves from the
  agent-home root); generated `CLAUDE.md` carries exactly the lean §5 fields (agent name,
  owner name, resolved vault path, picked-skill roster); the `component: shell` compose
  event is emitted; the `assemble_manifests` `.mcp.json` discord-trim survives the
  rewrite; placeholder-contract grep on the substrate diff.
- **First breath** (`test_server.py` + integration): `/api/first-breath` streams tokens for
  a composed home and falls back cleanly on error/timeout; **preflight negative: no
  composed home for the session → an error event, never a spawn**; one real-turn smoke
  with a real composed agent (fresh uuid4 session id).
- **Beats replay** (`test_server.py`): `GET /api/session/{id}/beats` returns the
  accumulated beats after several turns; unknown session id → 404; the returned beats
  carry prose + studio state sufficient to re-render the document.
- **Extractor** (`test_studio_extractor.py`): chapter valid/malformed/absent; unknown phase;
  title >80 chars; blocks vocabulary (valid, unknown type skipped, malformed → `[]`);
  **per-block field negatives: `step` without `text` → skipped; `key-field` with an
  unknown `integration` id → skipped**; chapter failure never kills picks/ask sync.
- **Prompt** (`test_system_prompt.py`): workshop contract contains the chapter instruction +
  phase set + rewrite/regenerate section; architect prompt byte-identical.
- **Server** (`test_server.py`): done event carries `chapter` through SSE.
- **Integration smoke**: a real workshop turn emits a parseable chapter with a valid phase
  (fresh uuid4 session ids, per the landed convention).
- **Manual browser checklist** per slice. The chapter-grouping algorithm has **no JS test
  runner** — the named steps below plus the integration smoke are its net.
  **D1a:** scrollytell feel end to end; a same-title turn continues the open chapter (no
  new heading — the staging is invisible); a new-title turn breaks a new numbered section;
  rail states; a forced `type: error` renders the brass error line, re-arms the writing
  line, and releases a card-held baton; reload mid-journey restores the document (beats
  replay); `?ui=chat` renders the old workshop chat on the same backend; reduced-motion;
  `?mode=architect` unchanged; workshop-room legibility on a shared screen.
  **D1b:** rewrite round-trip (stale → re-settle, "written before your rewrite of §NN"
  marks on downstream prose); regenerate replaces agent prose in place with fossils and
  choice cards intact (a retitled regenerate turn does not open a duplicate section).
  **D1c:** the full finale sequence with SKIP; the first-breath fallback path; launch-card
  chips pending → filling as connect completes.
  **D2:** a connect chapter end to end (steps render; `key-field` hosts the real smoke
  test via `wireKeyRow`; unknown block types and unknown `integration` ids skipped
  silently).
  **D3:** intake as the opening chapter (drop zone, name/path fields, `[studio event]`
  completions, same endpoints) with the C3 overlay retired.

## 11. Risks

1. **Branch collision (live now):** onboarding-cards is mid-implementation in the same
   repo. This spec lands as docs on `main` safely; **D1–D3 must not be executed** until
   `feat/onboarding-cards-impl` merges, then the implementation branch bases on that.
   **D0 is exempt** (composer/substrate-side, no contested files) and may execute
   immediately on its own branch. The execution handoff must restate this gate per slice.
2. **Packaging switch day-of-workshop:** D0 changes the participant install flow the night
   before the room. Mitigation: the reference-path invariant test + a fresh-machine dress
   rehearsal (ROADMAP "Cleanup / later" E2E item) before the room; the old plugin form
   remains one `git revert` away.
3. **Model contract compliance:** the agent may omit/mangle `chapter` under pressure. Fallback
   (append to open chapter) keeps the page whole; ⟳ regenerate is the in-room recovery; the
   integration smoke keeps the prompt honest.
4. **One page, growing DOM:** a session is tens of beats — trivial. Token streaming at the
   live edge (§4.1) reuses the existing per-turn render throttle.
5. **Fence discipline:** `chapter` lives inside the existing ```studio block — no new fence,
   so the spec/json/studio disjointness rules are untouched.
