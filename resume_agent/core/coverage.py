"""JD keyword coverage + hard-requirement warnings.

Coverage is computed over the text that will actually render (validated bullet
text or source fallback, skill names, summary). Hard requirements (e.g. a
required degree) are SURFACED as warnings -- never auto-filled or fabricated.
"""
from __future__ import annotations

import re

from ..models.jd import JDProfile
from ..models.llm_io import LLMTailorOutput
from ..models.output import CoverageReport
from ..models.selection import SelectionResult
from ..models.source import ResumeSource
from .validator import ValidationReport

_WORD = re.compile(r"[a-z0-9+#.]+")


def _terms(s: str) -> set[str]:
    return set(_WORD.findall(s.lower()))


def _rendered_text(
    output: LLMTailorOutput,
    report: ValidationReport,
    selection: SelectionResult,
    source: ResumeSource,
) -> str:
    src_by_id = {b.id: b for b in source.all_bullets()}
    parts: list[str] = []
    verdict_by_primary = {
        v.gen.source_bullet_ids[0]: v
        for v in report.bullets if v.ok and v.gen.source_bullet_ids
    }
    for item in selection.items:
        for sb in item.bullets:
            v = verdict_by_primary.get(sb.bullet_id)
            if v:
                parts.append(v.gen.text)
            elif sb.bullet_id in src_by_id:
                parts.append(src_by_id[sb.bullet_id].text)
    skills_by_id = {s.id: s for s in source.skills}
    for sid in selection.skills_section_ids:
        if sid in skills_by_id:
            parts.append(skills_by_id[sid].name)
    if output.summary and report.summary.ok:
        parts.append(output.summary.text)
    return " ".join(parts)


def compute_coverage(
    output: LLMTailorOutput,
    report: ValidationReport,
    selection: SelectionResult,
    source: ResumeSource,
    jd: JDProfile,
) -> CoverageReport:
    keywords: list[str] = []
    seen: set[str] = set()
    for k in (jd.required_skills + jd.ats_keywords):
        key = k.lower().strip()
        if key and key not in seen:
            seen.add(key)
            keywords.append(k)

    rendered = _terms(_rendered_text(output, report, selection, source))
    covered, missing = [], []
    for kw in keywords:
        if _terms(kw) & rendered:
            covered.append(kw)
        else:
            missing.append(kw)

    warnings: list[str] = []
    has_education = bool(source.education)
    for req in jd.hard_requirements:
        if req.kind == "degree" and not has_education:
            warnings.append(f"JD hard requirement not evidenced in source: {req.text}")
        elif req.kind == "certification" and not source.certifications:
            warnings.append(f"JD hard requirement not evidenced in source: {req.text}")

    return CoverageReport(
        jd_keywords_total=len(keywords),
        jd_keywords_covered=len(covered),
        covered=covered,
        missing=missing,
        warnings=warnings,
    )
