import pytest

from resume_agent.core.enrichment import enrich_source, propose_inferences
from resume_agent.models.inference import EnrichedResumeSource, InferenceRecord


def test_rules_propose_expected_labels(source):
    labels = {i.label for i in propose_inferences(source)}
    # amig_01 (sklearn + classification) -> Applied AI / Machine learning
    assert "Applied AI" in labels
    # lab_01 (pytorch + classification) too
    assert "Machine learning" in labels


def test_high_confidence_auto_approved(source):
    enriched = enrich_source(source, auto_approve_threshold=0.8)
    approved = enriched.approved_inferences()
    assert any(i.label == "Applied AI" for i in approved)


def test_manual_inference_passthrough(enriched):
    # the fixture includes a manually pre-approved cross-functional inference
    labels = {i.label for i in enriched.approved_inferences()}
    assert "Cross-functional collaboration" in labels


def test_blocked_escalation_cannot_be_approved(source):
    bad = InferenceRecord(
        id="inf_bad", source_bullet_id="amig_01", label="Led cross-functional teams",
        kind="competency", claim_level="blocked_escalation", confidence=0.99,
        evidence="x", approval_status="approved", allowed_uses=["summary"],
        inferred_by="rules",
    )
    with pytest.raises(ValueError):
        EnrichedResumeSource(source=source, inferences=[bad])
