"""LLM-1: JD text -> JDProfile. On parse/validation failure, one reformat retry,
then a deterministic keyword-only fallback so the pipeline never hard-fails on
JD interpretation (a non-fact stage)."""
from __future__ import annotations

import re

from ..models.jd import JDProfile
from .client import LLMClient
from ._json import extract_json
from .prompts.jd_analyze import JD_ANALYZE_SYSTEM, JD_ANALYZE_USER

_WORD = re.compile(r"[A-Za-z][A-Za-z0-9+#.\-]{2,}")
_STOP = {
    "and", "the", "for", "with", "you", "our", "are", "will", "that", "this",
    "have", "from", "their", "your", "all", "can", "into", "other", "such",
}


def analyze_jd(jd_text: str, client: LLMClient) -> tuple[JDProfile, int]:
    """Returns (profile, calls_used). calls_used is 1 or 2 (retry)."""
    user = JD_ANALYZE_USER.format(jd_text=jd_text)
    for attempt in range(2):
        raw = client.complete(system=JD_ANALYZE_SYSTEM, user=user, max_tokens=1200)
        try:
            return JDProfile.model_validate(extract_json(raw)), attempt + 1
        except Exception:
            continue
    return _keyword_fallback(jd_text), 2


def _keyword_fallback(jd_text: str) -> JDProfile:
    counts: dict[str, int] = {}
    for w in _WORD.findall(jd_text.lower()):
        if w in _STOP:
            continue
        counts[w] = counts.get(w, 0) + 1
    top = [w for w, _ in sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:25]]
    return JDProfile(
        title=None, seniority="unknown",
        required_skills=top[:12], ats_keywords=top, responsibilities=[],
        hard_requirements=[],
    )
