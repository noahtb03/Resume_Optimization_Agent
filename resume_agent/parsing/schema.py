"""Schemas for the parse stage output.

The parser produces a DRAFT source plus a list of flags. The draft is NOT a
source of truth until a human reviews it -- contradictions across resumes and
unverified numbers are surfaced as flags, never silently resolved.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

FlagKind = Literal[
    "contradiction",      # resumes disagree on a fact (tech, ownership, dates)
    "unverified_metric",  # a number was found; confirm + structure as a metric
    "low_confidence",     # extraction was uncertain / garbled
    "missing_field",      # expected field (dates, employer) could not be found
    "needs_review",       # generic: please confirm this is accurate
]


class ParseFlag(BaseModel):
    kind: FlagKind
    message: str                       # human-readable: what to check and why
    where: str = ""                    # bullet id / employer / field this concerns
    options: list[str] = Field(default_factory=list)  # for contradictions: the competing versions


class ParseDraft(BaseModel):
    """Draft source (same shape as ResumeSource raw dict) plus review flags."""
    source: dict                       # raw dict; validated by load_source after review
    flags: list[ParseFlag] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)  # extraction warnings, etc.
