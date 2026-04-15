# Phase 1 Comparison Summary

| Run | Description | Good Mean | Bad Mean | Overall Delta | Good > Bad Pairs | Mean Hit Rate | Weighted Hit Rate | Physician Delta | Triage Delta | Bedside Delta |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | Original Phase 1 run | 3.3630 | 3.3567 | 0.0064 | 4/10 | 0.3150 | 0.3200 | 0.1470 | -0.0980 | -0.0300 |
| brevity_fix | After anti-brevity-bias rubric/prompt refinement | 3.5157 | 3.2850 | 0.2307 | 7/10 | 0.4400 | 0.4600 | 0.2730 | 0.2320 | 0.1870 |
| persona_refinement | After role-profile refinement and synthetic-prior seeding | 3.6490 | 3.3053 | 0.3437 | 8/10 | 0.5883 | 0.6000 | 0.4400 | 0.3530 | 0.2380 |
