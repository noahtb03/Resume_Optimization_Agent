import pytest

from resume_agent.core.validate_source import load_source, SourceValidationError


def test_loads_valid_source(source):
    assert source.contact.full_name == "Jordan Rivera"
    assert len(source.all_bullets()) == 4


def test_rejects_duplicate_bullet_id(raw_source):
    raw = {k: v for k, v in raw_source.items() if k != "inferences"}
    raw["experiences"][0]["bullets"][1]["id"] = "amig_01"  # dup
    with pytest.raises(SourceValidationError):
        load_source(raw)


def test_drops_unknown_skill_ref(raw_source):
    # a dangling skill ref (parser slip) is now silently dropped, not rejected --
    # a missing tag is harmless; a crash would block the whole resume.
    raw = {k: v for k, v in raw_source.items() if k != "inferences"}
    raw["experiences"][0]["bullets"][0]["skill_ids"].append("ghost_skill")
    source = load_source(raw)
    all_skill_refs = {sid for b in source.all_bullets() for sid in b.skill_ids}
    assert "ghost_skill" not in all_skill_refs


def test_rejects_duplicate_metric_id(raw_source):
    raw = {k: v for k, v in raw_source.items() if k != "inferences"}
    raw["experiences"][1]["bullets"][0]["metrics"][0]["metric_id"] = "amig_02_time"
    with pytest.raises(SourceValidationError):
        load_source(raw)


def test_experience_requires_a_bullet(raw_source):
    raw = {k: v for k, v in raw_source.items() if k != "inferences"}
    raw["experiences"][0]["bullets"] = []
    with pytest.raises(SourceValidationError):
        load_source(raw)