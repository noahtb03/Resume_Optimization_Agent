"""Level 2 defensible-inference schemas.

Inferences are created at PROFILE time (not per generation), classified into
explicit / defensible_inference / blocked_escalation, and gated by approval.
Only `approved` `defensible_inference` records are usable at generation time.
`blocked_escalation` records may be stored for audit but can never be approved.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .source import ResumeSource

ClaimLevel = Literal["explicit", "defensible_inference", "blocked_escalation"]
InferenceKind = Literal["skill", "competency", "domain", "collaboration", "technique"]
AllowedUse = Literal["selector_only", "skills_section", "summary", "bullet_reframing"]
ApprovalStatus = Literal["suggested", "approved", "rejected"]


class InferenceRecord(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str
    source_bullet_id: str
    label: str
    kind: InferenceKind
    claim_level: ClaimLevel
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: str
    approval_status: ApprovalStatus = "suggested"
    allowed_uses: list[AllowedUse] = Field(default_factory=list)
    inferred_by: Literal["rules", "llm"]


class EnrichedResumeSource(BaseModel):
    model_config = ConfigDict(frozen=True)
    source: ResumeSource
    inferences: list[InferenceRecord] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_inferences(self):
        bullet_ids = {b.id for b in self.source.all_bullets()}
        seen: set[str] = set()
        for inf in self.inferences:
            if inf.source_bullet_id not in bullet_ids:
                raise ValueError(f"{inf.id}: unknown source_bullet_id {inf.source_bullet_id}")
            if inf.id in seen:
                raise ValueError(f"duplicate inference id {inf.id}")
            seen.add(inf.id)
            if inf.claim_level == "blocked_escalation" and inf.approval_status == "approved":
                raise ValueError(f"{inf.id}: blocked_escalation can never be approved")
        return self

    def approved_inferences(self) -> list[InferenceRecord]:
        return [
            i for i in self.inferences
            if i.approval_status == "approved" and i.claim_level == "defensible_inference"
        ]
