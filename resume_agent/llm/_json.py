"""Tiny helper: pull a JSON object out of an LLM response, tolerating code
fences and surrounding prose."""
from __future__ import annotations

import json
import re

_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


def extract_json(text: str) -> dict:
    m = _FENCE.search(text)
    candidate = m.group(1) if m else text
    candidate = candidate.strip()
    # fall back to the first {...} span if there is leading/trailing prose
    if not candidate.startswith("{"):
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = candidate[start:end + 1]
    return json.loads(candidate)
