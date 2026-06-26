"""What LLM-2 returns. UNTRUSTED until the validator clears it.

The model emits ONLY text + provenance declarations. It never emits employer,
title, dates, or metric values. Metric numbers may appear in `text` only as an
exact `Metric.display` substring, and must be declared in `used_metric_ids`.
`used_skill_ids` / `used_inference_ids` are model-reported provenance metadata:
the validator checks they are AUTHORIZED, not that they actually appear in prose.
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


class LLMTailorOutput(BaseModel):
    summary: Optional[GenSummary] = None
    bullets: list[GenBullet] = Field(default_factory=list)
