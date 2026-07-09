"""Headless `.plugin` export: spawn one tools-enabled claude -p that runs agent-architect
M2->M3->M4 from a client-ready spec, parse [[studio:...]] progress markers into build events."""
from __future__ import annotations
import asyncio
import copy
import ctypes
import json
import re
import shutil
import sys
from pathlib import Path
from typing import AsyncIterator

from studio.chat_session import resolve_claude
from studio import stream_parser as sp


def _win_job_for_tree(pid: int):
    """Put `pid` in a Windows Job Object set to KILL_ON_JOB_CLOSE so EVERY descendant dies when the
    job handle closes. Returns the handle (keep it open; closing it terminates the whole tree), or
    None on non-Windows / any failure. Fixes the verified-export leak: run_eval_win spawns its eval
    `claude -p` workers as grandchildren that otherwise orphan (outliving both run_eval_win and the
    orchestrator) — ~19 zombie processes per build. Best-effort: failure just reverts to old behavior."""
    if sys.platform != "win32":
        return None
    try:
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)

        class _BASIC(ctypes.Structure):
            _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64),
                        ("PerJobUserTimeLimit", ctypes.c_int64), ("LimitFlags", ctypes.c_uint32),
                        ("MinimumWorkingSetSize", ctypes.c_size_t),
                        ("MaximumWorkingSetSize", ctypes.c_size_t),
                        ("ActiveProcessLimit", ctypes.c_uint32), ("Affinity", ctypes.c_size_t),
                        ("PriorityClass", ctypes.c_uint32), ("SchedulingClass", ctypes.c_uint32)]

        class _IO(ctypes.Structure):
            _fields_ = [(n, ctypes.c_uint64) for n in (
                "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
                "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]

        class _EXT(ctypes.Structure):
            _fields_ = [("BasicLimitInformation", _BASIC), ("IoInfo", _IO),
                        ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t),
                        ("PeakProcessMemoryUsed", ctypes.c_size_t),
                        ("PeakJobMemoryUsed", ctypes.c_size_t)]

        job = k32.CreateJobObjectW(None, None)
        if not job:
            return None
        info = _EXT()
        info.BasicLimitInformation.LimitFlags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not k32.SetInformationJobObject(job, 9, ctypes.byref(info), ctypes.sizeof(info)):
            k32.CloseHandle(job)
            return None
        hproc = k32.OpenProcess(0x1F0FFF, False, pid)  # PROCESS_ALL_ACCESS
        if not hproc:
            k32.CloseHandle(job)
            return None
        ok = k32.AssignProcessToJobObject(job, hproc)
        k32.CloseHandle(hproc)
        if not ok:
            k32.CloseHandle(job)
            return None
        return job
    except Exception:
        return None


def _close_job(job) -> None:
    """Close a job handle from _win_job_for_tree — KILL_ON_JOB_CLOSE then reaps the whole tree."""
    if job and sys.platform == "win32":
        try:
            ctypes.WinDLL("kernel32").CloseHandle(job)
        except Exception:
            pass

# component key may itself contain a colon (e.g. "skill:standup"), so capture greedily up to
# the final ":<status>]]". status is a fixed enum.
_STAGE = re.compile(r"\[\[studio:stage:([a-z]+):(running|ok|fail)\]\]")
_COMPONENT = re.compile(r"\[\[studio:component:(.+?):(running|ok|fail)\]\]")
_STAGES = {"preflight", "generate", "assemble", "validate", "evals", "package"}

_HERE = Path(__file__).resolve().parent
_REPO = _HERE.parent
_BUILDS = _HERE / ".cache" / "builds"
_DIST = _REPO / "dist"

# The instruction handed to the headless run. {spec_path}/{workspace}/{outdir} are filled per build.
# Instructs spawning the NAMESPACED subagent agent-architect:plugin-generator (Task 0 §2) and
# running deterministic scripts from agent-architect/skills/agent-architect/ as python -m scripts.<name>.
# The M3 eval stage fans out many nested `claude -p` runs (runs-per-query each) and is the slow
# part of a build. It is optional: with evals the package is graded "verified"; without, the package
# still builds (validated structurally) but is graded "validated". {evals_clause} swaps in.
#
# Quality:speed tuning of the eval stage (highest-leverage first):
#   - eval_model: pin the model each eval claude -p uses instead of inheriting the heavy default.
#     POLICY: sonnet-and-above only — the eval grade gates "verified", so the judge must be capable;
#     haiku is too weak for these evals. sonnet is the quality:speed sweet spot (far faster than opus).
#   - eval_workers: run_eval_win parallelism (ProcessPoolExecutor). Default 10.
#   - eval_runs: runs-per-query. 3 = stable accuracy estimate; lower trades stability for speed.
#   - eval_timeout: per-query seconds. The eval stage is dominated by NON-triggering queries that
#     wait the whole timeout to confirm "didn't fire" — routing happens early in the stream, so 20s
#     (down from the harness default 30) cuts ~a third off every such wait at negligible quality cost.
_DEFAULT_EVAL_MODEL = "claude-sonnet-4-6"
# The orchestrator claude -p (preflight/generate/assemble/validate) defaults to the CLI's heavy model
# (opus-4-8). Generation+assembly is mechanical file-writing from a fixed spec — sonnet is fully
# capable and 2-3x faster, the biggest single quality:speed win for a build. Pin it (sonnet-and-above).
_DEFAULT_ORCH_MODEL = "claude-sonnet-4-6"
_EVALS_CLAUSE = (
    ", then run the M3 eval stage with these EXACT flags so it stays fast: for EACH skill run "
    "`python -m scripts.run_eval_win --eval-set <skill>/evals/evals.json --skill-path <skill> "
    "--model {eval_model} --num-workers {eval_workers} --runs-per-query {eval_runs} "
    "--timeout {eval_timeout}`, then "
    "`python -m scripts.aggregate_plugin <tree>` against the quality_bar — emit "
    "[[studio:stage:evals:running]] then [[studio:stage:evals:ok]] (or :fail if the bar is missed)")
_NO_EVALS_CLAUSE = (" (SKIP the M3 eval stage entirely for this build — do NOT run run_eval_win or "
                    "aggregate_plugin and do NOT emit any evals markers)")

_EXPORT_PROMPT = """Run agent-architect's M2->M4 pipeline to build the plugin described in
{spec_path} (already set to deliverable_grade=client-ready). Follow the agent-architect SKILL.md
choreography exactly: preflight (python -m scripts.doctor from agent-architect/skills/agent-architect/),
fan-out generate one agent-architect:plugin-generator subagent per component, assembly pass,
then run python -m scripts.validate_plugin{evals_clause}, then python -m scripts.package_plugin into {outdir}.
All deterministic scripts run from agent-architect/skills/agent-architect/ as `python -m scripts.<name>`.
During assembly, also materialize the spec's `runtime` block (storage dirs + README sections for
memory/routines) by running `python -m studio.runtime_export <tree> <spec_path>` before packaging.

CRITICAL — emit these machine markers on their OWN line at each boundary (the GUI parses them):
  [[studio:stage:preflight:running]] ... [[studio:stage:preflight:ok]]
  [[studio:stage:generate:running]]
  [[studio:component:<type>:<name>:running]] / :ok / :fail   (once per component)
  [[studio:stage:generate:ok]]  then assemble / validate / package similarly (and evals only if it runs).
On any unrecoverable failure emit [[studio:stage:<stage>:fail]] and stop.
Work in {workspace}. Do not ask questions; this is non-interactive."""


def parse_marker(line: str) -> dict | None:
    m = _STAGE.search(line or "")
    if m and m.group(1) in _STAGES:
        return {"type": "stage", "name": m.group(1), "status": m.group(2)}
    m = _COMPONENT.search(line or "")
    if m:
        return {"type": "component", "key": m.group(1), "status": m.group(2)}
    return None


def force_client_ready(spec: dict) -> dict:
    out = copy.deepcopy(spec)
    out.setdefault("plugin", {})["deliverable_grade"] = "client-ready"
    return out


def force_output_root(spec: dict, root) -> dict:
    """Set plugin.output_root so the generators resolve each component's rel_path under the build
    workspace. architecture-spec.md §2 requires output_root, but the studio chat contract never
    emits it — without this injection the plugin-generators have no tree root to write into and the
    build is non-deterministic. Deep-copies (does not mutate the caller's spec)."""
    out = copy.deepcopy(spec)
    out.setdefault("plugin", {})["output_root"] = str(root)
    return out


class Exporter:
    def __init__(self, claude_bin: str | None = None, repo_root: Path = _REPO):
        self.claude_bin = claude_bin or resolve_claude() or "claude"
        self.repo_root = Path(repo_root)

    def build_argv(self, spec_path: Path, workspace: Path, outdir: Path,
                   run_evals: bool = True, eval_model: str = _DEFAULT_EVAL_MODEL,
                   eval_workers: int = 10, eval_runs: int = 3, eval_timeout: int = 20,
                   orch_model: str = _DEFAULT_ORCH_MODEL) -> list[str]:
        evals_clause = (
            _EVALS_CLAUSE.format(eval_model=eval_model, eval_workers=eval_workers,
                                 eval_runs=eval_runs, eval_timeout=eval_timeout)
            if run_evals else _NO_EVALS_CLAUSE)
        prompt = _EXPORT_PROMPT.format(
            spec_path=spec_path, workspace=workspace, outdir=outdir, evals_clause=evals_clause)
        return [self.claude_bin, "-p", prompt,
                "--output-format", "stream-json", "--verbose",
                # Pin the orchestrator off the heavy default (opus) — sonnet builds 2-3x faster
                # at no quality cost for mechanical generation/assembly. (sonnet-and-above policy.)
                "--model", orch_model,
                # agent-architect loaded session-only (NOT globally installed) — Task 0 §2.
                "--plugin-dir", str(self.repo_root / "agent-architect"),
                # auto-accept file writes in print mode; keeps every other gate (Task 0 §3).
                "--permission-mode", "acceptEdits",
                # --allowed-tools is VARIADIC: tools are SEPARATE argv tokens, NOT one space-joined
                # string. Task enables subagent fan-out; Bash(python:*) scopes Bash to the python
                # deterministic scripts only. (Task 0 §3.)
                "--allowed-tools", "Task", "Read", "Write", "Edit", "Glob", "Grep", "Bash(python:*)"]

    async def _spawn_lines(self, argv, cwd) -> AsyncIterator[str]:
        proc = await asyncio.create_subprocess_exec(
            *argv, cwd=str(cwd),
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        # Tie the orchestrator's whole process tree to a kill-on-close job so the M3 eval workers
        # (run_eval_win's claude -p grandchildren) can't orphan. Assigned right after spawn, long
        # before any children appear. Closed in finally → the tree is reaped even on error/abort.
        job = _win_job_for_tree(proc.pid)
        try:
            # Drain stderr CONCURRENTLY — a long generation can fill the 64KB stderr pipe while we're
            # still reading stdout, deadlocking the child (P1 deferred-hardening item, staffreview I1).
            err_chunks: list[bytes] = []
            async def _drain_err():
                assert proc.stderr is not None
                async for line in proc.stderr:
                    err_chunks.append(line)
            err_task = asyncio.create_task(_drain_err())
            assert proc.stdout is not None
            async for raw in proc.stdout:
                yield raw.decode("utf-8", "replace")
            await proc.wait()
            await err_task
            self._returncode = proc.returncode
            self._stderr = b"".join(err_chunks).decode("utf-8", "replace")
        finally:
            _close_job(job)

    def _locate_plugin(self, name: str, outdir: Path) -> Path | None:
        hit = outdir / f"{name}.plugin"
        return hit if hit.exists() else None

    def _handoff(self, spec: dict, workspace: Path) -> dict:
        """Write Option-C fallback artefacts and return their paths."""
        name = (spec.get("plugin") or {}).get("name") or "agent"
        out_dir = _DIST / name
        out_dir.mkdir(parents=True, exist_ok=True)
        spec_path = out_dir / "spec.json"
        spec_path.write_text(json.dumps(spec, indent=2), encoding="utf-8")
        gen = out_dir / "GENERATE.md"
        gen.write_text(
            f"# Generate {name} from this spec\n\n"
            f"The headless build couldn't finish. Run generation supervised in your own session:\n\n"
            f"```\n/agent-architect\n```\n\n"
            f"Then: \"Generate the plugin from the approved spec at `{spec_path}` "
            f"(deliverable_grade=client-ready) — run M2 generate, M3 evals, M4 package.\"\n",
            encoding="utf-8")
        return {"spec_path": str(spec_path), "generate_md": str(gen)}

    async def build(self, spec: dict, run_evals: bool = True,
                    eval_model: str = _DEFAULT_EVAL_MODEL, eval_workers: int = 10,
                    eval_runs: int = 3, eval_timeout: int = 20,
                    orch_model: str = _DEFAULT_ORCH_MODEL) -> AsyncIterator[dict]:
        spec = force_client_ready(spec)
        name = (spec.get("plugin") or {}).get("name") or "agent"
        workspace = _BUILDS / name
        if workspace.exists():
            shutil.rmtree(workspace, ignore_errors=True)
        workspace.mkdir(parents=True, exist_ok=True)
        # Generators resolve each component's rel_path under plugin.output_root; the studio chat
        # never emits it, so pin it to this build's workspace before writing the spec they read.
        spec = force_output_root(spec, workspace)
        spec_path = workspace / "spec.json"
        spec_path.write_text(json.dumps(spec, indent=2), encoding="utf-8")
        _DIST.mkdir(parents=True, exist_ok=True)

        yield {"type": "stage", "name": "preflight", "status": "ok"}

        argv = self.build_argv(spec_path, workspace, _DIST, run_evals=run_evals,
                               eval_model=eval_model, eval_workers=eval_workers, eval_runs=eval_runs,
                               eval_timeout=eval_timeout, orch_model=orch_model)
        self._returncode = None
        self._stderr = ""
        failed_stage = None
        buf = ""
        try:
            async for chunk in self._spawn_lines(argv, cwd=self.repo_root):
                event = sp.parse_line(chunk)
                text = sp.assistant_text(event) if event and not sp.is_system(event) else ""
                if not text:
                    continue
                buf += text
                while "\n" in buf:
                    line, buf = buf.split("\n", 1)
                    marker = parse_marker(line)
                    if marker:
                        yield marker
                        if marker.get("status") == "fail":
                            failed_stage = marker.get("name") or marker.get("key")
                    elif line.strip():
                        yield {"type": "log", "text": line.strip()}
        except FileNotFoundError:
            yield {"type": "error", "stage": "spawn", "message": "`claude` not found",
                   "handoff": self._handoff(spec, workspace)}
            return

        if failed_stage or (self._returncode not in (0, None)):
            yield {"type": "error", "stage": failed_stage or "generate",
                   "message": f"build failed (rc={self._returncode}): {self._stderr[:400]}",
                   "handoff": self._handoff(spec, workspace)}
            return

        plugin_path = self._locate_plugin(name, _DIST)
        if plugin_path is None:
            yield {"type": "error", "stage": "package", "message": "no .plugin produced",
                   "handoff": self._handoff(spec, workspace)}
            return
        # "verified" only when the M3 evals actually ran and passed; otherwise the package built
        # and validated structurally but was not eval-checked.
        yield {"type": "done", "grade": "verified" if run_evals else "validated",
               "plugin_path": str(plugin_path)}
