# LENS: Role-Aware Clinical Summary Grading

LENS is a role-aware multi-agent grading pipeline for clinical (ED handoff) summaries. Three clinical roles (Physician, Triage Nurse, Bedside Nurse) score summaries in parallel across 8 rubric dimensions, then an orchestrator detects disagreements, optionally adjudicates via LLM, and aggregates final scores.

## Quick Start

Install the package:

```bash
pip install edlens
```

Run with the heuristic baseline (no API key needed):

```bash
lens --summary "Your clinical summary here" --engine heuristic
```

Run with LLM scoring (requires `OPENAI_API_KEY`):

```bash
lens --summary "Your clinical summary here" --engine llm --model gpt-4o
```

## Features

- Parallel scoring by three role-specific clinical agents
- Shared 8-dimension LENS rubric
- Two scoring modes: `llm` (OpenAI) and `heuristic` (keyword-based baseline)
- Per-role weighted overall scoring based on role priors
- Orchestrator validation, disagreement mapping, and score aggregation
- Human-readable and JSON output formats
- Optional source-grounded evaluation with `--source-text` or `--source-file`

## API Reference

See the [API Reference](api/cli.md) for detailed module documentation.

## Phase 2

See [Source-Grounded Phase 2](source_grounded_phase2.md) for the current design and source-packet plan.


## Phase 2 Scaffold
- Source-grounded benchmark manifest: `/Users/samuel/Documents/LENS Project/data/phase2/benchmarks/source_grounded_demo/manifest.json`
- Runner: `/Users/samuel/Documents/LENS Project/scripts/run_source_grounded_benchmark.py`
