import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from grading_pipeline.source_packets import load_source_file, render_source_packet


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
        json.dumps(
            {
                "source_packet_version": "v1",
                "source_id": "case_001",
                "patient_label": "Patient A",
                "recent_changes": ["Required 4 L oxygen in ED."],
            }
        ),
        encoding="utf-8",
    )

    loaded = load_source_file(source_path)

    assert loaded.metadata["file_format"] == "source_packet"
    assert loaded.metadata["source_id"] == "case_001"
    assert "Required 4 L oxygen" in loaded.text
