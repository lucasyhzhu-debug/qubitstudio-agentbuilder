import asyncio, json, shutil, subprocess
from pathlib import Path
import pytest
from studio import composer

def _run(agen):
    async def drain():
        return [ev async for ev in agen]
    return asyncio.run(drain())

_HAS_GIT = shutil.which("git") is not None
_needs_git = pytest.mark.skipif(not _HAS_GIT, reason="git not on PATH")


# --- the update-channel stamp + shipped infra skill (Part 3: own repo + pull updates) ---

def test_copy_home_always_ships_cos_update_even_when_unpicked(tmp_path):
    tree = tmp_path / "home"
    composer.copy_home(tree, ["crm"])                    # cos-update is NOT a pick
    assert (tree / ".claude/skills/cos-update/SKILL.md").exists()

def test_cos_update_skill_copied_verbatim(tmp_path):
    # It already speaks the home layout, so the reference-path rewrite must NOT touch it
    # (its generic `references/` mention must survive intact).
    tree = tmp_path / "home"
    composer.copy_home(tree, ["crm"])
    src = (composer._COS / "skills/cos-update/SKILL.md").read_text(encoding="utf-8")
    got = (tree / ".claude/skills/cos-update/SKILL.md").read_text(encoding="utf-8")
    assert got == src
    assert "skills/cos-update/references/" not in got    # the bare `references/` wasn't rewritten

def test_stamp_update_meta_records_version_and_upstream(tmp_path):
    composer.stamp_update_meta(tmp_path, version="0.9.0", repo="acme/qubitstudio-agentbuilder")
    meta = json.loads((tmp_path / ".cos-update.json").read_text(encoding="utf-8"))
    assert meta["substrate_version"] == "0.9.0"
    assert meta["upstream_repo"] == "acme/qubitstudio-agentbuilder"
    assert meta["upstream_branch"] == "main"
    assert meta["packages_path"] == "docs/upgrades"

def test_substrate_version_matches_the_anchor_file():
    # The stamped default version is the single-source-of-truth SUBSTRATE_VERSION file.
    anchor = (composer._COS / "SUBSTRATE_VERSION").read_text(encoding="utf-8").strip()
    assert composer._SUBSTRATE_VERSION == anchor == "0.9.0"

def test_write_home_gitignore_keeps_env_out(tmp_path):
    composer.write_home_gitignore(tmp_path)
    gi = (tmp_path / ".gitignore").read_text(encoding="utf-8")
    assert ".env" in gi and ".cache/" in gi


# --- compose stamps the home and makes it its own git repo ---

def test_compose_stamps_update_meta_and_advertises_in_claude_md(tmp_path):
    evs = _run(composer.compose(["crm"], "atlas", tmp_path / "dist", tmp_path / "vault"))
    home = Path(evs[-1]["plugin_path"])
    meta = json.loads((home / ".cos-update.json").read_text(encoding="utf-8"))
    assert meta["substrate_version"] == composer._SUBSTRATE_VERSION
    assert "qubitstudio-agentbuilder" in meta["upstream_repo"]
    cm = (home / "CLAUDE.md").read_text(encoding="utf-8")
    assert "update me" in cm and composer._SUBSTRATE_VERSION in cm

@_needs_git
def test_compose_makes_home_its_own_git_repo(tmp_path):
    evs = _run(composer.compose(["crm"], "atlas", tmp_path / "dist", tmp_path / "vault"))
    home = Path(evs[-1]["plugin_path"])
    assert (home / ".git").exists()
    log = subprocess.run(["git", "-C", str(home), "log", "--oneline"],
                         capture_output=True, text=True).stdout
    assert composer._SUBSTRATE_VERSION in log      # the initial compose commit records the version

@_needs_git
def test_rebuild_preserves_owner_git_history(tmp_path):
    # The home is the participant's OWN repo — their cos-update commits (and any of their own)
    # must survive a studio re-compose, exactly like the in-home vault memory does.
    home = tmp_path / "dist" / "atlas-cos"
    vault = home / "vault"
    _run(composer.compose(["crm"], "atlas", tmp_path / "dist", vault))
    (home / ".claude/skills/cos-update/NOTES.md").write_text("owner ran an update", encoding="utf-8")
    subprocess.run(["git", "-C", str(home), "add", "-A"], capture_output=True)
    subprocess.run(["git", "-C", str(home), "-c", "user.name=o", "-c", "user.email=o@o",
                    "commit", "-m", "cos-update: v0.9.0 -> v0.9.1"], capture_output=True)
    _run(composer.compose(["crm", "tasks"], "atlas", tmp_path / "dist", vault))   # rebuild + new pick
    log = subprocess.run(["git", "-C", str(home), "log", "--oneline"],
                         capture_output=True, text=True).stdout
    assert "cos-update: v0.9.0 -> v0.9.1" in log      # owner history survived the rebuild
    assert (home / ".claude/skills/tasks/SKILL.md").exists()   # the new pick landed
