# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LENS is a role-aware multi-agent grading pipeline for clinical (ED handoff) summaries. Three clinical roles (Physician, Triage Nurse, Bedside Nurse) score summaries in parallel across 8 rubric dimensions, then an orchestrator detects disagreements, optionally adjudicates via LLM, and aggregates final scores.

## Package

The project is published on PyPI as **`edlens`** and can be installed with `pip install edlens`. The `lens` CLI entry point is registered via `pyproject.toml`.

## Commands

```bash
# Install (editable, with dev + docs extras)
pip install -e ".[dev,docs]"

# Run the pipeline (heuristic mode, no API key needed)
python -m grading_pipeline --summary "..." --engine heuristic

# Run the pipeline (LLM mode, requires OPENAI_API_KEY in .env)
python -m grading_pipeline --summary "..." --engine llm --model gpt-4o

# Run via installed CLI entry point
lens --summary "..." --engine heuristic

# Run from file
python -m grading_pipeline --summary-file path/to/file.txt --engine heuristic

# Output formats: --format human (default) or --format json
# Other flags: --temperature, --gap-threshold, --pretty, --output

# Run tests
pytest -q

# Build and serve API docs locally
mkdocs serve

# Docker
docker build -t lens .
docker run lens --summary "..." --engine heuristic
```

## Architecture

The pipeline flows: **Input → Validate → Parallel Score (3 roles) → Validate Scorecards → Disagreement Map → Conditional Adjudication → Aggregate → Format Output**

### Source Layout (`src/grading_pipeline/`)

- **`__main__.py`** — Enables `python -m grading_pipeline` invocation
- **`cli.py`** — CLI argument parsing, entry point (`main()`), human-readable output formatting. Also registered as the `lens` console script
- **`orchestrator.py`** — Core pipeline logic: `run_pipeline()` coordinates async parallel scoring via `asyncio.gather()`, scorecard validation with retry, disagreement detection (`build_disagreement_map()`), conditional adjudication (LLM mode only, triggered when score gap ≥ threshold), and weighted aggregation
- **`llm_scoring.py`** — `score_summary_llm()` builds role-specific prompts from persona + profile + rubric, calls OpenAI Responses API with JSON schema for structured output
- **`openai_client.py`** — Raw HTTP client for OpenAI Responses API using `urllib` (no external dependencies). Loads API key from `.env` file or environment. Configurable via `OPENAI_BASE_URL`
- **`scoring.py`** — `score_summary_heuristic()` keyword-based baseline scoring engine. Each of the 8 dimensions has its own scoring function. `AgentScore` dataclass holds per-role results. `compute_overall_score()` uses `w_prior` weighted averaging
- **`config.py`** — Dataclasses (`Dimension`, `Rubric`, `RoleProfile`) and loaders for rubric/roles JSON
- **`validation.py`** — Summary input validation (≥30 chars, non-empty)

### Configuration (`config/`)

- **`lens_rubric.json`** — 8 evaluation dimensions with definitions
- **`roles.json`** — 3 roles with `w_prior` weight vectors (per-dimension importance)
- **`role_profiles/*.json`** — Role-specific LLM scoring profiles: evaluation style, priority dimensions, must-have signals, strict downgrade rules

### Schemas (`schemas/`)

- **`agent_output.schema.json`** — JSON Schema for structured agent scoring output

### Documentation (`docs/`)

- API reference docs built with **mkdocs** + **mkdocs-material** + **mkdocstrings**
- Configured in `mkdocs.yml`; deployed via GitHub Actions (`docs.yml` workflow) to GitHub Pages

### CI/CD (`.github/workflows/`)

- **`ci.yml`** — Runs `pytest -q` on push/PR to `main`
- **`docs.yml`** — Builds and deploys API docs to GitHub Pages
- **`docker.yml`** — Builds Docker image
- **`release.yml`** — Publishes to PyPI on GitHub release
- **`bump-and-release.yml`** — Bumps version in `pyproject.toml` and creates a GitHub release

### Docker

- **`Dockerfile`** — Minimal Python 3.12-slim image; installs the package and sets `python -m grading_pipeline` as the entrypoint

### Key Design Details

- **No external runtime dependencies** — HTTP via `urllib`, async via `asyncio`. Dev extras: `pytest`; docs extras: `mkdocs` stack
- **Python ≥ 3.12** required (per `pyproject.toml`)
- **Packaged as `edlens`** on PyPI, built with Hatchling
- **Dual scoring engines**: `llm` (OpenAI API) and `heuristic` (keyword-based baseline)
- **Strict scorecard validation**: all 8 dimensions required, scores in [1,5], rationales as strings, with retry on failure (up to `max_retries`)
- **Disagreement adjudication** only runs in LLM mode when any dimension's cross-role score gap ≥ `gap_threshold` (default 0.5)
- **Per-role weighted overall**: each role's overall score is a weighted average using its `w_prior` weights; cross-role overall is the mean of 3 role overalls
