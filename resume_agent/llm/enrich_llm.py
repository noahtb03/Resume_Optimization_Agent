"""EXTENSION POINT (not implemented in the MVP).

The optional LLM enrichment pass would propose additional Level 2 inference
labels per bullet, each with evidence and a self-classified claim_level. Per the
design, LLM-proposed inferences are NEVER auto-approved -- they must land as
`suggested` for human review. This stub defines the interface so a future
implementation drops in without touching generation-time code.

Wiring it later:
  1. Implement `propose_inferences_llm` to call the model per bullet.
  2. In enrich_service.enrich_profile, merge its output (status='suggested')
     with the deterministic rules-pass output.
  3. Generation-time code is UNCHANGED: it only ever consumes approved records.
"""
from __future__ import annotations

from ..models.inference import InferenceRecord
from ..models.source import ResumeSource
from .client import LLMClient


def propose_inferences_llm(source: ResumeSource, client: LLMClient) -> list[InferenceRecord]:
    raise NotImplementedError(
        "Optional LLM enrichment pass is a documented extension point; the MVP "
        "uses deterministic rules-based enrichment only (see core/enrichment.py)."
    )
