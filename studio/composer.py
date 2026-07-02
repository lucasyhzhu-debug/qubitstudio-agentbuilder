from __future__ import annotations
import json, re, shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import AsyncIterator

_HERE = Path(__file__).resolve().parent
_REPO = _HERE.parent
_CATALOG = _HERE / "catalog.json"
_VAULT_TEMPLATE = _HERE / "templates" / "vault"
_COS = _REPO / "chief-of-staff"

class UnknownPickError(ValueError): ...

@dataclass
class ResolveResult:
    skills: list[str]
    integrations: set[str]
    warnings: list[str] = field(default_factory=list)

def _catalog() -> dict:
    return json.loads(_CATALOG.read_text(encoding="utf-8"))

def resolve(picks: list[str]) -> ResolveResult:
    cat = _catalog()
    by_id = {it["id"]: it for it in cat["shelf"]["items"]}
    unknown = [p for p in picks if p not in by_id]
    if unknown:
        raise UnknownPickError(f"unknown pick(s): {', '.join(unknown)}")
    integrations, warnings = set(), []
    for p in picks:
        integrations.update(by_id[p].get("requires", []))
        for needed in by_id[p].get("needs_skills", []):
            if needed not in picks:
                warnings.append(f"'{p}' routes to '{needed}', which you didn't pick — that route will be inert.")
    return ResolveResult(skills=list(picks), integrations=integrations, warnings=warnings)

def scaffold_vault(vault_dir: Path, owner_name: str, picks: list[str]) -> None:
    vault_dir = Path(vault_dir)
    shutil.copytree(_VAULT_TEMPLATE, vault_dir, dirs_exist_ok=True)
    # Fill the owner-name placeholder wherever the template carries it (voice stays for the tweaker);
    # walking the tree (vs a hardcoded file list) keeps new template files substituted automatically.
    for f in vault_dir.rglob("*.md"):
        text = f.read_text(encoding="utf-8")
        if "{{OWNER_NAME}}" in text:
            f.write_text(text.replace("{{OWNER_NAME}}", owner_name), encoding="utf-8")
    if "drain" in picks:
        (vault_dir / "meta/chief-of-staff/drain-state.json").write_text("{}", encoding="utf-8")

_ALL_SKILLS = ["briefing", "capture", "crm", "drain", "intake", "scheduling", "tasks"]


def _rewrite_reference_paths(text: str, skill_id: str | None) -> str:
    """Rewrite path mentions in a copied SKILL.md or agents/*.md to be
    AGENT-HOME-ROOT-relative (the lean spec §5 invariant). The substrate speaks in four
    forms (grep-verified): `chief-of-staff/skills/<sk>/references/…`,
    `chief-of-staff/references/…`, bare `references/…` meaning THIS skill's dir, and the
    cross-skill shorthand `<sk>/references/…`. In the home, substrate refs live under
    `skills/<sk>/references/` and shared refs under `references/`; SKILL.md bodies live
    under `.claude/skills/`. `skill_id=None` is the agents/*.md mode (gate-2 I5): an
    agent file has no "this skill's dir", so its bare `references/…` already means the
    home root and step 1 is skipped. Deterministic string pass — same class as
    delucas(). Order matters: the bare form first (the lookbehind keeps it off the
    prefixed forms), prefixes after."""
    if skill_id:
        # 1. bare `references/…` (start of a path) → this skill's substrate dir
        text = re.sub(r"(?<![\w/\-.])references/", f"skills/{skill_id}/references/", text)
    # 2. cross-skill shorthand `briefing/references/…` → `skills/briefing/references/…`
    for sk in _ALL_SKILLS:
        text = re.sub(rf"(?<![\w/\-.]){sk}/references/", f"skills/{sk}/references/", text)
    # 3. full substrate prefixes drop their chief-of-staff/ root
    text = text.replace("chief-of-staff/skills/", "skills/")
    text = text.replace("chief-of-staff/references/", "references/")
    # 4. cross-skill SKILL.md mentions live under .claude/ in the home
    text = re.sub(r"(?<![\w/\-.])skills/([\w\-]+)/SKILL\.md", r".claude/skills/\1/SKILL.md", text)
    return text


def copy_home(tree: Path, picks: list[str]) -> None:
    """Copy the substrate into an AGENT HOME (lean spec §5), not a plugin: picked
    SKILL.md under .claude/skills/, agents under .claude/agents/, .mcp.json + shared
    references/ at the root. EVERY skill's references/ ships (inert markdown, kills the
    hard-dep class) at its unchanged `skills/<sk>/references/` location; only PICKED
    skills' SKILL.md ship (what Claude actually triggers on). Reference mentions in
    every shipped SKILL.md AND agents/*.md are rewritten home-root-relative (I5)."""
    tree = Path(tree)
    (tree / ".claude" / "skills").mkdir(parents=True, exist_ok=True)
    shutil.copy2(_COS / ".mcp.json", tree / ".mcp.json")
    (tree / ".claude" / "agents").mkdir(parents=True, exist_ok=True)
    for agent_md in sorted((_COS / "agents").glob("*.md")):
        text = agent_md.read_text(encoding="utf-8")
        (tree / ".claude" / "agents" / agent_md.name).write_text(
            _rewrite_reference_paths(text, None), encoding="utf-8")
    shutil.copytree(_COS / "references", tree / "references")
    for sk in _ALL_SKILLS:
        refs = _COS / "skills" / sk / "references"
        if refs.exists():
            shutil.copytree(refs, tree / "skills" / sk / "references")
    for sk in picks:
        dst = tree / ".claude" / "skills" / sk
        dst.mkdir(parents=True, exist_ok=True)
        text = (_COS / "skills" / sk / "SKILL.md").read_text(encoding="utf-8")
        (dst / "SKILL.md").write_text(_rewrite_reference_paths(text, sk), encoding="utf-8")

_LINEAR_TEAM = "d885fd34-71e6-4e8b-8fc6-da4f6bbf1875"
_LINEAR_PROJ = "504fb62b-28ba-4140-9031-1f03e189c70c"
_LUCAS_VAULT_WIN = r"D:\Documents\wiki-brain"
_LUCAS_VAULT_NIX = "D:/Documents/wiki-brain"
_TEXT_EXT = {".md", ".json", ".ps1", ".py", ".txt"}

def _subs(owner_name: str, vault_dir: Path) -> list[tuple[str, str]]:
    vault = str(vault_dir)
    vault_fwd = vault.replace("\\", "/")
    # Order matters: replace the longer/more-specific vault forms before bare "Lucas".
    return [
        (_LUCAS_VAULT_WIN, vault),
        (_LUCAS_VAULT_NIX, vault_fwd),
        # This repo's substrate is pre-scrubbed to {{VAULT_PATH}} (migration 2026-07-02);
        # the Lucas-form entries above are kept as no-op safety for any stray original text.
        ("{{VAULT_PATH}}", vault_fwd),
        ("{{OWNER_NAME}}", owner_name),
        ("wiki-brain/people/", "people/"),
        (_LINEAR_TEAM, "{{LINEAR_TEAM_ID}}"),
        (_LINEAR_PROJ, "{{LINEAR_PROJECT_ID}}"),
        ("LUCAS_USER_ID", "OWNER_USER_ID"),
        ("lucas@ikigaiventures.ai", "you@example.com"),
        ("lucasknowledgebot", "your-assistant-bot"),
        ("Lucas Zhu", owner_name),
        ("Lucas", owner_name),
    ]

def delucas(tree: Path, owner_name: str, vault_dir: Path) -> None:
    subs = _subs(owner_name, vault_dir)
    for f in Path(tree).rglob("*"):
        if not (f.is_file() and f.suffix.lower() in _TEXT_EXT):
            continue
        text = f.read_text(encoding="utf-8", errors="ignore")
        new = text
        for old, repl in subs:
            new = new.replace(old, repl)
        if new != text:
            f.write_text(new, encoding="utf-8")

def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")

def _edit_json(path: Path, mutate) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    mutate(data)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")

def write_claude_md(tree: Path, agent_name: str, owner: str,
                    vault_dir: Path, picks: list[str]) -> None:
    """The generated agent-home CLAUDE.md — deterministic per lean spec §5: identity
    (slug from the AGENT name), the OWNER's name (the participant — gate-2 I3: a
    distinct argument, so "Owner: atlas" can never happen), resolved vault path,
    picked-skill roster, and NOTHING more. No personalization claim — personalization
    lives in the tweak pass, not this file (review F10). Absorbs plugin.json's identity
    role; greets with identity so a correct launch is self-confirming."""
    cat = _catalog()
    by_id = {it["id"]: it for it in cat["shelf"]["items"]}
    slug = f"{_slug(agent_name)}-cos"
    roster = "\n".join(
        f"- **{p}** ({by_id[p]['name']}): {by_id[p]['what']}"
        for p in picks if p in by_id) or "- (baseline only)"
    vault = str(vault_dir).replace("\\", "/")
    (tree / "CLAUDE.md").write_text(f"""# {slug}

You are **{slug}** — {owner}'s personal chief of staff, composed at the QubitStudio
workshop. This folder is your home: your skills live in `.claude/skills/`, their shared
reference material under `skills/` and `references/`.

## Owner

- {owner}

## Your memory (the vault)

- Your wiki-brain vault lives at: `{vault}`
- People pages, meeting pages, and your `meta/` self-layer (personality, memories,
  lessons) live there. Read it before you act; write what you learn back.

## Your skills

{roster}
""", encoding="utf-8")


def assemble_manifests(tree: Path, integrations: set[str]) -> None:
    """Agent-home form (lean §5): no plugin.json / marketplace.json — the generated
    CLAUDE.md absorbs their identity role. Only the .mcp.json discord-trim behaviour
    survives the rewrite: keep discord only if a Discord-needing integration was picked."""
    mcp_path = tree / ".mcp.json"
    if mcp_path.exists():
        def _mcp(mcp):
            if "discord" not in integrations:
                mcp["mcpServers"] = {k: v for k, v in mcp.get("mcpServers", {}).items()
                                     if k != "discord"}
        _edit_json(mcp_path, _mcp)

def _stage(name: str, status: str) -> dict:
    return {"type": "stage", "name": name, "status": status}

def _onboarding_owner() -> str | None:
    """The participant's onboarding name, if the walk ran (gate-2 I3). Lazy, guarded
    import: composer keeps working standalone and tests monkeypatch this seam."""
    try:
        from studio import onboarding
        return onboarding.load_state().get("name") or None
    except Exception:
        return None


async def compose(picks, owner_name, outdir, vault_dir) -> AsyncIterator[dict]:
    outdir, vault_dir = Path(outdir), Path(vault_dir)
    try:
        yield _stage("preflight", "running")
        res = resolve(picks)
        for w in res.warnings:
            yield {"type": "log", "text": "⚠ " + w}
        yield _stage("preflight", "ok")

        base = _slug(owner_name)
        slug = f"{base}-cos"
        final = outdir / slug
        staging = _HERE / ".cache" / "compose" / slug
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
        staging.mkdir(parents=True, exist_ok=True)

        yield _stage("generate", "running")
        # An in-home vault (the <home>/vault/ default, lean §5) must ride the
        # staging→final move — scaffolding it at its final path would be destroyed by
        # the package step's rmtree below. External vaults (the onboarding second
        # brain) scaffold in place, exactly as before.
        in_home = vault_dir.resolve() == (final / "vault").resolve()
        scaffold_vault(staging / "vault" if in_home else vault_dir, owner_name, picks)
        yield {"type": "component", "key": "vault", "status": "ok"}
        copy_home(staging, picks)
        yield {"type": "component", "key": "shell", "status": "ok"}
        for sk in picks:
            yield {"type": "component", "key": f"skill:{sk}", "status": "ok"}
        yield _stage("generate", "ok")

        yield _stage("assemble", "running")
        delucas(staging, owner_name, vault_dir)
        # gate-2 I3: CLAUDE.md's Owner is the PARTICIPANT (onboarding name); the agent
        # name still drives the slug/identity. Fallback: the agent name.
        write_claude_md(staging, owner_name, _onboarding_owner() or owner_name,
                        vault_dir, picks)
        assemble_manifests(staging, res.integrations)
        yield _stage("assemble", "ok")

        yield _stage("package", "running")
        outdir.mkdir(parents=True, exist_ok=True)
        kept_vault = None
        if final.exists():
            # gate-2 I4: a REBUILD must not destroy the agent's memory — the in-home
            # vault moves aside, the home is rebuilt, then the vault rides back in
            # (replacing the fresh staging scaffold: memories win). Only .env is lost
            # on a rebuild — the documented consequence (spec §6.1).
            if in_home and (final / "vault").exists():
                kept_vault = _HERE / ".cache" / "compose" / f"{slug}-vault-keep"
                if kept_vault.exists():
                    shutil.rmtree(kept_vault, ignore_errors=True)
                shutil.move(str(final / "vault"), str(kept_vault))
            shutil.rmtree(final, ignore_errors=True)
        shutil.move(str(staging), str(final))
        if kept_vault is not None:
            shutil.rmtree(str(final / "vault"), ignore_errors=True)
            shutil.move(str(kept_vault), str(final / "vault"))
        yield _stage("package", "ok")
        yield {"type": "done", "grade": "composed", "plugin_path": str(final),
               "vault_path": str(vault_dir), "integrations": sorted(res.integrations),
               # gate-2 S4 (flagged deviation 11): `;` parses in Windows PowerShell 5.1
               # where `&&` is a parse error; the GUI splits ' ; ' into two lines.
               "install": f"cd {final} ; claude"}
    except UnknownPickError as e:
        yield {"type": "error", "stage": "preflight", "message": str(e)}
    except Exception as e:  # filesystem etc. — never leave a half-agent silently
        yield {"type": "error", "stage": "package", "message": f"{type(e).__name__}: {e}"}
