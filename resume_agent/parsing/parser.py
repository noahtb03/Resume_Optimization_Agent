"""Parser orchestrator (profile-time, one LLM call).

Files -> extracted text -> LLM structuring -> ParseDraft (draft source + flags).
The draft is NOT trusted: it must pass human review, then load_source, then the
linter. This module never decides truth -- it surfaces contradictions and
numbers as flags for a person to resolve.
"""
from __future__ import annotations

from ..llm.client import LLMClient
from ..llm._json import extract_json
from .extract import extract_text
from .prompts import PARSE_SYSTEM, PARSE_USER
from .schema import ParseDraft, ParseFlag


def parse_resumes(paths: list[str], client: LLMClient, max_files: int = 3) -> ParseDraft:
    if not paths:
        raise ValueError("provide at least one resume file")
    if len(paths) > max_files:
        raise ValueError(f"at most {max_files} resumes at once (got {len(paths)})")

    notes: list[str] = []
    blocks: list[str] = []
    for i, path in enumerate(paths, 1):
        res = extract_text(path)
        notes.extend(res.warnings)
        blocks.append(f"=== RESUME {i} ({res.path}) ===\n{res.text}")

    user = PARSE_USER.format(n=len(paths), resumes_block="\n\n".join(blocks))
    raw = client.complete(system=PARSE_SYSTEM, user=user, max_tokens=4000)

    try:
        data = extract_json(raw)
    except Exception as e:
        raise ValueError(f"parser model returned unparseable JSON: {e}") from e

    source = data.get("source", {})
    flags = [ParseFlag.model_validate(f) for f in data.get("flags", [])]
    notes.extend(data.get("notes", []))
    return ParseDraft(source=source, flags=flags, notes=notes)
