# Task 0 — Headless `.plugin` export spike (HARD GATE) — FINDINGS

**Date:** 2026-06-24 · **Run by:** main session via the Bash tool (`claude` v2.1.187 is on PATH at
`/c/Users/Irfan/.local/bin/claude`, so the spike ran headlessly here, not in the user's pwsh terminal).
**Verdict: GREEN — headless tools-enabled `claude -p` fan-out works in print mode.** Task 1+ unblocked.

## 1. Generation path: FAN-OUT works (no sequential fallback needed)

A print-mode `claude -p` (cwd = repo root) successfully spawned the `plugin-generator` subagent via the
Task/Agent tool and generated one real skill component end-to-end:

- **Result:** `subtype: success`, `is_error: false`, `num_turns: 3`, `duration_ms: 34546`, `cost ≈ $0.68`.
- **Subagent spawned:** `subagent_type = "agent-architect:plugin-generator"` (namespaced — see §2).
- **File written:** `skills/echo/SKILL.md` under the payload's `output_root` — a valid, well-formed skill.
- **Marker emitted on its own line:** `[[studio:component:skill:echo:ok]]` → parses cleanly with
  `parse_marker` (Task 1). The full stream-json is captured at
  `studio/tests/fixtures/export-markers.jsonl` (32 events) for the parser tests.

So the design stays on **build model A′ (headless full build)**; the per-component sequential
`claude -p` fallback (plan Task 0 Step 3) is **NOT** required.

## 2. Subagent discovery: `--plugin-dir agent-architect` (session-only, no global install)

`agent-architect` is **not** in `~/.claude/plugins/installed_plugins.json` (only `wiki-brain@consulting-agents`).
Rather than install it globally, the spawn loads it **for the session only**:

```
claude -p "<prompt>" --plugin-dir agent-architect ...
```

The `system/init` event then lists **`agent-architect:plugin-generator`** among available agents. The
orchestrator must spawn that **namespaced** id (`agent-architect:plugin-generator`), not bare
`plugin-generator`. `--plugin-dir` is repeatable and scoped to the one invocation — it leaves the user's
installed-plugins state untouched, which is exactly what the export wants. It also makes the
agent-architect **skill** and **`scripts/`** resolve for the M2→M3→M4 choreography.

## 3. Exact CLI form Task 2 must hardcode (CHANGES vs the plan's `build_argv`)

The plan's draft `build_argv` (plan §Task 2) is **wrong in three ways**; corrected form:

| Concern | Plan draft | Correct (verified) |
|---|---|---|
| tools flag | `"--allowed-tools", "Task Write Edit Bash Read Glob Grep"` (one string) | `--allowed-tools` is **variadic** (`<tools...>`) — pass **separate argv tokens**: `"--allowed-tools", "Task", "Read", "Write", "Edit", "Glob", "Grep", "Bash(python:*)"` |
| subagent reach | "install agent-architect or expose project agents" | `"--plugin-dir", "agent-architect"` (session-only) |
| permissions | (none) | `"--permission-mode", "acceptEdits"` — required so file writes don't prompt-hang in print mode |

- **`--allowed-tools` is variadic** (`claude --help`: `--allowedTools, --allowed-tools <tools...>`). A
  single space-joined string is read as ONE tool name. Chat's `--allowed-tools ""` (single empty token)
  is fine because empty = no tools; the export needs several, so they MUST be separate argv elements.
- **Subagent-spawn tool name:** passing `Task` in `--allowed-tools` enables fan-out; the call surfaces in
  the stream as a `tool_use` named **`Agent`** (CLI v2.1.187). Keep `Task` in the allowed list.
- **`--permission-mode acceptEdits`** auto-accepts Write/Edit while keeping every other gate. Do **NOT**
  use `--permission-mode bypassPermissions` — it disables gates wholesale and the safety classifier
  rejects spawning such an autonomous loop (and it is unnecessary).
- **Bash for the deterministic scripts:** the spike only generated (no Bash needed). The FULL export's
  orchestrator must run `python -m scripts.*` (validate/eval/aggregate/package), which needs Bash. Under
  `acceptEdits`, bare `Bash` still prompts — so scope it as an allow rule **`Bash(python:*)`** in
  `--allowed-tools` so only python invocations auto-run (gates stay on for everything else). This Bash
  path is exercised only by the **integration smoke (user-run, pending)** — the spike proved the
  generation half; the script half is verified there.

## 4. Deterministic CLIs (Task 0 Step 4) — confirmed via `--help`

Run from `agent-architect/skills/agent-architect/` as `python -m scripts.<name>` (the dir is the parent of
`scripts/`; resolve it the way `scripts/_common.ps1` does — never hardcode a per-user path):

| Script | Confirmed CLI |
|---|---|
| `scripts.doctor` | `python -m scripts.doctor [--json JSON_OUT]` |
| `scripts.validate_plugin` | `python -m scripts.validate_plugin <plugin_root> [--json OUT] [--check-violations] [--strict-violations]` |
| `scripts.run_eval_win` | `python -m scripts.run_eval_win --eval-set <json> --skill-path <dir> [--description ...] [--trigger-threshold ...] [--model ...]` (per-skill) |
| `scripts.aggregate_plugin` | `python -m scripts.aggregate_plugin <plugin_root> [--quality-bar <json>] [--results-root <root>] [--json OUT] [--html OUT]` |
| `scripts.package_plugin` | `python -m scripts.package_plugin <plugin_root> [--outdir OUTDIR]` |

**Quality bar** that `aggregate_plugin` enforces (defaults, `aggregate_plugin.py:44`):
`trigger_accuracy 0.85`, `behavioral_pass_rate 0.8`, `min_runs 3`. "verified" grade = this bar passes.

**Grade gating** (`references/architecture-spec.md:58`): `deliverable_grade` is required and gates
packaging — `personal` installs to `~/.claude` and packages **no** `.plugin`; `client-ready` packages the
`.plugin`. The exporter therefore **forces `client-ready`** (plan Task 2 `force_client_ready`).

## 5. cwd = repo root — derailment surface noted, did not derail

The spawn ran at repo root. The `system/init` event loaded the full project agent roster (all `gsd-*`,
`wiki-brain:*`, etc.) and the repo's CLAUDE.md — a large context surface — but the trivial 1-component
build completed cleanly in 3 turns without derailing into project skills. **Mitigation for production:**
consider `--exclude-dynamic-system-prompt-sections` (chat already uses it, `chat_session.py:56`) to drop
the SessionStart hook injection, and keep the export prompt explicit/non-interactive. Re-evaluate if a
larger multi-component build wanders; the integration smoke is the place to confirm at scale.

## 6. Gate decision

**GREEN.** Proceed to Task 1+. Task 2 implements the corrected `build_argv` from §3
(`--plugin-dir agent-architect`, variadic `--allowed-tools` with `Bash(python:*)`, `--permission-mode
acceptEdits`, namespaced `agent-architect:plugin-generator` in the prompt). The fan-out path holds; no
replan needed.
