# Component recipes — deterministic per-type generation guidance

This is the recipe the `plugin-generator` subagent follows so that independently, parallel-generated
components come out **consistent and deterministic**. Each generator gets one component slice plus
the spec's `shared` block (see `architecture-spec.md` §8) and renders it into files using the rules
here. `plugin-format.md` is the authoritative file-format reference; this file maps **spec fields →
file content** and fixes conventions the format doc leaves open.

Read this together with `plugin-format.md`. Where they overlap, `plugin-format.md` wins on *format*;
this file wins on *which spec field becomes what*.

## Universal rules (all types)

- **Output location**: write under `output_root` at the component's `rel_path`. Always use absolute
  paths; quote paths (Windows OneDrive paths contain spaces).
- **Source of truth**: the spec slice. Do not redesign; render faithfully. Never invent fields the
  spec didn't ask for.
- **Shared context**: reuse `shared.domain_context` verbatim where domain framing is needed, follow
  `shared.naming_convention`, and use `shared.global_glossary` terms consistently. This is the main
  anti-drift mechanism.
- **Descriptions are load-bearing**: for skill/agent/command, the `description` is how Claude decides
  to use the thing. Make it specific and a little pushy — state **what it does AND when to use it**.
- **Never write manifest/wiring files**: no `plugin.json`, `.mcp.json`, `marketplace.json`,
  `README.md`, `INSTALL.md`. Assembly owns those.
- **Receipt**: every generator returns the receipt in `architecture-spec.md` §9. The notes below say
  what goes in each receipt field per type.

---

## 1. `type: "skill"`

### Files to create
- `<rel_path>/SKILL.md` — **required**.
- `<rel_path>/scripts/` + `scripts/__init__.py` + one `.py` per entry — **only if** `needs_scripts`
  is truthy (a bool `true` means "scripts likely needed"; a list names the entry points).
- `<rel_path>/references/` + one `.md` per topic — **only if** `needs_references` is a non-empty
  list (each entry is a doc topic).
- `<rel_path>/assets/` + placeholder template files — **only if** `needs_assets` is truthy.

Do not create empty `scripts/`/`references/`/`assets/` dirs the spec didn't ask for.

### Required frontmatter keys
`name`, `description`. Allowed (do not invent others): `name`, `description`, `license`,
`allowed-tools`, `metadata`, `compatibility`. Set `allowed-tools` only if the spec implies a
restriction; otherwise omit it.

### Deriving the description (pushy, what + when)
Combine `description_seed` (the *what*) with `trigger_intent` (the *when*). Result: one or two
sentences — first the capability, then "Use when …" listing the trigger phrases. Skills under-trigger,
so be concrete and assertive. All "when to use" info lives in the description, not the body.

Example mapping:
```
description_seed: "Drafts your daily standup from git activity and your Notion tasks, then tightens it."
trigger_intent:   "write my standup, summarize what I did yesterday, prep for daily sync"
=>
description: Drafts your daily standup from git activity and your Notion tasks, then tightens it for clarity. Use whenever the user wants to write or prep a standup, summarize what they did yesterday, or get ready for daily sync.
```

### Field → content mapping
| Spec field | Becomes |
|---|---|
| `name` | frontmatter `name` (kebab-case, matches `rel_path` dir). |
| `description_seed` + `trigger_intent` | frontmatter `description` (see above). |
| `purpose` | the opening paragraph of the body (what the skill does / its value). |
| `needs_scripts` | `scripts/<name>.py` files + a "run `python -m scripts.<name>`" pointer in body. |
| `needs_references` | `references/<topic>.md` files + "read this when…" pointers in body. |
| `needs_assets` | `assets/` templates + a body note on when to use them. |
| `depends_on` | body references to those siblings **by name** (spawn the `<agent name>` agent; use the `<server_name>` MCP server). |

### Body shape (lean — keep < ~500 lines, use progressive disclosure)
```markdown
---
name: standup
description: <pushy what + when, derived as above>
---

# Standup

<one paragraph from `purpose`, grounded in shared.domain_context>

## How it works
- <high-level steps; defer detail to references>
- Run `python -m scripts.collect_git_activity` to gather commits.   # if needs_scripts
- Read `references/standup-format.md` for the output format.        # if needs_references
- Spawn the `standup-reviewer` agent to tighten the draft.          # if depends_on an agent
- Use the `notion` MCP server to read the task board.               # if depends_on an mcp
```

### Receipt notes
- `final_description` = the description written.
- `declared_tools` = `allowed-tools` if set, else `[]`.
- `references_to` = ids from `depends_on` that the body actually references.
- `scripts_entrypoints` = `python -m scripts.<name>` for each script written.

---

## 2. `type: "agent"`

### Files to create
- `<rel_path>` (e.g. `agents/<name>.md`) — a single markdown file. Nothing else.

### Required frontmatter keys
`name`, `description`, `tools`. Optional: `model` (default `inherit`), `color`.

### Field → content mapping
| Spec field | Becomes |
|---|---|
| `name` | frontmatter `name` — **must match exactly** what spawning skills call. |
| `purpose` | frontmatter `description` (rephrased as "when to spawn it") + the body system prompt. |
| `tools` | frontmatter `tools` — comma-separated, least-privilege, in spec order. |
| `model` | frontmatter `model` (omit or `inherit` if unspecified). |
| `invoked_by` | informs the description ("Spawn from the <x> skill when …"); not a separate field. |

`tools` form: the spec gives an array (`["Read","Grep"]`); write it comma-separated:
`tools: Read, Grep`.

### Body
The agent's system prompt: who it is, the one focused job it does in isolation, its inputs, and the
exact output it returns to the caller. Ground it in `shared.domain_context`. Keep it single-purpose.

Example:
```markdown
---
name: standup-reviewer
description: Reviews a single drafted standup for clarity, length, and missing blockers, in isolation. Spawn from the standup skill once a draft exists.
tools: Read
model: inherit
---

You are a focused standup reviewer. You receive one drafted standup and return a tightened version
plus a short list of issues (vague items, missing blockers, length). Do not rewrite voice; preserve
the user's first-person tone. Return only the revised standup and the issue list.
```

### Mandatory guardrails (every generated agent) — REQUIRED, do not skip

This section codifies Phase-1 fixes **A1–A4** (`eval-runs/2026-06-09-hypothesis-e2e/REPORT.md`) and the
Phase-3 **meta-finding** that named-but-unguarded guardrails graze in production
(`eval-runs/2026-06-09-engagement-eval/REPORT.md`). The root cause both runs converge on is at the
**builder** level: agents *name* a failure mode in prose but never enforce it, then rationalise around
it. Every agent you generate **must** carry the four items below. None is optional; none is satisfied by
the agent merely mentioning it.

**1. Explicit "Does NOT" boundary clause.** Every generated agent's body carries a trailing negative-scope
clause, *separate from its positive scope*, naming what it never touches / never authors / never owns —
and the owner instead (e.g. "Does NOT build, decompose, or re-tree the hypothesis — that is the
`hypothesis` plugin; it only tests a hypothesis already handed to it"). The description gets a matching
short "Does NOT … (owner instead)" sentence so routing respects the lane.

**2. Role-class mandatory guardrails.** Read the agent's role from the spec and bake in the guardrail(s)
for its class verbatim (an agent may be more than one class — apply all that fit):

- **quant / analysis-class** — ALL arithmetic is the output of code that ran, never computed in prose.
  This explicitly includes scenario, illustrative, alternative-case, and sanity-check numbers: "if a
  scenario is worth reporting, it is worth adding to the script." No figure reaches the reader unless a
  script emitted it.
- **evidence / research-class** — a **HIGH** confidence rating REQUIRES the figure traced to and fetched
  from its **primary publisher**; two related/syndicated/sister-brand vendors, or two figures via the
  same wire, are **NOT** independent triangulation; a path that only ever reaches an aggregator/PR-wire is
  **down-rated** (cap at MEDIUM) or filed as a gap. Every market-size fact carries a **sizing-method +
  scope label** (e.g. retail | wholesale | manufacturer + geography + as-of).
- **craft / comms-class** — emit the **REAL template** (fill the actual `database/templates/<archetype>`
  file verbatim via the generator, matching its actual class names), **never a hand-rolled look-alike**;
  never place a number on a client-facing page that is not in the consumed evidence trail (a bar value, an
  axis anchor, a bridge step) — leave a labelled gap or request it; never self-author a label the spine
  owns.

**3. Anti-self-waiver clause.** Every generated agent states that a guardrail is **NOT** satisfied by
labelling the output "illustrative", "a shortcut", "for this one page / this one eval", "placeholder", or
"footnoted". Naming or disclosing the violation does **not** license it; honest disclosure of a forbidden
route does not convert the violation into compliance.

**4. Paired violation-eval requirement.** For every guardrail you name in a generated agent (the "Does
NOT" boundary, each role-class guardrail, and the anti-self-waiver clause), the agent's eval hooks MUST
include **at least one adversarial hook** that actively tries to violate it and **passes only if the agent
refuses** (flags-and-stops / down-rates / leaves a labelled gap) — not merely "produces output." A named
guardrail with no firing adversarial eval is an incomplete build; the happy-path hooks do not count.

### Receipt notes
- `final_description` = the description written.
- `declared_tools` = the `tools` list.
- `references_to` = `[]` (agents are leaves unless the body references another component by id).
- `scripts_entrypoints` = `[]`.

---

## 3. `type: "command"`

### Files to create
- `<rel_path>` (e.g. `commands/<name>.md`) — a single markdown file. Nothing else.

### Required frontmatter keys
`description`. Optional: `argument-hint`, `allowed-tools`, `disable-model-invocation`.

> Note: the spec field is `argument_hint` (underscore); the **frontmatter key is `argument-hint`**
> (hyphen). Translate it.

### Field → content mapping
| Spec field | Becomes |
|---|---|
| `name` | the `/name` (filename); not a frontmatter key. |
| `argument_hint` | frontmatter `argument-hint` (omit if absent). |
| `delegates_to` | body: delegate to that skill by name, passing `$ARGUMENTS`. |

Derive `description` from the command's purpose / the skill it delegates to (what the command does,
shown in the command list).

### Body
A short instruction that hands off to the target skill.
```markdown
---
description: Draft and tighten today's standup.
argument-hint: "[date, default today]"
---

Invoke the `standup` skill for $ARGUMENTS (default: today).
```

### Receipt notes
- `final_description` = the description written.
- `declared_tools` = `allowed-tools` if set, else `[]`.
- `references_to` = `[delegates_to]` if set.
- `scripts_entrypoints` = `[]`.

---

## 4. `type: "mcp"`

### Files to create
- **None.** The generator writes nothing. The assembly pass writes the `.mcp.json` entry from the
  spec (`server_name`, `transport`, `auth_owner`), per `architecture-spec.md` §10.4 and
  `plugin-format.md` §6.

### What the generator does
Record the server need in the receipt and surface anything unresolved (e.g. the exact `command`/
`args` for stdio transport, or the `url`/`headers` for http transport, or which env var the user
must set) in `open_questions` so assembly can fill `.mcp.json` correctly. Never put real secrets
anywhere — auth is the user's job via `${ENV_VAR}` placeholders.

### Receipt notes
- `files_written` = `[]`.
- `final_description` = `""`.
- `declared_tools` = `[]`.
- `references_to` = ids of components that consume this server, if known (else `[]`).
- `scripts_entrypoints` = `[]`.
- `open_questions` = transport/command/url/auth details assembly needs.

---

## Quick cheat-sheet

| type | writes | required frontmatter | receipt `files_written` |
|---|---|---|---|
| skill | `SKILL.md` (+ scripts/references/assets if asked) | name, description | the files it wrote |
| agent | `agents/<name>.md` | name, description, tools | one file |
| command | `commands/<name>.md` | description | one file |
| mcp | nothing | — | `[]` |
