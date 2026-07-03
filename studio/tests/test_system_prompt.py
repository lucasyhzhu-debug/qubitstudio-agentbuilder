from pathlib import Path
from studio.system_prompt import build_system_prompt

def test_includes_quiz_and_schema():
    p = build_system_prompt()
    assert "Q0" in p                       # the quiz is present
    assert "architecture spec" in p.lower()  # the schema is present

def test_includes_studio_contract():
    p = build_system_prompt()
    assert "```spec" in p                   # emit-the-block instruction
    assert "runtime" in p                   # the extension schema
    assert "superpowers" in p.lower()       # the ignore-skill-injection override

def test_excludes_generation_pipeline():
    p = build_system_prompt()
    # M2-M4 machinery must NOT leak into a pure-chat prompt
    assert "render_setup" not in p
    assert "package_plugin" not in p
    assert "plugin-generator" not in p

def test_writes_file(tmp_path: Path):
    from studio.system_prompt import write_system_prompt
    out = write_system_prompt(tmp_path / "sp.md")
    assert out.exists() and out.read_text(encoding="utf-8").strip() != ""

def test_slicer_kept_q0_dropped_render_setup():
    """Extra: proves the slicer actually cut both files — Q0 present, render_setup absent.
    Both source files contain render_setup; if either is included un-sliced the test fails.
    """
    p = build_system_prompt()
    assert "Q0" in p              # quiz content survived the Q10-section excision
    assert "render_setup" not in p  # sliced out of both architecture-spec.md (§11) and quiz-bank.md (Q10 section)


# --- workshop mode (QubitStudio journey spec §4.2) ---
from studio.system_prompt import build_workshop_prompt

def test_workshop_includes_catalog_and_contract():
    p = build_workshop_prompt()
    for skill_id in ("crm", "briefing", "scheduling", "tasks", "intake", "drain"):
        assert skill_id in p                  # every shelf id injected
    assert "wiki-brain" in p                  # baseline injected
    assert "```studio" in p                   # emit-the-block instruction
    assert "superpowers" in p.lower()         # ignore-skill-injection guard kept

def test_workshop_excludes_architect_machinery():
    p = build_workshop_prompt()
    assert "Q0" not in p                      # no quiz
    assert "```spec" not in p                 # no spec contract
    assert "render_setup" not in p

def test_write_system_prompt_workshop_mode(tmp_path):
    from studio.system_prompt import write_system_prompt
    out = write_system_prompt(tmp_path / "wp.md", mode="workshop")
    text = out.read_text(encoding="utf-8")
    assert "```studio" in text and "crm" in text

def test_write_system_prompt_default_is_architect_unchanged(tmp_path):
    from studio.system_prompt import write_system_prompt, build_system_prompt
    out = write_system_prompt(tmp_path / "sp.md")
    assert out.read_text(encoding="utf-8") == build_system_prompt()


# --- onboarding-cards spec §4.3 + §5.5 ---
_P = {"name": "Ada", "second_brain": "C:/tmp/sb",
      "profile_text": "# Ada\n\nAnalyst at Babbage & Co.", "materials_index": "cv.pdf"}

def test_workshop_ask_contract_always_present():
    for kw in ({}, {"onboarding": True}, {"participant": _P}):
        p = build_workshop_prompt(**kw)
        assert '"ask"' in p and "[card]" in p

def test_participant_section_injected():
    p = build_workshop_prompt(participant=_P)
    assert "The participant" in p and "Ada" in p and "Babbage" in p and "C:/tmp/sb" in p

def test_participant_profile_capped():
    # "HEADMARK" is 8 chars, so a head-cap [:6000] keeps HEADMARK + 5992 x's and
    # drops TAILMARK; a tail-cap regression ([-6000:]) would do the opposite.
    big = dict(_P, profile_text="HEADMARK" + "x" * 20000 + "TAILMARK")
    p = build_workshop_prompt(participant=big)
    assert "HEADMARK" in p and "TAILMARK" not in p
    assert "x" * 5992 in p and "x" * 5993 not in p

def test_onboarding_contract_only_when_flagged():
    assert "onboarding walk" in build_workshop_prompt(onboarding=True)
    assert "onboarding walk" not in build_workshop_prompt()

def test_write_system_prompt_threads_kwargs(tmp_path):
    from studio.system_prompt import write_system_prompt
    out = write_system_prompt(tmp_path / "wp.md", mode="workshop", participant=_P, onboarding=False)
    assert "Ada" in out.read_text(encoding="utf-8")

def test_architect_mode_still_byte_identical(tmp_path):
    from studio.system_prompt import write_system_prompt, build_system_prompt
    out = write_system_prompt(tmp_path / "sp.md")
    assert out.read_text(encoding="utf-8") == build_system_prompt()


# --- dossier spec §3.3: the chapter contract ---
_PHASE_SET = ("welcome", "baseline", "skills", "personalize", "name", "build", "connect")

def test_workshop_chapter_contract_present():
    p = build_workshop_prompt()
    assert '"chapter"' in p
    for phase in _PHASE_SET:
        assert phase in p
    assert "REUSE the current title" in p
    assert "Do NOT restate the chapter title" in p

def test_chapter_contract_in_every_workshop_variant():
    for kw in ({}, {"onboarding": True}, {"participant": _P}):
        assert '"chapter"' in build_workshop_prompt(**kw)

def test_architect_has_no_chapter_contract():
    from studio.system_prompt import build_system_prompt
    assert '"chapter"' not in build_system_prompt()

def test_architect_mode_byte_identical_after_chapter(tmp_path):
    from studio.system_prompt import write_system_prompt, build_system_prompt
    out = write_system_prompt(tmp_path / "sp.md")
    assert out.read_text(encoding="utf-8") == build_system_prompt()


# --- dossier spec §5: the revision verbs ---

def test_workshop_revision_contract_present():
    p = build_workshop_prompt()
    assert "[studio event] rewrite" in p
    assert "[studio event] regenerate" in p
    assert "do not advance the interview" in p.lower()
    assert "drop picks that no longer fit" in p

def test_architect_has_no_revision_contract(tmp_path):
    from studio.system_prompt import build_system_prompt, write_system_prompt
    assert "[studio event] rewrite" not in build_system_prompt()
    out = write_system_prompt(tmp_path / "sp.md")
    assert out.read_text(encoding="utf-8") == build_system_prompt()
