"""Builds a targeted repair instruction from a failed ValidationReport.

The actual re-prompt is assembled in llm/tailor.py; this module just turns the
violations into a compact, model-readable correction brief. One repair only;
the budget is enforced in service.py.
"""
from __future__ import annotations

from .validator import ValidationReport


def build_repair_brief(report: ValidationReport) -> str:
    lines = ["The previous JSON had these violations. Fix ONLY these and return "
             "the same JSON schema. Do not introduce anything new:"]
    for v in report.violation_lines():
        lines.append(f"  - {v}")
    lines.append(
        "Rules reminder: use only the provided source bullets, approved skills, "
        "approved inferences (only where their allowed_uses permit), and metrics "
        "owned by the bullets you cite. A metric may appear in text ONLY as its "
        "exact display string."
    )
    return "\n".join(lines)
