"""Input validation for clinical summary text.

Enforces minimum length and non-empty constraints before the summary
enters the scoring pipeline.  Used by both the CLI layer and the
orchestrator.
"""

from __future__ import annotations

MIN_SUMMARY_CHARS = 30
MIN_SOURCE_CHARS = 30
EMPTY_SUMMARY_ERROR = "Error: summary is required and cannot be empty."
SHORT_SUMMARY_ERROR = (
    f"Error: summary must be at least {MIN_SUMMARY_CHARS} characters after trimming whitespace."
)
EMPTY_SOURCE_ERROR = "Error: source text cannot be empty if provided."
SHORT_SOURCE_ERROR = (
    f"Error: source text must be at least {MIN_SOURCE_CHARS} characters after trimming whitespace if provided."
)
SOURCE_GROUNDED_REQUIRES_LLM_ERROR = (
    "Error: source-grounded evaluation currently requires --engine llm. "
    "Heuristic mode does not use source text."
)


def validate_summary_text(summary: str | None) -> str:
    """Validate and clean a raw summary string.

    Args:
        summary: Raw summary text (may be ``None`` if user omitted input).

    Returns:
        The whitespace-stripped summary text.

    Raises:
        ValueError: If ``summary`` is ``None``, empty/whitespace-only,
            or shorter than ``MIN_SUMMARY_CHARS`` after stripping.
    """
    if summary is None:
        raise ValueError(EMPTY_SUMMARY_ERROR)

    cleaned = summary.strip()
    if not cleaned:
        raise ValueError(EMPTY_SUMMARY_ERROR)

    if len(cleaned) < MIN_SUMMARY_CHARS:
        raise ValueError(SHORT_SUMMARY_ERROR)

    return cleaned


def validate_source_text(source_text: str | None) -> str:
    """Validate and clean an optional source-record string.

    Source-grounded evaluation is optional. If a source string is provided,
    it must be non-empty and meet the same basic minimum length threshold as
    summaries so the model has enough patient context to compare against.
    """
    if source_text is None:
        raise ValueError(EMPTY_SOURCE_ERROR)

    cleaned = source_text.strip()
    if not cleaned:
        raise ValueError(EMPTY_SOURCE_ERROR)

    if len(cleaned) < MIN_SOURCE_CHARS:
        raise ValueError(SHORT_SOURCE_ERROR)

    return cleaned
