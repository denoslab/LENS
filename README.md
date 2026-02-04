# LENS-A-Role-Aware-Evaluation-Framework

Role-aware, multi-agent grading pipeline that scores the same clinical summary in parallel across 8 rubric dimensions. Supports both a heuristic baseline and GPT-4o scoring with structured JSON output.

## What It Does
- Runs three role agents (Physician, Triage Nurse, Bedside Nurse) in parallel.
- Scores 8 rubric dimensions on a 1-5 scale.
- Produces an overall score per role (weighted by role priors).
- Outputs in human-readable or JSON format.

## Quick Start
1. Create a local `.env` (not committed):
   - Copy `.env.example` to `.env`.
   - Set `OPENAI_API_KEY` in `.env`.
2. Run:
```bash
python -m grading_pipeline --summary "Your summary here"
```

## Usage
Run with GPT-4o (default engine):
```bash
python -m grading_pipeline --summary "Your summary here"
```

Run with heuristic baseline:
```bash
python -m grading_pipeline --engine heuristic --summary "Your summary here"
```

JSON output:
```bash
python -m grading_pipeline --summary "Your summary here" --format json --pretty
```

Choose model and temperature:
```bash
python -m grading_pipeline --model gpt-4o --temperature 0.2 --summary "Your summary here"
```

Use a summary file:
```bash
python -m grading_pipeline --summary-file path/to/summary.txt
```

## Output (Human Format)
```
Physician Agent:
Factual Accuracy: 3
Relevant Chronic Problem Coverage: 4
Organized by Condition: 2
Timeline and Evolution: 3
Recent Changes Highlighted: 1
Focused and Not Cluttered: 4
Usefulness for Decision-Making: 4
Clarity, Readability, and Formatting: 2
Overall: 2.88
```

## Project Structure
- `config/`
  - `lens_rubric.json`: 8-dimension rubric definitions
  - `roles.json`: role personas and prior weights
- `grading_pipeline/`
  - `cli.py`: CLI entrypoint
  - `llm_scoring.py`: GPT-4o scoring
  - `scoring.py`: heuristic baseline + scoring utilities
  - `openai_client.py`: minimal OpenAI Responses API client
- `schemas/`
  - `agent_output.schema.json`: agent output schema

## Notes
- `.env` is ignored by git.
- This scaffold can be extended with disagreement resolution and aggregation.
