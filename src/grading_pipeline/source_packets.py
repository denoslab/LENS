"""Utilities for rendering structured source packets into LLM-friendly text."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping


@dataclass(frozen=True)
class LoadedSource:
    """Resolved source input plus lightweight metadata."""

    text: str
    metadata: Dict[str, Any]


def _format_mapping_inline(mapping: Mapping[str, Any]) -> str:
    """Format a nested dict as ``key: value`` pairs joined by ``; ``.

    Fallback for generic list-of-dicts input where no section-specific
    formatter applies. Keeps the text readable for the LLM instead of
    falling through to ``str(dict)`` which emits Python repr (``{'k': 'v'}``).
    """
    parts: list[str] = []
    for key, value in mapping.items():
        if value is None:
            continue
        cleaned = str(value).strip()
        if cleaned:
            parts.append(f"{key}: {cleaned}")
    return "; ".join(parts)


def _normalize_items(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        cleaned = value.strip()
        return [cleaned] if cleaned else []
    if isinstance(value, Mapping):
        items: list[str] = []
        for key, item in value.items():
            if isinstance(item, list):
                joined = ", ".join(str(part).strip() for part in item if str(part).strip())
                if joined:
                    items.append(f"{key}: {joined}")
            else:
                cleaned = str(item).strip()
                if cleaned:
                    items.append(f"{key}: {cleaned}")
        return items
    if isinstance(value, Iterable):
        items = []
        for item in value:
            if isinstance(item, Mapping):
                formatted = _format_mapping_inline(item)
                if formatted:
                    items.append(formatted)
                continue
            cleaned = str(item).strip()
            if cleaned:
                items.append(cleaned)
        return items
    cleaned = str(value).strip()
    return [cleaned] if cleaned else []


def _format_medication(item: Any) -> str:
    """Render a medication entry.

    Supports two shapes:
      * plain string (legacy demo data)
      * schema-compliant object with ``name`` / ``status`` /
        ``timing_or_schedule`` / ``why_important``
    """
    if not isinstance(item, Mapping):
        return str(item).strip()

    name = str(item.get("name", "")).strip()
    if not name:
        return _format_mapping_inline(item)

    status = str(item.get("status", "")).strip()
    timing = str(item.get("timing_or_schedule", "")).strip()
    why = str(item.get("why_important", "")).strip()

    qualifiers = [part for part in (status, timing) if part]
    line = f"{name} ({', '.join(qualifiers)})" if qualifiers else name
    if why:
        line = f"{line} — {why}"
    return line


def _format_excerpt(item: Any) -> str:
    """Render a supporting-source excerpt as ``Label: text`` (or fallbacks)."""
    if not isinstance(item, Mapping):
        return str(item).strip()

    label = str(item.get("label", "")).strip()
    text = str(item.get("text", "")).strip()
    if label and text:
        return f"{label}: {text}"
    return text or label or _format_mapping_inline(item)


_SECTION_FORMATTERS = {
    "medications": _format_medication,
    "supporting_source_excerpts": _format_excerpt,
}


def _render_items(key: str, value: Any) -> list[str]:
    """Turn a packet section's raw value into a list of display strings."""
    formatter = _SECTION_FORMATTERS.get(key)
    if formatter is not None and isinstance(value, list):
        rendered = [formatter(item) for item in value]
        return [line for line in (part.strip() for part in rendered) if line]
    return _normalize_items(value)


def looks_like_source_packet(data: Any) -> bool:
    return isinstance(data, dict) and (
        "source_packet_version" in data
        or "source_id" in data
        or "patient_label" in data
        or "encounter_context" in data
    )


class SourcePacketValidationError(ValueError):
    """Raised when a source packet does not conform to the expected schema."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = list(errors)
        header = "Source packet failed validation:"
        body = "\n".join(f"- {msg}" for msg in self.errors)
        super().__init__(f"{header}\n{body}")


_REQUIRED_TOP_LEVEL = [
    "source_packet_version",
    "source_id",
    "encounter_context",
    "active_problems",
    "chronic_conditions",
    "recent_changes",
    "medications",
    "procedures_and_devices",
    "safety_critical_facts",
    "disposition_and_follow_up",
    "supporting_source_excerpts",
]

_STRING_ARRAY_FIELDS = [
    "active_problems",
    "chronic_conditions",
    "recent_changes",
    "procedures_and_devices",
    "safety_critical_facts",
    "disposition_and_follow_up",
    "notes",
]

_ENCOUNTER_REQUIRED = ["setting", "encounter_reason"]
_MEDICATION_REQUIRED = ["name", "status"]
_EXCERPT_REQUIRED = ["label", "text"]


def _check_string(value: Any, path: str, errors: list[str]) -> None:
    if not isinstance(value, str):
        errors.append(f"{path} must be a string, got {type(value).__name__}")


def _check_string_array(value: Any, path: str, errors: list[str]) -> None:
    if not isinstance(value, list):
        errors.append(f"{path} must be an array, got {type(value).__name__}")
        return
    for idx, item in enumerate(value):
        if not isinstance(item, str):
            errors.append(
                f"{path}[{idx}] must be a string, got {type(item).__name__}"
            )


def _check_object_array(
    value: Any,
    path: str,
    required_fields: list[str],
    errors: list[str],
) -> None:
    if not isinstance(value, list):
        errors.append(f"{path} must be an array, got {type(value).__name__}")
        return
    for idx, item in enumerate(value):
        item_path = f"{path}[{idx}]"
        if not isinstance(item, dict):
            errors.append(
                f"{item_path} must be an object, got {type(item).__name__}"
            )
            continue
        for field in required_fields:
            if field not in item:
                errors.append(f"{item_path} missing required field '{field}'")
            elif not isinstance(item[field], str):
                errors.append(
                    f"{item_path}.{field} must be a string, got "
                    f"{type(item[field]).__name__}"
                )


def validate_source_packet(data: Any) -> list[str]:
    """Validate a source-packet object against the documented schema.

    Returns a list of error strings; empty list means the packet is valid.
    This is a minimal stdlib check — it does not implement full JSON Schema,
    only the required fields and types the pipeline relies on.
    """
    errors: list[str] = []

    if not isinstance(data, dict):
        return [f"Source packet must be an object, got {type(data).__name__}"]

    for field in _REQUIRED_TOP_LEVEL:
        if field not in data:
            errors.append(f"Missing required field '{field}'")

    if "source_packet_version" in data:
        _check_string(data["source_packet_version"], "source_packet_version", errors)
    if "source_id" in data:
        _check_string(data["source_id"], "source_id", errors)
    if "patient_label" in data:
        _check_string(data["patient_label"], "patient_label", errors)

    if "encounter_context" in data:
        ctx = data["encounter_context"]
        if not isinstance(ctx, dict):
            errors.append(
                f"encounter_context must be an object, got {type(ctx).__name__}"
            )
        else:
            for field in _ENCOUNTER_REQUIRED:
                if field not in ctx:
                    errors.append(
                        f"encounter_context missing required field '{field}'"
                    )
                elif not isinstance(ctx[field], str):
                    errors.append(
                        f"encounter_context.{field} must be a string, got "
                        f"{type(ctx[field]).__name__}"
                    )
            if "time_window" in ctx and not isinstance(ctx["time_window"], str):
                errors.append(
                    f"encounter_context.time_window must be a string, got "
                    f"{type(ctx['time_window']).__name__}"
                )

    for field in _STRING_ARRAY_FIELDS:
        if field in data:
            _check_string_array(data[field], field, errors)

    if "medications" in data:
        _check_object_array(
            data["medications"], "medications", _MEDICATION_REQUIRED, errors
        )
    if "supporting_source_excerpts" in data:
        _check_object_array(
            data["supporting_source_excerpts"],
            "supporting_source_excerpts",
            _EXCERPT_REQUIRED,
            errors,
        )

    return errors


def render_source_packet(packet: Mapping[str, Any]) -> str:
    """Render a structured source packet into a compact narrative text block."""
    sections: list[str] = []

    header_lines = ["SOURCE PACKET"]
    if packet.get("source_id"):
        header_lines.append(f"Source ID: {packet['source_id']}")
    if packet.get("patient_label"):
        header_lines.append(f"Patient Label: {packet['patient_label']}")
    if packet.get("source_packet_version"):
        header_lines.append(f"Packet Version: {packet['source_packet_version']}")
    sections.append("\n".join(header_lines))

    section_map = [
        ("Encounter Context", "encounter_context"),
        ("Active Problems", "active_problems"),
        ("Chronic Conditions", "chronic_conditions"),
        ("Recent Changes", "recent_changes"),
        ("Medications", "medications"),
        ("Procedures and Devices", "procedures_and_devices"),
        ("Safety-Critical Facts", "safety_critical_facts"),
        ("Disposition and Follow-Up", "disposition_and_follow_up"),
        ("Supporting Source Excerpts", "supporting_source_excerpts"),
        ("Notes", "notes"),
    ]

    for title, key in section_map:
        items = _render_items(key, packet.get(key))
        if not items:
            continue
        body = "\n".join(f"- {item}" for item in items)
        sections.append(f"{title}:\n{body}")

    return "\n\n".join(sections).strip()


def load_source_file(path: str | Path, *, validate: bool = True) -> LoadedSource:
    """Load a source file, auto-rendering source-packet JSON when detected.

    Args:
        path: Path to the source file.
        validate: When True (default), JSON that looks like a source packet is
            validated against the documented schema. Invalid packets raise
            ``SourcePacketValidationError``. Set to False to skip validation
            for exploratory/legacy data.
    """
    source_path = Path(path)
    raw = source_path.read_text(encoding="utf-8")
    metadata: Dict[str, Any] = {
        "path": str(source_path),
        "file_name": source_path.name,
    }

    if source_path.suffix.lower() == ".json":
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            metadata["file_format"] = "json_text"
            return LoadedSource(text=raw, metadata=metadata)

        if looks_like_source_packet(data):
            if validate:
                errors = validate_source_packet(data)
                if errors:
                    raise SourcePacketValidationError(errors)
            metadata.update(
                {
                    "file_format": "source_packet",
                    "source_id": data.get("source_id"),
                    "source_packet_version": data.get("source_packet_version"),
                }
            )
            return LoadedSource(text=render_source_packet(data), metadata=metadata)

        metadata["file_format"] = "json_text"
        return LoadedSource(text=raw, metadata=metadata)

    metadata["file_format"] = "text"
    return LoadedSource(text=raw, metadata=metadata)
