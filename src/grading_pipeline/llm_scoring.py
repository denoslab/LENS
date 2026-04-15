"""LLM-based scoring engine using the OpenAI Responses API.

Builds role-specific prompts from persona + profile + rubric, sends them
to OpenAI with a strict JSON schema, and parses the structured response
into an ``AgentScore``.

The prompt includes global scoring anchors (1-5 scale), hard constraints
(e.g. missing evidence → score ≤ 2), and the role's full prompt profile
so the model applies role-appropriate evaluation priorities.
"""

from __future__ import annotations

import json
from typing import Any, Dict

from .config import RoleProfile, Rubric
from .openai_client import OpenAIClientError, create_response, extract_json_output
from .scoring import AgentScore, compute_overall_score


def _build_score_schema(rubric: Rubric) -> Dict[str, Any]:
    """Build the JSON schema that constrains the model's output format.

    Returns a schema requiring ``role_id`` (string) and ``score`` (object
    with one integer 1-5 field per rubric dimension).
    """
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


def _role_profile_json(role: RoleProfile) -> str:
    """Serialize the role's LLM prompt profile to a JSON string for prompt injection."""
    if not role.prompt_profile:
        return "{}"
    return json.dumps(role.prompt_profile, ensure_ascii=True, indent=2, sort_keys=True)


def _build_instructions(role: RoleProfile, rubric: Rubric) -> str:
    """Assemble the full system-level instruction prompt for a scoring call.

    Includes: role identity, persona, scoring anchors, hard constraints,
    the role's prompt profile JSON, and all rubric dimension definitions.
    """
    lines = [
        "You are scoring a clinical summary for ED handoff.",
        f"Role: {role.name}",
        f"Persona: {role.persona}",
        "Use the role profile JSON below as an authoritative scoring lens.",
        "Only use information explicitly present in the summary. Do not infer missing details.",
        "Do not reward brevity if clinically important information appears to have been omitted or generalized away.",
        "A shorter summary is not better if chronology, chronic problem coverage, recent changes, or decision-relevant detail are weakened.",
        "High scores for clarity or focus require preservation of clinically essential content, not just clean wording.",
        "",
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
        "",
        "Role profile JSON:",
        _role_profile_json(role),
        "",
        "Rubric dimensions:",
    ]

    for dim in rubric.dimensions:
        lines.append(
            f"- {dim.id}: {dim.name}. Definition: {dim.definition} Focus: {dim.evaluation_focus}"
        )

    lines.append("")
    lines.append("Return only JSON that matches the provided schema.")
    return "\n".join(lines)


def score_summary_llm(
    summary: str,
    role: RoleProfile,
    rubric: Rubric,
    *,
    model: str = "gpt-4o-mini",
    temperature: float = 0.2,
) -> AgentScore:
    """Score a clinical summary using an LLM via the OpenAI Responses API.

    Args:
        summary: The clinical summary text to evaluate.
        role: The clinical role whose perspective to apply.
        rubric: The evaluation rubric (defines which dimensions to score).
        model: OpenAI model identifier.
        temperature: Sampling temperature (lower = more deterministic).

    Returns:
        An ``AgentScore`` with per-dimension integer scores and a weighted
        overall.  Rationales are not returned by this engine (only the
        heuristic engine produces them).

    Raises:
        OpenAIClientError: If the API call fails, the response is malformed,
            or any score is missing / out of range.
    """
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

        if normalized[dim_id] < 1 or normalized[dim_id] > 5:
            raise OpenAIClientError(
                f"Out-of-range score for {dim_id}: {normalized[dim_id]}"
            )

    overall = compute_overall_score(normalized, role.w_prior, rubric.dimension_ids)

    return AgentScore(
        role_id=role.id,
        scores=normalized,
        overall_score=overall,
    )
