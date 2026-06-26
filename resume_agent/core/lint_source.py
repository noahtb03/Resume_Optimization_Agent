"""Deterministic source linter (profile-time, no LLM, no network).

Catches data-contract problems that would otherwise cause silent fallbacks or
forced repairs at generation time -- BEFORE any token is spent. Reports; never
auto-fixes (auto-fixing text would let code decide wording). Run after editing a
source file or after parsing.

Checks:
  - metric display strings must appear verbatim in their bullet text
  - any number in bullet text must belong to an attached metric's display
  - approved defensible_inferences usable in bullets should allow bullet_reframing
  - bullets already over the configured char cap (will never survive rephrasing)
  - summary-only inferences flagged so it's a conscious choice
"""
from __future__ import annotations

import re

from ..models.config import ResumeConfig, default_config
from ..models.inference import EnrichedResumeSource

_DIGIT_RUN = re.compile(r"\d[\d,.]*")


class LintFinding:
    def __init__(self, level: str, where: str, message: str):
        self.level = level      # "error" | "warning"
        self.where = where
        self.message = message

    def __repr__(self):
        return f"[{self.level}] {self.where}: {self.message}"


def lint_source(enriched: EnrichedResumeSource, config: ResumeConfig | None = None) -> list[LintFinding]:
    config = config or default_config()
    findings: list[LintFinding] = []
    source = enriched.source

    exp_cap = config.sections["experience"].max_chars_per_bullet or 10_000
    proj_cap = (config.sections.get("projects").max_chars_per_bullet
                if config.sections.get("projects") else exp_cap) or 10_000

    for bullet in source.all_bullets():
        displays = [m.display for m in bullet.metrics]
        # 1: each display must appear verbatim
        for m in bullet.metrics:
            if m.display not in bullet.text:
                findings.append(LintFinding(
                    "error", bullet.id,
                    f"metric '{m.metric_id}' display {m.display!r} does not appear "
                    f"verbatim in the bullet text -- will cause a fallback. Either put "
                    f"the exact phrase in the text or remove the metric."))
        # 2: every number in text must be covered by some display
        covered_spans: list[tuple[int, int]] = []
        for disp in displays:
            start = 0
            while True:
                idx = bullet.text.find(disp, start)
                if idx == -1:
                    break
                covered_spans.append((idx, idx + len(disp)))
                start = idx + len(disp)
        for mnum in _DIGIT_RUN.finditer(bullet.text):
            s, e = mnum.span()
            if not any(cs <= s and e <= ce for cs, ce in covered_spans):
                findings.append(LintFinding(
                    "error", bullet.id,
                    f"number {mnum.group()!r} in text is not part of any attached "
                    f"metric display -- it will be stripped or cause a fallback. Add a "
                    f"metric whose display contains it, or remove the number."))

    # 3: char-cap sanity (which cap depends on whether it's an exp or proj bullet)
    exp_bullet_ids = {b.id for e in source.experiences for b in e.bullets}
    for bullet in source.all_bullets():
        cap = exp_cap if bullet.id in exp_bullet_ids else proj_cap
        if len(bullet.text) > cap:
            findings.append(LintFinding(
                "warning", bullet.id,
                f"source text is {len(bullet.text)} chars, over the {cap} cap -- the "
                f"rephrase will likely be rejected on length and fall back to source."))

    # 4: inference allowed_uses sanity
    for inf in enriched.approved_inferences():
        if "bullet_reframing" not in inf.allowed_uses:
            findings.append(LintFinding(
                "warning", inf.id,
                f"approved inference {inf.label!r} cannot be used in bullets "
                f"(allowed_uses={inf.allowed_uses}). If you want it available in bullet "
                f"wording, add 'bullet_reframing'."))

    return findings


def format_findings(findings: list[LintFinding]) -> str:
    if not findings:
        return "Lint passed: no data-contract issues found."
    errors = [f for f in findings if f.level == "error"]
    warnings = [f for f in findings if f.level == "warning"]
    lines = [f"Lint found {len(errors)} error(s), {len(warnings)} warning(s):"]
    for f in errors + warnings:
        lines.append(f"  {f}")
    return "\n".join(lines)
