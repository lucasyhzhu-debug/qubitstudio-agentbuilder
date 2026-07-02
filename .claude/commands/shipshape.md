Review the design spec or implementation plan at $ARGUMENTS using the shipshape skill.

Read and follow the complete workflow in `.claude/skills/shipshape/SKILL.md` (QubitStudio Agent Builder edition — detect spec mode vs plan mode first).

If no argument was provided (empty $ARGUMENTS), list available documents in `docs/specs/` and `docs/plans/` and ask the user to select one.

Execute all steps (0-7) from the skill file. Save the review report to `docs/reviews/`.
