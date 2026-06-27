"""Job-description processing format. This is INTERPRETATION, not user fact,
so it never feeds the hallucination surface -- it only drives deterministic
selection and keyword coverage. `title` is optional; metadata falls back to
'Target Role' when absent."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

Seniority = Literal["intern", "entry", "mid", "senior", "lead", "unknown"]
RequirementKind = Literal["degree", "experience_years", "certification", "other"]


class JDRequirement(BaseModel):
    text: str
    kind: RequirementKind


class JDProfile(BaseModel):
    title: Optional[str] = None
    seniority: Seniority = "unknown"
    domain: Optional[str] = None
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    ats_keywords: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    hard_requirements: list[JDRequirement] = Field(default_factory=list)
