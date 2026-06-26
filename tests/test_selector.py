from resume_agent.core.selector import select
from resume_agent.models.config import default_config
from resume_agent.models.jd import JDProfile


def _jd():
    return JDProfile(
        title="Data Scientist",
        required_skills=["python", "sql", "machine learning"],
        ats_keywords=["python", "sql", "tableau", "classification", "machine learning"],
        responsibilities=["build models", "dashboards"],
    )


def test_selection_builds_authorization_sets(enriched):
    sel = select(enriched, _jd(), default_config())
    # selected bullets came from the source
    all_ids = {b.id for b in enriched.source.all_bullets()}
    assert sel.selected_source_bullet_ids.issubset(all_ids)
    assert sel.selected_source_bullet_ids  # non-empty
    # metric ownership maps only selected bullets
    for bid in sel.metric_ownership:
        assert bid in sel.selected_source_bullet_ids


def test_skills_section_is_subset_of_source(enriched):
    sel = select(enriched, _jd(), default_config())
    source_skill_ids = {s.id for s in enriched.source.skills}
    assert set(sel.skills_section_ids).issubset(source_skill_ids)


def test_approved_inferences_enter_allowlist(enriched):
    sel = select(enriched, _jd(), default_config())
    # only approved + attached-to-selected inferences should appear
    for inf_id in sel.approved_inference_ids:
        assert inf_id in sel.inference_uses
