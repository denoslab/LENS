import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.run_source_grounded_benchmark import load_manifest, _summarize_case


def test_load_manifest_resolves_case_files() -> None:
    manifest_path = PROJECT_ROOT / "data/phase2/benchmarks/source_grounded_demo/manifest.json"
    cases = load_manifest(manifest_path)

    assert len(cases) == 2
    assert cases[0].source_file.exists()
    assert cases[0].variants[0].summary_file.exists()


def test_summarize_case_counts_hits_against_reference() -> None:
    manifest_path = PROJECT_ROOT / "data/phase2/benchmarks/source_grounded_demo/manifest.json"
    case = load_manifest(manifest_path)[0]
    outputs = {
        "reference": {
            "overall_across_roles": 4.0,
            "per_role_scorecards": [
                {"scores": {dim: 4 for dim in [
                    "factual_accuracy",
                    "relevant_chronic_problem_coverage",
                    "organized_by_condition",
                    "timeline_evolution",
                    "recent_changes_highlighted",
                    "focused_not_cluttered",
                    "usefulness_for_decision_making",
                    "clarity_readability_formatting",
                ]}}
                for _ in range(3)
            ],
            "disagreement_map": {},
        },
        "wrong_patient_case_002": {
            "overall_across_roles": 2.0,
            "per_role_scorecards": [
                {"scores": {
                    "factual_accuracy": 1,
                    "relevant_chronic_problem_coverage": 1,
                    "organized_by_condition": 4,
                    "timeline_evolution": 2,
                    "recent_changes_highlighted": 3,
                    "focused_not_cluttered": 4,
                    "usefulness_for_decision_making": 1,
                    "clarity_readability_formatting": 4,
                }}
                for _ in range(3)
            ],
            "disagreement_map": {},
        },
        "safety_omission": {
            "overall_across_roles": 3.0,
            "per_role_scorecards": [
                {"scores": {
                    "factual_accuracy": 2,
                    "relevant_chronic_problem_coverage": 4,
                    "organized_by_condition": 4,
                    "timeline_evolution": 4,
                    "recent_changes_highlighted": 2,
                    "focused_not_cluttered": 4,
                    "usefulness_for_decision_making": 2,
                    "clarity_readability_formatting": 4,
                }}
                for _ in range(3)
            ],
            "disagreement_map": {},
        },
    }

    rows = _summarize_case(case, outputs)

    mismatch_row = next(row for row in rows if row["variant_type"] == "wrong_patient_mismatch")
    omission_row = next(row for row in rows if row["variant_type"] == "safety_critical_omission")
    assert mismatch_row["hit_rate"] == 1.0
    assert omission_row["hit_rate"] == 1.0
