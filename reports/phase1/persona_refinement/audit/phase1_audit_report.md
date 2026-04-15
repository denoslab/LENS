# Phase 1 Audit Report

## 1. Overview
- Result folder used: `/Users/samuel/Documents/LENS Project/reports/phase1/persona_refinement/run`
- Selection note: Assumption: result folder was provided explicitly by the user.
- Bad annotation file: `/Users/samuel/Documents/LENS Project/data/phase1/raw/lens_bad_samples_complete_english.txt`
- Good output directory: `/Users/samuel/Documents/LENS Project/reports/phase1/persona_refinement/run/outputs/good`
- Bad output directory: `/Users/samuel/Documents/LENS Project/reports/phase1/persona_refinement/run/outputs/bad`
- Good/bad pairs successfully audited: `10`
- Missing or failed pairs: `0`

## 2. Per-sample Audit

### Source ID 0
- Badness type: `Timeline distortion + omission-heavy`
- Expected low-scoring dimensions: `factual_accuracy, relevant_chronic_problem_coverage, timeline_evolution, recent_changes_highlighted, usefulness_for_decision_making`
- Degradation note: Removed key details such as The original traumatic low back injury occurred eight years earlier; Continuo.... Replaced specifics with broader wording (Replaced a long chronic pain history with "occasional back discomfort in the...). Additional change: Added "was functioning well until this new event," which is inconsistent with....
- Good overall_across_roles: `3.9800`
- Bad overall_across_roles: `3.3533`
- Delta overall (good - bad): `0.6267`
- Good flagged dimensions: `factual_accuracy, focused_not_cluttered, usefulness_for_decision_making`
- Bad flagged dimensions: `focused_not_cluttered`
- Hit rate: `1.0000`

| Dimension | Good Mean | Bad Mean | Delta | Result |
| --- | --- | --- | --- | --- |
| factual_accuracy | 4.6667 | 4.0000 | 0.6667 | HIT |
| relevant_chronic_problem_coverage | 4.0000 | 3.0000 | 1.0000 | HIT |
| timeline_evolution | 4.0000 | 3.0000 | 1.0000 | HIT |
| recent_changes_highlighted | 4.0000 | 3.0000 | 1.0000 | HIT |
| usefulness_for_decision_making | 3.6667 | 3.0000 | 0.6667 | HIT |

Interpretation: Removed key details such as The original traumatic low back injury occurred eight years earlier; Continuo.... Replaced specifics with broader wording (Replaced a long chronic pain history with "occasional back discomfort in the...). Additional change: Added "was functioning well until this new event," which is inconsistent with.... Observed score drops were broadly consistent with the intended degradation. The largest observed decreases were in Relevant Chronic Problem Coverage, Timeline and Evolution, Recent Changes Highlighted. The bad summary received a lower overall score than the matched good summary.

### Source ID 9
- Badness type: `Under-specification + omission-heavy + poor organization`
- Expected low-scoring dimensions: `relevant_chronic_problem_coverage, organized_by_condition, timeline_evolution, usefulness_for_decision_making, clarity_readability_formatting`
- Degradation note: Removed key details such as Recurrent bunion deformity in both feet, right greater than left; Pain specif.... Replaced specifics with broader wording (Replaced "recurrent bunion deformity in bilateral feet" with the less precise...). Additional change: Added "without much additional complexity," which downplays the structural re....
- Good overall_across_roles: `3.7867`
- Bad overall_across_roles: `3.4000`
- Delta overall (good - bad): `0.3867`
- Good flagged dimensions: `factual_accuracy, recent_changes_highlighted, timeline_evolution, usefulness_for_decision_making`
- Bad flagged dimensions: `factual_accuracy, focused_not_cluttered`
- Hit rate: `0.4000`

| Dimension | Good Mean | Bad Mean | Delta | Result |
| --- | --- | --- | --- | --- |
| relevant_chronic_problem_coverage | 4.0000 | 4.0000 | 0.0000 | MISS |
| organized_by_condition | 3.0000 | 3.0000 | 0.0000 | MISS |
| timeline_evolution | 3.6667 | 3.0000 | 0.6667 | HIT |
| usefulness_for_decision_making | 3.6667 | 3.0000 | 0.6667 | HIT |
| clarity_readability_formatting | 4.0000 | 4.0000 | 0.0000 | MISS |

Interpretation: Removed key details such as Recurrent bunion deformity in both feet, right greater than left; Pain specif.... Replaced specifics with broader wording (Replaced "recurrent bunion deformity in bilateral feet" with the less precise...). Additional change: Added "without much additional complexity," which downplays the structural re.... Observed score drops were partially consistent with the intended degradation. The largest observed decreases were in Timeline and Evolution, Recent Changes Highlighted, Usefulness for Decision-Making. The bad summary received a lower overall score than the matched good summary. Expected decreases were missed for Relevant Chronic Problem Coverage, Organized by Condition, Clarity, Readability, and Formatting.

### Source ID 14
- Badness type: `Omission-heavy + contradiction + vagueness`
- Expected low-scoring dimensions: `factual_accuracy, relevant_chronic_problem_coverage, timeline_evolution, recent_changes_highlighted, usefulness_for_decision_making, clarity_readability_formatting`
- Degradation note: Removed key details such as Hypertension; Prior stroke in 2002 with minimal residual right-sided weakness. Replaced specifics with broader wording (Replaced the detailed neurologic history with the vague phrase "discomfort in...). Additional change: Added "otherwise relatively stable," which is not supported by the source.
- Good overall_across_roles: `3.9933`
- Bad overall_across_roles: `3.1900`
- Delta overall (good - bad): `0.8033`
- Good flagged dimensions: `factual_accuracy, organized_by_condition, relevant_chronic_problem_coverage`
- Bad flagged dimensions: `none`
- Hit rate: `0.8333`

| Dimension | Good Mean | Bad Mean | Delta | Result |
| --- | --- | --- | --- | --- |
| factual_accuracy | 4.6667 | 4.0000 | 0.6667 | HIT |
| relevant_chronic_problem_coverage | 4.6667 | 4.0000 | 0.6667 | HIT |
| timeline_evolution | 4.0000 | 2.0000 | 2.0000 | HIT |
| recent_changes_highlighted | 3.0000 | 2.0000 | 1.0000 | HIT |
| usefulness_for_decision_making | 4.0000 | 3.0000 | 1.0000 | HIT |
| clarity_readability_formatting | 4.0000 | 4.0000 | 0.0000 | MISS |

Interpretation: Removed key details such as Hypertension; Prior stroke in 2002 with minimal residual right-sided weakness. Replaced specifics with broader wording (Replaced the detailed neurologic history with the vague phrase "discomfort in...). Additional change: Added "otherwise relatively stable," which is not supported by the source. Observed score drops were broadly consistent with the intended degradation. The largest observed decreases were in Timeline and Evolution, Recent Changes Highlighted, Focused and Not Cluttered. The bad summary received a lower overall score than the matched good summary. Expected decreases were missed for Clarity, Readability, and Formatting.

### Source ID 18
- Badness type: `Direct contradiction + medication-link removal`
- Expected low-scoring dimensions: `factual_accuracy, timeline_evolution, recent_changes_highlighted, usefulness_for_decision_making, clarity_readability_formatting`
- Degradation note: Removed key details such as The patient denied a spinning sensation and distinguished this from prior ver.... Replaced specifics with broader wording (Replaced position-related lightheadedness with "recurrent vertigo."). Additional change: Added "there has been no meaningful worsening," which conflicts with the source.
- Good overall_across_roles: `3.7933`
- Bad overall_across_roles: `3.1467`
- Delta overall (good - bad): `0.6466`
- Good flagged dimensions: `factual_accuracy, focused_not_cluttered, timeline_evolution, usefulness_for_decision_making`
- Bad flagged dimensions: `factual_accuracy`
- Hit rate: `0.8000`

| Dimension | Good Mean | Bad Mean | Delta | Result |
| --- | --- | --- | --- | --- |
| factual_accuracy | 4.6667 | 4.0000 | 0.6667 | HIT |
| timeline_evolution | 3.3333 | 3.0000 | 0.3333 | HIT |
| recent_changes_highlighted | 4.0000 | 2.0000 | 2.0000 | HIT |
| usefulness_for_decision_making | 3.6667 | 3.0000 | 0.6667 | HIT |
| clarity_readability_formatting | 4.0000 | 4.0000 | 0.0000 | MISS |

Interpretation: Removed key details such as The patient denied a spinning sensation and distinguished this from prior ver.... Replaced specifics with broader wording (Replaced position-related lightheadedness with "recurrent vertigo."). Additional change: Added "there has been no meaningful worsening," which conflicts with the source. Observed score drops were broadly consistent with the intended degradation. The largest observed decreases were in Recent Changes Highlighted, Factual Accuracy, Focused and Not Cluttered. The bad summary received a lower overall score than the matched good summary. Expected decreases were missed for Clarity, Readability, and Formatting.

### Source ID 37
- Badness type: `Contradiction + omission-heavy + false reassurance`
- Expected low-scoring dimensions: `factual_accuracy, recent_changes_highlighted, usefulness_for_decision_making, relevant_chronic_problem_coverage, clarity_readability_formatting`
- Degradation note: Removed key details such as Sepsis from nephrolithiasis; Left ureteral stent placement. Replaced specifics with broader wording (Replaced a complicated, unsafe post-discharge course with the generic phrase...). Additional change: Added "no major concerns today," which is unsupported by the source.
- Good overall_across_roles: `3.1100`
- Bad overall_across_roles: `3.4467`
- Delta overall (good - bad): `-0.3367`
- Good flagged dimensions: `clarity_readability_formatting, factual_accuracy`
- Bad flagged dimensions: `factual_accuracy, focused_not_cluttered`
- Hit rate: `0.0000`

| Dimension | Good Mean | Bad Mean | Delta | Result |
| --- | --- | --- | --- | --- |
| factual_accuracy | 3.6667 | 4.3333 | -0.6667 | MISS |
| recent_changes_highlighted | 3.0000 | 3.0000 | 0.0000 | MISS |
| usefulness_for_decision_making | 3.0000 | 3.0000 | 0.0000 | MISS |
| relevant_chronic_problem_coverage | 3.0000 | 3.0000 | 0.0000 | MISS |
| clarity_readability_formatting | 3.3333 | 4.0000 | -0.6667 | MISS |

Interpretation: Removed key details such as Sepsis from nephrolithiasis; Left ureteral stent placement. Replaced specifics with broader wording (Replaced a complicated, unsafe post-discharge course with the generic phrase...). Additional change: Added "no major concerns today," which is unsupported by the source. Observed score drops showed weak alignment with the intended degradation. The bad summary unexpectedly received a higher overall score than the matched good summary. Expected decreases were missed for Factual Accuracy, Recent Changes Highlighted, Usefulness for Decision-Making, Relevant Chronic Problem Coverage, Clarity, Readability, and Formatting.

### Source ID 43
- Badness type: `Contradiction + exaggeration + omission-heavy`
- Expected low-scoring dimensions: `factual_accuracy, recent_changes_highlighted, usefulness_for_decision_making, focused_not_cluttered, clarity_readability_formatting`
- Degradation note: Removed key details such as Prior similar sting reactions were localized swelling; The reason he came in.... Replaced specifics with broader wording (Replaced localized swelling with "generalized symptoms."). Additional change: Added prior anaphylaxis, throat tightness, and shortness of breath, all of wh....
- Good overall_across_roles: `3.8100`
- Bad overall_across_roles: `3.6100`
- Delta overall (good - bad): `0.2000`
- Good flagged dimensions: `timeline_evolution`
- Bad flagged dimensions: `factual_accuracy, recent_changes_highlighted, relevant_chronic_problem_coverage, timeline_evolution, usefulness_for_decision_making`
- Hit rate: `0.6000`

| Dimension | Good Mean | Bad Mean | Delta | Result |
| --- | --- | --- | --- | --- |
| factual_accuracy | 5.0000 | 4.6667 | 0.3333 | HIT |
| recent_changes_highlighted | 3.0000 | 2.3333 | 0.6667 | HIT |
| usefulness_for_decision_making | 4.0000 | 3.6667 | 0.3333 | HIT |
| focused_not_cluttered | 4.0000 | 4.0000 | 0.0000 | MISS |
| clarity_readability_formatting | 4.0000 | 4.0000 | 0.0000 | MISS |

Interpretation: Removed key details such as Prior similar sting reactions were localized swelling; The reason he came in.... Replaced specifics with broader wording (Replaced localized swelling with "generalized symptoms."). Additional change: Added prior anaphylaxis, throat tightness, and shortness of breath, all of wh.... Observed score drops were partially consistent with the intended degradation. The largest observed decreases were in Timeline and Evolution, Recent Changes Highlighted, Usefulness for Decision-Making. The bad summary received a lower overall score than the matched good summary. Expected decreases were missed for Focused and Not Cluttered, Clarity, Readability, and Formatting.

### Source ID 53
- Badness type: `Contradiction + omission-heavy + noise insertion`
- Expected low-scoring dimensions: `factual_accuracy, relevant_chronic_problem_coverage, timeline_evolution, usefulness_for_decision_making, clarity_readability_formatting`
- Degradation note: Removed key details such as Left otalgia and headache as the presenting issue; Three-week symptom duration. Replaced specifics with broader wording (Replaced unilateral ear pain with "bilateral ear pain."). Additional change: Added fever, sore throat, and cough, which are explicitly denied in the source.
- Good overall_across_roles: `3.3033`
- Bad overall_across_roles: `3.2400`
- Delta overall (good - bad): `0.0633`
- Good flagged dimensions: `factual_accuracy, relevant_chronic_problem_coverage`
- Bad flagged dimensions: `focused_not_cluttered, relevant_chronic_problem_coverage`
- Hit rate: `0.4000`

| Dimension | Good Mean | Bad Mean | Delta | Result |
| --- | --- | --- | --- | --- |
| factual_accuracy | 4.3333 | 4.0000 | 0.3333 | HIT |
| relevant_chronic_problem_coverage | 3.6667 | 3.3333 | 0.3333 | HIT |
| timeline_evolution | 3.0000 | 3.0000 | 0.0000 | MISS |
| usefulness_for_decision_making | 3.0000 | 3.0000 | 0.0000 | MISS |
| clarity_readability_formatting | 4.0000 | 4.0000 | 0.0000 | MISS |

Interpretation: Removed key details such as Left otalgia and headache as the presenting issue; Three-week symptom duration. Replaced specifics with broader wording (Replaced unilateral ear pain with "bilateral ear pain."). Additional change: Added fever, sore throat, and cough, which are explicitly denied in the source. Observed score drops were partially consistent with the intended degradation. The largest observed decreases were in Factual Accuracy, Relevant Chronic Problem Coverage. The bad summary received a lower overall score than the matched good summary. Expected decreases were missed for Timeline and Evolution, Usefulness for Decision-Making, Clarity, Readability, and Formatting.

### Source ID 59
- Badness type: `Contradiction + omission-heavy`
- Expected low-scoring dimensions: `factual_accuracy, relevant_chronic_problem_coverage, usefulness_for_decision_making, focused_not_cluttered, clarity_readability_formatting`
- Degradation note: Removed key details such as The question of blood in the stool; Nausea and vomiting. Replaced specifics with broader wording (Replaced multiple complaints with the narrower phrase "mainly for hernia pain...). Additional change: Added "is not currently anticoagulated," which directly conflicts with the so....
- Good overall_across_roles: `3.4733`
- Bad overall_across_roles: `2.8000`
- Delta overall (good - bad): `0.6733`
- Good flagged dimensions: `clarity_readability_formatting, focused_not_cluttered, usefulness_for_decision_making`
- Bad flagged dimensions: `clarity_readability_formatting, factual_accuracy`
- Hit rate: `1.0000`

| Dimension | Good Mean | Bad Mean | Delta | Result |
| --- | --- | --- | --- | --- |
| factual_accuracy | 4.0000 | 3.6667 | 0.3333 | HIT |
| relevant_chronic_problem_coverage | 4.0000 | 2.0000 | 2.0000 | HIT |
| usefulness_for_decision_making | 3.3333 | 3.0000 | 0.3333 | HIT |
| focused_not_cluttered | 3.3333 | 3.0000 | 0.3333 | HIT |
| clarity_readability_formatting | 3.6667 | 3.3333 | 0.3333 | HIT |

Interpretation: Removed key details such as The question of blood in the stool; Nausea and vomiting. Replaced specifics with broader wording (Replaced multiple complaints with the narrower phrase "mainly for hernia pain...). Additional change: Added "is not currently anticoagulated," which directly conflicts with the so.... Observed score drops were broadly consistent with the intended degradation. The largest observed decreases were in Relevant Chronic Problem Coverage, Timeline and Evolution, Recent Changes Highlighted. The bad summary received a lower overall score than the matched good summary.

### Source ID 62
- Badness type: `Timeline weakening + omission-heavy + under-calling severity`
- Expected low-scoring dimensions: `factual_accuracy, relevant_chronic_problem_coverage, timeline_evolution, recent_changes_highlighted, usefulness_for_decision_making`
- Degradation note: Removed key details such as The diagnosis context of cervical spinal stenosis; The prior visit date of 06.... Replaced specifics with broader wording (Replaced "cervical spinal stenosis" with the weaker phrase "chronic neck disc...). Additional change: Added "symptoms seem fairly stable overall," which downplays ongoing worsenin....
- Good overall_across_roles: `3.8967`
- Bad overall_across_roles: `3.5133`
- Delta overall (good - bad): `0.3834`
- Good flagged dimensions: `factual_accuracy`
- Bad flagged dimensions: `factual_accuracy, organized_by_condition`
- Hit rate: `0.6000`

| Dimension | Good Mean | Bad Mean | Delta | Result |
| --- | --- | --- | --- | --- |
| factual_accuracy | 4.6667 | 4.6667 | 0.0000 | MISS |
| relevant_chronic_problem_coverage | 4.0000 | 4.0000 | 0.0000 | MISS |
| timeline_evolution | 4.0000 | 3.0000 | 1.0000 | HIT |
| recent_changes_highlighted | 3.0000 | 2.0000 | 1.0000 | HIT |
| usefulness_for_decision_making | 4.0000 | 3.0000 | 1.0000 | HIT |

Interpretation: Removed key details such as The diagnosis context of cervical spinal stenosis; The prior visit date of 06.... Replaced specifics with broader wording (Replaced "cervical spinal stenosis" with the weaker phrase "chronic neck disc...). Additional change: Added "symptoms seem fairly stable overall," which downplays ongoing worsenin.... Observed score drops were partially consistent with the intended degradation. The largest observed decreases were in Timeline and Evolution, Recent Changes Highlighted, Usefulness for Decision-Making. The bad summary received a lower overall score than the matched good summary. Expected decreases were missed for Factual Accuracy, Relevant Chronic Problem Coverage.

### Source ID 81
- Badness type: `Vagueness + omission-heavy + loss of structural detail`
- Expected low-scoring dimensions: `relevant_chronic_problem_coverage, organized_by_condition, usefulness_for_decision_making, clarity_readability_formatting`
- Degradation note: Removed key details such as The pain had been increasing for years prior to surgical intervention; The pa.... Replaced specifics with broader wording (Replaced the detailed arthritic pattern with the generic phrase "progressive...). Additional change: Flattened a surgically rich orthopedic description into a generic degenerativ....
- Good overall_across_roles: `3.3433`
- Bad overall_across_roles: `3.3533`
- Delta overall (good - bad): `-0.0100`
- Good flagged dimensions: `clarity_readability_formatting, factual_accuracy, focused_not_cluttered, recent_changes_highlighted, relevant_chronic_problem_coverage, usefulness_for_decision_making`
- Bad flagged dimensions: `focused_not_cluttered, recent_changes_highlighted, timeline_evolution`
- Hit rate: `0.2500`

| Dimension | Good Mean | Bad Mean | Delta | Result |
| --- | --- | --- | --- | --- |
| relevant_chronic_problem_coverage | 3.6667 | 4.0000 | -0.3333 | MISS |
| organized_by_condition | 3.0000 | 3.0000 | 0.0000 | MISS |
| usefulness_for_decision_making | 3.3333 | 3.0000 | 0.3333 | HIT |
| clarity_readability_formatting | 3.3333 | 4.0000 | -0.6667 | MISS |

Interpretation: Removed key details such as The pain had been increasing for years prior to surgical intervention; The pa.... Replaced specifics with broader wording (Replaced the detailed arthritic pattern with the generic phrase "progressive...). Additional change: Flattened a surgically rich orthopedic description into a generic degenerativ.... Observed score drops showed weak alignment with the intended degradation. The largest observed decreases were in Timeline and Evolution, Usefulness for Decision-Making, Factual Accuracy. The bad summary unexpectedly received a higher overall score than the matched good summary. Expected decreases were missed for Relevant Chronic Problem Coverage, Organized by Condition, Clarity, Readability, and Formatting.

## 3. Aggregate Summary
- Average overall delta across audited pairs: `0.3437`
- Overall hit rate across all expected dimensions: `0.6000` (30/50)
- Average flagged dimensions per good summary: `2.9000`
- Average flagged dimensions per bad summary: `2.0000`

Dimensions most consistently lower in bad summaries (count of pairs with good > bad):

| Dimension | Drop Count |
| --- | --- |
| factual_accuracy | 8 |
| timeline_evolution | 8 |
| usefulness_for_decision_making | 8 |
| recent_changes_highlighted | 7 |
| focused_not_cluttered | 5 |
| relevant_chronic_problem_coverage | 4 |
| organized_by_condition | 1 |
| clarity_readability_formatting | 1 |

Expected-dimension performance:

| Dimension | Expected Count | Hit Count | Miss Count | Hit Rate |
| --- | --- | --- | --- | --- |
| factual_accuracy | 8 | 6 | 2 | 0.7500 |
| relevant_chronic_problem_coverage | 8 | 4 | 4 | 0.5000 |
| organized_by_condition | 2 | 0 | 2 | 0.0000 |
| timeline_evolution | 6 | 5 | 1 | 0.8333 |
| recent_changes_highlighted | 6 | 5 | 1 | 0.8333 |
| focused_not_cluttered | 2 | 1 | 1 | 0.5000 |
| usefulness_for_decision_making | 10 | 8 | 2 | 0.8000 |
| clarity_readability_formatting | 8 | 1 | 7 | 0.1250 |

## 4. Final Conclusion
Phase 1 results generally aligned with the intended degradations. The pipeline appears reasonably sensitive to bad summary quality, especially in the dimensions that were explicitly targeted.
The strongest evidence of sensitivity was in Factual Accuracy, Timeline and Evolution, Usefulness for Decision-Making.
The weakest areas were Organized by Condition, which frequently failed to drop even when they were expected to.
