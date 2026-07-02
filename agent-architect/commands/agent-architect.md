---
description: Start the agent-architect interview to design and scaffold a complete Claude Code plugin (skills + agents + commands + MCP) from a short quiz.
argument-hint: "[one-line description of the agent you want to build]"
---

# /agent-architect

You are starting the **agent-architect** workflow: an interactive interview that designs a
best-in-class Claude Code plugin, proposes a better structure than the user likely had in mind,
and (in later stages) generates and verifies it.

The real logic lives in the `agent-architect` **skill** — do not reimplement it here. Instead:

1. Invoke the `agent-architect` skill now.
2. If the user passed an argument, treat it as their answer to the quiz's opening question
   (the one-line purpose, "Q0") and use it to seed the interview — don't ask Q0 again.
3. Follow the skill's quiz → propose → setup-review pipeline.

Begin the interview.
