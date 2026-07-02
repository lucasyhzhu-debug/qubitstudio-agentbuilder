Alias for `/spec-plan-pipeline` — run the QubitStudio Agent Builder spec→plan pipeline for the phase described in $ARGUMENTS.

Read and follow the complete workflow in `.claude/skills/spec-plan-pipeline/SKILL.md` (QubitStudio edition). It carries one slice from intent to a landed, executable plan with two `shipshape` review gates, then writes a post-/clear execution handoff.

First identify which of the three units the slice touches — `studio/`, `chief-of-staff/` (substrate — placeholder contract applies), or `agent-architect/` (load-bearing core conversation) — then run the 8 steps in order; do not skip a gate.

If $ARGUMENTS is empty, ask the user what phase to take through the pipeline (and point them at `docs/ROADMAP.md` plus any in-progress spec in `docs/specs/`).

This repo is PUBLIC: scan every diff for real keys, tokens, ids, emails, or personal values before any push — the substrate stays placeholder-form.
