# LENS: Role-Aware Clinical Summary Grading

LENS is a role-aware multi-agent grading pipeline for clinical (ED handoff) summaries. Three clinical roles (Physician, Triage Nurse, Bedside Nurse) score summaries in parallel across 8 rubric dimensions, then an orchestrator detects disagreements, optionally adjudicates via LLM, and aggregates final scores.

## Quick Start

Install the package:

```bash
pip install lens-grading
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

## API Reference

See the [API Reference](api/cli.md) for detailed module documentation.
