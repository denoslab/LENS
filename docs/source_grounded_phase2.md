# Phase 2: Source-Grounded Evaluation Design

## Goal

Phase 2 extends LENS from summary-only grading to **source-grounded grading**. Instead of judging a summary in isolation, the evaluator compares the AI-generated summary against a patient-specific source record or a structured source packet.

## Why This Matters

A summary can be fluent and easy to read while still being unsafe if it:

- omits clinically important details from the patient record
- contradicts the patient record
- includes unsupported claims
- appears to describe the wrong patient

This is especially important for safety-critical details such as:

- medication timing and high-risk medication changes
- oxygen, device, or monitoring dependence
- insulin, anticoagulation, allergy, or code status information
- recent deterioration or urgent follow-up needs

## Current LENS Behavior

When source text is provided with:

- `--source-text`
- `--source-file`

LENS switches into **source-grounded evaluation mode**.

In this mode, the scorer distinguishes between:

- `unsupported_claims`
- `contradicted_claims`
- `omitted_safety_facts`
- `wrong_patient_suspected`

## Recommended Source Strategy

Avoid sending an entire raw chart when a compact source packet is sufficient. A good source packet should distill the patient record into the most clinically relevant facts for evaluation.

Recommended sections:

- encounter context
- active problems / working diagnoses
- chronic conditions
- recent changes
- medications and timing-sensitive treatments
- procedures / devices
- safety-critical facts
- disposition / follow-up
- supporting excerpts

## Priority Evaluation Checks

Phase 2 should focus on whether LENS can detect:

1. **Wrong-patient mismatch**
2. **Safety-critical omission**
3. **Contradiction**
4. **Unsupported claim**

## Suggested Benchmark Design

Examples of useful source-grounded pairs:

- original source packet + correct summary
- original source packet + omission-heavy summary
- original source packet + contradiction summary
- patient A source packet + patient B summary

## Benchmark Scaffold

The repo includes a local development scaffold for Phase 2:

- manifest: `data/phase2/benchmarks/source_grounded_demo/manifest.json`
- runner: `scripts/run_source_grounded_benchmark.py`

Run the source-grounded pilot with:

```bash
python scripts/run_source_grounded_benchmark.py --model gpt-4o-mini --temperature 0.0 --pretty
```

Run the same manifest in summary-only mode for ablation:

```bash
python scripts/run_source_grounded_benchmark.py --model gpt-4o-mini --temperature 0.0 --evaluation-context summary_only --pretty
```

The runner saves:

- raw per-variant JSON outputs
- `summary.csv`
- `report.md`
- `run_meta.json`

Each raw JSON output also preserves:

- `pre_adjudication_scorecards`
- `initial_disagreement_map`
- `disputed_dimensions`

This makes it easier to analyze how much the final result changed after adjudication.

## Practical Note

Source-grounded evaluation is a stronger faithfulness check than summary-only evaluation, but it still depends on the quality of the source packet and the consistency of LLM judgment. It should be treated as a structured evaluation layer, not as a replacement for clinical verification.
