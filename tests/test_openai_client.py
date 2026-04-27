from __future__ import annotations

import socket
import sys
from pathlib import Path
from urllib.error import URLError

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from grading_pipeline.openai_client import OpenAIClientError, extract_json_output, create_response


class _FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return b'{"output": []}'


def test_extract_json_output_redacts_long_invalid_text() -> None:
    response = {"output_text": "x" * 600}
    with pytest.raises(OpenAIClientError) as exc:
        extract_json_output(response)
    message = str(exc.value)
    assert "Failed to parse JSON output:" in message
    assert "chars=600" in message
    assert len(message) < 450


def test_create_response_wraps_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *args, **kwargs: (_ for _ in ()).throw(URLError(socket.timeout("timed out"))),
    )

    with pytest.raises(OpenAIClientError, match="timed out"):
        create_response(
            model="test-model",
            instructions="return json",
            input_text="hello",
            json_schema={"type": "object", "properties": {}},
        )
