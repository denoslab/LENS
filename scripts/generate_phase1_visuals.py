from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

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

DIMENSION_LABELS = {
    "factual_accuracy": "Factual Accuracy",
    "relevant_chronic_problem_coverage": "Chronic Coverage",
    "organized_by_condition": "Organized by Condition",
    "timeline_evolution": "Timeline and Evolution",
    "recent_changes_highlighted": "Recent Changes",
    "focused_not_cluttered": "Focused / Not Cluttered",
    "usefulness_for_decision_making": "Decision-Making Usefulness",
    "clarity_readability_formatting": "Clarity / Readability",
}

ROLE_NAMES = ["Physician", "Triage Nurse", "Bedside Nurse"]
REPO_ROOT = Path(__file__).resolve().parents[1]
REPORTS_ROOT = REPO_ROOT / "reports"
PHASE1_REPORTS_ROOT = REPORTS_ROOT / "phase1"


@dataclass(frozen=True)
class SampleResult:
    group: str
    source_id: str
    payload: dict[str, Any]


def iter_results_dirs() -> list[Path]:
    if not PHASE1_REPORTS_ROOT.exists():
        return []
    results_dirs: list[Path] = []
    for candidate in PHASE1_REPORTS_ROOT.glob("*/run"):
        if (candidate / "outputs" / "good").is_dir() and (candidate / "outputs" / "bad").is_dir():
            results_dirs.append(candidate)
    return sorted(results_dirs)



def detect_results_dir(explicit: str | None) -> Path:
    if explicit:
        path = Path(explicit)
        return path if path.is_absolute() else (REPO_ROOT / path)

    existing = iter_results_dirs()
    if not existing:
        raise FileNotFoundError(
            f"No Phase 1 results directory found under {PHASE1_REPORTS_ROOT}. "
            "Expected folders like reports/phase1/<label>/run with outputs/good and outputs/bad."
        )
    return max(existing, key=lambda path: path.stat().st_mtime)



def default_visuals_dir(results_dir: Path) -> Path:
    return results_dir.parent / "visuals"


def load_group_results(results_dir: Path, group: str) -> list[SampleResult]:
    group_dir = results_dir / "outputs" / group
    if not group_dir.exists():
        return []

    results: list[SampleResult] = []
    for path in sorted(group_dir.glob("source_*.json"), key=lambda p: int(p.stem.split("_")[1])):
        payload = json.loads(path.read_text(encoding="utf-8"))
        source_id = path.stem.split("_")[1]
        results.append(SampleResult(group=group, source_id=source_id, payload=payload))
    return results


def pair_results(good_results: list[SampleResult], bad_results: list[SampleResult]) -> list[tuple[SampleResult, SampleResult]]:
    good_by_id = {result.source_id: result for result in good_results}
    bad_by_id = {result.source_id: result for result in bad_results}
    paired_ids = sorted(set(good_by_id) & set(bad_by_id), key=int)
    return [(good_by_id[source_id], bad_by_id[source_id]) for source_id in paired_ids]


def role_overall(payload: dict[str, Any], role_name: str) -> float | None:
    for scorecard in payload.get("per_role_scorecards", []):
        if scorecard.get("role") == role_name:
            overall = scorecard.get("overall")
            if isinstance(overall, (int, float)):
                return float(overall)
    return None


def dimension_mean_across_roles(payload: dict[str, Any], dimension_id: str) -> float | None:
    values: list[float] = []
    for scorecard in payload.get("per_role_scorecards", []):
        score = scorecard.get("scores", {}).get(dimension_id)
        if isinstance(score, (int, float)):
            values.append(float(score))
    return mean(values) if values else None


def flagged_dimensions(payload: dict[str, Any]) -> list[str]:
    return [
        dim
        for dim, item in payload.get("disagreement_map", {}).items()
        if bool(item.get("flag"))
    ]


def safe_mean(values: list[float]) -> float | None:
    return mean(values) if values else None


def compute_role_means(results: list[SampleResult]) -> dict[str, float | None]:
    role_means: dict[str, float | None] = {}
    for role_name in ROLE_NAMES:
        values = [
            role_overall(result.payload, role_name)
            for result in results
        ]
        role_means[role_name] = safe_mean([value for value in values if value is not None])
    return role_means


def compute_dimension_means(results: list[SampleResult]) -> dict[str, float | None]:
    dim_means: dict[str, float | None] = {}
    for dimension_id in DIMENSION_IDS:
        values = [
            dimension_mean_across_roles(result.payload, dimension_id)
            for result in results
        ]
        dim_means[dimension_id] = safe_mean([value for value in values if value is not None])
    return dim_means


def plot_overall_comparison(pairs: list[tuple[SampleResult, SampleResult]], outpath: Path) -> None:
    source_ids = [pair[0].source_id for pair in pairs]
    x = list(range(len(source_ids)))
    good_scores = [float(pair[0].payload.get("overall_across_roles", 0.0)) for pair in pairs]
    bad_scores = [float(pair[1].payload.get("overall_across_roles", 0.0)) for pair in pairs]

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(x, good_scores, marker="o", linewidth=2, label="Good summaries")
    ax.plot(x, bad_scores, marker="o", linewidth=2, label="Bad summaries")
    ax.set_xticks(x)
    ax.set_xticklabels(source_ids)
    ax.set_xlabel("Source ID")
    ax.set_ylabel("overall_across_roles")
    ax.set_title("Overall Score Comparison: Good vs Bad Summaries")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(outpath, dpi=200)
    plt.close(fig)


def plot_role_comparison(good_role_means: dict[str, float | None], bad_role_means: dict[str, float | None], outpath: Path) -> None:
    roles = ROLE_NAMES
    x = list(range(len(roles)))
    good_values = [good_role_means.get(role) or 0.0 for role in roles]
    bad_values = [bad_role_means.get(role) or 0.0 for role in roles]

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(x, good_values, marker="o", linewidth=2, label="Good summaries")
    ax.plot(x, bad_values, marker="o", linewidth=2, label="Bad summaries")
    ax.set_xticks(x)
    ax.set_xticklabels(roles)
    ax.set_xlabel("Role")
    ax.set_ylabel("Mean overall score")
    ax.set_title("Average Per-Role Scores: Good vs Bad Summaries")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(outpath, dpi=200)
    plt.close(fig)


def plot_dimension_comparison(good_dim_means: dict[str, float | None], bad_dim_means: dict[str, float | None], outpath: Path) -> None:
    dimensions = DIMENSION_IDS
    x = list(range(len(dimensions)))
    good_values = [good_dim_means.get(dim) or 0.0 for dim in dimensions]
    bad_values = [bad_dim_means.get(dim) or 0.0 for dim in dimensions]
    labels = [DIMENSION_LABELS[dim] for dim in dimensions]

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(x, good_values, marker="o", linewidth=2, label="Good summaries")
    ax.plot(x, bad_values, marker="o", linewidth=2, label="Bad summaries")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=30, ha="right")
    ax.set_xlabel("Rubric dimension")
    ax.set_ylabel("Mean score across roles and samples")
    ax.set_title("Dimension-Level Mean Scores: Good vs Bad Summaries")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(outpath, dpi=200)
    plt.close(fig)


def plot_disagreement_comparison(pairs: list[tuple[SampleResult, SampleResult]], outpath: Path) -> None:
    source_ids = [pair[0].source_id for pair in pairs]
    x = list(range(len(source_ids)))
    good_counts = [len(flagged_dimensions(pair[0].payload)) for pair in pairs]
    bad_counts = [len(flagged_dimensions(pair[1].payload)) for pair in pairs]

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(x, good_counts, marker="o", linewidth=2, label="Good summaries")
    ax.plot(x, bad_counts, marker="o", linewidth=2, label="Bad summaries")
    ax.set_xticks(x)
    ax.set_xticklabels(source_ids)
    ax.set_xlabel("Source ID")
    ax.set_ylabel("Flagged disagreement dimensions")
    ax.set_title("Disagreement Comparison: Good vs Bad Summaries")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(outpath, dpi=200)
    plt.close(fig)


def build_short_report(
    *,
    results_dir: Path,
    good_results: list[SampleResult],
    bad_results: list[SampleResult],
    pairs: list[tuple[SampleResult, SampleResult]],
    outpath: Path,
) -> None:
    good_overall = safe_mean([
        float(result.payload.get("overall_across_roles", 0.0))
        for result in good_results
        if isinstance(result.payload.get("overall_across_roles"), (int, float))
    ])
    bad_overall = safe_mean([
        float(result.payload.get("overall_across_roles", 0.0))
        for result in bad_results
        if isinstance(result.payload.get("overall_across_roles"), (int, float))
    ])

    good_role_means = compute_role_means(good_results)
    bad_role_means = compute_role_means(bad_results)
    role_deltas = {
        role: (good_role_means[role] - bad_role_means[role])
        for role in ROLE_NAMES
        if good_role_means[role] is not None and bad_role_means[role] is not None
    }
    clearest_role = max(role_deltas, key=lambda role: abs(role_deltas[role])) if role_deltas else "NA"

    good_dim_means = compute_dimension_means(good_results)
    bad_dim_means = compute_dimension_means(bad_results)
    dim_deltas = {
        dim: (good_dim_means[dim] - bad_dim_means[dim])
        for dim in DIMENSION_IDS
        if good_dim_means[dim] is not None and bad_dim_means[dim] is not None
    }
    largest_drop_dims = sorted(dim_deltas.items(), key=lambda item: item[1], reverse=True)[:3]
    largest_drop_text = ", ".join(
        f"{DIMENSION_LABELS[dim]} ({delta:.3f})" for dim, delta in largest_drop_dims
    )

    good_disagreement = safe_mean([len(flagged_dimensions(result.payload)) for result in good_results])
    bad_disagreement = safe_mean([len(flagged_dimensions(result.payload)) for result in bad_results])

    better_pairs = sum(
        1
        for good_result, bad_result in pairs
        if float(good_result.payload.get("overall_across_roles", 0.0))
        > float(bad_result.payload.get("overall_across_roles", 0.0))
    )
    total_pairs = len(pairs)

    conclusion = (
        "The Phase 1 pilot shows partial sensitivity: LENS captured some expected drops in timeline and recent-change-related quality, "
        "but it did not consistently separate good summaries from degraded summaries at the overall level."
    )

    report = f"""# Phase 1 Short Report

## 1. Purpose
Phase 1 tested whether the Role-Aware Multi-Agent Grading Pipeline could distinguish original clinical summaries from intentionally degraded bad summaries without running a new human annotation study.

## 2. Key Results
- Final Phase 1 result set: `{results_dir}`
- Completed samples: {len(good_results)} good summaries and {len(bad_results)} bad summaries
- Mean overall score across roles:
  - Good summaries: {good_overall:.4f}
  - Bad summaries: {bad_overall:.4f}
- Good summaries scored higher than bad summaries in {better_pairs} of {total_pairs} matched pairs.
- The role with the clearest separation was **{clearest_role}**.
- The largest dimension-level drops from good to bad were: {largest_drop_text}.
- Average flagged disagreement dimensions per sample:
  - Good summaries: {good_disagreement:.4f}
  - Bad summaries: {bad_disagreement:.4f}

## 3. Interpretation
These results suggest that the current LENS configuration is somewhat sensitive to specific types of summary degradation, especially for timeline and recent-change information. However, the overall separation between good and bad summaries remained small, and several bad summaries still received comparable or higher scores. This indicates that the current scoring setup has some useful signal, but its discriminative sensitivity is not yet strong enough to fully support reliable quality separation.

## 4. Conclusion
{conclusion}
"""
    outpath.write_text(report, encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate Phase 1 charts and a short markdown report from existing experiment outputs.")
    parser.add_argument("--results-dir", default=None, help="Existing experiment result directory. If omitted, the newest Phase 1 result set is selected automatically.")
    parser.add_argument("--outdir", default=None, help="Directory for charts and the short report. Defaults to a sibling visuals/ folder next to the selected run/ directory.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    results_dir = detect_results_dir(args.results_dir)
    if args.outdir is None:
        outdir = default_visuals_dir(results_dir)
    else:
        outdir = Path(args.outdir)
        if not outdir.is_absolute():
            outdir = REPO_ROOT / outdir
    outdir.mkdir(parents=True, exist_ok=True)

    good_results = load_group_results(results_dir, "good")
    bad_results = load_group_results(results_dir, "bad")
    pairs = pair_results(good_results, bad_results)
    if not pairs:
        raise RuntimeError(f"No paired good/bad results found in {results_dir}")

    good_role_means = compute_role_means(good_results)
    bad_role_means = compute_role_means(bad_results)
    good_dim_means = compute_dimension_means(good_results)
    bad_dim_means = compute_dimension_means(bad_results)

    plot_overall_comparison(pairs, outdir / "overall_score_comparison.png")
    plot_role_comparison(good_role_means, bad_role_means, outdir / "per_role_comparison.png")
    plot_dimension_comparison(good_dim_means, bad_dim_means, outdir / "dimension_score_comparison.png")
    plot_disagreement_comparison(pairs, outdir / "disagreement_comparison.png")
    build_short_report(
        results_dir=results_dir,
        good_results=good_results,
        bad_results=bad_results,
        pairs=pairs,
        outpath=outdir / "phase1_short_report.md",
    )

    print(f"Charts and report written to {outdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
