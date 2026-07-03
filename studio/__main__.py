# studio/__main__.py  — stdlib ONLY (must run before the venv/deps exist)
from __future__ import annotations
import argparse, os, shutil, socket, subprocess, sys, venv, webbrowser
from pathlib import Path

# chat_session (and its imports) are stdlib-only, so this is safe pre-venv;
# reusing the one claude resolver keeps future shim fixes single-site.
from studio.chat_session import resolve_claude

_HERE = Path(__file__).resolve().parent
_REPO = _HERE.parent
_VENV = _REPO / ".venv"
_MIN_PY = (3, 10)

def check_python():
    ok = sys.version_info[:2] >= _MIN_PY
    fix = ""
    if not ok:
        fix = f"Install Python {_MIN_PY[0]}.{_MIN_PY[1]}+ and re-run."
        if sys.platform == "darwin":
            # Stock macOS resolves python3 to Apple's 3.9.6; Homebrew's python is not on PATH
            # until brew shellenv is in ~/.zprofile. Spell out the whole fix (workshop finding).
            fix = ("macOS ships an old system Python. Fix: `brew install python`, add "
                   "`eval \"$(/opt/homebrew/bin/brew shellenv)\"` to ~/.zprofile, open a NEW "
                   "terminal, then re-run. (Intel Macs: /usr/local/bin/brew.)")
    return ("Python >= 3.10", ok, fix)

def check_claude():
    ok = resolve_claude() is not None
    fix = "" if ok else ("Install Claude Code, then run `claude auth login`. "
                         "See https://docs.claude.com/claude-code")
    return ("claude on PATH", ok, fix)

def check_claude_auth():
    # Best-effort: a short smoke. Timeout is tolerated (⚠), an auth error is a hard ❌.
    claude = resolve_claude()
    if not claude:
        return ("claude authed", False, "Install claude first.")
    try:
        r = subprocess.run([claude, "-p", "reply READY", "--max-turns", "1"],
                           capture_output=True, text=True, timeout=25)
    except subprocess.TimeoutExpired:
        return ("claude authed", True, "⚠ couldn't confirm within 25s — if builds hang, run `claude auth login`.")
    ok = r.returncode == 0
    return ("claude authed", ok, "" if ok else "Run `claude auth login`.")

def _deps_importable(py: Path) -> bool:
    return subprocess.run([str(py), "-c", "import fastapi, uvicorn"], capture_output=True).returncode == 0

def _deps_row(ok: bool):
    return ("deps importable", ok, "" if ok else "Deps missing (the launcher installs them).")

def check_deps():
    py = _venv_python()
    if not py.exists():
        return ("deps importable", False, "venv not created yet (the launcher creates it).")
    return _deps_row(_deps_importable(py))

def check_git():
    ok = shutil.which("git") is not None
    return ("git on PATH", ok, "" if ok else "Install git (the composer git-inits your vault).")

def _port_open(port: int) -> bool:
    with socket.socket() as s:
        s.settimeout(0.2)
        return s.connect_ex(("127.0.0.1", port)) == 0

def pick_port(start: int = 8765) -> tuple[int, str]:
    p = start
    while _port_open(p):
        p += 1
    return p, (f"port {p}" if p == start else f"{start} busy → using {p}")

def _venv_python() -> Path:
    return _VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")

def doctor(include_auth: bool = False, deps_ok: bool | None = None) -> list[tuple[str, bool, str]]:
    # The live auth smoke costs ~25s + a quota call — only run it in --doctor (pre-work), NOT on
    # every launch (review P-I1). Normal launch relies on the fast checks + the pre-work --doctor.
    # deps_ok lets callers that already probed the venv (_ensure_venv) skip a second subprocess.
    rows = [check_python(), check_claude()]
    if include_auth:
        rows.append(check_claude_auth())
    rows += [_deps_row(deps_ok) if deps_ok is not None else check_deps(), check_git()]
    return rows

def _print_doctor(rows) -> bool:
    all_ok = True
    for name, ok, fix in rows:
        mark = "OK " if ok else "XX "
        print(f"  [{mark}] {name}" + (f"  → {fix}" if fix else ""))
        all_ok = all_ok and (ok or fix.startswith("⚠"))
    return all_ok

def _venv_outdated() -> bool:
    # A .venv created by an old launching Python (e.g. Apple's 3.9.6 before Homebrew was on
    # PATH) stays poisoned forever because _ensure_venv only creates-if-missing. pyvenv.cfg
    # records the creating interpreter — detect and rebuild instead of failing the doctor.
    cfg = _VENV / "pyvenv.cfg"
    if not cfg.exists():
        return False
    for line in cfg.read_text(encoding="utf-8").splitlines():
        key, _, val = line.partition("=")
        if key.strip() == "version":
            try:
                major, minor = val.strip().split(".")[:2]
                return (int(major), int(minor)) < _MIN_PY
            except ValueError:
                return False
    return False

def _ensure_venv() -> bool:
    if _venv_outdated():
        print("Rebuilding .venv (it was created by an older Python) …")
        shutil.rmtree(_VENV, ignore_errors=True)
    if not _venv_python().exists():
        print("Creating .venv …"); venv.create(_VENV, with_pip=True)
    if _deps_importable(_venv_python()):
        return True
    print("Installing deps …")
    subprocess.run([str(_venv_python()), "-m", "pip", "install", "-q", "-r",
                    str(_REPO / "requirements.txt")], check=True)
    return _deps_importable(_venv_python())

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m studio")
    ap.add_argument("--doctor", action="store_true", help="run preflight checks only")
    ap.add_argument("--no-open", action="store_true")
    ap.add_argument("--port", type=int, default=8765)
    args = ap.parse_args(argv)

    if args.doctor:
        deps_ok = None
        try:
            deps_ok = _ensure_venv()   # pre-work: install deps ahead of Friday so --doctor can go all-green (M6)
        except Exception as e:
            print(f"⚠ couldn't pre-install deps: {e}")
        print("agent-studio doctor:")
        return 0 if _print_doctor(doctor(include_auth=True, deps_ok=deps_ok)) else 1   # pre-work: full incl. auth smoke

    deps_ok = _ensure_venv()
    print("agent-studio doctor:")
    if not _print_doctor(doctor(include_auth=False, deps_ok=deps_ok)):  # launch: fast checks only (P-I1)
        print("\nFix the [XX] items above, then re-run. (⚠ items are non-blocking.)")
        return 1
    port, msg = pick_port(args.port)
    print(f"Serving on http://127.0.0.1:{port}  ({msg})")
    if not args.no_open:
        webbrowser.open(f"http://127.0.0.1:{port}")
    return subprocess.call([str(_venv_python()), "-m", "uvicorn", "studio.server:app",
                            "--host", "127.0.0.1", "--port", str(port)], cwd=str(_REPO))

if __name__ == "__main__":
    raise SystemExit(main())
