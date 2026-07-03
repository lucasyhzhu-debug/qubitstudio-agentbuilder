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


# --- D0 compose stream (dossier spec §7.0 / lean §5) ---

def test_compose_emits_shell_event_and_cd_install(tmp_path):
    evs = _run(composer.compose(["crm"], "Sam Rivera", tmp_path / "dist", tmp_path / "vault"))
    keys = [e.get("key") for e in evs if e.get("type") == "component"]
    assert keys[0] == "vault" and "shell" in keys and "skill:crm" in keys
    done = evs[-1]
    assert done["type"] == "done"
    assert done["install"] == f"cd {done['plugin_path']} ; claude"
    assert "&&" not in done["install"]      # gate-2 S4: `&&` is a PS 5.1 parse error
    assert "/plugin" not in done["install"]
    out = Path(done["plugin_path"])
    assert (out / ".claude/skills/crm/SKILL.md").exists()
    assert (out / "CLAUDE.md").exists()
    assert not (out / ".claude-plugin").exists() and not (out / "marketplace.json").exists()

def test_compose_in_home_vault_survives_package(tmp_path):
    # The <home>/vault/ default (spec §7.0): scaffolded into staging, rides the move —
    # NOT destroyed by the package step's rmtree of a pre-existing final tree.
    home_vault = tmp_path / "dist" / "sam-rivera-cos" / "vault"
    (tmp_path / "dist" / "sam-rivera-cos").mkdir(parents=True)   # simulate a rebuild over an old home
    evs = _run(composer.compose(["crm"], "Sam Rivera", tmp_path / "dist", home_vault))
    done = evs[-1]
    assert done["type"] == "done"
    assert done["vault_path"] == str(home_vault)
    assert (home_vault / "meta/chief-of-staff/personality.md").exists()
    text = (home_vault / "meta/chief-of-staff/personality.md").read_text(encoding="utf-8")
    assert "Sam Rivera" in text

def test_compose_rebuild_preserves_in_home_vault(tmp_path):
    # gate-2 I4: the agent's MEMORY survives its own rebuild — vault content written
    # AFTER a build (memories, lessons) is still there after building again; only the
    # home's .env is lost (the documented consequence).
    home = tmp_path / "dist" / "sam-rivera-cos"
    home_vault = home / "vault"
    _run(composer.compose(["crm"], "Sam Rivera", tmp_path / "dist", home_vault))
    memory = home_vault / "meta" / "chief-of-staff" / "memories.md"
    memory.write_text("Sam prefers Tuesday briefings.", encoding="utf-8")
    (home / ".env").write_text("X=1\n", encoding="utf-8")
    evs = _run(composer.compose(["crm"], "Sam Rivera", tmp_path / "dist", home_vault))
    assert evs[-1]["type"] == "done"
    assert memory.read_text(encoding="utf-8") == "Sam prefers Tuesday briefings."
    assert not (home / ".env").exists()     # .env is the ONLY rebuild loss

def test_compose_external_vault_unchanged(tmp_path):
    # The onboarding second brain stays an in-place scaffold outside the home.
    sb = tmp_path / "second-brain"
    evs = _run(composer.compose(["crm"], "Sam Rivera", tmp_path / "dist", sb))
    assert evs[-1]["type"] == "done"
    assert (sb / "meta/chief-of-staff/personality.md").exists()
    assert not (Path(evs[-1]["plugin_path"]) / "vault").exists()

def test_compose_rebuild_fails_closed_when_home_cannot_be_cleared(tmp_path, monkeypatch):
    # Final review: a Windows lock (participant has `claude` running inside the home)
    # makes rmtree(final) a silent no-op — the move must NOT nest the new home at
    # final/<slug>-cos and report success. It fails closed with a clear message, and
    # the kept in-home vault rides back so memories aren't stranded in .cache.
    home = tmp_path / "dist" / "sam-rivera-cos"
    home_vault = home / "vault"
    _run(composer.compose(["crm"], "Sam Rivera", tmp_path / "dist", home_vault))
    memory = home_vault / "meta" / "chief-of-staff" / "memories.md"
    memory.write_text("Sam prefers Tuesday briefings.", encoding="utf-8")

    real_rmtree = composer.shutil.rmtree
    def locked_rmtree(path, *a, **kw):
        if Path(path) == home:          # the locked old home survives its rmtree
            return None
        return real_rmtree(path, *a, **kw)
    monkeypatch.setattr(composer.shutil, "rmtree", locked_rmtree)

    evs = _run(composer.compose(["crm"], "Sam Rivera", tmp_path / "dist", home_vault))
    err = evs[-1]
    assert err["type"] == "error" and err["stage"] == "package"
    assert "close any terminal" in err["message"]
    assert not (home / "sam-rivera-cos").exists()          # no silent nesting
    # restore leg: the participant's memories are back in the home, not in .cache
    assert memory.read_text(encoding="utf-8") == "Sam prefers Tuesday briefings."


def test_compose_claude_md_owner_from_onboarding(tmp_path, monkeypatch):
    # gate-2 I3: the participant's onboarding name is the CLAUDE.md owner; the agent
    # name still drives the slug. (Monkeypatched — composer tests never read the real
    # studio/.cache/onboarding.json.)
    monkeypatch.setattr(composer, "_onboarding_owner", lambda: "Sam Rivera")
    evs = _run(composer.compose(["crm"], "atlas", tmp_path / "dist", tmp_path / "vault"))
    done = evs[-1]
    assert done["type"] == "done" and done["plugin_path"].endswith("atlas-cos")
    text = (Path(done["plugin_path"]) / "CLAUDE.md").read_text(encoding="utf-8")
    assert "atlas-cos" in text and "Sam Rivera" in text

def test_compose_claude_md_owner_falls_back_to_agent_name(tmp_path, monkeypatch):
    monkeypatch.setattr(composer, "_onboarding_owner", lambda: None)
    evs = _run(composer.compose(["crm"], "atlas", tmp_path / "dist", tmp_path / "vault"))
    text = (Path(evs[-1]["plugin_path"]) / "CLAUDE.md").read_text(encoding="utf-8")
    assert "## Owner\n\n- atlas" in text
