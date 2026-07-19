from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "evals"))

from interior_agent.agent import InteriorDesignAgent  # noqa: E402
from interior_agent.config import ConfigurationError, Settings  # noqa: E402
from interior_agent.db import CatalogRepository  # noqa: E402
from interior_agent.tools import AgentTools  # noqa: E402
from interior_agent.validator import PlanValidator  # noqa: E402
from scorers import deterministic_scores  # noqa: E402
from judge import score_with_anthropic  # noqa: E402
from offline_fixtures import make_fixture_result  # noqa: E402
from ship_gate import aggregate_ship_gate  # noqa: E402


class LiveSafetyError(ValueError):
    pass


def load_cases(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)["cases"]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", action="append", dest="case_ids", help="Run only selected case id(s).")
    parser.add_argument("--all", action="store_true", help="Run the full golden set. Live mode requires --confirm-full-live.")
    parser.add_argument("--output-dir", default="eval_results")
    parser.add_argument("--skip-judge", action="store_true", help="Skip the rubric-based LLM judgement scorer.")
    parser.add_argument("--judge-model", default=None, help="Optional model override for the judgement scorer.")
    parser.add_argument("--offline-fixtures", action="store_true", help="Run scripted no-key fixtures through the eval harness. Not live model results.")
    parser.add_argument("--confirm-multi-case-live", action="store_true", help="Required for live runs with more than one explicit case.")
    parser.add_argument("--confirm-full-live", action="store_true", help="Required for any full live run.")
    parser.add_argument("--confirm-judge-cost", action="store_true", help="Required before any LLM judge calls.")
    parser.add_argument("--resume-from", type=Path, help="Resume from a prior results.json, preserving passed cases and running unfinished/failed cases.")
    parser.add_argument("--failed-only", type=Path, help="Run only failed cases from a prior results.json.")
    return parser


def _prior_case_map(path: Path | None) -> dict[str, dict[str, Any]]:
    if not path:
        return {}
    return {case["id"]: case for case in json.loads(path.read_text(encoding="utf-8")).get("cases", [])}


def select_cases(all_cases: list[dict[str, Any]], args: argparse.Namespace) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_id = {case["id"]: case for case in all_cases}
    prior = _prior_case_map(args.resume_from or args.failed_only)
    preserved: list[dict[str, Any]] = []

    if args.failed_only:
        wanted = [case_id for case_id, case in prior.items() if not case.get("passed", False)]
        return [by_id[case_id] for case_id in wanted if case_id in by_id], preserved

    if args.resume_from:
        passed_ids = {case_id for case_id, case in prior.items() if case.get("passed", False)}
        preserved = [case for case_id, case in prior.items() if case_id in passed_ids]
        return [case for case in all_cases if case["id"] not in passed_ids], preserved

    if args.case_ids:
        wanted = set(args.case_ids)
        return [case for case in all_cases if case["id"] in wanted], preserved

    if args.offline_fixtures or args.all:
        return list(all_cases), preserved

    return [], preserved


def validate_live_plan(args: argparse.Namespace, selected: list[dict[str, Any]]) -> None:
    if args.offline_fixtures:
        return
    judge_enabled = not args.skip_judge
    count = len(selected)
    if not args.case_ids and not args.resume_from and not args.failed_only and not args.all:
        raise LiveSafetyError("Refusing to run all live cases by default. Use --all --confirm-full-live, or choose explicit --case values.")
    if count == 0:
        raise LiveSafetyError("No live cases selected. Use --case <id> for one case, or --all --confirm-full-live for the full golden set.")
    if args.all and not args.confirm_full_live:
        raise LiveSafetyError("Full live eval requires --all --confirm-full-live. Add --skip-judge to avoid judge calls.")
    if count > 1 and not (args.confirm_multi_case_live or args.confirm_full_live):
        raise LiveSafetyError("Live runs with more than one case require --confirm-multi-case-live, or --all --confirm-full-live for the full set.")
    if count > 3 and not args.confirm_full_live:
        raise LiveSafetyError("Live runs are limited to 3 cases unless --confirm-full-live is supplied.")
    if judge_enabled and not args.confirm_judge_cost:
        raise LiveSafetyError("Judge execution requires --confirm-judge-cost. Use --skip-judge to avoid judge calls.")
    if args.all and judge_enabled and not (args.confirm_full_live and args.confirm_judge_cost):
        raise LiveSafetyError("Full judged run requires --all --confirm-full-live --confirm-judge-cost.")


def preflight_summary(args: argparse.Namespace, selected: list[dict[str, Any]], settings: Settings) -> str:
    return "\n".join([
        "Live eval pre-flight",
        f"mode: {'offline-fixtures' if args.offline_fixtures else 'live'}",
        f"selected_case_count: {len(selected)}",
        "case_ids: " + ", ".join(case["id"] for case in selected),
        f"judge_enabled: {not args.skip_judge and not args.offline_fixtures}",
        f"model_id: {settings.anthropic_model}",
        f"max_iterations: {settings.max_iterations}",
        f"max_output_tokens: {settings.anthropic_max_tokens}",
        f"confirm_multi_case_live: {args.confirm_multi_case_live}",
        f"confirm_full_live: {args.confirm_full_live}",
        f"confirm_judge_cost: {args.confirm_judge_cost}",
    ])


def maybe_countdown(args: argparse.Namespace, selected: list[dict[str, Any]]) -> None:
    if args.offline_fixtures:
        return
    if len(selected) <= 1 and args.skip_judge and not args.all:
        return
    seconds = int(os.getenv("LIVE_EVAL_COUNTDOWN_SECONDS", "5"))
    if seconds <= 0:
        return
    for remaining in range(seconds, 0, -1):
        print(f"Starting live API calls in {remaining}s. Press Ctrl+C to cancel.")
        time.sleep(1)


def cost_guard_skip_case(case: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": case["id"],
        "tags": case.get("tags", []),
        "passed": False,
        "scores": [],
        "judge": None,
        "issues": [{"severity": "info", "code": "not_run_cost_guard", "message": "Skipped before starting because LIVE_EVAL_MAX_OUTPUT_TOKENS was reached."}],
        "trace_length": 0,
        "iterations": 0,
        "converged": False,
        "failure_diagnosis": "not_run_cost_guard",
        "not_run_reason": "not_run_cost_guard",
    }


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
        f"Usage: `{report.get('usage', {})}`",
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
    parser = build_parser()
    args = parser.parse_args()

    all_cases = load_cases(PROJECT_ROOT / "evals" / "golden_set.yaml")
    cases, preserved_cases = select_cases(all_cases, args)
    try:
        validate_live_plan(args, cases)
    except LiveSafetyError as exc:
        print(f"Safety stop: {exc}", file=sys.stderr)
        return 1

    if not args.offline_fixtures:
        load_dotenv(PROJECT_ROOT / ".env")
    try:
        settings = Settings.from_env(PROJECT_ROOT)
    except ConfigurationError as exc:
        parser.error(str(exc))
    if not args.offline_fixtures and not settings.anthropic_api_key:
        parser.error("ANTHROPIC_API_KEY is required for live eval runs.")
    if not args.offline_fixtures:
        print(preflight_summary(args, cases, settings))
        maybe_countdown(args, cases)

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
            max_tokens=settings.anthropic_max_tokens,
        )

    output_cases = list(preserved_cases)
    metric_totals: dict[str, dict[str, int]] = {}
    usage_totals = {
        "model_calls": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_read_tokens": 0,
        "cache_creation_tokens": 0,
        "usage_unavailable": False,
    }
    stopped_by_cost_guard = False
    for index, case in enumerate(cases, start=1):
        if (
            not args.offline_fixtures
            and settings.live_eval_max_output_tokens is not None
            and usage_totals["output_tokens"] >= settings.live_eval_max_output_tokens
        ):
            stopped_by_cost_guard = True
            output_cases.append(cost_guard_skip_case(case))
            continue
        print(f"[{index}/{len(cases)}] {case['id']}")
        brief = resolve_brief(case, repo)
        try:
            result = make_fixture_result(case["id"], brief, tools, validator) if args.offline_fixtures else agent.run(brief)  # type: ignore[union-attr]
            if not args.offline_fixtures:
                run_usage = result.usage.as_dict()
                for key in ("model_calls", "input_tokens", "output_tokens", "cache_read_tokens", "cache_creation_tokens"):
                    usage_totals[key] += int(run_usage.get(key, 0) or 0)
                usage_totals["usage_unavailable"] = usage_totals["usage_unavailable"] or bool(run_usage.get("usage_unavailable"))
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
                "usage": result.usage.as_dict(),
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
                "usage": {},
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
        "usage": usage_totals,
        "stopped_by_cost_guard": stopped_by_cost_guard,
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
