# Phase 1 Experiment Reproduction Guide

This guide explains how to reproduce the current **Phase 1** LENS experiments on the `codex/phase-1_experiment` branch.

Phase 1 is the **summary-only sensitivity** stage of the project.
It does **not** use a patient source record.

## 1. Branch To Use

Use the Phase 1 branch:

```bash
git switch codex/phase-1_experiment
```

## 2. What Phase 1 Tests

Phase 1 tests whether LENS can separate:

- **good summaries**
- **bad summaries with targeted degradations**

The main Phase 1 question is:

> Does LENS give lower scores to intentionally degraded summaries, and does it lower the correct rubric dimensions?

## 3. Phase 1 Data

Input files:

- `data/phase1/raw/MTS-Dialog-ValidationSet_top10_longest_section_texts.txt`
  - good summaries
- `data/phase1/raw/lens_bad_samples_complete_english.txt`
  - bad summaries with annotations
- `data/phase1/clean/phase1_good_summaries.txt`
- `data/phase1/clean/phase1_bad_summaries.txt`

## 4. Phase 1 Scripts

- `scripts/run_cli_sensitivity_experiment.py`
  - runs the paired good vs bad experiment
- `scripts/generate_phase1_visuals.py`
  - generates charts and a short markdown report
- `scripts/audit_phase1_results.py`
  - checks whether expected weak dimensions actually dropped

## 5. Phase 1 Output Layout

The branch stores Phase 1 outputs under:

- `reports/phase1/<label>/run/`
- `reports/phase1/<label>/visuals/`
- `reports/phase1/<label>/audit/`

Saved labels already present on this branch:

- `baseline`
- `brevity_fix`
- `persona_refinement`

## 6. Prerequisites

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

Recommended sanity check before running experiments:

```bash
pytest -q -p no:cacheprovider tests
```

## 7. How To Run Phase 1

### A. Run the main paired sensitivity experiment

```bash
python scripts/run_cli_sensitivity_experiment.py \
  --model gpt-4o-mini \
  --outdir reports/phase1/custom/run \
  --pretty
```

What this does:

- parses the good-summary file
- parses the annotated bad-summary file
- runs LENS on both groups
- saves raw JSON outputs for each sample
- writes `report.md` and `summary.csv`

Useful optional flags:

```bash
python scripts/run_cli_sensitivity_experiment.py --max-samples 3 --pretty
python scripts/run_cli_sensitivity_experiment.py --resume --pretty
python scripts/run_cli_sensitivity_experiment.py --good-file path/to/good.txt --bad-file path/to/bad.txt --pretty
```

### B. Generate Phase 1 visuals

```bash
python scripts/generate_phase1_visuals.py \
  --results-dir reports/phase1/custom/run \
  --outdir reports/phase1/custom/visuals
```

This writes:

- `overall_score_comparison.png`
- `per_role_comparison.png`
- `dimension_score_comparison.png`
- `disagreement_comparison.png`
- `phase1_short_report.md`

### C. Audit whether the expected dimensions dropped

```bash
python scripts/audit_phase1_results.py \
  --results-dir reports/phase1/custom/run \
  --outdir reports/phase1/custom/audit
```

This writes:

- `phase1_audit_report.md`
- `phase1_audit_summary.csv`

The audit measures:

- overall score delta
- pair-level success (`good > bad`)
- mean hit rate
- weighted hit rate
- which expected weak dimensions actually decreased

## 8. Reproducing The Named Phase 1 Runs

This branch preserves three archived result sets:

- `reports/phase1/baseline/`
- `reports/phase1/brevity_fix/`
- `reports/phase1/persona_refinement/`

These are summarized in:

- `reports/phase1/comparison_summary.md`
- `reports/phase1/comparison_summary.csv`

Important note:

- `scripts/run_cli_sensitivity_experiment.py` is a **generic runner**
- the current branch head best matches the latest saved Phase 1 setup
- the repo preserves the historical output folders, but does **not** expose separate frozen config snapshots for each named run inside one checkout

Practical implication:

- use the scripts above to reproduce the **Phase 1 workflow**
- use the saved `baseline`, `brevity_fix`, and `persona_refinement` folders to inspect the archived historical results
- if you intentionally want to regenerate one named folder with the currently checked-out Phase 1 code, change `--outdir` to that folder path

Example:

```bash
python scripts/run_cli_sensitivity_experiment.py \
  --model gpt-4o-mini \
  --outdir reports/phase1/persona_refinement/run \
  --pretty
```

## 9. How To Read The Main Phase 1 Metrics

### Overall Delta (Good - Bad)
The mean overall score difference between good and bad summaries.

### Good > Bad Pairs
The number of source IDs for which the good summary received a higher overall score than the bad summary.

### Mean Hit Rate
The mean proportion of expected weak dimensions that actually decreased in the bad summary.

### Weighted Hit Rate
A pooled version of hit rate across all expected weak dimensions in the benchmark.

## 10. Expected Pattern

For a stronger Phase 1 run, the expected pattern is:

- good summaries score higher than bad summaries
- more good/bad pairs are correctly separated
- hit rate improves because score drops happen in the expected dimensions

## 11. Troubleshooting

### API key missing
If LLM mode fails immediately, confirm:

```bash
echo $OPENAI_API_KEY
```

### Partial run failure
Use:

```bash
python scripts/run_cli_sensitivity_experiment.py --resume --pretty
```

## 12. Important Limitations

- Phase 1 is summary-only and cannot check patient-specific faithfulness
- it is useful for sensitivity testing, not source-grounded clinical validation
- strong Phase 1 results do not guarantee strong patient-level safety evaluation

## 13. Example Full Reproduction Sequence

```bash
export OPENAI_API_KEY=your_openai_api_key_here
export LENS_OPENAI_TIMEOUT_SECONDS=60

git switch codex/phase-1_experiment
pip install -e ".[dev,docs]"
pytest -q -p no:cacheprovider tests

python scripts/run_cli_sensitivity_experiment.py --model gpt-4o-mini --outdir reports/phase1/custom/run --pretty
python scripts/generate_phase1_visuals.py --results-dir reports/phase1/custom/run --outdir reports/phase1/custom/visuals
python scripts/audit_phase1_results.py --results-dir reports/phase1/custom/run --outdir reports/phase1/custom/audit
```

## 14. Contact Between Experiment Design And Code

Phase 1 is implemented mainly through:

- `scripts/run_cli_sensitivity_experiment.py`
- `scripts/generate_phase1_visuals.py`
- `scripts/audit_phase1_results.py`

This keeps the Phase 1 workflow separate from the later source-grounded Phase 2 benchmark.
