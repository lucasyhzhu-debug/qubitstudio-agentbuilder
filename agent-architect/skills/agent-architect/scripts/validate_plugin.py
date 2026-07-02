"""Plugin-level structural validator for agent-architect-generated plugins.

Validates a generated plugin tree against the canonical formats in
``references/plugin-format.md``: the manifest, every skill's SKILL.md frontmatter (required +
allowed keys), agent and command frontmatter, and (if present) ``.mcp.json`` and
``marketplace.json``.

It is the M2 structural gate the assembly pass runs before evals. It emits a per-item pass/fail
result to stdout and, with ``--json``, a structured file in a shape ``render_setup.py --validation``
can consume (``{component_key: {passed, message}}`` plus an ``overall`` summary). Exit code is
non-zero if any check fails.

Pure standard library, with one optional dependency: ``pyyaml`` is used to parse frontmatter if it
is importable; otherwise a yaml-free fallback parser (mirroring skill-creator's
``parse_skill_md``) is used, so the validator works even when pyyaml is absent (per R2).

CLI
---
    python -m scripts.validate_plugin <plugin_root> [--json <out.json>]

Run from anywhere; ``<plugin_root>`` is the generated plugin directory (absolute path recommended,
since the repo lives on a Windows OneDrive path with spaces).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Optional pyyaml; fall back to a yaml-free parser if unavailable.
try:  # pragma: no cover - import guard
    import yaml as _yaml  # type: ignore
    _HAVE_YAML = True
except Exception:  # pragma: no cover - import guard
    _yaml = None
    _HAVE_YAML = False


# Allowed/required frontmatter keys per plugin-format.md.
SKILL_ALLOWED = {"name", "description", "license", "allowed-tools", "metadata", "compatibility"}
SKILL_REQUIRED = {"name", "description"}
AGENT_REQUIRED = {"name", "description", "tools"}
COMMAND_REQUIRED = {"description"}

PLUGIN_REQUIRED = {"name", "description", "author"}


# --------------------------------------------------------------------------- #
# Frontmatter parsing (pyyaml if available, else yaml-free fallback)
# --------------------------------------------------------------------------- #

def _split_frontmatter(text: str):
    """Return (frontmatter_text, rest) or raise ValueError if no frontmatter block."""
    lines = text.split("\n")
    # Single gate: the first line must be exactly '---'. This also rejects a file whose
    # first line is e.g. '---name: x' (no standalone opening fence).
    if not lines or lines[0].strip() != "---":
        raise ValueError("missing frontmatter (no opening '---')")
    end_idx = None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end_idx = i
            break
    if end_idx is None:
        raise ValueError("missing frontmatter (no closing '---')")
    return "\n".join(lines[1:end_idx]), "\n".join(lines[end_idx + 1:])


def _fallback_parse_frontmatter(fm_text: str) -> dict:
    """yaml-free, line-based frontmatter parser.

    Mirrors skill-creator's parse_skill_md handling of simple scalar keys and YAML block scalars
    (``>``/``|`` and their chomping variants). A key with an empty value followed by indented
    ``- item`` lines is parsed into a real Python list. A key with an empty value followed by
    indented ``key: value`` mappings is recorded as the key with a placeholder dict so presence
    checks still work; we do not need its values for structural validation. Good enough for
    required/allowed-key checks when pyyaml is absent.
    """
    result: dict = {}
    lines = fm_text.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.lstrip().startswith("#"):
            i += 1
            continue
        # Top-level keys start at column 0 (no leading whitespace).
        if line[0] in (" ", "\t"):
            i += 1
            continue
        m = re.match(r"^([A-Za-z0-9_\-]+):(.*)$", line)
        if not m:
            i += 1
            continue
        key = m.group(1)
        value = m.group(2).strip()
        if value in (">", "|", ">-", "|-", ">+", "|+"):
            # Block scalar: consume indented continuation lines.
            cont = []
            i += 1
            while i < len(lines) and (lines[i].startswith(" ") or lines[i].startswith("\t") or not lines[i].strip()):
                if lines[i].strip():
                    cont.append(lines[i].strip())
                i += 1
            result[key] = " ".join(cont)
            continue
        if value == "":
            # Empty value: could introduce a block sequence (indented ``- item`` lines), a
            # nested mapping (indented ``key: value`` lines), or just be an empty scalar.
            # Peek at the first non-blank following line to decide.
            j = i + 1
            first_indented = None
            while j < len(lines):
                if not lines[j].strip():
                    j += 1
                    continue
                if lines[j].startswith(" ") or lines[j].startswith("\t"):
                    first_indented = lines[j]
                break
            if first_indented is not None and first_indented.strip().startswith("- "):
                # Block sequence -> collect into a real list.
                items: list = []
                i += 1
                while i < len(lines) and (lines[i].startswith(" ") or lines[i].startswith("\t") or not lines[i].strip()):
                    stripped = lines[i].strip()
                    if stripped.startswith("- "):
                        items.append(stripped[2:].strip().strip('"').strip("'"))
                    i += 1
                result[key] = items
                continue
            if first_indented is not None:
                # Nested mapping (indented ``key: value``): placeholder; presence is what matters.
                result[key] = {}
                i += 1
                while i < len(lines) and (lines[i].startswith(" ") or lines[i].startswith("\t") or not lines[i].strip()):
                    i += 1
                continue
            result[key] = ""
            i += 1
            continue
        # Inline list: [a, b, c]
        if value.startswith("["):
            if value.endswith("]"):
                inner = value[1:-1].strip()
                items = [x.strip().strip('"').strip("'") for x in inner.split(",")] if inner else []
                result[key] = items
            else:
                # Malformed (bracket not closed on this line): don't mis-split. Record the key
                # as present with the raw string so presence checks still pass.
                result[key] = value
            i += 1
            continue
        result[key] = value.strip('"').strip("'")
        i += 1
    return result


def parse_frontmatter(path: Path) -> dict:
    """Parse a markdown file's YAML frontmatter into a dict. Raises ValueError on malformed input."""
    text = path.read_text(encoding="utf-8")
    fm_text, _rest = _split_frontmatter(text)
    if _HAVE_YAML:
        try:
            data = _yaml.safe_load(fm_text)
        except Exception as exc:  # yaml.YAMLError and friends
            raise ValueError(f"invalid YAML frontmatter: {exc}")
        if data is None:
            data = {}
        if not isinstance(data, dict):
            raise ValueError("frontmatter must be a YAML mapping")
        return data
    return _fallback_parse_frontmatter(fm_text)


# --------------------------------------------------------------------------- #
# Result accumulation
# --------------------------------------------------------------------------- #

class Results:
    def __init__(self):
        self.items: dict[str, dict] = {}  # key -> {passed, message}
        self.order: list[str] = []

    def add(self, key: str, passed: bool, message: str):
        # Disambiguate duplicate keys (shouldn't happen, but be safe).
        if key in self.items:
            n = 2
            while f"{key}#{n}" in self.items:
                n += 1
            key = f"{key}#{n}"
        self.items[key] = {"passed": bool(passed), "message": message}
        self.order.append(key)

    def ok(self, key: str, message: str = "ok"):
        self.add(key, True, message)

    def fail(self, key: str, message: str):
        self.add(key, False, message)

    @property
    def all_passed(self) -> bool:
        return all(v["passed"] for v in self.items.values())


# --------------------------------------------------------------------------- #
# Individual checks
# --------------------------------------------------------------------------- #

def _check_manifest(root: Path, res: Results) -> None:
    manifest = root / ".claude-plugin" / "plugin.json"
    key = ".claude-plugin/plugin.json"
    if not manifest.exists():
        res.fail(key, "manifest not found at .claude-plugin/plugin.json")
        return
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        res.fail(key, f"manifest is not valid JSON: {exc}")
        return
    if not isinstance(data, dict):
        res.fail(key, "manifest must be a JSON object")
        return
    missing = sorted(k for k in PLUGIN_REQUIRED if not data.get(k))
    if missing:
        res.fail(key, f"manifest missing required field(s): {', '.join(missing)}")
        return
    author = data.get("author")
    if not (isinstance(author, dict) and author.get("name")) and not isinstance(author, str):
        res.fail(key, "manifest 'author' should be an object with a 'name' (or a string)")
        return
    res.ok(key, "manifest has name, description, author")


def _check_md_frontmatter(path: Path, key: str, required: set, allowed: set | None, res: Results) -> None:
    try:
        fm = parse_frontmatter(path)
    except ValueError as exc:
        res.fail(key, str(exc))
        return
    missing = sorted(k for k in required if not _present(fm, k))
    if missing:
        res.fail(key, f"frontmatter missing required key(s): {', '.join(missing)}")
        return
    if allowed is not None:
        extra = sorted(set(fm.keys()) - allowed)
        if extra:
            res.fail(key, f"frontmatter has disallowed key(s): {', '.join(extra)} "
                          f"(allowed: {', '.join(sorted(allowed))})")
            return
    res.ok(key, f"frontmatter ok ({', '.join(sorted(required))} present)")


def _present(fm: dict, k: str) -> bool:
    if k not in fm:
        return False
    v = fm[k]
    if v is None:
        return False
    if isinstance(v, str) and not v.strip():
        return False
    return True


def _check_skills(root: Path, res: Results) -> None:
    skills_dir = root / "skills"
    if not skills_dir.is_dir():
        return  # optional
    for skill_dir in sorted(p for p in skills_dir.iterdir() if p.is_dir()):
        skill_md = skill_dir / "SKILL.md"
        key = f"skills/{skill_dir.name}/SKILL.md"
        if not skill_md.exists():
            res.fail(key, "SKILL.md not found")
            continue
        _check_md_frontmatter(skill_md, key, SKILL_REQUIRED, SKILL_ALLOWED, res)


def _check_agents(root: Path, res: Results) -> None:
    agents_dir = root / "agents"
    if not agents_dir.is_dir():
        return
    for agent_md in sorted(agents_dir.glob("*.md")):
        key = f"agents/{agent_md.name}"
        _check_md_frontmatter(agent_md, key, AGENT_REQUIRED, None, res)


def _check_commands(root: Path, res: Results) -> None:
    commands_dir = root / "commands"
    if not commands_dir.is_dir():
        return
    for cmd_md in sorted(commands_dir.glob("*.md")):
        key = f"commands/{cmd_md.name}"
        _check_md_frontmatter(cmd_md, key, COMMAND_REQUIRED, None, res)


def _check_mcp(root: Path, res: Results) -> None:
    mcp = root / ".mcp.json"
    if not mcp.exists():
        return  # optional
    key = ".mcp.json"
    try:
        data = json.loads(mcp.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        res.fail(key, f".mcp.json is not valid JSON: {exc}")
        return
    if not isinstance(data, dict):
        res.fail(key, ".mcp.json must be a JSON object")
        return
    # Prefer an explicit, non-empty ``mcpServers`` map; otherwise fall back to treating the
    # top level as the server map. If neither yields a usable server map, fail clearly.
    mcp_servers = data.get("mcpServers")
    if isinstance(mcp_servers, dict) and mcp_servers:
        servers = mcp_servers
    else:
        servers = {k: v for k, v in data.items() if k != "mcpServers"}
    if not isinstance(servers, dict) or not servers:
        res.fail(key, ".mcp.json has no server entries "
                      "(expected top-level server map or 'mcpServers')")
        return
    problems = []
    for name, entry in servers.items():
        if not isinstance(entry, dict):
            # Wrong shape at the top level (e.g. scalar values) — surface as a no-servers / shape
            # error rather than a confusing per-entry "must be an object".
            problems.append(f"{name}: server entry must be an object "
                            f"(command-based {{command,args}} or http {{type:'http',url}})")
            continue
        if entry.get("type") == "http":
            if not entry.get("url"):
                problems.append(f"{name}: http transport requires 'url'")
        elif entry.get("command"):
            if "args" in entry and not isinstance(entry["args"], list):
                problems.append(f"{name}: 'args' must be a list")
        else:
            problems.append(f"{name}: must be command-based {{command,args}} or http {{type:'http',url}}")
    if problems:
        res.fail(key, "; ".join(problems))
    else:
        res.ok(key, f"{len(servers)} server entr{'y' if len(servers) == 1 else 'ies'} valid")


def _check_marketplace(root: Path, res: Results) -> None:
    mp = root / "marketplace.json"
    if not mp.exists():
        return  # optional
    key = "marketplace.json"
    try:
        data = json.loads(mp.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        res.fail(key, f"marketplace.json is not valid JSON: {exc}")
        return
    if not isinstance(data, dict):
        res.fail(key, "marketplace.json must be a JSON object")
        return
    plugins = data.get("plugins")
    if not isinstance(plugins, list) or not plugins:
        res.fail(key, "marketplace.json must have a non-empty 'plugins' array")
        return
    res.ok(key, f"lists {len(plugins)} plugin(s)")


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #

def validate_plugin(root: Path) -> Results:
    res = Results()
    if not root.is_dir():
        res.fail(str(root), f"plugin root is not a directory: {root}")
        return res
    _check_manifest(root, res)
    _check_skills(root, res)
    _check_agents(root, res)
    _check_commands(root, res)
    _check_mcp(root, res)
    _check_marketplace(root, res)
    return res


def _to_json_payload(res: Results) -> dict:
    total = len(res.items)
    passed = sum(1 for v in res.items.values() if v["passed"])
    payload = dict(res.items)  # {key: {passed, message}} — consumable by render_setup --validation
    payload["overall"] = {
        "passed": res.all_passed,
        "checks": total,
        "passed_count": passed,
        "failed_count": total - passed,
    }
    return payload


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="validate_plugin",
        description="Structurally validate a generated Claude Code plugin tree.",
    )
    parser.add_argument("plugin_root", help="Path to the generated plugin directory.")
    parser.add_argument("--json", dest="json_out", help="Write structured result JSON here.")
    parser.add_argument("--check-violations", action="store_true",
                        help="also enforce paired violation-eval coverage (evals/violations.json).")
    parser.add_argument("--strict-violations", action="store_true",
                        help="with --check-violations, require a paired eval per named guardrail.")
    args = parser.parse_args(argv)

    root = Path(args.plugin_root).resolve()
    res = validate_plugin(root)

    if args.check_violations:
        try:
            from scripts.check_violation_coverage import check as _vcheck
            _ok, _vres = _vcheck(root, strict=args.strict_violations)
            for r in _vres:
                res.add(f"violations:{r['key']}", r["passed"], r["message"])
        except Exception as exc:  # pragma: no cover - defensive
            res.fail("violations", f"coverage check errored: {exc}")

    # Human-readable stdout.
    print(f"Validating plugin: {root}")
    print(f"Frontmatter parser: {'pyyaml' if _HAVE_YAML else 'yaml-free fallback'}")
    print("-" * 60)
    for key in res.order:
        item = res.items[key]
        mark = "PASS" if item["passed"] else "FAIL"
        print(f"[{mark}] {key}: {item['message']}")
    total = len(res.items)
    passed = sum(1 for v in res.items.values() if v["passed"])
    print("-" * 60)
    print(f"{passed}/{total} checks passed")

    if args.json_out:
        out = Path(args.json_out)
        try:
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(_to_json_payload(res), indent=2), encoding="utf-8")
            print(f"Wrote result JSON: {out.resolve()}")
        except OSError as exc:
            print(f"error: could not write JSON to {out}: {exc}", file=sys.stderr)
            return 1

    return 0 if res.all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
