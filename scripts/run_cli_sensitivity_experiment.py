from __future__ import annotations

import argparse
import csv
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any

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

DEFAULT_GOOD_FILE = Path(
    "/Users/samuel/Desktop/LENS Project/MTS-Dialog-ValidationSet_top10_longest_section_texts.txt"
)
DEFAULT_BAD_FILE = Path(
    "/Users/samuel/Desktop/LENS Project/lens_bad_samples_complete_english.txt"
)
REPO_ROOT = Path(__file__).resolve().parents[1]
SLEEP_SECONDS = 0.75
GOOD_HEADER_RE = re.compile(
    r"^(?P<index>\d+)\.\s+ID=(?P<source_id>[^|]+)\|\s*section_header=(?P<section_header>[^|]+)\|.*$"
)

BAD_SAMPLE_BLOCK_RE = re.compile(r"BAD SAMPLE\s+\d+")


@dataclass(frozen=True)
class GoodSample:
    source_id: str
    section_header: str
    summary_text: str


@dataclass(frozen=True)
class BadSample:
    source_id: str
    section_header: str | None
    badness_type: str | None
    bad_summary_text: str
    expected_low_scoring_dimensions: list[str]


@dataclass
class SampleRunRecord:
    group: str
    source_id: str
    section_header: str | None
    success: bool
    output_path: Path | None
    error_path: Path | None
    payload: dict[str, Any] | None
    stderr: str | None
    expected_low_scoring_dimensions: list[str] | None = None
    badness_type: str | None = None


def parse_good_summaries(path: str | Path) -> list[GoodSample]:
    text = Path(path).read_text(encoding="utf-8")
    blocks = [
        block.strip()
        for block in re.split(r"\n\s*-{10,}\s*\n", text.strip())
        if block.strip()
    ]
    samples: list[GoodSample] = []
    for block in blocks:
        header, _, body = block.partition("\n")
        match = GOOD_HEADER_RE.match(header.strip())
        if not match:
            raise ValueError(f"Could not parse good-sample header: {header!r}")
        samples.append(
            GoodSample(
                source_id=match.group("source_id").strip(),
                section_header=match.group("section_header").strip(),
                summary_text=body.strip(),
            )
        )
    return samples


def _find_line_index(lines: list[str], label: str) -> int:
    for idx, line in enumerate(lines):
        if line.strip() == label:
            return idx
    return -1


def _extract_section(lines: list[str], label: str, stop_labels: set[str]) -> str:
    start = _find_line_index(lines, label)
    if start == -1:
        return ""
    collected: list[str] = []
    for line in lines[start + 1 :]:
        stripped = line.strip()
        if stripped in stop_labels:
            break
        collected.append(line)
    return "\n".join(collected).strip()


def _extract_bullet_list(lines: list[str], label: str) -> list[str]:
    start = _find_line_index(lines, label)
    if start == -1:
        return []
    items: list[str] = []
    for line in lines[start + 1 :]:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("BAD SAMPLE ") or set(stripped) == {"="}:
            break
        if stripped.startswith("- "):
            items.append(stripped[2:].strip())
        elif items:
            break
    return items


def parse_bad_summaries(path: str | Path) -> list[BadSample]:
    text = Path(path).read_text(encoding="utf-8")
    raw_blocks = [
        block.strip()
        for block in re.split(r"\n={10,}\n", text.strip())
        if block.strip()
    ]
    samples: list[BadSample] = []
    stop_labels = {
        "WHAT I REMOVED",
        "WHAT I REPLACED",
        "WHAT I CHANGED",
        "EXPECTED LOW-SCORING DIMENSIONS",
    }
    for block in raw_blocks:
        match = BAD_SAMPLE_BLOCK_RE.search(block)
        if match is None:
            continue
        block = block[match.start() :].strip()
        lines = block.splitlines()
        source_id = ""
        section_header: str | None = None
        badness_type: str | None = None
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("Source ID:"):
                source_id = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("Section Header:"):
                section_header = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("Badness Type:"):
                badness_type = stripped.split(":", 1)[1].strip()
        if not source_id:
            raise ValueError(
                f"Could not parse Source ID from bad sample block: {block[:120]!r}"
            )
        bad_summary = _extract_section(lines, "BAD SUMMARY", stop_labels)
        expected_dims = _extract_bullet_list(lines, "EXPECTED LOW-SCORING DIMENSIONS")
        samples.append(
            BadSample(
                source_id=source_id,
                section_header=section_header,
                badness_type=badness_type,
                bad_summary_text=bad_summary,
                expected_low_scoring_dimensions=expected_dims,
            )
        )
    return samples


def _repo_path(path_str: str) -> Path:
    path = Path(path_str)
    if path.is_absolute():
        return path
    return REPO_ROOT / path


def _cli_env() -> dict[str, str]:
    env = os.environ.copy()
    src_path = str(REPO_ROOT / "src")
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = src_path if not existing else f"{src_path}{os.pathsep}{existing}"
    return env


def _build_cli_command(
    python_bin: str,
    model: str,
    summary_text: str,
    pretty: bool,
) -> list[str]:
    cmd = [
        python_bin,
        "-m",
        "grading_pipeline",
        "--engine",
        "llm",
        "--model",
        model,
        "--format",
        "json",
        "--summary",
        summary_text.strip(),
    ]
    if pretty:
        cmd.append("--pretty")
    return cmd


def _save_json(path: Path, payload: dict[str, Any], pretty: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2 if pretty else None, ensure_ascii=False)
        handle.write("\n")


def _save_error(
    path: Path,
    command: list[str],
    returncode: int,
    stdout: str,
    stderr: str,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = [
        f"returncode: {returncode}",
        f"command: {' '.join(command)}",
        "",
        "STDOUT:",
        stdout,
        "",
        "STDERR:",
        stderr,
    ]
    path.write_text("\n".join(text), encoding="utf-8")


def _role_overall(payload: dict[str, Any], role_name: str) -> float | None:
    for scorecard in payload.get("per_role_scorecards", []):
        if scorecard.get("role") == role_name:
            overall = scorecard.get("overall")
            return float(overall) if isinstance(overall, (int, float)) else None
    return None


def _dimension_mean_across_roles(
    payload: dict[str, Any], dimension_id: str
) -> float | None:
    values: list[float] = []
    for scorecard in payload.get("per_role_scorecards", []):
        value = scorecard.get("scores", {}).get(dimension_id)
        if isinstance(value, (int, float)):
            values.append(float(value))
    return mean(values) if values else None


def _flagged_dimensions(payload: dict[str, Any]) -> list[str]:
    flagged: list[str] = []
    for dim, item in payload.get("disagreement_map", {}).items():
        if item.get("flag"):
            flagged.append(dim)
    return flagged


def _run_one_sample(
    *,
    group: str,
    source_id: str,
    section_header: str | None,
    summary_text: str,
    python_bin: str,
    model: str,
    outputs_dir: Path,
    pretty: bool,
    resume: bool,
    expected_low_scoring_dimensions: list[str] | None = None,
    badness_type: str | None = None,
) -> SampleRunRecord:
    outputs_dir.mkdir(parents=True, exist_ok=True)
    output_path = outputs_dir / f"source_{source_id}.json"
    error_path = outputs_dir / f"source_{source_id}.error.txt"

    if resume and output_path.exists():
        payload = json.loads(output_path.read_text(encoding="utf-8"))
        return SampleRunRecord(
            group=group,
            source_id=source_id,
            section_header=section_header,
            success=True,
            output_path=output_path,
            error_path=error_path if error_path.exists() else None,
            payload=payload,
            stderr=None,
            expected_low_scoring_dimensions=expected_low_scoring_dimensions,
            badness_type=badness_type,
        )

    if resume and error_path.exists() and not output_path.exists():
        return SampleRunRecord(
            group=group,
            source_id=source_id,
            section_header=section_header,
            success=False,
            output_path=None,
            error_path=error_path,
            payload=None,
            stderr=error_path.read_text(encoding="utf-8"),
            expected_low_scoring_dimensions=expected_low_scoring_dimensions,
            badness_type=badness_type,
        )

    command = _build_cli_command(python_bin, model, summary_text.strip(), pretty)
    process = subprocess.run(
        command,
        cwd=REPO_ROOT,
        env=_cli_env(),
        capture_output=True,
        text=True,
    )

    if process.returncode != 0:
        _save_error(error_path, command, process.returncode, process.stdout, process.stderr)
        return SampleRunRecord(
            group=group,
            source_id=source_id,
            section_header=section_header,
            success=False,
            output_path=None,
            error_path=error_path,
            payload=None,
            stderr=process.stderr,
            expected_low_scoring_dimensions=expected_low_scoring_dimensions,
            badness_type=badness_type,
        )

    try:
        payload = json.loads(process.stdout)
    except json.JSONDecodeError as exc:
        _save_error(
            error_path,
            command,
            process.returncode,
            process.stdout,
            f"JSON parse error: {exc}\n\n{process.stderr}",
        )
        return SampleRunRecord(
            group=group,
            source_id=source_id,
            section_header=section_header,
            success=False,
            output_path=None,
            error_path=error_path,
            payload=None,
            stderr=f"JSON parse error: {exc}",
            expected_low_scoring_dimensions=expected_low_scoring_dimensions,
            badness_type=badness_type,
        )

    _save_json(output_path, payload, pretty)
    return SampleRunRecord(
        group=group,
        source_id=source_id,
        section_header=section_header,
        success=True,
        output_path=output_path,
        error_path=error_path if error_path.exists() else None,
        payload=payload,
        stderr=process.stderr or None,
        expected_low_scoring_dimensions=expected_low_scoring_dimensions,
        badness_type=badness_type,
    )


def _markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    def fmt(value: Any) -> str:
        if value is None:
            return "NA"
        if isinstance(value, float):
            return f"{value:.4f}"
        if isinstance(value, list):
            return ", ".join(str(item) for item in value) if value else "-"
        return str(value)

    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(fmt(cell) for cell in row) + " |")
    return "\n".join(lines)


def _safe_mean(values: list[float]) -> float | None:
    return mean(values) if values else None


def _group_dimension_stats(records: list[SampleRunRecord]) -> dict[str, float | None]:
    stats: dict[str, float | None] = {}
    for dimension_id in DIMENSION_IDS:
        values = [
            _dimension_mean_across_roles(record.payload or {}, dimension_id)
            for record in records
            if record.payload is not None
        ]
        stats[dimension_id] = _safe_mean(
            [value for value in values if value is not None]
        )
    return stats


def _group_role_overall(records: list[SampleRunRecord], role_name: str) -> float | None:
    values = [
        _role_overall(record.payload or {}, role_name)
        for record in records
        if record.payload is not None
    ]
    return _safe_mean([value for value in values if value is not None])


def _group_flag_frequency(records: list[SampleRunRecord]) -> dict[str, int]:
    counts = {dimension_id: 0 for dimension_id in DIMENSION_IDS}
    for record in records:
        if not record.payload:
            continue
        for dimension_id in _flagged_dimensions(record.payload):
            counts[dimension_id] += 1
    return counts


def _summarize_to_csv(paired_rows: list[dict[str, Any]], summary_csv_path: Path) -> None:
    summary_csv_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "source_id",
        "section_header",
        "badness_type",
        "good_overall_across_roles",
        "bad_overall_across_roles",
        "delta_overall",
        "good_flagged_dimensions",
        "bad_flagged_dimensions",
        "expected_low_scoring_dimensions",
        "actual_decreased_dimensions",
        "missed_expected_dimensions",
        "hit_rate",
    ]
    with summary_csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in paired_rows:
            writer.writerow(
                {
                    **row,
                    "good_flagged_dimensions": ",".join(row["good_flagged_dimensions"]),
                    "bad_flagged_dimensions": ",".join(row["bad_flagged_dimensions"]),
                    "expected_low_scoring_dimensions": ",".join(
                        row["expected_low_scoring_dimensions"]
                    ),
                    "actual_decreased_dimensions": ",".join(
                        row["actual_decreased_dimensions"]
                    ),
                    "missed_expected_dimensions": ",".join(
                        row["missed_expected_dimensions"]
                    ),
                    "hit_rate": (
                        f"{row['hit_rate']:.4f}"
                        if row["hit_rate"] is not None
                        else "NA"
                    ),
                }
            )


def _build_report(
    *,
    model: str,
    outdir: Path,
    good_records: list[SampleRunRecord],
    bad_records: list[SampleRunRecord],
    paired_rows: list[dict[str, Any]],
) -> str:
    good_success = [
        record for record in good_records if record.success and record.payload is not None
    ]
    bad_success = [
        record for record in bad_records if record.success and record.payload is not None
    ]
    failures = [record for record in good_records + bad_records if not record.success]

    good_overall = _safe_mean(
        [
            float(record.payload["overall_across_roles"])
            for record in good_success
            if isinstance(record.payload.get("overall_across_roles"), (int, float))
        ]
    )
    bad_overall = _safe_mean(
        [
            float(record.payload["overall_across_roles"])
            for record in bad_success
            if isinstance(record.payload.get("overall_across_roles"), (int, float))
        ]
    )

    group_rows = [
        [
            "overall_across_roles",
            good_overall,
            bad_overall,
            (good_overall - bad_overall)
            if good_overall is not None and bad_overall is not None
            else None,
        ],
        [
            "Physician overall",
            _group_role_overall(good_success, "Physician"),
            _group_role_overall(bad_success, "Physician"),
            None,
        ],
        [
            "Triage Nurse overall",
            _group_role_overall(good_success, "Triage Nurse"),
            _group_role_overall(bad_success, "Triage Nurse"),
            None,
        ],
        [
            "Bedside Nurse overall",
            _group_role_overall(good_success, "Bedside Nurse"),
            _group_role_overall(bad_success, "Bedside Nurse"),
            None,
        ],
    ]
    for row in group_rows[1:]:
        if isinstance(row[1], float) and isinstance(row[2], float):
            row[3] = row[1] - row[2]

    good_dimension_stats = _group_dimension_stats(good_success)
    bad_dimension_stats = _group_dimension_stats(bad_success)
    dimension_rows = []
    for dimension_id in DIMENSION_IDS:
        good_value = good_dimension_stats[dimension_id]
        bad_value = bad_dimension_stats[dimension_id]
        delta = (
            good_value - bad_value
            if good_value is not None and bad_value is not None
            else None
        )
        dimension_rows.append([dimension_id, good_value, bad_value, delta])

    good_flag_counts = _group_flag_frequency(good_success)
    bad_flag_counts = _group_flag_frequency(bad_success)
    disagreement_rows = []
    for dimension_id in DIMENSION_IDS:
        disagreement_rows.append(
            [dimension_id, good_flag_counts[dimension_id], bad_flag_counts[dimension_id]]
        )

    good_flagged_per_sample = _safe_mean(
        [len(_flagged_dimensions(record.payload or {})) for record in good_success]
    )
    bad_flagged_per_sample = _safe_mean(
        [len(_flagged_dimensions(record.payload or {})) for record in bad_success]
    )

    hit_rates = [row["hit_rate"] for row in paired_rows if row["hit_rate"] is not None]
    overall_hit_rate = _safe_mean(hit_rates)
    total_expected = sum(
        len(row["expected_low_scoring_dimensions"]) for row in paired_rows
    )
    total_hits = sum(len(row["actual_decreased_dimensions"]) for row in paired_rows)
    weighted_hit_rate = (total_hits / total_expected) if total_expected else None

    paired_table_rows = [
        [
            row["source_id"],
            row["good_overall_across_roles"],
            row["bad_overall_across_roles"],
            row["delta_overall"],
            row["good_flagged_dimensions"],
            row["bad_flagged_dimensions"],
            row["expected_low_scoring_dimensions"],
            row["actual_decreased_dimensions"],
            row["hit_rate"],
        ]
        for row in paired_rows
    ]

    lines = [
        "# CLI Sensitivity Experiment Report",
        "",
        "## 1. Experiment Overview",
        f"- Model: `{model}`",
        f"- Good samples completed: {len(good_success)}",
        f"- Bad samples completed: {len(bad_success)}",
        f"- Failures: {len(failures)}",
        f"- Output directory: `{outdir}`",
        "",
        "## 2. Group-level Summary",
        _markdown_table(["Metric", "Good", "Bad", "Delta (Good-Bad)"], group_rows),
        "",
        "## 3. Dimension-level Summary",
        _markdown_table(
            ["Dimension", "Good Mean", "Bad Mean", "Delta (Good-Bad)"],
            dimension_rows,
        ),
        "",
        "## 4. Disagreement Summary",
        (
            f"- Average flagged dimensions per good sample: {good_flagged_per_sample:.4f}"
            if good_flagged_per_sample is not None
            else "- Average flagged dimensions per good sample: NA"
        ),
        (
            f"- Average flagged dimensions per bad sample: {bad_flagged_per_sample:.4f}"
            if bad_flagged_per_sample is not None
            else "- Average flagged dimensions per bad sample: NA"
        ),
        "",
        _markdown_table(
            ["Dimension", "Good Flag Count", "Bad Flag Count"],
            disagreement_rows,
        ),
        "",
        "## 5. Paired Comparison by Source ID",
        _markdown_table(
            [
                "Source ID",
                "Good Overall",
                "Bad Overall",
                "Delta Overall",
                "Good Flagged Dims",
                "Bad Flagged Dims",
                "Expected Low Dims",
                "Actual Decreased Dims",
                "Hit Rate",
            ],
            paired_table_rows,
        ),
        "",
        "## 6. Hit-rate Analysis",
        (
            f"- Mean per-sample hit rate: {overall_hit_rate:.4f}"
            if overall_hit_rate is not None
            else "- Mean per-sample hit rate: NA"
        ),
        (
            f"- Weighted overall hit rate: {weighted_hit_rate:.4f}"
            if weighted_hit_rate is not None
            else "- Weighted overall hit rate: NA"
        ),
    ]

    if failures:
        lines.extend(["", "## Failures"])
        for record in failures:
            lines.append(
                f"- `{record.group}` source `{record.source_id}` -> `{record.error_path}`"
            )

    return "\n".join(lines) + "\n"


def _pair_rows(
    good_records: list[SampleRunRecord], bad_records: list[SampleRunRecord]
) -> list[dict[str, Any]]:
    good_success = {
        record.source_id: record
        for record in good_records
        if record.success and record.payload is not None
    }
    bad_success = {
        record.source_id: record
        for record in bad_records
        if record.success and record.payload is not None
    }
    paired_ids = sorted(set(good_success) & set(bad_success), key=lambda value: int(value))
    paired_rows: list[dict[str, Any]] = []
    for source_id in paired_ids:
        good_record = good_success[source_id]
        bad_record = bad_success[source_id]
        expected_dims = bad_record.expected_low_scoring_dimensions or []
        actual_decreased: list[str] = []
        for dimension_id in expected_dims:
            good_value = _dimension_mean_across_roles(
                good_record.payload or {}, dimension_id
            )
            bad_value = _dimension_mean_across_roles(
                bad_record.payload or {}, dimension_id
            )
            if good_value is not None and bad_value is not None and good_value > bad_value:
                actual_decreased.append(dimension_id)
        missed = [
            dimension_id
            for dimension_id in expected_dims
            if dimension_id not in actual_decreased
        ]
        hit_rate = (len(actual_decreased) / len(expected_dims)) if expected_dims else None
        good_overall = float(good_record.payload["overall_across_roles"])
        bad_overall = float(bad_record.payload["overall_across_roles"])
        paired_rows.append(
            {
                "source_id": source_id,
                "section_header": bad_record.section_header or good_record.section_header,
                "badness_type": bad_record.badness_type,
                "good_overall_across_roles": good_overall,
                "bad_overall_across_roles": bad_overall,
                "delta_overall": good_overall - bad_overall,
                "good_flagged_dimensions": _flagged_dimensions(good_record.payload or {}),
                "bad_flagged_dimensions": _flagged_dimensions(bad_record.payload or {}),
                "expected_low_scoring_dimensions": expected_dims,
                "actual_decreased_dimensions": actual_decreased,
                "missed_expected_dimensions": missed,
                "hit_rate": hit_rate,
            }
        )
    return paired_rows


def run_experiment(args: argparse.Namespace) -> int:
    good_file = Path(args.good_file)
    bad_file = Path(args.bad_file)
    outdir = _repo_path(args.outdir)
    outputs_good_dir = outdir / "outputs" / "good"
    outputs_bad_dir = outdir / "outputs" / "bad"
    outdir.mkdir(parents=True, exist_ok=True)

    good_samples = parse_good_summaries(good_file)
    bad_samples = parse_bad_summaries(bad_file)

    if args.max_samples is not None:
        good_samples = good_samples[: args.max_samples]
        bad_samples = bad_samples[: args.max_samples]

    good_records: list[SampleRunRecord] = []
    for sample in good_samples:
        record = _run_one_sample(
            group="good",
            source_id=sample.source_id,
            section_header=sample.section_header,
            summary_text=sample.summary_text,
            python_bin=args.python_bin,
            model=args.model,
            outputs_dir=outputs_good_dir,
            pretty=args.pretty,
            resume=args.resume,
        )
        good_records.append(record)
        time.sleep(SLEEP_SECONDS)

    bad_records: list[SampleRunRecord] = []
    for sample in bad_samples:
        record = _run_one_sample(
            group="bad",
            source_id=sample.source_id,
            section_header=sample.section_header,
            summary_text=sample.bad_summary_text,
            python_bin=args.python_bin,
            model=args.model,
            outputs_dir=outputs_bad_dir,
            pretty=args.pretty,
            resume=args.resume,
            expected_low_scoring_dimensions=sample.expected_low_scoring_dimensions,
            badness_type=sample.badness_type,
        )
        bad_records.append(record)
        time.sleep(SLEEP_SECONDS)

    paired_rows = _pair_rows(good_records, bad_records)
    report_text = _build_report(
        model=args.model,
        outdir=outdir,
        good_records=good_records,
        bad_records=bad_records,
        paired_rows=paired_rows,
    )
    report_path = outdir / "report.md"
    report_path.write_text(report_text, encoding="utf-8")
    _summarize_to_csv(paired_rows, outdir / "summary.csv")

    if args.pretty:
        print(report_text)
    else:
        print(f"Report written to {report_path}")
        print(f"Summary CSV written to {outdir / 'summary.csv'}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the existing grading CLI across good/bad summary batches."
    )
    parser.add_argument("--model", default="gpt-4o-mini")
    parser.add_argument("--outdir", default="reports/cli_sensitivity_experiment")
    parser.add_argument("--python-bin", default=sys.executable)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--max-samples", type=int)
    parser.add_argument("--pretty", action="store_true")
    parser.add_argument("--good-file", default=str(DEFAULT_GOOD_FILE))
    parser.add_argument("--bad-file", default=str(DEFAULT_BAD_FILE))
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return run_experiment(args)


if __name__ == "__main__":
    raise SystemExit(main())
