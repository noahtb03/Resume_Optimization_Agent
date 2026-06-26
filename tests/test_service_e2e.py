from resume_agent.service import generate_resume
from tests.conftest import ScriptedClient


def _tailor_for(enriched, **overrides):
    """Build a valid tailor JSON: one bullet per selected bullet. Overrides let a
    test inject a violation into the first bullet."""
    from resume_agent.core.selector import select
    from resume_agent.models.config import default_config
    from resume_agent.models.jd import JDProfile
    jd = JDProfile(required_skills=["python", "sql"], ats_keywords=["python", "sql"])
    sel = select(enriched, jd, default_config())
    bullets = []
    for item in sel.items:
        for b in item.bullets:
            bullets.append({
                "text": f"Reworked: {b.text[:60]}",
                "source_bullet_ids": [b.bullet_id],
                "used_skill_ids": [], "used_metric_ids": [], "used_inference_ids": [],
            })
    if overrides.get("bad_skill") and bullets:
        bullets[0]["used_skill_ids"] = ["kubernetes"]
    if overrides.get("forbidden") and bullets:
        bullets[0]["text"] = "Built scalable pipelines."
    return {"summary": None, "bullets": bullets}


def test_happy_path_two_calls(enriched, jd_text, jd_json):
    client = ScriptedClient(jd_json, [_tailor_for(enriched)])
    result = generate_resume(enriched, jd_text, client)
    assert result.meta.llm_calls_used == 2
    statuses = [b.validation.status for e in result.experiences for b in e.bullets]
    assert statuses and all(s == "generated" for s in statuses)


def test_contact_and_dates_copied_verbatim(enriched, jd_text, jd_json):
    client = ScriptedClient(jd_json, [_tailor_for(enriched)])
    result = generate_resume(enriched, jd_text, client)
    assert result.contact.full_name == "Jordan Rivera"
    amig = next(e for e in result.experiences if e.source_id == "exp_amig")
    assert amig.employer == "Amigo Analytics"
    assert amig.end is None  # current role preserved


def test_repair_path_three_calls(enriched, jd_text, jd_json):
    # first tailor has a bad skill -> repair -> clean
    bad = _tailor_for(enriched, bad_skill=True)
    good = _tailor_for(enriched)
    client = ScriptedClient(jd_json, [bad, good])
    result = generate_resume(enriched, jd_text, client)
    assert result.meta.llm_calls_used == 3
    statuses = [b.validation.status for e in result.experiences for b in e.bullets]
    assert all(s == "repaired" for s in statuses)


def test_fallback_when_repair_also_fails(enriched, jd_text, jd_json):
    bad1 = _tailor_for(enriched, forbidden=True)
    bad2 = _tailor_for(enriched, forbidden=True)
    client = ScriptedClient(jd_json, [bad1, bad2])
    result = generate_resume(enriched, jd_text, client)
    assert result.meta.llm_calls_used == 3
    # the offending first bullet falls back to source; others may be repaired-ok
    all_bullets = [b for e in result.experiences for b in e.bullets]
    assert any(b.validation.status == "fallback_source" for b in all_bullets)
    # fallback bullets carry original source text
    fb = next(b for b in all_bullets if b.validation.status == "fallback_source")
    assert not fb.text.startswith("Reworked:")


def test_unparseable_tailor_falls_back_entirely(enriched, jd_text, jd_json):
    class BrokenTailor(ScriptedClient):
        def complete(self, *, system, user, max_tokens=1500):
            self.calls += 1
            if "information extractor" in system.lower():
                import json
                return json.dumps(jd_json)
            return "this is not json at all"
    client = BrokenTailor(jd_json, [])
    result = generate_resume(enriched, jd_text, client)
    all_bullets = [b for e in result.experiences for b in e.bullets]
    assert all(b.validation.status == "fallback_source" for b in all_bullets)
