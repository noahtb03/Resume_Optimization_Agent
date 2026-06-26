"""Load + validate raw source data into an immutable ResumeSource and enforce
cross-record invariants BEFORE any token is spent."""
from __future__ import annotations

from ..models.source import ResumeSource


class SourceValidationError(ValueError):
    pass


def load_source(raw: dict) -> ResumeSource:
    """Parse raw dict -> ResumeSource, then enforce global invariants:
      1. skill ids unique; bullet ids globally unique; metric ids globally unique
      2. every bullet.skill_ids resolves to a known skill
    Raises SourceValidationError on any failure.
    """
    try:
        source = ResumeSource.model_validate(raw)
    except Exception as e:  # pydantic ValidationError -> our error type
        raise SourceValidationError(f"source failed schema validation: {e}") from e

    skill_ids = [s.id for s in source.skills]
    _require_unique(skill_ids, "skill id")

    bullets = source.all_bullets()
    _require_unique([b.id for b in bullets], "bullet id")

    metric_ids: list[str] = [m.metric_id for b in bullets for m in b.metrics]
    _require_unique(metric_ids, "metric id")

    known_skills = set(skill_ids)
    for b in bullets:
        unknown = [sid for sid in b.skill_ids if sid not in known_skills]
        if unknown:
            raise SourceValidationError(
                f"bullet {b.id} references unknown skill ids: {unknown}"
            )
    return source


def _require_unique(ids: list[str], label: str) -> None:
    seen: set[str] = set()
    dupes: set[str] = set()
    for i in ids:
        if i in seen:
            dupes.add(i)
        seen.add(i)
    if dupes:
        raise SourceValidationError(f"duplicate {label}(s): {sorted(dupes)}")
