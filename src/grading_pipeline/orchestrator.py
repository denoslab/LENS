"""Core orchestration logic for the multi-agent grading pipeline.

Pipeline stages:
  1. **Validate** the input summary.
  2. **Parallel Score**: three clinical roles score independently via
     ``asyncio.gather()``.
  3. **Validate Scorecards**: retry any role whose output fails validation
     (missing dims, out-of-range scores, etc.).
  4. **Disagreement Map**: compute per-dimension cross-role score gaps.
  5. **Conditional Adjudication** (LLM mode only): if any gap ≥ threshold,
     an adjudicator LLM refines disputed dimensions.
  6. **Aggregate**: compute per-role weighted overalls and cross-role mean.
  7. **Return** structured result dict.
"""

from __future__ import annotations

import asyncio
import json
import inspect
from statistics import mean
from typing import Any, Callable, Dict, List

from .config import RoleProfile, Rubric
from .llm_scoring import score_summary_llm
from .openai_client import OpenAIClientError, create_response, extract_json_output
from .scoring import AgentScore, compute_overall_score, score_summary_heuristic
from .validation import validate_source_text, validate_summary_text

# The 8 canonical rubric dimension IDs, in display order.
DIMENSION_IDS = [
    "factual_accuracy",
    "relevant_chronic_problem_coverage",
    "organized_by_condition",
    "timeline_evolution",
    "recent_changes_highlighted",
    "focused_not_cluttered",
    "usefulness_for_decision_making",
    "clarity_readability_formatting",
]

ROLE_NAME_BY_ID = {
    "physician": "Physician",
    "triage_nurse": "Triage Nurse",
    "bedside_nurse": "Bedside Nurse",
}

CANONICAL_ROLE_IDS = ["physician", "triage_nurse", "bedside_nurse"]


def _normalize_weights(weights: Dict[str, float]) -> Dict[str, float]:
    """Clip weights to ≥0 and normalize to sum to 1.  Falls back to uniform if all zero."""
    clipped = {dim: max(0.0, float(weights.get(dim, 0.0))) for dim in DIMENSION_IDS}
    total = sum(clipped.values())
    if total <= 0.0:
        return {dim: 1.0 / len(DIMENSION_IDS) for dim in DIMENSION_IDS}
    return {dim: value / total for dim, value in clipped.items()}


def calibrate_weights(
    w_prior: Dict[str, float], delta_w: Dict[str, float] | None = None
) -> Dict[str, float]:
    """Combine prior weights with an optional delta adjustment and normalize.

    Note: ``delta_w`` is currently a no-op stub (always zeros).  It exists
    as a hook for future weight calibration logic.
    """
    if delta_w is None:
        delta_w = {dim: 0.0 for dim in DIMENSION_IDS}

    combined = {
        dim: float(w_prior.get(dim, 0.0)) + float(delta_w.get(dim, 0.0))
        for dim in DIMENSION_IDS
    }
    return _normalize_weights(combined)


def _to_role_name(role: RoleProfile) -> str:
    """Map a RoleProfile to its human-readable display name."""
    return ROLE_NAME_BY_ID.get(role.id, role.name.replace(" Agent", ""))


def _agent_to_scorecard(agent: AgentScore, role: RoleProfile) -> Dict[str, Any]:
    """Convert an ``AgentScore`` into the mutable scorecard dict used internally.

    The scorecard format has keys: role, role_id, scores, rationales, overall,
    and optionally evidence.
    """
    rationales = agent.rationales or {dim: "" for dim in DIMENSION_IDS}
    scorecard = {
        "role": _to_role_name(role),
        "role_id": role.id,
        "scores": {dim: float(agent.scores[dim]) for dim in DIMENSION_IDS},
        "rationales": {dim: str(rationales.get(dim, "")) for dim in DIMENSION_IDS},
        "overall": float(agent.overall_score) if agent.overall_score is not None else None,
    }
    if agent.evidence is not None:
        scorecard["evidence"] = {
            dim: list(agent.evidence.get(dim, [])) for dim in DIMENSION_IDS
        }
    return scorecard


def _validate_scorecard(scorecard: Dict[str, Any]) -> List[str]:
    """Validate a scorecard dict, returning a list of error strings (empty = valid).

    Checks: recognized role name, all 8 dimensions present with numeric
    scores in [1, 5], all rationales present as strings, and overall in [1, 5].
    """
    errors: List[str] = []

    role_name = scorecard.get("role")
    if role_name not in set(ROLE_NAME_BY_ID.values()):
        errors.append(
            f"role must be one of {sorted(ROLE_NAME_BY_ID.values())}, got {role_name}"
        )

    scores = scorecard.get("scores")
    if not isinstance(scores, dict):
        errors.append("scores must exist as an object")
    else:
        for dim in DIMENSION_IDS:
            if dim not in scores:
                errors.append(f"missing score for dimension '{dim}'")
                continue
            value = scores[dim]
            if not isinstance(value, (int, float)):
                errors.append(f"score for '{dim}' must be numeric")
                continue
            if value < 1 or value > 5:
                errors.append(f"score for '{dim}' must be within [1, 5], got {value}")

    rationales = scorecard.get("rationales")
    if not isinstance(rationales, dict):
        errors.append("rationales must exist as an object")
    else:
        for dim in DIMENSION_IDS:
            if dim not in rationales:
                errors.append(f"missing rationale for dimension '{dim}'")
                continue
            if not isinstance(rationales[dim], str):
                errors.append(f"rationale for '{dim}' must be a string")

    overall = scorecard.get("overall")
    if not isinstance(overall, (int, float)):
        errors.append("overall must exist and be numeric")
    elif overall < 1 or overall > 5:
        errors.append(f"overall must be within [1, 5], got {overall}")

    return errors


def build_disagreement_map(
    scorecards_by_role_id: Dict[str, Dict[str, Any]], gap_threshold: float
) -> Dict[str, Dict[str, Any]]:
    """Build a per-dimension disagreement map across the three roles.

    For each dimension, computes the score gap (max - min) and flags
    dimensions where the gap meets or exceeds ``gap_threshold``.

    Returns:
        Dict mapping dimension_id → {role_scores, score_gap, flag}.
    """
    disagreement_map: Dict[str, Dict[str, Any]] = {}

    for dim in DIMENSION_IDS:
        role_scores = {
            ROLE_NAME_BY_ID[role_id]: float(scorecards_by_role_id[role_id]["scores"][dim])
            for role_id in CANONICAL_ROLE_IDS
        }
        values = list(role_scores.values())
        gap = max(values) - min(values)
        disagreement_map[dim] = {
            "role_scores": role_scores,
            "score_gap": round(gap, 4),
            "flag": gap >= gap_threshold,
        }

    return disagreement_map


def _default_adjudicator(
    *,
    summary: str,
    rubric: Rubric,
    scorecards_by_role_id: Dict[str, Dict[str, Any]],
    disputed_dims: List[str],
    model: str,
    source_text: str | None = None,
) -> Dict[str, Dict[str, Dict[str, Any]]]:
    """LLM-based adjudicator that refines scores for disputed dimensions.

    Sends the original summary, rubric subset, and all three role scorecards
    to the LLM, asking it to produce updated scores and rationales *only*
    for the disputed dimensions.  Uses temperature=0.0 for consistency.

    Returns:
        Nested dict: ``updates[role_id]["scores"|"rationales"][dim_id]``.
    """
    score_props = {
        dim: {"type": "integer", "minimum": 1, "maximum": 5} for dim in disputed_dims
    }
    rationale_props = {dim: {"type": "string"} for dim in disputed_dims}

    role_update_schema = {
        "type": "object",
        "additionalProperties": False,
        "required": ["scores", "rationales"],
        "properties": {
            "scores": {
                "type": "object",
                "additionalProperties": False,
                "required": disputed_dims,
                "properties": score_props,
            },
            "rationales": {
                "type": "object",
                "additionalProperties": False,
                "required": disputed_dims,
                "properties": rationale_props,
            },
        },
    }

    schema = {
        "type": "object",
        "additionalProperties": False,
        "required": ["updates"],
        "properties": {
            "updates": {
                "type": "object",
                "additionalProperties": False,
                "required": CANONICAL_ROLE_IDS,
                "properties": {
                    role_id: role_update_schema for role_id in CANONICAL_ROLE_IDS
                },
            }
        },
    }

    rubric_subset = [d for d in rubric.dimensions if d.id in disputed_dims]
    adjudication_input = {
        "summary": summary,
        "source_text": source_text,
        "disputed_dimensions": disputed_dims,
        "rubric": [
            {
                "id": dim.id,
                "name": dim.name,
                "definition": dim.definition,
                "evaluation_focus": dim.evaluation_focus,
            }
            for dim in rubric_subset
        ],
        "scorecards": scorecards_by_role_id,
    }

    instruction_lines = [
        "You are an adjudicator for role-aware summary grading.",
        "Refine ONLY disputed dimensions for each role.",
        "Return updates for all three roles in one response.",
        "Do not change non-disputed dimensions.",
        "Scores must remain within [1, 5].",
        "Provide concise rationales for each disputed dimension.",
    ]
    if source_text is None:
        instruction_lines.append("Use only the summary text and the disputed scorecards.")
    else:
        instruction_lines.extend([
            "This is a source-grounded adjudication task.",
            "Compare the summary against the provided source record when deciding updated scores.",
            "If the summary conflicts with the source, omits clinically important source details, or appears to describe the wrong patient, adjudicate downward accordingly.",
        ])
    instruction_lines.append("Return only JSON matching the provided schema.")
    instructions = "\n".join(instruction_lines)

    response = create_response(
        model=model,
        instructions=instructions,
        input_text=json.dumps(adjudication_input, ensure_ascii=True),
        json_schema=schema,
        temperature=0.0,
    )
    data = extract_json_output(response)

    updates = data.get("updates")
    if not isinstance(updates, dict):
        raise OpenAIClientError("Adjudicator output missing 'updates' object.")
    return updates


def _apply_adjudication_updates(
    scorecards_by_role_id: Dict[str, Dict[str, Any]],
    updates: Dict[str, Dict[str, Dict[str, Any]]],
    disputed_dims: List[str],
) -> None:
    """Merge adjudicator updates into the live scorecards (in place).

    Only overwrites disputed dimension scores and rationales; non-disputed
    dimensions are preserved unchanged.
    """
    for role_id in CANONICAL_ROLE_IDS:
        if role_id not in updates:
            continue

        role_update = updates[role_id]
        score_updates = role_update.get("scores", {})
        rationale_updates = role_update.get("rationales", {})

        for dim in disputed_dims:
            if dim in score_updates:
                scorecards_by_role_id[role_id]["scores"][dim] = float(score_updates[dim])
            if dim in rationale_updates:
                scorecards_by_role_id[role_id]["rationales"][dim] = str(
                    rationale_updates[dim]
                )


def _repair_disputed_fields(
    target_scorecard: Dict[str, Any],
    repaired_scorecard: Dict[str, Any],
    disputed_dims: List[str],
) -> None:
    """Copy disputed-dimension fields from a freshly re-scored scorecard into the target.

    Used after post-adjudication validation fails: re-score the role and
    selectively patch only the disputed dimensions, preserving non-disputed
    fields from the adjudicated result.
    """
    for dim in disputed_dims:
        target_scorecard["scores"][dim] = float(repaired_scorecard["scores"][dim])
        target_scorecard["rationales"][dim] = str(
            repaired_scorecard["rationales"].get(dim, "")
        )
        if "evidence" in target_scorecard and "evidence" in repaired_scorecard:
            target_scorecard["evidence"][dim] = list(
                repaired_scorecard["evidence"].get(dim, [])
            )


def _aggregate_role_overalls(
    scorecards_by_role_id: Dict[str, Dict[str, Any]], roles_by_id: Dict[str, RoleProfile]
) -> float:
    """Compute per-role weighted overalls and the cross-role mean.

    For each role: calibrates weights, computes weighted average across
    dimensions, and stores the result back into the scorecard.  Returns
    the mean of the three role overalls (rounded to 4 decimal places).
    """
    per_role_overalls: List[float] = []

    for role_id in CANONICAL_ROLE_IDS:
        scorecard = scorecards_by_role_id[role_id]
        role = roles_by_id[role_id]
        w_final = calibrate_weights(role.w_prior)

        score_values = {dim: float(scorecard["scores"][dim]) for dim in DIMENSION_IDS}
        role_overall = compute_overall_score(score_values, w_final, DIMENSION_IDS)

        scorecard["overall"] = role_overall
        scorecard["w_final"] = w_final
        per_role_overalls.append(role_overall)

    return round(mean(per_role_overalls), 4)


async def run_pipeline(
    summary: str,
    mode: str,
    output_format: str,
    *,
    rubric: Rubric,
    roles: List[RoleProfile],
    model: str = "gpt-4o-mini",
    adjudicator_model: str | None = None,
    temperature: float = 0.2,
    gap_threshold: float = 0.5,
    source_text: str | None = None,
    max_retries: int = 2,
    role_scorer: Callable[[str, RoleProfile, Rubric], AgentScore] | None = None,
    adjudicator: Callable[..., Dict[str, Dict[str, Dict[str, Any]]]] | None = None,
) -> Dict[str, Any]:
    """Run the full grading pipeline end-to-end.

    Args:
        summary: Raw clinical summary text.
        mode: ``"llm"`` or ``"heuristic"``.
        output_format: ``"human"`` or ``"json"`` (passed through to meta).
        rubric: Loaded rubric with dimension definitions.
        roles: List of 3 ``RoleProfile`` instances.
        model: OpenAI model ID (LLM mode only).
        temperature: Sampling temperature (LLM mode only).
        gap_threshold: Min score gap to trigger adjudication.
        max_retries: Max re-scoring attempts per role on validation failure.
        role_scorer: Optional override for the per-role scoring function
            (useful for testing without API calls).
        adjudicator: Optional override for the adjudication function.

    Returns:
        Dict with keys: ``per_role_scorecards``, ``disagreement_map``,
        ``adjudication_ran``, ``overall_across_roles``, ``meta``.
    """
    if mode not in {"llm", "heuristic"}:
        raise ValueError(f"Unsupported mode: {mode}")

    checked_summary = validate_summary_text(summary)
    checked_source = validate_source_text(source_text) if source_text is not None else None
    if checked_source is not None and mode != "llm":
        raise ValueError(
            "Source-grounded evaluation currently requires mode='llm'; heuristic mode ignores source text."
        )
    effective_adjudicator_model = adjudicator_model or model

    roles_by_id = {role.id: role for role in roles}
    missing_roles = [role_id for role_id in CANONICAL_ROLE_IDS if role_id not in roles_by_id]
    if missing_roles:
        raise ValueError(f"Missing required role configs: {missing_roles}")

    def _supports_keyword_argument(func: Callable[..., Any], keyword: str) -> bool:
        signature = inspect.signature(func)
        for param in signature.parameters.values():
            if param.kind == inspect.Parameter.VAR_KEYWORD:
                return True
            if param.name == keyword:
                return True
        return False

    scorer_supports_source = role_scorer is not None and _supports_keyword_argument(role_scorer, "source_text")
    adjudicator_supports_source = adjudicator is not None and _supports_keyword_argument(adjudicator, "source_text")

    def score_once(input_summary: str, role: RoleProfile, input_rubric: Rubric) -> AgentScore:
        if role_scorer is not None:
            if scorer_supports_source:
                return role_scorer(input_summary, role, input_rubric, source_text=checked_source)
            return role_scorer(input_summary, role, input_rubric)
        if mode == "llm":
            return score_summary_llm(
                input_summary,
                role,
                input_rubric,
                source_text=checked_source,
                model=model,
                temperature=temperature,
            )
        return score_summary_heuristic(input_summary, role, input_rubric, source_text=checked_source)

    async def run_role(role: RoleProfile) -> AgentScore:
        return await asyncio.to_thread(score_once, checked_summary, role, rubric)

    initial_agents = await asyncio.gather(
        *(run_role(roles_by_id[role_id]) for role_id in CANONICAL_ROLE_IDS)
    )

    scorecards_by_role_id = {
        role_id: _agent_to_scorecard(agent, roles_by_id[role_id])
        for role_id, agent in zip(CANONICAL_ROLE_IDS, initial_agents)
    }

    for role_id in CANONICAL_ROLE_IDS:
        retries = 0
        while True:
            errors = _validate_scorecard(scorecards_by_role_id[role_id])
            if not errors:
                break

            if retries >= max_retries:
                raise RuntimeError(
                    f"Validation failed for {role_id} after {max_retries} retries: {errors}"
                )

            retries += 1
            repaired = await run_role(roles_by_id[role_id])
            scorecards_by_role_id[role_id] = _agent_to_scorecard(
                repaired, roles_by_id[role_id]
            )

    initial_disagreement_map = build_disagreement_map(scorecards_by_role_id, gap_threshold)
    disputed_dims = [
        dim for dim, item in initial_disagreement_map.items() if item["flag"]
    ]

    adjudication_ran = False
    if mode == "llm" and disputed_dims:
        adjudication_ran = True

        if adjudicator is not None:
            adjudicator_kwargs = {
                "summary": checked_summary,
                "rubric": rubric,
                "scorecards_by_role_id": scorecards_by_role_id,
                "disputed_dims": disputed_dims,
                "model": effective_adjudicator_model,
            }
            if adjudicator_supports_source:
                adjudicator_kwargs["source_text"] = checked_source
            updates = adjudicator(**adjudicator_kwargs)
        else:
            updates = await asyncio.to_thread(
                _default_adjudicator,
                summary=checked_summary,
                source_text=checked_source,
                rubric=rubric,
                scorecards_by_role_id=scorecards_by_role_id,
                disputed_dims=disputed_dims,
                model=effective_adjudicator_model,
            )

        _apply_adjudication_updates(scorecards_by_role_id, updates, disputed_dims)

        for role_id in CANONICAL_ROLE_IDS:
            retries = 0
            while True:
                errors = _validate_scorecard(scorecards_by_role_id[role_id])
                if not errors:
                    break

                if retries >= max_retries:
                    raise RuntimeError(
                        "Validation failed after adjudication for "
                        f"{role_id} after {max_retries} retries: {errors}"
                    )

                retries += 1
                repaired = await run_role(roles_by_id[role_id])
                repaired_scorecard = _agent_to_scorecard(repaired, roles_by_id[role_id])
                _repair_disputed_fields(
                    scorecards_by_role_id[role_id],
                    repaired_scorecard,
                    disputed_dims,
                )

    disagreement_map = build_disagreement_map(scorecards_by_role_id, gap_threshold)
    overall_across_roles = _aggregate_role_overalls(scorecards_by_role_id, roles_by_id)

    per_role_scorecards = [
        scorecards_by_role_id[role_id] for role_id in CANONICAL_ROLE_IDS
    ]

    return {
        "per_role_scorecards": per_role_scorecards,
        "disagreement_map": disagreement_map,
        "adjudication_ran": adjudication_ran,
        "overall_across_roles": overall_across_roles,
        "meta": {
            "version": "orchestrator_v1",
            "mode": mode,
            "output_format": output_format,
            "gap_threshold": gap_threshold,
            "max_retries": max_retries,
            "scoring_model": model,
            "adjudicator_model": effective_adjudicator_model if adjudication_ran else None,
            "evaluation_context": "source_grounded" if checked_source is not None else "summary_only",
            "source_text_provided": checked_source is not None,
        },
    }
