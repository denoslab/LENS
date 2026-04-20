import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from grading_pipeline.config import load_roles, load_rubric
from grading_pipeline.llm_scoring import score_summary_llm


def _load_config():
    rubric = load_rubric(PROJECT_ROOT / "config" / "lens_rubric.json")
    roles = load_roles(PROJECT_ROOT / "config" / "roles.json", rubric.dimension_ids)
    return rubric, roles[0]


def test_score_summary_llm_returns_rationales_and_evidence(monkeypatch: pytest.MonkeyPatch) -> None:
    rubric, role = _load_config()
    score = {dim_id: 3 for dim_id in rubric.dimension_ids}
    rationales = {dim_id: f"rationale for {dim_id}" for dim_id in rubric.dimension_ids}
    evidence = {dim_id: [f"evidence for {dim_id}"] for dim_id in rubric.dimension_ids}

    monkeypatch.setattr(
        "grading_pipeline.llm_scoring.create_response",
        lambda **kwargs: {"ok": True},
    )
    monkeypatch.setattr(
        "grading_pipeline.llm_scoring.extract_json_output",
        lambda response: {
            "role_id": role.id,
            "score": score,
            "rationales": rationales,
            "evidence": evidence,
        },
    )

    result = score_summary_llm(
        "Patient summary with enough detail for testing.",
        role,
        rubric,
        source_text="Source packet with matching clinical detail.",
        model="test-model",
    )

    assert result.rationales == rationales
    assert result.evidence == evidence
    assert result.overall_score is not None


def test_score_summary_llm_rejects_missing_rationales(monkeypatch: pytest.MonkeyPatch) -> None:
    rubric, role = _load_config()
    score = {dim_id: 3 for dim_id in rubric.dimension_ids}
    evidence = {dim_id: [f"evidence for {dim_id}"] for dim_id in rubric.dimension_ids}

    monkeypatch.setattr(
        "grading_pipeline.llm_scoring.create_response",
        lambda **kwargs: {"ok": True},
    )
    monkeypatch.setattr(
        "grading_pipeline.llm_scoring.extract_json_output",
        lambda response: {
            "role_id": role.id,
            "score": score,
            "evidence": evidence,
        },
    )

    with pytest.raises(Exception, match="rationales"):
        score_summary_llm(
            "Patient summary with enough detail for testing.",
            role,
            rubric,
            model="test-model",
        )
