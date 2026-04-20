# Phase 2: Source-Grounded Evaluation Design

## Goal

Phase 2 extends LENS from summary-only grading to **source-grounded grading**.
Instead of judging a summary in isolation, the model compares the generated
summary against a patient-specific source record or a structured source packet.

## Why this matters

A summary can be well written but still be unsafe or wrong if it:
- omits clinically important details from the patient record
- contradicts the source record
- includes unsupported claims
- appears to describe the wrong patient

This matters especially for safety-critical details such as:
- medication timing or high-risk medication changes
- oxygen, device, or monitoring dependence
- insulin, anticoagulation, allergy, or code status information
- recent deterioration or urgent follow-up needs

## Current implementation status

The pipeline now accepts optional source text via:
- `--source-text`
- `--source-file`

When source text is provided, the LLM scorer switches into a
**source-grounded evaluation mode** and is instructed to compare the summary
against the source record rather than score the summary in isolation.

## Recommended source strategy

Do not send an entire raw EHR chart directly unless necessary.
Instead, prepare a **source packet** that distills the patient record into a
compact, clinically relevant representation for evaluation.

Recommended packet sections:
- encounter context
- active problems / working diagnoses
- chronic conditions
- recent changes
- medications and timing-sensitive treatments
- procedures / devices
- safety-critical facts
- disposition / follow-up
- short supporting excerpts

## Priority evaluation checks

Phase 2 should focus on whether LENS can detect:
1. **Wrong-patient mismatch**
   - summary content does not match the patient source record
2. **Safety-critical omission**
   - a clinically important detail is missing even though the summary still reads well
3. **Contradiction**
   - summary states something inconsistent with the source
4. **Unsupported claim**
   - summary adds facts not supported by the source

## Suggested benchmark design

Build paired source-grounded tests such as:
- original source packet + correct summary
- original source packet + omission-heavy summary
- original source packet + contradiction summary
- patient A source packet + patient B summary (wrong-patient mismatch)

## Practical next step

Start with manually curated source packets for a small number of cases.
This is a lower-risk way to test source-grounded prompting before attempting
full EHR ingestion.

## Runner scaffold

A local Phase 2 scaffold is now included:
- benchmark manifest: `/Users/samuel/Documents/LENS Project/data/phase2/benchmarks/source_grounded_demo/manifest.json`
- runner: `/Users/samuel/Documents/LENS Project/scripts/run_source_grounded_benchmark.py`

This scaffold is meant for development-time validation of wrong-patient mismatch and safety-critical omission behavior.
