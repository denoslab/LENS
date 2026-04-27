from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from grading_pipeline import openai_client
from grading_pipeline.config import (
    load_default_roles,
    load_default_rubric,
    load_roles,
    load_rubric,
)
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
    assert captured["path"] in {Path.cwd() / ".env", openai_client.DOTENV_PATH}


def test_load_default_rubric_and_roles() -> None:
    rubric = load_default_rubric()
    roles = load_default_roles(rubric.dimension_ids)

    assert rubric.rubric_id == "lens_v1"
    assert len(rubric.dimensions) == 8
    assert {role.id for role in roles} == {"physician", "triage_nurse", "bedside_nurse"}


def test_load_rubric_rejects_duplicate_dimension_ids(tmp_path: Path) -> None:
    rubric_path = tmp_path / "rubric.json"
    rubric_path.write_text(
        json.dumps(
            {
                "rubric_id": "dup",
                "dimensions": [
                    {
                        "id": "factual_accuracy",
                        "name": "Factual Accuracy",
                        "definition": "A",
                        "evaluation_focus": "B",
                    },
                    {
                        "id": "factual_accuracy",
                        "name": "Duplicate",
                        "definition": "C",
                        "evaluation_focus": "D",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicate dimension id"):
        load_rubric(rubric_path)


def test_load_roles_rejects_duplicate_role_ids(tmp_path: Path) -> None:
    roles_path = tmp_path / "roles.json"
    roles_path.write_text(
        json.dumps(
            {
                "roles": [
                    {
                        "id": "physician",
                        "name": "Physician Agent",
                        "persona": "p1",
                        "w_prior": {dim: 1.0 for dim in load_default_rubric().dimension_ids},
                    },
                    {
                        "id": "physician",
                        "name": "Physician Agent 2",
                        "persona": "p2",
                        "w_prior": {dim: 1.0 for dim in load_default_rubric().dimension_ids},
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicate role id"):
        load_roles(roles_path, load_default_rubric().dimension_ids)


def test_decision_usefulness_ignores_substring_false_positive() -> None:
    score, _, hits = _score_decision_usefulness("Action plan reviewed during clinic follow-up.")

    assert hits == []
    assert score == 1



def test_timeline_ignores_common_preposition_false_positive() -> None:
    score, _, hits = _score_timeline("Patient presents for asthma follow-up and medication refill.")

    assert hits == []
    assert score == 1
