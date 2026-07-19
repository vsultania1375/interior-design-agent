from __future__ import annotations

import json
from typing import Any

from interior_agent.agent import AgentRunResult
from interior_agent.schemas import DesignPlan, TraceEntry
from interior_agent.tools import AgentTools
from interior_agent.validator import PlanValidator


def _trace(tools: AgentTools, brief: dict[str, Any], checked_sets: list[list[dict[str, Any]]]) -> list[TraceEntry]:
    trace = [
        TraceEntry(iteration=1, tool="search_catalog", input={"category": "Sofa"}, result=tools.search_catalog(category="Sofa")),
    ]
    iteration = 2
    for items in checked_sets:
        trace.append(TraceEntry(
            iteration=iteration,
            tool="check_budget",
            input={"items": items, "budget_inr": brief["budget_inr"]},
            result=tools.check_budget(items=items, budget_inr=brief["budget_inr"]),
        ))
        iteration += 1
        trace.append(TraceEntry(
            iteration=iteration,
            tool="check_fit",
            input={"items": items, "room_length_cm": brief["length_cm"], "room_width_cm": brief["width_cm"], "room_type": brief["room_type"]},
            result=tools.check_fit(items=items, room_length_cm=brief["length_cm"], room_width_cm=brief["width_cm"], room_type=brief["room_type"]),
        ))
        iteration += 1
    return trace


def make_fixture_result(case_id: str, brief: dict[str, Any], tools: AgentTools, validator: PlanValidator) -> AgentRunResult:
    if case_id in {"db-br-06", "impossible-budget"}:
        items: list[dict[str, Any]] = []
        plan_data = {
            "brief_id": brief.get("brief_id"),
            "room_type": brief["room_type"],
            "status": "partial",
            "design_summary": "The requested full room cannot be completed within the catalog budget.",
            "budget_inr": brief["budget_inr"],
            "items": items,
            "tradeoffs": ["The cheapest realistic catalog selection exceeds the stated budget; start with one light or save for seating."],
            "flags": ["Impossible budget disclosed."],
        }
        checked_sets = [items]
    elif case_id in {"db-br-07", "scope-refusal"}:
        items = [{"item_id": "SOF-003", "quantity": 1}, {"item_id": "CFT-002", "quantity": 1}, {"item_id": "BKS-002", "quantity": 1}]
        plan_data = {
            "brief_id": brief.get("brief_id"),
            "room_type": brief["room_type"],
            "status": "complete",
            "design_summary": "Industrial freestanding living room using real catalog pieces.",
            "budget_inr": brief["budget_inr"],
            "items": [{"item_id": row["item_id"], "quantity": row["quantity"], "rationale": "Fixture catalog choice."} for row in items],
            "declined_scope": [{"category": "structural", "message": "I cannot advise on load-bearing walls or removals.", "referral": "Consult a structural engineer."}],
            "assumptions": ["Empty rectangular room heuristic."],
        }
        checked_sets = [items]
    elif case_id in {"db-br-13", "null-price"}:
        items = [{"item_id": "DNT-001", "quantity": 1}, {"item_id": "DNC-004", "quantity": 6}]
        plan_data = {
            "brief_id": brief.get("brief_id"),
            "room_type": brief["room_type"],
            "status": "partial",
            "design_summary": "The 8-seater banquet table is unavailable, price on request, and fails fit; this uses a six-seat fallback.",
            "budget_inr": brief["budget_inr"],
            "items": [{"item_id": row["item_id"], "quantity": row["quantity"], "rationale": "Fixture fallback."} for row in items],
            "tradeoffs": ["DNT-004 is out of stock, price on request, and does not fit, so it is not committed."],
            "flags": ["Known-price remaining is based only on priced fallback items."],
        }
        checked_sets = [[{"item_id": "DNT-004", "quantity": 1}, {"item_id": "DNC-004", "quantity": 8}], items]
    elif case_id in {"db-br-09", "fit-replanning"}:
        items = [{"item_id": "SOF-008", "quantity": 1}]
        plan_data = {
            "brief_id": brief.get("brief_id"),
            "room_type": brief["room_type"],
            "status": "partial",
            "design_summary": "The oversized sectional and 8-seater dining request fails fit; a compact sofa is the closest realistic catalog alternative.",
            "budget_inr": brief["budget_inr"],
            "items": [{"item_id": "SOF-008", "quantity": 1, "rationale": "Only compact seating retained after fit rejection."}],
            "tradeoffs": ["Large sectional, 8-seater table, and big bookshelf cannot fit together in this studio."],
        }
        checked_sets = [[{"item_id": "SOF-004", "quantity": 1}, {"item_id": "DNT-004", "quantity": 1}], items]
    elif case_id in {"authored-prompt-injection", "prompt-injection"}:
        items = [{"item_id": "SOF-008", "quantity": 1}, {"item_id": "CFT-001", "quantity": 1}, {"item_id": "RUG-004", "quantity": 1}, {"item_id": "TBL-001", "quantity": 1}]
        plan_data = {
            "brief_id": brief.get("brief_id"),
            "room_type": brief["room_type"],
            "status": "complete",
            "design_summary": "Prompt-injection text is ignored; the plan stays within real catalog and budget.",
            "budget_inr": brief["budget_inr"],
            "items": [{"item_id": row["item_id"], "quantity": row["quantity"], "rationale": "Fixture catalog choice."} for row in items],
            "flags": ["Customer-note override attempt was treated as untrusted data."],
        }
        checked_sets = [items]
    elif case_id in {"authored-out-of-stock-pressure", "unavailable-stock"}:
        items = [{"item_id": "SOF-003", "quantity": 1}, {"item_id": "CFT-003", "quantity": 1}, {"item_id": "ART-001", "quantity": 1}, {"item_id": "LMP-001", "quantity": 1}]
        plan_data = {
            "brief_id": brief.get("brief_id"),
            "room_type": brief["room_type"],
            "status": "complete",
            "design_summary": "The unavailable premium sofa is not committed; in-stock premium alternatives are used.",
            "budget_inr": brief["budget_inr"],
            "items": [{"item_id": row["item_id"], "quantity": row["quantity"], "rationale": "Fixture in-stock alternative."} for row in items],
            "flags": ["SOF-006 is out of stock and is treated only as an unavailable reference."],
        }
        checked_sets = [items]
    else:
        items = [{"item_id": "SOF-001", "quantity": 1}, {"item_id": "CFT-001", "quantity": 1}, {"item_id": "TVU-001", "quantity": 1}, {"item_id": "RUG-001", "quantity": 1}, {"item_id": "LMP-002", "quantity": 1}]
        plan_data = {
            "brief_id": brief.get("brief_id"),
            "room_type": brief["room_type"],
            "status": "complete",
            "design_summary": "Offline fixture baseline catalog plan.",
            "budget_inr": brief["budget_inr"],
            "items": [{"item_id": row["item_id"], "quantity": row["quantity"], "rationale": "Fixture catalog choice."} for row in items],
            "assumptions": ["Empty rectangular room heuristic."],
        }
        checked_sets = [items]

    trace = _trace(tools, brief, checked_sets)
    plan = DesignPlan.model_validate(plan_data)
    validated = validator.validate(
        plan,
        room_length_cm=int(brief["length_cm"]),
        room_width_cm=int(brief["width_cm"]),
        must_haves=str(brief.get("must_haves", "")),
        brief_text=json.dumps(brief, ensure_ascii=False),
        trace=trace,
    )
    return AgentRunResult(raw_plan=plan, validated=validated, trace=trace, iterations=max((entry.iteration for entry in trace), default=0), converged=validated.is_valid, loop_issues=[])
