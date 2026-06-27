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
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        # last resort: try to salvage a truncated object by trimming to the last
        # complete element and closing open braces/brackets.
        salvaged = _salvage_truncated_json(candidate)
        if salvaged is not None:
            return salvaged
        raise


def _salvage_truncated_json(s: str) -> dict | None:
    # cut back to the last closing brace/bracket, then balance the delimiters
    cut = max(s.rfind("}"), s.rfind("]"))
    if cut == -1:
        return None
    frag = s[: cut + 1]
    # count unbalanced openers (approximate string handling is good enough for
    # closing a truncated tail)
    depth_stack: list[str] = []
    in_str = False
    esc = False
    for ch in frag:
        if esc:
            esc = False
            continue
        if ch == "\\":
            esc = True
            continue
        if ch == '"':
            in_str = not in_str
            continue
        if in_str:
            continue
        if ch in "{[":
            depth_stack.append(ch)
        elif ch in "}]":
            if depth_stack:
                depth_stack.pop()
    closers = "".join("}" if c == "{" else "]" for c in reversed(depth_stack))
    for attempt in (frag + closers, frag.rstrip().rstrip(",") + closers):
        try:
            return json.loads(attempt)
        except json.JSONDecodeError:
            continue
    return None