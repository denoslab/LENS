# CLI Sensitivity Experiment Report

## 1. Experiment Overview
- Model: `gpt-4o-mini`
- Good samples completed: 10
- Bad samples completed: 10
- Failures: 0
- Output directory: `/Users/samuel/Documents/LENS Project/reports/phase1/persona_refinement/run`

## 2. Group-level Summary
| Metric | Good | Bad | Delta (Good-Bad) |
| --- | --- | --- | --- |
| overall_across_roles | 3.6490 | 3.3053 | 0.3437 |
| Physician overall | 3.6490 | 3.2090 | 0.4400 |
| Triage Nurse overall | 3.6580 | 3.3050 | 0.3530 |
| Bedside Nurse overall | 3.6400 | 3.4020 | 0.2380 |

## 3. Dimension-level Summary
| Dimension | Good Mean | Bad Mean | Delta (Good-Bad) |
| --- | --- | --- | --- |
| factual_accuracy | 4.4667 | 4.1667 | 0.3000 |
| relevant_chronic_problem_coverage | 3.7000 | 3.4000 | 0.3000 |
| organized_by_condition | 2.9333 | 3.0333 | -0.1000 |
| timeline_evolution | 3.4667 | 2.7000 | 0.7667 |
| recent_changes_highlighted | 3.0000 | 2.2667 | 0.7333 |
| focused_not_cluttered | 3.6000 | 3.4667 | 0.1333 |
| usefulness_for_decision_making | 3.5667 | 3.0667 | 0.5000 |
| clarity_readability_formatting | 3.8333 | 3.9333 | -0.1000 |

## 4. Disagreement Summary
- Average flagged dimensions per good sample: 2.9000
- Average flagged dimensions per bad sample: 2.0000

| Dimension | Good Flag Count | Bad Flag Count |
| --- | --- | --- |
| factual_accuracy | 8 | 6 |
| relevant_chronic_problem_coverage | 3 | 2 |
| organized_by_condition | 1 | 1 |
| timeline_evolution | 3 | 2 |
| recent_changes_highlighted | 2 | 2 |
| focused_not_cluttered | 4 | 5 |
| usefulness_for_decision_making | 5 | 1 |
| clarity_readability_formatting | 3 | 1 |

## 5. Paired Comparison by Source ID
| Source ID | Good Overall | Bad Overall | Delta Overall | Good Flagged Dims | Bad Flagged Dims | Expected Low Dims | Actual Decreased Dims | Hit Rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 3.9800 | 3.3533 | 0.6267 | factual_accuracy, focused_not_cluttered, usefulness_for_decision_making | focused_not_cluttered | factual_accuracy, relevant_chronic_problem_coverage, timeline_evolution, recent_changes_highlighted, usefulness_for_decision_making | factual_accuracy, relevant_chronic_problem_coverage, timeline_evolution, recent_changes_highlighted, usefulness_for_decision_making | 1.0000 |
| 9 | 3.7867 | 3.4000 | 0.3867 | factual_accuracy, timeline_evolution, recent_changes_highlighted, usefulness_for_decision_making | factual_accuracy, focused_not_cluttered | relevant_chronic_problem_coverage, organized_by_condition, timeline_evolution, usefulness_for_decision_making, clarity_readability_formatting | timeline_evolution, usefulness_for_decision_making | 0.4000 |
| 14 | 3.9933 | 3.1900 | 0.8033 | factual_accuracy, relevant_chronic_problem_coverage, organized_by_condition | - | factual_accuracy, relevant_chronic_problem_coverage, timeline_evolution, recent_changes_highlighted, usefulness_for_decision_making, clarity_readability_formatting | factual_accuracy, relevant_chronic_problem_coverage, timeline_evolution, recent_changes_highlighted, usefulness_for_decision_making | 0.8333 |
| 18 | 3.7933 | 3.1467 | 0.6466 | factual_accuracy, timeline_evolution, focused_not_cluttered, usefulness_for_decision_making | factual_accuracy | factual_accuracy, timeline_evolution, recent_changes_highlighted, usefulness_for_decision_making, clarity_readability_formatting | factual_accuracy, timeline_evolution, recent_changes_highlighted, usefulness_for_decision_making | 0.8000 |
| 37 | 3.1100 | 3.4467 | -0.3367 | factual_accuracy, clarity_readability_formatting | factual_accuracy, focused_not_cluttered | factual_accuracy, recent_changes_highlighted, usefulness_for_decision_making, relevant_chronic_problem_coverage, clarity_readability_formatting | - | 0.0000 |
| 43 | 3.8100 | 3.6100 | 0.2000 | timeline_evolution | factual_accuracy, relevant_chronic_problem_coverage, timeline_evolution, recent_changes_highlighted, usefulness_for_decision_making | factual_accuracy, recent_changes_highlighted, usefulness_for_decision_making, focused_not_cluttered, clarity_readability_formatting | factual_accuracy, recent_changes_highlighted, usefulness_for_decision_making | 0.6000 |
| 53 | 3.3033 | 3.2400 | 0.0633 | factual_accuracy, relevant_chronic_problem_coverage | relevant_chronic_problem_coverage, focused_not_cluttered | factual_accuracy, relevant_chronic_problem_coverage, timeline_evolution, usefulness_for_decision_making, clarity_readability_formatting | factual_accuracy, relevant_chronic_problem_coverage | 0.4000 |
| 59 | 3.4733 | 2.8000 | 0.6733 | focused_not_cluttered, usefulness_for_decision_making, clarity_readability_formatting | factual_accuracy, clarity_readability_formatting | factual_accuracy, relevant_chronic_problem_coverage, usefulness_for_decision_making, focused_not_cluttered, clarity_readability_formatting | factual_accuracy, relevant_chronic_problem_coverage, usefulness_for_decision_making, focused_not_cluttered, clarity_readability_formatting | 1.0000 |
| 62 | 3.8967 | 3.5133 | 0.3834 | factual_accuracy | factual_accuracy, organized_by_condition | factual_accuracy, relevant_chronic_problem_coverage, timeline_evolution, recent_changes_highlighted, usefulness_for_decision_making | timeline_evolution, recent_changes_highlighted, usefulness_for_decision_making | 0.6000 |
| 81 | 3.3433 | 3.3533 | -0.0100 | factual_accuracy, relevant_chronic_problem_coverage, recent_changes_highlighted, focused_not_cluttered, usefulness_for_decision_making, clarity_readability_formatting | timeline_evolution, recent_changes_highlighted, focused_not_cluttered | relevant_chronic_problem_coverage, organized_by_condition, usefulness_for_decision_making, clarity_readability_formatting | usefulness_for_decision_making | 0.2500 |

## 6. Hit-rate Analysis
- Mean per-sample hit rate: 0.5883
- Weighted overall hit rate: 0.6000
