"""Run a source-grounded benchmark manifest through the existing LENS CLI.

This script is intentionally an external experiment runner: each benchmark
variant is scored by invoking ``python -m grading_pipeline`` with
``--summary-file`` and, for source-grounded runs, ``--source-file``. That
keeps Phase 2 results aligned with the same public workflow users run from
the terminal.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any, Dict, Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = PROJECT_ROOT / "data/phase2/benchmarks/source_grounded_demo/manifest.json"
DEFAULT_OUTDIR_SOURCE_GROUNDED = PROJECT_ROOT / "reports/phase2/source_grounded_demo"
DEFAULT_OUTDIR_SUMMARY_ONLY = PROJECT_ROOT / "reports/phase2/source_grounded_demo_summary_only"
DEFAULT_RUBRIC = PROJECT_ROOT / "config/lens_rubric.json"
DEFAULT_ROLES = PROJECT_ROOT / "config/roles.json"
DEFAULT_EVALUATION_CONTEXT = "source_grounded"
DEFAULT_TEMPERATURE = 0.0
DIMENSION_IDS = [
    "factual_accuracy",
    "relevant_chronic_problem_coverage",
    "organized_by_condition",
    "timeline_evolution",
    "recent_changes_highlighted",
    "focused_not_cluttered",
    "usefulness_for_decision_making",
    "clarity_readability_formatting",
]
ERROR_PREVIEW_CHARS = 240


@dataclass(frozen=True)
class Variant:
    case_id: str
    variant_id: str
    variant_type: str
    summary_file: Path
    expected_low_scoring_dimensions: list[str]


@dataclass(frozen=True)
class Case:
    case_id: str
    source_file: Path
    reference_variant_id: str
    variants: list[Variant]


@dataclass
class BenchmarkStats:
    attempted_cases: int = 0
    attempted_variants: int = 0
    completed_cases: int = 0
    completed_variants: int = 0
    resumed_variants: int = 0
    skipped_cases: list[str] = field(default_factory=list)
    failed_variants: list[str] = field(default_factory=list)


def load_manifest(path: str | Path) -> list[Case]:
    manifest_path = Path(path)
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    base_dir = manifest_path.parent
    cases: list[Case] = []
    for item in data["cases"]:
        variants = [
            Variant(
                case_id=item["case_id"],
                variant_id=variant["variant_id"],
                variant_type=variant["variant_type"],
                summary_file=(base_dir / variant["summary_file"]).resolve(),
                expected_low_scoring_dimensions=list(
                    variant.get("expected_low_scoring_dimensions", [])
                ),
            )
            for variant in item["variants"]
        ]
        cases.append(
            Case(
                case_id=item["case_id"],
                source_file=(base_dir / item["source_file"]).resolve(),
                reference_variant_id=item["reference_variant_id"],
                variants=variants,
            )
        )
    return cases


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _current_git_sha() -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    sha = result.stdout.strip()
    return sha or None


def _preview_text(text: str, *, max_chars: int = ERROR_PREVIEW_CHARS) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[:max_chars] + "..."


def _default_outdir_for_context(evaluation_context: str) -> Path:
    if evaluation_context == "source_grounded":
        return DEFAULT_OUTDIR_SOURCE_GROUNDED
    if evaluation_context == "summary_only":
        return DEFAULT_OUTDIR_SUMMARY_ONLY
    raise ValueError(f"Unsupported evaluation context: {evaluation_context}")


def _build_cli_command(
    summary_file: Path,
    source_file: Path,
    *,
    model: str,
    python_bin: str,
    rubric: Path,
    roles: Path,
    evaluation_context: str,
    temperature: float,
) -> list[str]:
    command = [
        python_bin,
        "-m",
        "grading_pipeline",
        "--engine",
        "llm",
        "--model",
        model,
        "--temperature",
        str(temperature),
        "--format",
        "json",
        "--summary-file",
        str(summary_file),
        "--rubric",
        str(rubric),
        "--roles",
        str(roles),
    ]
    if evaluation_context == "source_grounded":
        command.extend(["--source-file", str(source_file)])
    elif evaluation_context != "summary_only":
        raise ValueError(f"Unsupported evaluation context: {evaluation_context}")
    return command


def _run_cli(
    summary_file: Path,
    source_file: Path,
    *,
    model: str,
    python_bin: str,
    rubric: Path,
    roles: Path,
    evaluation_context: str,
    temperature: float,
) -> subprocess.CompletedProcess[str]:
    """Run the existing CLI for one benchmark variant."""
    env = dict(os.environ)
    src_path = str(PROJECT_ROOT / "src")
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        f"{src_path}{os.pathsep}{existing_pythonpath}"
        if existing_pythonpath
        else src_path
    )
    return subprocess.run(
        _build_cli_command(
            summary_file,
            source_file,
            model=model,
            python_bin=python_bin,
            rubric=rubric,
            roles=roles,
            evaluation_context=evaluation_context,
            temperature=temperature,
        ),
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        env=env,
    )


def _write_error_log(
    path: Path,
    *,
    case: Case,
    variant: Variant,
    result: subprocess.CompletedProcess[str] | None = None,
    error: Exception | None = None,
) -> None:
    lines = [
        f"case_id: {case.case_id}",
        f"variant_id: {variant.variant_id}",
        f"variant_type: {variant.variant_type}",
        f"summary_file: {variant.summary_file}",
        f"source_file: {case.source_file}",
        "",
    ]
    if result is not None:
        lines.extend(
            [
                f"returncode: {result.returncode}",
                f"stdout_chars: {len(result.stdout)}",
                f"stderr_chars: {len(result.stderr)}",
                f"stdout_preview: {_preview_text(result.stdout)}",
                f"stderr_preview: {_preview_text(result.stderr)}",
            ]
        )
    if error is not None:
        lines.extend(["exception:", f"{type(error).__name__}: {error}"])
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _dimension_means(payload: Dict[str, Any]) -> Dict[str, float]:
    means: Dict[str, float] = {}
    scorecards = payload.get("per_role_scorecards", [])
    for dim in DIMENSION_IDS:
        values = [
            float(card["scores"][dim])
            for card in scorecards
            if dim in card.get("scores", {})
        ]
        means[dim] = round(mean(values), 4) if values else 0.0
    return means


def _flagged_dimensions(payload: Dict[str, Any]) -> list[str]:
    disagreement = payload.get("disagreement_map", {})
    return [dim for dim, item in disagreement.items() if item.get("flag")]


def _signal_fields(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Extract structured signals from the source-grounded summary, if present."""
    summary = payload.get("source_grounded_summary")
    if not isinstance(summary, dict):
        return {
            "wrong_patient_suspected": False,
            "unsupported_claim_count": 0,
            "contradicted_claim_count": 0,
            "omitted_safety_fact_count": 0,
        }
    return {
        "wrong_patient_suspected": bool(summary.get("wrong_patient_suspected")),
        "unsupported_claim_count": len(summary.get("unsupported_claims", []) or []),
        "contradicted_claim_count": len(summary.get("contradicted_claims", []) or []),
        "omitted_safety_fact_count": len(summary.get("omitted_safety_facts", []) or []),
    }


def _summarize_case(case: Case, outputs: Dict[str, Dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    reference = outputs[case.reference_variant_id]
    reference_dims = _dimension_means(reference)
    reference_overall = float(reference["overall_across_roles"])

    for variant in case.variants:
        payload = outputs[variant.variant_id]
        variant_dims = _dimension_means(payload)
        hit_count = 0
        expected_count = len(variant.expected_low_scoring_dimensions)
        for dim in variant.expected_low_scoring_dimensions:
            if reference_dims[dim] > variant_dims[dim]:
                hit_count += 1
        signals = _signal_fields(payload)
        rows.append(
            {
                "case_id": case.case_id,
                "variant_id": variant.variant_id,
                "variant_type": variant.variant_type,
                "overall": float(payload["overall_across_roles"]),
                "overall_delta_vs_reference": round(
                    reference_overall - float(payload["overall_across_roles"]), 4
                ),
                "expected_dims_count": expected_count,
                "hit_count": hit_count,
                "hit_rate": round(hit_count / expected_count, 4)
                if expected_count
                else 1.0,
                "flagged_dimensions": ", ".join(_flagged_dimensions(payload)),
                "wrong_patient_suspected": signals["wrong_patient_suspected"],
                "unsupported_claim_count": signals["unsupported_claim_count"],
                "contradicted_claim_count": signals["contradicted_claim_count"],
                "omitted_safety_fact_count": signals["omitted_safety_fact_count"],
            }
        )
    return rows


def _write_csv(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    rows = list(rows)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _write_report(
    path: Path,
    manifest_name: str,
    rows: list[dict[str, Any]],
    *,
    run_meta: Dict[str, Any],
    stats: BenchmarkStats,
) -> None:
    degraded_rows = [row for row in rows if row["variant_type"] != "reference"]
    reference_rows = [row for row in rows if row["variant_type"] == "reference"]
    omission_rows = [row for row in degraded_rows if row["variant_type"] == "safety_critical_omission"]
    mismatch_rows = [row for row in degraded_rows if row["variant_type"] == "wrong_patient_mismatch"]
    overall_mean_delta = (
        round(mean(row["overall_delta_vs_reference"] for row in degraded_rows), 4)
        if degraded_rows
        else 0.0
    )
    omission_hit_rate = (
        round(mean(row["hit_rate"] for row in omission_rows), 4)
        if omission_rows
        else 0.0
    )
    mismatch_hit_rate = (
        round(mean(row["hit_rate"] for row in mismatch_rows), 4)
        if mismatch_rows
        else 0.0
    )
    mismatch_signal_rate = (
        round(mean(1.0 if row["wrong_patient_suspected"] else 0.0 for row in mismatch_rows), 4)
        if mismatch_rows
        else 0.0
    )
    omission_signal_rate = (
        round(mean(1.0 if row["omitted_safety_fact_count"] > 0 else 0.0 for row in omission_rows), 4)
        if omission_rows
        else 0.0
    )

    evaluation_context = run_meta.get("evaluation_context", DEFAULT_EVALUATION_CONTEXT)
    benchmark_label = "Source-Grounded" if evaluation_context == "source_grounded" else "Summary-Only"
    mismatch_signal_display = (
        f"`{mismatch_signal_rate}`" if evaluation_context == "source_grounded" else "`N/A (summary-only run)`"
    )
    omission_signal_display = (
        f"`{omission_signal_rate}`" if evaluation_context == "source_grounded" else "`N/A (summary-only run)`"
    )

    lines = [
        f"# {benchmark_label} Benchmark Report: {manifest_name}",
        "",
        "## Run Metadata",
        f"- Timestamp (UTC): `{run_meta['timestamp_utc']}`",
        f"- Git SHA: `{run_meta.get('git_sha') or 'unknown'}`",
        f"- Evaluation context: `{evaluation_context}`",
        f"- Model: `{run_meta['model']}`",
        f"- Temperature: `{run_meta['temperature']}`",
        f"- Rubric: `{run_meta['rubric_path']}` (sha256 `{run_meta['rubric_sha256']}`)",
        f"- Roles: `{run_meta['roles_path']}` (sha256 `{run_meta['roles_sha256']}`)",
        f"- Manifest: `{run_meta['manifest_path']}` (sha256 `{run_meta['manifest_sha256']}`)",
        f"- Resume enabled: `{run_meta['resume_enabled']}`",
        "",
        "## Overview",
        f"- Attempted cases: `{stats.attempted_cases}`",
        f"- Attempted variants: `{stats.attempted_variants}`",
        f"- Completed cases: `{stats.completed_cases}`",
        f"- Completed variants: `{stats.completed_variants}`",
        f"- Completed reference variants: `{len(reference_rows)}`",
        f"- Completed degraded test variants: `{len(degraded_rows)}`",
        f"- Resumed variants: `{stats.resumed_variants}`",
        f"- Skipped cases: `{len(stats.skipped_cases)}`",
        f"- Failed variants: `{len(stats.failed_variants)}`",
        f"- Mean overall delta vs reference (degraded variants only): `{overall_mean_delta}`",
        f"- Mean hit rate (wrong-patient mismatch, score-based): `{mismatch_hit_rate}`",
        f"- Mean hit rate (safety-critical omission, score-based): `{omission_hit_rate}`",
        f"- Wrong-patient signal rate (LLM flagged): {mismatch_signal_display}",
        f"- Safety-omission signal rate (LLM flagged >=1 fact): {omission_signal_display}",
    ]

    if stats.skipped_cases:
        lines.extend(["", "## Skipped Cases"])
        lines.extend([f"- `{case_id}`" for case_id in stats.skipped_cases])
    if stats.failed_variants:
        lines.extend(["", "## Failed Variants"])
        lines.extend([f"- `{variant_id}`" for variant_id in stats.failed_variants])

    lines.extend(["", "## Variant Summary"])
    for row in rows:
        lines.extend(
            [
                f"- `{row['case_id']} / {row['variant_id']}`",
                f"  - type: `{row['variant_type']}`",
                f"  - overall delta vs reference: `{row['overall_delta_vs_reference']}`",
                f"  - hit rate: `{row['hit_rate']}`",
                f"  - flagged dimensions: `{row['flagged_dimensions'] or 'none'}`",
                f"  - wrong_patient_suspected: `{row['wrong_patient_suspected']}`",
                f"  - unsupported_claims: `{row['unsupported_claim_count']}`",
                f"  - contradicted_claims: `{row['contradicted_claim_count']}`",
                f"  - omitted_safety_facts: `{row['omitted_safety_fact_count']}`",
            ]
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _run_benchmark(
    args: argparse.Namespace,
    cases: list[Case],
) -> tuple[list[dict[str, Any]], BenchmarkStats]:
    outdir = _default_outdir_for_context(args.evaluation_context) if args.outdir is None else Path(args.outdir)
    outputs_dir = outdir / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)

    summary_rows: list[dict[str, Any]] = []
    stats = BenchmarkStats(attempted_cases=len(cases), attempted_variants=sum(len(case.variants) for case in cases))

    for case in cases:
        variant_outputs: Dict[str, Dict[str, Any]] = {}
        for variant in case.variants:
            output_path = outputs_dir / f"{case.case_id}__{variant.variant_id}.json"
            error_path = outputs_dir / f"{case.case_id}__{variant.variant_id}.error.txt"
            if args.resume and output_path.exists():
                variant_outputs[variant.variant_id] = json.loads(
                    output_path.read_text(encoding="utf-8")
                )
                stats.resumed_variants += 1
                stats.completed_variants += 1
                continue

            result = _run_cli(
                variant.summary_file,
                case.source_file,
                model=args.model,
                python_bin=args.python_bin,
                rubric=Path(args.rubric),
                roles=Path(args.roles),
                evaluation_context=args.evaluation_context,
                temperature=args.temperature,
            )
            if result.returncode != 0:
                _write_error_log(error_path, case=case, variant=variant, result=result)
                stats.failed_variants.append(f"{case.case_id}/{variant.variant_id}")
                continue
            try:
                payload = json.loads(result.stdout)
            except json.JSONDecodeError as exc:
                _write_error_log(
                    error_path,
                    case=case,
                    variant=variant,
                    result=result,
                    error=exc,
                )
                stats.failed_variants.append(f"{case.case_id}/{variant.variant_id}")
                continue

            if error_path.exists():
                error_path.unlink()
            output_path.write_text(
                json.dumps(payload, indent=2 if args.pretty else None),
                encoding="utf-8",
            )
            variant_outputs[variant.variant_id] = payload
            stats.completed_variants += 1
            if args.sleep_seconds > 0:
                time.sleep(args.sleep_seconds)

        if case.reference_variant_id not in variant_outputs or any(
            variant.variant_id not in variant_outputs for variant in case.variants
        ):
            stats.skipped_cases.append(case.case_id)
            continue

        stats.completed_cases += 1
        summary_rows.extend(_summarize_case(case, variant_outputs))

    return summary_rows, stats


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the Phase 2 source-grounded benchmark via the LENS CLI."
    )
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST), help="Path to benchmark manifest JSON.")
    parser.add_argument("--model", default="gpt-4o-mini")
    parser.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE)
    parser.add_argument(
        "--evaluation-context",
        choices=["source_grounded", "summary_only"],
        default=DEFAULT_EVALUATION_CONTEXT,
        help="Whether to compare summaries against source packets or run the same benchmark in summary-only mode.",
    )
    parser.add_argument("--python-bin", default=sys.executable)
    parser.add_argument(
        "--outdir",
        default=None,
        help="Output directory. Defaults depend on evaluation context.",
    )
    parser.add_argument("--rubric", default=str(DEFAULT_RUBRIC))
    parser.add_argument("--roles", default=str(DEFAULT_ROLES))
    parser.add_argument("--sleep-seconds", type=float, default=0.5)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--max-cases", type=int)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    cases = load_manifest(args.manifest)
    if args.max_cases is not None:
        cases = cases[: args.max_cases]

    summary_rows, stats = _run_benchmark(args, cases)

    outdir = _default_outdir_for_context(args.evaluation_context) if args.outdir is None else Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    run_meta = {
        "timestamp_utc": _utc_now_iso(),
        "git_sha": _current_git_sha(),
        "model": args.model,
        "temperature": args.temperature,
        "evaluation_context": args.evaluation_context,
        "python_bin": args.python_bin,
        "manifest_path": str(Path(args.manifest).resolve()),
        "manifest_sha256": _sha256_file(Path(args.manifest)),
        "rubric_path": str(Path(args.rubric).resolve()),
        "rubric_sha256": _sha256_file(Path(args.rubric)),
        "roles_path": str(Path(args.roles).resolve()),
        "roles_sha256": _sha256_file(Path(args.roles)),
        "resume_enabled": bool(args.resume),
        "stats": {
            "attempted_cases": stats.attempted_cases,
            "attempted_variants": stats.attempted_variants,
            "completed_cases": stats.completed_cases,
            "completed_variants": stats.completed_variants,
            "resumed_variants": stats.resumed_variants,
            "skipped_cases": stats.skipped_cases,
            "failed_variants": stats.failed_variants,
        },
    }
    _write_csv(outdir / "summary.csv", summary_rows)
    _write_report(
        outdir / "report.md",
        Path(args.manifest).stem,
        summary_rows,
        run_meta=run_meta,
        stats=stats,
    )
    (outdir / "run_meta.json").write_text(
        json.dumps(run_meta, indent=2),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
