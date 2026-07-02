# Setup — before Friday

Four steps, ~15 minutes total. Do these ahead of time so we can start building the moment the
workshop opens — none of it needs the workshop to be running.

## 1. Install Claude Code + sign in

**Windows (PowerShell):**
```powershell
irm https://claude.ai/install.ps1 | iex
claude auth login
```

**macOS / Linux:**
```bash
curl -fsSL https://claude.ai/install.sh | bash
claude auth login
```

`claude auth login` opens a browser — sign in with your Claude account and approve access.

## 2. Install Python 3.10+ and git

**Windows (PowerShell):**
```powershell
winget install Python.Python.3.12
winget install Git.Git
```

**macOS:**
```bash
brew install python git
```

**Linux (Debian/Ubuntu):**
```bash
sudo apt update && sudo apt install -y python3 python3-venv git
```

Already have both? Skip this step — just confirm versions:
```bash
python --version   # or python3 --version — need 3.10+
git --version
```

## 3. Clone the repo

**Windows (PowerShell):**
```powershell
git clone https://github.com/lucasyhzhu-debug/Consulting-Agents.git
cd Consulting-Agents
```

**macOS / Linux:**
```bash
git clone https://github.com/lucasyhzhu-debug/Consulting-Agents.git
cd Consulting-Agents
```

## 4. Run the preflight doctor

**Windows (PowerShell):**
```powershell
.\studio\run.ps1 --doctor
```

**macOS / Linux:**
```bash
python -m studio --doctor
```

This creates the `.venv` and installs dependencies first, then checks Python, `claude` on PATH, a
live `claude` auth smoke, that dependencies import cleanly, and git on PATH. Each row prints `[OK]`
or `[XX]` with a fix hint — work through any `[XX]` rows and re-run until everything is green.

**All green? You're ready for Friday.** If something won't go green, bring it to the workshop and
we'll fix it together — don't lose sleep over it.
