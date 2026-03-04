import asyncio
import sys
from pathlib import Path
from statistics import mean
from typing import Dict


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from grading_pipeline.config import load_roles, load_rubric
from grading_pipeline.orchestrator import (
    CANONICAL_ROLE_IDS,
    DIMENSION_IDS,
    ROLE_NAME_BY_ID,
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

    by_role = {
        card["role_id"]: card for card in with_gap_result["per_role_scorecards"]
    }
    assert by_role["physician"]["scores"]["factual_accuracy"] == 4.0
    assert by_role["triage_nurse"]["scores"]["factual_accuracy"] == 4.0
    assert by_role["bedside_nurse"]["scores"]["factual_accuracy"] == 4.0


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
