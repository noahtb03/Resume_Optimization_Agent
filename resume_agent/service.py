"""Public generation entry point: generate_resume(...).

Pipeline: LLM-1 (JD analyze) -> select -> LLM-2 (tailor) -> validate ->
optional single repair -> assemble (with per-bullet source fallback).

Stateless. Takes an LLMClient explicitly (BYOK) -- it never reads keys from env
or disk. A request-scoped CountingClient tracks llm_calls_used so the call
budget is reported honestly (2 on the happy path; +1 if a repair fires; +1 more
only if LLM-1 needed a reformat retry).
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

from .core.assembler import assemble
from .core.coverage import compute_coverage
from .core.repair import build_repair_brief
from .core.selector import select
from .core.validator import validate
from .llm.client import LLMClient
from .llm.jd_analyzer import analyze_jd
from .llm.tailor import tailor
from .models.config import ResumeConfig, default_config
from .models.inference import EnrichedResumeSource
from .models.llm_io import LLMTailorOutput
from .models.output import TailoredResume


class _CountingClient:
    def __init__(self, inner: LLMClient) -> None:
        self._inner = inner
        self.calls = 0

    def complete(self, *, system: str, user: str, max_tokens: int = 1500) -> str:
        self.calls += 1
        return self._inner.complete(system=system, user=user, max_tokens=max_tokens)


def generate_resume(
    enriched: EnrichedResumeSource,
    jd_text: str,
    client: LLMClient,
    config: ResumeConfig | None = None,
) -> TailoredResume:
    config = config or default_config()
    source = enriched.source
    counter = _CountingClient(client)

    # LLM-1
    jd_profile, _ = analyze_jd(jd_text, counter)

    # deterministic selection (authorization boundary)
    selection = select(enriched, jd_profile, config)

    # LLM-2 (parse failure -> empty output -> full source fallback downstream)
    try:
        output = tailor(selection, enriched, config, counter)
    except Exception:
        output = LLMTailorOutput(bullets=[])

    report = validate(output, selection, source, config)
    passing_status = "generated"

    if os.environ.get("RESUME_AGENT_DEBUG") and not report.ok:
        import sys
        print("[debug] first-pass validation violations:", file=sys.stderr)
        for line in report.violation_lines():
            print(f"[debug]   {line}", file=sys.stderr)

    # one bounded repair attempt
    if not report.ok and config.repair_budget > 0 and output.bullets:
        brief = build_repair_brief(report)
        try:
            repaired = tailor(selection, enriched, config, counter, repair_brief=brief)
            repaired_report = validate(repaired, selection, source, config)
            # adopt the repaired round even if partially failing; remaining
            # failures fall back to source per-bullet in the assembler.
            output, report, passing_status = repaired, repaired_report, "repaired"
        except Exception:
            pass  # keep first round; assembler falls back failed bullets

    coverage = compute_coverage(output, report, selection, source, jd_profile)
    return assemble(
        output=output, report=report, selection=selection, source=source,
        config=config, coverage=coverage,
        generated_at=datetime.now(timezone.utc).isoformat(),
        llm_calls_used=counter.calls,
        passing_status=passing_status,
    )
