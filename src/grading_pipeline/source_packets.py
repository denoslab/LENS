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
            cleaned = str(item).strip()
            if cleaned:
                items.append(cleaned)
        return items
    cleaned = str(value).strip()
    return [cleaned] if cleaned else []


def looks_like_source_packet(data: Any) -> bool:
    return isinstance(data, dict) and (
        "source_packet_version" in data
        or "source_id" in data
        or "patient_label" in data
        or "encounter_context" in data
    )


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
        items = _normalize_items(packet.get(key))
        if not items:
            continue
        body = "\n".join(f"- {item}" for item in items)
        sections.append(f"{title}:\n{body}")

    return "\n\n".join(sections).strip()


def load_source_file(path: str | Path) -> LoadedSource:
    """Load a source file, auto-rendering source-packet JSON when detected."""
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
