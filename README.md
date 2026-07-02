# QubitStudio Agent Builder

Build your own **chief-of-staff agent** — a personal AI that drains your inbox, briefs your
morning, tracks your people, and schedules your meetings — composed from real, working skills
through a guided browser studio.

This is the participant repo for the QubitStudio **"Build Your Own Chief of Staff"** workshop.
Everything runs on **your laptop**, against **your own** Claude Code login and **your own**
integrations (Discord, Linear, Google). Nothing is hosted; nothing is shared.

## Pre-work (do this before the workshop)

1. **Python 3.10+** — `python --version` to check.
2. **Claude Code** — install from [claude.com/claude-code](https://claude.com/claude-code), then
   log in: `claude` (follow the prompt).
3. **Clone this repo** and run the readiness check:

```bash
git clone https://github.com/lucasyhzhu-debug/qubitstudio-agentbuilder.git
cd qubitstudio-agentbuilder
python -m studio --doctor
```

Every line should print ✅. If anything prints ❌, the fix is on the same line — do it before the
day, or come 15 minutes early.

Full pre-work detail: [`studio/SETUP.md`](studio/SETUP.md).

## Workshop day

```bash
python -m studio
```

Your browser opens the studio. The journey: **pick skills from the shelf → personalize each one →
connect your integrations (guided, with live tests) → your agent is built** into a folder that is
yours to keep, read, and edit. Start it any time with:

```bash
cd dist/<your-agent-name>-cos
claude
```

## What's in here

| Path | What it is |
| --- | --- |
| `studio/` | The browser studio: launcher + doctor, skill shelf, composer, personalizer, integration smokes |
| `chief-of-staff/` | The skill substrate your agent is composed from (briefing, drain, CRM, scheduling, tasks, intake, capture) |
| `docs/specs/` | Design specs for how this all works |
| `docs/ROADMAP.md` | What's being built next |

Facilitators: see [`studio/FACILITATOR.md`](studio/FACILITATOR.md).
