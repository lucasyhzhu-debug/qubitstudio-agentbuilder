# Studio SapphireOS reskin + conversation-driven journey

**Date:** 2026-07-02
**Status:** Draft — pending shipshape gate
**Owner:** Lucas
**Target:** QubitStudio "Build Your Own Chief of Staff" workshop, Friday 2026-07-03
**Depends on:** v0.1.0 migration (shipped) · qubit-site design system (`github.com/Nicegarrry/qubit-site`, `app/globals.css`)
**Supersedes:** `docs/specs/2026-07-02-studio-theme-toggle-design.md` (uncommitted draft — its
dark/light toggle is dropped; its hardcoded-color audit is folded into §3.4)

## 1. Problem

Two defects in the participant-facing studio, both visible in the first minute of the workshop:

1. **Look & feel.** The studio ships a dark navy hacker palette that shares nothing with the
   QubitStudio brand. qubit-site runs a house design system ("SapphireOS, white-canvas recast" —
   `qubit-site/app/globals.css:38`): white canvas, one sapphire accent, mono uppercase eyebrows,
   hairline rules, soft shadows, four self-hosted fonts. Participants arrive from the site/slides
   into an app that looks like a different company.

2. **Journey dissonance.** The chat and the skill shelf are two disconnected systems. The chat
   runs a *generic* "design any Claude Code plugin" interview (`system_prompt.py` builds
   quiz-bank Q0–Q9; no mention of chief-of-staff, the shelf, or the catalog) and feeds only
   `/api/export`. The shelf feeds `/api/compose` and never reads the conversation
   (`composeAgent(picks, name)` — `app.js:349`). So the agent asks "what agent do you want?"
   while the shelf has already answered "a chief of staff." The lean-distribution spec's stated
   model — *"the conversation is the spine, compose is a tool the conversation drives"* — was
   never wired.

## 2. Decisions (chosen / rejected)

| Decision | Chosen | Rejected & why |
|---|---|---|
| Visual system | **Adopt SapphireOS verbatim, light-only** — lift `:root` tokens + fonts from qubit-site | Dark/light toggle of the current palette (theme-toggle draft): qubit-site has no dark mode; two themes = double QA surface the night before the room |
| Journey shape | **Conversation drives the shelf** — cos-aware interview recommends picks; shelf/panel is the confirmation surface | (a) Guided stepper rebuild: too much layout rework for tonight; a header journey rail gives 80% of the clarity. (b) Two explicit modes: leaves the workshop chat generic — the dissonance survives |
| Prompt home | **Workshop prompt lives in `studio/`** (`system_prompt.py` + catalog injection) | New reference under `agent-architect/`: the workshop interview is studio-specific; agent-architect stays the generic meta-agent (three-unit boundary) |
| Generic architect path | **Kept, demoted** — `mode="architect"` on session creation; header export controls collapse behind an "advanced" disclosure | Removal: load-bearing (13 tests at v0.1.0; export path tested) and it's the post-workshop growth path |
| Chat→shelf channel | **A second fenced block ` ```studio `** parsed server-side like ` ```spec ` | Tool calls / MCP: the chat is deliberately tool-less (`--allowed-tools ""`); fenced-block extraction is the proven pattern (`spec_extractor.py`) |

## 3. Unit A — SapphireOS reskin (`studio/static/` only)

### 3.1 Tokens

Replace the dark `:root` block (`styles.css:2-17`) with SapphireOS values (source:
`qubit-site/app/globals.css:39-59`):

```css
:root {
  --canvas:#FFFFFF; --band:#F7FAFC;
  --sapphire:#306FA8; --sapphire-hover:#1E4C80; --tint:#EEF4FA; --tint-2:#DBE8F3;
  --teal:#347890; --brass:#C2791A; --brass-tint:#F6EDDC;
  --ink:#141A21; --ink-2:#3A4550; --ink-3:#6B7681; --ink-4:#9AA4AD;
  --rule:rgba(20,26,33,0.10); --rule-strong:rgba(20,26,33,0.20);
  --ok:#2E7D5B; --warn:#B5852B; --err:#B6463C;              /* SapphireOS status set */
  --r-card:14px; --r-btn:10px; --r-pill:999px;
  --sh-sm:0 1px 2px rgba(20,26,33,.04),0 2px 8px rgba(20,26,33,.05);
  --sh-md:0 2px 6px rgba(20,26,33,.06),0 10px 28px rgba(20,26,33,.09);
  --sh-lg:0 12px 40px rgba(20,26,33,.11);
  --display:'Bricolage Grotesque',system-ui,sans-serif;
  --body:'Hanken Grotesk',system-ui,sans-serif;
  --mono:'JetBrains Mono',ui-monospace,monospace;
  --wordmark:'Crimson Pro',Georgia,serif;
}
```

Old token names (`--bg --panel --panel2 --line --ink --mut --dim --acc --acc2 --ok --warn
--pink --sans`) are **renamed at every use site** in `styles.css` + `shelf.css` (mapping:
bg→canvas, panel→white card, panel2→band, line→rule, mut→ink-3, dim→ink-4, acc→sapphire,
acc2→sapphire, pink→err, sans→body). A grep for the old names must come back empty — no alias
layer left behind.

### 3.2 Fonts

Copy from `qubit-site/public/fonts/` into `studio/static/fonts/` with the same `@font-face`
declarations: BricolageGrotesque.ttf (variable 200–800), HankenGrotesk.ttf + italic (variable),
JetBrainsMono-Regular/-Medium.woff2, CrimsonPro-Regular/-Italic.woff2. All four are OFL-licensed
Google Fonts — safe for the public repo (~1.5 MB total, local-first so no CDN dependency in the
room). Add `# fonts are OFL (see qubit-site)` provenance note in `studio/README.md`.

### 3.3 Component translation (signature moves)

- **Header** → SapphireOS nav: sticky, 62px, `rgba(255,255,255,.92)` + `backdrop-filter:blur(8px)`,
  bottom hairline. Left: the CSS-drawn qmark (2×2 rounded squares, one filled) + "qubit" in
  Crimson Pro + `AGENT STUDIO` mono eyebrow. Status becomes a mono chip with the SapphireOS
  pulsing live-dot (`@keyframes pulse`) — grey "connecting…" → sapphire "agent live" (§4.6).
- **Eyebrows everywhere**: `10.5px JetBrains Mono, 500, uppercase, +0.14em, --ink-3` replaces
  the current all-caps mono panel labels (IDENTITY, COMPONENTS, …) — a direct idiom match.
- **Cards** (`.bp-card`, `.shelf-card`, wizard rows): white, `1px var(--rule)`, `--r-card`,
  `--sh-sm`; hover lift `translateY(-3px)` + `--sh-md` on interactive cards.
- **Chat**: mirrors qubit-site's concierge — `#log` on `--band`; user bubbles solid sapphire,
  white text, 12px radius with a 4px tail; assistant bubbles white with hairline + tail.
- **Buttons**: `.btn-primary` (solid sapphire → hover deepen), `.btn-outline`, `.btn-ghost` with
  the sliding `→`; Send + "Build my agent" are primaries.
- **Price tags / chips** → SapphireOS pills: `--tint` bg + `--tint-2` border; tiers t-free →
  `--ok` tinted, t-one → `--warn` tinted, t-many → `--err` tinted (keep the punched-hole detail).
- **Shelf drawer**: white panel, `--sh-lg`, band-colored body; backdrop scrim stays dark-based.
- **Focus/motion**: sapphire focus ring `0 0 0 3px rgba(48,111,168,.35)`; 150–180ms ease
  transitions; keep the existing `prefers-reduced-motion` fallback in `shelf.js:118`.

### 3.4 Hardcoded-color fixes (folded in from the superseded toggle draft)

- `#composer button[type=submit]` + `.brief-btn`: text `#04060c` → `#fff` (on solid sapphire).
- `.shelf-card.on`: `background:#1d2235` → `--tint` + `1.5px` sapphire border.
- `.bubble.assistant strong { color:#fff }` → `color:var(--ink)`.
- `.bubble.user` `color:#fff` stays (now on solid sapphire).

### 3.5 Non-goals (Unit A)

No dark mode. No layout re-architecture (the 1fr/1fr grid + drawer stay). No new JS for the
reskin except the qmark/wordmark markup in `index.html`.

## 4. Unit B — conversation-driven journey

### 4.1 Session modes (`server.py`, `system_prompt.py`)

`POST /api/session/new` accepts optional JSON body `{"mode": "workshop" | "architect"}`;
**default `workshop`** (no body → workshop). `write_system_prompt` gains the mode: architect
mode writes today's prompt unchanged; workshop mode writes `build_workshop_prompt()`. Cache
files split: `.cache/architect-system-prompt.md` / `.cache/workshop-system-prompt.md` so modes
don't clobber each other. The UI reaches architect mode via `?mode=architect` on the page URL
(read by `app.js:start()`); no visible toggle.

### 4.2 The workshop system prompt (`build_workshop_prompt`)

New builder in `system_prompt.py`, composed of:

1. **Role intro**: "You are the participant's agent-architect for the Build-Your-Own-Chief-of-Staff
   workshop. Everyone in the room is building a personal chief-of-staff agent on a fixed
   substrate; your job is to interview them about their working life and recommend which shelf
   skills belong in THEIR build. You only converse and emit the studio block — no tools." Keep
   the existing ignore-superpowers guard line verbatim (`system_prompt.py:17-18`).
2. **The substrate & shelf, injected live from `catalog.json`** (same read the server already
   does at `/api/catalog`): baseline items (locked, always built) and each shelf item's `id`,
   `name`, `what`, `deliverable`, `requires`, `needs_skills`, `cost.label`. The model must only
   ever recommend real catalog ids.
3. **Interview guidance**: ask about work life, one topic at a time (inbox volume and where
   tasks live → `tasks`; morning routine → `briefing`; meeting/scheduling load → `scheduling`;
   people/relationship tracking → `crm`; screenshot habits → `intake`; appetite for an always-on
   channel → `drain`). Recommend, explain the price tag (integrations required), respect
   `needs_skills` prerequisites, and never oversell `drain` (tier "many") to a first-timer.
4. **Studio contract**: after EVERY turn emit the full current state as one fenced block
   labelled ` ```studio `:

   ```studio
   { "picks": ["crm", "briefing"], "name": "my-cos" | null, "ready": false }
   ```

   `picks` = shelf ids currently recommended+accepted; `name` once the participant chooses one;
   `ready: true` only when the participant confirms the build. Whole block every turn, no diffs,
   no prose inside the fence.

Quiz-bank Q0–Q9 and the architecture-spec schema are **not** included in workshop mode — the
spec artifact isn't this journey's output. Architect mode keeps them all.

### 4.3 Studio-block extraction (`studio_extractor.py`, new)

Sibling of `spec_extractor.py`, same shape: `extract_studio(assistant_text, catalog_ids) ->
dict | None`. Last ` ```studio ` fence wins; `json.loads`; validation: dict, `picks` a list —
unknown ids are **dropped with the valid remainder kept** (a hallucinated id must not kill the
sync), `name` str|None, `ready` coerced to bool. Returns None on malformed JSON so the caller
keeps prior state. `ChatSession` gains `self.studio` alongside `self.spec`; `send()` runs both
extractors and the `done` event carries `{"type":"done", "spec":…, "studio":…}` (either may be
None). `app.js:stripSpec` regex extends to `(?:spec|json|studio)` so the block never flashes
in chat.

### 4.4 Chat→shelf sync (frontend)

`shelf.js` exposes one new function on `window`: `shelfSync({picks, name})` — replaces the
`selected` map with the catalog items for `picks` (marking cards `.on.recommended`, with a
mono `✓ recommended` eyebrow), fills `.shelf-name` if empty and `name` given, re-renders foot +
badge. User toggles after a sync still work (the map is the single source of truth; the next
sync from a later turn re-asserts the agent's view — acceptable for the workshop: the agent is
told the current picks in the conversation, so divergence self-corrects conversationally).
`app.js` calls `window.shelfSync(ev.studio)` on `done` when `ev.studio` exists.

### 4.5 The right panel — "Your agent" (workshop mode)

`renderBlueprint` stays for architect mode. Workshop mode renders `renderAgentPanel(studio,
catalog)` into the same `#blueprint` aside: an eyebrow `YOUR AGENT`, the baseline (two locked
rows), a row per picked skill (name + price pill), an `INTEGRATIONS` eyebrow with the union of
`requires` as chips, the agent name, and a primary **Build my agent ▶** button that calls the
same `buildAgent()` path (shelf foot logic extracted to be callable from both). Empty state:
"Talk to the architect — your agent takes shape here." The panel replaces the empty blueprint
as the participant's persistent mirror of the conversation; the drawer remains the browse-all
surface via the header button.

### 4.6 Handshake + seed

Seed message becomes `'Begin the workshop interview.'` in workshop mode (architect mode keeps
the current string); the `app.js:41` suppress check matches whichever seed was sent. Status
chip: `starting…` (grey) → on session `ready` → on **first streamed token** flip to `agent
live` with the sapphire pulsing dot — the roadmap's "verifiable handshake, not a silent
spinner", with zero new endpoints.

### 4.7 Advanced-path demotion

`Load spec.json` / `Download spec.json` / `evals` / `Export .plugin` move into a collapsed
`advanced ▸` disclosure at the header's right edge (plain `<details>`; no behavior change to
the functions). In architect mode (`?mode=architect`) the disclosure starts open.

### 4.8 Non-goals (Unit B)

Custom vault location, conversation persistence across restarts, per-skill personalize Q&A
(r1-B), raw-skills packaging — all stay separate roadmap items. The studio block schema is
designed to grow (e.g. a future `personalize` key) but ships with the three fields only.

## 5. Build order (risk-sorted, hard cut lines — each lands independently)

1. **B1 — workshop prompt + studio extractor + session mode + chat→shelf sync** (§4.1–4.4, 4.6).
   The dissonance fix. Floor if the evening dies here: the agent talks chief-of-staff and the
   shelf follows it.
2. **A — SapphireOS reskin** (§3). Pure static; parallelizable with B1 (different files except
   `index.html`, coordinate the header block).
3. **B2 — "Your agent" panel + advanced demotion** (§4.5, 4.7). Stretch; the shelf badge +
   drawer already show the synced state without it.

## 6. Testing

Backend (pytest, `studio/tests/`, per the test-per-module pattern):

- `test_system_prompt.py` (extend): workshop prompt includes catalog ids/names + studio
  contract + ignore-superpowers guard; excludes quiz Q0 header and architecture-spec schema;
  architect mode byte-identical to today (all 5 existing tests keep passing).
- `test_studio_extractor.py` (new): valid block; absent → None; malformed JSON → None; unknown
  pick dropped while valid remainder kept; last-block-wins; `ready` coercion.
- `test_server.py` (extend): `session/new` default is workshop (cache file written);
  `{"mode":"architect"}` selects architect prompt; chat `done` event carries `studio` (mocked
  ChatSession, same monkeypatch idiom as `test_chat_streams_tokens_then_done`).
- `test_smoke_integration.py`: keep `test_one_real_turn`; add a workshop-mode real-turn variant
  asserting the reply contains a parseable ` ```studio ` block (marked slow like its sibling).

Frontend (no JS runner in repo): manual verification via `python -m studio` — checklist in the
plan (reskin legibility across chat/shelf/wizard/build panel; shelfSync on a real conversation;
handshake chip; advanced disclosure; `prefers-reduced-motion`).

Placeholder contract: `chief-of-staff/` untouched; no personal values enter the repo (fonts are
public OFL binaries; palette is public site CSS).

## 7. Risks

| Risk | Mitigation |
|---|---|
| Workshop prompt regresses real `claude -p` behavior the night before | Real-turn smoke variant (§6); architect mode untouched as fallback — flipping the default back is a one-line revert |
| Model emits malformed/hallucinated studio blocks | Extractor returns None / drops unknown ids; prior state kept; UI never crashes on a bad block |
| Reskin breaks legibility in a corner (wizard fail states, build log) | §3.4 audit + manual checklist over every panel; single theme keeps the matrix small |
| Two people editing `index.html` (A ∥ B1) | A owns `<header>`; B1 touches only `app.js`/`shelf.js`; B2 rebases on both |
| Fonts bloat the public repo | ~1.5 MB one-time, local-first for a flaky-wifi room — accepted |
