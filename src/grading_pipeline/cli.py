"""Command-line interface for the LENS grading pipeline.

Usage examples::

    python -m grading_pipeline --summary "Patient presents with..." --engine heuristic
    python -m grading_pipeline --summary-file note.txt --engine llm --model gpt-4o
    python -m grading_pipeline --summary "..." --engine heuristic --format json --pretty
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, Sequence

from .config import Rubric, load_roles, load_rubric
from .orchestrator import run_pipeline
from .source_packets import load_source_file
from .validation import (
    MIN_SOURCE_CHARS,
    MIN_SUMMARY_CHARS,
    SOURCE_GROUNDED_REQUIRES_LLM_ERROR,
    validate_source_text,
    validate_summary_text,
)


def _resolve_summary(args: argparse.Namespace) -> str | None:
    """Read summary text from ``--summary`` flag or ``--summary-file`` path.

    Returns ``None`` if neither was provided (triggers a validation error
    downstream).  Treats ``--summary ""`` as explicit empty input — does
    not fall back to ``--summary-file``.
    """
    if args.summary is not None:
        return args.summary
    if args.summary_file:
        return Path(args.summary_file).read_text()
    return None


def _resolve_source(args: argparse.Namespace) -> tuple[str | None, Dict[str, Any] | None]:
    """Read optional source text from ``--source-text`` or ``--source-file``."""
    if args.source_text is not None:
        return args.source_text, {"file_format": "inline_text"}
    if args.source_file:
        loaded = load_source_file(args.source_file)
        return loaded.text, loaded.metadata
    return None, None


def _validate_summary(summary: str | None) -> str:
    """Thin wrapper around ``validate_summary_text`` for CLI use."""
    return validate_summary_text(summary)


def _validate_source(source_text: str | None) -> str | None:
    """Validate optional source text for source-grounded evaluation."""
    if source_text is None:
        return None
    return validate_source_text(source_text)


def _summarize_source_input(args: argparse.Namespace, source_text: str | None, source_metadata: Dict[str, Any] | None = None) -> Dict[str, Any] | None:
    """Return non-sensitive metadata about the optional source input."""
    if source_text is None:
        return None

    input_mode = "inline" if args.source_text is not None else "file"
    payload = {
        "provided": True,
        "input_mode": input_mode,
        "char_count": len(source_text),
        "sha256": hashlib.sha256(source_text.encode("utf-8")).hexdigest(),
    }
    if source_metadata:
        payload.update({k: v for k, v in source_metadata.items() if v is not None and k != "path"})
    return payload


def _print_human(result: Dict[str, Any], rubric: Rubric) -> None:
    """Format and print pipeline results as a human-readable report to stdout."""
    separator = "----------------------------------------"

    # Keep one empty line before the formatted report block.
    print("")
    print(separator)
    print("Role-Aware Multi-Agent Grading Pipeline:")
    print(separator)

    for scorecard in result["per_role_scorecards"]:
        print(f"{scorecard['role']}:")
        scores = scorecard.get("scores", {})
        for dim in rubric.dimensions:
            score = scores.get(dim.id)
            if isinstance(score, (int, float)):
                print(f"{dim.name}: {float(score):.1f}")
            else:
                print(f"{dim.name}: NA")

        print("")
        overall = scorecard.get("overall")
        if isinstance(overall, (int, float)):
            print(f"Overall: {float(overall):.2f}")
        else:
            print("Overall: NA")
        print(separator)

    # Keep an extra separator before disagreement to match the requested layout.
    print(separator)
    print("Orchestrator Disagreement:")
    print(separator)

    disagreement_map = result.get("disagreement_map", {})
    for dim in rubric.dimensions:
        item = disagreement_map.get(dim.id, {})
        gap = item.get("score_gap")
        if isinstance(gap, (int, float)):
            print(f"{dim.name}: {float(gap):.1f}")
        else:
            print(f"{dim.name}: NA")
    print(separator)

    overall_score = result.get("overall_across_roles")
    if isinstance(overall_score, (int, float)):
        print(f"Overall Score: {float(overall_score):.1f}")
    else:
        print("Overall Score: NA")


def _build_parser() -> argparse.ArgumentParser:
    """Create the CLI argument parser with all pipeline options."""
    parser = argparse.ArgumentParser(
        description="Role-aware multi-agent grading pipeline (orchestrated)."
    )
    parser.add_argument("--summary", type=str, help="Summary text to score.")
    parser.add_argument(
        "--summary-file", type=str, help="Path to a file containing the summary."
    )
    parser.add_argument("--source-text", type=str, help="Optional source record text for source-grounded evaluation.")
    parser.add_argument("--source-file", type=str, help="Path to a file containing source record text or a source packet narrative.")
    parser.add_argument(
        "--rubric",
        type=str,
        default=str(Path("config/lens_rubric.json")),
        help="Path to rubric JSON.",
    )
    parser.add_argument(
        "--roles",
        type=str,
        default=str(Path("config/roles.json")),
        help="Path to roles JSON.",
    )
    parser.add_argument(
        "--engine",
        choices=["llm", "heuristic"],
        default="llm",
        help="Scoring engine to use.",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="gpt-4o-mini",
        help="OpenAI model for LLM scoring.",
    )
    parser.add_argument(
        "--temperature", type=float, default=0.2, help="LLM sampling temperature."
    )
    parser.add_argument(
        "--gap-threshold",
        type=float,
        default=0.5,
        help="Disagreement threshold: flag dimension if max-min >= threshold.",
    )
    parser.add_argument(
        "--format",
        choices=["human", "json"],
        default="human",
        help="Output format.",
    )
    parser.add_argument(
        "--pretty", action="store_true", help="Pretty JSON output (json format only)."
    )
    parser.add_argument("--output", type=str, help="Write output JSON to this file.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point.  Parses args, runs the pipeline, and prints output.

    Returns 0 on success, 2 on input validation errors.
    """
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        summary = _validate_summary(_resolve_summary(args))
        source_text, source_metadata = _resolve_source(args)
        source_text = _validate_source(source_text)
        if source_text is not None and args.engine != "llm":
            raise ValueError(SOURCE_GROUNDED_REQUIRES_LLM_ERROR)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2) from exc

    rubric = load_rubric(args.rubric)
    roles = load_roles(args.roles, rubric.dimension_ids)

    result = asyncio.run(
        run_pipeline(
            summary,
            args.engine,
            args.format,
            rubric=rubric,
            roles=roles,
            model=args.model,
            temperature=args.temperature,
            gap_threshold=args.gap_threshold,
            max_retries=2,
            source_text=source_text,
        )
    )

    if args.format == "human":
        _print_human(result, rubric)
        return 0

    payload = {
        "summary": summary,
        "source": _summarize_source_input(args, source_text, source_metadata),
        "rubric_id": rubric.rubric_id,
        **result,
    }

    output = json.dumps(payload, indent=2 if args.pretty else None)
    if args.output:
        Path(args.output).write_text(output)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
