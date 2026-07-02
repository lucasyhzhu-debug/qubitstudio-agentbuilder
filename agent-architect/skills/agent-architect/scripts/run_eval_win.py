#!/usr/bin/env python3
"""Windows-safe trigger evaluation for a skill description.

Rewrite of skill-creator's ``scripts/run_eval.py`` for Windows. The original
drained the ``claude`` subprocess pipe with ``select.select([process.stdout], ...)``.
On Windows ``select`` only accepts sockets, so polling an anonymous pipe raises
``OSError: [WinError 10038] An operation was attempted on something that is not a
socket``. This version replaces that with a **background reader thread** that
drains ``process.stdout`` line-by-line into a ``queue.Queue``; the main loop
consumes lines from the queue with a timeout. Behaviour, CLI flags, and JSON
output shape are otherwise identical to the original.

It invokes the local ``claude`` CLI to test whether a skill's description causes
Claude to trigger (read the skill / invoke it) for each query. This works with
the CLI's local auth — no ``ANTHROPIC_API_KEY`` is required.

CLI
---
    python -m scripts.run_eval_win --eval-set <json> --skill-path <path>
        [--description ..] [--num-workers N] [--timeout S]
        [--runs-per-query N] [--trigger-threshold F] [--model M] [--verbose]

Run from the owning skill dir so it resolves as a package module.
"""

from __future__ import annotations

import argparse
import json
import os
import queue
import subprocess
import sys
import threading
import time
import uuid
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from scripts._vendor.utils import parse_skill_md


def find_project_root() -> Path:
    """Find the project root by walking up from cwd looking for .claude/.

    Mimics how Claude Code discovers its project root, so the command file
    we create ends up where claude -p will look for it.
    """
    current = Path.cwd()
    for parent in [current, *current.parents]:
        if (parent / ".claude").is_dir():
            return parent
    return current


def _drain_pipe(pipe, q: "queue.Queue[str | None]") -> None:
    """Read lines from ``pipe`` into ``q`` until EOF.

    Runs in a background thread. ``readline()`` blocks instead of being polled,
    which is the Windows-safe replacement for ``select.select()`` on the pipe.
    Pushes a sentinel ``None`` when the pipe closes so the consumer can stop.
    """
    try:
        for line in iter(pipe.readline, ""):
            q.put(line)
    except (ValueError, OSError):
        # Pipe closed underneath us (process killed) — treat as EOF.
        pass
    finally:
        q.put(None)


def run_single_query(
    query: str,
    skill_name: str,
    skill_description: str,
    timeout: int,
    project_root: str,
    model: str | None = None,
) -> bool:
    """Run a single query and return whether the skill was triggered.

    Creates a command file in .claude/commands/ so it appears in Claude's
    available_skills list, then runs `claude -p` with the raw query.
    Uses --include-partial-messages to detect triggering early from
    stream events (content_block_start) rather than waiting for the
    full assistant message, which only arrives after tool execution.
    """
    unique_id = uuid.uuid4().hex[:8]
    clean_name = f"{skill_name}-skill-{unique_id}"
    project_commands_dir = Path(project_root) / ".claude" / "commands"
    command_file = project_commands_dir / f"{clean_name}.md"

    try:
        project_commands_dir.mkdir(parents=True, exist_ok=True)
        # Use YAML block scalar to avoid breaking on quotes in description
        indented_desc = "\n  ".join(skill_description.split("\n"))
        command_content = (
            f"---\n"
            f"description: |\n"
            f"  {indented_desc}\n"
            f"---\n\n"
            f"# {skill_name}\n\n"
            f"This skill handles: {skill_description}\n"
        )
        command_file.write_text(command_content)

        # On Windows the `claude` launcher is often a claude.cmd / claude.bat
        # shim (npm install), which Popen(shell=False) cannot execute directly
        # (raises WinError 193). _resolve_claude() returns a command PREFIX list,
        # prepending ["cmd", "/c"] for .cmd/.bat shims; .exe resolves to a single
        # element. Concatenate it with the rest of the argv.
        cmd = _resolve_claude() + [
            "-p", query,
            "--output-format", "stream-json",
            "--verbose",
            "--include-partial-messages",
        ]
        if model:
            cmd.extend(["--model", model])

        # Remove CLAUDECODE env var to allow nesting claude -p inside a
        # Claude Code session. The guard is for interactive terminal conflicts;
        # programmatic subprocess usage is safe.
        env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            cwd=project_root,
            env=env,
            text=True,                # decode to str (line-oriented)
            encoding="utf-8",
            errors="replace",
            bufsize=1,                # line-buffered
        )

        # Background reader thread drains stdout into a queue (Windows-safe;
        # replaces the POSIX-only select.select on the pipe).
        q: "queue.Queue[str | None]" = queue.Queue()
        reader = threading.Thread(
            target=_drain_pipe, args=(process.stdout, q), daemon=True
        )
        reader.start()

        triggered = False
        start_time = time.time()
        eof = False
        # Track state for stream event detection
        pending_tool_name = None
        accumulated_json = ""

        try:
            while time.time() - start_time < timeout:
                remaining = timeout - (time.time() - start_time)
                try:
                    line = q.get(timeout=min(1.0, max(0.05, remaining)))
                except queue.Empty:
                    # No line this tick; if the process already exited and the
                    # reader hit EOF we'll get the sentinel shortly — keep looping
                    # until timeout or sentinel.
                    if process.poll() is not None and eof:
                        break
                    continue

                if line is None:
                    # Sentinel: pipe closed (EOF).
                    eof = True
                    break

                line = line.strip()
                if not line:
                    continue

                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue

                # Early detection via stream events
                if event.get("type") == "stream_event":
                    se = event.get("event", {})
                    se_type = se.get("type", "")

                    if se_type == "content_block_start":
                        cb = se.get("content_block", {})
                        if cb.get("type") == "tool_use":
                            tool_name = cb.get("name", "")
                            if tool_name in ("Skill", "Read"):
                                pending_tool_name = tool_name
                                accumulated_json = ""
                            else:
                                return False

                    elif se_type == "content_block_delta" and pending_tool_name:
                        delta = se.get("delta", {})
                        if delta.get("type") == "input_json_delta":
                            accumulated_json += delta.get("partial_json", "")
                            if clean_name in accumulated_json:
                                return True

                    elif se_type in ("content_block_stop", "message_stop"):
                        if pending_tool_name:
                            return clean_name in accumulated_json
                        if se_type == "message_stop":
                            return False

                # Fallback: full assistant message
                elif event.get("type") == "assistant":
                    message = event.get("message", {})
                    for content_item in message.get("content", []):
                        if content_item.get("type") != "tool_use":
                            continue
                        tool_name = content_item.get("name", "")
                        tool_input = content_item.get("input", {})
                        if tool_name == "Skill" and clean_name in tool_input.get("skill", ""):
                            triggered = True
                        elif tool_name == "Read" and clean_name in tool_input.get("file_path", ""):
                            triggered = True
                        return triggered

                elif event.get("type") == "result":
                    return triggered
        finally:
            # Clean up process on any exit path (return, exception, timeout)
            if process.poll() is None:
                process.kill()
                process.wait()
            # Join the background reader so the pipe handle is released and the
            # thread doesn't outlive this call (avoids handle leak / nondeterministic
            # thread lifetime). It exits once it sees the closed pipe (EOF).
            reader.join(timeout=2.0)

        return triggered
    finally:
        if command_file.exists():
            command_file.unlink()


_CLAUDE_CMD_CACHE: list[str] | None = None


def _resolve_claude() -> list[str]:
    """Resolve the ``claude`` launcher to a command PREFIX list.

    ``shutil.which`` finds the launcher via PATHEXT. A ``.cmd``/``.bat`` shim
    (typical of an npm-installed ``claude``) cannot be executed by
    ``Popen(shell=False)`` directly (raises WinError 193), so we prepend
    ``["cmd", "/c"]``. A ``.exe`` (or any other path) is returned as a single-
    element list. Falls back to the bare name if not found.

    The cache is per-process. ProcessPoolExecutor workers are separate
    processes, so each worker resolves and caches independently (not shared).
    """
    global _CLAUDE_CMD_CACHE
    if _CLAUDE_CMD_CACHE is not None:
        return _CLAUDE_CMD_CACHE
    import shutil

    resolved = shutil.which("claude")
    if resolved and resolved.lower().endswith((".cmd", ".bat")):
        _CLAUDE_CMD_CACHE = ["cmd", "/c", resolved]
    else:
        _CLAUDE_CMD_CACHE = [resolved or "claude"]
    return _CLAUDE_CMD_CACHE


def run_eval(
    eval_set: list[dict],
    skill_name: str,
    description: str,
    num_workers: int,
    timeout: int,
    project_root: Path,
    runs_per_query: int = 1,
    trigger_threshold: float = 0.5,
    model: str | None = None,
) -> dict:
    """Run the full eval set and return results."""
    results = []

    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        future_to_info = {}
        for item in eval_set:
            for run_idx in range(runs_per_query):
                future = executor.submit(
                    run_single_query,
                    item["query"],
                    skill_name,
                    description,
                    timeout,
                    str(project_root),
                    model,
                )
                future_to_info[future] = (item, run_idx)

        query_triggers: dict[str, list[bool]] = {}
        query_items: dict[str, dict] = {}
        for future in as_completed(future_to_info):
            item, _ = future_to_info[future]
            query = item["query"]
            query_items[query] = item
            if query not in query_triggers:
                query_triggers[query] = []
            try:
                query_triggers[query].append(future.result())
            except Exception as e:
                print(f"Warning: query failed: {e}", file=sys.stderr)
                query_triggers[query].append(False)

    for query, triggers in query_triggers.items():
        item = query_items[query]
        trigger_rate = sum(triggers) / len(triggers)
        should_trigger = item["should_trigger"]
        if should_trigger:
            did_pass = trigger_rate >= trigger_threshold
        else:
            did_pass = trigger_rate < trigger_threshold
        results.append({
            "query": query,
            "should_trigger": should_trigger,
            "trigger_rate": trigger_rate,
            "triggers": sum(triggers),
            "runs": len(triggers),
            "pass": did_pass,
        })

    passed = sum(1 for r in results if r["pass"])
    total = len(results)

    return {
        "skill_name": skill_name,
        "description": description,
        "results": results,
        "summary": {
            "total": total,
            "passed": passed,
            "failed": total - passed,
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Run trigger evaluation for a skill description (Windows-safe)")
    parser.add_argument("--eval-set", required=True, help="Path to eval set JSON file")
    parser.add_argument("--skill-path", required=True, help="Path to skill directory")
    parser.add_argument("--description", default=None, help="Override description to test")
    parser.add_argument("--num-workers", type=int, default=10, help="Number of parallel workers")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout per query in seconds")
    parser.add_argument("--runs-per-query", type=int, default=3, help="Number of runs per query")
    parser.add_argument("--trigger-threshold", type=float, default=0.5, help="Trigger rate threshold")
    parser.add_argument("--model", default=None, help="Model to use for claude -p (default: user's configured model)")
    parser.add_argument("--verbose", action="store_true", help="Print progress to stderr")
    args = parser.parse_args()

    eval_set = json.loads(Path(args.eval_set).read_text())
    skill_path = Path(args.skill_path)

    if not (skill_path / "SKILL.md").exists():
        print(f"Error: No SKILL.md found at {skill_path}", file=sys.stderr)
        sys.exit(1)

    name, original_description, content = parse_skill_md(skill_path)
    description = args.description or original_description
    project_root = find_project_root()

    if args.verbose:
        print(f"Evaluating: {description}", file=sys.stderr)

    output = run_eval(
        eval_set=eval_set,
        skill_name=name,
        description=description,
        num_workers=args.num_workers,
        timeout=args.timeout,
        project_root=project_root,
        runs_per_query=args.runs_per_query,
        trigger_threshold=args.trigger_threshold,
        model=args.model,
    )

    if args.verbose:
        summary = output["summary"]
        print(f"Results: {summary['passed']}/{summary['total']} passed", file=sys.stderr)
        for r in output["results"]:
            status = "PASS" if r["pass"] else "FAIL"
            rate_str = f"{r['triggers']}/{r['runs']}"
            print(f"  [{status}] rate={rate_str} expected={r['should_trigger']}: {r['query'][:70]}", file=sys.stderr)

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
