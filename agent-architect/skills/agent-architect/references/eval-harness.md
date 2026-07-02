# Eval Harness (M3) — running plugin-level evals on Windows

This is the verify phase of the pipeline: after a plugin is assembled and
`validate_plugin.py` passes, run the eval loop to check the built plugin against
the spec's `quality_bar` and produce a reviewable report. The harness is
**vendored and Windows-safe** — it never depends on skill-creator being
installed. All scripts run as package modules with cwd = this skill dir
(`skills/agent-architect`), e.g. `python -m scripts.run_eval_win ...`.

## Two-layer model

A skill's quality has two distinct dimensions; we eval them separately.

### Layer 1 — Trigger eval (does the description route correctly?)
`scripts/run_eval_win.py` invokes the local `claude` CLI to test whether a
skill's description causes Claude to trigger (Skill/Read the skill) for each
query in an eval set. It needs **no API key** (the CLI uses local auth).

- Eval-set shape (JSON list): `[{"query": "...", "should_trigger": true}, ...]`.
- A query passes if its trigger rate is `>= --trigger-threshold` when
  `should_trigger` is true, or `< --trigger-threshold` when false.
- Output JSON: `{skill_name, description, results: [{query, should_trigger,
  trigger_rate, triggers, runs, pass}], summary: {total, passed, failed}}`.

```
python -m scripts.run_eval_win \
  --eval-set "<abs path to eval-set.json>" \
  --skill-path "<abs path to skill dir>" \
  [--description "override"] [--runs-per-query N] [--trigger-threshold F] \
  [--num-workers N] [--timeout S] [--model M] [--verbose]
```

**Windows note (why `_win`):** skill-creator's original `run_eval.py` polled the
subprocess pipe with `select.select()`, which on Windows raises
`OSError: [WinError 10038] ... not a socket` (select accepts only sockets there).
`run_eval_win.py` replaces that with a background reader thread draining
`process.stdout.readline()` into a `queue.Queue`; the CLI flags and JSON output
shape are otherwise identical. Always use `run_eval_win.py` on Windows.

### Layer 2 — Behavioral eval (does the skill actually do the work?)
Behavioral evals run a real task with vs. without the skill, then grade the
outputs against expectations (golden outputs). This layer uses the bundled
**grader** and **analyzer** agents plus eval definitions:

- `evals/evals.json` per skill (shape in `references/schemas.md` → `evals.json`):
  each eval has `id`, `prompt`, `expected_output`, optional `files`, and an
  `expectations` list of verifiable statements.
- For each eval, execute the task twice — once `with_skill`, once
  `without_skill` — capturing a transcript + `outputs/` per run, repeated
  `quality_bar.min_runs` times per configuration.
- The **grader** agent (`agents/grader.md`) reads each run's transcript and
  outputs and writes `grading.json` (shape in `references/schemas.md` →
  `grading.json`). Each `expectations[]` entry has exactly `text` (string),
  `passed` (bool), `evidence` (string). The run's `configuration` field must be
  exactly `"with_skill"` or `"without_skill"` — the viewer and the roll-up key
  on those exact strings; anything else is ignored/zeroed.
- The **analyzer** agent (`agents/analyzer.md`) surfaces cross-run patterns
  (flaky assertions, assertions that pass in both configs and thus don't
  differentiate the skill, etc.) as freeform notes.

Run-dir layout the roll-up understands (per skill):

```
<skill>/benchmarks/<timestamp>/
  eval-1/
    with_skill/run-1/grading.json
    with_skill/run-2/grading.json
    without_skill/run-1/grading.json
  eval-2/ ...
```

(A legacy `benchmarks/<timestamp>/runs/eval-N/...` layout is also accepted.)

## Optimization (optional, API-key gated)
`scripts/run_loop_win.py` auto-optimizes a skill's trigger description: it runs
`run_eval_win`'s eval, then asks Claude (via the Anthropic SDK) to rewrite the
description, keeping the best-scoring variant across iterations.

- The optimization step needs `ANTHROPIC_API_KEY`. **It is gated**: with no key
  set, `run_loop_win.py` prints
  `set ANTHROPIC_API_KEY to enable description optimization; skipping`
  to stderr and exits 0 — it never crashes. Trigger eval alone (Layer 1) does
  not need a key; only the description-rewrite step does.

```
python -m scripts.run_loop_win --eval-set <json> --skill-path <path> --model <m> \
  [--max-iterations N] [--holdout F] [--runs-per-query N] [--verbose]
```

## Roll-up + quality bar
`scripts/aggregate_plugin.py` is the plugin-wide orchestrator. It discovers each
skill's artifacts, rolls behavioral benchmarks up via the vendored
`_vendor/aggregate_benchmark.py`, combines trigger results, checks the
`quality_bar`, and emits a JSON summary plus a static HTML report.

```
python -m scripts.aggregate_plugin "<plugin_root>" \
  [--quality-bar "<spec-or-bar.json>"] [--results-root "<dir>"] \
  [--json "<out.json>"] [--html "<out.html>"]
```

- `--quality-bar` accepts either a bare `{trigger_accuracy, behavioral_pass_rate,
  min_runs}` object or a full spec (it reads `spec.quality_bar`). Defaults:
  `trigger_accuracy 0.85`, `behavioral_pass_rate 0.8`, `min_runs 3`.
- Discovery searches each skill dir and `<results-root>/<skill-name>/`, so eval
  artifacts can live outside the shipped tree.
- **Exit code:** non-zero if any checked metric is below the bar. A gate with no
  data is reported as `no_data` and does **not** fail the build — so a
  trigger-only or empty plugin aggregates gracefully (the bar is simply not
  enforced where there's nothing to measure). `min_runs` shortfalls are surfaced
  as warnings on the affected gate.

## Headless HTML report
`aggregate_plugin.py` renders the report via the vendored
`_vendor/generate_review.py --static <out.html>`, which writes a self-contained
HTML file and exits — **no server** (skill-creator's server mode used `lsof` and
a blocking `serve_forever`, neither of which is Windows-friendly). The static
renderer needs at least one run directory (a dir containing `outputs/`) to embed;
if none exist (trigger-only run), the HTML step is skipped with a note and the
aggregate still completes.

## Vendored pieces (under `scripts/_vendor/`)
- `aggregate_benchmark.py` — per-skill benchmark roll-up (mean/stddev/min/max,
  with/without-skill delta).
- `generate_review.py` + `viewer.html` — static HTML eval viewer.
- `quick_validate.py` — minimal SKILL.md frontmatter validator.
- `package_skill.py` — `.skill` zipper (used in M4 packaging).
- `utils.py` — `parse_skill_md`.
All are copied verbatim from skill-creator (only relocated imports adjusted).
