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

_SHELL = [".claude-plugin", ".mcp.json", "marketplace.json", "agents", "references"]
_ALL_SKILLS = ["briefing", "capture", "crm", "drain", "intake", "scheduling", "tasks"]

def copy_plugin(tree: Path, picks: list[str]) -> None:
    tree = Path(tree)
    tree.mkdir(parents=True, exist_ok=True)
    for item in _SHELL:
        src = _COS / item
        if not src.exists():
            continue
        dst = tree / item
        shutil.copytree(src, dst) if src.is_dir() else shutil.copy2(src, dst)
    # Copy the shared substrate: EVERY skill's references/ (inert markdown, kills the hard-dep
    # class), but only the PICKED skills' SKILL.md (what Claude actually triggers on). Un-picked
    # skills' references land under references/skills/<sk>/ — a folder under skills/ without a
    # SKILL.md reads as a malformed skill to the plugin loader ("1 error during load", finding #7).
    for sk in _ALL_SKILLS:
        refs = _COS / "skills" / sk / "references"
        if refs.exists():
            dst = (tree / "skills" / sk / "references") if sk in picks else (tree / "references" / "skills" / sk)
            shutil.copytree(refs, dst)
    for sk in picks:
        (tree / "skills" / sk).mkdir(parents=True, exist_ok=True)
        shutil.copy2(_COS / "skills" / sk / "SKILL.md", tree / "skills" / sk / "SKILL.md")
    _write_identity(tree, picks)

# The repo contract promises a "raw-skills agent home (.claude/skills/ + CLAUDE.md + root
# .mcp.json)" — but nothing wrote that CLAUDE.md, so every composed agent shipped without an
# identity and the participant's named, voiced chief of staff never spoke as one (finding #8).
# Placeholders are left for delucas()/the tweaker to fill; the voice pass rewrites ## Voice.
def _write_identity(tree: Path, picks: list[str]) -> None:
    template = (_HERE / "templates" / "agent-identity.md").read_text(encoding="utf-8")
    skills_list = "\n".join(f"- `{sk}`" for sk in picks) or "- (no skills picked)"
    (tree / "CLAUDE.md").write_text(template.replace("{{SKILLS_LIST}}", skills_list), encoding="utf-8")

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
        ("lucas.yh.zhu@gmail.com", "you@example.com"),  # was live PII in a sample log line (finding #11)
        ("lucasknowledgebot", "your-assistant-bot"),
        ("needs-lucas", "needs-owner"),  # functional Linear label carried the original owner's name (finding #10)
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

def assemble_manifests(tree: Path, owner_name: str, picks: list[str], integrations: set[str]) -> None:
    base = _slug(owner_name)
    slug = f"{base}-cos"
    description = f"{owner_name}'s chief of staff — composed at the workshop."

    def _plugin(pj):
        pj["name"] = slug
        pj["author"] = {"name": owner_name, "email": "workshop@local"}  # non-empty — empty email can fail plugin validation (P-I3)
        pj["description"] = description
    _edit_json(tree / ".claude-plugin/plugin.json", _plugin)

    def _marketplace(mk):
        mk["name"] = f"{base}-workshop"
        mk["owner"] = {"name": owner_name, "email": ""}
        mk["plugins"] = [{"name": slug, "source": ".", "description": description,
                          "version": "0.1.0", "category": "productivity"}]
    _edit_json(tree / "marketplace.json", _marketplace)
    # Claude Code resolves a local marketplace at <dir>/.claude-plugin/marketplace.json — at the
    # tree root, `/plugin marketplace add <dir>` can't find it and the install step fails (finding #6).
    (tree / "marketplace.json").replace(tree / ".claude-plugin" / "marketplace.json")

    # Trim .mcp.json: keep discord only if a Discord-needing integration was picked.
    mcp_path = tree / ".mcp.json"
    if mcp_path.exists():
        def _mcp(mcp):
            if "discord" not in integrations:
                mcp["mcpServers"] = {k: v for k, v in mcp.get("mcpServers", {}).items() if k != "discord"}
        _edit_json(mcp_path, _mcp)

def _stage(name: str, status: str) -> dict:
    return {"type": "stage", "name": name, "status": status}

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
        staging = _HERE / ".cache" / "compose" / slug
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
        staging.mkdir(parents=True, exist_ok=True)

        yield _stage("generate", "running")
        scaffold_vault(vault_dir, owner_name, picks)
        yield {"type": "component", "key": "vault", "status": "ok"}
        copy_plugin(staging, picks)
        for sk in picks:
            yield {"type": "component", "key": f"skill:{sk}", "status": "ok"}
        yield _stage("generate", "ok")

        yield _stage("assemble", "running")
        delucas(staging, owner_name, vault_dir)
        assemble_manifests(staging, owner_name, picks, res.integrations)
        yield _stage("assemble", "ok")

        yield _stage("package", "running")
        final = outdir / slug
        outdir.mkdir(parents=True, exist_ok=True)
        if final.exists():
            shutil.rmtree(final, ignore_errors=True)
        shutil.move(str(staging), str(final))
        yield _stage("package", "ok")
        yield {"type": "done", "grade": "composed", "plugin_path": str(final),
               "vault_path": str(vault_dir), "integrations": sorted(res.integrations),
               "install": f"/plugin marketplace add {final} ; /plugin install {slug}@{base}-workshop"}
    except UnknownPickError as e:
        yield {"type": "error", "stage": "preflight", "message": str(e)}
    except Exception as e:  # filesystem etc. — never leave a half-agent silently
        yield {"type": "error", "stage": "package", "message": f"{type(e).__name__}: {e}"}
