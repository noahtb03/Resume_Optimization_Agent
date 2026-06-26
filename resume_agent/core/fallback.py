"""Source-bullet fallback. When a generated bullet cannot be validated (even
after the single repair), revert to the original wording.

Metric rule on fallback: keep a source bullet's structured metrics only if the
renderer can show them exactly as provided (we attach the Metric objects; the
renderer uses Metric.display verbatim). We never inject numbers into prose. If
that isn't possible in context, metrics are omitted -- never reformatted.
"""
from __future__ import annotations

from ..models.output import TailoredBullet, ValidationStatus
from ..models.source import SourceBullet


def fallback_bullet(src: SourceBullet, reason: str) -> TailoredBullet:
    return TailoredBullet(
        text=src.text,
        source_bullet_ids=[src.id],
        used_skill_ids=list(src.skill_ids),
        used_inference_ids=[],
        used_metrics=list(src.metrics),  # carried as structured records, shown via display
        validation=ValidationStatus(
            status="fallback_source",
            notes=[f"reverted to source wording: {reason}"],
        ),
    )
