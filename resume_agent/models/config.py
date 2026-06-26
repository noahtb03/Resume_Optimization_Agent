"""Section taxonomy + run config. Pure config: decides which sections exist,
their order, and the length proxies. NO one-page guarantee (that needs a
renderer). Also holds scorer weights and the repair budget."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

SectionType = Literal[
    "summary", "skills", "experience", "projects", "education", "certifications",
]


class ScorerWeights(BaseModel):
    skill: float = 3.0
    tag: float = 1.5
    inference: float = 2.0
    keyword: float = 0.7
    title: float = 1.0
    strength: float = 6.0   # job-independent impact; raised so quantified bullets compete with keyword density


class SectionSpec(BaseModel):
    type: SectionType
    enabled: bool = True
    heading: str
    max_items: Optional[int] = None
    max_bullets_per_item: Optional[int] = None
    max_chars_per_bullet: Optional[int] = None
    max_skills: Optional[int] = None
    max_summary_chars: Optional[int] = None


class ResumeConfig(BaseModel):
    section_order: list[SectionType] = Field(
        default_factory=lambda: [
            "skills", "experience", "projects", "education", "certifications",
        ]
    )
    sections: dict[SectionType, SectionSpec] = Field(default_factory=dict)
    weights: ScorerWeights = Field(default_factory=ScorerWeights)
    repair_budget: int = 1
    forbidden_modifiers: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _spec_for_every_section(self):
        missing = [s for s in self.section_order if s not in self.sections]
        if missing:
            raise ValueError(f"No SectionSpec for sections in order: {missing}")
        return self


def default_config() -> ResumeConfig:
    """A sensible MVP config so callers don't have to hand-build specs."""
    specs = {
        "summary": SectionSpec(type="summary", heading="Summary", max_summary_chars=320),
        "skills": SectionSpec(type="skills", heading="Skills", max_skills=18),
        "experience": SectionSpec(
            type="experience", heading="Experience",
            max_items=4, max_bullets_per_item=5, max_chars_per_bullet=320,
        ),
        "projects": SectionSpec(
            type="projects", heading="Projects",
            max_items=3, max_bullets_per_item=3, max_chars_per_bullet=320,
        ),
        "education": SectionSpec(type="education", heading="Education", max_items=3),
        "certifications": SectionSpec(
            type="certifications", heading="Certifications", max_items=6
        ),
    }
    return ResumeConfig(
        sections=specs,
        forbidden_modifiers=[
            "scalable", "robust", "world-class", "cutting-edge", "synergy",
        ],
    )
