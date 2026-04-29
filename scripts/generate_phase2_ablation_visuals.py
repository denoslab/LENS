from __future__ import annotations

import csv
import json
from pathlib import Path
from statistics import mean

import matplotlib.pyplot as plt

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_GROUNDED_DIR = PROJECT_ROOT / 'reports/phase2/source_grounded_demo'
SUMMARY_ONLY_DIR = PROJECT_ROOT / 'reports/phase2/source_grounded_demo_summary_only'
OUTDIR = PROJECT_ROOT / 'reports/phase2/ablation_visuals'


def _read_summary_rows(report_dir: Path) -> list[dict[str, str]]:
    with (report_dir / 'summary.csv').open(encoding='utf-8') as handle:
        return list(csv.DictReader(handle))


def _read_run_meta(report_dir: Path) -> dict:
    return json.loads((report_dir / 'run_meta.json').read_text(encoding='utf-8'))


def _group_by_variant_type(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        grouped.setdefault(row['variant_type'], []).append(row)
    return grouped


def _mean_float(rows: list[dict[str, str]], field: str) -> float:
    return mean(float(row[field]) for row in rows)


def _mean_bool_string(rows: list[dict[str, str]], field: str) -> float:
    return mean(1.0 if row[field] == 'True' else 0.0 for row in rows)


def _build_metrics(report_dir: Path) -> dict:
    rows = _read_summary_rows(report_dir)
    meta = _read_run_meta(report_dir)
    grouped = _group_by_variant_type(rows)
    return {
        'meta': meta,
        'rows': rows,
        'overall_means': {
            variant_type: _mean_float(variant_rows, 'overall')
            for variant_type, variant_rows in grouped.items()
        },
        'hit_rate_means': {
            variant_type: _mean_float(variant_rows, 'hit_rate')
            for variant_type, variant_rows in grouped.items()
            if variant_type != 'reference'
        },
        'wrong_patient_detection_rate': _mean_bool_string(
            grouped['wrong_patient_mismatch'], 'wrong_patient_suspected'
        ),
    }


def _write_comparison_csv(path: Path, source_grounded: dict, summary_only: dict) -> None:
    rows = [
        {
            'metric_group': 'overall_mean',
            'metric_name': 'reference',
            'source_grounded': round(source_grounded['overall_means']['reference'], 4),
            'summary_only': round(summary_only['overall_means']['reference'], 4),
        },
        {
            'metric_group': 'overall_mean',
            'metric_name': 'safety_critical_omission',
            'source_grounded': round(source_grounded['overall_means']['safety_critical_omission'], 4),
            'summary_only': round(summary_only['overall_means']['safety_critical_omission'], 4),
        },
        {
            'metric_group': 'overall_mean',
            'metric_name': 'wrong_patient_mismatch',
            'source_grounded': round(source_grounded['overall_means']['wrong_patient_mismatch'], 4),
            'summary_only': round(summary_only['overall_means']['wrong_patient_mismatch'], 4),
        },
        {
            'metric_group': 'hit_rate_mean',
            'metric_name': 'safety_critical_omission',
            'source_grounded': round(source_grounded['hit_rate_means']['safety_critical_omission'], 4),
            'summary_only': round(summary_only['hit_rate_means']['safety_critical_omission'], 4),
        },
        {
            'metric_group': 'hit_rate_mean',
            'metric_name': 'wrong_patient_mismatch',
            'source_grounded': round(source_grounded['hit_rate_means']['wrong_patient_mismatch'], 4),
            'summary_only': round(summary_only['hit_rate_means']['wrong_patient_mismatch'], 4),
        },
        {
            'metric_group': 'detection_rate',
            'metric_name': 'wrong_patient_suspected',
            'source_grounded': round(source_grounded['wrong_patient_detection_rate'], 4),
            'summary_only': round(summary_only['wrong_patient_detection_rate'], 4),
        },
    ]
    with path.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _make_plot(path: Path, source_grounded: dict, summary_only: dict) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.8))
    bar_width = 0.35
    sg_color = '#1f5aa6'
    so_color = '#9aa6b2'

    overall_categories = ['Reference', 'Safety omission', 'Wrong patient']
    overall_keys = ['reference', 'safety_critical_omission', 'wrong_patient_mismatch']
    x = list(range(len(overall_categories)))
    sg_vals = [source_grounded['overall_means'][k] for k in overall_keys]
    so_vals = [summary_only['overall_means'][k] for k in overall_keys]
    axes[0].bar([i - bar_width / 2 for i in x], sg_vals, width=bar_width, color=sg_color, label='Source-grounded')
    axes[0].bar([i + bar_width / 2 for i in x], so_vals, width=bar_width, color=so_color, label='Summary-only')
    axes[0].set_xticks(x, overall_categories, rotation=15)
    axes[0].set_ylim(0, 5.2)
    axes[0].set_ylabel('Mean overall score')
    axes[0].set_title('Overall Score Comparison')
    axes[0].grid(axis='y', linestyle='--', alpha=0.3)

    hit_categories = ['Safety omission', 'Wrong patient']
    hit_keys = ['safety_critical_omission', 'wrong_patient_mismatch']
    x2 = list(range(len(hit_categories)))
    sg_hit = [source_grounded['hit_rate_means'][k] for k in hit_keys]
    so_hit = [summary_only['hit_rate_means'][k] for k in hit_keys]
    axes[1].bar([i - bar_width / 2 for i in x2], sg_hit, width=bar_width, color=sg_color)
    axes[1].bar([i + bar_width / 2 for i in x2], so_hit, width=bar_width, color=so_color)
    axes[1].set_xticks(x2, hit_categories, rotation=15)
    axes[1].set_ylim(0, 1.05)
    axes[1].set_ylabel('Mean hit rate')
    axes[1].set_title('Hit Rate Comparison')
    axes[1].grid(axis='y', linestyle='--', alpha=0.3)

    x3 = [0]
    axes[2].bar([i - bar_width / 2 for i in x3], [source_grounded['wrong_patient_detection_rate']], width=bar_width, color=sg_color)
    axes[2].bar([i + bar_width / 2 for i in x3], [summary_only['wrong_patient_detection_rate']], width=bar_width, color=so_color)
    axes[2].set_xticks(x3, ['Wrong-patient detection'])
    axes[2].set_ylim(0, 1.05)
    axes[2].set_ylabel('Detection rate')
    axes[2].set_title('Wrong-Patient Detection')
    axes[2].grid(axis='y', linestyle='--', alpha=0.3)

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc='upper center', ncol=2, frameon=False, bbox_to_anchor=(0.5, 1.04))
    fig.suptitle('Phase 2 Ablation: Source-Grounded vs Summary-Only', fontsize=15, fontweight='bold', y=1.08)
    fig.tight_layout()
    fig.savefig(path, dpi=220, bbox_inches='tight')
    plt.close(fig)


def _write_slide_markdown(path: Path, source_grounded: dict, summary_only: dict) -> None:
    sg_ref = source_grounded['overall_means']['reference']
    sg_omit = source_grounded['overall_means']['safety_critical_omission']
    sg_wrong = source_grounded['overall_means']['wrong_patient_mismatch']
    so_ref = summary_only['overall_means']['reference']
    so_omit = summary_only['overall_means']['safety_critical_omission']
    so_wrong = summary_only['overall_means']['wrong_patient_mismatch']

    lines = [
        '# Slide Title',
        'Phase 2 Ablation: Source-Grounded vs Summary-Only',
        '',
        '# Main Message',
        'Adding the patient source record made LENS much more sensitive to omission and wrong-patient errors.',
        '',
        '# Left-Side Bullets',
        f'- Source-grounded overall means: reference {sg_ref:.2f}, omission {sg_omit:.2f}, wrong-patient {sg_wrong:.2f}',
        f'- Summary-only overall means: reference {so_ref:.2f}, omission {so_omit:.2f}, wrong-patient {so_wrong:.2f}',
        f'- Hit rate improved from {summary_only["hit_rate_means"]["safety_critical_omission"]:.2f} to {source_grounded["hit_rate_means"]["safety_critical_omission"]:.2f} for safety omission',
        f'- Hit rate improved from {summary_only["hit_rate_means"]["wrong_patient_mismatch"]:.2f} to {source_grounded["hit_rate_means"]["wrong_patient_mismatch"]:.2f} for wrong-patient mismatch',
        f'- Wrong-patient detection improved from {summary_only["wrong_patient_detection_rate"]:.0%} to {source_grounded["wrong_patient_detection_rate"]:.0%}',
        '',
        '# Figure Placement',
        '- Place `source_grounded_vs_summary_only_ablation.png` on the right half of the slide.',
        '',
        '# Take-Home Line',
        'Source grounding changed LENS from rating summary fluency in isolation to evaluating whether the summary is actually correct for the patient.',
        '',
        '# Speaker Notes',
        '- We used the same 15 summary variants in both experiments and only changed whether the source packet was available.',
        '- In summary-only mode, wrong-patient summaries still looked plausible and often kept high scores.',
        '- In source-grounded mode, the score gap became large and wrong-patient detection reached 100 percent on this pilot benchmark.',
    ]
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    source_grounded = _build_metrics(SOURCE_GROUNDED_DIR)
    summary_only = _build_metrics(SUMMARY_ONLY_DIR)
    _write_comparison_csv(OUTDIR / 'phase2_ablation_comparison.csv', source_grounded, summary_only)
    _make_plot(OUTDIR / 'source_grounded_vs_summary_only_ablation.png', source_grounded, summary_only)
    _write_slide_markdown(OUTDIR / 'phase2_ablation_result_slide.md', source_grounded, summary_only)


if __name__ == '__main__':
    main()
