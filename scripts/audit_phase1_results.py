from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.run_cli_sensitivity_experiment import (  # noqa: E402
    DEFAULT_BAD_FILE,
    DIMENSION_IDS,
    _extract_bullet_list,
    parse_bad_summaries,
)

RESULTS_ROOT = REPO_ROOT / "reports" / "phase1"
ROLE_NAMES = ["Physician", "Triage Nurse", "Bedside Nurse"]
DIMENSION_LABELS = {
    "factual_accuracy": "Factual Accuracy",
    "relevant_chronic_problem_coverage": "Relevant Chronic Problem Coverage",
    "organized_by_condition": "Organized by Condition",
    "timeline_evolution": "Timeline and Evolution",
    "recent_changes_highlighted": "Recent Changes Highlighted",
    "focused_not_cluttered": "Focused and Not Cluttered",
    "usefulness_for_decision_making": "Usefulness for Decision-Making",
    "clarity_readability_formatting": "Clarity, Readability, and Formatting",
}


@dataclass(frozen=True)
class BadAnnotation:
    source_id: str
    section_header: str | None
    badness_type: str | None
    expected_low_scoring_dimensions: list[str]
    removal_notes: list[str]
    replacement_notes: list[str]
    change_notes: list[str]
    degradation_reason: str


@dataclass
class LoadedOutput:
    source_id: str
    path: Path
    payload: dict[str, Any] | None
    issues: list[str]


@dataclass
class ExpectedDimensionAudit:
    dimension: str
    good_mean: float | None
    bad_mean: float | None
    delta: float | None
    status: str


@dataclass
class PairAudit:
    source_id: str
    annotation: BadAnnotation
    good_output: LoadedOutput | None
    bad_output: LoadedOutput | None
    good_overall: float | None
    bad_overall: float | None
    delta_overall: float | None
    dimension_deltas: dict[str, float | None]
    expected_dimension_audit: list[ExpectedDimensionAudit]
    hit_count: int
    hit_rate: float | None
    good_flagged_count: int | None
    bad_flagged_count: int | None
    good_flagged_dimensions: list[str]
    bad_flagged_dimensions: list[str]
    issues: list[str]
    interpretation: str


@dataclass(frozen=True)
class ResultsSelection:
    path: Path
    good_count: int
    bad_count: int
    has_report: bool
    has_summary: bool
    selection_note: str


BAD_SECTION_LABELS = {
    "WHAT I REMOVED",
    "WHAT I REPLACED",
    "WHAT I CHANGED",
    "EXPECTED LOW-SCORING DIMENSIONS",
}


def _sample_sort_key(source_id: str) -> tuple[int, str]:
    try:
        return (0, f"{int(source_id):09d}")
    except ValueError:
        return (1, source_id)


def _format_float(value: float | None, digits: int = 4) -> str:
    if value is None:
        return "NA"
    return f"{value:.{digits}f}"


def _format_float_short(value: float | None) -> str:
    if value is None:
        return "NA"
    return f"{value:.2f}"


def _shorten_bullets(items: list[str], max_items: int = 2, max_len: int = 80) -> str:
    trimmed = [item.rstrip(".") for item in items[:max_items] if item.strip()]
    if not trimmed:
        return ""
    rendered = "; ".join(trimmed)
    if len(rendered) > max_len:
        return rendered[: max_len - 3].rstrip() + "..."
    return rendered


def detect_results_dir(reports_root: Path) -> ResultsSelection:
    candidates: list[ResultsSelection] = []
    for child in reports_root.glob("*/run"):
        if not child.is_dir():
            continue
        good_dir = child / "outputs" / "good"
        bad_dir = child / "outputs" / "bad"
        if not good_dir.is_dir() or not bad_dir.is_dir():
            continue
        good_count = len(list(good_dir.glob("source_*.json")))
        bad_count = len(list(bad_dir.glob("source_*.json")))
        has_report = (child / "report.md").is_file()
        has_summary = (child / "summary.csv").is_file()
        label = child.parent.name
        selection_note = (
            f"candidate={label}/run, good_json={good_count}, bad_json={bad_count}, "
            f"report={'yes' if has_report else 'no'}, summary={'yes' if has_summary else 'no'}"
        )
        candidates.append(
            ResultsSelection(
                path=child,
                good_count=good_count,
                bad_count=bad_count,
                has_report=has_report,
                has_summary=has_summary,
                selection_note=selection_note,
            )
        )
    if not candidates:
        raise FileNotFoundError(
            f"No Phase 1 result directory found under {reports_root}. Expected folders like reports/phase1/<label>/run with outputs/good and outputs/bad."
        )
    candidates.sort(
        key=lambda item: (
            min(item.good_count, item.bad_count),
            item.good_count + item.bad_count,
            int(item.has_report),
            int(item.has_summary),
            item.path.stat().st_mtime,
        ),
        reverse=True,
    )
    selected = candidates[0]
    notes = [selected.selection_note]
    if len(candidates) > 1:
        notes.append(
            "Assumption: selected the most complete result set by JSON coverage, supporting files, and newest timestamp."
        )
    else:
        notes.append("Assumption: this is the only result folder with paired JSON outputs.")
    return ResultsSelection(
        path=selected.path,
        good_count=selected.good_count,
        bad_count=selected.bad_count,
        has_report=selected.has_report,
        has_summary=selected.has_summary,
        selection_note=" ".join(notes),
    )


def parse_bad_annotations(path: Path) -> dict[str, BadAnnotation]:
    text = path.read_text(encoding="utf-8")
    parsed_base = {item.source_id: item for item in parse_bad_summaries(path)}
    blocks = [block.strip() for block in text.split("======================================================================") if block.strip()]
    annotations: dict[str, BadAnnotation] = {}
    for block in blocks:
        if "BAD SAMPLE" not in block:
            continue
        lines = [line.rstrip() for line in block.splitlines()]
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
            continue
        removal_notes = _extract_bullet_list(lines, "WHAT I REMOVED")
        replacement_notes = _extract_bullet_list(lines, "WHAT I REPLACED")
        change_notes = _extract_bullet_list(lines, "WHAT I CHANGED")
        expected_dims = parsed_base[source_id].expected_low_scoring_dimensions if source_id in parsed_base else []
        reason_parts: list[str] = []
        removed_text = _shorten_bullets(removal_notes)
        replaced_text = _shorten_bullets(replacement_notes, max_items=1)
        changed_text = _shorten_bullets(change_notes, max_items=1)
        if removed_text:
            reason_parts.append(f"Removed key details such as {removed_text}.")
        if replaced_text:
            reason_parts.append(f"Replaced specifics with broader wording ({replaced_text}).")
        if changed_text:
            reason_parts.append(f"Additional change: {changed_text}.")
        degradation_reason = " ".join(reason_parts) or "Bad summary annotations describe a targeted degradation of the original summary."
        annotations[source_id] = BadAnnotation(
            source_id=source_id,
            section_header=section_header,
            badness_type=badness_type,
            expected_low_scoring_dimensions=expected_dims,
            removal_notes=removal_notes,
            replacement_notes=replacement_notes,
            change_notes=change_notes,
            degradation_reason=degradation_reason,
        )
    return annotations


def load_outputs(group_dir: Path) -> dict[str, LoadedOutput]:
    loaded: dict[str, LoadedOutput] = {}
    for path in sorted(group_dir.glob("source_*.json")):
        source_id = path.stem.split("_", 1)[1]
        issues: list[str] = []
        payload: dict[str, Any] | None = None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            issues.append(f"Invalid JSON: {exc}")
        loaded[source_id] = LoadedOutput(
            source_id=source_id,
            path=path,
            payload=payload,
            issues=issues,
        )
    return loaded


def _extract_role_map(payload: dict[str, Any], issues: list[str]) -> dict[str, dict[str, Any]]:
    scorecards = payload.get("per_role_scorecards")
    if not isinstance(scorecards, list):
        issues.append("Missing per_role_scorecards list.")
        return {}
    role_map: dict[str, dict[str, Any]] = {}
    for item in scorecards:
        if not isinstance(item, dict):
            continue
        role_name = item.get("role")
        if isinstance(role_name, str):
            role_map[role_name] = item
    for role_name in ROLE_NAMES:
        if role_name not in role_map:
            issues.append(f"Missing role scorecard: {role_name}.")
    return role_map


def _extract_overall(payload: dict[str, Any], issues: list[str]) -> float | None:
    overall = payload.get("overall_across_roles")
    if isinstance(overall, (int, float)):
        return float(overall)
    issues.append("Missing numeric overall_across_roles.")
    return None


def _mean_dimension_scores(payload: dict[str, Any], issues: list[str]) -> dict[str, float | None]:
    role_map = _extract_role_map(payload, issues)
    means: dict[str, float | None] = {}
    for dim in DIMENSION_IDS:
        values: list[float] = []
        for role_name in ROLE_NAMES:
            scorecard = role_map.get(role_name)
            if not scorecard:
                continue
            scores = scorecard.get("scores")
            if not isinstance(scores, dict):
                issues.append(f"Role {role_name} missing scores dict for dimension {dim}.")
                continue
            value = scores.get(dim)
            if isinstance(value, (int, float)):
                values.append(float(value))
            else:
                issues.append(f"Role {role_name} missing numeric score for dimension {dim}.")
        means[dim] = mean(values) if values else None
    return means


def _flagged_dimensions(payload: dict[str, Any], issues: list[str]) -> list[str]:
    disagreement = payload.get("disagreement_map")
    if not isinstance(disagreement, dict):
        issues.append("Missing disagreement_map.")
        return []
    flagged: list[str] = []
    for dim, item in disagreement.items():
        if not isinstance(item, dict):
            issues.append(f"Malformed disagreement entry for {dim}.")
            continue
        if item.get("flag") is True:
            flagged.append(dim)
    return sorted(flagged, key=_sample_sort_key)


def _build_expected_audit(
    annotation: BadAnnotation,
    good_means: dict[str, float | None],
    bad_means: dict[str, float | None],
) -> tuple[list[ExpectedDimensionAudit], int]:
    audits: list[ExpectedDimensionAudit] = []
    hit_count = 0
    for dim in annotation.expected_low_scoring_dimensions:
        good_mean = good_means.get(dim)
        bad_mean = bad_means.get(dim)
        if good_mean is None or bad_mean is None:
            delta = None
            status = "ISSUE"
        else:
            delta = good_mean - bad_mean
            if delta > 0:
                status = "HIT"
                hit_count += 1
            else:
                status = "MISS"
        audits.append(
            ExpectedDimensionAudit(
                dimension=dim,
                good_mean=good_mean,
                bad_mean=bad_mean,
                delta=delta,
                status=status,
            )
        )
    return audits, hit_count


def _interpret_pair(
    annotation: BadAnnotation,
    delta_overall: float | None,
    expected_dimension_audit: list[ExpectedDimensionAudit],
    dimension_deltas: dict[str, float | None],
) -> str:
    hit_dims = [item.dimension for item in expected_dimension_audit if item.status == "HIT"]
    miss_dims = [item.dimension for item in expected_dimension_audit if item.status == "MISS"]
    issue_dims = [item.dimension for item in expected_dimension_audit if item.status == "ISSUE"]
    strongest_drops = [
        dim for dim, delta in sorted(
            dimension_deltas.items(), key=lambda pair: pair[1] if pair[1] is not None else -999, reverse=True
        )
        if delta is not None and delta > 0
    ][:3]
    if not expected_dimension_audit:
        alignment = "No expected low-scoring dimensions were provided, so alignment could not be assessed."
    else:
        hit_rate = len(hit_dims) / len(expected_dimension_audit)
        if hit_rate >= 0.67:
            alignment = "Observed score drops were broadly consistent with the intended degradation."
        elif hit_rate >= 0.34:
            alignment = "Observed score drops were partially consistent with the intended degradation."
        else:
            alignment = "Observed score drops showed weak alignment with the intended degradation."
    parts = [annotation.degradation_reason, alignment]
    if strongest_drops:
        rendered = ", ".join(DIMENSION_LABELS.get(dim, dim) for dim in strongest_drops)
        parts.append(f"The largest observed decreases were in {rendered}.")
    if delta_overall is not None:
        if delta_overall > 0:
            parts.append("The bad summary received a lower overall score than the matched good summary.")
        elif delta_overall < 0:
            parts.append("The bad summary unexpectedly received a higher overall score than the matched good summary.")
        else:
            parts.append("The good and bad summaries received the same overall score.")
    if miss_dims:
        rendered = ", ".join(DIMENSION_LABELS.get(dim, dim) for dim in miss_dims)
        parts.append(f"Expected decreases were missed for {rendered}.")
    if issue_dims:
        rendered = ", ".join(DIMENSION_LABELS.get(dim, dim) for dim in issue_dims)
        parts.append(f"Audit issues were recorded for {rendered}.")
    return " ".join(parts)


def audit_pairs(
    annotations: dict[str, BadAnnotation],
    good_outputs: dict[str, LoadedOutput],
    bad_outputs: dict[str, LoadedOutput],
) -> tuple[list[PairAudit], list[str]]:
    all_source_ids = sorted(set(annotations) | set(good_outputs) | set(bad_outputs), key=_sample_sort_key)
    pair_audits: list[PairAudit] = []
    missing_messages: list[str] = []
    for source_id in all_source_ids:
        annotation = annotations.get(source_id)
        if annotation is None:
            missing_messages.append(f"Missing bad-summary annotation for Source ID {source_id}.")
            continue
        good_output = good_outputs.get(source_id)
        bad_output = bad_outputs.get(source_id)
        issues: list[str] = []
        if good_output is None:
            issues.append(f"Missing good output JSON for Source ID {source_id}.")
        if bad_output is None:
            issues.append(f"Missing bad output JSON for Source ID {source_id}.")
        if good_output is None or bad_output is None:
            pair_audits.append(
                PairAudit(
                    source_id=source_id,
                    annotation=annotation,
                    good_output=good_output,
                    bad_output=bad_output,
                    good_overall=None,
                    bad_overall=None,
                    delta_overall=None,
                    dimension_deltas={dim: None for dim in DIMENSION_IDS},
                    expected_dimension_audit=[],
                    hit_count=0,
                    hit_rate=None,
                    good_flagged_count=None,
                    bad_flagged_count=None,
                    good_flagged_dimensions=[],
                    bad_flagged_dimensions=[],
                    issues=issues,
                    interpretation="Missing paired JSON output prevented a full audit for this Source ID.",
                )
            )
            continue
        issues.extend(good_output.issues)
        issues.extend(bad_output.issues)
        good_payload = good_output.payload or {}
        bad_payload = bad_output.payload or {}
        good_overall = _extract_overall(good_payload, issues)
        bad_overall = _extract_overall(bad_payload, issues)
        delta_overall = None if good_overall is None or bad_overall is None else good_overall - bad_overall
        good_means = _mean_dimension_scores(good_payload, issues)
        bad_means = _mean_dimension_scores(bad_payload, issues)
        dimension_deltas = {
            dim: None if good_means.get(dim) is None or bad_means.get(dim) is None else good_means[dim] - bad_means[dim]
            for dim in DIMENSION_IDS
        }
        expected_dimension_audit, hit_count = _build_expected_audit(annotation, good_means, bad_means)
        hit_rate = None
        if annotation.expected_low_scoring_dimensions:
            hit_rate = hit_count / len(annotation.expected_low_scoring_dimensions)
        good_flagged_dimensions = _flagged_dimensions(good_payload, issues)
        bad_flagged_dimensions = _flagged_dimensions(bad_payload, issues)
        interpretation = _interpret_pair(annotation, delta_overall, expected_dimension_audit, dimension_deltas)
        pair_audits.append(
            PairAudit(
                source_id=source_id,
                annotation=annotation,
                good_output=good_output,
                bad_output=bad_output,
                good_overall=good_overall,
                bad_overall=bad_overall,
                delta_overall=delta_overall,
                dimension_deltas=dimension_deltas,
                expected_dimension_audit=expected_dimension_audit,
                hit_count=hit_count,
                hit_rate=hit_rate,
                good_flagged_count=len(good_flagged_dimensions),
                bad_flagged_count=len(bad_flagged_dimensions),
                good_flagged_dimensions=good_flagged_dimensions,
                bad_flagged_dimensions=bad_flagged_dimensions,
                issues=issues,
                interpretation=interpretation,
            )
        )
    return pair_audits, missing_messages


def _markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    output = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        output.append("| " + " | ".join(row) + " |")
    return "\n".join(output)


def _aggregate_summary(pair_audits: list[PairAudit]) -> dict[str, Any]:
    valid_pairs = [pair for pair in pair_audits if pair.good_output and pair.bad_output and not any(msg.startswith("Missing") for msg in pair.issues)]
    overall_deltas = [pair.delta_overall for pair in valid_pairs if pair.delta_overall is not None]
    avg_overall_delta = mean(overall_deltas) if overall_deltas else None
    total_expected = sum(len(pair.annotation.expected_low_scoring_dimensions) for pair in valid_pairs)
    total_hits = sum(pair.hit_count for pair in valid_pairs)
    overall_hit_rate = (total_hits / total_expected) if total_expected else None

    drop_counter = Counter()
    expected_counter = Counter()
    expected_hit_counter = Counter()
    expected_miss_counter = Counter()
    for pair in valid_pairs:
        for dim, delta in pair.dimension_deltas.items():
            if delta is not None and delta > 0:
                drop_counter[dim] += 1
        for item in pair.expected_dimension_audit:
            expected_counter[item.dimension] += 1
            if item.status == "HIT":
                expected_hit_counter[item.dimension] += 1
            elif item.status == "MISS":
                expected_miss_counter[item.dimension] += 1

    avg_good_flagged = mean([pair.good_flagged_count for pair in valid_pairs if pair.good_flagged_count is not None]) if valid_pairs else None
    avg_bad_flagged = mean([pair.bad_flagged_count for pair in valid_pairs if pair.bad_flagged_count is not None]) if valid_pairs else None

    return {
        "valid_pairs": valid_pairs,
        "avg_overall_delta": avg_overall_delta,
        "overall_hit_rate": overall_hit_rate,
        "total_expected": total_expected,
        "total_hits": total_hits,
        "drop_counter": drop_counter,
        "expected_counter": expected_counter,
        "expected_hit_counter": expected_hit_counter,
        "expected_miss_counter": expected_miss_counter,
        "avg_good_flagged": avg_good_flagged,
        "avg_bad_flagged": avg_bad_flagged,
    }


def write_audit_report(
    outdir: Path,
    selected_results: ResultsSelection,
    pair_audits: list[PairAudit],
    missing_messages: list[str],
    bad_file: Path,
) -> Path:
    aggregate = _aggregate_summary(pair_audits)
    valid_pairs = aggregate["valid_pairs"]
    missing_or_failed = len(pair_audits) - len(valid_pairs)
    report_lines = [
        "# Phase 1 Audit Report",
        "",
        "## 1. Overview",
        f"- Result folder used: `{selected_results.path}`",
        f"- Selection note: {selected_results.selection_note}",
        f"- Bad annotation file: `{bad_file}`",
        f"- Good output directory: `{selected_results.path / 'outputs' / 'good'}`",
        f"- Bad output directory: `{selected_results.path / 'outputs' / 'bad'}`",
        f"- Good/bad pairs successfully audited: `{len(valid_pairs)}`",
        f"- Missing or failed pairs: `{missing_or_failed}`",
    ]
    if missing_messages:
        report_lines.append(f"- Missing-data notes: {'; '.join(missing_messages)}")
    report_lines.extend([
        "",
        "## 2. Per-sample Audit",
        "",
    ])

    for pair in sorted(pair_audits, key=lambda item: _sample_sort_key(item.source_id)):
        report_lines.extend([
            f"### Source ID {pair.source_id}",
            f"- Badness type: `{pair.annotation.badness_type or 'NA'}`",
            f"- Expected low-scoring dimensions: `{', '.join(pair.annotation.expected_low_scoring_dimensions) or 'none'}`",
            f"- Degradation note: {pair.annotation.degradation_reason}",
            f"- Good overall_across_roles: `{_format_float(pair.good_overall)}`",
            f"- Bad overall_across_roles: `{_format_float(pair.bad_overall)}`",
            f"- Delta overall (good - bad): `{_format_float(pair.delta_overall)}`",
            f"- Good flagged dimensions: `{', '.join(pair.good_flagged_dimensions) or 'none'}`",
            f"- Bad flagged dimensions: `{', '.join(pair.bad_flagged_dimensions) or 'none'}`",
            f"- Hit rate: `{_format_float(pair.hit_rate)}`",
        ])
        if pair.issues:
            report_lines.append(f"- Audit issues: {'; '.join(pair.issues)}")
        if pair.expected_dimension_audit:
            rows = []
            for item in pair.expected_dimension_audit:
                rows.append([
                    item.dimension,
                    _format_float(item.good_mean),
                    _format_float(item.bad_mean),
                    _format_float(item.delta),
                    item.status,
                ])
            report_lines.extend([
                "",
                _markdown_table(
                    ["Dimension", "Good Mean", "Bad Mean", "Delta", "Result"],
                    rows,
                ),
            ])
        report_lines.extend([
            "",
            f"Interpretation: {pair.interpretation}",
            "",
        ])

    report_lines.extend([
        "## 3. Aggregate Summary",
        f"- Average overall delta across audited pairs: `{_format_float(aggregate['avg_overall_delta'])}`",
        f"- Overall hit rate across all expected dimensions: `{_format_float(aggregate['overall_hit_rate'])}` ({aggregate['total_hits']}/{aggregate['total_expected']})",
        f"- Average flagged dimensions per good summary: `{_format_float(aggregate['avg_good_flagged'])}`",
        f"- Average flagged dimensions per bad summary: `{_format_float(aggregate['avg_bad_flagged'])}`",
        "",
    ])

    drop_rows = [
        [dim, str(count)]
        for dim, count in aggregate["drop_counter"].most_common()
    ]
    if drop_rows:
        report_lines.extend([
            "Dimensions most consistently lower in bad summaries (count of pairs with good > bad):",
            "",
            _markdown_table(["Dimension", "Drop Count"], drop_rows),
            "",
        ])

    expected_rows = []
    for dim in DIMENSION_IDS:
        expected_count = aggregate["expected_counter"].get(dim, 0)
        if not expected_count:
            continue
        hit_count = aggregate["expected_hit_counter"].get(dim, 0)
        miss_count = aggregate["expected_miss_counter"].get(dim, 0)
        hit_rate = hit_count / expected_count if expected_count else None
        expected_rows.append([
            dim,
            str(expected_count),
            str(hit_count),
            str(miss_count),
            _format_float(hit_rate),
        ])
    if expected_rows:
        report_lines.extend([
            "Expected-dimension performance:",
            "",
            _markdown_table(["Dimension", "Expected Count", "Hit Count", "Miss Count", "Hit Rate"], expected_rows),
            "",
        ])

    report_lines.extend([
        "## 4. Final Conclusion",
    ])

    avg_delta = aggregate["avg_overall_delta"]
    overall_hit_rate = aggregate["overall_hit_rate"]
    if (avg_delta or 0) > 0.2 and (overall_hit_rate or 0) >= 0.6:
        conclusion = (
            "Phase 1 results generally aligned with the intended degradations. The pipeline appears reasonably sensitive to bad summary quality, especially in the dimensions that were explicitly targeted."
        )
    elif (overall_hit_rate or 0) >= 0.3:
        conclusion = (
            "Phase 1 results showed partial alignment with the intended degradations. The pipeline demonstrated some sensitivity, but the signal was inconsistent and overall score separation remained weak."
        )
    else:
        conclusion = (
            "Phase 1 results showed limited alignment with the intended degradations. The current pipeline did not reliably respond to bad summary quality in a consistent way."
        )
    report_lines.append(conclusion)
    strong_dims = [dim for dim, _ in aggregate["drop_counter"].most_common(3)]
    weak_dims = [
        dim
        for dim, expected in aggregate["expected_counter"].items()
        if expected > 0 and aggregate["expected_hit_counter"].get(dim, 0) == 0
    ]
    if strong_dims:
        rendered = ", ".join(DIMENSION_LABELS.get(dim, dim) for dim in strong_dims)
        report_lines.append(f"The strongest evidence of sensitivity was in {rendered}.")
    if weak_dims:
        rendered = ", ".join(DIMENSION_LABELS.get(dim, dim) for dim in weak_dims)
        report_lines.append(f"The weakest areas were {rendered}, which frequently failed to drop even when they were expected to.")

    outdir.mkdir(parents=True, exist_ok=True)
    report_path = outdir / "phase1_audit_report.md"
    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    return report_path


def write_summary_csv(outdir: Path, pair_audits: list[PairAudit]) -> Path:
    outdir.mkdir(parents=True, exist_ok=True)
    csv_path = outdir / "phase1_audit_summary.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "source_id",
                "badness_type",
                "good_overall",
                "bad_overall",
                "overall_delta",
                "expected_dims_count",
                "hit_count",
                "hit_rate",
            ],
        )
        writer.writeheader()
        for pair in sorted(pair_audits, key=lambda item: _sample_sort_key(item.source_id)):
            writer.writerow(
                {
                    "source_id": pair.source_id,
                    "badness_type": pair.annotation.badness_type or "",
                    "good_overall": _format_float(pair.good_overall),
                    "bad_overall": _format_float(pair.bad_overall),
                    "overall_delta": _format_float(pair.delta_overall),
                    "expected_dims_count": len(pair.annotation.expected_low_scoring_dimensions),
                    "hit_count": pair.hit_count,
                    "hit_rate": _format_float(pair.hit_rate),
                }
            )
    return csv_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit existing Phase 1 LENS experiment results without rerunning the pipeline.")
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=None,
        help="Optional explicit result folder. If omitted, the script auto-selects the most complete Phase 1 result set under reports/.",
    )
    parser.add_argument(
        "--bad-file",
        type=Path,
        default=DEFAULT_BAD_FILE,
        help="Bad-summary annotation file used for the sensitivity test.",
    )
    parser.add_argument(
        "--outdir",
        type=Path,
        default=None,
        help="Directory for the audit markdown report and CSV summary. Defaults to a sibling audit/ folder next to the selected run/ directory.",
    )
    args = parser.parse_args()

    if args.results_dir is None:
        selected_results = detect_results_dir(RESULTS_ROOT)
    else:
        explicit_results_dir = args.results_dir if args.results_dir.is_absolute() else (REPO_ROOT / args.results_dir)
        selected_results = ResultsSelection(
            path=explicit_results_dir,
            good_count=len(list((explicit_results_dir / "outputs" / "good").glob("source_*.json"))),
            bad_count=len(list((explicit_results_dir / "outputs" / "bad").glob("source_*.json"))),
            has_report=(explicit_results_dir / "report.md").is_file(),
            has_summary=(explicit_results_dir / "summary.csv").is_file(),
            selection_note="Assumption: result folder was provided explicitly by the user.",
        )

    bad_file = args.bad_file if args.bad_file.is_absolute() else (REPO_ROOT / args.bad_file)
    outdir = args.outdir
    if outdir is None:
        outdir = selected_results.path.parent / "audit"
    elif not outdir.is_absolute():
        outdir = REPO_ROOT / outdir

    annotations = parse_bad_annotations(bad_file)
    good_outputs = load_outputs(selected_results.path / "outputs" / "good")
    bad_outputs = load_outputs(selected_results.path / "outputs" / "bad")
    pair_audits, missing_messages = audit_pairs(annotations, good_outputs, bad_outputs)
    report_path = write_audit_report(outdir, selected_results, pair_audits, missing_messages, bad_file)
    csv_path = write_summary_csv(outdir, pair_audits)
    print(f"Audit report written to: {report_path}")
    print(f"CSV summary written to: {csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
