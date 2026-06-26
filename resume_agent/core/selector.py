"""Hybrid deterministic selector. Scores each source bullet against the
JDProfile using explicit skills, tags, approved L2 inferences, and keyword
overlap, then emits the SelectionResult authorization boundary.

No embeddings in the MVP. Alias resolution gives a little fuzz (py->python)
without external models.
"""
from __future__ import annotations

import re

from ..models.config import ResumeConfig
from ..models.inference import EnrichedResumeSource, InferenceRecord
from ..models.jd import JDProfile
from ..models.selection import SelectedBullet, SelectedItem, SelectionResult
from ..models.source import Experience, Project, Skill, SourceBullet

_WORD = re.compile(r"[a-z0-9+#.]+")


def _norm(s: str) -> set[str]:
    return set(_WORD.findall(s.lower()))


def _jd_terms(jd: JDProfile) -> set[str]:
    terms: set[str] = set()
    for group in (jd.required_skills, jd.preferred_skills, jd.ats_keywords, jd.responsibilities):
        for item in group:
            terms |= _norm(item)
    return terms


def _skill_terms(skill: Skill) -> set[str]:
    t = _norm(skill.name) | {skill.id.lower()}
    for a in skill.aliases:
        t |= _norm(a)
    return t


def _score_bullet(
    bullet: SourceBullet,
    skills_by_id: dict[str, Skill],
    infs_by_bullet: dict[str, list[InferenceRecord]],
    jd_terms: set[str],
    weights,
) -> float:
    score = 0.0
    # explicit skills
    for sid in bullet.skill_ids:
        sk = skills_by_id.get(sid)
        if sk and (_skill_terms(sk) & jd_terms):
            score += weights.skill
    # tags
    for tag in bullet.tags:
        if _norm(tag) & jd_terms:
            score += weights.tag
    # approved inferences attached to this bullet
    for inf in infs_by_bullet.get(bullet.id, []):
        if _norm(inf.label) & jd_terms:
            score += weights.inference
    # raw keyword overlap of the bullet text
    overlap = _norm(bullet.text) & jd_terms
    score += weights.keyword * len(overlap)
    # job-independent strength (impact) boost: rewards quantified, high-impact
    # bullets even when keyword overlap is low. strength is 1-10; normalize to 0-1.
    score += weights.strength * (bullet.strength / 10.0)
    return score


def select(
    enriched: EnrichedResumeSource,
    jd: JDProfile,
    config: ResumeConfig,
) -> SelectionResult:
    source = enriched.source
    weights = config.weights
    skills_by_id = {s.id: s for s in source.skills}
    jd_terms = _jd_terms(jd)

    approved = enriched.approved_inferences()
    infs_by_bullet: dict[str, list[InferenceRecord]] = {}
    for inf in approved:
        infs_by_bullet.setdefault(inf.source_bullet_id, []).append(inf)

    exp_spec = config.sections["experience"]
    proj_spec = config.sections.get("projects")

    items: list[SelectedItem] = []
    selected_bullet_ids: set[str] = set()
    approved_skill_ids: set[str] = set()
    approved_inf_ids: set[str] = set()
    inference_uses: dict[str, set] = {}
    metric_ownership: dict[str, set[str]] = {}

    def build_item(container: Experience | Project, kind: str, spec) -> SelectedItem | None:
        if spec is None or not spec.enabled:
            return None
        max_bullets = spec.max_bullets_per_item or len(container.bullets)
        max_chars = spec.max_chars_per_bullet or 240
        scored = sorted(
            container.bullets,
            key=lambda b: _score_bullet(b, skills_by_id, infs_by_bullet, jd_terms, weights),
            reverse=True,
        )
        chosen = [b for b in scored if _score_bullet(b, skills_by_id, infs_by_bullet, jd_terms, weights) > 0]
        chosen = (chosen or scored)[:max_bullets]  # never emit an empty item
        sel_bullets: list[SelectedBullet] = []
        for b in chosen:
            selected_bullet_ids.add(b.id)
            approved_skill_ids.update(b.skill_ids)
            metric_ownership[b.id] = {m.metric_id for m in b.metrics}
            bullet_inf_ids: list[str] = []
            for inf in infs_by_bullet.get(b.id, []):
                approved_inf_ids.add(inf.id)
                inference_uses[inf.id] = set(inf.allowed_uses)
                bullet_inf_ids.append(inf.id)
            sel_bullets.append(SelectedBullet(
                bullet_id=b.id, text=b.text, skill_ids=list(b.skill_ids),
                metric_ids=[m.metric_id for m in b.metrics],
                inference_ids=bullet_inf_ids,
            ))
        return SelectedItem(
            source_id=container.id, kind=kind, bullets=sel_bullets,
            max_bullets=max_bullets, max_chars_per_bullet=max_chars,
        )

    # rank experiences by best bullet score, take top max_items
    def item_score(container) -> float:
        return max(
            (_score_bullet(b, skills_by_id, infs_by_bullet, jd_terms, weights)
             for b in container.bullets),
            default=0.0,
        )

    exps = sorted(source.experiences, key=item_score, reverse=True)
    exps = exps[: (exp_spec.max_items or len(exps))]
    for e in exps:
        it = build_item(e, "experience", exp_spec)
        if it:
            items.append(it)

    if proj_spec and proj_spec.enabled and source.projects:
        projs = sorted(source.projects, key=item_score, reverse=True)
        projs = projs[: (proj_spec.max_items or len(projs))]
        for p in projs:
            it = build_item(p, "project", proj_spec)
            if it:
                items.append(it)

    # skills section: strict subset of source skills, ranked by JD relevance
    skills_spec = config.sections.get("skills")
    skills_section_ids: list[str] = []
    if skills_spec and skills_spec.enabled:
        ranked = sorted(
            source.skills,
            key=lambda s: len(_skill_terms(s) & jd_terms),
            reverse=True,
        )
        cap = skills_spec.max_skills or len(ranked)
        skills_section_ids = [s.id for s in ranked[:cap]]
        approved_skill_ids.update(skills_section_ids)

    return SelectionResult(
        items=items,
        approved_skill_ids=approved_skill_ids,
        approved_inference_ids=approved_inf_ids,
        inference_uses=inference_uses,
        selected_source_bullet_ids=selected_bullet_ids,
        metric_ownership=metric_ownership,
        skills_section_ids=skills_section_ids,
        jd_profile=jd,
    )
