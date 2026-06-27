"""Final output schema, deterministically assembled. Fact fields here are
copied verbatim from ResumeSource -- the assembler, not the LLM, fills them."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

from .config import SectionType
from .source import (
    Certification, Contact, DateMark, Education, Metric, Skill,
)

ValidationOutcome = Literal["generated", "repaired", "fallback_source"]


class ValidationStatus(BaseModel):
    status: ValidationOutcome
    notes: list[str] = Field(default_factory=list)


class TailoredBullet(BaseModel):
    text: str
    source_bullet_ids: list[str] = Field(default_factory=list)
    used_skill_ids: list[str] = Field(default_factory=list)
    used_inference_ids: list[str] = Field(default_factory=list)
    used_metrics: list[Metric] = Field(default_factory=list)  # resolved verbatim from source
    validation: ValidationStatus


class TailoredExperience(BaseModel):
    source_id: str
    employer: str
    title: str
    location: Optional[str] = None
    start: DateMark
    end: Optional[DateMark] = None
    bullets: list[TailoredBullet]


class TailoredProject(BaseModel):
    source_id: str
    name: str
    url: Optional[str] = None
    bullets: list[TailoredBullet]


class SummaryBlock(BaseModel):
    text: str
    validation: ValidationStatus


class CoverageReport(BaseModel):
    jd_keywords_total: int
    jd_keywords_covered: int
    covered: list[str] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ResumeMeta(BaseModel):
    generated_at: str
    jd_title: str
    coverage: CoverageReport
    llm_calls_used: int

class SkillGroupOut(BaseModel):
    label: str
    skills: list[Skill] = Field(default_factory=list)


class TailoredResume(BaseModel):
    meta: ResumeMeta
    contact: Contact
    summary: Optional[SummaryBlock] = None
    skills: list[Skill] = Field(default_factory=list)
    skill_groups: list[SkillGroupOut] = Field(default_factory=list)  # job-adaptive grouping
    experiences: list[TailoredExperience] = Field(default_factory=list)
    projects: list[TailoredProject] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    certifications: list[Certification] = Field(default_factory=list)
    section_order: list[SectionType] = Field(default_factory=list)