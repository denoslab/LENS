# Phase 1 Audit Report

## 1. Overview
- Result folder used: `/Users/samuel/Documents/LENS Project/reports/cli_sensitivity_experiment`
- Selection note: candidate=cli_sensitivity_experiment, good_json=10, bad_json=10, report=yes, summary=yes Assumption: this is the only result folder with paired JSON outputs.
- Bad annotation file: `/Users/samuel/Desktop/LENS Project/lens_bad_samples_complete_english.txt`
- Good output directory: `/Users/samuel/Documents/LENS Project/reports/cli_sensitivity_experiment/outputs/good`
- Bad output directory: `/Users/samuel/Documents/LENS Project/reports/cli_sensitivity_experiment/outputs/bad`
- Good/bad pairs successfully audited: `10`
- Missing or failed pairs: `0`

## 2. Per-sample Audit

### Source ID 0
- Badness type: `Timeline distortion + omission-heavy`
- Expected low-scoring dimensions: `factual_accuracy, relevant_chronic_problem_coverage, timeline_evolution, recent_changes_highlighted, usefulness_for_decision_making`
- Degradation note: Removed key details such as The original traumatic low back injury occurred eight years earlier; Continuo.... Replaced specifics with broader wording (Replaced a long chronic pain history with "occasional back discomfort in the...). Additional change: Added "was functioning well until this new event," which is inconsistent with....
- Good overall_across_roles: `3.4100`
- Bad overall_across_roles: `3.5333`
- Delta overall (good - bad): `-0.1233`
- Good flagged dimensions: `focused_not_cluttered, recent_changes_highlighted`
- Bad flagged dimensions: `factual_accuracy, usefulness_for_decision_making`
- Hit rate: `0.4000`

| Dimension | Good Mean | Bad Mean | Delta | Result |
| --- | --- | --- | --- | --- |
| factual_accuracy | 4.0000 | 4.6667 | -0.6667 | MISS |
| relevant_chronic_problem_coverage | 4.0000 | 3.0000 | 1.0000 | HIT |
| timeline_evolution | 3.0000 | 3.0000 | 0.0000 | MISS |
| recent_changes_highlighted | 3.6667 | 3.0000 | 0.6667 | HIT |
| usefulness_for_decision_making | 3.0000 | 3.3333 | -0.3333 | MISS |

Interpretation: Removed key details such as The original traumatic low back injury occurred eight years earlier; Continuo.... Replaced specifics with broader wording (Replaced a long chronic pain history with "occasional back discomfort in the...). Additional change: Added "was functioning well until this new event," which is inconsistent with.... Observed score drops were partially consistent with the intended degradation. The largest observed decreases were in Relevant Chronic Problem Coverage, Recent Changes Highlighted. The bad summary unexpectedly received a higher overall score than the matched good summary. Expected decreases were missed for Factual Accuracy, Timeline and Evolution, Usefulness for Decision-Making.

### Source ID 9
- Badness type: `Under-specification + omission-heavy + poor organization`
- Expected low-scoring dimensions: `relevant_chronic_problem_coverage, organized_by_condition, timeline_evolution, usefulness_for_decision_making, clarity_readability_formatting`
- Degradation note: Removed key details such as Recurrent bunion deformity in both feet, right greater than left; Pain specif.... Replaced specifics with broader wording (Replaced "recurrent bunion deformity in bilateral feet" with the less precise...). Additional change: Added "without much additional complexity," which downplays the structural re....
- Good overall_across_roles: `3.3033`
- Bad overall_across_roles: `3.3133`
- Delta overall (good - bad): `-0.0100`
- Good flagged dimensions: `clarity_readability_formatting, factual_accuracy, focused_not_cluttered, relevant_chronic_problem_coverage`
- Bad flagged dimensions: `factual_accuracy, focused_not_cluttered, relevant_chronic_problem_coverage, timeline_evolution`
- Hit rate: `0.2000`

| Dimension | Good Mean | Bad Mean | Delta | Result |
| --- | --- | --- | --- | --- |
| relevant_chronic_problem_coverage | 3.6667 | 4.3333 | -0.6667 | MISS |
| organized_by_condition | 3.0000 | 3.0000 | 0.0000 | MISS |
| timeline_evolution | 3.0000 | 2.3333 | 0.6667 | HIT |
| usefulness_for_decision_making | 3.0000 | 3.0000 | 0.0000 | MISS |
| clarity_readability_formatting | 3.6667 | 4.0000 | -0.3333 | MISS |

Interpretation: Removed key details such as Recurrent bunion deformity in both feet, right greater than left; Pain specif.... Replaced specifics with broader wording (Replaced "recurrent bunion deformity in bilateral feet" with the less precise...). Additional change: Added "without much additional complexity," which downplays the structural re.... Observed score drops showed weak alignment with the intended degradation. The largest observed decreases were in Timeline and Evolution. The bad summary unexpectedly received a higher overall score than the matched good summary. Expected decreases were missed for Relevant Chronic Problem Coverage, Organized by Condition, Usefulness for Decision-Making, Clarity, Readability, and Formatting.

### Source ID 14
- Badness type: `Omission-heavy + contradiction + vagueness`
- Expected low-scoring dimensions: `factual_accuracy, relevant_chronic_problem_coverage, timeline_evolution, recent_changes_highlighted, usefulness_for_decision_making, clarity_readability_formatting`
- Degradation note: Removed key details such as Hypertension; Prior stroke in 2002 with minimal residual right-sided weakness. Replaced specifics with broader wording (Replaced the detailed neurologic history with the vague phrase "discomfort in...). Additional change: Added "otherwise relatively stable," which is not supported by the source.
- Good overall_across_roles: `3.4267`
- Bad overall_across_roles: `3.0700`
- Delta overall (good - bad): `0.3567`
- Good flagged dimensions: `clarity_readability_formatting, factual_accuracy, focused_not_cluttered, relevant_chronic_problem_coverage`
- Bad flagged dimensions: `clarity_readability_formatting, factual_accuracy, focused_not_cluttered, relevant_chronic_problem_coverage, usefulness_for_decision_making`
- Hit rate: `0.5000`

| Dimension | Good Mean | Bad Mean | Delta | Result |
| --- | --- | --- | --- | --- |
| factual_accuracy | 4.6667 | 4.6667 | 0.0000 | MISS |
| relevant_chronic_problem_coverage | 4.3333 | 4.3333 | 0.0000 | MISS |
| timeline_evolution | 3.0000 | 2.0000 | 1.0000 | HIT |
| recent_changes_highlighted | 3.0000 | 2.0000 | 1.0000 | HIT |
| usefulness_for_decision_making | 3.0000 | 2.3333 | 0.6667 | HIT |
| clarity_readability_formatting | 3.3333 | 3.3333 | 0.0000 | MISS |

Interpretation: Removed key details such as Hypertension; Prior stroke in 2002 with minimal residual right-sided weakness. Replaced specifics with broader wording (Replaced the detailed neurologic history with the vague phrase "discomfort in...). Additional change: Added "otherwise relatively stable," which is not supported by the source. Observed score drops were partially consistent with the intended degradation. The largest observed decreases were in Timeline and Evolution, Recent Changes Highlighted, Usefulness for Decision-Making. The bad summary received a lower overall score than the matched good summary. Expected decreases were missed for Factual Accuracy, Relevant Chronic Problem Coverage, Clarity, Readability, and Formatting.

### Source ID 18
- Badness type: `Direct contradiction + medication-link removal`
- Expected low-scoring dimensions: `factual_accuracy, timeline_evolution, recent_changes_highlighted, usefulness_for_decision_making, clarity_readability_formatting`
- Degradation note: Removed key details such as The patient denied a spinning sensation and distinguished this from prior ver.... Replaced specifics with broader wording (Replaced position-related lightheadedness with "recurrent vertigo."). Additional change: Added "there has been no meaningful worsening," which conflicts with the source.
- Good overall_across_roles: `3.8033`
- Bad overall_across_roles: `3.4800`
- Delta overall (good - bad): `0.3233`
- Good flagged dimensions: `factual_accuracy, timeline_evolution`
- Bad flagged dimensions: `factual_accuracy`
- Hit rate: `0.6000`

| Dimension | Good Mean | Bad Mean | Delta | Result |
| --- | --- | --- | --- | --- |
| factual_accuracy | 4.6667 | 4.6667 | 0.0000 | MISS |
| timeline_evolution | 3.6667 | 3.0000 | 0.6667 | HIT |
| recent_changes_highlighted | 4.0000 | 3.0000 | 1.0000 | HIT |
| usefulness_for_decision_making | 4.0000 | 3.0000 | 1.0000 | HIT |
| clarity_readability_formatting | 4.0000 | 4.0000 | 0.0000 | MISS |

Interpretation: Removed key details such as The patient denied a spinning sensation and distinguished this from prior ver.... Replaced specifics with broader wording (Replaced position-related lightheadedness with "recurrent vertigo."). Additional change: Added "there has been no meaningful worsening," which conflicts with the source. Observed score drops were partially consistent with the intended degradation. The largest observed decreases were in Recent Changes Highlighted, Usefulness for Decision-Making, Timeline and Evolution. The bad summary received a lower overall score than the matched good summary. Expected decreases were missed for Factual Accuracy, Clarity, Readability, and Formatting.

### Source ID 37
- Badness type: `Contradiction + omission-heavy + false reassurance`
- Expected low-scoring dimensions: `factual_accuracy, recent_changes_highlighted, usefulness_for_decision_making, relevant_chronic_problem_coverage, clarity_readability_formatting`
- Degradation note: Removed key details such as Sepsis from nephrolithiasis; Left ureteral stent placement. Replaced specifics with broader wording (Replaced a complicated, unsafe post-discharge course with the generic phrase...). Additional change: Added "no major concerns today," which is unsupported by the source.
- Good overall_across_roles: `2.8567`
- Bad overall_across_roles: `3.5300`
- Delta overall (good - bad): `-0.6733`
- Good flagged dimensions: `factual_accuracy`
- Bad flagged dimensions: `factual_accuracy, usefulness_for_decision_making`
- Hit rate: `0.0000`

| Dimension | Good Mean | Bad Mean | Delta | Result |
| --- | --- | --- | --- | --- |
| factual_accuracy | 3.6667 | 4.6667 | -1.0000 | MISS |
| recent_changes_highlighted | 2.0000 | 3.0000 | -1.0000 | MISS |
| usefulness_for_decision_making | 3.0000 | 3.3333 | -0.3333 | MISS |
| relevant_chronic_problem_coverage | 3.0000 | 3.0000 | 0.0000 | MISS |
| clarity_readability_formatting | 3.0000 | 4.0000 | -1.0000 | MISS |

Interpretation: Removed key details such as Sepsis from nephrolithiasis; Left ureteral stent placement. Replaced specifics with broader wording (Replaced a complicated, unsafe post-discharge course with the generic phrase...). Additional change: Added "no major concerns today," which is unsupported by the source. Observed score drops showed weak alignment with the intended degradation. The bad summary unexpectedly received a higher overall score than the matched good summary. Expected decreases were missed for Factual Accuracy, Recent Changes Highlighted, Usefulness for Decision-Making, Relevant Chronic Problem Coverage, Clarity, Readability, and Formatting.

### Source ID 43
- Badness type: `Contradiction + exaggeration + omission-heavy`
- Expected low-scoring dimensions: `factual_accuracy, recent_changes_highlighted, usefulness_for_decision_making, focused_not_cluttered, clarity_readability_formatting`
- Degradation note: Removed key details such as Prior similar sting reactions were localized swelling; The reason he came in.... Replaced specifics with broader wording (Replaced localized swelling with "generalized symptoms."). Additional change: Added prior anaphylaxis, throat tightness, and shortness of breath, all of wh....
- Good overall_across_roles: `3.4367`
- Bad overall_across_roles: `3.5600`
- Delta overall (good - bad): `-0.1233`
- Good flagged dimensions: `none`
- Bad flagged dimensions: `factual_accuracy, recent_changes_highlighted, relevant_chronic_problem_coverage, timeline_evolution, usefulness_for_decision_making`
- Hit rate: `0.2000`

| Dimension | Good Mean | Bad Mean | Delta | Result |
| --- | --- | --- | --- | --- |
| factual_accuracy | 5.0000 | 4.6667 | 0.3333 | HIT |
| recent_changes_highlighted | 2.0000 | 2.3333 | -0.3333 | MISS |
| usefulness_for_decision_making | 3.0000 | 3.6667 | -0.6667 | MISS |
| focused_not_cluttered | 4.0000 | 4.0000 | 0.0000 | MISS |
| clarity_readability_formatting | 4.0000 | 4.0000 | 0.0000 | MISS |

Interpretation: Removed key details such as Prior similar sting reactions were localized swelling; The reason he came in.... Replaced specifics with broader wording (Replaced localized swelling with "generalized symptoms."). Additional change: Added prior anaphylaxis, throat tightness, and shortness of breath, all of wh.... Observed score drops showed weak alignment with the intended degradation. The largest observed decreases were in Timeline and Evolution, Factual Accuracy. The bad summary unexpectedly received a higher overall score than the matched good summary. Expected decreases were missed for Recent Changes Highlighted, Usefulness for Decision-Making, Focused and Not Cluttered, Clarity, Readability, and Formatting.

### Source ID 53
- Badness type: `Contradiction + omission-heavy + noise insertion`
- Expected low-scoring dimensions: `factual_accuracy, relevant_chronic_problem_coverage, timeline_evolution, usefulness_for_decision_making, clarity_readability_formatting`
- Degradation note: Removed key details such as Left otalgia and headache as the presenting issue; Three-week symptom duration. Replaced specifics with broader wording (Replaced unilateral ear pain with "bilateral ear pain."). Additional change: Added fever, sore throat, and cough, which are explicitly denied in the source.
- Good overall_across_roles: `3.3700`
- Bad overall_across_roles: `3.4267`
- Delta overall (good - bad): `-0.0567`
- Good flagged dimensions: `factual_accuracy, focused_not_cluttered`
- Bad flagged dimensions: `factual_accuracy, relevant_chronic_problem_coverage, usefulness_for_decision_making`
- Hit rate: `0.2000`

| Dimension | Good Mean | Bad Mean | Delta | Result |
| --- | --- | --- | --- | --- |
| factual_accuracy | 4.6667 | 4.6667 | 0.0000 | MISS |
| relevant_chronic_problem_coverage | 4.0000 | 3.6667 | 0.3333 | HIT |
| timeline_evolution | 3.0000 | 3.0000 | 0.0000 | MISS |
| usefulness_for_decision_making | 3.0000 | 3.3333 | -0.3333 | MISS |
| clarity_readability_formatting | 4.0000 | 4.0000 | 0.0000 | MISS |

Interpretation: Removed key details such as Left otalgia and headache as the presenting issue; Three-week symptom duration. Replaced specifics with broader wording (Replaced unilateral ear pain with "bilateral ear pain."). Additional change: Added fever, sore throat, and cough, which are explicitly denied in the source. Observed score drops showed weak alignment with the intended degradation. The largest observed decreases were in Relevant Chronic Problem Coverage. The bad summary unexpectedly received a higher overall score than the matched good summary. Expected decreases were missed for Factual Accuracy, Timeline and Evolution, Usefulness for Decision-Making, Clarity, Readability, and Formatting.

### Source ID 59
- Badness type: `Contradiction + omission-heavy`
- Expected low-scoring dimensions: `factual_accuracy, relevant_chronic_problem_coverage, usefulness_for_decision_making, focused_not_cluttered, clarity_readability_formatting`
- Degradation note: Removed key details such as The question of blood in the stool; Nausea and vomiting. Replaced specifics with broader wording (Replaced multiple complaints with the narrower phrase "mainly for hernia pain...). Additional change: Added "is not currently anticoagulated," which directly conflicts with the so....
- Good overall_across_roles: `3.4600`
- Bad overall_across_roles: `2.8833`
- Delta overall (good - bad): `0.5767`
- Good flagged dimensions: `clarity_readability_formatting, factual_accuracy, focused_not_cluttered, relevant_chronic_problem_coverage`
- Bad flagged dimensions: `clarity_readability_formatting, factual_accuracy, recent_changes_highlighted`
- Hit rate: `0.4000`

| Dimension | Good Mean | Bad Mean | Delta | Result |
| --- | --- | --- | --- | --- |
| factual_accuracy | 4.6667 | 3.6667 | 1.0000 | HIT |
| relevant_chronic_problem_coverage | 4.3333 | 2.0000 | 2.3333 | HIT |
| usefulness_for_decision_making | 3.0000 | 3.0000 | 0.0000 | MISS |
| focused_not_cluttered | 3.6667 | 4.0000 | -0.3333 | MISS |
| clarity_readability_formatting | 3.3333 | 3.6667 | -0.3333 | MISS |

Interpretation: Removed key details such as The question of blood in the stool; Nausea and vomiting. Replaced specifics with broader wording (Replaced multiple complaints with the narrower phrase "mainly for hernia pain...). Additional change: Added "is not currently anticoagulated," which directly conflicts with the so.... Observed score drops were partially consistent with the intended degradation. The largest observed decreases were in Relevant Chronic Problem Coverage, Factual Accuracy, Organized by Condition. The bad summary received a lower overall score than the matched good summary. Expected decreases were missed for Usefulness for Decision-Making, Focused and Not Cluttered, Clarity, Readability, and Formatting.

### Source ID 62
- Badness type: `Timeline weakening + omission-heavy + under-calling severity`
- Expected low-scoring dimensions: `factual_accuracy, relevant_chronic_problem_coverage, timeline_evolution, recent_changes_highlighted, usefulness_for_decision_making`
- Degradation note: Removed key details such as The diagnosis context of cervical spinal stenosis; The prior visit date of 06.... Replaced specifics with broader wording (Replaced "cervical spinal stenosis" with the weaker phrase "chronic neck disc...). Additional change: Added "symptoms seem fairly stable overall," which downplays ongoing worsenin....
- Good overall_across_roles: `3.4767`
- Bad overall_across_roles: `3.3700`
- Delta overall (good - bad): `0.1067`
- Good flagged dimensions: `clarity_readability_formatting, factual_accuracy, focused_not_cluttered, timeline_evolution`
- Bad flagged dimensions: `factual_accuracy, focused_not_cluttered`
- Hit rate: `0.4000`

| Dimension | Good Mean | Bad Mean | Delta | Result |
| --- | --- | --- | --- | --- |
| factual_accuracy | 4.6667 | 4.6667 | 0.0000 | MISS |
| relevant_chronic_problem_coverage | 4.0000 | 4.0000 | 0.0000 | MISS |
| timeline_evolution | 3.3333 | 3.0000 | 0.3333 | HIT |
| recent_changes_highlighted | 3.0000 | 2.0000 | 1.0000 | HIT |
| usefulness_for_decision_making | 3.0000 | 3.0000 | 0.0000 | MISS |

Interpretation: Removed key details such as The diagnosis context of cervical spinal stenosis; The prior visit date of 06.... Replaced specifics with broader wording (Replaced "cervical spinal stenosis" with the weaker phrase "chronic neck disc...). Additional change: Added "symptoms seem fairly stable overall," which downplays ongoing worsenin.... Observed score drops were partially consistent with the intended degradation. The largest observed decreases were in Recent Changes Highlighted, Timeline and Evolution. The bad summary received a lower overall score than the matched good summary. Expected decreases were missed for Factual Accuracy, Relevant Chronic Problem Coverage, Usefulness for Decision-Making.

### Source ID 81
- Badness type: `Vagueness + omission-heavy + loss of structural detail`
- Expected low-scoring dimensions: `relevant_chronic_problem_coverage, organized_by_condition, usefulness_for_decision_making, clarity_readability_formatting`
- Degradation note: Removed key details such as The pain had been increasing for years prior to surgical intervention; The pa.... Replaced specifics with broader wording (Replaced the detailed arthritic pattern with the generic phrase "progressive...). Additional change: Flattened a surgically rich orthopedic description into a generic degenerativ....
- Good overall_across_roles: `3.0867`
- Bad overall_across_roles: `3.4000`
- Delta overall (good - bad): `-0.3133`
- Good flagged dimensions: `relevant_chronic_problem_coverage, timeline_evolution, usefulness_for_decision_making`
- Bad flagged dimensions: `factual_accuracy, focused_not_cluttered, relevant_chronic_problem_coverage`
- Hit rate: `0.2500`

| Dimension | Good Mean | Bad Mean | Delta | Result |
| --- | --- | --- | --- | --- |
| relevant_chronic_problem_coverage | 3.6667 | 4.3333 | -0.6667 | MISS |
| organized_by_condition | 2.0000 | 3.0000 | -1.0000 | MISS |
| usefulness_for_decision_making | 3.3333 | 3.0000 | 0.3333 | HIT |
| clarity_readability_formatting | 3.0000 | 4.0000 | -1.0000 | MISS |

Interpretation: Removed key details such as The pain had been increasing for years prior to surgical intervention; The pa.... Replaced specifics with broader wording (Replaced the detailed arthritic pattern with the generic phrase "progressive...). Additional change: Flattened a surgically rich orthopedic description into a generic degenerativ.... Observed score drops showed weak alignment with the intended degradation. The largest observed decreases were in Timeline and Evolution, Usefulness for Decision-Making. The bad summary unexpectedly received a higher overall score than the matched good summary. Expected decreases were missed for Relevant Chronic Problem Coverage, Organized by Condition, Clarity, Readability, and Formatting.

## 3. Aggregate Summary
- Average overall delta across audited pairs: `0.0064`
- Overall hit rate across all expected dimensions: `0.3200` (16/50)
- Average flagged dimensions per good summary: `2.6000`
- Average flagged dimensions per bad summary: `3.0000`

Dimensions most consistently lower in bad summaries (count of pairs with good > bad):

| Dimension | Drop Count |
| --- | --- |
| timeline_evolution | 7 |
| recent_changes_highlighted | 5 |
| relevant_chronic_problem_coverage | 3 |
| usefulness_for_decision_making | 3 |
| factual_accuracy | 2 |
| organized_by_condition | 1 |

Expected-dimension performance:

| Dimension | Expected Count | Hit Count | Miss Count | Hit Rate |
| --- | --- | --- | --- | --- |
| factual_accuracy | 8 | 2 | 6 | 0.2500 |
| relevant_chronic_problem_coverage | 8 | 3 | 5 | 0.3750 |
| organized_by_condition | 2 | 0 | 2 | 0.0000 |
| timeline_evolution | 6 | 4 | 2 | 0.6667 |
| recent_changes_highlighted | 6 | 4 | 2 | 0.6667 |
| focused_not_cluttered | 2 | 0 | 2 | 0.0000 |
| usefulness_for_decision_making | 10 | 3 | 7 | 0.3000 |
| clarity_readability_formatting | 8 | 0 | 8 | 0.0000 |

## 4. Final Conclusion
Phase 1 results showed partial alignment with the intended degradations. The pipeline demonstrated some sensitivity, but the signal was inconsistent and overall score separation remained weak.
The strongest evidence of sensitivity was in Timeline and Evolution, Recent Changes Highlighted, Relevant Chronic Problem Coverage.
The weakest areas were Organized by Condition, Clarity, Readability, and Formatting, Focused and Not Cluttered, which frequently failed to drop even when they were expected to.
