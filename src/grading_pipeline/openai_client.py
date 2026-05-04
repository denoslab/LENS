"""Minimal HTTP client for the OpenAI Responses API.

Uses only stdlib (``urllib``) — no external dependencies. Handles:
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
import socket
from pathlib import Path
import urllib.error
import urllib.request
from typing import Any, Dict


DEFAULT_REQUEST_TIMEOUT_SECONDS = 60.0
MAX_ERROR_PREVIEW_CHARS = 280
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOTENV_PATH = PROJECT_ROOT / ".env"


class OpenAIClientError(RuntimeError):
    """Raised for any OpenAI API communication or response-parsing failure."""

    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable



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
    """Parse a ``.env`` file into a dict.

    Handles comments, ``export`` prefixes, quoted values, and inline comments.
    Returns an empty dict if the file is missing.
    """
    try:
        raw = Path(path).read_text(encoding="utf-8")
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
        if key:
            result[key] = value
    return result


def _candidate_dotenv_paths() -> list[Path]:
    candidates = [Path.cwd() / ".env", DOTENV_PATH]
    deduped: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        deduped.append(candidate)
    return deduped


def _resolve_api_key() -> str | None:
    """Resolve the OpenAI API key.

    Priority order:
    1. ``OPENAI_API_KEY`` from the process environment
    2. ``.env`` in the current working directory
    3. repo-root ``.env`` when running from a checkout
    """
    env_key = os.getenv("OPENAI_API_KEY")
    if env_key:
        return env_key

    for dotenv_path in _candidate_dotenv_paths():
        dotenv = _read_dotenv(dotenv_path)
        key = dotenv.get("OPENAI_API_KEY")
        if key:
            os.environ["OPENAI_API_KEY"] = key
            return key
    return None


def _resolve_request_timeout() -> float:
    raw = os.getenv("LENS_OPENAI_TIMEOUT_SECONDS") or os.getenv("OPENAI_TIMEOUT_SECONDS")
    if raw is None:
        return DEFAULT_REQUEST_TIMEOUT_SECONDS
    try:
        timeout = float(raw)
    except ValueError as exc:
        raise OpenAIClientError(
            f"Invalid timeout value in environment: {raw!r}."
        ) from exc
    if timeout <= 0:
        raise OpenAIClientError("OpenAI request timeout must be > 0 seconds.")
    return timeout


def _request_headers(api_key: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def _preview_text(text: str, *, max_chars: int = MAX_ERROR_PREVIEW_CHARS) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= max_chars:
        return f"{cleaned} (chars={len(text)})"
    return f"{cleaned[:max_chars]}... (chars={len(text)})"


def create_response(
    *,
    model: str,
    instructions: str,
    input_text: str,
    json_schema: Dict[str, Any],
    temperature: float = 0.2,
) -> Dict[str, Any]:
    """Send a request to the OpenAI Responses API and return the raw JSON response."""
    api_key = _resolve_api_key()
    if not api_key:
        raise OpenAIClientError("OPENAI_API_KEY is not set.")

    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1/responses")
    timeout_seconds = _resolve_request_timeout()
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
        with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        err_body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        raise OpenAIClientError(
            f"OpenAI API error {exc.code}: {_preview_text(err_body)}",
            retryable=exc.code == 429 or 500 <= exc.code < 600,
        ) from exc
    except (TimeoutError, socket.timeout) as exc:
        raise OpenAIClientError(
            f"OpenAI API request timed out after {timeout_seconds:.1f}s.",
            retryable=True,
        ) from exc
    except urllib.error.URLError as exc:
        reason = getattr(exc, "reason", exc)
        if isinstance(reason, socket.timeout):
            raise OpenAIClientError(
                f"OpenAI API request timed out after {timeout_seconds:.1f}s.",
                retryable=True,
            ) from exc
        retryable = isinstance(reason, OSError)
        raise OpenAIClientError(
            f"OpenAI API request failed: {reason}",
            retryable=retryable,
        ) from exc

    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise OpenAIClientError(
            f"OpenAI API returned invalid JSON: {_preview_text(raw)}",
            retryable=True,
        ) from exc


def extract_json_output(response: Dict[str, Any]) -> Dict[str, Any]:
    """Extract and parse JSON from an OpenAI Responses API response."""
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
        raise OpenAIClientError(
            "No text output found in OpenAI response.",
            retryable=True,
        )

    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise OpenAIClientError(
            f"Failed to parse JSON output: {_preview_text(text)}",
            retryable=True,
        ) from exc
