import asyncio
import sys
from pathlib import Path
from statistics import mean
from typing import Dict

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from grading_pipeline.config import load_roles, load_rubric
from grading_pipeline.orchestrator import (
    CANONICAL_ROLE_IDS,
    DIMENSION_IDS,
    ROLE_NAME_BY_ID,
    _default_adjudicator,
    build_disagreement_map,
    run_pipeline,
)
from grading_pipeline.scoring import AgentScore, compute_overall_score


def _load_config():
    rubric = load_rubric(PROJECT_ROOT / "config" / "lens_rubric.json")
    roles = load_roles(PROJECT_ROOT / "config" / "roles.json", rubric.dimension_ids)
    return rubric, roles


def _make_agent(role_id: str, scores: Dict[str, int], overall: float = 3.0) -> AgentScore:
    rationales = {dim: "ok" for dim in DIMENSION_IDS}
    return AgentScore(
        role_id=role_id,
        scores=scores,
        rationales=rationales,
        overall_score=overall,
    )


def test_disagreement_map_gap_and_flag_logic() -> None:
    base_scores = {dim: 3.0 for dim in DIMENSION_IDS}

    physician_scores = dict(base_scores)
    triage_scores = dict(base_scores)
    bedside_scores = dict(base_scores)

    physician_scores["factual_accuracy"] = 4.0
    triage_scores["factual_accuracy"] = 3.0
    bedside_scores["factual_accuracy"] = 2.0

    scorecards = {
        "physician": {"scores": physician_scores},
        "triage_nurse": {"scores": triage_scores},
        "bedside_nurse": {"scores": bedside_scores},
    }

    disagreement = build_disagreement_map(scorecards, gap_threshold=0.5)

    factual = disagreement["factual_accuracy"]
    assert factual["role_scores"] == {
        "Physician": 4.0,
        "Triage Nurse": 3.0,
        "Bedside Nurse": 2.0,
    }
    assert factual["score_gap"] == 2.0
    assert factual["flag"] is True

    non_disputed = disagreement["organized_by_condition"]
    assert non_disputed["score_gap"] == 0.0
    assert non_disputed["flag"] is False


def test_validation_repairs_only_invalid_role_output() -> None:
    rubric, roles = _load_config()
    calls = {role_id: 0 for role_id in CANONICAL_ROLE_IDS}

    valid_scores = {dim: 3 for dim in DIMENSION_IDS}
    invalid_scores = dict(valid_scores)
    invalid_scores["factual_accuracy"] = 6

    def role_scorer(summary, role, rubric):
        calls[role.id] += 1
        if role.id == "physician" and calls[role.id] == 1:
            return _make_agent(role.id, invalid_scores, overall=6.0)
        return _make_agent(role.id, valid_scores, overall=3.0)

    result = asyncio.run(
        run_pipeline(
            summary="Patient has diabetes, CKD, and recent symptoms with medication and lab updates.",
            mode="heuristic",
            output_format="json",
            rubric=rubric,
            roles=roles,
            role_scorer=role_scorer,
            gap_threshold=10.0,
            max_retries=2,
        )
    )

    assert calls["physician"] == 2
    assert calls["triage_nurse"] == 1
    assert calls["bedside_nurse"] == 1
    assert len(result["per_role_scorecards"]) == 3


def test_conditional_adjudication_in_llm_mode() -> None:
    rubric, roles = _load_config()

    no_gap_scores = {dim: 3 for dim in DIMENSION_IDS}
    adjudicator_calls = {"count": 0}

    def no_gap_scorer(summary, role, rubric):
        return _make_agent(role.id, no_gap_scores, overall=3.0)

    def adjudicator_spy(**kwargs):
        adjudicator_calls["count"] += 1
        return {role_id: {"scores": {}, "rationales": {}} for role_id in CANONICAL_ROLE_IDS}

    no_gap_result = asyncio.run(
        run_pipeline(
            summary="Patient has chronic disease history and clear treatment updates over time.",
            mode="llm",
            output_format="json",
            rubric=rubric,
            roles=roles,
            role_scorer=no_gap_scorer,
            adjudicator=adjudicator_spy,
            gap_threshold=0.5,
            max_retries=2,
        )
    )

    assert no_gap_result["adjudication_ran"] is False
    assert adjudicator_calls["count"] == 0
    assert no_gap_result["disputed_dimensions"] == []
    assert no_gap_result["initial_disagreement_map"]["factual_accuracy"]["flag"] is False

    disputed_physician = dict(no_gap_scores)
    disputed_triage = dict(no_gap_scores)
    disputed_bedside = dict(no_gap_scores)
    disputed_physician["factual_accuracy"] = 5
    disputed_triage["factual_accuracy"] = 3
    disputed_bedside["factual_accuracy"] = 2

    def gap_scorer(summary, role, rubric):
        if role.id == "physician":
            return _make_agent(role.id, disputed_physician, overall=3.0)
        if role.id == "triage_nurse":
            return _make_agent(role.id, disputed_triage, overall=3.0)
        return _make_agent(role.id, disputed_bedside, overall=3.0)

    def adjudicator_once(**kwargs):
        adjudicator_calls["count"] += 1
        disputed_dims = kwargs["disputed_dims"]
        updates = {}
        for role_id in CANONICAL_ROLE_IDS:
            updates[role_id] = {
                "scores": {dim: 4 for dim in disputed_dims},
                "rationales": {dim: "adjudicated" for dim in disputed_dims},
            }
        return updates

    with_gap_result = asyncio.run(
        run_pipeline(
            summary="Patient has chronic disease history and clear treatment updates over time.",
            mode="llm",
            output_format="json",
            rubric=rubric,
            roles=roles,
            role_scorer=gap_scorer,
            adjudicator=adjudicator_once,
            gap_threshold=0.5,
            max_retries=2,
        )
    )

    assert with_gap_result["adjudication_ran"] is True
    assert adjudicator_calls["count"] == 1
    assert with_gap_result["disputed_dimensions"] == ["factual_accuracy"]
    assert with_gap_result["initial_disagreement_map"]["factual_accuracy"]["flag"] is True

    pre_by_role = {
        card["role_id"]: card for card in with_gap_result["pre_adjudication_scorecards"]
    }
    assert pre_by_role["physician"]["scores"]["factual_accuracy"] == 5.0
    assert pre_by_role["triage_nurse"]["scores"]["factual_accuracy"] == 3.0
    assert pre_by_role["bedside_nurse"]["scores"]["factual_accuracy"] == 2.0

    by_role = {
        card["role_id"]: card for card in with_gap_result["per_role_scorecards"]
    }
    assert by_role["physician"]["scores"]["factual_accuracy"] == 4.0
    assert by_role["triage_nurse"]["scores"]["factual_accuracy"] == 4.0
    assert by_role["bedside_nurse"]["scores"]["factual_accuracy"] == 4.0


def test_run_pipeline_rejects_short_summary_programmatically() -> None:
    rubric, roles = _load_config()

    with pytest.raises(ValueError, match="at least 30 characters"):
        asyncio.run(
            run_pipeline(
                summary="too short",
                mode="heuristic",
                output_format="json",
                rubric=rubric,
                roles=roles,
            )
        )


def test_post_adjudication_repair_preserves_non_disputed_dimensions() -> None:
    rubric, roles = _load_config()
    calls = {role_id: 0 for role_id in CANONICAL_ROLE_IDS}

    physician_initial = {dim: 3 for dim in DIMENSION_IDS}
    triage_initial = {dim: 3 for dim in DIMENSION_IDS}
    bedside_initial = {dim: 3 for dim in DIMENSION_IDS}
    physician_initial["factual_accuracy"] = 5
    triage_initial["factual_accuracy"] = 3
    bedside_initial["factual_accuracy"] = 2

    physician_repair = {dim: 1 for dim in DIMENSION_IDS}
    physician_repair["factual_accuracy"] = 4

    def role_scorer(summary, role, rubric):
        calls[role.id] += 1
        if role.id == "physician":
            if calls[role.id] == 1:
                return _make_agent(role.id, physician_initial, overall=3.0)
            return _make_agent(role.id, physician_repair, overall=3.0)
        if role.id == "triage_nurse":
            return _make_agent(role.id, triage_initial, overall=3.0)
        return _make_agent(role.id, bedside_initial, overall=3.0)

    def invalid_adjudicator(**kwargs):
        disputed_dims = kwargs["disputed_dims"]
        updates = {role_id: {"scores": {}, "rationales": {}} for role_id in CANONICAL_ROLE_IDS}
        updates["physician"] = {
            "scores": {dim: 6 for dim in disputed_dims},
            "rationales": {dim: "invalid" for dim in disputed_dims},
        }
        return updates

    result = asyncio.run(
        run_pipeline(
            summary="Patient history includes chronic disease, medication changes, and enough detail for the pipeline to validate input.",
            mode="llm",
            output_format="json",
            rubric=rubric,
            roles=roles,
            role_scorer=role_scorer,
            adjudicator=invalid_adjudicator,
            gap_threshold=0.5,
            max_retries=2,
        )
    )

    physician = {card["role_id"]: card for card in result["per_role_scorecards"]}["physician"]
    assert calls["physician"] == 2
    assert physician["scores"]["factual_accuracy"] == 4.0
    assert physician["scores"]["timeline_evolution"] == 3.0


def test_aggregation_recomputes_role_overall_from_w_prior() -> None:
    rubric, roles = _load_config()
    role_by_id = {role.id: role for role in roles}

    scores = {
        "factual_accuracy": 5,
        "relevant_chronic_problem_coverage": 4,
        "organized_by_condition": 3,
        "timeline_evolution": 2,
        "recent_changes_highlighted": 1,
        "focused_not_cluttered": 5,
        "usefulness_for_decision_making": 4,
        "clarity_readability_formatting": 2,
    }

    def role_scorer(summary, role, rubric):
        return _make_agent(role.id, scores, overall=2.0)

    result = asyncio.run(
        run_pipeline(
            summary="Patient history includes multiple chronic diseases, recent changes, and medication details for ED handoff.",
            mode="heuristic",
            output_format="json",
            rubric=rubric,
            roles=roles,
            role_scorer=role_scorer,
            gap_threshold=10.0,
            max_retries=2,
        )
    )

    by_role = {card["role_id"]: card for card in result["per_role_scorecards"]}

    expected_overalls = []
    for role_id in CANONICAL_ROLE_IDS:
        role = role_by_id[role_id]
        expected = compute_overall_score(scores, role.w_prior, rubric.dimension_ids)
        expected_overalls.append(expected)
        assert by_role[role_id]["role"] == ROLE_NAME_BY_ID[role_id]
        assert by_role[role_id]["overall"] == expected

    expected_overall_across_roles = round(mean(expected_overalls), 4)
    assert result["overall_across_roles"] == expected_overall_across_roles


def test_source_grounded_pipeline_rejects_heuristic_mode() -> None:
    rubric, roles = _load_config()

    with pytest.raises(ValueError, match="requires mode='llm'"):
        asyncio.run(
            run_pipeline(
                summary="Patient has chronic disease history, recent worsening, and medication changes relevant to handoff.",
                source_text="Source packet shows insulin timing, oxygen dependence, and recent deterioration over 24 hours.",
                mode="heuristic",
                output_format="json",
                rubric=rubric,
                roles=roles,
                gap_threshold=10.0,
            )
        )


def test_source_grounded_llm_pipeline_sets_meta_and_passes_source() -> None:
    rubric, roles = _load_config()
    captured = {}
    fixed_scores = {dim: 3 for dim in DIMENSION_IDS}

    def role_scorer(summary, role, rubric, source_text=None):
        captured[role.id] = source_text
        return AgentScore(
            role_id=role.id,
            scores=fixed_scores,
            rationales={dim: "ok" for dim in DIMENSION_IDS},
            overall_score=3.0,
            source_grounded_signals={
                "wrong_patient_suspected": False,
                "unsupported_claims": [],
                "contradicted_claims": [],
                "omitted_safety_facts": [],
            },
        )

    result = asyncio.run(
        run_pipeline(
            summary="Patient has chronic disease history, recent worsening, and medication changes relevant to handoff.",
            source_text="Source packet shows insulin timing, oxygen dependence, and recent deterioration over 24 hours.",
            mode="llm",
            output_format="json",
            rubric=rubric,
            roles=roles,
            role_scorer=role_scorer,
            gap_threshold=10.0,
        )
    )

    assert result["meta"]["evaluation_context"] == "source_grounded"
    assert result["meta"]["source_text_provided"] is True
    assert set(captured) == set(CANONICAL_ROLE_IDS)
    for value in captured.values():
        assert value is not None
        assert "oxygen dependence" in value


def test_adjudication_uses_configured_model_not_hardcoded_default() -> None:
    rubric, roles = _load_config()

    disputed_physician = {dim: 3 for dim in DIMENSION_IDS}
    disputed_triage = {dim: 3 for dim in DIMENSION_IDS}
    disputed_bedside = {dim: 3 for dim in DIMENSION_IDS}
    disputed_physician["factual_accuracy"] = 5
    disputed_triage["factual_accuracy"] = 3
    disputed_bedside["factual_accuracy"] = 2
    seen = {}

    def gap_scorer(summary, role, rubric):
        if role.id == "physician":
            return _make_agent(role.id, disputed_physician, overall=3.0)
        if role.id == "triage_nurse":
            return _make_agent(role.id, disputed_triage, overall=3.0)
        return _make_agent(role.id, disputed_bedside, overall=3.0)

    def adjudicator_spy(**kwargs):
        seen.update(kwargs)
        disputed_dims = kwargs["disputed_dims"]
        return {
            role_id: {
                "scores": {dim: 4 for dim in disputed_dims},
                "rationales": {dim: "ok" for dim in disputed_dims},
            }
            for role_id in CANONICAL_ROLE_IDS
        }

    result = asyncio.run(
        run_pipeline(
            summary="Patient has chronic disease history and clear treatment updates over time.",
            mode="llm",
            output_format="json",
            rubric=rubric,
            roles=roles,
            role_scorer=gap_scorer,
            adjudicator=adjudicator_spy,
            model="test-model-mini",
            gap_threshold=0.5,
            max_retries=2,
        )
    )

    assert result["adjudication_ran"] is True
    assert seen["model"] == "test-model-mini"
    assert result["meta"]["adjudicator_model"] == "test-model-mini"


def test_source_grounded_summary_aggregates_signals_across_roles() -> None:
    """Per-role signals must be unioned into a single pipeline-level summary,
    with ``wrong_patient_suspected`` OR'd and text findings deduped with the
    roles that reported them."""
    rubric, roles = _load_config()
    fixed_scores = {dim: 3 for dim in DIMENSION_IDS}

    per_role_signals = {
        "physician": {
            "wrong_patient_suspected": False,
            "unsupported_claims": ["claim A", "shared claim"],
            "contradicted_claims": ["summary says no anticoagulation"],
            "omitted_safety_facts": ["missed insulin"],
        },
        "triage_nurse": {
            "wrong_patient_suspected": True,
            "unsupported_claims": ["shared claim"],
            "contradicted_claims": ["summary says no anticoagulation"],
            "omitted_safety_facts": [],
        },
        "bedside_nurse": {
            "wrong_patient_suspected": False,
            "unsupported_claims": [],
            "contradicted_claims": [],
            "omitted_safety_facts": ["missed insulin", "oxygen dependence not noted"],
        },
    }

    def role_scorer(summary, role, rubric, source_text=None):
        return AgentScore(
            role_id=role.id,
            scores=fixed_scores,
            rationales={dim: "ok" for dim in DIMENSION_IDS},
            overall_score=3.0,
            source_grounded_signals=per_role_signals[role.id],
        )

    result = asyncio.run(
        run_pipeline(
            summary="Patient has chronic disease history, recent worsening, and medication changes relevant to handoff.",
            source_text="Source packet shows insulin timing, oxygen dependence, and recent deterioration.",
            mode="llm",
            output_format="json",
            rubric=rubric,
            roles=roles,
            role_scorer=role_scorer,
            gap_threshold=10.0,
        )
    )

    assert "source_grounded_summary" in result
    summary = result["source_grounded_summary"]
    assert summary["wrong_patient_suspected"] is True
    assert summary["reporting_roles"] == list(CANONICAL_ROLE_IDS)

    unsupported_by_text = {entry["text"]: entry["reporting_roles"] for entry in summary["unsupported_claims"]}
    assert unsupported_by_text["claim A"] == ["physician"]
    assert sorted(unsupported_by_text["shared claim"]) == ["physician", "triage_nurse"]

    contradicted_by_text = {entry["text"]: entry["reporting_roles"] for entry in summary["contradicted_claims"]}
    assert sorted(contradicted_by_text["summary says no anticoagulation"]) == ["physician", "triage_nurse"]

    omitted_by_text = {entry["text"]: entry["reporting_roles"] for entry in summary["omitted_safety_facts"]}
    assert sorted(omitted_by_text["missed insulin"]) == ["bedside_nurse", "physician"]
    assert omitted_by_text["oxygen dependence not noted"] == ["bedside_nurse"]


def test_source_grounded_summary_absent_when_no_signals() -> None:
    rubric, roles = _load_config()
    fixed_scores = {dim: 3 for dim in DIMENSION_IDS}

    def role_scorer(summary, role, rubric):
        return _make_agent(role.id, fixed_scores, overall=3.0)

    result = asyncio.run(
        run_pipeline(
            summary="Patient has chronic disease history and recent changes relevant to handoff.",
            mode="heuristic",
            output_format="json",
            rubric=rubric,
            roles=roles,
            role_scorer=role_scorer,
            gap_threshold=10.0,
        )
    )

    assert "source_grounded_summary" not in result


def test_source_grounded_adjudication_updates_final_signals() -> None:
    rubric, roles = _load_config()

    per_role_scores = {
        "physician": {dim: 3 for dim in DIMENSION_IDS},
        "triage_nurse": {dim: 3 for dim in DIMENSION_IDS},
        "bedside_nurse": {dim: 3 for dim in DIMENSION_IDS},
    }
    per_role_scores["physician"]["factual_accuracy"] = 5
    per_role_scores["triage_nurse"]["factual_accuracy"] = 3
    per_role_scores["bedside_nurse"]["factual_accuracy"] = 2

    initial_signals = {
        role_id: {
            "wrong_patient_suspected": False,
            "unsupported_claims": [],
            "contradicted_claims": [],
            "omitted_safety_facts": [],
        }
        for role_id in CANONICAL_ROLE_IDS
    }
    updated_signals = {
        "physician": {
            "wrong_patient_suspected": True,
            "unsupported_claims": ["summary says no oxygen requirement"],
            "contradicted_claims": ["summary says no insulin use"],
            "omitted_safety_facts": ["missed q8h insulin"],
        },
        "triage_nurse": {
            "wrong_patient_suspected": True,
            "unsupported_claims": ["summary says no oxygen requirement"],
            "contradicted_claims": ["summary says no insulin use"],
            "omitted_safety_facts": [],
        },
        "bedside_nurse": {
            "wrong_patient_suspected": False,
            "unsupported_claims": [],
            "contradicted_claims": [],
            "omitted_safety_facts": ["missed q8h insulin", "oxygen dependence not noted"],
        },
    }

    def gap_scorer(summary, role, rubric, source_text=None):
        return AgentScore(
            role_id=role.id,
            scores=per_role_scores[role.id],
            rationales={dim: "ok" for dim in DIMENSION_IDS},
            overall_score=3.0,
            source_grounded_signals=initial_signals[role.id],
        )

    def adjudicator_spy(**kwargs):
        disputed_dims = kwargs["disputed_dims"]
        return {
            role_id: {
                "scores": {dim: 2 for dim in disputed_dims},
                "rationales": {dim: "revised" for dim in disputed_dims},
                "source_grounded_signals": updated_signals[role_id],
            }
            for role_id in CANONICAL_ROLE_IDS
        }

    result = asyncio.run(
        run_pipeline(
            summary="Patient has chronic disease history, recent worsening, and medication changes relevant to handoff.",
            source_text="Source packet shows insulin timing, oxygen dependence, and recent deterioration over 24 hours.",
            mode="llm",
            output_format="json",
            rubric=rubric,
            roles=roles,
            role_scorer=gap_scorer,
            adjudicator=adjudicator_spy,
            gap_threshold=0.5,
            max_retries=2,
        )
    )

    by_role = {card["role_id"]: card for card in result["per_role_scorecards"]}
    assert by_role["physician"]["source_grounded_signals"]["wrong_patient_suspected"] is True
    assert by_role["physician"]["source_grounded_signals"]["unsupported_claims"] == [
        "summary says no oxygen requirement"
    ]
    assert by_role["physician"]["source_grounded_signals"]["contradicted_claims"] == [
        "summary says no insulin use"
    ]

    summary = result["source_grounded_summary"]
    assert summary["wrong_patient_suspected"] is True
    contradicted_by_text = {entry["text"]: entry["reporting_roles"] for entry in summary["contradicted_claims"]}
    assert sorted(contradicted_by_text["summary says no insulin use"]) == ["physician", "triage_nurse"]
    omitted_by_text = {entry["text"]: entry["reporting_roles"] for entry in summary["omitted_safety_facts"]}
    assert sorted(omitted_by_text["missed q8h insulin"]) == ["bedside_nurse", "physician"]


def test_source_grounded_meta_reports_truncation() -> None:
    rubric, roles = _load_config()
    fixed_scores = {dim: 3 for dim in DIMENSION_IDS}
    valid_signals = {
        "wrong_patient_suspected": False,
        "unsupported_claims": [],
        "contradicted_claims": [],
        "omitted_safety_facts": [],
    }

    def role_scorer(summary, role, rubric, source_text=None):
        return AgentScore(
            role_id=role.id,
            scores=fixed_scores,
            rationales={dim: "ok" for dim in DIMENSION_IDS},
            overall_score=3.0,
            source_grounded_signals=valid_signals,
        )

    result = asyncio.run(
        run_pipeline(
            summary="Patient has chronic disease history, recent worsening, and medication changes relevant to handoff.",
            source_text="x" * 120,
            mode="llm",
            output_format="json",
            rubric=rubric,
            roles=roles,
            role_scorer=role_scorer,
            gap_threshold=10.0,
            max_source_chars=40,
        )
    )

    assert result["meta"]["source_truncated"] is True
    assert result["meta"]["source_original_chars"] == 120
    assert result["meta"]["source_used_chars"] == 40
    assert result["meta"]["source_max_chars"] == 40


def test_default_adjudicator_uses_prepared_source_text(monkeypatch: pytest.MonkeyPatch) -> None:
    rubric, _ = _load_config()
    captured = {}

    scorecards_by_role_id = {
        role_id: {
            "scores": {dim: 3.0 for dim in DIMENSION_IDS},
            "rationales": {dim: "ok" for dim in DIMENSION_IDS},
            "overall": 3.0,
            "source_grounded_signals": {
                "wrong_patient_suspected": False,
                "unsupported_claims": [],
                "contradicted_claims": [],
                "omitted_safety_facts": [],
            },
        }
        for role_id in CANONICAL_ROLE_IDS
    }

    monkeypatch.setattr(
        "grading_pipeline.orchestrator.create_response",
        lambda **kwargs: captured.update(kwargs) or {"ok": True},
    )
    monkeypatch.setattr(
        "grading_pipeline.orchestrator.extract_json_output",
        lambda response: {
            "updates": {
                role_id: {
                    "scores": {"factual_accuracy": 3},
                    "rationales": {"factual_accuracy": "ok"},
                    "source_grounded_signals": {
                        "wrong_patient_suspected": False,
                        "unsupported_claims": [],
                        "contradicted_claims": [],
                        "omitted_safety_facts": [],
                    },
                }
                for role_id in CANONICAL_ROLE_IDS
            }
        },
    )

    _default_adjudicator(
        summary="Patient summary for adjudication testing.",
        source_text="y" * 80,
        rubric=rubric,
        scorecards_by_role_id=scorecards_by_role_id,
        disputed_dims=["factual_accuracy"],
        model="test-model",
        max_source_chars=20,
    )

    payload = __import__("json").loads(captured["input_text"])
    assert payload["source_grounding_meta"]["source_truncated"] is True
    assert payload["source_grounding_meta"]["source_original_chars"] == 80
    assert payload["source_grounding_meta"]["source_used_chars"] == 20
    assert "source truncated to first 20 characters" in payload["source_text"]


def test_run_pipeline_reports_role_failure_context() -> None:
    rubric, roles = _load_config()

    def role_scorer(summary, role, rubric):
        if role.id == "triage_nurse":
            raise RuntimeError("mock scorer failure")
        return _make_agent(role.id, {dim: 3 for dim in DIMENSION_IDS}, overall=3.0)

    with pytest.raises(RuntimeError, match="triage_nurse"):
        asyncio.run(
            run_pipeline(
                summary="Patient has chronic disease history, medication changes, and enough detail for ED handoff scoring.",
                mode="llm",
                output_format="json",
                rubric=rubric,
                roles=roles,
                role_scorer=role_scorer,
                gap_threshold=10.0,
            )
        )
