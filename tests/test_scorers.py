from __future__ import annotations

import json
from pathlib import Path

from interior_agent.agent import AgentRunResult
from interior_agent.db import CatalogRepository
from interior_agent.schemas import DesignPlan, TraceEntry
from interior_agent.tools import AgentTools
from interior_agent.validator import PlanValidator
from scorers import deterministic_scores, trace_replanned
from ship_gate import aggregate_ship_gate


def _repo() -> CatalogRepository:
    return CatalogRepository(Path(__file__).resolve().parents[1] / "data" / "interior_company_catalog.db")


def _result(items: list[dict[str, object]], *, status: str = "complete", trace: list[TraceEntry] | None = None) -> AgentRunResult:
    repo = _repo()
    brief = repo.get_brief("BR-01")
    plan = DesignPlan.model_validate({
        "brief_id": "BR-01",
        "room_type": "Living Room",
        "status": status,
        "design_summary": "Fixture plan with catalog items.",
        "budget_inr": brief["budget_inr"],
        "items": [{"item_id": item["item_id"], "quantity": item.get("quantity", 1), "rationale": "Fixture"} for item in items],
        "assumptions": ["Empty rectangular room."],
    })
    trace = trace or [
        TraceEntry(iteration=1, tool="search_catalog", input={"category": "Sofa"}, result={"ok": True}),
        TraceEntry(iteration=2, tool="check_budget", input={"items": items, "budget_inr": brief["budget_inr"]}, result={"ok": True}),
        TraceEntry(iteration=3, tool="check_fit", input={"items": items}, result={"ok": True}),
    ]
    validated = PlanValidator(repo).validate(
        plan,
        room_length_cm=brief["length_cm"],
        room_width_cm=brief["width_cm"],
        must_haves=brief["must_haves"],
        brief_text=json.dumps(brief),
        trace=trace,
    )
    return AgentRunResult(plan, validated, trace, 3, True, [])


def test_scorer_required_and_forbidden_categories() -> None:
    result = _result([{"item_id": "SOF-001", "quantity": 1}, {"item_id": "TVU-001", "quantity": 1}])
    scores = deterministic_scores(result, {}, {"expect": {"required_categories": ["Sofa"], "forbidden_categories": ["TV Unit"]}})
    by_name = {score.name: score for score in scores}
    assert by_name["required_category:Sofa"].passed is True
    assert by_name["forbidden_category:TV Unit"].passed is False


def test_scorer_minimum_quantities() -> None:
    result = _result([{"item_id": "DNC-003", "quantity": 8}], status="partial")
    scores = deterministic_scores(result, {}, {"expect": {"minimum_quantities": {"Dining Chair": 8}}})
    assert {score.name: score for score in scores}["minimum_quantity:Dining Chair"].passed is True


def test_trace_replanning_requires_rejected_then_changed_set() -> None:
    trace = [
        TraceEntry(iteration=1, tool="check_fit", input={"items": [{"item_id": "SOF-004", "quantity": 1}]}, result={"fits": False}),
        TraceEntry(iteration=2, tool="check_fit", input={"items": [{"item_id": "SOF-008", "quantity": 1}]}, result={"fits": True}),
    ]
    assert trace_replanned(trace) is True
    assert trace_replanned(trace[:1]) is False


def test_ship_gate_marks_skipped_judge_not_evaluated() -> None:
    cases = [{
        "id": "case",
        "passed": True,
        "scores": [
            {"name": "real_items", "passed": True},
            {"name": "no_silent_budget_overflow", "passed": True},
            {"name": "required_declines", "passed": True},
            {"name": "fit_outcome", "passed": True},
            {"name": "all_required_tools_used", "passed": True},
            {"name": "final_fit_checked", "passed": True},
        ],
    }]
    gate = aggregate_ship_gate(cases, judge_skipped=True)
    assert gate["metrics"]["judge_overall_4_plus"]["not_evaluated"] is True
    assert gate["overall_passed"] is True
