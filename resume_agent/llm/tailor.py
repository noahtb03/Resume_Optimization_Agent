"""LLM-2: SelectionResult (+ enriched source for labels) -> LLMTailorOutput.

Serializes the closed record set as an explicit allowlist and calls the model.
A `repair_brief` (built by core.repair) appends a targeted correction request.
Parsing/validation of the RESULT is the validator's job; here we only ensure we
return a well-formed LLMTailorOutput object (raising on unparseable JSON so the
service can fall back).
"""
from __future__ import annotations

from ..models.config import ResumeConfig
from ..models.inference import EnrichedResumeSource, InferenceRecord
from ..models.llm_io import LLMTailorOutput
from ..models.selection import SelectionResult
from .client import LLMClient
from ._json import extract_json
from .prompts.tailor import TAILOR_SYSTEM, TAILOR_USER


def _skills_block(selection: SelectionResult, enriched: EnrichedResumeSource) -> str:
    names = {s.id: s.name for s in enriched.source.skills}
    lines = [f"  {sid} -> {names.get(sid, sid)}" for sid in sorted(selection.approved_skill_ids)]
    return "\n".join(lines) or "  (none)"


def _inferences_block(selection: SelectionResult, enriched: EnrichedResumeSource) -> str:
    by_id: dict[str, InferenceRecord] = {i.id: i for i in enriched.inferences}
    lines = []
    for inf_id in sorted(selection.approved_inference_ids):
        inf = by_id.get(inf_id)
        if not inf:
            continue
        lines.append(f"  {inf.id} -> {inf.label} | uses={','.join(inf.allowed_uses)} | {inf.evidence}")
    return "\n".join(lines) or "  (none)"


def _metrics_block(selection: SelectionResult, enriched: EnrichedResumeSource) -> str:
    m_owner: dict[str, str] = {}
    for bid, mids in selection.metric_ownership.items():
        for mid in mids:
            m_owner[mid] = bid
    disp = {m.metric_id: m.display for b in enriched.source.all_bullets() for m in b.metrics}
    lines = [f"  {mid} -> {disp.get(mid, '?')} | bullet={bid}" for mid, bid in sorted(m_owner.items())]
    return "\n".join(lines) or "  (none)"


def _records_block(selection: SelectionResult) -> str:
    lines = []
    for item in selection.items:
        lines.append(f"{item.source_id} ({item.kind}):")
        for b in item.bullets:
            extra = []
            if b.skill_ids:
                extra.append(f"skills=[{','.join(b.skill_ids)}]")
            if b.metric_ids:
                extra.append(f"metrics=[{','.join(b.metric_ids)}]")
            if b.inference_ids:
                extra.append(f"inferences=[{','.join(b.inference_ids)}]")
            lines.append(f"  {b.bullet_id}  text=\"{b.text}\"  {' '.join(extra)}")
    return "\n".join(lines)


def tailor(
    selection: SelectionResult,
    enriched: EnrichedResumeSource,
    config: ResumeConfig,
    client: LLMClient,
    repair_brief: str | None = None,
) -> LLMTailorOutput:
    jd = selection.jd_profile
    forbidden = config.forbidden_modifiers
    forbidden_clause = (
        f"7. Do not use these words: {', '.join(forbidden)}." if forbidden else ""
    )
    max_chars = max((it.max_chars_per_bullet for it in selection.items), default=200)
    summary_spec = config.sections.get("summary")
    summary_enabled = summary_spec is not None and "summary" in config.section_order
    max_summary = (summary_spec.max_summary_chars if summary_spec else 320) or 320

    system = TAILOR_SYSTEM.format(forbidden_clause=forbidden_clause)
    user = TAILOR_USER.format(
        jd_title=jd.title or "Target Role",
        required_skills=", ".join(jd.required_skills) or "(none)",
        ats_keywords=", ".join(jd.ats_keywords) or "(none)",
        skills_block=_skills_block(selection, enriched),
        inferences_block=_inferences_block(selection, enriched),
        metrics_block=_metrics_block(selection, enriched),
        records_block=_records_block(selection),
        max_chars=max_chars,
        max_summary=max_summary,
        repair_block=("\n" + repair_brief) if repair_brief else "",
    )
    raw = client.complete(system=system, user=user, max_tokens=2000)
    out = LLMTailorOutput.model_validate(extract_json(raw))
    if not summary_enabled:
        out.summary = None  # summary not in section_order -> never include one
    return out