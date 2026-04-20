"""LLM-based scoring engine using the OpenAI Responses API.

Builds role-specific prompts from persona + profile + rubric, sends them
to OpenAI with a strict JSON schema, and parses the structured response
into an ``AgentScore``.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

from .config import RoleProfile, Rubric
from .openai_client import OpenAIClientError, create_response, extract_json_output
from .scoring import AgentScore, compute_overall_score


def _build_score_schema(rubric: Rubric) -> Dict[str, Any]:
    """Build the JSON schema that constrains the model's output format."""
    score_props: Dict[str, Any] = {}
    rationale_props: Dict[str, Any] = {}
    evidence_props: Dict[str, Any] = {}
    for dim in rubric.dimensions:
        score_props[dim.id] = {
            "type": "integer",
            "minimum": 1,
            "maximum": 5,
        }
        rationale_props[dim.id] = {"type": "string"}
        evidence_props[dim.id] = {
            "type": "array",
            "maxItems": 3,
            "items": {"type": "string"},
        }

    required_dims = [dim.id for dim in rubric.dimensions]
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["role_id", "score", "rationales", "evidence"],
        "properties": {
            "role_id": {"type": "string"},
            "score": {
                "type": "object",
                "additionalProperties": False,
                "required": required_dims,
                "properties": score_props,
            },
            "rationales": {
                "type": "object",
                "additionalProperties": False,
                "required": required_dims,
                "properties": rationale_props,
            },
            "evidence": {
                "type": "object",
                "additionalProperties": False,
                "required": required_dims,
                "properties": evidence_props,
            },
        },
    }


def _role_profile_json(role: RoleProfile) -> str:
    if not role.prompt_profile:
        return "{}"
    return json.dumps(role.prompt_profile, ensure_ascii=True, indent=2, sort_keys=True)


def _build_instructions(
    role: RoleProfile, rubric: Rubric, source_text: str | None = None
) -> str:
    lines = [
        "You are scoring a clinical summary for ED handoff.",
        f"Role: {role.name}",
        f"Persona: {role.persona}",
        "Use the role profile JSON below as an authoritative scoring lens.",
    ]

    if source_text is None:
        lines.extend(
            [
                "Evaluation mode: summary-only.",
                "Only use information explicitly present in the summary. Do not infer missing details.",
                "Do not reward brevity if clinically important information appears to have been omitted or generalized away.",
                "A shorter summary is not better if chronology, chronic problem coverage, recent changes, or decision-relevant detail are weakened.",
                "High scores for clarity or focus require preservation of clinically essential content, not just clean wording.",
                "",
            ]
        )
    else:
        lines.extend(
            [
                "Evaluation mode: source-grounded.",
                "Compare the summary against the provided source record or source packet.",
                "Penalize unsupported claims, contradictions, wrong-patient mismatch, and omission of clinically important source information.",
                "If the summary appears to describe a different patient than the source, factual_accuracy and usefulness_for_decision_making must be very low.",
                "If explicit clinically important source evidence is omitted, the corresponding dimension should not receive a high score.",
                "If safety-critical source details are missing (for example medication timing, oxygen or device dependence, anticoagulation or insulin, allergy, code status, recent deterioration, or urgent follow-up), usefulness_for_decision_making must be <= 2.",
                "Do not reward clarity or brevity when they are achieved by omitting clinically important source information.",
                "",
            ]
        )

    lines.extend(
        [
            "Global scoring anchors (apply per dimension):",
            "- 5: Multiple explicit details directly satisfy the dimension with minimal gaps.",
            "- 4: Clear evidence with small omissions.",
            "- 3: Partial evidence with important omissions or ambiguity.",
            "- 2: Weak evidence; mostly missing.",
            "- 1: No evidence or misleading content.",
            "",
            "Hard constraints:",
            "1) If explicit evidence for a dimension is missing, score must be <= 2.",
            "2) Apply high_priority_dimensions more strictly than lower_priority_dimensions.",
            "3) Enforce must_have_signals and strict_downgrade_rules from the role profile.",
            "4) If undecided between two values, choose the lower score.",
            "5) Output integer scores only (1-5).",
            "6) Provide a brief rationale per dimension and 1-3 short evidence bullets grounded in the summary or source.",
            "",
            "Role profile JSON:",
            _role_profile_json(role),
            "",
            "Rubric dimensions:",
        ]
    )

    for dim in rubric.dimensions:
        lines.append(
            f"- {dim.id}: {dim.name}. Definition: {dim.definition} Focus: {dim.evaluation_focus}"
        )

    lines.append("")
    lines.append("Return only JSON that matches the provided schema.")
    return "\n".join(lines)


def _build_model_input(summary: str, source_text: str | None = None) -> str:
    if source_text is None:
        return summary
    return "\n\n".join(
        [
            "SOURCE RECORD:\n" + source_text,
            "SUMMARY TO GRADE:\n" + summary,
        ]
    )


def _extract_required_mapping(data: Dict[str, Any], key: str) -> Dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        raise OpenAIClientError(f"Model output missing '{key}' object.")
    return value


def _normalize_rationales(rationales: Dict[str, Any], dimension_ids: List[str]) -> Dict[str, str]:
    normalized: Dict[str, str] = {}
    for dim_id in dimension_ids:
        value = rationales.get(dim_id)
        if value is None:
            raise OpenAIClientError(f"Missing rationale for dimension: {dim_id}")
        normalized[dim_id] = str(value)
    return normalized


def _normalize_evidence(evidence: Dict[str, Any], dimension_ids: List[str]) -> Dict[str, List[str]]:
    normalized: Dict[str, List[str]] = {}
    for dim_id in dimension_ids:
        value = evidence.get(dim_id)
        if value is None:
            raise OpenAIClientError(f"Missing evidence list for dimension: {dim_id}")
        if not isinstance(value, list):
            raise OpenAIClientError(f"Evidence for {dim_id} must be a list.")
        normalized[dim_id] = [str(item) for item in value]
    return normalized


def score_summary_llm(
    summary: str,
    role: RoleProfile,
    rubric: Rubric,
    *,
    source_text: str | None = None,
    model: str = "gpt-4o-mini",
    temperature: float = 0.2,
) -> AgentScore:
    """Score a clinical summary using an LLM via the OpenAI Responses API."""
    schema = _build_score_schema(rubric)
    instructions = _build_instructions(role, rubric, source_text=source_text)

    response = create_response(
        model=model,
        instructions=instructions,
        input_text=_build_model_input(summary, source_text=source_text),
        json_schema=schema,
        temperature=temperature,
    )

    data = extract_json_output(response)

    scores = data.get("score") or data.get("scores")
    if not isinstance(scores, dict):
        raise OpenAIClientError("Model output missing 'score' object.")

    normalized_scores: Dict[str, int] = {}
    for dim_id in rubric.dimension_ids:
        value = scores.get(dim_id)
        if value is None:
            raise OpenAIClientError(f"Missing score for dimension: {dim_id}")
        try:
            normalized_scores[dim_id] = int(value)
        except (TypeError, ValueError) as exc:
            raise OpenAIClientError(f"Invalid score for {dim_id}: {value}") from exc
        if normalized_scores[dim_id] < 1 or normalized_scores[dim_id] > 5:
            raise OpenAIClientError(
                f"Out-of-range score for {dim_id}: {normalized_scores[dim_id]}"
            )

    normalized_rationales = _normalize_rationales(
        _extract_required_mapping(data, "rationales"), rubric.dimension_ids
    )
    normalized_evidence = _normalize_evidence(
        _extract_required_mapping(data, "evidence"), rubric.dimension_ids
    )

    overall = compute_overall_score(normalized_scores, role.w_prior, rubric.dimension_ids)

    return AgentScore(
        role_id=role.id,
        scores=normalized_scores,
        rationales=normalized_rationales,
        evidence=normalized_evidence,
        overall_score=overall,
    )
