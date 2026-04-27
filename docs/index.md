# LENS: Role-Aware Clinical Summary Grading

LENS is a role-aware multi-agent grading pipeline for AI-generated clinical summaries. Three Emergency Department roles — Physician, Triage Nurse, and Bedside Nurse — score the same summary across eight rubric dimensions. An orchestrator validates outputs, measures disagreement, optionally adjudicates disputed dimensions, and aggregates final scores.

## Installation

### Installed package

```bash
pip install edlens
```

This uses the bundled default rubric, roles, and role profiles.

### Editable development install

```bash
pip install -e ".[dev,docs]"
```

Use this mode if you want to modify configs, prompts, or experiment scripts.

## Quick Start

Heuristic baseline:

```bash
lens --summary "Your clinical summary here" --engine heuristic
```

LLM scoring:

```bash
lens --summary "Your clinical summary here" --engine llm --model gpt-4o-mini
```

Source-grounded scoring:

```bash
lens --summary-file path/to/summary.txt --source-file path/to/source_packet.json --engine llm
```

## Configuration

By default, LENS loads bundled package resources for:

- the rubric
- the role definitions
- the role-specific prompt profiles

You can override them with `--rubric` and `--roles`.

## Source-Grounded Phase 2

See [Source-Grounded Phase 2](source_grounded_phase2.md) for the current source-grounded design, source-packet strategy, and benchmark scaffold.

## API Reference

See the [API Reference](api/cli.md) for module-level documentation.
