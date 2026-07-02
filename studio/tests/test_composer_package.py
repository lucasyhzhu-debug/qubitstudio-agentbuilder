import asyncio, json
from pathlib import Path
from studio import composer

def _run(agen):
    async def drain():
        return [ev async for ev in agen]
    return asyncio.run(drain())

def test_claude_md_carries_exactly_the_lean_fields(tmp_path):
    tree = tmp_path / "home"; tree.mkdir()
    composer.write_claude_md(tree, "atlas", "Sam Rivera", tmp_path / "vault", ["crm", "tasks"])
    text = (tree / "CLAUDE.md").read_text(encoding="utf-8")
    assert "atlas-cos" in text                            # identity — slug from the AGENT name
    assert "Sam Rivera" in text                           # owner — the PARTICIPANT (gate-2 I3)
    assert "sam-rivera-cos" not in text                   # the owner never leaks into the slug
    assert str(tmp_path / "vault").replace("\\", "/") in text   # resolved vault path
    assert "crm" in text and "tasks" in text              # picked-skill roster
    assert "drain" not in text                            # roster is the PICKS, not the shelf
    assert "personaliz" not in text.lower()               # no personalization claim (review F10)

def test_assemble_trims_mcp_when_no_discord(tmp_path):
    tree = tmp_path / "home"
    composer.copy_home(tree, ["crm"])
    composer.assemble_manifests(tree, set())              # crm needs no discord
    mcp = json.loads((tree / ".mcp.json").read_text(encoding="utf-8"))
    assert mcp.get("mcpServers", {}) == {}

def test_assemble_keeps_discord_when_needed(tmp_path):
    tree = tmp_path / "home"
    composer.copy_home(tree, ["drain"])
    composer.assemble_manifests(tree, {"discord", "linear", "scheduler"})
    mcp = json.loads((tree / ".mcp.json").read_text(encoding="utf-8"))
    assert "discord" in mcp["mcpServers"]

def test_assemble_writes_no_plugin_manifests(tmp_path):
    tree = tmp_path / "home"
    composer.copy_home(tree, ["crm"])
    composer.assemble_manifests(tree, set())
    assert not (tree / ".claude-plugin").exists()
    assert not (tree / "marketplace.json").exists()
