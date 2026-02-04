from __future__ import annotations

from typing import Any, Dict

from .config import RoleProfile, Rubric
from .openai_client import OpenAIClientError, create_response, extract_json_output
from .scoring import AgentScore, compute_overall_score


def _build_score_schema(rubric: Rubric) -> Dict[str, Any]:
    score_props: Dict[str, Any] = {}
    for dim in rubric.dimensions:
        score_props[dim.id] = {
            "type": "integer",
            "minimum": 1,
            "maximum": 5,
        }

    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["role_id", "score"],
        "properties": {
            "role_id": {"type": "string"},
            "score": {
                "type": "object",
                "additionalProperties": False,
                "required": [dim.id for dim in rubric.dimensions],
                "properties": score_props,
            },
        },
    }


def _build_instructions(role: RoleProfile, rubric: Rubric) -> str:
    lines = [
        "You are scoring a clinical summary for ED handoff.",
        f"Role: {role.name}. Persona: {role.persona}",
        "Score each dimension from 1 to 5 (integers). 1 = poor, 5 = excellent.",
        "Only use information explicitly present in the summary.",
        "Return only JSON that matches the provided schema.",
        "Dimensions:",
    ]
    for dim in rubric.dimensions:
        lines.append(
            f"- {dim.id}: {dim.name}. {dim.definition} Evaluation focus: {dim.evaluation_focus}"
        )
    return "\n".join(lines)


def score_summary_llm(
    summary: str,
    role: RoleProfile,
    rubric: Rubric,
    *,
    model: str = "gpt-4o",
    temperature: float = 0.2,
) -> AgentScore:
    schema = _build_score_schema(rubric)
    instructions = _build_instructions(role, rubric)

    response = create_response(
        model=model,
        instructions=instructions,
        input_text=summary,
        json_schema=schema,
        temperature=temperature,
    )

    data = extract_json_output(response)

    scores = data.get("score") or data.get("scores")
    if not isinstance(scores, dict):
        raise OpenAIClientError("Model output missing 'score' object.")

    normalized: Dict[str, int] = {}
    for dim_id in rubric.dimension_ids:
        value = scores.get(dim_id)
        if value is None:
            raise OpenAIClientError(f"Missing score for dimension: {dim_id}")
        try:
            normalized[dim_id] = int(value)
        except (TypeError, ValueError) as exc:
            raise OpenAIClientError(f"Invalid score for {dim_id}: {value}") from exc

    overall = compute_overall_score(normalized, role.w_prior, rubric.dimension_ids)

    return AgentScore(
        role_id=role.id,
        scores=normalized,
        overall_score=overall,
    )
