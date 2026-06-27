"""Deterministic rules-based enrichment (profile time, NOT generation time).

Proposes high-confidence Level 2 InferenceRecords from explicit signals and
auto-approves those above a confidence threshold. The optional LLM enrichment
pass is intentionally left as a stub in llm/enrich_llm.py -- see that file.

Every rule here is traceable to an EXPLICIT skill or keyword on the bullet, so
auto-approval is safe. Anything implying scope/ownership/scale/outcome must be
emitted as `blocked_escalation` (which can never be approved) -- but the MVP
rules simply never propose those.
"""
from __future__ import annotations

from ..models.inference import EnrichedResumeSource, InferenceRecord
from ..models.source import ResumeSource, SourceBullet

# (trigger skill_ids OR keywords) -> proposed defensible-inference labels.
# Each entry: (label, kind, allowed_uses, confidence)
_RULES: list[dict] = [
    {
        "any_skill": {"pytorch", "tensorflow", "bert", "scikit-learn", "sklearn"},
        "any_kw": {"model", "classification", "fine-tune", "fine-tuned", "training"},
        "proposals": [
            ("Applied AI", "domain", ["skills_section", "summary", "bullet_reframing"], 0.85),
            ("Machine learning", "skill", ["skills_section", "summary", "bullet_reframing"], 0.8),
        ],
    },
    {
        "any_skill": {"pandas", "spark", "airflow"},
        "any_kw": {"pipeline", "preprocessing", "etl", "ingest", "clean"},
        "proposals": [
            ("Data pipeline", "competency", ["skills_section", "summary", "bullet_reframing"], 0.8),
            ("Data preprocessing", "technique", ["skills_section", "bullet_reframing"], 0.8),
        ],
    },
    {
        "any_skill": set(),
        "any_kw": {"customer service", "stakeholder", "cross-functional",
                   "worked with", "collaborated", "partnered"},
        "proposals": [
            ("Cross-functional collaboration", "collaboration",
             ["skills_section", "summary", "bullet_reframing"], 0.75),
        ],
    },
]


def _bullet_matches(bullet: SourceBullet, rule: dict) -> bool:
    skills = set(bullet.skill_ids)
    text = bullet.text.lower()
    tags = {t.lower() for t in bullet.tags}
    skill_hit = bool(rule["any_skill"] & skills) if rule["any_skill"] else False
    kw_hit = any(kw in text or kw in tags for kw in rule["any_kw"]) if rule["any_kw"] else False
    if rule["any_skill"] and rule["any_kw"]:
        return skill_hit and kw_hit
    return skill_hit or kw_hit


def propose_inferences(source: ResumeSource) -> list[InferenceRecord]:
    """Pure: returns suggested InferenceRecords (approval_status='suggested')."""
    out: list[InferenceRecord] = []
    seen: set[tuple[str, str]] = set()  # (bullet_id, label) de-dupe
    for bullet in source.all_bullets():
        for rule in _RULES:
            if not _bullet_matches(bullet, rule):
                continue
            for label, kind, uses, conf in rule["proposals"]:
                key = (bullet.id, label)
                if key in seen:
                    continue
                seen.add(key)
                slug = label.lower().replace(" ", "_")
                out.append(InferenceRecord(
                    id=f"inf_{bullet.id}_{slug}",
                    source_bullet_id=bullet.id,
                    label=label,
                    kind=kind,
                    claim_level="defensible_inference",
                    confidence=conf,
                    evidence=f"bullet {bullet.id}: {bullet.text[:80]}",
                    approval_status="suggested",
                    allowed_uses=uses,
                    inferred_by="rules",
                ))
    return out


def enrich_source(
    source: ResumeSource,
    auto_approve_threshold: float = 0.8,
    extra: list[InferenceRecord] | None = None,
) -> EnrichedResumeSource:
    """Build an EnrichedResumeSource. Rules-pass records >= threshold are
    auto-approved; the rest stay 'suggested'. `extra` lets callers inject
    manually-authored / pre-approved inferences from their JSON.
    """
    proposed = propose_inferences(source)
    approved: list[InferenceRecord] = []
    for inf in proposed:
        if inf.confidence >= auto_approve_threshold:
            approved.append(inf.model_copy(update={"approval_status": "approved"}))
        else:
            approved.append(inf)
    if extra:
        approved.extend(extra)
    return EnrichedResumeSource(source=source, inferences=approved)
