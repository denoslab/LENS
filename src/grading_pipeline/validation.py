"""Input validation for clinical summary text.

Enforces minimum length and non-empty constraints before the summary
enters the scoring pipeline.  Used by both the CLI layer and the
orchestrator.
"""

from __future__ import annotations

MIN_SUMMARY_CHARS = 30
EMPTY_SUMMARY_ERROR = "Error: summary is required and cannot be empty."
SHORT_SUMMARY_ERROR = (
    f"Error: summary must be at least {MIN_SUMMARY_CHARS} characters after trimming whitespace."
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
