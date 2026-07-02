# Architecture spec — the skill↔subagent contract (the spine)

This document defines the single artifact the whole pipeline hangs on: the **architecture spec**.
The orchestrator skill produces one spec from the quiz, gets it approved via the HTML setup review,
then (in later milestones) hands each component — sliced from the spec, plus shared context — to a
generator, collects receipts, and runs an assembly pass. Because the spec is the **single source
of truth**, parallel generators cannot drift and the build is deterministic and reproducible.

This file is read by later milestones (generation, assembly, eval). Keep it precise.

## Table of contents
1. Spec schema (top level)
2. `plugin` block
3. `shared` block
4. `components` array (per type)
5. `cross_references`
6. `quality_bar`
7. Full worked example
8. Per-component generator payload (skill → generator)
9. Generator receipt (generator → skill)
10. Assembly pass responsibilities
11. Validation rules

---

## 1. Spec schema (top level)

```jsonc
{
  "spec_version": "1.0",          // schema version; bump on breaking changes
  "plugin":   { ... },            // see §2 — manifest-level facts (source of truth for plugin.json)
  "shared":   { ... },            // see §3 — context every generator reuses verbatim
  "components": [ ... ],          // see §4 — one entry per skill/agent/command/mcp to generate
  "cross_references": [ ... ],    // see §5 — typed edges between components
  "quality_bar": { ... }         // see §6 — eval thresholds (used in later milestones)
}
```

`spec_version`, `plugin`, and `components` are required. `shared`, `cross_references`, and
`quality_bar` are recommended but the renderer tolerates their absence.

---

## 2. `plugin` block

Manifest-level facts. The assembly pass writes `plugin.json` (and the marketplace listing) from
**this block only** — generators never touch the manifest.

| Field | Req? | Meaning |
|---|---|---|
| `name` | yes | kebab-case plugin name = folder name = primary command name. |
| `description` | yes | The pushy one-liner (what + when). Drives discovery. |
| `author` | yes | `{ "name", "email" }`. |
| `version` | no | Semver; default `"0.1.0"`. |
| `license` | no | SPDX id or `"UNLICENSED"`. |
| `keywords` | no | Array of strings. |
| `category` | no | e.g. `"developer-tools"`. |
| `deliverable_grade` | yes | `"personal"` (install to `~/.claude`) or `"client-ready"` (marketplace.json + packaged `.plugin` + README/INSTALL). Decided in Q1; gates packaging. |
| `output_root` | yes | Absolute path where the generated plugin tree will be written. |

---

## 3. `shared` block

Context that **every** generator receives verbatim, so independently-generated components speak the
same language. This is the main anti-drift mechanism alongside the spec.

| Field | Req? | Meaning |
|---|---|---|
| `naming_convention` | no | e.g. "kebab-case files, snake_case Python, verbs for commands". |
| `domain_context` | yes | A paragraph describing the domain/problem, reused verbatim by every generator so terminology and assumptions match. |
| `global_glossary` | no | Object of term → definition shared across components. |

---

## 4. `components` array

One entry per thing to generate. Every component has `id` (unique, `"<type>:<short>"`), `type`, a
human `name`, and (where it produces files) a `rel_path` relative to `output_root`. Type-specific
fields follow.

### 4a. `type: "skill"`
| Field | Req? | Meaning |
|---|---|---|
| `id` | yes | e.g. `"skill:intake"`. |
| `type` | yes | `"skill"`. |
| `name` | yes | kebab-case skill name. |
| `rel_path` | yes | e.g. `"skills/intake"` (the skill directory). |
| `purpose` | yes | One-paragraph statement of what the skill does. |
| `trigger_intent` | yes | The user intents/phrases that should trigger it (feeds the description). |
| `description_seed` | yes | A draft pushy description the generator refines into final frontmatter. |
| `needs_scripts` | no | Bool or list — deterministic work that should live in `scripts/`. |
| `needs_references` | no | Array of reference doc topics the skill should ship. |
| `needs_assets` | no | Bool or list — templates/brand files needed. |
| `evals` | no | `{ "behavioral": bool, "trigger": bool }` — which eval kinds apply (later milestones). |
| `depends_on` | no | Array of component ids this skill relies on (e.g. `["mcp:notion","agent:reviewer"]`). |

### 4b. `type: "agent"` (subagent)
| Field | Req? | Meaning |
|---|---|---|
| `id` | yes | e.g. `"agent:reviewer"`. |
| `type` | yes | `"agent"`. |
| `name` | yes | Agent name (must match what skill bodies reference). |
| `rel_path` | yes | e.g. `"agents/reviewer.md"`. |
| `purpose` | yes | What the subagent does and why it's isolated (heavy/context-polluting step). |
| `tools` | yes | Array of allowed tools, least-privilege (e.g. `["Read","Grep"]`). |
| `model` | no | `"inherit"` (default) or a specific model id/alias. |
| `invoked_by` | no | Array of component ids that spawn it (e.g. `["skill:intake"]`). |

### 4c. `type: "command"`
| Field | Req? | Meaning |
|---|---|---|
| `id` | yes | e.g. `"command:onboard"`. |
| `type` | yes | `"command"`. |
| `name` | yes | Command name (the `/name`). |
| `rel_path` | yes | e.g. `"commands/onboard.md"`. |
| `argument_hint` | no | Placeholder shown after the command, e.g. `"[client name]"`. |
| `delegates_to` | no | Component id the command hands off to (usually a skill). |

### 4d. `type: "mcp"`
| Field | Req? | Meaning |
|---|---|---|
| `id` | yes | e.g. `"mcp:notion"`. |
| `type` | yes | `"mcp"`. |
| `server_name` | yes | The key written into `.mcp.json`. |
| `discovery` | no | `{ "via": "mcp-registry", "keywords": [...] }` — how the server was found. |
| `transport` | yes | `"command"` (stdio) or `"http"`. |
| `auth_owner` | yes | Who completes auth — normally `"user"` (we never commit secrets). |

> An `mcp` component produces no files of its own at generation time; the assembly pass writes the
> `.mcp.json` entry from it. It still appears on the setup review so the user knows what auth they
> must complete.

---

## 5. `cross_references`

Typed edges that make the component graph explicit. The assembly pass verifies every edge resolves
to real component ids.

```jsonc
"cross_references": [
  { "from": "command:onboard", "to": "skill:intake",   "kind": "delegates_to" },
  { "from": "skill:intake",    "to": "agent:reviewer", "kind": "spawns" },
  { "from": "skill:intake",    "to": "mcp:notion",     "kind": "uses_server" }
]
```

`kind` ∈ `delegates_to | spawns | uses_server`.

---

## 6. `quality_bar`

Thresholds the eval loop (later milestone) checks against.

| Field | Default | Meaning |
|---|---|---|
| `trigger_accuracy` | `0.85` | Min fraction of trigger-eval queries that route correctly. |
| `behavioral_pass_rate` | `0.8` | Min fraction of behavioral assertions that pass. |
| `min_runs` | `3` | Times each query/eval is run for a stable rate. |

---

## 7. Full worked example

```json
{
  "spec_version": "1.0",
  "plugin": {
    "name": "standup-bot",
    "description": "Drafts your daily standup from git activity and your task tracker, and reviews it for clarity before you post. Use when the user wants to write a standup, summarize yesterday's work, or prep for daily sync.",
    "author": { "name": "Lucas Zhu", "email": "you@example.com" },
    "version": "0.1.0",
    "license": "UNLICENSED",
    "keywords": ["standup", "git", "productivity", "notion"],
    "category": "developer-tools",
    "deliverable_grade": "personal",
    "output_root": "C:\\Users\\lucas\\OneDrive\\Documents\\Consulting Agents\\standup-bot"
  },
  "shared": {
    "naming_convention": "kebab-case files, snake_case Python, verbs for commands",
    "domain_context": "A solo consultant who wants a daily standup drafted from their git commits and their Notion task board, then sanity-checked for clarity before posting to Slack. Tone: concise, first-person, no fluff.",
    "global_glossary": {
      "standup": "A short daily status: what I did, what I'll do, blockers.",
      "blocker": "Anything preventing progress that needs someone else."
    }
  },
  "components": [
    {
      "id": "skill:standup",
      "type": "skill",
      "name": "standup",
      "rel_path": "skills/standup",
      "purpose": "Gathers git activity and Notion tasks, drafts a standup in the user's voice, then asks the reviewer subagent to tighten it.",
      "trigger_intent": "write my standup, summarize what I did yesterday, prep for daily sync",
      "description_seed": "Drafts your daily standup from git activity and your Notion tasks, then tightens it. Use whenever the user wants to write/prep a standup or summarize yesterday's work.",
      "needs_scripts": ["collect_git_activity"],
      "needs_references": ["standup-format"],
      "needs_assets": false,
      "evals": { "behavioral": true, "trigger": true },
      "depends_on": ["mcp:notion", "agent:reviewer"]
    },
    {
      "id": "agent:reviewer",
      "type": "agent",
      "name": "standup-reviewer",
      "rel_path": "agents/standup-reviewer.md",
      "purpose": "Reviews a drafted standup for clarity, length, and missing blockers in isolation, so the editing pass doesn't pollute the main draft context.",
      "tools": ["Read"],
      "model": "inherit",
      "invoked_by": ["skill:standup"]
    },
    {
      "id": "command:standup",
      "type": "command",
      "name": "standup",
      "rel_path": "commands/standup.md",
      "argument_hint": "[date, default today]",
      "delegates_to": "skill:standup"
    },
    {
      "id": "mcp:notion",
      "type": "mcp",
      "server_name": "notion",
      "discovery": { "via": "mcp-registry", "keywords": ["notion", "tasks"] },
      "transport": "http",
      "auth_owner": "user"
    }
  ],
  "cross_references": [
    { "from": "command:standup", "to": "skill:standup",   "kind": "delegates_to" },
    { "from": "skill:standup",   "to": "agent:reviewer",  "kind": "spawns" },
    { "from": "skill:standup",   "to": "mcp:notion",      "kind": "uses_server" }
  ],
  "quality_bar": { "trigger_accuracy": 0.85, "behavioral_pass_rate": 0.8, "min_runs": 3 }
}
```

---

## 8. Per-component generator payload (skill → generator)

In a later milestone the skill fans out one generator invocation per component. Each receives
**exactly its slice plus shared context** — never the whole spec — so it can't reach into siblings:

```jsonc
{
  "component": { /* the single component object from spec.components */ },
  "shared":    { /* spec.shared, verbatim */ },
  "plugin":    { /* spec.plugin minus output_root internals it doesn't need; name/description/author/version/license */ },
  "output_root": "<absolute path>",
  "reference_paths": {
    "plugin_format":     "<abs path to references/plugin-format.md>",
    "component_recipes": "<abs path to references/component-recipes.md>",   // M2
    "schemas":           "<abs path to references/schemas.md>"              // M3, only if evals
  }
}
```

The generator creates **only its component's files** under `output_root/<rel_path>`. It does NOT
write `plugin.json`, `.mcp.json`, `marketplace.json`, or `README` — those are the assembly pass's
job (source of truth = spec).

---

## 9. Generator receipt (generator → skill)

Every generator returns exactly this so the assembly pass can reconcile the build:

```jsonc
{
  "component_id": "skill:standup",
  "files_written": ["skills/standup/SKILL.md", "skills/standup/scripts/collect_git_activity.py"],
  "final_description": "Drafts your daily standup ...",   // the actual description it wrote
  "declared_tools": ["Read", "Bash"],                      // tools it ended up using/allowing
  "references_to": ["agent:standup-reviewer", "mcp:notion"], // sibling ids it actually references
  "scripts_entrypoints": ["python -m scripts.collect_git_activity"],
  "open_questions": ["Should git history span 1 day or since last standup?"]
}
```

`files_written` and `references_to` are what the assembly pass cross-checks against the spec.

---

## 10. Assembly pass responsibilities

Runs in the main session (it needs all receipts at once, so it is NOT a subagent). Steps:

1. **Collect receipts** into a `component_id → receipt` map.
2. **Validate cross-references**: every `cross_references` edge must resolve to a real component id,
   and every `references_to` a generator reported should correspond to a declared edge. Reconcile
   drifted names (an agent's frontmatter `name` must equal what skill bodies call it).
3. **Write the manifest** `plugin.json` from `spec.plugin` (NOT from generator output).
4. **Write `.mcp.json`** for each `type:"mcp"` component (command-based `{command,args}` or
   http-based `{type:"http",url,headers}` with `${ENV}` placeholders, per `plugin-format.md` §6).
5. **Write distribution files** `marketplace.json` + `README.md`/`INSTALL.md` ONLY if
   `deliverable_grade == "client-ready"`.
6. **Validate the whole tree** with `validate_plugin.py` (M2) before evals.

The guiding rule: **the spec is the source of truth; generators own component files, the skill owns
the manifest and the wiring.**

---

## 11. Validation rules (minimal, enforced by render_setup.py in M1)

`render_setup.py` validates the spec just enough to render safely and exits non-zero with a clear
message if it's malformed:
- Top-level must be a JSON object.
- `plugin` must exist and have a `name`.
- `components` must be a list (may be empty).
- Each component must have `id` and `type`; `type` should be one of skill/agent/command/mcp
  (unknown types render in a generic card rather than crashing).
Missing optional fields render as "—" or sensible placeholders — never a crash.
