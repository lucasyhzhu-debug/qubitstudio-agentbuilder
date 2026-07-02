# Studio dark/light theme toggle

## Context

`studio/static/` (the agent-builder's browser UI) ships a single, fixed dark palette defined
once as CSS custom properties in `styles.css:1-17` and reused unmodified by `shelf.css`. There is
no theme system, no `prefers-color-scheme` support, and no persisted user preference of any kind —
the backend is explicitly in-memory/session-only (`server.py` docstring). Participants using the
studio in bright rooms / light-mode OS setups have no way to switch. This spec adds a light theme
and a toggle, defaulting to the participant's OS preference and remembering their explicit choice.

## Mechanism

All colors in `styles.css` / `shelf.css` already route through `:root` custom properties, so the
swap is a single override block, no selector rewrites:

```css
:root { /* existing dark values, unchanged */ }
html[data-theme="light"] { /* light overrides, listed below */ }
```

`html[data-theme="light"]` has higher CSS specificity than `:root` regardless of file/rule order,
so this is safe to append directly after the existing `:root` block in `styles.css`. `shelf.css`
needs no changes to its variable usage — it already consumes the same tokens.

**New file `studio/static/theme.js`** (plain script, no build step, matching the rest of the
app), loaded via a **blocking** `<script src="/static/theme.js"></script>` tag in `<head>`,
placed after the two `<link rel="stylesheet">` tags and before `</head>`. Not `defer`/`async` —
it must run and set the attribute before first paint to avoid a flash of the wrong theme.

Two responsibilities in one file (mirrors `shelf.js`'s existing pattern of one file per
self-contained feature, keeping `app.js` untouched):

1. **Runs immediately** (top of file, executes during `<head>` parsing, before `<body>` exists):
   decide and apply the initial theme.
   - `localStorage.getItem('agent-studio-theme')` if set (`"dark"` or `"light"`)
   - else `window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark'`
   - else `'dark'` (today's default, unchanged)
   - `document.documentElement.dataset.theme = <result>`
2. **Runs on `DOMContentLoaded`** (button doesn't exist until `<body>` parses): find
   `#themetoggle`, set its icon/`aria-label` to reflect the theme applied in step 1, and wire a
   click handler that flips `document.documentElement.dataset.theme`, writes the new value to
   `localStorage['agent-studio-theme']`, and updates the icon/label.

**New header control** in `index.html`, placed next to the existing `#evalstoggle` control:

```html
<button id="themetoggle" aria-label="Switch to light mode">🌙</button>
```

Icon reflects the *current* active theme (🌙 while dark is active, ☀️ while light is active) —
matches the plain-Unicode-glyph convention already used in this header (`▦` on `#shelfbtn`, `✕`
on `.shelf-close`), no icon font/SVG needed. `aria-label` updates each toggle to name the action
("Switch to light mode" / "Switch to dark mode").

## Palette

Light values mirror the dark hues; accent colors (`--acc`, `--acc2`, `--ok`, `--warn`, `--pink`)
are deepened relative to their dark-mode pastels because several rules use them as **text/border
color directly on a light background** (e.g. `.bp-card h3`, `.step.active`, `.price-tag.t-*`,
`#useHandoff`) — the dark-mode pastel values would be near-invisible on white.

| var | dark (unchanged) | light (new) |
|---|---|---|
| `--bg` | `#0b0e14` | `#f5f7fb` |
| `--panel` | `#131823` | `#ffffff` |
| `--panel2` | `#1a2030` | `#eef1f7` |
| `--line` | `#283044` | `#d7dce6` |
| `--ink` | `#e6e9ef` | `#161a22` |
| `--mut` | `#8a93a6` | `#5b6478` |
| `--dim` | `#5d6678` | `#8892a3` |
| `--acc` | `#6ea8fe` | `#2f6fe0` |
| `--acc2` | `#9d7bff` | `#6d4de0` |
| `--ok` | `#3ddc97` | `#12925f` |
| `--warn` | `#f7b955` | `#a3690a` |
| `--pink` | `#f06595` | `#cf3572` |

Two **new** semantic tokens, added because the current single-theme CSS has hardcoded colors that
a real light theme turns from a style nitpick into an actual readability bug:

| var | dark | light | replaces |
|---|---|---|---|
| `--on-accent` | `#04060c` | `#ffffff` | hardcoded `#04060c` text on `#composer button[type="submit"]` (`styles.css:228`) and `.brief-btn` (`shelf.css:227`) — dark mode's pale `--acc` needs near-black text; light mode's deepened `--acc` needs white text |
| `--panel-selected` | `#1d2235` | `#e8ecff` | hardcoded `background: #1d2235` on `.shelf-card.on` (`shelf.css:121`) — with `--ink` flipping to near-black in light mode, near-black text on the current hardcoded dark-navy background would be unreadable |

One more hardcoded-color fix, no new variable needed:

- `.bubble.assistant strong { color: #fff; }` (`styles.css:161`) sits on `var(--panel2)`, which
  becomes near-white in light mode — white-on-near-white is invisible. Change to
  `color: var(--ink);` (matches the surrounding assistant-bubble text, which already uses
  `--ink` everywhere else).

**Left unchanged** (theme-agnostic by design, verified during exploration):
- `.bubble.user` / `#shelfbtn .count`: hardcoded `color: #fff` on `var(--acc2)` — stays readable
  in light mode because `--acc2` is deepened, not lightened.
- `#shelf-backdrop` scrim (`rgba(4,6,12,.55)`) and `box-shadow: ... rgba(0,0,0,.45)` on
  `#shelf-drawer` — modal backdrops/shadows conventionally stay dark-based in both themes.
- `.bp-card.flash` keyframe (`rgba(124,92,255,.25)` → transparent) — a transient decorative wash
  over the card's own themed background, not a text-contrast concern.

## Persistence & initial state

- Storage: `localStorage['agent-studio-theme']`, value `"dark"` or `"light"`. No backend changes —
  matches the existing in-memory/session-only backend design; this is a pure browser-side
  preference tied to the participant's machine/browser, same trust boundary as everything else in
  `studio/static/`.
- Initial state precedence: saved choice → OS `prefers-color-scheme` → `dark` default. Once a
  participant clicks the toggle, that choice sticks (overrides OS preference) until they clear
  browser storage.

## Testing / verification

No JS test runner or DOM/UI test tooling exists anywhere in this repo (confirmed during
exploration — `studio/tests/` is pytest-only, backend-only). This change is pure static
frontend behavior, so verification is manual, via `python -m studio`:

1. Fresh browser profile / cleared `localStorage`, OS set to dark → studio opens dark, no toggle
   needed to confirm parity with today's look.
2. Same, OS set to light → studio opens light on first load (no prior click).
3. Click the toggle both directions → every panel (chat bubbles, blueprint cards, skill shelf
   drawer, connect-integrations wizard, build panel/stepper/log) stays legible, particularly the
   three fixed hardcoded-color spots above.
4. Reload the page after toggling → theme persists (localStorage), independent of OS setting.
5. Toggle OS `prefers-color-scheme` via DevTools rendering emulation after a manual choice is
   saved → confirms the saved choice wins over OS preference.
