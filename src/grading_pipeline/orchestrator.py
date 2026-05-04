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
import copy
import hashlib
import json
import inspect
from statistics import mean
from typing import Any, Callable, Dict, List

from .config import RoleProfile, Rubric
from .llm_scoring import (
    DEFAULT_MAX_SOURCE_CHARS,
    prepare_source_text,
    score_summary_llm,
)
from .openai_client import OpenAIClientError, create_response, extract_json_output
from .scoring import (
    AgentScore,
    compute_overall_score,
    normalize_source_grounded_signals,
    score_summary_heuristic,
)
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



def _retry_delay_seconds(attempt: int) -> float:
    """Deterministic exponential backoff for retryable LLM failures."""
    return min(0.5 * (2 ** max(0, attempt - 1)), 4.0)


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
    if agent.source_grounded_signals is not None:
        scorecard["source_grounded_signals"] = dict(agent.source_grounded_signals)
    return scorecard


def _validate_scorecard(
    scorecard: Dict[str, Any], *, require_source_grounded_signals: bool = False
) -> List[str]:
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

    evidence = scorecard.get("evidence")
    if evidence is not None:
        if not isinstance(evidence, dict):
            errors.append("evidence must be an object when present")
        else:
            for dim in DIMENSION_IDS:
                if dim not in evidence:
                    errors.append(f"missing evidence for dimension '{dim}'")
                    continue
                value = evidence[dim]
                if not isinstance(value, list):
                    errors.append(f"evidence for '{dim}' must be a list")
                    continue
                for item in value:
                    if not isinstance(item, str) or not item.strip():
                        errors.append(f"evidence for '{dim}' must contain non-empty strings")
                        break

    signals = scorecard.get("source_grounded_signals")
    if require_source_grounded_signals and signals is None:
        errors.append("source_grounded_signals must exist for source-grounded runs")
    elif signals is not None:
        try:
            normalize_source_grounded_signals(signals)
        except ValueError as exc:
            errors.append(str(exc))

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
    max_source_chars: int = DEFAULT_MAX_SOURCE_CHARS,
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
    evidence_props = {
        dim: {
            "type": "array",
            "minItems": 1,
            "maxItems": 3,
            "items": {"type": "string", "minLength": 1},
        }
        for dim in disputed_dims
    }

    source_signal_schema = {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "wrong_patient_suspected",
            "unsupported_claims",
            "contradicted_claims",
            "omitted_safety_facts",
        ],
        "properties": {
            "wrong_patient_suspected": {"type": "boolean"},
            "unsupported_claims": {
                "type": "array",
                "maxItems": 5,
                "items": {"type": "string"},
            },
            "contradicted_claims": {
                "type": "array",
                "maxItems": 5,
                "items": {"type": "string"},
            },
            "omitted_safety_facts": {
                "type": "array",
                "maxItems": 5,
                "items": {"type": "string"},
            },
        },
    }

    role_update_required = ["scores", "rationales", "evidence"]
    role_update_properties = {
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
        "evidence": {
            "type": "object",
            "additionalProperties": False,
            "required": disputed_dims,
            "properties": evidence_props,
        },
    }
    if source_text is not None:
        role_update_required.append("source_grounded_signals")
        role_update_properties["source_grounded_signals"] = source_signal_schema

    role_update_schema = {
        "type": "object",
        "additionalProperties": False,
        "required": role_update_required,
        "properties": role_update_properties,
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
    prepared_source = (
        prepare_source_text(source_text, max_chars=max_source_chars)
        if source_text is not None
        else None
    )
    adjudication_input = {
        "summary": summary,
        "source_text": prepared_source.text if prepared_source is not None else None,
        "source_grounding_meta": (
            {
                "source_original_chars": prepared_source.original_chars,
                "source_used_chars": prepared_source.kept_chars,
                "source_truncated": prepared_source.truncated,
                "source_max_chars": prepared_source.max_chars,
            }
            if prepared_source is not None
            else None
        ),
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
            "Also return updated source_grounded_signals for each role so the final safety summary matches the final adjudicated judgment, including unsupported vs contradicted claims.",
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
        if "evidence" not in role_update and "evidence" in scorecards_by_role_id[role_id]:
            raise OpenAIClientError(
                f"Adjudication update for role '{role_id}' is missing evidence for disputed dimensions.",
                retryable=False,
            )
        score_updates = role_update.get("scores", {})
        rationale_updates = role_update.get("rationales", {})
        evidence_updates = role_update.get("evidence", {})

        for dim in disputed_dims:
            if dim in score_updates:
                scorecards_by_role_id[role_id]["scores"][dim] = float(score_updates[dim])
            if dim in rationale_updates:
                scorecards_by_role_id[role_id]["rationales"][dim] = str(
                    rationale_updates[dim]
                )
            if dim in evidence_updates and "evidence" in scorecards_by_role_id[role_id]:
                scorecards_by_role_id[role_id]["evidence"][dim] = [
                    str(item).strip() for item in evidence_updates[dim] if str(item).strip()
                ]

        if "source_grounded_signals" in role_update:
            scorecards_by_role_id[role_id]["source_grounded_signals"] = (
                normalize_source_grounded_signals(role_update["source_grounded_signals"])
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

    if "source_grounded_signals" in repaired_scorecard:
        target_scorecard["source_grounded_signals"] = dict(
            repaired_scorecard["source_grounded_signals"]
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


def _aggregate_source_grounded_signals(
    scorecards_by_role_id: Dict[str, Dict[str, Any]],
) -> Dict[str, Any] | None:
    """Union per-role structured safety signals into a pipeline-level summary."""
    wrong_patient_any = False
    unsupported_seen: Dict[str, List[str]] = {}
    contradicted_seen: Dict[str, List[str]] = {}
    omitted_seen: Dict[str, List[str]] = {}
    reporting_roles: List[str] = []

    for role_id in CANONICAL_ROLE_IDS:
        signals = scorecards_by_role_id[role_id].get("source_grounded_signals")
        if not isinstance(signals, dict):
            continue
        reporting_roles.append(role_id)
        if bool(signals.get("wrong_patient_suspected")):
            wrong_patient_any = True
        for claim in signals.get("unsupported_claims", []) or []:
            text = str(claim).strip()
            if not text:
                continue
            unsupported_seen.setdefault(text, []).append(role_id)
        for claim in signals.get("contradicted_claims", []) or []:
            text = str(claim).strip()
            if not text:
                continue
            contradicted_seen.setdefault(text, []).append(role_id)
        for fact in signals.get("omitted_safety_facts", []) or []:
            text = str(fact).strip()
            if not text:
                continue
            omitted_seen.setdefault(text, []).append(role_id)

    if not reporting_roles:
        return None

    return {
        "wrong_patient_suspected": wrong_patient_any,
        "unsupported_claims": [
            {"text": text, "reporting_roles": roles}
            for text, roles in unsupported_seen.items()
        ],
        "contradicted_claims": [
            {"text": text, "reporting_roles": roles}
            for text, roles in contradicted_seen.items()
        ],
        "omitted_safety_facts": [
            {"text": text, "reporting_roles": roles}
            for text, roles in omitted_seen.items()
        ],
        "reporting_roles": reporting_roles,
    }


def _canonical_json_sha256(payload: Any) -> str:
    rendered = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",",":"))
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


def _rubric_provenance(rubric: Rubric) -> Dict[str, Any]:
    payload = {
        "rubric_id": rubric.rubric_id,
        "dimensions": [
            {
                "id": dim.id,
                "name": dim.name,
                "definition": dim.definition,
                "evaluation_focus": dim.evaluation_focus,
            }
            for dim in rubric.dimensions
        ],
    }
    return {
        "rubric_id": rubric.rubric_id,
        "rubric_sha256": _canonical_json_sha256(payload),
    }


def _roles_provenance(roles_by_id: Dict[str, RoleProfile]) -> Dict[str, Any]:
    role_payloads = []
    prompt_profile_sha256_by_role: Dict[str, str] = {}
    for role_id in CANONICAL_ROLE_IDS:
        role = roles_by_id[role_id]
        prompt_profile_sha256_by_role[role_id] = _canonical_json_sha256(role.prompt_profile)
        role_payloads.append(
            {
                "id": role.id,
                "name": role.name,
                "persona": role.persona,
                "w_prior": role.w_prior,
                "prompt_profile": role.prompt_profile,
            }
        )
    return {
        "role_ids": CANONICAL_ROLE_IDS,
        "roles_sha256": _canonical_json_sha256(role_payloads),
        "prompt_profile_sha256_by_role": prompt_profile_sha256_by_role,
    }


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
    gap_threshold: float = 1.0,
    source_text: str | None = None,
    max_source_chars: int = DEFAULT_MAX_SOURCE_CHARS,
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
        ``initial_disagreement_map``, ``pre_adjudication_scorecards``,
        ``disputed_dimensions``, ``adjudication_ran``,
        ``overall_across_roles``, ``meta``.
    """
    if mode not in {"llm", "heuristic"}:
        raise ValueError(f"Unsupported mode: {mode}")

    checked_summary = validate_summary_text(summary)
    checked_source = validate_source_text(source_text) if source_text is not None else None
    source_prep = (
        prepare_source_text(checked_source, max_chars=max_source_chars, emit_warning=False)
        if checked_source is not None
        else None
    )
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
                max_source_chars=max_source_chars,
            )
        return score_summary_heuristic(input_summary, role, input_rubric)

    async def run_role(role: RoleProfile) -> AgentScore:
        attempt = 0
        while True:
            try:
                return await asyncio.to_thread(score_once, checked_summary, role, rubric)
            except OpenAIClientError as exc:
                if not getattr(exc, "retryable", False):
                    raise RuntimeError(
                        f"Role '{role.id}' scoring failed without retry because the error is non-retryable: {exc}"
                    ) from exc
                attempt += 1
                if attempt > max_retries:
                    raise RuntimeError(
                        f"Role '{role.id}' LLM scoring failed after {attempt} attempts: {exc}"
                    ) from exc
                await asyncio.sleep(_retry_delay_seconds(attempt))
            except Exception as exc:
                raise RuntimeError(f"Role '{role.id}' scoring failed: {exc}") from exc

    initial_results = await asyncio.gather(
        *(run_role(roles_by_id[role_id]) for role_id in CANONICAL_ROLE_IDS),
        return_exceptions=True,
    )
    role_failures = []
    for role_id, result in zip(CANONICAL_ROLE_IDS, initial_results):
        if isinstance(result, Exception):
            role_failures.append(f"{role_id}: {result}")
    if role_failures:
        raise RuntimeError("Role scoring failed: " + "; ".join(role_failures))

    initial_agents = list(initial_results)
    scorecards_by_role_id = {
        role_id: _agent_to_scorecard(agent, roles_by_id[role_id])
        for role_id, agent in zip(CANONICAL_ROLE_IDS, initial_agents)
    }

    for role_id in CANONICAL_ROLE_IDS:
        retries = 0
        while True:
            errors = _validate_scorecard(
                scorecards_by_role_id[role_id],
                require_source_grounded_signals=checked_source is not None,
            )
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

    pre_adjudication_scorecards = [
        copy.deepcopy(scorecards_by_role_id[role_id]) for role_id in CANONICAL_ROLE_IDS
    ]
    initial_disagreement_map = build_disagreement_map(scorecards_by_role_id, gap_threshold)
    disputed_dims = [
        dim for dim, item in initial_disagreement_map.items() if item["flag"]
    ]

    adjudication_ran = False
    if mode == "llm" and disputed_dims:
        adjudication_ran = True

        try:
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
                    max_source_chars=max_source_chars,
                )
        except Exception as exc:
            raise RuntimeError(f"Adjudication failed: {exc}") from exc

        _apply_adjudication_updates(scorecards_by_role_id, updates, disputed_dims)

        for role_id in CANONICAL_ROLE_IDS:
            retries = 0
            while True:
                errors = _validate_scorecard(
                    scorecards_by_role_id[role_id],
                    require_source_grounded_signals=checked_source is not None,
                )
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
    source_grounded_summary = _aggregate_source_grounded_signals(scorecards_by_role_id)

    per_role_scorecards = [
        scorecards_by_role_id[role_id] for role_id in CANONICAL_ROLE_IDS
    ]

    result: Dict[str, Any] = {
        "pre_adjudication_scorecards": pre_adjudication_scorecards,
        "initial_disagreement_map": initial_disagreement_map,
        "disputed_dimensions": disputed_dims,
        "per_role_scorecards": per_role_scorecards,
        "disagreement_map": disagreement_map,
        "adjudication_ran": adjudication_ran,
        "overall_across_roles": overall_across_roles,
    }
    if source_grounded_summary is not None:
        result["source_grounded_summary"] = source_grounded_summary
    rubric_meta = _rubric_provenance(rubric)
    roles_meta = _roles_provenance(roles_by_id)
    result["meta"] = {
        "version": "orchestrator_v1",
        "mode": mode,
        "output_format": output_format,
        "gap_threshold": gap_threshold,
        "max_retries": max_retries,
        "scoring_model": model,
        "adjudicator_model": effective_adjudicator_model if adjudication_ran else None,
        "temperature": temperature if mode == "llm" else None,
        "max_source_chars": max_source_chars,
        "evaluation_context": "source_grounded" if checked_source is not None else "summary_only",
        "initial_disputed_dimensions_count": len(disputed_dims),
        "source_text_provided": checked_source is not None,
        "source_truncated": source_prep.truncated if source_prep is not None else False,
        "source_original_chars": source_prep.original_chars if source_prep is not None else None,
        "source_used_chars": source_prep.kept_chars if source_prep is not None else None,
        "source_max_chars": source_prep.max_chars if source_prep is not None else None,
        **rubric_meta,
        **roles_meta,
    }
    return result
