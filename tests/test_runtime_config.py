from __future__ import annotations

import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from grading_pipeline import openai_client
from grading_pipeline.scoring import _score_decision_usefulness, _score_timeline


def test_openai_client_reads_project_root_dotenv(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Path] = {}

    def fake_read_dotenv(path: str | Path) -> dict[str, str]:
        captured["path"] = Path(path)
        return {"OPENAI_API_KEY": "test-key"}

    monkeypatch.setattr(openai_client, "_read_dotenv", fake_read_dotenv)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    key = openai_client._resolve_api_key()

    assert key == "test-key"
    assert captured["path"] == openai_client.DOTENV_PATH


def test_decision_usefulness_ignores_substring_false_positive() -> None:
    score, _, hits = _score_decision_usefulness("Action plan reviewed during clinic follow-up.")

    assert hits == []
    assert score == 1


def test_timeline_ignores_common_preposition_false_positive() -> None:
    score, _, hits = _score_timeline("Patient presents for asthma follow-up and medication refill.")

    assert hits == []
    assert score == 1
