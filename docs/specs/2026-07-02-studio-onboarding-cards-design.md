# Studio onboarding journey + guided card framework

**Date:** 2026-07-02
**Status:** Draft — pending shipshape gate 1
**Owner:** Lucas
**Target:** QubitStudio "Build Your Own Chief of Staff" workshop
**Depends on:** the QubitStudio journey slice (`docs/specs/2026-07-02-studio-qubitstudio-journey-design.md`,
plan `docs/plans/qubitstudio-journey.md`) — workshop session mode, ` ```studio ` extractor,
`shelfSync`, and the "Your agent" panel. That slice is **in flight on
`feat/qubitstudio-journey-impl`**; this spec targets the post-landing state and must not be
planned/implemented until it merges.
**Proofing artifacts:** `.superpowers/brainstorm/412-1782986830/content/onboarding-guided-v3.html`
(the locked walk) and `question-card-framework-v2.html` (the locked component), gitignored.

## 1. Problem

Three gaps in the participant's first minutes, measured against the workshop outcome bar
(participants pay $1200/session and must feel the value, feel EMPOWERED, feel MORE PRODUCTIVE,
and find the journey ENGAGING):

1. **Cold open.** The studio drops straight into a chat. There is no welcome, the agent knows
   nothing about the participant, and the interview starts generic. The roadmap's product
   requirements already demand a custom vault location and a verifiable first-run handshake;
   nothing yet asks *who the participant is*.
2. **No shared memory.** The architect (studio chat) and the composed chief of staff have no
   common knowledge of the participant. The vault is created only at compose time, at a
   hardcoded `dist/<name>-vault` path — the participant never chooses their "second brain"
   home, and nothing seeds it with an understanding of them.
3. **One-off UI patterns.** The journey ahead needs step-by-step guided interactions in at
   least four places — onboarding, mid-interview questions, per-skill personalization (r1-B),
   and the connect/API-key wizard — and without a shared primitive each will be designed and
   animated ad hoc.

## 2. Decisions (chosen / rejected)

| Decision | Chosen | Rejected & why |
|---|---|---|
| Onboarding shape | **The guided walk** — cinematic full-screen fade-in, then the live agent narrates on the left while the right panel is the single action surface, strictly one step at a time | (a) Full-screen wizard gate: agent offstage until the end — weakest empowered beat. (b) Parallel interview+intake: participant cannot drop files and answer questions at once (user-rejected in proofing) |
| Narration source | **Live agent throughout** — the real workshop `claude -p` session runs from the reveal; the UI sends bracketed `[studio event]` messages it never displays; every visible bubble is genuine model output | Scripted concierge lines: bulletproof but the onboarding stops being the participant's first real agent demo — weaker $1200/empowered beat. Kept as *failure fallback only* (§5.6) |
| Materials intake | **Drop-copies + folder-path field** — dropped files are read client-side and saved (via the local server) into the second brain's inbox; a path field registers big local folders without copying | Typed-paths only: browsers cannot reveal paths of dropped files, and typing paths is hostile UX. Drop-only: large folders (notes vaults, essay dirs) shouldn't be copied wholesale |
| Upload transport | **JSON + base64** (`FileReader` client-side, 20 MB/file cap) | `multipart/form-data`: FastAPI needs the `python-multipart` package — a new bootstrap dependency for zero UX gain at workshop file sizes |
| Card UI channel | **Reuse the ` ```studio ` block** — it gains an optional `ask` field | A second fenced block or MCP/tool calls: the chat is deliberately tool-less; the studio block is already extracted, validated, and shipped on every `done` event |
| Second brain vs vault | **They are the same directory** — the onboarding-chosen path becomes compose's `vault_dir`; onboarding seeds it, compose scaffolds the full template into it | A separate "profile store" merged later: two memory homes contradicts "the start of the one wiki brain" and doubles the path plumbing |
| Profile writing | **Server writes `profile.md` from the distiller's stdout** | Giving the distiller a `Write` tool: needless permission surface; stdout capture is deterministic and testable |
| Framework scope | **Card framework + `ask` channel + onboarding ship now; personalize (r1-B) and connect adopt the framework in their own slices** | Building all four producers now: multi-subsystem slice, undeliverable before the workshop |

## 3. Unit C — the guided card framework (`studio/static/cards.js` + `cards.css`, new)

One reusable primitive: a **card** rendered into the right-panel rail (the `#blueprint` aside
in workshop mode), with four producers — onboarding steps, the architect's mid-conversation
asks, per-skill personalization (r1-B, later), and the connect/key walkthroughs (later).

### 3.1 Card contract

```json
{
  "id": "briefing-time",
  "producer": "onboarding | ask | personalize | connect",
  "kind": "question | files | path | keys",
  "eyebrow": "personalize · briefing",
  "progress": {"i": 2, "n": 4},
  "title": "When should your morning briefing land?",
  "why": "It compiles overnight — pick when it's waiting for you.",
  "options": [
    {"id": "a", "label": "07:30 weekdays", "why": "before the day starts — the default rhythm"}
  ],
  "multi": false,
  "allow_custom": true,
  "skippable": true
}
```

- `kind: "question"` renders options + (always in v1) the open write-your-own lane.
  `files` renders the drop zone + folder-path field; `path` a location input with a default;
  `keys` is **reserved for the connect slice** (schema noted here so it isn't redesigned:
  numbered steps, an open-URL button, paste fields, a Test action wired to `/api/keys/test`).
- `progress` and `why` are optional; `options[].id` defaults to `a`, `b`, … when absent.
- Answers are a single shape for every kind:
  `{card_id, choices: ["a"], custom: "…"|null, skipped: false, payload: {...}|null}`
  (`payload` carries kind-specific data — registered files, the chosen path).

### 3.2 JS API (vanilla, no new dependencies, IIFE like `shelf.js`)

```js
window.cards = {
  show(card, onAnswer),   // rise-in; returns when answered/skipped via onAnswer(answer)
  queue(cards),           // render upcoming cards ghosted below the hot one
  fold(cardId, receipt),  // compress an answered card to a one-line receipt, dimmed
  morph(html),            // replace the folded stack with what it built (e.g. Your-agent panel)
  baton(holder)           // 'card' | 'composer' — exactly one hot surface (§3.3)
};
```

The producer owns routing: onboarding's `onAnswer` calls `/api/onboarding/*`; the ask
producer sends a chat message (§4.2); later producers route to their own endpoints.

### 3.3 Motion vocabulary (four moves, shared by every producer)

| Move | Behavior |
|---|---|
| **rise** | New card enters: 10px translate-up + fade, ~300ms, the same curve as the welcome fade-in (`cubic-bezier(.2,.7,.2,1)`). One card rises at a time |
| **fold** | Answered card compresses to a one-line receipt ("07:30 weekdays ✓") and dims. History stays visible in the rail — never modal |
| **baton** | Exactly one hot surface. `baton('card')` disables the chat composer (visible sleep state: dashed border, "the architect will ask for you in a moment…"); `baton('composer')` wakes it. The sapphire border marks the holder |
| **morph** | A finished sequence is replaced by what it built — onboarding cards become the "Your agent" panel; connect cards will become the green integrations row |

All four collapse to instant cuts under `prefers-reduced-motion: reduce` (same media-query
pattern the journey reskin uses). Styling is SapphireOS tokens only — no new hex values.

## 4. Unit D — the `ask` channel (visual AskUserQuestion for the tool-less chat)

### 4.1 Studio-block extension (`studio_extractor.py`)

The workshop studio block gains an optional `ask` field:

```studio
{ "picks": ["tasks"], "name": null, "ready": false,
  "ask": { "id": "triage-depth",
           "title": "How aggressive should inbox triage be?",
           "why": "Both keep you in control — this sets how much it drafts for you.",
           "options": [ {"id": "a", "label": "Summarize only", "why": "daily digest, you act"},
                        {"id": "b", "label": "Draft replies", "why": "it writes, you send"} ],
           "multi": false } }
```

`extract_studio` returns a fourth key `ask: dict | None`. Validation (tolerant, like picks):
`ask` must be a dict with non-empty str `title` and `options` a list of ≥2 dicts each with a
non-empty str `label`; option `id` defaults positionally (`a`, `b`, …); `why` fields optional
strs; `multi` coerced to bool; `allow_custom` forced `true` in v1. Anything invalid → `ask`
is `None` **and the rest of the block still syncs** (a malformed ask must not kill shelfSync).
A new valid block with no `ask` clears any pending ask (the whole-state-every-turn rule).

### 4.2 The answer path (frontend, `app.js` + the ask producer)

On a `done` event whose `studio.ask` is set, the UI renders the ask card (producer `ask`,
kind `question`) and passes the baton to the card. Submitting sends a normal chat message:

```
[card] How aggressive should inbox triage be? → Draft replies
[card] How aggressive should inbox triage be? → (custom) only newsletters, never clients
[card] How aggressive should inbox triage be? → skipped
```

`[card]` and `[studio event]` (§5.4) messages are **never rendered as user bubbles** — the
card's fold receipt is their visible trace (extend the existing seed-suppression check).

### 4.3 Prompt contract (`system_prompt.py`, workshop mode)

The workshop contract gains an "asking questions" section: *whenever you offer the
participant a small closed set of choices, ALSO emit it as `ask` inside the studio block —
options get a one-line consequence (`why`); at most one pending ask at a time; the reply
arrives as a `[card]` message (a click, a custom-typed answer, or a skip); after emitting an
ask keep the prose above it short and do not restate the options; omit `ask` when nothing is
pending.* This applies to every workshop session, onboarding or not — the interview itself
gets clickable questions, which is the "engaging" outcome working from minute one.

## 5. Unit E — the onboarding journey

### 5.1 State (`studio/onboarding.py`, new; file `studio/.cache/onboarding.json`, gitignored)

```json
{ "name": "Ada",
  "second_brain": "C:/Users/ada/second-brain",
  "materials": { "copied": ["cv.pdf", "linkedin-1.png"], "folders": ["C:/Users/ada/essays"] },
  "completed_at": "2026-07-02T21:14:00Z" }
```

`completed_at: null` (or a missing file) → the UI runs the wizard. `?onboard=1` on the page
URL re-runs it (existing values prefilled; a completed re-run overwrites state). Dropped
files stage in `studio/.cache/onboarding-inbox/` until the second brain exists, then move.

### 5.2 Endpoints (`server.py`, thin wrappers over `onboarding.py` logic)

| Endpoint | Body → behavior |
|---|---|
| `GET /api/onboarding` | → full state + `completed: bool` |
| `POST /api/onboarding/name` | `{name}` (trimmed, 1–60 chars) → saved |
| `POST /api/onboarding/materials` | `{files: [{name, b64}]}` → filenames sanitized (basename only, no traversal), each ≤ 20 MB, ≤ 40 total → staged. Or `{folder}` → expanduser → must exist and be a dir → registered |
| `POST /api/onboarding/materials/done` | starts the distiller as a background `asyncio` task over the staging dir + registered folders → `{ok, copied, folders}` |
| `POST /api/onboarding/second-brain` | `{path}` → expanduser → absolute; **rejected if inside the repo checkout** (public-repo protection); `mkdir(parents=True, exist_ok=True)`; staged files move to `<sb>/inbox/onboarding/`; `materials.md` index written (copied names + linked folder paths) |
| `POST /api/onboarding/complete` | SSE: awaits the distiller task (cap 180 s), writes `<sb>/profile.md` (or the fallback stub, §5.6), sets `completed_at`, streams `stage` events then `{"type":"profile","text":…}` then `done` |

Default second-brain suggestion shown by the path card: `~/second-brain`.

### 5.3 The second brain IS the vault

- Seeded at onboarding: `<sb>/profile.md` (the distilled owner profile — the wiki's first
  page), `<sb>/inbox/onboarding/` (copies of dropped materials), `<sb>/materials.md` (index).
- `POST /api/compose` changes: when onboarding is complete, `vault_dir = second_brain`
  (replacing the hardcoded `dist/<slug>-vault`); otherwise the old default stands.
  `scaffold_vault` already copies with `dirs_exist_ok=True`, so the template lands around the
  seeded files; the plan must verify the template contains no `profile.md`/`materials.md`
  collision. Every `{{VAULT_PATH}}` substitution then points the composed chief of staff at
  the same directory the architect seeded — one memory, two readers.

### 5.4 The walk (choreography — all narration is the real session)

The workshop session starts at the reveal and runs the whole walk. The UI sends bracketed
`[studio event]` messages (suppressed from the log, §4.2); the agent narrates, the cards act:

1. **Name screen** → `POST name` → **fade-in** "Welcome, {name}." (Bricolage, staggered
   rise) → the welcome card **slides up** to reveal the studio (~600 ms, one continuous
   motion; instant under reduced motion).
2. `session/new` (workshop; onboarding contract in the prompt, §5.5). Seed message:
   `'Begin onboarding.'` — the agent greets by name and points right. The **files card** is
   hot (drop zone + folder field); the **path card** waits ghosted; `baton('card')`.
3. Each registration → `[studio event] materials registered: cv.pdf, linkedin-1.png; linked
   folder: ~/essays` → the agent acknowledges and invites more or done.
4. "That's everything" → `materials/done` (distiller starts in the background) → the agent
   asks where the mind-palace should live; path card goes hot. **The distiller overlaps with
   this decision** — no dead waiting.
5. Path confirmed → `second-brain` then `complete` (SSE). On `done` the UI sends
   `[studio event] second brain created at <path>. Distilled profile:\n<profile>` → the agent
   reacts **with specifics from the profile** (the "it actually read it" proof-beat), the
   folded cards **morph** into the "Your agent" panel, `baton('composer')`, and the interview
   begins — same session, no seam.
6. During onboarding turns the agent still emits the studio block (`picks: []` until the
   interview produces recommendations) — the extractor is already tolerant of empty picks.

### 5.5 Prompt changes (`system_prompt.py`)

`build_workshop_prompt(catalog_path=None, participant=None, onboarding=False)`:

- `participant` (dict: `name`, `second_brain`, `profile_text`, `materials_index`) → a
  `# The participant` section: greet and refer to them by name; the profile text (head-capped
  at ~6,000 chars) is their standing context. Injected on **every** workshop session once
  onboarding is complete — the architect knows them every launch.
- `onboarding=True` → a `# The onboarding walk` contract: the beats of §5.4, the
  `[studio event]` convention ("messages in brackets come from the studio, not the
  participant — never quote them back"), react-with-specifics instruction, then hand off into
  the normal interview. Plus the §4.3 ask contract in both modes.
- `write_system_prompt(..., mode="workshop", participant=…, onboarding=…)` threads through;
  architect mode remains byte-identical.

### 5.6 The distiller (`studio/distiller.py`, new — mirrors the tweaker's voice pass)

```python
build_distill_argv(claude_bin, source_dirs: list[Path]) -> list[str]
#   [claude, -p, PROMPT, --allowed-tools, Read, --add-dir, <staging>, --add-dir, <folder>…]
async def distill(source_dirs: list[Path], timeout: int = 180) -> str   # stdout, stripped
```

Prompt (fixed): read every file under the given directories — CVs (PDF), LinkedIn
screenshots (images — the Read tool handles both), writing samples — and return a concise
markdown owner profile: identity & career arc, current focus, people/orgs in orbit, working
style & voice, notable specifics worth remembering. No preamble, ≤ ~150 lines,
non-interactive. `cwd` = the staging dir; subprocess + `wait_for` timeout + nonzero-exit
handling copied from `tweaker._run_voice_pass`.

**Non-fatal by design:** on any failure `complete` writes a stub profile (`# <name>` + the
materials index + "not yet distilled") and the `[studio event]` says the materials are
registered but unread — the agent adapts, onboarding still completes. This is the only
"scripted fallback" in the design.

### 5.7 Frontend (`studio/static/onboard.js`, new; `app.js`/`index.html` edits)

`onboard.js` is the onboarding **producer**: overlay screens (name → welcome → reveal), the
files/path cards via `window.cards`, event-message sending, the complete-SSE consumer, and
the morph hand-off to `renderAgentPanel`. `app.js` gains: the `GET /api/onboarding` gate in
`start()`, `[card]`/`[studio event]` bubble suppression, ask-card rendering on `done`, and
the baton hooks on the composer. Status chip: unchanged states, plus during the walk it reads
`onboarding` until the first streamed token flips it to `agent live` (the journey's handshake
rule, untouched).

## 6. Build order (risk-sorted, hard cut lines — each lands independently)

1. **C1 — card framework + ask channel** (§3, §4). `cards.js`/`cards.css`, extractor `ask`,
   prompt ask-contract, app.js render/answer path. Ships value alone: the interview gets
   clickable questions. Floor if the slice dies here.
2. **C2 — onboarding backend** (§5.1–5.3, 5.5, 5.6). `onboarding.py`, `distiller.py`,
   endpoints, prompt participant/onboarding sections, compose vault override. Fully
   API-testable without UI.
3. **C3 — the walk** (§5.4, 5.7). `onboard.js` overlay + producers + events + morph. The
   full journey.

## 7. Testing

Backend (pytest, test-per-module):

- `test_studio_extractor.py` (extend): valid `ask` extracted; option-id defaulting; <2
  options → `ask` None with picks kept; non-dict/missing-title → None; block without ask
  clears nothing it shouldn't (returns `ask: None`); `multi` coercion.
- `test_system_prompt.py` (extend): participant section includes name + profile text +
  cap; onboarding contract present only when `onboarding=True`; ask contract in both
  workshop variants; architect mode byte-identical (existing tests).
- `test_onboarding.py` (new): state round-trip; name validation; b64 staging with filename
  sanitization (traversal attempt → basename); size/count caps; folder validation; second-
  brain creation + staged-file move + `materials.md`; **repo-path rejection**; completed
  flag; re-run overwrite.
- `test_distiller.py` (new): argv shape (variadic `--allowed-tools Read`, one `--add-dir`
  per source); prompt mentions the dirs; timeout/nonzero-exit raise (subprocess mocked, same
  idiom as the tweaker tests).
- `test_server.py` (extend): endpoint happy paths + validation errors; `session/new`
  injects participant when complete / onboarding contract when not (prompt cache file
  content asserted); compose vault override (monkeypatched composer); `complete` SSE shape
  with a mocked distiller.
- `test_smoke_integration.py` (extend, marked integration): one real `distill()` over a
  two-file fixture (a small `.md` + a `.png`) asserting non-empty markdown comes back.

Frontend: no JS runner — manual checklist in the plan (fade-in/reveal/reduced-motion; baton
sleep/wake; drop + folder link; distill overlap; profile reaction names a real detail; morph
to panel; ask card round-trip mid-interview; `?onboard=1` re-run; returning-user launch skips
straight to a knows-you greeting).

Placeholder contract: `chief-of-staff/` and `agent-architect/` untouched. All participant
data lives in gitignored `.cache/` or the user-chosen second brain (rejected if inside the
repo). Nothing personal can enter a commit.

## 8. Risks

| Risk | Mitigation |
|---|---|
| Live narration drifts off the walk | Every gate is server/UI-driven — the agent only narrates; the onboarding contract is short and imperative; malformed asks/blocks are dropped tolerantly; worst case the participant still completes via cards |
| Distiller slow or failing on the night | Overlapped with the path decision; 180 s cap; non-fatal stub fallback (§5.6); one real integration smoke before the room |
| Base64 uploads bloat memory | 20 MB/file, 40-file caps enforced server-side; workshop materials are CVs and screenshots |
| Filename/path abuse | Basename-only sanitization on staged files; second-brain path expanded, absolute, repo-interior rejected |
| Returning-user prompt bloat | Profile injection head-capped (~6,000 chars); materials index is names only |
| Framework built for four producers, shipped with two | The card contract + `keys` kind are specified here (§3.1) so personalize/connect slices consume, not redesign; YAGNI beyond the contract — no speculative code paths |

## 9. Non-goals

Per-skill personalization content and sequencing (r1-B — will consume the framework);
the connect-step reskin onto `keys` cards (own slice; smoke tests already exist); LinkedIn
scraping or any network fetch of participant data; a profile viewer/editor UI (the second
brain is plain markdown — that's the point); conversation persistence across studio restarts
(separate roadmap item); the always-on scheduler (r1-A).
