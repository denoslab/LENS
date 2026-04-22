import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import pytest

from grading_pipeline.source_packets import (
    SourcePacketValidationError,
    load_source_file,
    render_source_packet,
    validate_source_packet,
)


def _valid_packet(**overrides: object) -> dict:
    """Return a schema-compliant packet dict; overrides replace top-level keys."""
    base = {
        "source_packet_version": "v1",
        "source_id": "case_valid",
        "patient_label": "Patient Test",
        "encounter_context": {
            "setting": "Emergency Department",
            "encounter_reason": "Test encounter",
            "time_window": "last 24 hours",
        },
        "active_problems": ["Problem A"],
        "chronic_conditions": ["Chronic A"],
        "recent_changes": ["Required 4 L oxygen in ED."],
        "medications": [
            {
                "name": "Insulin",
                "status": "active",
                "timing_or_schedule": "q8h",
                "why_important": "glucose control",
            }
        ],
        "procedures_and_devices": ["Pulse oximetry"],
        "safety_critical_facts": ["Insulin q8h must continue."],
        "disposition_and_follow_up": ["Admit"],
        "supporting_source_excerpts": [
            {"label": "Nursing note", "text": "Missed insulin dose before arrival."}
        ],
    }
    base.update(overrides)
    return base


def test_render_source_packet_includes_key_sections() -> None:
    packet = {
        "source_packet_version": "v1",
        "source_id": "case_123",
        "patient_label": "Patient Z",
        "active_problems": ["Acute hypoxia"],
        "safety_critical_facts": ["Insulin q8h must continue."],
    }

    rendered = render_source_packet(packet)

    assert "SOURCE PACKET" in rendered
    assert "Source ID: case_123" in rendered
    assert "Patient Label: Patient Z" in rendered
    assert "Active Problems:" in rendered
    assert "Safety-Critical Facts:" in rendered
    assert "Insulin q8h must continue." in rendered


def test_load_source_file_auto_renders_source_packet_json(tmp_path: Path) -> None:
    source_path = tmp_path / "packet.json"
    source_path.write_text(
        json.dumps(_valid_packet(source_id="case_001", patient_label="Patient A")),
        encoding="utf-8",
    )

    loaded = load_source_file(source_path)

    assert loaded.metadata["file_format"] == "source_packet"
    assert loaded.metadata["source_id"] == "case_001"
    assert "Required 4 L oxygen" in loaded.text


def test_validate_source_packet_accepts_valid_packet() -> None:
    assert validate_source_packet(_valid_packet()) == []


def test_validate_source_packet_reports_missing_required_fields() -> None:
    packet = _valid_packet()
    del packet["source_id"]
    del packet["medications"]

    errors = validate_source_packet(packet)

    assert any("source_id" in msg for msg in errors)
    assert any("medications" in msg for msg in errors)


def test_validate_source_packet_reports_wrong_shape_for_medications() -> None:
    packet = _valid_packet()
    packet["medications"] = ["Insulin q8h at home"]

    errors = validate_source_packet(packet)

    assert any("medications[0]" in msg and "object" in msg for msg in errors)


def test_validate_source_packet_reports_missing_medication_fields() -> None:
    packet = _valid_packet()
    packet["medications"] = [{"name": "Insulin"}]

    errors = validate_source_packet(packet)

    assert any("medications[0]" in msg and "status" in msg for msg in errors)


def test_validate_source_packet_reports_wrong_encounter_context_shape() -> None:
    packet = _valid_packet()
    packet["encounter_context"] = ["free-text line"]

    errors = validate_source_packet(packet)

    assert any("encounter_context" in msg and "object" in msg for msg in errors)


def test_load_source_file_raises_on_invalid_packet(tmp_path: Path) -> None:
    packet = _valid_packet()
    del packet["safety_critical_facts"]
    source_path = tmp_path / "bad.json"
    source_path.write_text(json.dumps(packet), encoding="utf-8")

    with pytest.raises(SourcePacketValidationError) as exc_info:
        load_source_file(source_path)

    assert any("safety_critical_facts" in msg for msg in exc_info.value.errors)


def test_load_source_file_allows_skipping_validation(tmp_path: Path) -> None:
    packet = _valid_packet()
    del packet["safety_critical_facts"]
    source_path = tmp_path / "bad.json"
    source_path.write_text(json.dumps(packet), encoding="utf-8")

    loaded = load_source_file(source_path, validate=False)

    assert loaded.metadata["file_format"] == "source_packet"


def test_bundled_demo_cases_are_schema_compliant() -> None:
    """The shipped Phase 2 demo cases must validate against their own schema."""
    demo_root = PROJECT_ROOT / "data/phase2/benchmarks/source_grounded_demo/cases"
    for packet_path in sorted(demo_root.glob("case_*/source_packet.json")):
        with packet_path.open(encoding="utf-8") as handle:
            data = json.load(handle)
        errors = validate_source_packet(data)
        assert errors == [], f"{packet_path.name} validation errors: {errors}"


def test_render_source_packet_formats_structured_medications() -> None:
    """Schema-compliant medications (list of dicts) must render as readable text,
    not Python dict repr like ``{'name': 'Insulin', ...}``."""
    packet = {
        "source_id": "case_med",
        "medications": [
            {
                "name": "Insulin",
                "status": "active",
                "timing_or_schedule": "q8h",
                "why_important": "omission causes hyperglycemia",
            },
            {"name": "Aspirin", "status": "continued"},
            "Free-text legacy medication entry",
        ],
    }

    rendered = render_source_packet(packet)

    assert "{'name'" not in rendered
    assert "Insulin (active, q8h) — omission causes hyperglycemia" in rendered
    assert "Aspirin (continued)" in rendered
    assert "Free-text legacy medication entry" in rendered


def test_render_source_packet_formats_structured_excerpts() -> None:
    """Schema-compliant excerpts (list of dicts with label/text) must render as
    ``label: text`` lines, not Python dict repr."""
    packet = {
        "source_id": "case_excerpt",
        "supporting_source_excerpts": [
            {"label": "Nursing note", "text": "Missed q8h insulin before arrival."},
            "Plain-text excerpt without label",
        ],
    }

    rendered = render_source_packet(packet)

    assert "{'label'" not in rendered
    assert "Nursing note: Missed q8h insulin before arrival." in rendered
    assert "Plain-text excerpt without label" in rendered


def test_render_source_packet_renders_nested_list_of_dicts_as_inline() -> None:
    """Any unrecognized list-of-dict section must still produce readable output
    rather than Python dict repr. Guards against regressions in other sections."""
    packet = {
        "source_id": "case_generic",
        "active_problems": [
            {"problem": "Hypoxia", "severity": "acute"},
        ],
    }

    rendered = render_source_packet(packet)

    assert "{'problem'" not in rendered
    assert "problem: Hypoxia" in rendered
    assert "severity: acute" in rendered
