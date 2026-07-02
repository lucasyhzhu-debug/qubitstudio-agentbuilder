import asyncio
from pathlib import Path
from studio import tweaker


def _run(agen):
    async def drain(): return [ev async for ev in agen]
    return asyncio.run(drain())


def test_structured_substitution_fills_placeholders(tmp_path):
    # Back-compat: nested layout — vault seeded UNDER the passed root, no vault_dir given.
    vault = tmp_path / "vault/meta/chief-of-staff"; vault.mkdir(parents=True)
    (vault / "personality.md").write_text("Voice: {{OWNER_VOICE}}", encoding="utf-8")
    evs = _run(tweaker.tweak(tmp_path, {"OWNER_VOICE": "warm, terse", "voice_sample": ""}))
    assert "{{OWNER_VOICE}}" not in (vault / "personality.md").read_text(encoding="utf-8")
    assert any(ev["type"] == "done" for ev in evs)


def test_sibling_vault_is_substituted_when_vault_dir_given(tmp_path):
    # Real compose layout: plugin tree and vault are SIBLING dirs, not nested — the vault
    # carries the seeded personality.md with {{OWNER_VOICE}}. Regression for the studio
    # live-QA bug: /api/tweak only walked `tree` and silently left the vault untouched.
    plug = tmp_path / "plug"; plug.mkdir()
    vault = tmp_path / "vault"
    personality_dir = vault / "meta/chief-of-staff"; personality_dir.mkdir(parents=True)
    (personality_dir / "personality.md").write_text("Voice: {{OWNER_VOICE}}", encoding="utf-8")
    evs = _run(tweaker.tweak(plug, {"OWNER_VOICE": "warm, terse", "voice_sample": ""}, vault_dir=vault))
    assert "{{OWNER_VOICE}}" not in (personality_dir / "personality.md").read_text(encoding="utf-8")
    assert not any(ev["type"] == "log" and "no {{OWNER_*}}" in ev["text"] for ev in evs)
    assert any(ev["type"] == "done" for ev in evs)


def test_missing_vault_dir_does_not_error(tmp_path):
    # vault_dir pointing at a path that doesn't exist should just be skipped, not crash —
    # server.py preflight-validates this before calling tweak(), but tweak() itself should
    # be defensive too.
    plug = tmp_path / "plug"; plug.mkdir()
    evs = _run(tweaker.tweak(plug, {"OWNER_VOICE": "warm"}, vault_dir=tmp_path / "nope"))
    assert any(ev["type"] == "done" for ev in evs)


def test_voice_sample_empty_skips_voice_pass(monkeypatch, tmp_path):
    # No claude spawn should happen when voice_sample is empty/whitespace-only — assert by
    # monkeypatching _run_voice_pass to blow up if it's ever called.
    async def _boom(*a, **k):
        raise AssertionError("voice pass must not run when voice_sample is empty")
    monkeypatch.setattr(tweaker, "_run_voice_pass", _boom)
    evs = _run(tweaker.tweak(tmp_path, {"OWNER_VOICE": "calm", "voice_sample": "   "}))
    assert not any(ev.get("name") == "voice" for ev in evs if ev["type"] == "stage")
    assert any(ev["type"] == "done" for ev in evs)


def test_voice_pass_failure_is_non_fatal(monkeypatch, tmp_path):
    async def _fail(*a, **k):
        raise RuntimeError("boom")
    monkeypatch.setattr(tweaker, "_run_voice_pass", _fail)
    evs = _run(tweaker.tweak(tmp_path, {"OWNER_VOICE": "calm", "voice_sample": "hello there"}))
    assert any(ev["type"] == "log" and "non-fatal" in ev["text"] for ev in evs)
    assert any(ev["type"] == "done" for ev in evs)  # non-fatal — still completes


def test_voice_sample_is_not_substituted_as_a_placeholder(tmp_path):
    f = tmp_path / "note.md"
    f.write_text("sample placeholder: {{voice_sample}}", encoding="utf-8")
    evs = _run(tweaker.tweak(tmp_path, {"voice_sample": "some sample text"}))
    # voice_sample is phase-2 input, never a {{KEY}} substitution value.
    assert "{{voice_sample}}" in f.read_text(encoding="utf-8")
    assert any(ev["type"] == "done" for ev in evs)


def test_build_voice_argv_is_variadic_not_joined():
    argv = tweaker.build_voice_argv("claude", [Path("/tmp/tree")], "warm", "sample text")
    assert argv[0] == "claude"
    # --allowed-tools must be followed by SEPARATE tokens "Read", "Edit" — never "Read Edit" joined.
    i = argv.index("--allowed-tools")
    assert argv[i + 1] == "Read"
    assert argv[i + 2] == "Edit"
    assert "Read Edit" not in argv
    j = argv.index("--add-dir")
    assert argv[j + 1] == str(Path("/tmp/tree"))


def test_build_voice_argv_adds_one_flag_per_dir():
    # Sibling plugin tree + vault: TWO separate --add-dir flags (one per root), not one
    # space-joined value — --add-dir accepts a single path per flag.
    dirs = [Path("/tmp/plug"), Path("/tmp/vault")]
    argv = tweaker.build_voice_argv("claude", dirs, "warm", "sample text")
    indices = [i for i, tok in enumerate(argv) if tok == "--add-dir"]
    assert len(indices) == 2
    assert argv[indices[0] + 1] == str(Path("/tmp/plug"))
    assert argv[indices[1] + 1] == str(Path("/tmp/vault"))
