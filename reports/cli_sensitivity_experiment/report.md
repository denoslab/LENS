# CLI Sensitivity Experiment Report

## 1. Experiment Overview
- Model: `gpt-4o-mini`
- Good samples completed: 10
- Bad samples completed: 10
- Failures: 0
- Output directory: `/Users/samuel/Documents/LENS Project/reports/cli_sensitivity_experiment`

## 2. Group-level Summary
| Metric | Good | Bad | Delta (Good-Bad) |
| --- | --- | --- | --- |
| overall_across_roles | 3.3630 | 3.3567 | 0.0064 |
| Physician overall | 3.4000 | 3.2530 | 0.1470 |
| Triage Nurse overall | 3.3090 | 3.4070 | -0.0980 |
| Bedside Nurse overall | 3.3800 | 3.4100 | -0.0300 |

## 3. Dimension-level Summary
| Dimension | Good Mean | Bad Mean | Delta (Good-Bad) |
| --- | --- | --- | --- |
| factual_accuracy | 4.4667 | 4.5667 | -0.1000 |
| relevant_chronic_problem_coverage | 3.7000 | 3.5000 | 0.2000 |
| organized_by_condition | 2.5000 | 2.9000 | -0.4000 |
| timeline_evolution | 3.2333 | 2.7667 | 0.4667 |
| recent_changes_highlighted | 2.6667 | 2.3667 | 0.3000 |
| focused_not_cluttered | 3.5333 | 3.8667 | -0.3333 |
| usefulness_for_decision_making | 3.1333 | 3.1000 | 0.0333 |
| clarity_readability_formatting | 3.5667 | 3.9000 | -0.3333 |

## 4. Disagreement Summary
- Average flagged dimensions per good sample: 2.6000
- Average flagged dimensions per bad sample: 3.0000

| Dimension | Good Flag Count | Bad Flag Count |
| --- | --- | --- |
| factual_accuracy | 7 | 10 |
| relevant_chronic_problem_coverage | 4 | 5 |
| organized_by_condition | 0 | 0 |
| timeline_evolution | 3 | 2 |
| recent_changes_highlighted | 1 | 2 |
| focused_not_cluttered | 6 | 4 |
| usefulness_for_decision_making | 1 | 5 |
| clarity_readability_formatting | 4 | 2 |

## 5. Paired Comparison by Source ID
| Source ID | Good Overall | Bad Overall | Delta Overall | Good Flagged Dims | Bad Flagged Dims | Expected Low Dims | Actual Decreased Dims | Hit Rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 3.4100 | 3.5333 | -0.1233 | recent_changes_highlighted, focused_not_cluttered | factual_accuracy, usefulness_for_decision_making | factual_accuracy, relevant_chronic_problem_coverage, timeline_evolution, recent_changes_highlighted, usefulness_for_decision_making | relevant_chronic_problem_coverage, recent_changes_highlighted | 0.4000 |
| 9 | 3.3033 | 3.3133 | -0.0100 | factual_accuracy, relevant_chronic_problem_coverage, focused_not_cluttered, clarity_readability_formatting | factual_accuracy, relevant_chronic_problem_coverage, timeline_evolution, focused_not_cluttered | relevant_chronic_problem_coverage, organized_by_condition, timeline_evolution, usefulness_for_decision_making, clarity_readability_formatting | timeline_evolution | 0.2000 |
| 14 | 3.4267 | 3.0700 | 0.3567 | factual_accuracy, relevant_chronic_problem_coverage, focused_not_cluttered, clarity_readability_formatting | factual_accuracy, relevant_chronic_problem_coverage, focused_not_cluttered, usefulness_for_decision_making, clarity_readability_formatting | factual_accuracy, relevant_chronic_problem_coverage, timeline_evolution, recent_changes_highlighted, usefulness_for_decision_making, clarity_readability_formatting | timeline_evolution, recent_changes_highlighted, usefulness_for_decision_making | 0.5000 |
| 18 | 3.8033 | 3.4800 | 0.3233 | factual_accuracy, timeline_evolution | factual_accuracy | factual_accuracy, timeline_evolution, recent_changes_highlighted, usefulness_for_decision_making, clarity_readability_formatting | timeline_evolution, recent_changes_highlighted, usefulness_for_decision_making | 0.6000 |
| 37 | 2.8567 | 3.5300 | -0.6733 | factual_accuracy | factual_accuracy, usefulness_for_decision_making | factual_accuracy, recent_changes_highlighted, usefulness_for_decision_making, relevant_chronic_problem_coverage, clarity_readability_formatting | - | 0.0000 |
| 43 | 3.4367 | 3.5600 | -0.1233 | - | factual_accuracy, relevant_chronic_problem_coverage, timeline_evolution, recent_changes_highlighted, usefulness_for_decision_making | factual_accuracy, recent_changes_highlighted, usefulness_for_decision_making, focused_not_cluttered, clarity_readability_formatting | factual_accuracy | 0.2000 |
| 53 | 3.3700 | 3.4267 | -0.0567 | factual_accuracy, focused_not_cluttered | factual_accuracy, relevant_chronic_problem_coverage, usefulness_for_decision_making | factual_accuracy, relevant_chronic_problem_coverage, timeline_evolution, usefulness_for_decision_making, clarity_readability_formatting | relevant_chronic_problem_coverage | 0.2000 |
| 59 | 3.4600 | 2.8833 | 0.5767 | factual_accuracy, relevant_chronic_problem_coverage, focused_not_cluttered, clarity_readability_formatting | factual_accuracy, recent_changes_highlighted, clarity_readability_formatting | factual_accuracy, relevant_chronic_problem_coverage, usefulness_for_decision_making, focused_not_cluttered, clarity_readability_formatting | factual_accuracy, relevant_chronic_problem_coverage | 0.4000 |
| 62 | 3.4767 | 3.3700 | 0.1067 | factual_accuracy, timeline_evolution, focused_not_cluttered, clarity_readability_formatting | factual_accuracy, focused_not_cluttered | factual_accuracy, relevant_chronic_problem_coverage, timeline_evolution, recent_changes_highlighted, usefulness_for_decision_making | timeline_evolution, recent_changes_highlighted | 0.4000 |
| 81 | 3.0867 | 3.4000 | -0.3133 | relevant_chronic_problem_coverage, timeline_evolution, usefulness_for_decision_making | factual_accuracy, relevant_chronic_problem_coverage, focused_not_cluttered | relevant_chronic_problem_coverage, organized_by_condition, usefulness_for_decision_making, clarity_readability_formatting | usefulness_for_decision_making | 0.2500 |

## 6. Hit-rate Analysis
- Mean per-sample hit rate: 0.3150
- Weighted overall hit rate: 0.3200
