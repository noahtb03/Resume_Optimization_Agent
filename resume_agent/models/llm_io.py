"""LLM I/O schemas (what we send to / parse from the tailoring model).

`used_skill_ids` / `used_inference_ids` are model-reported provenance metadata:
the model declares what it drew on, and the validator checks those claims
against the authorization boundary. They are NOT trusted blindly.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class GenBullet(BaseModel):
    text: str
    source_bullet_ids: list[str] = Field(default_factory=list)
    used_skill_ids: list[str] = Field(default_factory=list)
    used_metric_ids: list[str] = Field(default_factory=list)
    used_inference_ids: list[str] = Field(default_factory=list)


class GenSummary(BaseModel):
    text: str
    used_skill_ids: list[str] = Field(default_factory=list)
    referenced_experience_ids: list[str] = Field(default_factory=list)
    used_inference_ids: list[str] = Field(default_factory=list)


class SkillGroup(BaseModel):
    label: str                 # job-relevant heading, e.g. "Full Stack", "Languages"
    skill_ids: list[str] = Field(default_factory=list)


class LLMTailorOutput(BaseModel):
    summary: Optional[GenSummary] = None
    bullets: list[GenBullet] = Field(default_factory=list)
    skill_groups: list[SkillGroup] = Field(default_factory=list)  # optional job-adaptive grouping