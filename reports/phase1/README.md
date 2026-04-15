# Phase 1 Results Layout

This folder keeps all Phase 1 experiment artifacts in one predictable place.

## Structure
- `baseline/run/`
  Original Phase 1 CLI experiment outputs (`report.md`, `summary.csv`, `outputs/`).
- `baseline/visuals/`
  Charts and short presentation report generated from the baseline run.
- `baseline/audit/`
  Audit report comparing intended bad-sample degradations against actual score drops.
- `brevity_fix/run/`
  Rerun after the anti-brevity-bias rubric/prompt/profile refinement.
- `brevity_fix/visuals/`
  Charts and short presentation report for the rerun.
- `brevity_fix/audit/`
  Audit report for the rerun.
- `persona_refinement/run/`
  Rerun after the later persona/profile refinement and synthetic-prior seeding.
- `persona_refinement/visuals/`
  Charts and short presentation report for the latest rerun.
- `persona_refinement/audit/`
  Audit report for the latest rerun.
- `custom/`
  Created only when you intentionally run an extra Phase 1-style experiment outside the named benchmark folders.

## Quick Navigation
- Baseline overall report:
  - `baseline/run/report.md`
- Baseline charts:
  - `baseline/visuals/`
- Baseline audit:
  - `baseline/audit/phase1_audit_report.md`
- Brevity-fix overall report:
  - `brevity_fix/run/report.md`
- Brevity-fix charts:
  - `brevity_fix/visuals/`
- Brevity-fix audit:
  - `brevity_fix/audit/phase1_audit_report.md`
- Latest persona-refinement overall report:
  - `persona_refinement/run/report.md`
- Latest persona-refinement charts:
  - `persona_refinement/visuals/`
- Latest persona-refinement audit:
  - `persona_refinement/audit/phase1_audit_report.md`

## Script Defaults
- `scripts/run_cli_sensitivity_experiment.py`
  Defaults to writing new runs into `reports/phase1/custom/run/`.
- `scripts/generate_phase1_visuals.py`
  Defaults to writing charts into a sibling `visuals/` folder next to the selected `run/` folder.
- `scripts/audit_phase1_results.py`
  Defaults to writing the audit into a sibling `audit/` folder next to the selected `run/` folder.
