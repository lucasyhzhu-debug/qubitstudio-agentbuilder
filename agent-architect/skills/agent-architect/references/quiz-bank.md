# Quiz bank — the adaptive interview + answer→spec mapping

This is the centerpiece the user actually experiences. It turns a fuzzy idea into a complete
**architecture spec** (see `architecture-spec.md`). Run it as a conversation, not a form.

## How to run it (principles)

- **One cluster at a time.** Ask a focused question (or a tight group), wait, then move on. Never
  paste all of Q0–Q10 at once — that overwhelms and produces shallow answers.
- **Plain language.** Most users aren't fluent in "frontmatter" or "subagent". Explain a term in a
  half-sentence the first time, or avoid it. Read the user's vocabulary and match it.
- **Smart defaults.** Propose the likely answer so the user can just confirm: "I'd default this to
  *personal use* — sound right?" Defaults move fast; the user can always override.
- **Skip settled questions.** If `/agent-architect` was invoked with a one-liner, Q0 is answered.
  If they already said "it's just for me", Q1 is settled. If they only want a single skill, don't
  belabor commands and subagents — offer the default and move on.
- **Propose, don't just record.** The value you add is structure. After you understand the purpose,
  recommend a decomposition and explain why (see the "structure it better" step below). The user
  approves or reshapes it.

## The flow

### Q0 — Purpose (one line)
"In one sentence, what should this agent do?" Capture the essence. If they ramble, reflect it back
as a crisp one-liner and confirm.
→ seeds `plugin.description` and `shared.domain_context`.

### Q1 — Deliverable grade
"Is this just for you, or something you'll hand to a client?" `personal` = install to `~/.claude`,
lighter packaging. `client-ready` = marketplace.json + packaged `.plugin` + README/INSTALL.
Default: `personal` unless they mention a client.
→ `plugin.deliverable_grade`.

### Q2 — Primary surface(s)
"How will you reach this agent — by typing a slash command, by just describing what you want
(skill), or both? And does it need to call out to a heavy helper or an external app?" Establish the
rough shape: how many skills, whether there are commands, subagents, MCP servers.
→ determines which `components` exist (and their `type`s).

### Q3 — Per-skill trigger intent
For each skill: "What kinds of things would you say that should make this kick in?" Gather real
phrasings, including ones that don't name the skill.
→ `component.trigger_intent` and `component.description_seed` (made pushy).

### Q4 — Per-skill determinism
"Is there a step here that should always happen the same way — a calculation, a file format, a data
pull — rather than free-form reasoning?" Deterministic/repetitive steps become `scripts/`.
→ `component.needs_scripts`.

### Q5 — Reference material
"Is there reference knowledge the agent needs on hand — a format spec, a style guide, domain facts?
Things it should read when relevant rather than memorize." 
→ `component.needs_references` (and assets via `needs_assets` if it's templates/brand files).

### Q6 — Subagents (heavy/isolated steps)
"Is there a step that's heavy, noisy, or best done in isolation — something whose intermediate work
shouldn't clutter the main conversation? Those make good subagents." Propose splitting such steps
out. Set least-privilege `tools` and a `model` (default `inherit`).
→ adds `type:"agent"` components + `cross_references` `spawns` edges.

### Q7 — Commands
"Do you want an explicit `/command` entry point, or is triggering by description enough?" If yes,
get an `argument_hint` and which skill it hands off to. Default: one command matching the plugin
name that delegates to the main skill.
→ adds `type:"command"` components + `delegates_to` edges.

### Q8 — MCP / tools / external systems
"Does this need to touch an external system — Notion, GitHub, a database, Slack?" If so, recommend
servers. **If the in-session MCP registry tools `mcp__mcp-registry__search_mcp_registry` and
`suggest_connectors` are available, use them** to find and suggest connectors by keyword. **If they
are NOT present in this session, skip gracefully** — say so in one line and just ask the user which
systems are needed and whether a known server exists. Always note that the user completes auth.
→ adds `type:"mcp"` components (`server_name`, `transport`, `auth_owner:"user"`) + `uses_server` edges.

### Q9 — Evals / quality bar
"How strict should the quality check be before this is 'done'?" Offer the default and let them
tune: `trigger_accuracy 0.85`, `behavioral_pass_rate 0.8`, `min_runs 3`. For a quick personal tool
they may want it lighter; for client-ready, keep or raise it.
→ `quality_bar` + per-skill `evals.{behavioral,trigger}`.

### Q10 — Render & approve (setup review)
Assemble the spec, write it to a file, then render the HTML setup review:
```
python -m scripts.render_setup <spec.json> --out <review.html> --stage proposal
```
Tell the user to open it, review the structure, and click **Approve** or **Request changes** — the
decision exports to `setup-feedback.json` (downloaded + shown in a copyable textarea; no server).
Read that file back. `approve` → spec locked (generation is the next milestone). `changes` → apply
the notes/per-component edits and re-render. (Talking it through in chat instead of the HTML is
fine — the HTML is a convenience, not a gate.)

## The "structure it better" proposal step

This is where you earn your keep — do it before or during Q10, after you understand the purpose.
Don't just transcribe what the user asked for. Propose a decomposition and justify it:

- **What should be a skill vs a subagent vs a command vs an MCP server**, and where the boundaries
  lie. (Reasoning + orchestration → skill. Heavy/noisy/isolated step → subagent. Explicit entry
  point → command. External system access → MCP.)
- **Tool allowlists** per component (least privilege — name the few tools each actually needs).
- **Model choice** per subagent (`inherit` unless a cheaper/stronger model is clearly warranted).
- **The rationale for each choice**, in plain language, so the user can push back meaningfully.

Present it as "here's how I'd structure this, and why" → the user approves or reshapes. The
approved decomposition becomes `components` + `cross_references`. The HTML setup review surfaces
this rationale in its "structure it better" area so the user reviews the *reasoning*, not just the
shape.

## Answer → spec-field mapping table

| Quiz step | Answer captured | Spec field(s) |
|---|---|---|
| Q0 | one-line purpose | `plugin.description` (seed), `shared.domain_context` |
| Q1 | personal vs client-ready | `plugin.deliverable_grade` |
| Q2 | which surfaces exist | the set of `components[].type` |
| Q3 | per-skill trigger phrasings | `component.trigger_intent`, `component.description_seed` |
| Q4 | deterministic steps | `component.needs_scripts` |
| Q5 | reference knowledge / templates | `component.needs_references`, `component.needs_assets` |
| Q6 | heavy/isolated steps | new `type:"agent"` component(s), `tools`, `model`; `spawns` edge |
| Q7 | explicit entry points | new `type:"command"` component(s), `argument_hint`; `delegates_to` edge |
| Q8 | external systems | new `type:"mcp"` component(s), `server_name`, `transport`, `auth_owner`; `uses_server` edge |
| Q9 | strictness | `quality_bar.*`, `component.evals.{behavioral,trigger}` |
| "structure it better" | decomposition + rationale | full `components` + `cross_references` shape; tool allowlists; models |
| name/author/version | (mostly defaults) | `plugin.name` (from Q0), `plugin.author` (Lucas Zhu / you@example.com), `plugin.version` `0.1.0`, `plugin.output_root` (repo root / plugin name) |

Every answer maps to a concrete spec field, and (in later milestones) every spec field maps to a
concrete generator instruction — that two-way mapping is what makes generation deterministic.
