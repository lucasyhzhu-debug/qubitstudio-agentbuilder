import asyncio, json
from pathlib import Path
from studio import composer

def _run(agen):
    async def drain():
        return [ev async for ev in agen]
    return asyncio.run(drain())

def test_assemble_writes_plugin_and_marketplace(tmp_path):
    tree = tmp_path / "plug"
    composer.copy_plugin(tree, ["crm"])
    composer.assemble_manifests(tree, "Sam Rivera", ["crm"], set())
    pj = json.loads((tree / ".claude-plugin/plugin.json").read_text(encoding="utf-8"))
    assert pj["author"]["name"] == "Sam Rivera" and pj["name"] == "sam-rivera-cos"
    # marketplace.json must live at .claude-plugin/ — that's where `/plugin marketplace add <dir>`
    # resolves it; at the tree root the install step fails (finding #6).
    mk = json.loads((tree / ".claude-plugin/marketplace.json").read_text(encoding="utf-8"))
    assert mk["plugins"][0]["name"] == "sam-rivera-cos" and mk["plugins"][0]["source"] == "."
    assert not (tree / "marketplace.json").exists()

def test_mcp_trimmed_when_no_discord(tmp_path):
    tree = tmp_path / "plug"
    composer.copy_plugin(tree, ["crm"])
    composer.assemble_manifests(tree, "Sam", ["crm"], set())  # crm needs no discord
    mcp = json.loads((tree / ".mcp.json").read_text(encoding="utf-8"))
    assert mcp.get("mcpServers", {}) == {}

def test_compose_streams_done_with_installable_tree(tmp_path):
    evs = _run(composer.compose(["crm"], "Sam Rivera", tmp_path / "dist", tmp_path / "vault"))
    assert evs[-1]["type"] == "done"
    out = Path(evs[-1]["plugin_path"])
    assert (out / ".claude-plugin/plugin.json").exists() and (out / ".claude-plugin/marketplace.json").exists()
    assert not (out / "marketplace.json").exists()
    # the composed agent carries its identity, with placeholders filled (finding #8)
    identity = (out / "CLAUDE.md").read_text(encoding="utf-8")
    assert "Sam Rivera" in identity and "{{OWNER_NAME}}" not in identity
    assert "personality.md" in identity and "- `crm`" in identity
