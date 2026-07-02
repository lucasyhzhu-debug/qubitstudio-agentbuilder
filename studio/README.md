# agent-studio

A browser-based UI for the agent-architect conversational interview. Chat with the architect on the
left; watch the architecture blueprint populate on the right in real time.

## What it is

agent-studio wraps the `agent-architect` skill as a web app. The assistant runs the quiz
conversationally (one cluster at a time), and after every turn it emits the full architecture spec.
The right-hand pane parses and renders the spec live — Identity, Components, Tools, Storage, Memory,
Routines, and Quality bar.

When you are satisfied with the spec, click **Download spec.json** to export the architecture file —
or click **Export .plugin** to build it into an installable, eval-verified plugin in place (see below).

## Export a `.plugin` (P2)

Once a blueprint exists, **Export .plugin** builds it end-to-end without leaving the GUI. The build
panel swaps in for the blueprint and streams every stage live: a stepper
(preflight → generate → assemble → validate → evals → package), per-component fan-out cards, a log, and
a final result card with the grade and the `.plugin` path.

Under the hood `studio/exporter.py` spawns ONE tools-enabled `claude -p` at the repo root that runs
agent-architect's real **M2 → M3 → M4** pipeline from the current spec (forced to
`deliverable_grade = client-ready`, since `personal` grade packages no `.plugin`). It loads
agent-architect **session-only** (`--plugin-dir agent-architect`, no global install) and parses
`[[studio:…]]` progress markers into the live panel — it orchestrates the build, it does not
reimplement generation/eval/packaging. The packaged `.plugin` lands in `dist/`.

**M3 evals are optional.** They fan out many nested `claude -p` runs and are the slow part of a build,
so the **evals** checkbox in the header is **off by default** — the export then grades the package
`validated` (built + structurally validated). Tick **evals** to run the M3 eval stage and earn the
`verified` grade (slower).

If any stage fails (validation, evals below the quality bar, a generation error), the run halts and the
panel offers the **Use handoff** fallback: it writes `dist/<name>/spec.json` + `GENERATE.md` (a
paste-ready `/agent-architect` prompt) so you can finish the build supervised in your own session — a
flaky build is never a dead end.

## Load / resume + live highlighting (P3)

- **Load spec.json** rehydrates a previously downloaded blueprint into a fresh session so you can keep
  designing or export it.
- Blueprint fields **flash** when they change each turn, so you can see what the last answer moved.
- A spec's optional **`runtime`** block (storage / memory / routines) is materialized into the built
  plugin tree on export (dirs + README sections).

## Start

```powershell
./studio/run.ps1
```

This activates the repo `.venv`, opens `http://127.0.0.1:8765` in your browser, and starts the
FastAPI server. The server is bound to `127.0.0.1` only (not exposed on the network).

## No API key required

agent-studio uses your local `claude` CLI login (`claude auth login`). No `ANTHROPIC_API_KEY`
environment variable is needed or read.

## Scope

- **P1:** Chat interview → live blueprint → **Download spec.json**
- **P2:** **Export .plugin** — one-click headless build (generate → evals → package) with a live build panel
- **P3:** Changed-field highlighting, **Load spec.json** resume, and `runtime`-block materialization on export

> **Note:** `.plugin` export and the live browser flows are validated by user-run manual QA
> (`.\studio\run.ps1`) and the opt-in `pytest studio -m integration` smoke — both spawn a real `claude`
> build, so they run on your machine, not in the build sandbox.

## Fonts

Fonts in studio/static/fonts/ are OFL-licensed (Bricolage Grotesque, Hanken Grotesk, JetBrains Mono, Crimson Pro), copied from the qubit-site repo.
