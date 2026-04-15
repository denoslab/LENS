import json
import numpy as np
import pandas as pd

SEED = 20260414
np.random.seed(SEED)

# This script reproduces the synthetic LENS bootstrap survey used for early pipeline testing.
# It is intentionally simple and easy for Codex to modify.

# Recommended usage:
# 1. Load synthetic_calgary_ed_questionnaire_100.csv
# 2. Recompute role-specific Q3 weights with Borda aggregation
# 3. Use lens_agent_seed_config.json as seed priors for role-aware agents
# 4. Replace these priors with real questionnaire results when available

df = pd.read_csv("synthetic_calgary_ed_questionnaire_100.csv")

dimension_cols = [
    "q3_rank__factual_accuracy",
    "q3_rank__relevant_chronic_problem_coverage",
    "q3_rank__organized_by_condition",
    "q3_rank__timeline_evolution",
    "q3_rank__recent_changes_highlighted",
    "q3_rank__focused_not_cluttered",
    "q3_rank__usefulness_for_decision_making",
    "q3_rank__clarity_readability_formatting",
]

def borda_weights(subdf: pd.DataFrame) -> dict:
    points = {}
    for col in dimension_cols:
        points[col] = float((9 - subdf[col]).mean())  # rank 1 -> 8 points
    total = sum(points.values())
    return {k: v / total for k, v in points.items()}

print("Overall weights:")
print(json.dumps(borda_weights(df), indent=2))

print("\nPer-role weights:")
for role_id, subdf in df.groupby("q1_role_id"):
    print(f"\n{role_id}")
    print(json.dumps(borda_weights(subdf), indent=2))
