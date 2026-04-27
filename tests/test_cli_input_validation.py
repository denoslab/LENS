import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from grading_pipeline import cli


EMPTY_ERROR = "Error: summary is required and cannot be empty."
SHORT_ERROR = (
    f"Error: summary must be at least {cli.MIN_SUMMARY_CHARS} characters after trimming whitespace."
)
SOURCE_SHORT_ERROR = (
    f"Error: source text must be at least {cli.MIN_SOURCE_CHARS} characters after trimming whitespace if provided."
)
SOURCE_REQUIRES_LLM_ERROR = cli.SOURCE_GROUNDED_REQUIRES_LLM_ERROR


def _run_cli(args: list[str]) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "PYTHONPATH": str(PROJECT_ROOT / "src")}
    return subprocess.run(
        [sys.executable, "-m", "grading_pipeline", *args],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        env=env,
    )


def test_cli_rejects_empty_summary_string() -> None:
    result = _run_cli(["--summary", ""])

    assert result.returncode == 2
    assert EMPTY_ERROR in result.stderr
    assert "Physician:" not in result.stdout


def test_cli_rejects_whitespace_summary_string() -> None:
    result = _run_cli(["--summary", "   "])

    assert result.returncode == 2
    assert EMPTY_ERROR in result.stderr
    assert "Physician:" not in result.stdout


def test_cli_rejects_too_short_summary() -> None:
    result = _run_cli(["--summary", "too short"])

    assert result.returncode == 2
    assert SHORT_ERROR in result.stderr
    assert "Physician:" not in result.stdout


def test_cli_accepts_valid_summary_in_heuristic_mode() -> None:
    valid_summary = (
        "Patient has diabetes and CKD, with worsening shortness of breath over two days, "
        "recent admission and medication changes relevant to ED decision-making."
    )
    result = _run_cli(["--engine", "heuristic", "--summary", valid_summary])

    assert result.returncode == 0
    assert "Physician:" in result.stdout
    assert "Triage Nurse:" in result.stdout
    assert "Bedside Nurse:" in result.stdout
    assert "Orchestrator Disagreement:" in result.stdout
    assert "Evaluation Context:" in result.stdout


def test_invalid_summary_does_not_call_llm(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    calls = {"count": 0}

    def _spy(*args, **kwargs):
        calls["count"] += 1
        raise AssertionError("LLM client must not be called for invalid input")

    monkeypatch.setattr("grading_pipeline.openai_client.create_response", _spy)
    monkeypatch.setattr("grading_pipeline.llm_scoring.create_response", _spy)

    with pytest.raises(SystemExit) as exc:
        cli.main(["--summary", ""])

    captured = capsys.readouterr()
    assert exc.value.code == 2
    assert EMPTY_ERROR in captured.err
    assert calls["count"] == 0


def test_cli_rejects_too_short_source_text() -> None:
    valid_summary = (
        "Patient has diabetes and CKD, with worsening shortness of breath over two days, "
        "recent admission and medication changes relevant to ED decision-making."
    )
    result = _run_cli(["--engine", "heuristic", "--summary", valid_summary, "--source-text", "too short"])

    assert result.returncode == 2
    assert SOURCE_SHORT_ERROR in result.stderr


def test_cli_rejects_source_grounded_input_in_heuristic_mode(tmp_path: Path) -> None:
    summary = (
        "Patient has diabetes, oxygen dependence, and recent medication changes with worsening symptoms over two days."
    )
    source_path = tmp_path / "source.txt"
    source_path.write_text(
        "ED source packet: patient has diabetes, home oxygen requirement, insulin schedule, and worsening shortness of breath over two days.",
        encoding="utf-8",
    )

    result = _run_cli(["--engine", "heuristic", "--summary", summary, "--source-file", str(source_path)])

    assert result.returncode == 2
    assert SOURCE_REQUIRES_LLM_ERROR in result.stderr


def test_cli_json_output_hides_raw_summary_and_source_by_default(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    summary = (
        "Patient has diabetes, oxygen dependence, and recent medication changes with worsening symptoms over two days."
    )
    raw_source = "ED source packet: oxygen dependence, insulin timing, anticoagulation, and recent deterioration over two days."
    source_path = tmp_path / "source.txt"
    source_path.write_text(raw_source, encoding="utf-8")

    async def _fake_run_pipeline(*args, **kwargs):
        return {
            "per_role_scorecards": [],
            "disagreement_map": {},
            "adjudication_ran": False,
            "overall_across_roles": 3.0,
            "meta": {"evaluation_context": "source_grounded", "source_text_provided": True},
            "source_grounded_summary": {
                "wrong_patient_suspected": False,
                "unsupported_claims": [],
                "contradicted_claims": [],
                "omitted_safety_facts": [],
                "reporting_roles": [],
            },
        }

    monkeypatch.setattr(cli, "run_pipeline", _fake_run_pipeline)

    exit_code = cli.main([
        "--engine", "llm",
        "--format", "json",
        "--summary", summary,
        "--source-file", str(source_path),
    ])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert raw_source not in captured.out
    assert summary not in captured.out
    assert "summary" not in payload
    assert payload["summary_metadata"]["char_count"] == len(summary)
    assert "text" not in payload["summary_metadata"]
    assert payload["source"]["char_count"] == len(raw_source)
    assert payload["config"]["rubric"]["mode"] in {"bundled_default", "file"}


def test_cli_json_output_can_include_raw_summary_when_requested(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    summary = (
        "Patient has diabetes and chronic kidney disease, with worsening shortness of breath and recent medication changes."
    )

    async def _fake_run_pipeline(*args, **kwargs):
        return {
            "per_role_scorecards": [],
            "disagreement_map": {},
            "adjudication_ran": False,
            "overall_across_roles": 3.0,
            "meta": {"evaluation_context": "summary_only", "source_text_provided": False},
        }

    monkeypatch.setattr(cli, "run_pipeline", _fake_run_pipeline)

    exit_code = cli.main([
        "--engine", "llm",
        "--format", "json",
        "--summary", summary,
        "--include-summary",
    ])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert payload["summary_metadata"]["text"] == summary
