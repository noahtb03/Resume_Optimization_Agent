import pytest

from resume_agent.core.selector import select
from resume_agent.core.validator import validate
from resume_agent.models.config import default_config
from resume_agent.models.jd import JDProfile
from resume_agent.models.llm_io import GenBullet, GenSummary, LLMTailorOutput


def _jd():
    return JDProfile(
        title="Data Scientist",
        required_skills=["python", "sql", "machine learning"],
        ats_keywords=["python", "sql", "tableau", "classification"],
    )


@pytest.fixture
def ctx(enriched):
    cfg = default_config()
    sel = select(enriched, _jd(), cfg)
    return enriched.source, sel, cfg


def _metric_bullet(sel):
    """Return a (bullet_id, metric_id, display) for a selected bullet with a metric."""
    for bid, mids in sel.metric_ownership.items():
        if mids:
            mid = next(iter(mids))
            return bid, mid
    raise AssertionError("no selected bullet owns a metric")


def test_clean_bullet_passes(ctx):
    source, sel, cfg = ctx
    bid = next(iter(sel.selected_source_bullet_ids))
    out = LLMTailorOutput(bullets=[GenBullet(
        text="Built classification models in Python.",
        source_bullet_ids=[bid], used_skill_ids=[],
    )])
    rep = validate(out, sel, source, cfg)
    assert rep.ok


def test_unauthorized_source_bullet_fails(ctx):
    source, sel, cfg = ctx
    out = LLMTailorOutput(bullets=[GenBullet(text="x", source_bullet_ids=["ghost_99"])])
    rep = validate(out, sel, source, cfg)
    assert not rep.ok
    assert any("unauthorized source_bullet_ids" in v for v in rep.violation_lines())


def test_unauthorized_skill_fails(ctx):
    source, sel, cfg = ctx
    bid = next(iter(sel.selected_source_bullet_ids))
    out = LLMTailorOutput(bullets=[GenBullet(
        text="x", source_bullet_ids=[bid], used_skill_ids=["kubernetes"],
    )])
    rep = validate(out, sel, source, cfg)
    assert not rep.ok
    assert any("unauthorized used_skill_ids" in v for v in rep.violation_lines())


def test_metric_exact_display_passes(ctx):
    source, sel, cfg = ctx
    bid, mid = _metric_bullet(sel)
    disp = next(m.display for b in source.all_bullets() for m in b.metrics if m.metric_id == mid)
    out = LLMTailorOutput(bullets=[GenBullet(
        text=f"Improved reporting; {disp} overall.",
        source_bullet_ids=[bid], used_metric_ids=[mid],
    )])
    rep = validate(out, sel, source, cfg)
    assert rep.ok, rep.violation_lines()


def test_altered_metric_number_fails(ctx):
    source, sel, cfg = ctx
    bid, mid = _metric_bullet(sel)
    out = LLMTailorOutput(bullets=[GenBullet(
        text="Cut reporting time by 95% across teams.",
        source_bullet_ids=[bid], used_metric_ids=[mid],
    )])
    rep = validate(out, sel, source, cfg)
    assert not rep.ok
    assert any("number" in v or "display not found" in v for v in rep.violation_lines())


def test_unapproved_number_fails(ctx):
    source, sel, cfg = ctx
    bid = next(iter(sel.selected_source_bullet_ids))
    out = LLMTailorOutput(bullets=[GenBullet(
        text="Improved throughput by 250 requests per second.",
        source_bullet_ids=[bid],
    )])
    rep = validate(out, sel, source, cfg)
    assert not rep.ok
    assert any("unapproved number" in v for v in rep.violation_lines())


def test_metric_not_owned_fails(ctx):
    source, sel, cfg = ctx
    # cite a bullet that does NOT own lab_01_f1 but claim that metric
    bid_no_metric = None
    for bid in sel.selected_source_bullet_ids:
        if not sel.metric_ownership.get(bid):
            bid_no_metric = bid
            break
    assert bid_no_metric
    out = LLMTailorOutput(bullets=[GenBullet(
        text="Reached 0.91 macro F1.", source_bullet_ids=[bid_no_metric],
        used_metric_ids=["lab_01_f1"],
    )])
    rep = validate(out, sel, source, cfg)
    assert not rep.ok
    assert any("not owned" in v for v in rep.violation_lines())


def test_forbidden_modifier_fails(ctx):
    source, sel, cfg = ctx
    bid = next(iter(sel.selected_source_bullet_ids))
    out = LLMTailorOutput(bullets=[GenBullet(
        text="Built scalable Python systems.", source_bullet_ids=[bid],
    )])
    rep = validate(out, sel, source, cfg)
    assert not rep.ok
    assert any("forbidden modifiers" in v for v in rep.violation_lines())


def test_length_cap_fails(ctx):
    source, sel, cfg = ctx
    bid = next(iter(sel.selected_source_bullet_ids))
    out = LLMTailorOutput(bullets=[GenBullet(
        text="x" * 5000, source_bullet_ids=[bid],
    )])
    rep = validate(out, sel, source, cfg)
    assert not rep.ok
    assert any("length" in v for v in rep.violation_lines())


def test_summary_with_number_fails(ctx):
    source, sel, cfg = ctx
    out = LLMTailorOutput(
        bullets=[],
        summary=GenSummary(text="Analyst with 10 years of experience.", used_skill_ids=[]),
    )
    rep = validate(out, sel, source, cfg)
    assert not rep.summary.ok
    assert any("number" in v for v in rep.summary.violations)
