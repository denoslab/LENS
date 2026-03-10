from __future__ import annotations

MIN_SUMMARY_CHARS = 30
EMPTY_SUMMARY_ERROR = "Error: summary is required and cannot be empty."
SHORT_SUMMARY_ERROR = (
    f"Error: summary must be at least {MIN_SUMMARY_CHARS} characters after trimming whitespace."
)


def validate_summary_text(summary: str | None) -> str:
    if summary is None:
        raise ValueError(EMPTY_SUMMARY_ERROR)

    cleaned = summary.strip()
    if not cleaned:
        raise ValueError(EMPTY_SUMMARY_ERROR)

    if len(cleaned) < MIN_SUMMARY_CHARS:
        raise ValueError(SHORT_SUMMARY_ERROR)

    return cleaned
