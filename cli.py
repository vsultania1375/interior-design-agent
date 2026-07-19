from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env")
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from interior_agent.agent import InteriorDesignAgent  # noqa: E402
from interior_agent.config import ConfigurationError, Settings  # noqa: E402
from interior_agent.db import CatalogRepository  # noqa: E402
from interior_agent.tools import AgentTools  # noqa: E402
from interior_agent.validator import PlanValidator  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one catalog-grounded interior design brief.")
    parser.add_argument("brief_id", nargs="?", default="BR-01")
    parser.add_argument("--list-briefs", action="store_true", help="List available database briefs and exit.")
    parser.add_argument("--model", help="Override ANTHROPIC_MODEL for this run.")
    parser.add_argument("--max-iterations", type=int, help="Override MAX_AGENT_ITERATIONS for this run.")
    parser.add_argument("--output", type=Path, help="Write the validated result JSON to a file.")
    parser.add_argument("--json", action="store_true", help="Print only machine-readable JSON.")
    args = parser.parse_args()

    try:
        settings = Settings.from_env(PROJECT_ROOT)
    except ConfigurationError as exc:
        parser.error(str(exc))
    if args.model:
        settings = Settings(settings.db_path, settings.anthropic_api_key, args.model, settings.max_iterations)
    if args.max_iterations:
        settings = Settings(settings.db_path, settings.anthropic_api_key, settings.anthropic_model, max(1, min(args.max_iterations, 30)))
    repo = CatalogRepository(settings.db_path)
    if args.list_briefs:
        for brief in repo.list_briefs():
            print(f"{brief['brief_id']}\t{brief['room_type']}\tINR {brief['budget_inr']:,}\t{brief['must_haves']}")
        return 0
    if not settings.anthropic_api_key:
        parser.error("ANTHROPIC_API_KEY is missing. Copy .env.example to .env and add it.")
    brief = repo.get_brief(args.brief_id)
    if not brief:
        parser.error(f"Unknown brief_id: {args.brief_id}")

    agent = InteriorDesignAgent(
        tools=AgentTools(repo),
        validator=PlanValidator(repo),
        api_key=settings.anthropic_api_key,
        model=settings.anthropic_model,
        max_iterations=settings.max_iterations,
    )
    trace_lines: list[str] = []
    result = agent.run(brief, on_trace=lambda entry: trace_lines.append(f"[{entry.iteration}] {entry.tool}: ok={entry.result.get('ok', entry.result.get('fits', 'n/a'))}"))
    payload = {
        "model": settings.anthropic_model,
        "converged": result.converged,
        "iterations": result.iterations,
        "trace_summary": trace_lines,
        "validated": result.validated.model_dump(mode="json"),
    }
    output = json.dumps(payload if args.json else result.validated.model_dump(mode="json"), indent=2, ensure_ascii=False)
    if args.output:
        args.output.write_text(output, encoding="utf-8")
    print(output if args.json else "\n".join([*trace_lines, output]))
    return 0 if result.validated.is_valid else 2


if __name__ == "__main__":
    raise SystemExit(main())
