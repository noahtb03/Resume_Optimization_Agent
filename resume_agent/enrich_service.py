"""Profile-time entry: enrich_profile(...).

Runs deterministic rules-based enrichment over a validated source and returns an
EnrichedResumeSource. The optional LLM enrichment pass is a documented stub
(llm/enrich_llm.py) and is intentionally NOT called here in the MVP.

Manually-authored inferences can be supplied in the source JSON under an
optional top-level "inferences" key and are passed through as pre-approved.
"""
from __future__ import annotations

from .core.enrichment import enrich_source
from .core.validate_source import load_source
from .models.inference import EnrichedResumeSource, InferenceRecord


def enrich_profile(
    raw_source: dict,
    auto_approve_threshold: float = 0.8,
) -> EnrichedResumeSource:
    extra_raw = raw_source.get("inferences", [])
    source = load_source({k: v for k, v in raw_source.items() if k != "inferences"})
    extra = [InferenceRecord.model_validate(i) for i in extra_raw] if extra_raw else None
    return enrich_source(source, auto_approve_threshold=auto_approve_threshold, extra=extra)
