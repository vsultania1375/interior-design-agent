from __future__ import annotations

from pathlib import Path

import pytest

from interior_agent.db import CatalogRepository
from interior_agent.schemas import DesignPlan, TraceEntry
from interior_agent.validator import PlanValidator


@pytest.fixture()
def validator() -> PlanValidator:
    repo = CatalogRepository(Path(__file__).resolve().parents[1] / "data" / "interior_company_catalog.db")
    return PlanValidator(repo)


def full_trace() -> list[TraceEntry]:
    return [
        TraceEntry(iteration=1, tool="search_catalog", input={"category": "Sofa"}, result={"ok": True}),
        TraceEntry(iteration=2, tool="check_budget", input={"items": []}, result={"ok": True}),
        TraceEntry(iteration=3, tool="check_fit", input={"items": []}, result={"ok": True}),
    ]


def trace_for_items(items: list[dict[str, object]]) -> list[TraceEntry]:
    return [
        TraceEntry(iteration=1, tool="search_catalog", input={"category": "Coffee Table"}, result={"ok": True}),
        TraceEntry(iteration=2, tool="check_budget", input={"items": items, "budget_inr": 100000}, result={"ok": True}),
        TraceEntry(iteration=3, tool="check_fit", input={"items": items}, result={"ok": True}),
    ]


def test_validator_catches_invented_item(validator: PlanValidator) -> None:
    plan = DesignPlan.model_validate({
        "room_type": "Living Room",
        "design_summary": "Test",
        "budget_inr": 100000,
        "items": [{"item_id": "FAKE-001", "quantity": 1, "rationale": "Test"}],
    })
    result = validator.validate(
        plan,
        room_length_cm=400,
        room_width_cm=300,
        must_haves="",
        brief_text="",
        trace=full_trace(),
    )
    assert "invented_item" in {issue.code for issue in result.issues}
    assert result.is_valid is False


def test_validator_catches_negative_tv_requirement(validator: PlanValidator) -> None:
    plan = DesignPlan.model_validate({
        "room_type": "Living Room",
        "design_summary": "Test",
        "budget_inr": 100000,
        "items": [{"item_id": "TVU-001", "quantity": 1, "rationale": "Test"}],
    })
    result = validator.validate(
        plan,
        room_length_cm=400,
        room_width_cm=300,
        must_haves="no TV",
        brief_text="no TV",
        trace=full_trace(),
    )
    assert "missing_must_have" in {issue.code for issue in result.issues}


def test_validator_requires_structural_decline(validator: PlanValidator) -> None:
    plan = DesignPlan.model_validate({
        "room_type": "Living Room",
        "design_summary": "Test",
        "budget_inr": 100000,
        "items": [],
    })
    result = validator.validate(
        plan,
        room_length_cm=400,
        room_width_cm=300,
        must_haves="",
        brief_text="Should I knock down the kitchen wall? Is it load-bearing?",
        trace=full_trace(),
    )
    assert "missing_decline" in {issue.code for issue in result.issues}


def test_validator_accepts_structural_decline(validator: PlanValidator) -> None:
    plan = DesignPlan.model_validate({
        "room_type": "Living Room",
        "design_summary": "Test",
        "budget_inr": 100000,
        "items": [],
        "declined_scope": [{
            "category": "structural",
            "message": "I cannot assess whether a wall is load-bearing.",
            "referral": "Consult a structural engineer.",
        }],
    })
    result = validator.validate(
        plan,
        room_length_cm=400,
        room_width_cm=300,
        must_haves="",
        brief_text="Should I knock down the kitchen wall? Is it load-bearing?",
        trace=full_trace(),
    )
    assert "missing_decline" not in {issue.code for issue in result.issues}


def test_validator_requires_all_three_tools(validator: PlanValidator) -> None:
    plan = DesignPlan.model_validate({
        "room_type": "Living Room",
        "design_summary": "Test",
        "budget_inr": 100000,
        "items": [],
    })
    result = validator.validate(
        plan,
        room_length_cm=400,
        room_width_cm=300,
        must_haves="",
        brief_text="",
        trace=[],
    )
    missing_tool_issues = [issue for issue in result.issues if issue.code == "missing_tool_use"]
    assert len(missing_tool_issues) == 3


def test_partial_plan_can_honestly_omit_impossible_must_haves(validator: PlanValidator) -> None:
    plan = DesignPlan.model_validate({
        "room_type": "Living Room",
        "status": "partial",
        "design_summary": "The full room cannot be delivered within this budget.",
        "budget_inr": 20000,
        "items": [],
        "tradeoffs": ["The cheapest catalog sofa alone exceeds the budget; start with lighting and save for seating."],
    })
    result = validator.validate(
        plan,
        room_length_cm=450,
        room_width_cm=360,
        must_haves="sofa, coffee table, TV unit, rug, lighting",
        brief_text="Can you do the whole room for INR 20,000?",
        trace=full_trace(),
    )
    assert result.is_valid is True
    missing = [issue for issue in result.issues if issue.code == "missing_must_have"]
    assert len(missing) == 1
    assert missing[0].severity == "warning"


def test_undisclosed_unknown_price_is_error(validator: PlanValidator) -> None:
    plan = DesignPlan.model_validate({
        "room_type": "Living Room",
        "design_summary": "Traditional plan",
        "budget_inr": 100000,
        "items": [{"item_id": "CFT-004", "quantity": 1, "rationale": "Traditional table"}],
    })
    result = validator.validate(
        plan,
        room_length_cm=450,
        room_width_cm=350,
        must_haves="coffee table",
        brief_text="",
        trace=full_trace(),
    )
    assert "undisclosed_unknown_price" in {issue.code for issue in result.issues}
    assert result.is_valid is False


def test_disclosed_unknown_price_is_warning(validator: PlanValidator) -> None:
    plan = DesignPlan.model_validate({
        "room_type": "Living Room",
        "design_summary": "Traditional plan",
        "budget_inr": 100000,
        "items": [{"item_id": "CFT-004", "quantity": 1, "rationale": "Traditional table"}],
        "flags": ["CFT-004 is price on request, so the known BOQ total is incomplete."],
    })
    result = validator.validate(
        plan,
        room_length_cm=450,
        room_width_cm=350,
        must_haves="coffee table",
        brief_text="",
        trace=trace_for_items([{"item_id": "CFT-004", "quantity": 1}]),
    )
    assert "unknown_price" in {issue.code for issue in result.issues}
    assert "undisclosed_unknown_price" not in {issue.code for issue in result.issues}
    assert "unknown_price_complete" in {issue.code for issue in result.issues}
    assert result.is_valid is False


def test_undisclosed_out_of_stock_is_error(validator: PlanValidator) -> None:
    plan = DesignPlan.model_validate({
        "room_type": "Living Room",
        "design_summary": "Premium plan",
        "budget_inr": 500000,
        "items": [{"item_id": "SOF-006", "quantity": 1, "rationale": "Premium sofa"}],
    })
    result = validator.validate(
        plan,
        room_length_cm=520,
        room_width_cm=380,
        must_haves="sofa",
        brief_text="",
        trace=full_trace(),
    )
    assert "undisclosed_out_of_stock" in {issue.code for issue in result.issues}
    assert result.is_valid is False


def test_validator_rejects_budget_changed_from_brief(validator: PlanValidator) -> None:
    plan = DesignPlan.model_validate({
        "room_type": "Living Room",
        "design_summary": "Test",
        "budget_inr": 999999,
        "items": [],
    })
    result = validator.validate(plan, room_length_cm=400, room_width_cm=300, must_haves="", brief_text='{"budget_inr": 100000, "room_type": "Living Room"}', trace=full_trace())
    assert "budget_changed" in {issue.code for issue in result.issues}


def test_validator_detects_stale_final_checks(validator: PlanValidator) -> None:
    plan = DesignPlan.model_validate({
        "room_type": "Living Room",
        "design_summary": "Test",
        "budget_inr": 100000,
        "items": [{"item_id": "SOF-001", "quantity": 1, "rationale": "Test"}],
    })
    result = validator.validate(plan, room_length_cm=480, room_width_cm=360, must_haves="", brief_text="", trace=full_trace())
    assert "stale_budget_check" in {issue.code for issue in result.issues}
    assert "stale_fit_check" in {issue.code for issue in result.issues}


def test_validator_flags_deadline_conflict(validator: PlanValidator) -> None:
    plan = DesignPlan.model_validate({
        "room_type": "Bedroom",
        "design_summary": "Bedroom plan",
        "budget_inr": 200000,
        "items": [{"item_id": "BED-004", "quantity": 1, "rationale": "Coastal bed"}],
        "flags": ["Lead time may conflict with the delivery deadline; delivery cannot be guaranteed."],
        "declined_scope": [{"category": "delivery_guarantee", "message": "I cannot guarantee delivery by a date."}],
    })
    trace = trace_for_items([{"item_id": "BED-004", "quantity": 1}])
    result = validator.validate(plan, room_length_cm=400, room_width_cm=340, must_haves="bed", brief_text="move-in in 14 days; guarantee delivery", trace=trace)
    assert "lead_time_conflict" in {issue.code for issue in result.issues}


def test_validator_flags_duplicate_item_ids(validator: PlanValidator) -> None:
    plan = DesignPlan.model_validate({
        "room_type": "Living Room",
        "design_summary": "Test",
        "budget_inr": 100000,
        "items": [
            {"item_id": "LMP-001", "quantity": 1, "rationale": "Test"},
            {"item_id": "LMP-001", "quantity": 1, "rationale": "Test"},
        ],
    })
    result = validator.validate(plan, room_length_cm=480, room_width_cm=360, must_haves="lighting", brief_text="", trace=trace_for_items([{"item_id": "LMP-001", "quantity": 2}]))
    assert "duplicate_item_id" in {issue.code for issue in result.issues}
