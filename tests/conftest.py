import json
import pathlib

import pytest

from resume_agent.core.validate_source import load_source
from resume_agent.core.enrichment import enrich_source
from resume_agent.enrich_service import enrich_profile

FIX = pathlib.Path(__file__).parent / "fixtures"


@pytest.fixture
def raw_source() -> dict:
    return json.loads((FIX / "source_sample.json").read_text())


@pytest.fixture
def jd_text() -> str:
    return (FIX / "jd_sample.txt").read_text()


@pytest.fixture
def source(raw_source):
    return load_source({k: v for k, v in raw_source.items() if k != "inferences"})


@pytest.fixture
def enriched(raw_source):
    return enrich_profile(raw_source)


class ScriptedClient:
    """Returns queued responses in order. First call is LLM-1 (JD), then LLM-2,
    then any repair. Distinguishes JD vs tailor by the system prompt."""

    def __init__(self, jd_json: dict, tailor_jsons: list[dict]):
        self._jd = json.dumps(jd_json)
        self._tailor = [json.dumps(t) for t in tailor_jsons]
        self.calls = 0

    def complete(self, *, system: str, user: str, max_tokens: int = 1500) -> str:
        self.calls += 1
        if "information extractor" in system.lower():
            return self._jd
        out = self._tailor.pop(0)
        return out


@pytest.fixture
def jd_json():
    return {
        "title": "Data Scientist", "seniority": "mid", "domain": "healthcare",
        "required_skills": ["python", "sql", "machine learning", "scikit-learn"],
        "preferred_skills": ["nlp", "pytorch"],
        "ats_keywords": ["python", "sql", "tableau", "machine learning",
                         "classification", "data pipelines", "pandas"],
        "responsibilities": ["build machine learning models", "write sql", "dashboards"],
        "hard_requirements": [{"text": "Bachelor's degree in a quantitative field", "kind": "degree"}],
    }
