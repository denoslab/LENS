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
    assert "Disagreement:" in result.stdout


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
