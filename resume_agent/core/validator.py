"""Provenance & Constraint Validator.

Validates LLMTailorOutput against the SelectionResult authorization boundary.
It guarantees ATTRIBUTION and STRUCTURED FACTS:
  - referenced source-bullet ids exist in the selected set
  - declared skills / inferences are authorized (and inferences used only where
    their allowed_uses permit)
  - every metric in prose is an EXACT Metric.display substring, owned by a cited
    bullet, and no other number appears in the text
  - length and section caps hold

It does NOT prove that paraphrase is semantically faithful. `used_skill_ids` and
`used_inference_ids` are model-reported provenance metadata -- we validate they
are AUTHORIZED, not that the term literally appears in the prose. The residual
(scope/inflation drift) is held by prompt constraints, the forbidden-modifier
lint (check 6), one repair, and source-bullet fallback.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from ..models.config import ResumeConfig
from ..models.llm_io import GenBullet, GenSummary, LLMTailorOutput
from ..models.selection import SelectionResult
from ..models.source import Metric, ResumeSource

_DIGIT_RUN = re.compile(r"\d[\d,.]*")


@dataclass
class BulletVerdict:
    gen: GenBullet
    ok: bool
    violations: list[str] = field(default_factory=list)
    resolved_metrics: list[Metric] = field(default_factory=list)


@dataclass
class SummaryVerdict:
    gen: GenSummary | None
    ok: bool
    violations: list[str] = field(default_factory=list)


@dataclass
class ValidationReport:
    bullets: list[BulletVerdict]
    summary: SummaryVerdict

    @property
    def ok(self) -> bool:
        return all(b.ok for b in self.bullets) and self.summary.ok

    def violation_lines(self) -> list[str]:
        lines: list[str] = []
        for i, b in enumerate(self.bullets):
            for v in b.violations:
                lines.append(f"bullet[{i}]: {v}")
        for v in self.summary.violations:
            lines.append(f"summary: {v}")
        return lines


def _metric_index(source: ResumeSource) -> dict[str, Metric]:
    return {m.metric_id: m for b in source.all_bullets() for m in b.metrics}


def _check_numbers(text: str, displays: list[str]) -> list[str]:
    """Every Metric.display must be an exact substring; every digit-run in text
    must fall inside one of those display substrings."""
    violations: list[str] = []
    covered: list[tuple[int, int]] = []
    for disp in displays:
        start = 0
        found_any = False
        while True:
            idx = text.find(disp, start)
            if idx == -1:
                break
            found_any = True
            covered.append((idx, idx + len(disp)))
            start = idx + len(disp)
        if not found_any:
            violations.append(f"declared metric display not found verbatim in text: {disp!r}")

    for m in _DIGIT_RUN.finditer(text):
        s, e = m.span()
        if not any(cs <= s and e <= ce for cs, ce in covered):
            violations.append(f"unapproved number {m.group()!r} in text")
    return violations


def validate(
    output: LLMTailorOutput,
    selection: SelectionResult,
    source: ResumeSource,
    config: ResumeConfig,
) -> ValidationReport:
    metric_by_id = _metric_index(source)
    forbidden = [w.lower() for w in config.forbidden_modifiers]
    max_chars = max(
        (it.max_chars_per_bullet for it in selection.items), default=240
    )

    bullet_verdicts: list[BulletVerdict] = []
    for gen in output.bullets:
        viol: list[str] = []

        # check 2: source-bullet ids authorized
        bad_src = [b for b in gen.source_bullet_ids
                   if b not in selection.selected_source_bullet_ids]
        if not gen.source_bullet_ids:
            viol.append("no source_bullet_ids declared")
        if bad_src:
            viol.append(f"unauthorized source_bullet_ids: {bad_src}")

        # check 3: skills authorized (declared provenance only)
        bad_skill = [s for s in gen.used_skill_ids
                     if s not in selection.approved_skill_ids]
        if bad_skill:
            viol.append(f"unauthorized used_skill_ids: {bad_skill}")

        # check 9: inferences authorized AND allowed for bullet_reframing
        bad_inf = []
        for inf_id in gen.used_inference_ids:
            if inf_id not in selection.approved_inference_ids:
                bad_inf.append(inf_id)
            elif "bullet_reframing" not in selection.inference_uses.get(inf_id, set()):
                viol.append(f"inference {inf_id} not permitted for bullet_reframing")
        if bad_inf:
            viol.append(f"unauthorized used_inference_ids: {bad_inf}")

        # check 4: metric ownership + exactness
        owned: set[str] = set()
        for b in gen.source_bullet_ids:
            owned |= selection.metric_ownership.get(b, set())
        resolved: list[Metric] = []
        bad_metric = [m for m in gen.used_metric_ids if m not in owned]
        if bad_metric:
            viol.append(f"metrics not owned by cited bullets: {bad_metric}")
        displays: list[str] = []
        for mid in gen.used_metric_ids:
            if mid in owned and mid in metric_by_id:
                resolved.append(metric_by_id[mid])
                displays.append(metric_by_id[mid].display)
        viol.extend(_check_numbers(gen.text, displays))

        # check 5: length cap
        if len(gen.text) > max_chars:
            viol.append(f"text length {len(gen.text)} > cap {max_chars}")

        # check 6: forbidden modifier lint
        low = gen.text.lower()
        hits = [w for w in forbidden if re.search(rf"\b{re.escape(w)}\b", low)]
        if hits:
            viol.append(f"forbidden modifiers present: {hits}")

        bullet_verdicts.append(BulletVerdict(
            gen=gen, ok=not viol, violations=viol, resolved_metrics=resolved,
        ))

    # check 8: summary references
    summary_v: list[str] = []
    gs: GenSummary | None = output.summary
    if gs is not None:
        bad_sk = [s for s in gs.used_skill_ids if s not in selection.approved_skill_ids]
        if bad_sk:
            summary_v.append(f"unauthorized summary skills: {bad_sk}")
        for inf_id in gs.used_inference_ids:
            if inf_id not in selection.approved_inference_ids:
                summary_v.append(f"unauthorized summary inference: {inf_id}")
            elif "summary" not in selection.inference_uses.get(inf_id, set()):
                summary_v.append(f"inference {inf_id} not permitted for summary")
        valid_exp_ids = {it.source_id for it in selection.items if it.kind == "experience"}
        bad_exp = [e for e in gs.referenced_experience_ids if e not in valid_exp_ids]
        if bad_exp:
            summary_v.append(f"unauthorized referenced_experience_ids: {bad_exp}")
        # summary may not contain numbers at all (no metric is attached to a summary)
        if _DIGIT_RUN.search(gs.text):
            summary_v.append("summary contains a number (not permitted)")
        spec = config.sections.get("summary")
        cap = spec.max_summary_chars if spec else None
        if cap and len(gs.text) > cap:
            summary_v.append(f"summary length {len(gs.text)} > cap {cap}")
        hits = [w for w in forbidden if re.search(rf"\b{re.escape(w)}\b", gs.text.lower())]
        if hits:
            summary_v.append(f"forbidden modifiers in summary: {hits}")

    return ValidationReport(
        bullets=bullet_verdicts,
        summary=SummaryVerdict(gen=gs, ok=not summary_v, violations=summary_v),
    )
