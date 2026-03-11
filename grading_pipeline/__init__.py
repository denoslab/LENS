"""LENS – Role-aware multi-agent grading pipeline for clinical ED handoff summaries.

Three clinical roles (Physician, Triage Nurse, Bedside Nurse) independently score
summaries across 8 rubric dimensions, then an orchestrator detects cross-role
disagreements, optionally adjudicates via LLM, and aggregates final scores.

Supports two scoring engines:
  - ``heuristic``: keyword-based baseline (no API key needed)
  - ``llm``: OpenAI-powered scoring with structured JSON output

Entry points:
  - CLI: ``python -m grading_pipeline --summary "..." --engine heuristic``
  - Programmatic: ``from grading_pipeline.orchestrator import run_pipeline``
"""

__all__ = ["config"]
