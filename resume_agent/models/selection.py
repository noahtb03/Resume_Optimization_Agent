"""SelectionResult is the AUTHORIZATION BOUNDARY.

Whatever the selector puts here is the exact universe LLM-2 may use AND the
exact universe the validator checks against. The two are guaranteed identical
because they read the same object.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from .inference import AllowedUse
from .jd import JDProfile


class SelectedBullet(BaseModel):
    bullet_id: str
    text: str                                  # original wording; also fallback text
    skill_ids: list[str] = Field(default_factory=list)
    metric_ids: list[str] = Field(default_factory=list)
    inference_ids: list[str] = Field(default_factory=list)  # approved L2 attached here


class SelectedItem(BaseModel):
    source_id: str
    kind: Literal["experience", "project"]
    bullets: list[SelectedBullet]
    max_bullets: int
    max_chars_per_bullet: int


class SelectionResult(BaseModel):
    items: list[SelectedItem]
    approved_skill_ids: set[str] = Field(default_factory=set)
    approved_inference_ids: set[str] = Field(default_factory=set)
    inference_uses: dict[str, set[AllowedUse]] = Field(default_factory=dict)
    selected_source_bullet_ids: set[str] = Field(default_factory=set)
    metric_ownership: dict[str, set[str]] = Field(default_factory=dict)
    skills_section_ids: list[str] = Field(default_factory=list)  # ordered subset of source skills
    jd_profile: JDProfile
