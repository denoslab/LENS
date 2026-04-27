"""Command-line interface for the LENS grading pipeline."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, Sequence

from .config import (
    Rubric,
    load_default_roles,
    load_default_rubric,
    load_roles,
    load_rubric,
)
from .orchestrator import run_pipeline
from .source_packets import load_source_file
from .validation import (
    MIN_SOURCE_CHARS,
    MIN_SUMMARY_CHARS,
    SOURCE_GROUNDED_REQUIRES_LLM_ERROR,
    validate_source_text,
    validate_summary_text,
)


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _resolve_summary(args: argparse.Namespace) -> str | None:
    """Read summary text from ``--summary`` or ``--summary-file``."""
    if args.summary is not None:
        return args.summary
    if args.summary_file:
        return Path(args.summary_file).read_text(encoding="utf-8")
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
    return validate_summary_text(summary)


def _validate_source(source_text: str | None) -> str | None:
    if source_text is None:
        return None
    return validate_source_text(source_text)


def _summarize_summary_input(summary: str, *, include_text: bool) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "char_count": len(summary),
        "sha256": _sha256_text(summary),
    }
    if include_text:
        payload["text"] = summary
    return payload


def _summarize_source_input(
    args: argparse.Namespace,
    source_text: str | None,
    source_metadata: Dict[str, Any] | None = None,
) -> Dict[str, Any] | None:
    """Return non-sensitive metadata about the optional source input."""
    if source_text is None:
        return None

    input_mode = "inline" if args.source_text is not None else "file"
    payload = {
        "provided": True,
        "input_mode": input_mode,
        "char_count": len(source_text),
        "sha256": _sha256_text(source_text),
    }
    if source_metadata:
        payload.update(
            {k: v for k, v in source_metadata.items() if v is not None and k != "path"}
        )
    return payload


def _load_runtime_config(
    args: argparse.Namespace,
) -> tuple[Rubric, list[Any], Dict[str, Any]]:
    if args.rubric:
        rubric = load_rubric(args.rubric)
        rubric_source = {"mode": "file", "path": str(Path(args.rubric).resolve())}
    else:
        rubric = load_default_rubric()
        rubric_source = {"mode": "bundled_default", "resource": "grading_pipeline.defaults/lens_rubric.json"}

    if args.roles:
        roles = load_roles(args.roles, rubric.dimension_ids)
        roles_source = {"mode": "file", "path": str(Path(args.roles).resolve())}
    else:
        roles = load_default_roles(rubric.dimension_ids)
        roles_source = {"mode": "bundled_default", "resource": "grading_pipeline.defaults/roles.json"}

    return rubric, roles, {"rubric": rubric_source, "roles": roles_source}


def _print_human(result: Dict[str, Any], rubric: Rubric) -> None:
    """Format and print pipeline results as a human-readable report to stdout."""
    separator = "----------------------------------------"
    meta = result.get("meta", {})

    print("")
    print(separator)
    print("Role-Aware Multi-Agent Grading Pipeline:")
    print(separator)
    print(f"Evaluation Context: {meta.get('evaluation_context', 'unknown')}")
    print(f"Adjudication Ran: {'yes' if result.get('adjudication_ran') else 'no'}")
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

    source_summary = result.get("source_grounded_summary")
    if isinstance(source_summary, dict):
        print(f"Wrong-Patient Suspected: {'yes' if source_summary.get('wrong_patient_suspected') else 'no'}")
        print(
            f"Unsupported Claims: {len(source_summary.get('unsupported_claims', []) or [])} | "
            f"Contradicted Claims: {len(source_summary.get('contradicted_claims', []) or [])} | "
            f"Omitted Safety Facts: {len(source_summary.get('omitted_safety_facts', []) or [])}"
        )
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
        "--source-text",
        type=str,
        help="Optional source record text for source-grounded evaluation.",
    )
    parser.add_argument(
        "--source-file",
        type=str,
        help="Path to a file containing source record text or a source packet narrative.",
    )
    parser.add_argument(
        "--rubric",
        type=str,
        default=None,
        help="Path to rubric JSON. Defaults to the bundled package rubric.",
    )
    parser.add_argument(
        "--roles",
        type=str,
        default=None,
        help="Path to roles JSON. Defaults to the bundled package roles.",
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
        default=1.0,
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
    parser.add_argument(
        "--include-summary",
        action="store_true",
        help="Include raw summary text in JSON output. Disabled by default for privacy.",
    )
    parser.add_argument("--output", type=str, help="Write output JSON to this file.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point. Parses args, runs the pipeline, and prints output."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        summary = _validate_summary(_resolve_summary(args))
        source_text, source_metadata = _resolve_source(args)
        source_text = _validate_source(source_text)
        if source_text is not None and args.engine != "llm":
            raise ValueError(SOURCE_GROUNDED_REQUIRES_LLM_ERROR)
        rubric, roles, config_meta = _load_runtime_config(args)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2) from exc
    except OSError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc

    try:
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
    except Exception as exc:
        print(f"Pipeline error: {exc}", file=sys.stderr)
        return 1

    if args.format == "human":
        _print_human(result, rubric)
        return 0

    payload: Dict[str, Any] = {
        "summary_metadata": _summarize_summary_input(summary, include_text=args.include_summary),
        "source": _summarize_source_input(args, source_text, source_metadata),
        "rubric_id": rubric.rubric_id,
        "config": config_meta,
        **result,
    }

    output = json.dumps(payload, indent=2 if args.pretty else None)
    if args.output:
        try:
            Path(args.output).write_text(output, encoding="utf-8")
        except OSError as exc:
            print(f"Error writing output file: {exc}", file=sys.stderr)
            return 1
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
