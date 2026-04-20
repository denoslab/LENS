from __future__ import annotations

import argparse
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEMPLATE = REPO_ROOT / "data" / "phase2" / "templates" / "source_packet_template.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create a new source-packet template JSON file for Phase 2 experiments.")
    parser.add_argument("--source-id", required=True, help="Source packet identifier (for example case_001).")
    parser.add_argument("--patient-label", default="Patient A", help="Human-readable patient label for the template.")
    parser.add_argument("--output", required=True, help="Output JSON path.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    payload = json.loads(DEFAULT_TEMPLATE.read_text(encoding="utf-8"))
    payload["source_id"] = args.source_id
    payload["patient_label"] = args.patient_label

    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = REPO_ROOT / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote source packet template to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
