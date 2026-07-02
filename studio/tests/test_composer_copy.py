import re
from pathlib import Path
from studio import composer

def test_copy_home_agent_form(tmp_path):
    tree = tmp_path / "home"
    composer.copy_home(tree, ["crm"])
    # agent-home form (lean spec §5)
    assert (tree / ".claude/skills/crm/SKILL.md").exists()
    assert (tree / ".claude/agents/context-gatherer.md").exists()
    assert (tree / ".mcp.json").exists()
    assert (tree / "references/google-auth.md").exists()
    # a NON-picked skill's SKILL.md absent, but its references still ship (inert, hard-dep safe)
    assert not (tree / ".claude/skills/drain").exists()
    assert (tree / "skills/drain/references/linear-api.md").exists()
    # the plugin form is GONE
    assert not (tree / ".claude-plugin").exists()
    assert not (tree / "marketplace.json").exists()
    assert not (tree / "skills/crm/SKILL.md").exists()   # SKILL.md lives under .claude/ only

def test_reference_prefixes_rewritten_root_relative(tmp_path):
    tree = tmp_path / "home"
    composer.copy_home(tree, ["briefing"])
    text = (tree / ".claude/skills/briefing/SKILL.md").read_text(encoding="utf-8")
    assert "chief-of-staff/skills/" not in text
    assert "chief-of-staff/references/" not in text

def test_rewrite_reference_paths_forms():
    out = composer._rewrite_reference_paths(
        "read `references/crm-page-format.md` and `chief-of-staff/references/google-auth.md` "
        "and `chief-of-staff/skills/drain/references/linear-api.md` "
        "and `briefing/references/meeting-page.md` "
        "and follow `chief-of-staff/skills/crm/SKILL.md`.", "crm")
    assert "`skills/crm/references/crm-page-format.md`" in out
    assert "`references/google-auth.md`" in out
    assert "`skills/drain/references/linear-api.md`" in out
    assert "`skills/briefing/references/meeting-page.md`" in out
    assert "`.claude/skills/crm/SKILL.md`" in out

def test_rewrite_reference_paths_agent_mode():
    # skill_id=None (a copied agents/*.md — gate-2 I5): bare `references/…` already
    # means the home root and must NOT be re-homed under skills/<sk>/; the
    # chief-of-staff/ prefixes still drop.
    out = composer._rewrite_reference_paths(
        "mint per `chief-of-staff/references/google-auth.md`; see `references/google-auth.md` "
        "and `chief-of-staff/skills/drain/references/linear-api.md` "
        "and `skills/drain/references/drain-state.md`.", None)
    assert out.count("`references/google-auth.md`") == 2
    assert "`skills/drain/references/linear-api.md`" in out
    assert "`skills/drain/references/drain-state.md`" in out
    assert "chief-of-staff/" not in out

def test_agent_files_rewritten_home_root_relative(tmp_path):
    # gate-2 I5: context-gatherer.md is baseline machinery for briefing/drain — its
    # substrate-form paths must be rewritten exactly like the SKILL.md files.
    tree = tmp_path / "home"
    composer.copy_home(tree, ["briefing"])
    text = (tree / ".claude/agents/context-gatherer.md").read_text(encoding="utf-8")
    assert "chief-of-staff/skills/" not in text
    assert "chief-of-staff/references/" not in text

_REF_RE = re.compile(r"(?:[\w.\-]+/)*references/(?:[\w.\-]+/)*[\w.\-]+\.md")

def test_reference_path_invariant_all_shelf_picks(tmp_path):
    """The lean §5 invariant: every reference mentioned in a shipped SKILL.md — or in a
    shipped .claude/agents/*.md (gate-2 I5) — resolves from the agent-home root."""
    picks = ["crm", "briefing", "scheduling", "tasks", "intake", "drain"]
    tree = tmp_path / "home"
    composer.copy_home(tree, picks)
    missing = []
    shipped = [(sk, tree / ".claude/skills" / sk / "SKILL.md") for sk in picks]
    shipped += [(f"agents/{p.name}", p) for p in sorted((tree / ".claude/agents").glob("*.md"))]
    for label, path in shipped:
        text = path.read_text(encoding="utf-8")
        for ref in sorted(set(_REF_RE.findall(text))):
            if not (tree / ref).exists():
                missing.append(f"{label}: {ref}")
    assert not missing, f"unresolvable reference paths from the agent-home root: {missing}"
