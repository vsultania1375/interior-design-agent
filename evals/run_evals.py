from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "evals"))
load_dotenv(PROJECT_ROOT / ".env")

from interior_agent.agent import InteriorDesignAgent  # noqa: E402
from interior_agent.config import Settings  # noqa: E402
from interior_agent.db import CatalogRepository  # noqa: E402
from interior_agent.tools import AgentTools  # noqa: E402
from interior_agent.validator import PlanValidator  # noqa: E402
from scorers import deterministic_scores  # noqa: E402
from judge import score_with_anthropic  # noqa: E402
from offline_fixtures import make_fixture_result  # noqa: E402
from ship_gate import aggregate_ship_gate  # noqa: E402


def load_cases(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)["cases"]


def resolve_brief(case: dict[str, Any], repo: CatalogRepository) -> dict[str, Any]:
    if case["source"] == "database":
        brief = repo.get_brief(case["brief_id"])
        if not brief:
            raise KeyError(f"Missing database brief: {case['brief_id']}")
        return brief
    brief = dict(case["brief"])
    brief["brief_id"] = case["id"]
    return brief


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Evaluation Results",
        "",
        report.get("run_label", ""),
        "",
        f"Generated: {report['generated_at']}",
        f"Configured agent model: `{report['model']}`",
        f"Configured judge model: `{report['judge_model']}`",
        f"Cases: {report['case_count']}",
        f"Judge: {report['judge_note']}",
        "",
        "## Ship-gate summary",
        "",
        "| Metric | Status | Numerator | Denominator | Rate | Threshold |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for metric, row in report["ship_gate"]["metrics"].items():
        status = "NOT EVALUATED" if row["not_evaluated"] else ("PASS" if row["passed"] else "FAIL")
        lines.append(f"| {metric} | {status} | {row['numerator']} | {row['denominator']} | {row['rate']:.1%} | {row['threshold']:.0%} |")
    lines.append(f"\nOverall ship gate: {'PASS' if report['ship_gate']['overall_passed'] else 'FAIL'}")
    lines.extend(["", "## Case results", ""])
    for case in report["cases"]:
        lines.append(f"### {case['id']} — {'PASS' if case['passed'] else 'FAIL'}")
        lines.append(f"Tags: {', '.join(case['tags'])}")
        lines.append("")
        for score in case["scores"]:
            lines.append(f"- {'PASS' if score['passed'] else 'FAIL'} `{score['name']}`: {score['detail']} Value: `{score['value']}`")
        if case.get("judge"):
            judge = case["judge"]
            lines.append(f"- {'PASS' if judge['overall'] >= 4 else 'FAIL'} `judge_overall`: {judge['overall']}/5 — {judge['rationale']}")
        if case["issues"]:
            lines.append("- Validator issues: " + "; ".join(f"{issue['severity']}:{issue['code']}" for issue in case["issues"]))
        if case.get("failure_diagnosis"):
            lines.append(f"- Diagnosis: {case['failure_diagnosis']}")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", action="append", dest="case_ids", help="Run only selected case id(s).")
    parser.add_argument("--output-dir", default="eval_results")
    parser.add_argument("--skip-judge", action="store_true", help="Skip the rubric-based LLM judgement scorer.")
    parser.add_argument("--judge-model", default=None, help="Optional model override for the judgement scorer.")
    parser.add_argument("--offline-fixtures", action="store_true", help="Run scripted no-key fixtures through the eval harness. Not live model results.")
    args = parser.parse_args()

    settings = Settings.from_env(PROJECT_ROOT)
    if not args.offline_fixtures and not settings.anthropic_api_key:
        parser.error("ANTHROPIC_API_KEY is required for live eval runs.")

    repo = CatalogRepository(settings.db_path)
    tools = AgentTools(repo)
    validator = PlanValidator(repo)
    agent = None
    if not args.offline_fixtures:
        agent = InteriorDesignAgent(
            tools=tools,
            validator=validator,
            api_key=settings.anthropic_api_key or "",
            model=settings.anthropic_model,
            max_iterations=settings.max_iterations,
        )
    cases = load_cases(PROJECT_ROOT / "evals" / "golden_set.yaml")
    if args.case_ids:
        wanted = set(args.case_ids)
        cases = [case for case in cases if case["id"] in wanted]

    output_cases = []
    metric_totals: dict[str, dict[str, int]] = {}
    for index, case in enumerate(cases, start=1):
        print(f"[{index}/{len(cases)}] {case['id']}")
        brief = resolve_brief(case, repo)
        try:
            result = make_fixture_result(case["id"], brief, tools, validator) if args.offline_fixtures else agent.run(brief)  # type: ignore[union-attr]
            scores = deterministic_scores(result, brief, case)
            judge = None
            if not args.skip_judge and not args.offline_fixtures:
                judge = score_with_anthropic(
                    api_key=settings.anthropic_api_key,
                    model=args.judge_model or settings.anthropic_model,
                    brief=brief,
                    validated_plan=result.validated.model_dump(mode="json"),
                )
            passed = all(score.passed for score in scores) and (judge is None or judge.passed)
            for score in scores:
                bucket = metric_totals.setdefault(score.name, {"passed": 0, "total": 0})
                bucket["total"] += 1
                bucket["passed"] += int(score.passed)
            if judge is not None:
                bucket = metric_totals.setdefault("judge_overall_4_plus", {"passed": 0, "total": 0})
                bucket["total"] += 1
                bucket["passed"] += int(judge.passed)
            output_cases.append({
                "id": case["id"],
                "tags": case.get("tags", []),
                "passed": passed,
                "scores": [score.__dict__ for score in scores],
                "judge": None if judge is None else judge.__dict__,
                "issues": [issue.model_dump() for issue in result.validated.issues],
                "trace_length": len(result.trace),
                "iterations": result.iterations,
                "converged": result.converged,
                "failure_diagnosis": "" if passed else "; ".join(score.name for score in scores if not score.passed)[:500],
            })
        except Exception as exc:
            output_cases.append({
                "id": case["id"],
                "tags": case.get("tags", []),
                "passed": False,
                "scores": [],
                "judge": None,
                "issues": [{"severity": "error", "code": "runner_error", "message": str(exc)}],
                "trace_length": 0,
                "iterations": 0,
                "converged": False,
                "failure_diagnosis": str(exc)[:500],
            })

    summary = {
        name: {**counts, "rate": counts["passed"] / counts["total"] if counts["total"] else 0.0}
        for name, counts in metric_totals.items()
    }
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_label": "OFFLINE FIXTURE RUN — NOT LIVE MODEL RESULTS" if args.offline_fixtures else "LIVE MODEL EVALUATION",
        "model": settings.anthropic_model,
        "judge_model": args.judge_model or settings.anthropic_model,
        "judge_note": "NOT EVALUATED" if (args.skip_judge or args.offline_fixtures) else "evaluated with configured judge model",
        "case_count": len(output_cases),
        "summary": summary,
        "ship_gate": aggregate_ship_gate(output_cases, judge_skipped=(args.skip_judge or args.offline_fixtures)),
        "cases": output_cases,
    }

    out_dir = PROJECT_ROOT / ("eval_results/offline" if args.offline_fixtures and args.output_dir == "eval_results" else args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "results.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    (out_dir / "results.md").write_text(render_markdown(report), encoding="utf-8")
    print(f"Wrote {out_dir / 'results.json'} and {out_dir / 'results.md'}")
    if args.offline_fixtures:
        return 0
    return 0 if all(case["passed"] for case in output_cases) else 2


if __name__ == "__main__":
    raise SystemExit(main())
