import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.run_source_grounded_benchmark import (
    BenchmarkStats,
    _build_cli_command,
    _summarize_case,
    _write_report,
    load_manifest,
)


def test_load_manifest_resolves_case_files() -> None:
    manifest_path = PROJECT_ROOT / "data/phase2/benchmarks/source_grounded_demo/manifest.json"
    cases = load_manifest(manifest_path)

    assert len(cases) >= 5
    for case in cases:
        assert case.source_file.exists(), f"missing source for {case.case_id}"
        for variant in case.variants:
            assert variant.summary_file.exists(), (
                f"missing summary for {case.case_id}/{variant.variant_id}"
            )


def test_build_cli_command_supports_context_and_temperature() -> None:
    source_file = PROJECT_ROOT / "data/phase2/benchmarks/source_grounded_demo/cases/case_001/source_packet.json"
    summary_file = PROJECT_ROOT / "data/phase2/benchmarks/source_grounded_demo/cases/case_001/reference_summary.txt"

    source_grounded_cmd = _build_cli_command(
        summary_file,
        source_file,
        model="gpt-4o-mini",
        python_bin=sys.executable,
        rubric=PROJECT_ROOT / "config/lens_rubric.json",
        roles=PROJECT_ROOT / "config/roles.json",
        evaluation_context="source_grounded",
        temperature=0.0,
    )
    summary_only_cmd = _build_cli_command(
        summary_file,
        source_file,
        model="gpt-4o-mini",
        python_bin=sys.executable,
        rubric=PROJECT_ROOT / "config/lens_rubric.json",
        roles=PROJECT_ROOT / "config/roles.json",
        evaluation_context="summary_only",
        temperature=0.0,
    )

    assert "--temperature" in source_grounded_cmd
    assert "0.0" in source_grounded_cmd
    assert "--source-file" in source_grounded_cmd
    assert "--source-file" not in summary_only_cmd


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
            "source_grounded_summary": {
                "wrong_patient_suspected": False,
                "unsupported_claims": [],
                "contradicted_claims": [],
                "omitted_safety_facts": [],
            },
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
            "source_grounded_summary": {
                "wrong_patient_suspected": True,
                "unsupported_claims": [{"text": "unsupported", "reporting_roles": ["physician"]}],
                "contradicted_claims": [{"text": "contradicted", "reporting_roles": ["triage_nurse"]}],
                "omitted_safety_facts": [],
            },
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
            "source_grounded_summary": {
                "wrong_patient_suspected": False,
                "unsupported_claims": [],
                "contradicted_claims": [],
                "omitted_safety_facts": [{"text": "missed insulin", "reporting_roles": ["bedside_nurse"]}],
            },
        },
    }

    rows = _summarize_case(case, outputs)

    mismatch_row = next(row for row in rows if row["variant_type"] == "wrong_patient_mismatch")
    omission_row = next(row for row in rows if row["variant_type"] == "safety_critical_omission")
    assert mismatch_row["hit_rate"] == 1.0
    assert mismatch_row["contradicted_claim_count"] == 1
    assert omission_row["hit_rate"] == 1.0
    assert omission_row["omitted_safety_fact_count"] == 1


def test_write_report_records_metadata_and_failures(tmp_path: Path) -> None:
    report_path = tmp_path / "report.md"
    rows = [
        {
            "case_id": "case_001",
            "variant_id": "reference",
            "variant_type": "reference",
            "overall": 4.0,
            "overall_delta_vs_reference": 0.0,
            "expected_dims_count": 0,
            "hit_count": 0,
            "hit_rate": 1.0,
            "flagged_dimensions": "",
            "wrong_patient_suspected": False,
            "unsupported_claim_count": 0,
            "contradicted_claim_count": 0,
            "omitted_safety_fact_count": 0,
        },
        {
            "case_id": "case_001",
            "variant_id": "wrong_patient_case_002",
            "variant_type": "wrong_patient_mismatch",
            "overall": 2.0,
            "overall_delta_vs_reference": 2.0,
            "expected_dims_count": 4,
            "hit_count": 4,
            "hit_rate": 1.0,
            "flagged_dimensions": "factual_accuracy",
            "wrong_patient_suspected": True,
            "unsupported_claim_count": 2,
            "contradicted_claim_count": 1,
            "omitted_safety_fact_count": 0,
        },
        {
            "case_id": "case_001",
            "variant_id": "safety_omission",
            "variant_type": "safety_critical_omission",
            "overall": 3.0,
            "overall_delta_vs_reference": 1.0,
            "expected_dims_count": 3,
            "hit_count": 2,
            "hit_rate": 0.6667,
            "flagged_dimensions": "usefulness_for_decision_making",
            "wrong_patient_suspected": False,
            "unsupported_claim_count": 0,
            "contradicted_claim_count": 0,
            "omitted_safety_fact_count": 2,
        },
    ]
    run_meta = {
        "timestamp_utc": "2026-04-27T00:00:00+00:00",
        "git_sha": "abc123",
        "model": "gpt-4o-mini",
        "temperature": 0.0,
        "evaluation_context": "source_grounded",
        "manifest_path": "/tmp/manifest.json",
        "manifest_sha256": "mhash",
        "rubric_path": "/tmp/rubric.json",
        "rubric_sha256": "rhash",
        "roles_path": "/tmp/roles.json",
        "roles_sha256": "rohash",
        "resume_enabled": False,
    }
    stats = BenchmarkStats(
        attempted_cases=2,
        attempted_variants=6,
        completed_cases=1,
        completed_variants=3,
        resumed_variants=0,
        skipped_cases=["case_002"],
        failed_variants=["case_002/wrong_patient_case_003"],
    )

    _write_report(report_path, "demo_manifest", rows, run_meta=run_meta, stats=stats)
    report = report_path.read_text(encoding="utf-8")

    assert "Timestamp (UTC): `2026-04-27T00:00:00+00:00`" in report
    assert "Evaluation context: `source_grounded`" in report
    assert "Temperature: `0.0`" in report
    assert "Completed reference variants: `1`" in report
    assert "Completed degraded test variants: `2`" in report
    assert "Mean overall delta vs reference (degraded variants only): `1.5`" in report
    assert "Skipped cases: `1`" in report
    assert "Failed variants: `1`" in report
    assert "contradicted_claims: `1`" in report
