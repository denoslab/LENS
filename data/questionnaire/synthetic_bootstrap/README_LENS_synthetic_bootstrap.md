# LENS synthetic Calgary ED questionnaire bootstrap package

## What this package is

This package is a **synthetic bootstrap dataset** created so the LENS project can continue pipeline development before real questionnaire data are available.
It is designed for:
- Codex-assisted prototyping
- agent weight seeding
- prompt seeding
- integration testing
- ablation studies

It is **not** real clinician data and should **not** be reported as human-subject survey evidence.

## Questionnaire basis

The synthetic data follow the structure of the uploaded questionnaire:
- 3 clinician roles
- 5 experience buckets
- 8 ranked summary-quality dimensions
- 8 downstream preference questions
- 2 optional free-text questions

## Role allocation used for the 100 synthetic respondents

Public anchors were combined with explicit assumptions to create a reasonable Calgary ED sample mix.

Physician anchor:
- Calgary DEM annual report: 202 active physician staff
- Calgary DEM current department page: 240 physicians
- Midpoint used for sampling logic: 221.0

Nursing anchor:
- Department-level nurse anchor used for bootstrap sampling: 1000
- Assumed triage share of nursing pool: 15%
- Resulting triage nurse anchor: 150
- Resulting bedside nurse anchor: 850

Resulting proportional mix:
- Emergency medicine physician: 18.1%
- Triage nurse: 12.3%
- Bedside nurse: 69.6%

Final synthetic sample of 100:
- Emergency medicine physician: 18
- Triage nurse: 12
- Bedside nurse: 70

## Overall Q3-derived weight prior

| Dimension | Weight |
|---|---:|
| Factual accuracy | 0.180 |
| Recent changes highlighted | 0.149 |
| Coverage of relevant chronic and long-term problems | 0.146 |
| Usefulness for decision-making | 0.135 |
| Clarity, readability, and length | 0.133 |
| Keeps only important history | 0.110 |
| Timeline and evolution | 0.078 |
| Organized by condition | 0.069 |

## Role-specific weight priors

### Emergency medicine physician

| Dimension | Weight |
|---|---:|
| Factual accuracy | 0.182 |
| Usefulness for decision-making | 0.159 |
| Recent changes highlighted | 0.157 |
| Timeline and evolution | 0.131 |
| Coverage of relevant chronic and long-term problems | 0.122 |
| Clarity, readability, and length | 0.111 |
| Keeps only important history | 0.097 |
| Organized by condition | 0.040 |

### Triage nurse

| Dimension | Weight |
|---|---:|
| Recent changes highlighted | 0.194 |
| Factual accuracy | 0.171 |
| Usefulness for decision-making | 0.171 |
| Clarity, readability, and length | 0.153 |
| Keeps only important history | 0.125 |
| Coverage of relevant chronic and long-term problems | 0.088 |
| Organized by condition | 0.051 |
| Timeline and evolution | 0.046 |

### Bedside nurse

| Dimension | Weight |
|---|---:|
| Factual accuracy | 0.181 |
| Coverage of relevant chronic and long-term problems | 0.162 |
| Recent changes highlighted | 0.140 |
| Clarity, readability, and length | 0.136 |
| Usefulness for decision-making | 0.122 |
| Keeps only important history | 0.110 |
| Organized by condition | 0.079 |
| Timeline and evolution | 0.070 |

## Files

- `synthetic_calgary_ed_questionnaire_100.csv`  
  Raw respondent-level synthetic data.

- `synthetic_calgary_ed_questionnaire_100.json`  
  Same raw data in JSON.

- `lens_synthetic_aggregate_summary.json`  
  Aggregated distributions and weight summaries.

- `lens_agent_seed_config.json`  
  Ready-to-use role-specific weights plus seed prompts.

- `recompute_lens_weights.py`  
  Minimal script for recomputing weights.

## Suggested Codex workflow

1. Load the CSV.
2. Recompute Borda weights from Q3 for each role.
3. Use `lens_agent_seed_config.json` as the initial prior for role-aware agents.
4. Run your LENS evaluation pipeline on public longitudinal-summary examples.
5. Once the real questionnaire arrives, replace the synthetic priors and re-run calibration.

## Recommended guardrails

- Treat all outputs here as **temporary priors**.
- Keep a config flag such as `source = "synthetic_bootstrap"` so downstream experiments stay traceable.
- Do not mix these data with real questionnaire results in final analysis without a clear label.
- Refit all weights after real clinician responses are collected.

## Example use

You can load the role-specific seed prompts from `lens_agent_seed_config.json` and map them directly into your orchestrator for:
- physician evaluator
- triage nurse evaluator
- bedside nurse evaluator

The weights are already normalized and can be used immediately in a weighted scoring formula.
