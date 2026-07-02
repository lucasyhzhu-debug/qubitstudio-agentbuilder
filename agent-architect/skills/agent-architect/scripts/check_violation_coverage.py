"""Violation-eval coverage check (harness plan H-1).

Enforces ``component-recipes.md`` mandate item 4: every agent that declares a
``## Guardrails`` section must ship at least one PAIRED adversarial violation-eval
in the plugin's ``evals/violations.json``. Optionally (``--strict``) every named
guardrail bullet must have a matching violation entry, not just the agent.

This is a *standalone* gate (it is NOT folded into ``validate_plugin`` by default,
so existing plugins keep validating green until their violation-sets are authored
in H-3). ``validate_plugin --check-violations`` opts into it.

violations.json schema (one per plugin, at ``<plugin>/evals/violations.json``)::

    {
      "plugin": "engagement",
      "violations": [
        {
          "id": "comms-no-fabricated-numbers",   # unique
          "agent": "comms",                        # agents/<agent>.md (or skill name)
          "guardrail": "Fabricated on-page numbers", # must match a ## Guardrails bullet
          "prompt": "<the tempting task>",
          "files": ["fixtures/comms-net-only-spine.md"],  # optional fixtures
          "must_refuse": true,
          "expectations": [                        # observable refusal behaviours
            {"text": "Did NOT print any invented intermediate value"},
            {"text": "Left a labelled gap or requested the figure"}
          ]
        }
      ]
    }

CLI::

    python -m scripts.check_violation_coverage <plugin_root> [--json out] [--strict]

Exit code is non-zero if coverage fails. Pure standard library.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REQUIRED_ENTRY_KEYS = {"id", "agent", "guardrail", "prompt", "expectations"}


def strip_frontmatter(text: str) -> str:
    lines = text.split("\n")
    if lines and lines[0].strip() == "---":
        for i, line in enumerate(lines[1:], start=1):
            if line.strip() == "---":
                return "\n".join(lines[i + 1:])
    return text


def _norm(s: str) -> str:
    """Normalize a guardrail name for matching: lowercase, alnum+space only."""
    return re.sub(r"[^a-z0-9 ]+", " ", s.lower()).strip()


def extract_guardrails(body: str) -> list[str]:
    """Return the named guardrails under a ## Guardrails (or 'Guardrails') section."""
    # isolate the Guardrails section (until the next H2/H1)
    m = re.search(r"\n#{1,3}\s*Guardrails[^\n]*\n(.*?)(?:\n#{1,3}\s|\Z)", "\n" + body, re.DOTALL | re.IGNORECASE)
    if not m:
        return []
    section = m.group(1)
    names = []
    for line in section.split("\n"):
        s = line.strip()
        if not s.startswith("- ") and not s.startswith("* "):
            continue
        item = s[2:].strip()
        # name = bolded lead **X** if present, else text up to first . or :
        b = re.match(r"\*\*(.+?)\*\*", item)
        if b:
            names.append(b.group(1).strip().rstrip(".:"))
        else:
            names.append(re.split(r"[.:]", item, 1)[0].strip())
    return [n for n in names if n]


def scan_agent_guardrails(root: Path) -> dict[str, list[str]]:
    """Map agent/skill name -> its declared guardrail names."""
    out: dict[str, list[str]] = {}
    for md in sorted((root / "agents").glob("*.md")) if (root / "agents").is_dir() else []:
        body = strip_frontmatter(md.read_text(encoding="utf-8", errors="replace"))
        g = extract_guardrails(body)
        if g:
            out[md.stem] = g
    for sk in sorted((root / "skills").glob("*/SKILL.md")) if (root / "skills").is_dir() else []:
        body = strip_frontmatter(sk.read_text(encoding="utf-8", errors="replace"))
        g = extract_guardrails(body)
        if g:
            out[sk.parent.name] = g
    return out


def load_violations(root: Path):
    p = root / "evals" / "violations.json"
    if not p.exists():
        return None, "evals/violations.json not found"
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, f"violations.json invalid JSON: {exc}"
    if not isinstance(data, dict) or not isinstance(data.get("violations"), list):
        return None, "violations.json must be an object with a 'violations' array"
    return data, None


def check(root: Path, strict: bool = False) -> tuple[bool, list[dict]]:
    results: list[dict] = []
    guardrails = scan_agent_guardrails(root)

    if not guardrails:
        results.append({"key": "guardrails", "passed": True,
                        "message": "no agent declares a ## Guardrails section — coverage N/A"})
        return True, results

    data, err = load_violations(root)
    if data is None:
        results.append({"key": "violations.json", "passed": False, "message": err})
        return False, results

    # validate entries
    by_agent: dict[str, list[dict]] = {}
    ids = set()
    for i, v in enumerate(data["violations"]):
        miss = sorted(REQUIRED_ENTRY_KEYS - set(v))
        if miss:
            results.append({"key": f"violations[{i}]", "passed": False,
                            "message": f"entry missing key(s): {', '.join(miss)}"})
            continue
        if v["id"] in ids:
            results.append({"key": f"violations[{i}]", "passed": False,
                            "message": f"duplicate id: {v['id']}"})
            continue
        ids.add(v["id"])
        if not v.get("must_refuse", True):
            results.append({"key": v["id"], "passed": False,
                            "message": "violation-eval must have must_refuse: true"})
            continue
        by_agent.setdefault(v["agent"], []).append(v)

    # coverage: each agent with guardrails needs >=1 violation; strict => per-guardrail
    for agent, names in sorted(guardrails.items()):
        entries = by_agent.get(agent, [])
        if not entries:
            results.append({"key": f"agent:{agent}", "passed": False,
                            "message": f"{len(names)} guardrail(s) but 0 violation-evals"})
            continue
        covered = {_norm(e["guardrail"]) for e in entries}
        uncovered = [n for n in names if not any(_norm(n) in c or c in _norm(n) for c in covered)]
        if uncovered and strict:
            results.append({"key": f"agent:{agent}", "passed": False,
                            "message": f"guardrails with no paired violation-eval: {', '.join(uncovered)}"})
        elif uncovered:
            results.append({"key": f"agent:{agent}", "passed": True,
                            "message": f"{len(entries)} eval(s); {len(uncovered)} guardrail(s) uncovered (warn): {', '.join(uncovered)}"})
        else:
            results.append({"key": f"agent:{agent}", "passed": True,
                            "message": f"{len(entries)} violation-eval(s) cover {len(names)} guardrail(s)"})

    ok = all(r["passed"] for r in results)
    return ok, results


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="check_violation_coverage",
                                 description="Check paired violation-eval coverage for a plugin.")
    ap.add_argument("plugin_root")
    ap.add_argument("--strict", action="store_true", help="require a paired eval per named guardrail")
    ap.add_argument("--json", dest="json_out")
    args = ap.parse_args(argv)

    root = Path(args.plugin_root).resolve()
    if not root.is_dir():
        print(f"[FAIL] plugin root is not a directory: {root}", file=sys.stderr)
        return 1
    ok, results = check(root, strict=args.strict)
    print(f"Violation-eval coverage: {root}  (strict={args.strict})")
    print("-" * 60)
    for r in results:
        print(f"[{'PASS' if r['passed'] else 'FAIL'}] {r['key']}: {r['message']}")
    print("-" * 60)
    passed = sum(1 for r in results if r["passed"])
    print(f"{passed}/{len(results)} coverage checks passed")
    if args.json_out:
        Path(args.json_out).write_text(json.dumps({"plugin": str(root), "passed": ok, "results": results}, indent=2), encoding="utf-8")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
