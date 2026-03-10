import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict, Sequence

from .config import Rubric, load_roles, load_rubric
from .orchestrator import run_pipeline
from .validation import (
    EMPTY_SUMMARY_ERROR,
    MIN_SUMMARY_CHARS,
    SHORT_SUMMARY_ERROR,
    validate_summary_text,
)


def _resolve_summary(args: argparse.Namespace) -> str | None:
    # Treat --summary "" as explicitly provided input; do not fall back.
    if args.summary is not None:
        return args.summary
    if args.summary_file:
        return Path(args.summary_file).read_text()
    return None


def _validate_summary(summary: str | None) -> str:
    return validate_summary_text(summary)


def _print_human(result: Dict[str, Any], rubric: Rubric) -> None:
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
    parser = argparse.ArgumentParser(
        description="Role-aware multi-agent grading pipeline (orchestrated)."
    )
    parser.add_argument("--summary", type=str, help="Summary text to score.")
    parser.add_argument(
        "--summary-file", type=str, help="Path to a file containing the summary."
    )
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
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        summary = _validate_summary(_resolve_summary(args))
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
        )
    )

    if args.format == "human":
        _print_human(result, rubric)
        return 0

    payload = {
        "summary": summary,
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
