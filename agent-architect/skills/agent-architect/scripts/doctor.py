"""Preflight checks for the agent-architect pipeline.

Reports the environment and ensures the Python dependencies later milestones need are importable,
auto-installing them if missing (per the locked decision). It is intentionally tolerant: a missing
``ANTHROPIC_API_KEY`` is reported, not fatal (optimization is gated elsewhere); a failed pip install
is reported, not crashed on. The only hard prerequisites are Python itself and the ``claude`` CLI.

CLI
---
    python -m scripts.doctor [--json <out.json>]

Run from the owning skill dir so it resolves as a package module. Exit 0 unless a hard prerequisite
(Python too old, or ``claude`` not on PATH) truly blocks.
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

MIN_PY = (3, 9)
REQUIRED_PACKAGES = ["yaml", "anthropic"]  # import name -> pip name handled below
PIP_NAME = {"yaml": "pyyaml", "anthropic": "anthropic"}


def _check_python(report: dict) -> bool:
    v = sys.version_info
    ok = (v.major, v.minor) >= MIN_PY
    report["python"] = {
        "version": f"{v.major}.{v.minor}.{v.micro}",
        "ok": ok,
        "min_required": ".".join(map(str, MIN_PY)),
        "executable": sys.executable,  # interpreter path — debugs mismatched-interpreter setups
    }
    return ok


def _check_claude_cli(report: dict) -> bool:
    path = shutil.which("claude")
    info: dict = {"on_path": bool(path), "path": path, "version": None}
    if path:
        try:
            proc = subprocess.run(
                [path, "--version"],
                capture_output=True, text=True, timeout=20,
            )
            out = (proc.stdout or proc.stderr or "").strip()
            if out:
                info["version"] = out.splitlines()[0]
        except Exception as exc:  # noqa: BLE001 - report, don't crash
            info["version_error"] = str(exc)
    report["claude_cli"] = info
    return bool(path)


def _importable(modname: str) -> bool:
    try:
        importlib.import_module(modname)
        return True
    except Exception:  # noqa: BLE001
        return False


def _ensure_packages(report: dict) -> None:
    pkgs: dict = {}
    report["packages"] = pkgs
    for mod in REQUIRED_PACKAGES:
        if _importable(mod):
            pkgs[mod] = {"present": True, "installed_now": False}
            continue
        pip_name = PIP_NAME.get(mod, mod)
        entry = {"present": False, "installed_now": False, "pip_name": pip_name}
        try:
            proc = subprocess.run(
                [sys.executable, "-m", "pip", "install", pip_name],
                capture_output=True, text=True, timeout=300,
            )
            if proc.returncode == 0:
                # importlib caches; invalidate so the fresh install is visible.
                importlib.invalidate_caches()
                if _importable(mod):
                    entry["present"] = True
                    entry["installed_now"] = True
                else:
                    entry["install_error"] = "pip reported success but module still not importable"
            else:
                tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-3:]
                entry["install_error"] = " | ".join(tail) or f"pip exit {proc.returncode}"
        except Exception as exc:  # noqa: BLE001 - resilient: report, don't crash
            entry["install_error"] = str(exc)
        pkgs[mod] = entry


def _check_api_key(report: dict) -> None:
    present = bool(os.environ.get("ANTHROPIC_API_KEY"))
    report["anthropic_api_key"] = {
        "present": present,
        "note": "" if present else
        "Not set. Optimization/eval steps that call the API are gated and will be skipped; set "
        "ANTHROPIC_API_KEY to enable them. Not an error for setup/generation.",
    }


def run_doctor() -> tuple[dict, bool]:
    """Return (report, hard_ok). hard_ok is False only if a hard prerequisite is missing."""
    report: dict = {}
    py_ok = _check_python(report)
    claude_ok = _check_claude_cli(report)
    _ensure_packages(report)
    _check_api_key(report)
    hard_ok = py_ok and claude_ok
    report["hard_prerequisites_ok"] = hard_ok
    return report, hard_ok


def _print_summary(report: dict, hard_ok: bool) -> None:
    print("agent-architect doctor — preflight")
    print("=" * 60)

    py = report["python"]
    mark = "OK" if py["ok"] else "BLOCK"
    print(f"[{mark}] Python {py['version']} (need >= {py['min_required']})")
    print(f"       interpreter: {py.get('executable', '?')}")

    cli = report["claude_cli"]
    if cli["on_path"]:
        ver = cli.get("version") or "version unknown"
        print(f"[OK] claude CLI on PATH ({ver})")
    else:
        print("[BLOCK] claude CLI not found on PATH")

    for mod, info in report["packages"].items():
        name = PIP_NAME.get(mod, mod)
        if info.get("present") and info.get("installed_now"):
            print(f"[OK] {name}: installed now")
        elif info.get("present"):
            print(f"[OK] {name}: present")
        else:
            print(f"[WARN] {name}: missing and install failed — {info.get('install_error', 'unknown error')}")

    key = report["anthropic_api_key"]
    if key["present"]:
        print("[OK] ANTHROPIC_API_KEY is set")
    else:
        print("[INFO] ANTHROPIC_API_KEY not set (optimization/eval gated; not an error)")

    print("=" * 60)
    print("Preflight OK" if hard_ok else "Preflight BLOCKED — fix hard prerequisites above")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="doctor",
        description="Preflight checks for the agent-architect pipeline.",
    )
    parser.add_argument("--json", dest="json_out", help="Write the full report JSON here.")
    args = parser.parse_args(argv)

    report, hard_ok = run_doctor()
    _print_summary(report, hard_ok)

    if args.json_out:
        out = Path(args.json_out)
        try:
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(report, indent=2), encoding="utf-8")
            print(f"Wrote report JSON: {out.resolve()}")
        except OSError as exc:
            print(f"warning: could not write JSON to {out}: {exc}", file=sys.stderr)

    return 0 if hard_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
