#!/usr/bin/env python3
"""Whole-plugin packager — zips an entire plugin tree into a distributable ``.plugin`` file.

This is the M4 analogue of ``_vendor/package_skill.py`` (which packages a single skill into a
``.skill``). Where that one zips one skill folder, this zips an entire plugin tree — manifest,
skills, agents, commands, ``.mcp.json`` — into ``<plugin_name>.plugin`` (a zip), preserving the
tree structure so it unzips back to a valid, installable plugin (``.claude-plugin/plugin.json`` at
the root).

The plugin name comes from ``.claude-plugin/plugin.json``; the root is validated to contain that
manifest before anything is written.

Excluded from the archive (build artifacts, scratch, secrets, OS junk):
- directories anywhere in the tree: ``__pycache__``, ``node_modules``, ``.git``, ``dist``,
  ``evals`` (eval sets/golden are dev-time inputs, not shipped), and any ``*-workspace`` dir;
- glob-matched files anywhere: ``*.pyc``, ``*.plugin``, ``*.skill``;
- environment/secret files: ``.env`` and ``.env.*``;
- OS junk: ``.DS_Store``, ``Thumbs.db``.

Pure standard library (``zipfile``, ``pathlib``, ``argparse``, ``fnmatch``, ``json``).

CLI
---
    python -m scripts.package_plugin <plugin_root> [--outdir <dir>]

``<plugin_root>`` is the built plugin directory; use an absolute path (the repo lives on a Windows
OneDrive path with spaces). Prints the output path and a file count; exits non-zero on error.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import sys
import zipfile
from pathlib import Path

# Directories excluded anywhere in the tree.
EXCLUDE_DIRS = {"__pycache__", "node_modules", ".git", "dist", "evals"}
# Directory name glob patterns excluded anywhere (e.g. "*-workspace").
EXCLUDE_DIR_GLOBS = {"*-workspace"}
# File name glob patterns excluded anywhere.
EXCLUDE_FILE_GLOBS = {"*.pyc", "*.plugin", "*.skill", ".env", ".env.*"}
# Exact file names excluded anywhere (OS junk).
EXCLUDE_FILES = {".DS_Store", "Thumbs.db"}


def _is_excluded_dir(name: str) -> bool:
    if name in EXCLUDE_DIRS:
        return True
    return any(fnmatch.fnmatch(name, pat) for pat in EXCLUDE_DIR_GLOBS)


def _is_excluded_file(name: str) -> bool:
    if name in EXCLUDE_FILES:
        return True
    return any(fnmatch.fnmatch(name, pat) for pat in EXCLUDE_FILE_GLOBS)


def should_exclude(rel_path: Path) -> bool:
    """Return True if a path (relative to the plugin root) should be left out of the archive."""
    parts = rel_path.parts
    # Exclude if any parent directory component is an excluded dir.
    for part in parts[:-1]:
        if _is_excluded_dir(part):
            return True
    # The path itself: if it names an excluded dir (defensive) or an excluded file.
    name = rel_path.name
    if _is_excluded_dir(name):
        return True
    return _is_excluded_file(name)


def _read_plugin_name(root: Path) -> str:
    """Read the plugin name from ``.claude-plugin/plugin.json``. Raises ValueError on problems."""
    manifest = root / ".claude-plugin" / "plugin.json"
    if not manifest.exists():
        raise ValueError(
            f"not a plugin root: missing .claude-plugin/plugin.json under {root}"
        )
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f".claude-plugin/plugin.json is not valid JSON: {exc}")
    if not isinstance(data, dict):
        raise ValueError(".claude-plugin/plugin.json must be a JSON object")
    name = data.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError(".claude-plugin/plugin.json is missing a non-empty 'name'")
    return name.strip()


def package_plugin(plugin_root, output_dir=None):
    """Package an entire plugin tree into a ``<name>.plugin`` zip.

    Returns the Path to the created ``.plugin`` file. Raises ValueError on validation problems and
    OSError if the archive cannot be written.
    """
    root = Path(plugin_root).resolve()
    if not root.exists():
        raise ValueError(f"plugin root not found: {root}")
    if not root.is_dir():
        raise ValueError(f"plugin root is not a directory: {root}")

    plugin_name = _read_plugin_name(root)

    if output_dir:
        out_dir = Path(output_dir).resolve()
        out_dir.mkdir(parents=True, exist_ok=True)
    else:
        out_dir = Path.cwd()

    out_file = out_dir / f"{plugin_name}.plugin"
    # Write to a temp path in the same dir, then atomically replace the final file only after the
    # archive completes. This guarantees a partial/corrupt archive (e.g. a mid-write failure) never
    # replaces or appears as the final ``.plugin``.
    tmp_file = out_file.with_suffix(out_file.suffix + ".tmp")

    file_count = 0
    skipped = 0
    try:
        with zipfile.ZipFile(tmp_file, "w", zipfile.ZIP_DEFLATED) as zf:
            for path in sorted(root.rglob("*")):
                # Skip symlinks (they are not packaged); warn so the omission is visible.
                if path.is_symlink():
                    print(
                        f"warning: skipping symlink (not packaged): {path}",
                        file=sys.stderr,
                    )
                    skipped += 1
                    continue
                if not path.is_file():
                    continue
                rel = path.relative_to(root)
                # Never include the artifacts we are currently writing (if outdir is inside root).
                if path.resolve() in (out_file.resolve(), tmp_file.resolve()):
                    continue
                if should_exclude(rel):
                    skipped += 1
                    continue
                # Preserve the tree under the plugin name so it unzips to a self-contained plugin dir.
                arcname = Path(plugin_name) / rel
                zf.write(path, arcname.as_posix())
                file_count += 1
        os.replace(tmp_file, out_file)
    except BaseException:
        # Remove the partial temp archive on any failure so no broken artifact remains, then re-raise.
        try:
            tmp_file.unlink()
        except OSError:
            pass
        raise

    return out_file, file_count, skipped


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="package_plugin",
        description="Package an entire Claude Code plugin tree into a distributable .plugin file.",
    )
    parser.add_argument("plugin_root", help="Path to the built plugin directory.")
    parser.add_argument(
        "--outdir",
        dest="outdir",
        default=None,
        help="Output directory for the .plugin file (defaults to the current directory).",
    )
    args = parser.parse_args(argv)

    try:
        out_file, file_count, skipped = package_plugin(args.plugin_root, args.outdir)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"error: could not write .plugin archive: {exc}", file=sys.stderr)
        return 1

    print(f"Packaged plugin: {out_file}")
    print(f"Files archived: {file_count} (skipped {skipped} excluded)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
