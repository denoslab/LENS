"""Run a source-grounded benchmark manifest through the existing LENS CLI."""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any, Dict, Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = PROJECT_ROOT / "data/phase2/benchmarks/source_grounded_demo/manifest.json"
DEFAULT_OUTDIR = PROJECT_ROOT / "reports/phase2/source_grounded_demo"
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
                expected_low_scoring_dimensions=list(variant.get("expected_low_scoring_dimensions", [])),
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


def _run_cli(summary_file: Path, source_file: Path, model: str, python_bin: str) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "PYTHONPATH": str(PROJECT_ROOT / "src")}
    return subprocess.run(
        [
            python_bin,
            "-m",
            "grading_pipeline",
            "--engine",
            "llm",
            "--model",
            model,
            "--format",
            "json",
            "--summary-file",
            str(summary_file),
            "--source-file",
            str(source_file),
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        env=env,
    )


def _dimension_means(payload: Dict[str, Any]) -> Dict[str, float]:
    means: Dict[str, float] = {}
    scorecards = payload.get("per_role_scorecards", [])
    for dim in DIMENSION_IDS:
        values = [float(card["scores"][dim]) for card in scorecards if dim in card.get("scores", {})]
        means[dim] = round(mean(values), 4) if values else 0.0
    return means


def _flagged_dimensions(payload: Dict[str, Any]) -> list[str]:
    disagreement = payload.get("disagreement_map", {})
    return [dim for dim, item in disagreement.items() if item.get("flag")]


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
        rows.append(
            {
                "case_id": case.case_id,
                "variant_id": variant.variant_id,
                "variant_type": variant.variant_type,
                "overall": float(payload["overall_across_roles"]),
                "overall_delta_vs_reference": round(reference_overall - float(payload["overall_across_roles"]), 4),
                "expected_dims_count": expected_count,
                "hit_count": hit_count,
                "hit_rate": round(hit_count / expected_count, 4) if expected_count else 1.0,
                "flagged_dimensions": ", ".join(_flagged_dimensions(payload)),
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


def _write_report(path: Path, manifest_name: str, rows: list[dict[str, Any]]) -> None:
    completed = len(rows)
    omission_rows = [row for row in rows if row["variant_type"] == "safety_critical_omission"]
    mismatch_rows = [row for row in rows if row["variant_type"] == "wrong_patient_mismatch"]
    overall_mean_delta = round(mean(row["overall_delta_vs_reference"] for row in rows), 4) if rows else 0.0
    omission_hit_rate = round(mean(row["hit_rate"] for row in omission_rows), 4) if omission_rows else 0.0
    mismatch_hit_rate = round(mean(row["hit_rate"] for row in mismatch_rows), 4) if mismatch_rows else 0.0

    lines = [
        f"# Source-Grounded Benchmark Report: {manifest_name}",
        "",
        "## Overview",
        f"- Completed variants: `{completed}`",
        f"- Mean overall delta vs reference: `{overall_mean_delta}`",
        f"- Mean hit rate (wrong-patient mismatch): `{mismatch_hit_rate}`",
        f"- Mean hit rate (safety-critical omission): `{omission_hit_rate}`",
        "",
        "## Variant Summary",
    ]
    for row in rows:
        lines.extend(
            [
                f"- `{row['case_id']} / {row['variant_id']}`",
                f"  - type: `{row['variant_type']}`",
                f"  - overall delta vs reference: `{row['overall_delta_vs_reference']}`",
                f"  - hit rate: `{row['hit_rate']}`",
                f"  - flagged dimensions: `{row['flagged_dimensions'] or 'none'}`",
            ]
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Phase 2 source-grounded benchmark scaffold.")
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST), help="Path to benchmark manifest JSON.")
    parser.add_argument("--model", default="gpt-4o-mini")
    parser.add_argument("--python-bin", default=sys.executable)
    parser.add_argument("--outdir", default=str(DEFAULT_OUTDIR))
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--max-cases", type=int)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    cases = load_manifest(args.manifest)
    if args.max_cases is not None:
        cases = cases[: args.max_cases]

    outdir = Path(args.outdir)
    outputs_dir = outdir / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)

    summary_rows: list[dict[str, Any]] = []
    for case in cases:
        variant_outputs: Dict[str, Dict[str, Any]] = {}
        for variant in case.variants:
            output_path = outputs_dir / f"{case.case_id}__{variant.variant_id}.json"
            error_path = outputs_dir / f"{case.case_id}__{variant.variant_id}.error.txt"
            if args.resume and output_path.exists():
                variant_outputs[variant.variant_id] = json.loads(output_path.read_text(encoding="utf-8"))
                continue

            result = _run_cli(variant.summary_file, case.source_file, args.model, args.python_bin)
            if result.returncode != 0:
                error_path.write_text(result.stderr, encoding="utf-8")
                continue
            payload = json.loads(result.stdout)
            output_path.write_text(
                json.dumps(payload, indent=2 if args.pretty else None), encoding="utf-8"
            )
            variant_outputs[variant.variant_id] = payload
            time.sleep(0.5)

        if case.reference_variant_id not in variant_outputs:
            continue
        if any(variant.variant_id not in variant_outputs for variant in case.variants):
            continue
        summary_rows.extend(_summarize_case(case, variant_outputs))

    _write_csv(outdir / "summary.csv", summary_rows)
    _write_report(outdir / "report.md", Path(args.manifest).stem, summary_rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
