# LENS: Role-Aware Clinical Summary Grading

<p align="left">
  <img src="static/LENS-logo.png" alt="LENS Logo" width="300">
</p>

<p align="left">
  <a href="https://github.com/denoslab/LENS/actions/workflows/ci.yml"><img src="https://github.com/denoslab/LENS/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://github.com/denoslab/LENS/actions/workflows/docs.yml"><img src="https://github.com/denoslab/LENS/actions/workflows/docs.yml/badge.svg" alt="Docs"></a>
  <a href="https://github.com/denoslab/LENS/actions/workflows/docker.yml"><img src="https://github.com/denoslab/LENS/actions/workflows/docker.yml/badge.svg" alt="Docker"></a>
  <a href="https://denoslab.com/LENS/"><img src="https://img.shields.io/badge/docs-online-blue" alt="API Docs"></a>
</p>

📖 **[Full API documentation](https://denoslab.github.io/LENS/)**

LENS is a role-aware multi-agent grading pipeline for evaluating AI-generated clinical summaries in Emergency Department workflows. The same summary is reviewed from three clinical perspectives:

- `Physician`
- `Triage Nurse`
- `Bedside Nurse`

Each role scores the summary on eight rubric dimensions. LENS preserves per-role scorecards, measures cross-role disagreement, optionally adjudicates disputed dimensions, and reports an overall score.

## Core Capabilities

- Parallel scoring by three role-specific evaluators
- Shared 8-dimension LENS rubric
- Two scoring modes:
  - `llm`: OpenAI model-based scoring
  - `heuristic`: local baseline scoring without API calls
- Role-specific weighting based on questionnaire-derived priors
- Validation, disagreement mapping, and aggregation
- Summary-only and source-grounded evaluation modes
- Human-readable and JSON outputs
- External benchmark runner for Phase 2 source-grounded experiments

## Installation Modes

### 1. Installed package

```bash
pip install edlens
```

This mode uses the **bundled default rubric, roles, and role profiles** packaged with `edlens`.

### 2. Editable development install

```bash
pip install -e ".[dev,docs]"
```

This mode is recommended if you want to modify prompts, configs, or benchmark scripts.

The package has no runtime dependencies beyond the Python standard library.

## Configuration Resolution

By default, the CLI loads bundled package resources for:

- the LENS rubric
- the 3 role definitions
- the role-specific prompt profiles

You can override them with:

- `--rubric path/to/lens_rubric.json`
- `--roles path/to/roles.json`

## API Key Setup

LLM mode requires your own OpenAI API key.

Preferred setup:

```bash
export OPENAI_API_KEY=your_openai_api_key_here
```

Optional `.env` support is also available. LENS checks:

1. `OPENAI_API_KEY` in the current shell environment
2. `.env` in the current working directory
3. `.env` in the repo root when running from a checkout

Optional timeout override:

```bash
export LENS_OPENAI_TIMEOUT_SECONDS=60
```

Important notes:

- `.env` should never be committed
- `heuristic` mode does not require an API key
- the default OpenAI endpoint is `https://api.openai.com/v1/responses`

## Quick Start

Run with the default LLM mode:

```bash
python -m grading_pipeline --summary "Your summary here"
# or
lens --summary "Your summary here"
```

Run with the heuristic baseline:

```bash
lens --engine heuristic --summary "Your summary here"
```

Use a summary file:

```bash
lens --summary-file path/to/summary.txt
```

Run in source-grounded mode:

```bash
lens --summary-file path/to/summary.txt --source-file path/to/source_packet.json --engine llm
```

Output JSON:

```bash
lens --summary "Your summary here" --format json --pretty
```

Include raw summary text in JSON output only when you explicitly want it:

```bash
lens --summary "Your summary here" --format json --include-summary
```

Adjust the disagreement threshold:

```bash
lens --gap-threshold 1.0 --summary "Your summary here"
```

## Source-Grounded Evaluation

When `--source-text` or `--source-file` is provided, LENS switches into **source-grounded evaluation**. The LLM is asked to compare the summary against the patient source record or source packet.

The source-grounded output distinguishes between:

- `unsupported_claims`: the summary says something the source does not support
- `contradicted_claims`: the summary says something that conflicts with the source
- `omitted_safety_facts`: safety-critical source facts are missing from the summary
- `wrong_patient_suspected`: the summary may describe a different patient

This mode is intended to evaluate whether a summary is faithful to patient-specific information, not only whether it sounds clinically plausible.

## Privacy and Sensitive Text Handling

By default, JSON output does **not** echo raw source text or raw summary text.

Instead, LENS stores lightweight metadata such as:

- character count
- SHA-256 hash
- source format metadata

Use `--include-summary` only when you explicitly want raw summary text in the saved output.

## Output Structure

The main JSON output includes:

- `per_role_scorecards`
- `disagreement_map`
- `adjudication_ran`
- `overall_across_roles`
- `source_grounded_summary` when source-grounded mode is used
- `meta`

The `meta` block records run context such as:

- scoring model
- adjudicator model
- disagreement threshold
- evaluation context (`summary_only` or `source_grounded`)
- source truncation metadata when applicable

## Disagreement and Aggregation

LENS computes disagreement **per dimension** using:

```text
score gap = max(role scores) - min(role scores)
```

The CLI default is:

```text
gap threshold = 1.0
```

That means adjudication is triggered when at least one rubric dimension differs by 1 point or more across roles.

Role-level overall score:

```text
Role Overall = weighted average of the 8 dimension scores
```

Cross-role overall score:

```text
Overall Score = average of the 3 role overalls
```

## Benchmark Runner

Phase 2 includes an external source-grounded benchmark runner:

- manifest: `data/phase2/benchmarks/source_grounded_demo/manifest.json`
- runner: `scripts/run_source_grounded_benchmark.py`

Example:

```bash
python scripts/run_source_grounded_benchmark.py --model gpt-4o-mini --pretty
```

Outputs include:

- raw per-variant JSON outputs
- `summary.csv`
- `report.md`
- `run_meta.json`

The benchmark report records:

- timestamp
- git SHA when available
- model name
- rubric / roles / manifest hashes
- attempted / completed / skipped / failed counts

## Testing

Run the full test suite:

```bash
pytest -q
```

## Limitations

- `heuristic` mode is a baseline only; it is not a clinically grounded evaluator
- source packets are distilled representations, not the full EHR
- source-grounded scoring improves faithfulness checks, but it is still an LLM judgment layer rather than ground-truth clinical verification
- `calibrate_weights()` currently normalizes role priors only; it does **not** implement learned bounded calibration yet

## Repository Structure

- `src/grading_pipeline/` — core package
- `src/grading_pipeline/defaults/` — bundled default rubric, roles, and role profiles
- `config/` — editable repo-local config copies
- `schemas/` — checked-in output and source packet schemas
- `scripts/` — experiment runners and utilities
- `docs/` — MkDocs site content
- `tests/` — unit and integration tests
