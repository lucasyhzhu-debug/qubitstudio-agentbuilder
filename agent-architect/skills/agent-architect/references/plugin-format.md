# Plugin format (our canonical, self-contained reference)

This is the authoritative description of every file format `agent-architect` generates. It is
deliberately self-contained: generation must never depend on any external plugin being installed,
on a docs site being reachable, or on a version-brittle cache path. If a format detail matters for
generation, it is captured here.

## Table of contents
1. Plugin directory layout
2. `.claude-plugin/plugin.json`
3. `skills/<name>/SKILL.md`
4. `agents/<name>.md`
5. `commands/<name>.md`
6. `.mcp.json`
7. `marketplace.json` (listing)
8. Conventions & gotchas

---

## 1. Plugin directory layout

A plugin is a directory whose `.claude-plugin/plugin.json` declares it. Everything else is
optional and discovered by convention:

```
<plugin-root>/
├── .claude-plugin/
│   └── plugin.json            # REQUIRED — the manifest
├── commands/                  # optional — one .md per slash command
│   └── <command>.md
├── skills/                    # optional — one subdir per skill
│   └── <skill>/
│       ├── SKILL.md           # REQUIRED for the skill
│       ├── references/        # docs the skill reads on demand
│       ├── scripts/           # executable helpers (run as python -m scripts.<name>)
│       └── assets/            # templates / brand files used in output
├── agents/                    # optional — one .md per subagent
│   └── <agent>.md
└── .mcp.json                  # optional — MCP server declarations
```

Folder name, plugin `name`, and the primary command name should share one kebab-case identifier.

---

## 2. `.claude-plugin/plugin.json`

The manifest. JSON (no comments).

| Field | Req? | Notes |
|---|---|---|
| `name` | yes | kebab-case; matches the plugin folder. |
| `description` | yes | One line, "what + when to use". Drives discovery — make it specific and a little pushy so it triggers. |
| `author` | yes | Object `{ "name": "...", "email": "..." }`. |
| `version` | no | Semver string, e.g. `"0.1.0"`. Start at `0.1.0`. |
| `license` | no | SPDX id or `"UNLICENSED"`. |
| `category` | no | e.g. `"developer-tools"`, `"strategy"`, `"research"`. Aids marketplace placement. |
| `keywords` | no | Array of strings for searchability. |

Example:

```json
{
  "name": "standup-bot",
  "description": "Drafts your daily standup from git activity and your task tracker. Use when the user asks to write a standup, summarize what they did yesterday, or prep for daily sync.",
  "version": "0.1.0",
  "author": { "name": "Lucas Zhu", "email": "you@example.com" },
  "license": "UNLICENSED",
  "category": "developer-tools",
  "keywords": ["standup", "git", "productivity"]
}
```

---

## 3. `skills/<name>/SKILL.md`

Markdown with YAML frontmatter, then a markdown body of instructions.

**Allowed frontmatter keys** (a validator enforces this set — do not invent others):

| Key | Req? | Notes |
|---|---|---|
| `name` | yes | Skill identifier (kebab-case). |
| `description` | yes | The primary triggering mechanism. Include BOTH what it does AND when to use it. Make it pushy — skills tend to under-trigger. All "when to use" info lives here, not in the body. |
| `license` | no | SPDX id or `"UNLICENSED"`. |
| `allowed-tools` | no | Restrict the tools the skill may use (comma- or list-form). |
| `metadata` | no | Free-form object for build bookkeeping. |
| `compatibility` | no | Required tools / environment notes (rarely needed). |

Body guidance (progressive disclosure):
- Keep SKILL.md lean (ideally < 500 lines). Push detail into `references/` and point to it with
  clear "read this when…" guidance.
- Explain the *why* behind instructions rather than piling on rigid MUSTs — the model has good
  theory of mind and works better when it understands intent.
- Put deterministic / repetitive work in `scripts/` and call them, instead of describing the steps
  in prose. Scripts run as `python -m scripts.<name>` with cwd = the skill dir.

```markdown
---
name: standup-bot
description: Drafts a daily standup from git activity and the user's task tracker. Use whenever the user asks to write/prep a standup, summarize yesterday's work, or get ready for daily sync.
---

# Standup Bot
... instructions ...
```

---

## 4. `agents/<name>.md` (subagents)

A subagent is an isolated worker the main session spawns for a heavy or context-polluting step.
Markdown with YAML frontmatter; the body is the agent's system prompt.

| Key | Req? | Notes |
|---|---|---|
| `name` | yes | Identifier the spawning skill references. Must match exactly what skill bodies call. |
| `description` | yes | When to use this subagent. |
| `tools` | yes | The tools the agent may use. Comma-separated list (e.g. `Read, Grep, Bash`). Keep it minimal — least privilege. |
| `model` | no | `inherit` (default — use the caller's model), or a specific model id / alias. |
| `color` | no | UI hint. |

```markdown
---
name: pr-reviewer
description: Reviews a single pull request diff for correctness and style. Spawn one per PR.
tools: Read, Grep, Bash
model: inherit
---

You are a focused PR reviewer. ...
```

---

## 5. `commands/<name>.md` (slash commands)

An explicit entry point the user invokes as `/<name>`. Markdown with YAML frontmatter; the body is
the instruction executed when the command runs (it typically delegates to a skill).

| Key | Req? | Notes |
|---|---|---|
| `description` | yes | What the command does (shown in the command list). |
| `argument-hint` | no | Placeholder shown after the command name, e.g. `"[pr number]"`. |
| `allowed-tools` | no | Restrict tools available while the command runs. |
| `disable-model-invocation` | no | Boolean; if true the command is only user-invokable, not model-invokable. |

```markdown
---
description: Review a pull request for correctness and style.
argument-hint: "[pr number or url]"
---

Invoke the pr-review skill on $ARGUMENTS.
```

---

## 6. `.mcp.json`

Declares MCP servers the plugin needs. JSON object whose **keys are server names** and whose values
describe the transport. The user completes any auth — never commit secrets.

Two value shapes:

**Command-based (stdio)** — a local process:

```json
{
  "mcpServers": {
    "context7": {
      "command": "npx",
      "args": ["-y", "@upstash/context7-mcp"]
    }
  }
}
```

**HTTP-based** — a remote endpoint:

```json
{
  "mcpServers": {
    "github": {
      "type": "http",
      "url": "https://api.githubcopilot.com/mcp/",
      "headers": { "Authorization": "Bearer ${GITHUB_TOKEN}" }
    }
  }
}
```

Notes:
- Some hosts expect the servers under a top-level `mcpServers` object (shown above); others accept
  server names at the top level. Generate the `mcpServers`-wrapped form — it is the most widely
  accepted.
- For command transport: `command` + `args` (+ optional `env`).
- For http transport: `type: "http"`, `url`, optional `headers` (auth via `${ENV_VAR}` placeholders
  the user fills, not literal secrets).

---

## 7. `marketplace.json` (listing)

Only needed for a `client-ready` deliverable that will be distributed through a marketplace. It
lists one or more plugins available from a repository.

```json
{
  "name": "lucas-consulting-agents",
  "owner": { "name": "Lucas Zhu", "email": "you@example.com" },
  "plugins": [
    {
      "name": "standup-bot",
      "source": "./standup-bot",
      "description": "Drafts your daily standup from git activity and your task tracker.",
      "version": "0.1.0",
      "category": "developer-tools",
      "keywords": ["standup", "git", "productivity"]
    }
  ]
}
```

- `source` is a path (or git ref) to the plugin directory relative to the marketplace file.
- The per-plugin fields mirror that plugin's `plugin.json` — keep them in sync (the assembly pass
  derives them from the spec, not by re-reading the manifest).

---

## 8. Conventions & gotchas

- **One kebab-case name** shared by folder / plugin / primary command.
- **Least-privilege tools** on every agent and (where it matters) skill.
- **Descriptions are load-bearing**: skill and plugin descriptions are how Claude decides to use
  them. Specific + pushy > vague.
- **No secrets in `.mcp.json`** — use `${ENV_VAR}` placeholders; auth is the user's job.
- **Windows reality**: scripts are invoked `python -m scripts.<name>` with cwd = the owning skill
  dir; paths can contain spaces — always use absolute paths and quote them.
- **Agent name drift**: a skill body that says "spawn the `pr-reviewer` agent" must match the
  agent file's frontmatter `name`. The assembly pass reconciles this.
