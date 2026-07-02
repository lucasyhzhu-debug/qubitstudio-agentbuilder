import asyncio, json
from pathlib import Path
from studio import composer

def test_resolve_rejects_unknown_pick():
    try:
        composer.resolve(["crm", "not-a-skill"])
        assert False
    except composer.UnknownPickError as e:
        assert "not-a-skill" in str(e)

def test_resolve_unions_integrations_and_warns_on_soft_gaps():
    r = composer.resolve(["drain"])            # drain needs_skills intake/tasks/crm/scheduling
    assert "discord" in r.integrations and "linear" in r.integrations
    assert any("intake" in w for w in r.warnings)  # soft gap → warning, not error

def test_scaffold_vault_writes_templated_identity(tmp_path):
    composer.scaffold_vault(tmp_path / "vault", "Sam Rivera", ["crm"])
    p = (tmp_path / "vault/meta/chief-of-staff/personality.md").read_text(encoding="utf-8")
    assert "Sam Rivera" in p and "{{OWNER_NAME}}" not in p
    assert (tmp_path / "vault/people").is_dir()
    assert not (tmp_path / "vault/meta/chief-of-staff/drain-state.json").exists()  # drain not picked
