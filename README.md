# LENS: A Role-Aware Evaluation Framework

LENS is a role-aware multi-agent grading pipeline for clinical summaries. The same summary is scored in parallel by three role-specific agents:

- `Physician`
- `Triage Nurse`
- `Bedside Nurse`

Each role scores the summary across 8 rubric dimensions on a `1-5` scale. The system then computes a role-level weighted overall score, a cross-role overall score, and an `Orchestrator Disagreement` view that shows how far the three role scores differ on each dimension.

## Core Capabilities

- Parallel scoring by three role-specific agents
- Shared 8-dimension LENS rubric
- Two scoring modes:
  - `llm`: OpenAI model-based scoring
  - `heuristic`: local baseline scoring without API calls
- Per-role weighted overall scoring based on questionnaire-derived role priors
- Orchestrator validation, disagreement mapping, and score aggregation
- Human-readable and JSON outputs

## Pipeline Overview

1. Input a clinical summary.
2. Load rubric definitions and role configurations.
3. Run the three role agents in parallel.
4. Validate each role scorecard.
5. Build an `Orchestrator Disagreement` map for all 8 dimensions.
6. Aggregate the role outputs into:
   - per-role scores
   - per-role overall scores
   - final overall score across roles

## Repository Structure

- `config/lens_rubric.json`
  Defines the 8 rubric dimensions and evaluation focus.
- `config/roles.json`
  Defines the three role agents, persona metadata, and `w_prior` weights.
- `grading_pipeline/cli.py`
  Command-line entrypoint and human-readable output formatting.
- `grading_pipeline/orchestrator.py`
  Runs the multi-agent pipeline, validation, disagreement mapping, and aggregation.
- `grading_pipeline/llm_scoring.py`
  LLM-based scoring logic.
- `grading_pipeline/scoring.py`
  Heuristic baseline scoring and score utilities.
- `grading_pipeline/openai_client.py`
  Minimal OpenAI Responses API client.
- `tests/`
  Input-validation and orchestrator tests.

## Requirements

- Python 3.10+
- OpenAI API key for `llm` mode

This project uses the Python standard library only. There is no dependency installation step at the moment.

## API Key Setup

If you want to run the LLM pipeline, you must use **your own OpenAI API key**.

Create a file named `.env` in the **project root**.

Project root:
- same folder as `README.md`
- same folder as `config/`
- same folder as `grading_pipeline/`

Expected file location:
```bash
LENS Project/.env
```

Add the following line to `.env`:
```bash
OPENAI_API_KEY=your_openai_api_key_here
```

Optional override:
```bash
OPENAI_BASE_URL=https://api.openai.com/v1/responses
```

You can use `.env.example` as the template:
```bash
cp .env.example .env
```

Important notes:
- `.env` is already ignored by git and should not be committed.
- If you run with `--engine heuristic`, no API key is required.
- The code reads `OPENAI_API_KEY` from `.env` first, then falls back to your shell environment.

## Quick Start

Run with the default LLM mode:
```bash
python -m grading_pipeline --summary "Your summary here"
```

Run with the heuristic baseline:
```bash
python -m grading_pipeline --engine heuristic --summary "Your summary here"
```

Use a summary file:
```bash
python -m grading_pipeline --summary-file path/to/summary.txt
```

Output JSON instead of the human-readable report:
```bash
python -m grading_pipeline --summary "Your summary here" --format json --pretty
```

Select a specific model:
```bash
python -m grading_pipeline --model gpt-4o-mini --summary "Your summary here"
```

Adjust the disagreement threshold:
```bash
python -m grading_pipeline --gap-threshold 0.5 --summary "Your summary here"
```

## Input Rules

The CLI validates summary input before the scoring pipeline runs.

The summary must:
- be provided through `--summary` or `--summary-file`
- not be empty
- not be whitespace only
- be at least `30` characters after trimming whitespace

If the summary is invalid, the CLI exits with a non-zero code and no scoring call is made.

## Output

The human-readable output includes:
- role-by-role scores for all 8 dimensions
- a weighted `Overall` score for each role
- `Orchestrator Disagreement` showing score gaps per dimension
- final `Overall Score` across all three roles

Example output shape:
```text
----------------------------------------
Role-Aware Multi-Agent Grading Pipeline:
----------------------------------------
Physician:
Factual Accuracy: 5.0
Relevant Chronic Problem Coverage: 4.0
...

Overall: 4.12
----------------------------------------
Triage Nurse:
...
----------------------------------------
Bedside Nurse:
...
----------------------------------------
----------------------------------------
Orchestrator Disagreement:
----------------------------------------
Factual Accuracy: 1.0
Relevant Chronic Problem Coverage: 0.0
...
----------------------------------------
Overall Score: 4.0
```

## Scoring Logic

Each role has its own prior weights in `config/roles.json`.

Role-level overall score:
```text
Role Overall = weighted average of the 8 dimension scores
```

Cross-role overall score:
```text
Overall Score = average of the 3 role overall scores
```

Disagreement per dimension:
```text
Gap = highest agent score - lowest agent score
```

## Testing

Run the test suite:
```bash
pytest -q
```

Current tests cover:
- CLI summary input validation
- disagreement-map correctness
- validation and repair behavior
- conditional adjudication behavior
- weighted aggregation behavior

## Current Status

The current implementation includes:
- parallel three-role scoring
- role-aware weighting
- strict input validation
- orchestrator disagreement reporting
- weighted final score aggregation
- human-readable report formatting for demo and presentation use
