import argparse
import asyncio
import json
from pathlib import Path
from typing import List

from .config import load_roles, load_rubric
from .scoring import AgentScore, score_summary_heuristic
from .llm_scoring import score_summary_llm


DEFAULT_SUMMARY = (
    "PMH: diabetes, hypertension, CKD. Recent: admitted last week for CHF "
    "exacerbation, discharged 2 days ago. Today presents with SOB x 2 days, "
    "worsened overnight. Meds: lisinopril, metformin, furosemide. Allergies: "
    "NKDA. Vitals: BP 150/90, HR 105, SpO2 92% RA. Labs pending, CT chest ordered."
)


def _load_summary(args: argparse.Namespace) -> str:
    if args.summary:
        return args.summary
    if args.summary_file:
        return Path(args.summary_file).read_text().strip()
    return DEFAULT_SUMMARY


async def _run_agents(summary: str, roles, rubric, engine: str, model: str, temperature: float) -> List[AgentScore]:
    if engine == "llm":
        tasks = [asyncio.to_thread(score_summary_llm, summary, role, rubric, model=model, temperature=temperature) for role in roles]
    else:
        tasks = [asyncio.to_thread(score_summary_heuristic, summary, role, rubric) for role in roles]
    return await asyncio.gather(*tasks)


def _print_human(agents: List[AgentScore], roles, rubric) -> None:
    role_map = {role.id: role.name for role in roles}
    for agent in agents:
        title = role_map.get(agent.role_id, agent.role_id)
        print(f"{title}:")
        for dim in rubric.dimensions:
            score = agent.scores.get(dim.id, "NA")
            print(f"{dim.name}: {score}")
        if agent.overall_score is not None:
            print(f"Overall: {agent.overall_score}")
        print("")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Role-aware multi-agent grading pipeline (heuristic scaffold)."
    )
    parser.add_argument("--summary", type=str, help="Summary text to score.")
    parser.add_argument(
        "--summary-file", type=str, help="Path to a file containing the summary."
    )
    parser.add_argument(
        "--rubric",
        type=str,
        default=str(Path("config/lens_rubric.json")),
        help="Path to rubric JSON.",
    )
    parser.add_argument(
        "--roles",
        type=str,
        default=str(Path("config/roles.json")),
        help="Path to roles JSON.",
    )
    parser.add_argument("--engine", choices=["llm", "heuristic"], default="llm", help="Scoring engine to use.")
    parser.add_argument("--model", type=str, default="gpt-4o", help="OpenAI model for LLM scoring.")
    parser.add_argument("--temperature", type=float, default=0.2, help="LLM sampling temperature.")
    parser.add_argument("--format", choices=["human", "json"], default="human", help="Output format.")
    parser.add_argument("--pretty", action="store_true", help="Pretty JSON output (json format only).")
    parser.add_argument("--output", type=str, help="Write output JSON to this file.")

    args = parser.parse_args()
    summary = _load_summary(args)

    rubric = load_rubric(args.rubric)
    roles = load_roles(args.roles, rubric.dimension_ids)

    agents = asyncio.run(_run_agents(summary, roles, rubric, args.engine, args.model, args.temperature))

    if args.format == "human":
        _print_human(agents, roles, rubric)
        return 0

    payload = {
        "summary": summary,
        "rubric_id": rubric.rubric_id,
        "engine": args.engine,
        "model": args.model if args.engine == "llm" else None,
        "agents": [agent.to_dict() for agent in agents],
    }

    output = json.dumps(payload, indent=2 if args.pretty else None)
    if args.output:
        Path(args.output).write_text(output)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
