import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from grading_pipeline.config import load_roles, load_rubric
from grading_pipeline.llm_scoring import (
    DEFAULT_MAX_SOURCE_CHARS,
    SOURCE_TRUNCATION_NOTICE,
    _build_model_input,
    _truncate_source,
    score_summary_llm,
)


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
            "source_grounded_signals": {
                "wrong_patient_suspected": False,
                "unsupported_claims": [],
                "omitted_safety_facts": [],
            },
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
    assert result.source_grounded_signals == {
        "wrong_patient_suspected": False,
        "unsupported_claims": [],
        "omitted_safety_facts": [],
    }


def test_score_summary_llm_parses_structured_signals(monkeypatch: pytest.MonkeyPatch) -> None:
    """Signals returned by the LLM must be exposed on the AgentScore, with
    blank entries pruned and lists capped at 5 items."""
    rubric, role = _load_config()
    score = {dim_id: 3 for dim_id in rubric.dimension_ids}
    rationales = {dim_id: "r" for dim_id in rubric.dimension_ids}
    evidence = {dim_id: ["e"] for dim_id in rubric.dimension_ids}

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
            "source_grounded_signals": {
                "wrong_patient_suspected": True,
                "unsupported_claims": ["claim 1", "", "  ", "claim 2"],
                "omitted_safety_facts": [f"fact {i}" for i in range(7)],
            },
        },
    )

    result = score_summary_llm(
        "Patient summary with enough detail for testing.",
        role,
        rubric,
        source_text="Source packet describing a different patient entirely.",
        model="test-model",
    )

    assert result.source_grounded_signals is not None
    assert result.source_grounded_signals["wrong_patient_suspected"] is True
    assert result.source_grounded_signals["unsupported_claims"] == ["claim 1", "claim 2"]
    assert len(result.source_grounded_signals["omitted_safety_facts"]) == 5


def test_score_summary_llm_rejects_missing_signals_when_source_grounded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rubric, role = _load_config()
    score = {dim_id: 3 for dim_id in rubric.dimension_ids}
    rationales = {dim_id: "r" for dim_id in rubric.dimension_ids}
    evidence = {dim_id: ["e"] for dim_id in rubric.dimension_ids}

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

    with pytest.raises(Exception, match="source_grounded_signals"):
        score_summary_llm(
            "Patient summary with enough detail for testing.",
            role,
            rubric,
            source_text="Source packet with matching clinical detail.",
            model="test-model",
        )


def test_build_model_input_wraps_source_and_summary_in_delimiters() -> None:
    rendered = _build_model_input(
        "The summary body.",
        source_text="Source record body.",
    )
    assert "<<<SOURCE_RECORD>>>" in rendered
    assert "<<<END_SOURCE_RECORD>>>" in rendered
    assert "<<<SUMMARY_TO_GRADE>>>" in rendered
    assert "<<<END_SUMMARY_TO_GRADE>>>" in rendered
    assert rendered.index("<<<SOURCE_RECORD>>>") < rendered.index("<<<SUMMARY_TO_GRADE>>>")


def test_build_model_input_returns_bare_summary_when_no_source() -> None:
    assert _build_model_input("Just the summary.") == "Just the summary."


def test_truncate_source_appends_notice_when_over_budget(caplog: pytest.LogCaptureFixture) -> None:
    long_source = "x" * (DEFAULT_MAX_SOURCE_CHARS + 500)
    with caplog.at_level("WARNING", logger="grading_pipeline.llm_scoring"):
        truncated = _truncate_source(long_source)
    expected_notice = SOURCE_TRUNCATION_NOTICE.format(max_chars=DEFAULT_MAX_SOURCE_CHARS)
    assert truncated.endswith(expected_notice)
    assert len(truncated) == DEFAULT_MAX_SOURCE_CHARS + 1 + len(expected_notice)
    assert any("truncated" in record.message for record in caplog.records)


def test_truncate_source_noop_when_under_budget() -> None:
    short = "abc"
    assert _truncate_source(short) == short


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
