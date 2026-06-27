"""Source-of-truth schemas. These are FACTS supplied by the user.

The LLM never writes any field in this module. Deterministic code copies
employer/title/date/metric values verbatim into the final output.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DateMark(BaseModel):
    """A typed date. `end=None` on a role means 'current' -- there is no
    separate `present` flag (one representation only)."""
    model_config = ConfigDict(frozen=True)
    year: int = Field(ge=1900, le=2100)
    month: Optional[int] = Field(default=None, ge=1, le=12)


class Metric(BaseModel):
    """A typed, verifiable metric attached to a single bullet.

    `display` is the ONLY string the LLM may reproduce in prose, and it must
    be reproduced exactly. `value`/`unit` exist for deterministic comparison.
    """
    model_config = ConfigDict(frozen=True)
    metric_id: str                       # globally unique across the whole source
    value: Decimal | int | float
    unit: Optional[str] = None
    context: str                         # what it measures
    display: str                         # canonical rendered form, e.g. "40% lower latency"


class Skill(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str
    name: str
    category: Optional[str] = None
    aliases: list[str] = Field(default_factory=list)


class SourceBullet(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str                              # globally unique across all bullets
    text: str                            # original wording; also the fallback text
    skill_ids: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    metrics: list[Metric] = Field(default_factory=list)
    strength: int = Field(default=5, ge=1, le=10)  # job-independent impact rating; human-reviewable


class Experience(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str
    employer: str
    title: str
    location: Optional[str] = None
    start: DateMark
    end: Optional[DateMark] = None       # None == current role
    bullets: list[SourceBullet]

    @model_validator(mode="after")
    def _require_bullets(self):
        if not self.bullets:
            raise ValueError(f"Experience {self.id} must have at least one bullet")
        return self


class Project(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str
    name: str
    url: Optional[str] = None
    start: Optional[DateMark] = None
    end: Optional[DateMark] = None
    bullets: list[SourceBullet]

    @model_validator(mode="after")
    def _require_bullets(self):
        if not self.bullets:
            raise ValueError(f"Project {self.id} must have at least one bullet")
        return self


class Education(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str
    institution: str
    degree: str
    field: Optional[str] = None
    location: Optional[str] = None
    start: Optional[DateMark] = None
    end: Optional[DateMark] = None
    details: list[str] = Field(default_factory=list)


class Certification(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str
    name: str
    issuer: Optional[str] = None
    date: Optional[DateMark] = None


class Contact(BaseModel):
    model_config = ConfigDict(frozen=True)
    full_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    links: list[str] = Field(default_factory=list)


class ResumeSource(BaseModel):
    """Validated once, then read-only for the whole pipeline."""
    model_config = ConfigDict(frozen=True)
    contact: Contact
    skills: list[Skill]
    experiences: list[Experience]
    projects: list[Project] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    certifications: list[Certification] = Field(default_factory=list)

    def all_bullets(self) -> list[SourceBullet]:
        out: list[SourceBullet] = []
        for e in self.experiences:
            out.extend(e.bullets)
        for p in self.projects:
            out.extend(p.bullets)
        return out
