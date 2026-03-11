"""Heuristic (keyword-based) scoring engine for clinical summaries.

This module provides a fast, deterministic baseline scorer that requires
no API key.  Each of the 8 rubric dimensions has its own scoring function
that inspects the summary text for keyword hits, structural markers,
sentence statistics, and word count.

Scoring flow for one role:
  1. Run all 8 dimension scorers independently.
  2. Apply role-specific adjustments (``_apply_role_adjustments``).
  3. Clamp all scores to [1, 5].
  4. Compute a weighted overall using the role's ``w_prior`` weights.

Score scale: 1 (worst) to 5 (best) per dimension.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Tuple

from .config import RoleProfile, Rubric


@dataclass(frozen=True)
class AgentScore:
    """Container for a single role's scoring output.

    Attributes:
        role_id: Which clinical role produced this score.
        scores: Mapping of dimension_id → integer score (1-5).
        rationales: Optional per-dimension textual justification.
        evidence: Optional per-dimension list of matched keywords/evidence.
        overall_notes: Free-text note about the role's perspective.
        warnings: Any warnings generated during scoring (e.g. empty input).
        overall_score: Weighted average across dimensions (computed post-scoring).
    """
    role_id: str
    scores: Dict[str, int]
    rationales: Dict[str, str] | None = None
    evidence: Dict[str, List[str]] | None = None
    overall_notes: str = ""
    warnings: List[str] | None = None
    overall_score: float | None = None

    def to_dict(self) -> Dict:
        payload = {
            "role_id": self.role_id,
            "scores": self.scores,
            "score": self.scores,
        }
        if self.rationales is not None:
            payload["rationales"] = self.rationales
        if self.evidence is not None:
            payload["evidence"] = self.evidence
        if self.overall_notes:
            payload["overall_notes"] = self.overall_notes
        if self.overall_score is not None:
            payload["overall_score"] = self.overall_score
        if self.warnings:
            payload["warnings"] = self.warnings
        return payload


# ---------------------------------------------------------------------------
# Keyword lists used by the dimension scorers.
# Each list targets a specific clinical concept.  Keywords are matched as
# whole words (word-boundary regex) to avoid false positives from substrings.
# ---------------------------------------------------------------------------

CHRONIC_KEYWORDS = [
    "diabetes",
    "hypertension",
    "copd",
    "ckd",
    "chf",
    "asthma",
    "cancer",
    "stroke",
    "afib",
    "cad",
    "heart failure",
    "renal",
]

DECISION_KEYWORDS = [
    "bp",
    "hr",
    "rr",
    "spo2",
    "oxygen",
    "o2",
    "temp",
    "vitals",
    "pain",
    "meds",
    "medications",
    "allergy",
    "allergies",
    "labs",
    "imaging",
    "ct",
    "x-ray",
    "ekg",
    "ecg",
]

TEMPORAL_KEYWORDS = [
    "today",
    "yesterday",
    "last",
    "recent",
    "since",
    "weeks",
    "days",
    "months",
    "years",
    "ago",
    "admitted",
    "discharged",
]

RECENT_CHANGE_KEYWORDS = [
    "new",
    "recent",
    "started",
    "stopped",
    "changed",
    "adjusted",
    "admitted",
    "discharged",
    "ed visit",
    "surgery",
]

STRUCTURE_MARKERS = [
    "- ",
    "* ",
    "1.",
    "2.",
    "3.",
    "pmh:",
    "hx:",
    "dx:",
    "problem:",
    "assessment:",
    "plan:",
]

UNCERTAINTY_KEYWORDS = ["possible", "maybe", "unclear", "unknown", "?", "likely"]
FACTUAL_EVIDENCE_KEYWORDS = [
    "diagnosis",
    "dx",
    "lab",
    "labs",
    "imaging",
    "meds",
    "medications",
    "allergy",
    "allergies",
]


# ---------------------------------------------------------------------------
# Text analysis helpers
# ---------------------------------------------------------------------------


def _word_count(text: str) -> int:
    """Count words using word-boundary regex (handles punctuation/hyphens)."""
    return len(re.findall(r"\b\w+\b", text))


def _sentence_lengths(text: str) -> List[int]:
    """Return a list of word counts per sentence (split on `.`, `!`, `?`).

    Returns ``[0]`` for empty text so callers can safely compute averages.
    """
    sentences = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]
    return [len(re.findall(r"\b\w+\b", s)) for s in sentences] or [0]


def _keyword_pattern(keyword: str) -> str:
    """Build a regex that matches *keyword* as a whole word (not a substring)."""
    return rf"(?<!\w){re.escape(keyword)}(?!\w)"


def _find_hits(text: str, keywords: List[str]) -> List[str]:
    """Return which keywords appear in *text* (case-insensitive, whole-word).

    Alphanumeric keywords use word-boundary matching to prevent false
    positives (e.g. "days" won't match inside "holidays").  Pure
    punctuation keywords (like "?") use simple substring search.
    """
    hits: List[str] = []
    lowered = text.lower()
    for kw in keywords:
        if any(ch.isalnum() or ch == "_" for ch in kw):
            if re.search(_keyword_pattern(kw), lowered):
                hits.append(kw)
        elif kw in lowered:
            hits.append(kw)
    return hits


def _score_from_hits(count: int) -> int:
    """Map a keyword hit count to a 1-5 score: 0→1, 1→2, 2-3→3, 4-5→4, 6+→5."""
    if count >= 6:
        return 5
    if count >= 4:
        return 4
    if count >= 2:
        return 3
    if count >= 1:
        return 2
    return 1


def _score_focus_by_length(word_count: int) -> Tuple[int, str]:
    """Score the ``focused_not_cluttered`` dimension based on word count.

    Ideal range is 80-200 words (score 5).  Scores decrease as length
    deviates further from this window in either direction.
    """
    if 80 <= word_count <= 200:
        return 5, "Length is concise and focused."
    if 50 <= word_count <= 79 or 201 <= word_count <= 260:
        return 4, "Length is mostly focused."
    if 30 <= word_count <= 49 or 261 <= word_count <= 340:
        return 3, "Length is borderline for focus."
    if 20 <= word_count <= 29 or 341 <= word_count <= 450:
        return 2, "Length suggests either too brief or too verbose."
    return 1, "Length suggests lack of focus."


def _score_clarity(text: str) -> Tuple[int, str, List[str]]:
    """Score ``clarity_readability_formatting`` via sentence length and structure markers.

    Starts at 3, +1 for short avg sentences (≤12 words), -1 for long (≥30),
    +1 if structural markers (bullets, numbered lists, section headers) are present.
    """
    lengths = _sentence_lengths(text)
    avg_len = sum(lengths) / max(len(lengths), 1)
    markers = [m for m in STRUCTURE_MARKERS if m in text.lower()]
    score = 3
    notes: List[str] = []
    if avg_len <= 12:
        score += 1
        notes.append("Short sentences aid readability.")
    elif avg_len >= 30:
        score -= 1
        notes.append("Long sentences reduce scanability.")
    if markers:
        score += 1
        notes.append("Structural markers improve scanning.")
    score = max(1, min(5, score))
    rationale = " ".join(notes) if notes else "Readability is acceptable."
    return score, rationale, markers


def _score_factual_accuracy(text: str) -> Tuple[int, str, List[str]]:
    """Score ``factual_accuracy`` using evidence keywords and uncertainty language.

    Starts at 3, +1 for clinical evidence terms, -1 for uncertainty hedges,
    -1 if very short (<40 words) since brevity risks factual omissions.
    """
    score = 3
    evidence = _find_hits(text, FACTUAL_EVIDENCE_KEYWORDS)
    uncertainty = _find_hits(text, UNCERTAINTY_KEYWORDS)
    if evidence:
        score += 1
    if uncertainty:
        score -= 1
    word_count = _word_count(text)
    if word_count < 40:
        score -= 1
    score = max(1, min(5, score))
    rationale = "Specific clinical details suggest grounded facts."
    if uncertainty:
        rationale += " Uncertainty language lowers confidence."
    if word_count < 40:
        rationale += " Very short summary risks omissions."
    return score, rationale, evidence


def _score_organized(text: str) -> Tuple[int, str, List[str]]:
    """Score ``organized_by_condition`` by counting structural markers (bullets, headers)."""
    markers = [m for m in STRUCTURE_MARKERS if m in text.lower()]
    marker_count = len(markers)
    if marker_count >= 4:
        score = 5
    elif marker_count >= 2:
        score = 4
    elif marker_count >= 1:
        score = 3
    else:
        score = 2
    rationale = "Grouping markers suggest organization by condition."
    if marker_count == 0:
        rationale = "No clear grouping markers found."
    return score, rationale, markers


def _score_timeline(text: str) -> Tuple[int, str, List[str]]:
    """Score ``timeline_evolution`` by counting temporal keyword hits."""
    hits = _find_hits(text, TEMPORAL_KEYWORDS)
    score = _score_from_hits(len(hits))
    rationale = "Temporal cues help track evolution."
    if not hits:
        rationale = "Few or no temporal cues found."
    return score, rationale, hits


def _score_recent_changes(text: str) -> Tuple[int, str, List[str]]:
    """Score ``recent_changes_highlighted`` by counting change-related keyword hits."""
    hits = _find_hits(text, RECENT_CHANGE_KEYWORDS)
    score = _score_from_hits(len(hits))
    rationale = "Recent changes are explicitly called out."
    if not hits:
        rationale = "Recent changes are not clearly highlighted."
    return score, rationale, hits


def _score_chronic_coverage(text: str) -> Tuple[int, str, List[str]]:
    """Score ``relevant_chronic_problem_coverage`` by counting chronic-condition keyword hits."""
    hits = _find_hits(text, CHRONIC_KEYWORDS)
    score = _score_from_hits(len(hits))
    rationale = "Chronic condition coverage is represented."
    if not hits:
        rationale = "Chronic conditions are not mentioned."
    return score, rationale, hits


def _score_decision_usefulness(text: str) -> Tuple[int, str, List[str]]:
    """Score ``usefulness_for_decision_making`` by counting clinical-decision keyword hits."""
    hits = _find_hits(text, DECISION_KEYWORDS)
    score = _score_from_hits(len(hits))
    rationale = "Decision-supporting details are present."
    if not hits:
        rationale = "Missing vitals/meds/labs that support decisions."
    return score, rationale, hits


def compute_overall_score(
    scores: Dict[str, int], weights: Dict[str, float], dimension_ids: List[str]
) -> float:
    """Compute a weighted average score across dimensions.

    If total weight is zero (or all weights missing), falls back to a
    simple unweighted mean.  Result is rounded to 2 decimal places.
    """
    total_weight = sum(weights.get(dim, 0.0) for dim in dimension_ids)
    if total_weight <= 0:
        total_weight = float(len(dimension_ids) or 1)
        return round(sum(scores[dim] for dim in dimension_ids) / total_weight, 2)
    weighted_sum = sum(scores[dim] * weights.get(dim, 0.0) for dim in dimension_ids)
    return round(weighted_sum / total_weight, 2)


def score_summary_heuristic(summary: str, role: RoleProfile, rubric: Rubric) -> AgentScore:
    """Score a clinical summary using the keyword-based heuristic engine.

    Runs all 8 dimension scorers, applies role-specific adjustments,
    clamps to [1, 5], and computes the weighted overall score.

    Args:
        summary: The clinical summary text to evaluate.
        role: The clinical role whose perspective to apply.
        rubric: The evaluation rubric (defines which dimensions to score).

    Returns:
        An ``AgentScore`` with per-dimension scores, rationales, evidence,
        and a weighted overall score.
    """
    summary = summary.strip()
    warnings: List[str] = []
    if not summary:
        warnings.append("Empty summary provided.")

    scores: Dict[str, int] = {}
    rationales: Dict[str, str] = {}
    evidence: Dict[str, List[str]] = {}

    factual_score, factual_rationale, factual_evidence = _score_factual_accuracy(summary)
    scores["factual_accuracy"] = factual_score
    rationales["factual_accuracy"] = factual_rationale
    evidence["factual_accuracy"] = factual_evidence

    chronic_score, chronic_rationale, chronic_evidence = _score_chronic_coverage(summary)
    scores["relevant_chronic_problem_coverage"] = chronic_score
    rationales["relevant_chronic_problem_coverage"] = chronic_rationale
    evidence["relevant_chronic_problem_coverage"] = chronic_evidence

    org_score, org_rationale, org_evidence = _score_organized(summary)
    scores["organized_by_condition"] = org_score
    rationales["organized_by_condition"] = org_rationale
    evidence["organized_by_condition"] = org_evidence

    timeline_score, timeline_rationale, timeline_evidence = _score_timeline(summary)
    scores["timeline_evolution"] = timeline_score
    rationales["timeline_evolution"] = timeline_rationale
    evidence["timeline_evolution"] = timeline_evidence

    recent_score, recent_rationale, recent_evidence = _score_recent_changes(summary)
    scores["recent_changes_highlighted"] = recent_score
    rationales["recent_changes_highlighted"] = recent_rationale
    evidence["recent_changes_highlighted"] = recent_evidence

    word_count = _word_count(summary)
    focus_score, focus_rationale = _score_focus_by_length(word_count)
    scores["focused_not_cluttered"] = focus_score
    rationales["focused_not_cluttered"] = focus_rationale
    evidence["focused_not_cluttered"] = [f"word_count={word_count}"]

    decision_score, decision_rationale, decision_evidence = _score_decision_usefulness(summary)
    scores["usefulness_for_decision_making"] = decision_score
    rationales["usefulness_for_decision_making"] = decision_rationale
    evidence["usefulness_for_decision_making"] = decision_evidence

    clarity_score, clarity_rationale, clarity_evidence = _score_clarity(summary)
    scores["clarity_readability_formatting"] = clarity_score
    rationales["clarity_readability_formatting"] = clarity_rationale
    evidence["clarity_readability_formatting"] = clarity_evidence

    _apply_role_adjustments(role.id, scores, rationales)

    overall_notes = f"Role perspective: {role.name}. Summary length {word_count} words."

    for dim_id in rubric.dimension_ids:
        scores[dim_id] = max(1, min(5, int(scores[dim_id])))

    overall_score = compute_overall_score(scores, role.w_prior, rubric.dimension_ids)

    return AgentScore(
        role_id=role.id,
        scores=scores,
        rationales=rationales,
        evidence=evidence,
        overall_score=overall_score,
        overall_notes=overall_notes,
        warnings=warnings or None,
    )


def _apply_role_adjustments(
    role_id: str, scores: Dict[str, int], rationales: Dict[str, str]
) -> None:
    """Apply role-specific score adjustments that reflect clinical priorities.

    - **Physician**: penalizes low decision-usefulness (expects richer data).
    - **Triage Nurse**: penalizes poor focus and clarity (needs fast scanning).
    - **Bedside Nurse**: boosts recent-changes and decision-usefulness
      (values actionable care details).

    Modifies *scores* and *rationales* dicts in place.
    """
    if role_id == "physician":
        if scores["usefulness_for_decision_making"] <= 2:
            scores["usefulness_for_decision_making"] = max(
                1, scores["usefulness_for_decision_making"] - 1
            )
            rationales["usefulness_for_decision_making"] += (
                " Physician perspective expects higher decision support."
            )
    elif role_id == "triage_nurse":
        if scores["focused_not_cluttered"] <= 3:
            scores["focused_not_cluttered"] = max(
                1, scores["focused_not_cluttered"] - 1
            )
            rationales["focused_not_cluttered"] += (
                " Triage perspective favors tighter focus."
            )
        if scores["clarity_readability_formatting"] <= 3:
            scores["clarity_readability_formatting"] = max(
                1, scores["clarity_readability_formatting"] - 1
            )
            rationales["clarity_readability_formatting"] += (
                " Triage perspective requires fast scanning."
            )
    elif role_id == "bedside_nurse":
        if scores["recent_changes_highlighted"] <= 3:
            scores["recent_changes_highlighted"] = min(
                5, scores["recent_changes_highlighted"] + 1
            )
            rationales["recent_changes_highlighted"] += (
                " Bedside perspective prioritizes recent changes."
            )
        if scores["usefulness_for_decision_making"] <= 3:
            scores["usefulness_for_decision_making"] = min(
                5, scores["usefulness_for_decision_making"] + 1
            )
            rationales["usefulness_for_decision_making"] += (
                " Bedside perspective values actionable care details."
            )
