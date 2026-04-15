# CLI Sensitivity Experiment Report

## 1. Experiment Overview
- Model: `gpt-4o-mini`
- Good samples completed: 10
- Bad samples completed: 10
- Failures: 0
- Output directory: `/Users/samuel/Documents/LENS Project/reports/cli_sensitivity_experiment_brevity_fix`

## 2. Group-level Summary
| Metric | Good | Bad | Delta (Good-Bad) |
| --- | --- | --- | --- |
| overall_across_roles | 3.5157 | 3.2850 | 0.2307 |
| Physician overall | 3.5040 | 3.2310 | 0.2730 |
| Triage Nurse overall | 3.5440 | 3.3120 | 0.2320 |
| Bedside Nurse overall | 3.4990 | 3.3120 | 0.1870 |

## 3. Dimension-level Summary
| Dimension | Good Mean | Bad Mean | Delta (Good-Bad) |
| --- | --- | --- | --- |
| factual_accuracy | 4.5000 | 4.5333 | -0.0333 |
| relevant_chronic_problem_coverage | 3.8333 | 3.4333 | 0.4000 |
| organized_by_condition | 2.9667 | 3.0000 | -0.0333 |
| timeline_evolution | 3.5667 | 2.7667 | 0.8000 |
| recent_changes_highlighted | 2.9333 | 2.3000 | 0.6333 |
| focused_not_cluttered | 3.1667 | 3.4667 | -0.3000 |
| usefulness_for_decision_making | 3.3000 | 3.0333 | 0.2667 |
| clarity_readability_formatting | 3.8333 | 3.9000 | -0.0667 |

## 4. Disagreement Summary
- Average flagged dimensions per good sample: 3.0000
- Average flagged dimensions per bad sample: 3.1000

| Dimension | Good Flag Count | Bad Flag Count |
| --- | --- | --- |
| factual_accuracy | 10 | 9 |
| relevant_chronic_problem_coverage | 4 | 5 |
| organized_by_condition | 2 | 2 |
| timeline_evolution | 1 | 1 |
| recent_changes_highlighted | 2 | 4 |
| focused_not_cluttered | 4 | 7 |
| usefulness_for_decision_making | 6 | 1 |
| clarity_readability_formatting | 1 | 2 |

## 5. Paired Comparison by Source ID
| Source ID | Good Overall | Bad Overall | Delta Overall | Good Flagged Dims | Bad Flagged Dims | Expected Low Dims | Actual Decreased Dims | Hit Rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 3.6367 | 3.3833 | 0.2534 | factual_accuracy, usefulness_for_decision_making | factual_accuracy, recent_changes_highlighted, focused_not_cluttered | factual_accuracy, relevant_chronic_problem_coverage, timeline_evolution, recent_changes_highlighted, usefulness_for_decision_making | relevant_chronic_problem_coverage, timeline_evolution, recent_changes_highlighted, usefulness_for_decision_making | 0.8000 |
| 9 | 3.5767 | 3.4767 | 0.1000 | factual_accuracy, timeline_evolution, recent_changes_highlighted, focused_not_cluttered, usefulness_for_decision_making | factual_accuracy, recent_changes_highlighted, focused_not_cluttered | relevant_chronic_problem_coverage, organized_by_condition, timeline_evolution, usefulness_for_decision_making, clarity_readability_formatting | timeline_evolution, usefulness_for_decision_making | 0.4000 |
| 14 | 3.9300 | 2.9800 | 0.9500 | factual_accuracy, organized_by_condition, recent_changes_highlighted, focused_not_cluttered, usefulness_for_decision_making | clarity_readability_formatting | factual_accuracy, relevant_chronic_problem_coverage, timeline_evolution, recent_changes_highlighted, usefulness_for_decision_making, clarity_readability_formatting | factual_accuracy, relevant_chronic_problem_coverage, timeline_evolution, recent_changes_highlighted, usefulness_for_decision_making, clarity_readability_formatting | 1.0000 |
| 18 | 3.8533 | 3.1967 | 0.6566 | factual_accuracy, relevant_chronic_problem_coverage, focused_not_cluttered, usefulness_for_decision_making | factual_accuracy, relevant_chronic_problem_coverage, organized_by_condition, recent_changes_highlighted, focused_not_cluttered | factual_accuracy, timeline_evolution, recent_changes_highlighted, usefulness_for_decision_making, clarity_readability_formatting | factual_accuracy, timeline_evolution, recent_changes_highlighted, usefulness_for_decision_making | 0.8000 |
| 37 | 3.0867 | 3.4300 | -0.3433 | factual_accuracy | factual_accuracy, focused_not_cluttered | factual_accuracy, recent_changes_highlighted, usefulness_for_decision_making, relevant_chronic_problem_coverage, clarity_readability_formatting | - | 0.0000 |
| 43 | 3.1767 | 3.4600 | -0.2833 | factual_accuracy, usefulness_for_decision_making | factual_accuracy, relevant_chronic_problem_coverage, recent_changes_highlighted, usefulness_for_decision_making | factual_accuracy, recent_changes_highlighted, usefulness_for_decision_making, focused_not_cluttered, clarity_readability_formatting | - | 0.0000 |
| 53 | 3.5800 | 3.3033 | 0.2767 | factual_accuracy | factual_accuracy, relevant_chronic_problem_coverage, focused_not_cluttered | factual_accuracy, relevant_chronic_problem_coverage, timeline_evolution, usefulness_for_decision_making, clarity_readability_formatting | relevant_chronic_problem_coverage, timeline_evolution | 0.4000 |
| 59 | 3.4300 | 2.8767 | 0.5533 | factual_accuracy, relevant_chronic_problem_coverage | factual_accuracy, clarity_readability_formatting | factual_accuracy, relevant_chronic_problem_coverage, usefulness_for_decision_making, focused_not_cluttered, clarity_readability_formatting | relevant_chronic_problem_coverage, clarity_readability_formatting | 0.4000 |
| 62 | 3.7900 | 3.3833 | 0.4067 | factual_accuracy, relevant_chronic_problem_coverage, organized_by_condition, focused_not_cluttered, usefulness_for_decision_making | factual_accuracy, relevant_chronic_problem_coverage, organized_by_condition, timeline_evolution, focused_not_cluttered | factual_accuracy, relevant_chronic_problem_coverage, timeline_evolution, recent_changes_highlighted, usefulness_for_decision_making | timeline_evolution, recent_changes_highlighted, usefulness_for_decision_making | 0.6000 |
| 81 | 3.0967 | 3.3600 | -0.2633 | factual_accuracy, relevant_chronic_problem_coverage, clarity_readability_formatting | factual_accuracy, relevant_chronic_problem_coverage, focused_not_cluttered | relevant_chronic_problem_coverage, organized_by_condition, usefulness_for_decision_making, clarity_readability_formatting | - | 0.0000 |

## 6. Hit-rate Analysis
- Mean per-sample hit rate: 0.4400
- Weighted overall hit rate: 0.4600
