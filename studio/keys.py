"""OS-env persistence for the connect-integrations wizard (T13). `persist()` is the only
public entry point: it writes each supplied value to the OS environment (so a participant's
already-installed plugin can read it on its next `claude -p` run) and drops a `<tree>/.env`
reference copy alongside the composed vault.

`_write_os_env` is a module-level function so tests can monkeypatch it out — it is the only
function in this module that has a real side effect (subprocess `setx` on Windows, appending
to shell profiles on posix). Never call it from a unit test unmocked.
"""
from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path

def _posix_export_line(key: str, value: str) -> str:
    """Build one `export K=<quoted V>` line for a posix shell profile. Factored out so
    tests can exercise the shell-quoting directly without touching a real file. Uses
    shlex.quote (single-quote form) so pasted quotes/`$`/backticks in `value` can't break
    out of the assignment and run arbitrary shell — newline rejection happens in
    `persist()` before this is ever called."""
    return f"export {key}={shlex.quote(value)}\n"


def _write_os_env(key: str, value: str) -> None:
    """Write one KEY=VALUE to the OS environment so future processes (including a
    cron-launched `claude -p`) can read it. Branches on os.name; has real side effects —
    tests must monkeypatch this out."""
    if os.name == "nt":
        subprocess.run(["setx", key, value], check=True, capture_output=True)
        return
    line = _posix_export_line(key, value)
    for profile in (Path.home() / ".zprofile", Path.home() / ".bash_profile"):
        with open(profile, "a", encoding="utf-8") as f:
            f.write(line)


def persist(values: dict, tree: Path) -> dict:
    """Write every value in `values` to the OS env and drop a `<tree>/.env` reference copy
    (plain `K=V` lines — NOT loaded at runtime by any studio/plugin code; the real values
    live in the OS environment via `_write_os_env`, this file just lets a participant see
    what was written). Returns {"written": [keys], "env_cmds": [what we ran, for the wizard
    to show the participant]}.

    Rejects any value containing a newline BEFORE writing anything — a newline could split
    a Windows `setx` invocation or corrupt a `.env`/shell-profile line (posix export
    injection is additionally blocked by shlex-quoting in `_posix_export_line`, but
    newlines are rejected outright on every platform rather than merely quoted)."""
    for key, value in values.items():
        if "\n" in value or "\r" in value:
            raise ValueError(f"value for {key!r} contains a newline — refusing to persist")

    written: list[str] = []
    env_cmds: list[str] = []
    lines: list[str] = []
    for key, value in values.items():
        _write_os_env(key, value)
        written.append(key)
        env_cmds.append(f"setx {key} <value>" if os.name == "nt" else f'export {key}="<value>"')
        lines.append(f"{key}={value}")

    tree = Path(tree)
    tree.mkdir(parents=True, exist_ok=True)
    (tree / ".env").write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {"written": written, "env_cmds": env_cmds}
