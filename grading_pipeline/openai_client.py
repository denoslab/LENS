"""Minimal HTTP client for the OpenAI Responses API.

Uses only stdlib (``urllib``) — no external dependencies.  Handles:
  - ``.env`` file parsing for ``OPENAI_API_KEY``
  - Building and sending JSON requests to the Responses API
  - Extracting structured JSON output from the response

The base URL defaults to ``https://api.openai.com/v1/responses`` but can
be overridden via the ``OPENAI_BASE_URL`` environment variable (useful for
proxies or local testing).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import urllib.error
import urllib.request
from typing import Any, Dict


class OpenAIClientError(RuntimeError):
    """Raised for any OpenAI API communication or response-parsing failure."""
    pass


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOTENV_PATH = PROJECT_ROOT / ".env"


def _strip_inline_comment(value: str) -> str:
    """Remove an inline ``# comment`` from a .env value, respecting quotes."""
    if "#" not in value:
        return value
    in_single = False
    in_double = False
    for idx, ch in enumerate(value):
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "#" and not in_single and not in_double:
            return value[:idx].rstrip()
    return value


def _read_dotenv(path: str | Path) -> dict[str, str]:
    """Parse a ``.env`` file into a dict.  Handles comments, ``export`` prefix,
    quoted values, and inline comments.  Returns empty dict if file is missing.
    """
    try:
        raw = Path(path).read_text()
    except FileNotFoundError:
        return {}

    result: dict[str, str] = {}
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :]
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = _strip_inline_comment(value.strip())
        value = value.strip().strip('"').strip("'")
        if not key:
            continue
        result[key] = value
    return result


def _resolve_api_key() -> str | None:
    """Resolve the OpenAI API key: .env file takes priority, then env var.

    If found in .env, the key is also injected into ``os.environ`` so
    downstream code can access it consistently.
    """
    dotenv = _read_dotenv(DOTENV_PATH)
    key = dotenv.get("OPENAI_API_KEY")
    if key:
        os.environ["OPENAI_API_KEY"] = key
        return key
    return os.getenv("OPENAI_API_KEY")


def _request_headers(api_key: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def create_response(
    *,
    model: str,
    instructions: str,
    input_text: str,
    json_schema: Dict[str, Any],
    temperature: float = 0.2,
) -> Dict[str, Any]:
    """Send a request to the OpenAI Responses API and return the raw JSON response.

    Uses ``json_schema`` for structured output (strict mode), ensuring the
    model returns JSON conforming to the provided schema.

    Raises:
        OpenAIClientError: If the API key is missing, or the request fails
            with an HTTP or network error.
    """
    api_key = _resolve_api_key()
    if not api_key:
        raise OpenAIClientError("OPENAI_API_KEY is not set.")

    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1/responses")

    payload: Dict[str, Any] = {
        "model": model,
        "instructions": instructions,
        "input": input_text,
        "temperature": temperature,
        "text": {
            "format": {
                "type": "json_schema",
                "name": "role_score",
                "strict": True,
                "schema": json_schema,
            }
        },
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(base_url, data=data, headers=_request_headers(api_key))

    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        err_body = exc.read().decode("utf-8") if exc.fp else ""
        raise OpenAIClientError(
            f"OpenAI API error {exc.code}: {err_body}"
        ) from exc
    except urllib.error.URLError as exc:
        raise OpenAIClientError(f"OpenAI API request failed: {exc.reason}") from exc

    return json.loads(raw)


def extract_json_output(response: Dict[str, Any]) -> Dict[str, Any]:
    """Extract and parse JSON from an OpenAI Responses API response.

    Handles two response formats:
      - Shortcut: ``response["output_text"]`` (newer API versions)
      - Nested: ``response["output"][*]["content"][*]["text"]`` (standard format)

    Raises:
        OpenAIClientError: If no text output is found or JSON parsing fails.
    """
    if isinstance(response, dict) and response.get("output_text"):
        text = response["output_text"]
    else:
        text_parts = []
        for item in response.get("output", []) if isinstance(response, dict) else []:
            if not isinstance(item, dict):
                continue
            if "content" in item:
                for content in item.get("content", []):
                    if not isinstance(content, dict):
                        continue
                    if content.get("type") in ("output_text", "text") and content.get("text"):
                        text_parts.append(content["text"])
                    elif content.get("text"):
                        text_parts.append(content["text"])
            elif item.get("type") in ("output_text", "text") and item.get("text"):
                text_parts.append(item["text"])
        text = "".join(text_parts).strip()

    if not text:
        raise OpenAIClientError("No text output found in OpenAI response.")

    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise OpenAIClientError(f"Failed to parse JSON output: {text}") from exc
