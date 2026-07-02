# agent-studio export — performance notes, lessons & techniques

Captured while making the one-click `.plugin` export fast and reliable (P2 + the M3-evals work).
The export spawns ONE headless `claude -p` that runs agent-architect's M2→M4 from the spec; studio
orchestrates + parses markers, it does not reimplement the build. All timings are real builds on a
1-component skill (Windows, MAX local auth, no API key).

## Measured journey (1 skill, trigger evals)

| Build | Orchestrator | Evals | Outcome | Total | Where the time went |
|---|---|---|---|---|---|
| evals OFF | opus-4-8 (default) | — | `validated` + `.plugin` | **~280s** | preflight→generate→assemble→validate→package |
| verified #1 | opus-4-8 (default) | sonnet ×3 | `evals:fail` (0.43<0.85) | **626s** | preflight 145 · gen 76 · asm 68 · val 12 · **evals 324** |
| verified #2 (opt) | **sonnet** | sonnet ×3 | `verified` + `.plugin` | **614s** | reached evals at **331s vs 429s** (−98s) · evals still dominate |

Headline: with evals off a real `.plugin` builds in ~4.5 min. With evals on, the **eval stage is the
bottleneck** (≈50% of wall-clock) and the **orchestrator was silently running on opus** (≈46%).

## Lessons learnt

1. **The default model for a headless `claude -p` is the heavy one (opus-4-8 [1m]).** A nested build
   inherits it unless you pass `--model`. For mechanical generate/assemble (rendering files from a
   fixed spec) that is pure waste — sonnet does it 2-3× faster at no quality cost. *Always pin the
   orchestrator model for sub-builds.* (Probe it: `claude -p "hi" --output-format stream-json --verbose`
   → read `model` on the `system/init` event.)
2. **The eval stage cost is dominated by NON-triggering queries.** A trigger eval waits the full
   `--timeout` (default 30s) to confirm a query *didn't* fire the skill. Negatives + non-triggering
   positives are most of the set, so most of the eval wall-clock is timeout-waiting, not model work.
   Lowering `--timeout` (→20s) is a near-free speedup; routing decisions show up early in the stream.
3. **Eval quality has a model floor.** Trigger evals gate the `verified` grade, so the judge must be
   capable — haiku is too weak (rejected). sonnet is the quality:speed sweet spot; opus is wasteful
   for a routing-classification call. Policy: **sonnet-and-above** for both orchestrator and evals.
4. **A "fail" is a valid, informative result.** The verified gate correctly refused to package a skill
   that scored `trigger_accuracy 0.43 < 0.85` — the model drafts the standup inline instead of routing
   to the skill. That's real routing behaviour, not a harness bug. The gate working is the point.
5. **Nested agent builds leak processes on Windows.** `run_eval_win` fans eval `claude -p` workers via
   a `ProcessPoolExecutor`; on timeout/abort those workers **orphan** (parent dies, they don't) — ~19
   zombie `claude.exe` per verified build, eventually exhausting fork resources. Child processes do NOT
   die with their parent on Windows by default.
6. **The generator emitted the wrong eval schema.** `plugin-generator` wrote `evals/evals.json` in the
   *behavioral* shape for a `trigger:true` component; `run_eval_win` wants a flat
   `[{query, should_trigger}]` list. The orchestrator self-corrected mid-build, but this is a real
   agent-architect bug worth fixing upstream (generate the trigger shape when `trigger:true`).

## Techniques learnt (reusable)

- **Pin sub-build models explicitly.** `--model claude-sonnet-4-6` on the orchestrator; `--model` on
  the eval harness too. Don't inherit the session default for machine work.
- **Kill-on-close Job Objects for headless agent trees (Windows).** Put the spawned process in a Job
  Object with `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`, keep the handle, close it in `finally` → every
  descendant (children, grandchildren, the leaked eval workers) is reaped on completion/error/abort.
  Pure `ctypes`, no `pywin32`, best-effort with a POSIX/no-op fallback. See `exporter._win_job_for_tree`.
  Validate cheaply: spawn parent→grandchild, assign, close, assert both die — no full build needed.
- **Instrument by parsing your own marker stream.** The export already emits `[[studio:stage:*]]`;
  stamping each event with elapsed time in the driver gives a free per-stage flame profile, which is
  how the opus-orchestrator and timeout-bound-eval costs were found. Measure before optimizing.
- **Probe the headless default model** before assuming — `system/init` carries it.
- **Benchmark the happy path by lowering the gate, not faking the work.** To measure the full verified
  pipeline (through package→`done`) on a weak-triggering test skill, drop the spec's
  `quality_bar.trigger_accuracy` — the eval still runs for real (same speed), only the pass threshold
  moves, so the timing is honest and you still exercise package + the `.plugin` artifact.

## Tunable knobs (all on `Exporter.build`, sonnet-and-above defaults)

`run_evals` (default off) · `orch_model` (sonnet) · `eval_model` (sonnet) · `eval_workers` (10) ·
`eval_runs` (3, = quality_bar.min_runs) · `eval_timeout` (20s).

## Open follow-ups

- The ~19 orphans from builds made *before* the Job Object fix persist until reboot / Task Manager
  (can't be targeted safely — the studio session is also `claude.exe`). New builds won't leak.
- Fix `plugin-generator` upstream to emit the trigger eval schema for `trigger:true` components.
- The orchestrator preflight (reading agent-architect's SKILL.md + references each build, ~45-90s) is
  fixed per-build overhead; a future lever is caching/condensing that context.
