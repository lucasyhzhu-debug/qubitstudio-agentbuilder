#!/usr/bin/env python3
"""Plugin-wide eval report + quality-bar check.

A thin orchestrator over the vendored eval harness. Given a built plugin root
(and the eval results produced for its skills), it:

1. Discovers each skill component's eval artifacts:
   - **behavioral** benchmarks: directories named ``benchmark*`` / containing
     ``eval-*`` run dirs with ``grading.json`` (rolled up via the vendored
     ``aggregate_benchmark.py``).
   - **trigger** results: ``*trigger*.json`` files in the shape emitted by
     ``run_eval_win.py`` (with ``summary.passed/total``).
2. Rolls them into one plugin-wide report.
3. Checks against the spec's ``quality_bar`` (defaults: trigger_accuracy 0.85,
   behavioral_pass_rate 0.8, min_runs 3).
4. Emits a JSON summary and a static HTML report (via the vendored
   ``generate_review.py --static``, headless — no server).

Exit code is non-zero when any checked metric is below the bar. Trigger-only or
fully-empty plugins are handled gracefully (no behavioral data => that gate is
reported as "no_data" and does not fail the build).

CLI
---
    python -m scripts.aggregate_plugin <plugin_root>
        [--quality-bar <json>] [--json <out.json>] [--html <out.html>]
        [--results-root <dir>]

``--results-root`` defaults to ``<plugin_root>``: eval artifacts are searched for
under each skill dir AND under ``<results-root>/<skill-name>/`` so results can
live outside the shipped plugin tree.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from scripts._vendor.aggregate_benchmark import generate_benchmark

DEFAULT_QUALITY_BAR = {
    "trigger_accuracy": 0.85,
    "behavioral_pass_rate": 0.8,
    "min_runs": 3,
}

# Where generate_review.py (vendored) lives — used in --static mode.
_GENERATE_REVIEW = Path(__file__).parent / "_vendor" / "generate_review.py"


def find_skill_dirs(plugin_root: Path) -> list[Path]:
    """Return skill component directories (dirs under skills/ with a SKILL.md)."""
    skills_root = plugin_root / "skills"
    if not skills_root.is_dir():
        # Single-skill plugin where the root itself is the skill.
        if (plugin_root / "SKILL.md").exists():
            return [plugin_root]
        return []
    out = []
    for child in sorted(skills_root.iterdir()):
        if child.is_dir() and (child / "SKILL.md").exists():
            out.append(child)
    return out


def _is_benchmark_dir(d: Path) -> bool:
    """A benchmark dir contains eval-* run dirs (directly or under runs/)."""
    if list(d.glob("eval-*")):
        return True
    if (d / "runs").is_dir() and list((d / "runs").glob("eval-*")):
        return True
    return False


def discover_artifacts(skill_dir: Path, results_root: Path) -> dict:
    """Find behavioral benchmark dirs and trigger-result JSONs for one skill."""
    skill_name = skill_dir.name
    search_dirs = [skill_dir]
    candidate = results_root / skill_name
    if candidate.is_dir() and candidate != skill_dir:
        search_dirs.append(candidate)

    benchmark_dirs: list[Path] = []
    trigger_files: list[Path] = []
    seen = set()

    for base in search_dirs:
        # Behavioral benchmark directories
        for d in base.rglob("*"):
            if not d.is_dir():
                continue
            if "__pycache__" in d.parts:
                continue
            if d in seen:
                continue
            if _is_benchmark_dir(d):
                benchmark_dirs.append(d)
                seen.add(d)
        # Trigger result JSONs (run_eval_win output shape)
        for f in base.rglob("*.json"):
            name = f.name.lower()
            if "trigger" in name or name in ("eval_results.json", "trigger_results.json"):
                trigger_files.append(f)

    return {
        "skill_name": skill_name,
        "skill_dir": str(skill_dir),
        "benchmark_dirs": benchmark_dirs,
        "trigger_files": trigger_files,
    }


def _load_trigger_summary(trigger_files: list[Path]) -> dict | None:
    """Combine one-or-more run_eval_win outputs into a trigger accuracy summary."""
    passed = 0
    total = 0
    found = False
    runs_seen: list[int] = []
    for f in trigger_files:
        try:
            data = json.loads(f.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        summary = data.get("summary")
        if not isinstance(summary, dict):
            continue
        found = True
        passed += int(summary.get("passed", 0))
        total += int(summary.get("total", 0))
        for r in data.get("results", []):
            if isinstance(r, dict) and "runs" in r:
                runs_seen.append(int(r["runs"]))
    if not found:
        return None
    accuracy = (passed / total) if total else 0.0
    return {
        "passed": passed,
        "total": total,
        "accuracy": round(accuracy, 4),
        "min_runs_observed": min(runs_seen) if runs_seen else 0,
    }


def _load_behavioral_summary(skill_name: str, skill_dir: Path, benchmark_dirs: list[Path]) -> dict | None:
    """Roll up behavioral benchmarks for one skill via aggregate_benchmark."""
    if not benchmark_dirs:
        return None

    all_pass_rates: list[float] = []
    min_runs = None
    rolled = []
    for bd in benchmark_dirs:
        benchmark = generate_benchmark(bd, skill_name=skill_name, skill_path=str(skill_dir))
        rolled.append({"benchmark_dir": str(bd), "run_summary": benchmark.get("run_summary", {})})
        run_summary = benchmark.get("run_summary", {})
        # Prefer the with_skill configuration's pass rate; else any config.
        config = None
        if "with_skill" in run_summary:
            config = "with_skill"
        else:
            configs = [k for k in run_summary if k != "delta"]
            config = configs[0] if configs else None
        if config:
            mean = run_summary.get(config, {}).get("pass_rate", {}).get("mean", 0.0)
            all_pass_rates.append(mean)
        # Count runs from the benchmark's runs array
        runs = benchmark.get("runs", [])
        # group runs per (eval_id, configuration)
        counts: dict[tuple, int] = {}
        for run in runs:
            key = (run.get("eval_id"), run.get("configuration"))
            counts[key] = counts.get(key, 0) + 1
        if counts:
            grp_min = min(counts.values())
            min_runs = grp_min if min_runs is None else min(min_runs, grp_min)

    if not all_pass_rates:
        return None
    pass_rate = sum(all_pass_rates) / len(all_pass_rates)
    return {
        "pass_rate": round(pass_rate, 4),
        "min_runs_observed": min_runs if min_runs is not None else 0,
        "benchmarks": rolled,
    }


def check_skill(skill_summary: dict, quality_bar: dict) -> dict:
    """Apply the quality bar to one skill's summary, returning gate results."""
    gates = {}

    trig = skill_summary.get("trigger")
    if trig is None:
        gates["trigger_accuracy"] = {"status": "no_data"}
    else:
        threshold = quality_bar["trigger_accuracy"]
        passed = trig["accuracy"] >= threshold
        gate = {
            "status": "pass" if passed else "fail",
            "value": trig["accuracy"],
            "threshold": threshold,
        }
        if trig["total"] and trig["min_runs_observed"] < quality_bar["min_runs"]:
            gate["min_runs_warning"] = (
                f"only {trig['min_runs_observed']} run(s)/query, "
                f"quality_bar.min_runs={quality_bar['min_runs']}"
            )
        gates["trigger_accuracy"] = gate

    beh = skill_summary.get("behavioral")
    if beh is None:
        gates["behavioral_pass_rate"] = {"status": "no_data"}
    else:
        threshold = quality_bar["behavioral_pass_rate"]
        passed = beh["pass_rate"] >= threshold
        gate = {
            "status": "pass" if passed else "fail",
            "value": beh["pass_rate"],
            "threshold": threshold,
        }
        if beh["min_runs_observed"] < quality_bar["min_runs"]:
            gate["min_runs_warning"] = (
                f"only {beh['min_runs_observed']} run(s), "
                f"quality_bar.min_runs={quality_bar['min_runs']}"
            )
        gates["behavioral_pass_rate"] = gate

    return gates


def build_report(plugin_root: Path, results_root: Path, quality_bar: dict) -> dict:
    """Build the plugin-wide report and overall pass/fail."""
    skill_dirs = find_skill_dirs(plugin_root)
    skills_report = []
    any_fail = False
    any_data = False

    for sd in skill_dirs:
        arts = discover_artifacts(sd, results_root)
        trigger = _load_trigger_summary(arts["trigger_files"])
        behavioral = _load_behavioral_summary(arts["skill_name"], sd, arts["benchmark_dirs"])
        if trigger is not None or behavioral is not None:
            any_data = True

        skill_summary = {
            "skill_name": arts["skill_name"],
            "skill_dir": arts["skill_dir"],
            "trigger": trigger,
            "behavioral": behavioral,
        }
        gates = check_skill(skill_summary, quality_bar)
        for g in gates.values():
            if g.get("status") == "fail":
                any_fail = True
        skill_summary["gates"] = gates
        skills_report.append(skill_summary)

    return {
        "plugin_root": str(plugin_root),
        "quality_bar": quality_bar,
        "skills": skills_report,
        "summary": {
            "skill_count": len(skill_dirs),
            "skills_with_data": sum(
                1 for s in skills_report if s["trigger"] or s["behavioral"]
            ),
            "any_data": any_data,
            "passed": not any_fail,
        },
    }


def write_static_html(plugin_root: Path, html_out: Path) -> tuple[bool, str]:
    """Render a static HTML review via the vendored generate_review.py --static.

    Returns (ok, message). generate_review needs a *workspace* with run dirs
    (dirs containing outputs/). If none exist it exits non-zero; we surface that
    as a graceful note rather than failing the whole aggregate.
    """
    workspace = plugin_root
    proc = subprocess.run(
        [sys.executable, str(_GENERATE_REVIEW), str(workspace),
         "--static", str(html_out), "--skill-name", plugin_root.name],
        capture_output=True, text=True,
    )
    if proc.returncode == 0 and html_out.exists():
        return True, f"static HTML written to {html_out}"
    msg = (proc.stdout + proc.stderr).strip().splitlines()
    tail = msg[-1] if msg else "no run directories found"
    return False, f"static HTML skipped ({tail})"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Plugin-wide eval report + quality-bar check")
    parser.add_argument("plugin_root", help="Path to the built plugin root")
    parser.add_argument("--quality-bar", dest="quality_bar", default=None,
                        help="Path to a JSON file with quality_bar overrides")
    parser.add_argument("--results-root", dest="results_root", default=None,
                        help="Root to search for eval results (default: plugin_root)")
    parser.add_argument("--json", dest="json_out", default=None,
                        help="Write the report JSON here")
    parser.add_argument("--html", dest="html_out", default=None,
                        help="Write the static HTML report here (default: <plugin_root>/eval-report.html)")
    args = parser.parse_args(argv)

    plugin_root = Path(args.plugin_root).resolve()
    if not plugin_root.is_dir():
        print(f"Error: plugin root not found: {plugin_root}", file=sys.stderr)
        return 2

    results_root = Path(args.results_root).resolve() if args.results_root else plugin_root

    quality_bar = dict(DEFAULT_QUALITY_BAR)
    if args.quality_bar:
        try:
            override = json.loads(Path(args.quality_bar).read_text())
            if isinstance(override, dict):
                # Accept either a bare quality_bar object or a full spec.
                qb = override.get("quality_bar", override)
                for k in DEFAULT_QUALITY_BAR:
                    if k in qb:
                        quality_bar[k] = qb[k]
        except (json.JSONDecodeError, OSError) as exc:
            print(f"warning: could not read quality-bar file: {exc}", file=sys.stderr)

    report = build_report(plugin_root, results_root, quality_bar)

    # Static HTML
    html_out = Path(args.html_out).resolve() if args.html_out else (plugin_root / "eval-report.html")
    html_ok, html_msg = write_static_html(plugin_root, html_out)
    report["html_report"] = {"ok": html_ok, "path": str(html_out) if html_ok else None, "note": html_msg}

    # Print summary
    print(f"Plugin: {plugin_root}")
    print(f"Quality bar: {quality_bar}")
    print("=" * 60)
    for s in report["skills"]:
        print(f"  {s['skill_name']}:")
        for gate_name, gate in s["gates"].items():
            status = gate["status"]
            if status == "no_data":
                print(f"    [no data] {gate_name}")
            else:
                mark = "PASS" if status == "pass" else "FAIL"
                print(f"    [{mark}] {gate_name}: {gate['value']:.2f} (>= {gate['threshold']})")
                if "min_runs_warning" in gate:
                    print(f"           warn: {gate['min_runs_warning']}")
    print("=" * 60)
    if not report["summary"]["any_data"]:
        print("No eval data found (trigger-only/empty plugin). Quality bar not enforced.")
    print(f"HTML: {html_msg}")
    print("Quality bar: PASSED" if report["summary"]["passed"] else "Quality bar: FAILED")

    if args.json_out:
        out = Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Wrote report JSON: {out.resolve()}")

    return 0 if report["summary"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
