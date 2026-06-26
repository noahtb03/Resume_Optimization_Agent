"""Deterministic assembler: validated LLM output + source -> TailoredResume.

Fact fields (employer/title/dates, metric values, contact, education) are
copied VERBATIM from the source here -- the LLM never supplied them. Each
selected source bullet maps 1:1 to either a passing generated bullet or a
source-text fallback.
"""
from __future__ import annotations

from typing import Literal

from ..models.config import ResumeConfig
from ..models.llm_io import LLMTailorOutput
from ..models.output import (
    CoverageReport, ResumeMeta, SummaryBlock, TailoredBullet, TailoredExperience,
    TailoredProject, TailoredResume, ValidationStatus,
)
from ..models.selection import SelectionResult
from ..models.source import Experience, Project, ResumeSource
from .fallback import fallback_bullet
from .validator import ValidationReport


def assemble(
    output: LLMTailorOutput,
    report: ValidationReport,
    selection: SelectionResult,
    source: ResumeSource,
    config: ResumeConfig,
    coverage: CoverageReport,
    generated_at: str,
    llm_calls_used: int,
    passing_status: Literal["generated", "repaired"] = "generated",
) -> TailoredResume:
    src_bullets = {b.id: b for b in source.all_bullets()}
    exp_by_id = {e.id: e for e in source.experiences}
    proj_by_id = {p.id: p for p in source.projects}
    skills_by_id = {s.id: s for s in source.skills}

    verdict_by_primary = {
        v.gen.source_bullet_ids[0]: v
        for v in report.bullets if v.gen.source_bullet_ids
    }

    def tailor_bullets(item) -> list[TailoredBullet]:
        out: list[TailoredBullet] = []
        for sb in item.bullets:
            v = verdict_by_primary.get(sb.bullet_id)
            if v and v.ok:
                out.append(TailoredBullet(
                    text=v.gen.text,
                    source_bullet_ids=list(v.gen.source_bullet_ids),
                    used_skill_ids=list(v.gen.used_skill_ids),
                    used_inference_ids=list(v.gen.used_inference_ids),
                    used_metrics=list(v.resolved_metrics),
                    validation=ValidationStatus(status=passing_status),
                ))
            else:
                reason = "; ".join(v.violations) if v else "no generated bullet produced"
                out.append(fallback_bullet(src_bullets[sb.bullet_id], reason))
        return out

    experiences: list[TailoredExperience] = []
    projects: list[TailoredProject] = []
    for item in selection.items:
        if item.kind == "experience":
            e: Experience = exp_by_id[item.source_id]
            experiences.append(TailoredExperience(
                source_id=e.id, employer=e.employer, title=e.title,
                location=e.location, start=e.start, end=e.end,
                bullets=tailor_bullets(item),
            ))
        else:
            p: Project = proj_by_id[item.source_id]
            projects.append(TailoredProject(
                source_id=p.id, name=p.name, url=p.url,
                bullets=tailor_bullets(item),
            ))

    summary_block = None
    if output.summary and report.summary.ok:
        summary_block = SummaryBlock(
            text=output.summary.text,
            validation=ValidationStatus(status=passing_status),
        )

    skills = [skills_by_id[sid] for sid in selection.skills_section_ids if sid in skills_by_id]

    meta = ResumeMeta(
        generated_at=generated_at,
        jd_title=(selection.jd_profile.title or "Target Role"),
        coverage=coverage,
        llm_calls_used=llm_calls_used,
    )

    return TailoredResume(
        meta=meta,
        contact=source.contact,
        summary=summary_block,
        skills=skills,
        experiences=experiences,
        projects=projects,
        education=list(source.education),
        certifications=list(source.certifications),
        section_order=list(config.section_order),
    )
