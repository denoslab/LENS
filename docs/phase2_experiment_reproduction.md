# Phase 2 Experiment Reproduction Guide

This guide explains how to reproduce the current **Phase 2** LENS experiments on the `codex/phase_2_experiment` branch.

Phase 2 is the **source-grounded** stage of the project.
It tests whether LENS becomes more reliable when the patient source record is available.

## 1. Branch To Use

Use the Phase 2 branch:

```bash
git switch codex/phase_2_experiment
```

## 2. What Phase 2 Tests

The main comparison is:

- `source_grounded`
  - the summary is scored against the paired patient source packet
- `summary_only`
  - the same summary is scored in isolation, without the source packet

This makes it possible to measure how much source grounding improves:

- overall score separation
- dimension-level sensitivity
- wrong-patient mismatch detection

## 3. Benchmark Used In This Repo

The current Phase 2 benchmark is a **small synthetic pilot benchmark**.

Benchmark manifest:

- `data/phase2/benchmarks/source_grounded_demo/manifest.json`

The manifest currently defines:

- `5` patient cases
- `3` summary variants per case
- `15` total benchmark evaluations

For each case, the three summary variants are:

1. `reference`
   - a correct summary for the same patient
2. `safety_critical_omission`
   - a degraded summary for the same patient with important safety details removed
3. `wrong_patient_mismatch`
   - a summary from a different patient

This benchmark is intended for **method development and pilot evaluation**, not final clinical validation.

## 4. Repository Paths

Important files and folders:

- Benchmark runner:
  - `scripts/run_source_grounded_benchmark.py`
- Manifest:
  - `data/phase2/benchmarks/source_grounded_demo/manifest.json`
- Case files:
  - `data/phase2/benchmarks/source_grounded_demo/cases/`
- LENS rubric:
  - `config/lens_rubric.json`
- Role definitions:
  - `config/roles.json`

Outputs will be written to:

- Source-grounded run:
  - `reports/phase2/source_grounded_demo/`
- Summary-only run:
  - `reports/phase2/source_grounded_demo_summary_only/`

## 5. Prerequisites

You need:

- Python available in your shell
- access to the LENS repository checkout
- a valid OpenAI API key for LLM mode

Recommended setup:

```bash
export OPENAI_API_KEY=your_openai_api_key_here
export LENS_OPENAI_TIMEOUT_SECONDS=60
```

Editable install:

```bash
pip install -e ".[dev,docs]"
```

Recommended sanity check before running the benchmark:

```bash
pytest -q -p no:cacheprovider tests
```

## 6. How To Run The Phase 2 Experiments

### A. Source-grounded experiment

This is the main Phase 2 experiment.

```bash
python scripts/run_source_grounded_benchmark.py \
  --model gpt-4o-mini \
  --temperature 0.0 \
  --evaluation-context source_grounded \
  --pretty
```

What this does:

- reads the benchmark manifest
- loads all 5 cases
- runs all 15 summary variants
- passes both `--summary-file` and `--source-file` into the LENS CLI
- saves raw outputs and summary reports

### B. Summary-only ablation

This runs the same 15 summary variants, but **without** the source packet.

```bash
python scripts/run_source_grounded_benchmark.py \
  --model gpt-4o-mini \
  --temperature 0.0 \
  --evaluation-context summary_only \
  --pretty
```

What this does:

- uses the same benchmark manifest
- uses the same summaries
- does **not** pass `--source-file`
- tests how LENS behaves when the summary is judged in isolation

## 7. Optional Useful Flags

### Limit the run to a smaller subset

```bash
python scripts/run_source_grounded_benchmark.py --max-cases 1 --pretty
```

### Resume a partially completed run

```bash
python scripts/run_source_grounded_benchmark.py --resume --pretty
```

### Override output directory

```bash
python scripts/run_source_grounded_benchmark.py \
  --evaluation-context source_grounded \
  --outdir reports/phase2/my_custom_run \
  --pretty
```

### Override model

```bash
python scripts/run_source_grounded_benchmark.py --model gpt-4o
```

## 8. What The Runner Actually Calls

For each benchmark variant, the runner calls the existing public CLI workflow.

Source-grounded mode uses the pattern:

```bash
python -m grading_pipeline \
  --engine llm \
  --model gpt-4o-mini \
  --temperature 0.0 \
  --format json \
  --summary-file <summary_file> \
  --source-file <source_file> \
  --rubric config/lens_rubric.json \
  --roles config/roles.json
```

Summary-only mode uses the same pattern, but omits `--source-file`.

## 9. Output Files

Each run directory contains:

### `outputs/`
Per-variant raw JSON outputs, for example:

- `case_001__reference.json`
- `case_001__safety_omission.json`
- `case_001__wrong_patient_case_002.json`

These raw JSON outputs preserve:

- `pre_adjudication_scorecards`
- `initial_disagreement_map`
- `disputed_dimensions`
- final `per_role_scorecards`
- `disagreement_map`
- `overall_across_roles`
- `source_grounded_summary` when applicable
- `meta`

### `summary.csv`
A compact experiment summary table with one row per variant.

Important columns include:

- `case_id`
- `variant_id`
- `variant_type`
- `overall`
- `overall_delta_vs_reference`
- `hit_rate`
- `wrong_patient_suspected`
- `unsupported_claim_count`
- `contradicted_claim_count`
- `omitted_safety_fact_count`

### `report.md`
A human-readable markdown report containing:

- run metadata
- experiment overview
- aggregate metrics
- per-variant summary

### `run_meta.json`
Machine-readable metadata for reproducibility, including:

- timestamp
- git SHA
- model
- temperature
- evaluation context
- manifest path and hash
- rubric path and hash
- roles path and hash
- attempted/completed/skipped/failed counts

## 10. How To Read The Main Metrics

### Overall Mean
The mean overall score for a summary type.

Use this to check whether LENS separates:

- correct summaries
- omission summaries
- wrong-patient summaries

### Hit Rate Mean
The proportion of expected weak dimensions that actually decreased.

Use this to check whether LENS lowered the scores in the **correct dimensions**, not just the total score.

### Wrong-Patient Detection Rate
The proportion of wrong-patient summaries flagged as patient mismatch.

Use this to check whether source grounding allows LENS to identify patient-summary inconsistency.

## 11. Expected Pattern

For the current synthetic pilot benchmark, the expected qualitative pattern is:

### In `source_grounded` mode

- `reference` summaries should receive the highest scores
- `safety_critical_omission` summaries should receive clearly lower scores
- `wrong_patient_mismatch` summaries should receive the lowest scores
- wrong-patient detection should be much stronger than in summary-only mode

### In `summary_only` mode

- `reference` summaries should still score well
- omission summaries may still score relatively high
- wrong-patient summaries may appear fluent and can still receive high scores

This contrast is the main purpose of the Phase 2 ablation.

## 12. Reproducing The Current Ablation Comparison

After both experiments are complete, you can generate the Phase 2 comparison figure and slide text with:

```bash
python scripts/generate_phase2_ablation_visuals.py
```

This writes:

- `reports/phase2/ablation_visuals/source_grounded_vs_summary_only_ablation.png`
- `reports/phase2/ablation_visuals/phase2_ablation_comparison.csv`
- `reports/phase2/ablation_visuals/phase2_ablation_result_slide.md`

## 13. Troubleshooting

### API key missing
If LLM mode fails immediately, confirm:

```bash
echo $OPENAI_API_KEY
```

### Timeout or API instability
Try increasing timeout:

```bash
export LENS_OPENAI_TIMEOUT_SECONDS=90
```

### Partial run failure
Use:

```bash
python scripts/run_source_grounded_benchmark.py --resume --pretty
```

### Per-variant error logs
If a variant fails, inspect the corresponding file in `outputs/`, for example:

- `case_003__safety_omission.error.txt`

## 14. Important Limitations

- This benchmark is synthetic and small
- It is useful for pipeline development and pilot evaluation
- It should not be presented as real-world clinical validation
- Strong results on this benchmark do not guarantee performance on real EHR or MIMIC data

## 15. Recommended Reproduction Workflow

For a clean reproduction, follow this order:

1. set `OPENAI_API_KEY`
2. run the test suite
3. run the `source_grounded` experiment
4. run the `summary_only` ablation
5. compare `summary.csv`, `report.md`, and `run_meta.json`
6. generate the comparison visuals if needed

## 16. Example Full Reproduction Sequence

```bash
export OPENAI_API_KEY=your_openai_api_key_here
export LENS_OPENAI_TIMEOUT_SECONDS=60

pytest -q -p no:cacheprovider tests

python scripts/run_source_grounded_benchmark.py \
  --model gpt-4o-mini \
  --temperature 0.0 \
  --evaluation-context source_grounded \
  --pretty

python scripts/run_source_grounded_benchmark.py \
  --model gpt-4o-mini \
  --temperature 0.0 \
  --evaluation-context summary_only \
  --pretty

python scripts/generate_phase2_ablation_visuals.py
```

## 17. Contact Between Experiment Design And Code

Phase 2 is implemented through three main parts of the repo:

- `src/grading_pipeline/source_packets.py`
  - loads and renders structured source packets
- `src/grading_pipeline/llm_scoring.py`
  - builds source-grounded prompts and source-grounded output schema
- `src/grading_pipeline/orchestrator.py`
  - runs the role-aware grading flow, disagreement analysis, adjudication, and final aggregation

The benchmark runner itself is external by design:

- `scripts/run_source_grounded_benchmark.py`

This keeps Phase 2 experiments aligned with the same CLI workflow that end users run.
