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


def test_rejects_unknown_skill_ref(raw_source):
    raw = {k: v for k, v in raw_source.items() if k != "inferences"}
    raw["experiences"][0]["bullets"][0]["skill_ids"].append("ghost_skill")
    with pytest.raises(SourceValidationError):
        load_source(raw)


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
