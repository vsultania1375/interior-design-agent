from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from interior_agent.agent import InteriorDesignAgent
from interior_agent.db import CatalogRepository
from interior_agent.schemas import DesignPlan
from interior_agent.tools import AgentTools
from interior_agent.validator import PlanValidator


@dataclass
class TextBlock:
    text: str
    type: str = "text"


@dataclass
class ToolBlock:
    id: str
    name: str
    input: dict[str, Any]
    type: str = "tool_use"


@dataclass
class Response:
    content: list[Any]


class ScriptedMessages:
    def __init__(self, responses: list[Response]):
        self.responses = responses
        self.calls = 0
        self.requests: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> Response:
        self.requests.append(kwargs)
        response = self.responses[min(self.calls, len(self.responses) - 1)]
        self.calls += 1
        return response


class ScriptedClient:
    def __init__(self, responses: list[Response]):
        self.messages = ScriptedMessages(responses)


def repo() -> CatalogRepository:
    return CatalogRepository(Path(__file__).resolve().parents[1] / "data" / "interior_company_catalog.db")


def brief() -> dict[str, Any]:
    return repo().get_brief("BR-01")  # type: ignore[return-value]


def plan(items: list[dict[str, Any]] | None = None) -> str:
    payload = {
        "brief_id": "BR-01",
        "room_type": "Living Room",
        "status": "complete",
        "design_summary": "Valid fixture plan.",
        "budget_inr": 250000,
        "items": [
            {"item_id": row["item_id"], "quantity": row.get("quantity", 1), "rationale": "Fixture."}
            for row in (items or [{"item_id": "SOF-001"}, {"item_id": "CFT-001"}, {"item_id": "TVU-001"}, {"item_id": "RUG-001"}, {"item_id": "LMP-002"}])
        ],
        "assumptions": ["Empty rectangular room."],
        "tradeoffs": [],
        "flags": [],
        "style_relaxations": [],
        "declined_scope": [],
    }
    return json.dumps(payload)


def make_agent(responses: list[Response], max_iterations: int = 10) -> InteriorDesignAgent:
    r = repo()
    return InteriorDesignAgent(
        tools=AgentTools(r),
        validator=PlanValidator(r),
        api_key="",
        model="fake-model",
        max_iterations=max_iterations,
        client=ScriptedClient(responses),
    )


def test_happy_path_tool_sequence_and_callback_order() -> None:
    items = [{"item_id": "SOF-001", "quantity": 1}]
    agent = make_agent([
        Response([ToolBlock("1", "search_catalog", {"category": "Sofa"})]),
        Response([ToolBlock("2", "check_budget", {"items": items, "budget_inr": 250000})]),
        Response([ToolBlock("3", "check_fit", {"items": items, "room_length_cm": 480, "room_width_cm": 360, "room_type": "Living Room"})]),
        Response([TextBlock(plan(items))]),
    ])
    seen = []
    result = agent.run(brief(), on_trace=seen.append)
    assert [entry.tool for entry in result.trace] == ["search_catalog", "check_budget", "check_fit"]
    assert seen == result.trace
    assert result.converged is True


def test_multiple_tool_calls_in_one_response() -> None:
    items = [{"item_id": "SOF-001", "quantity": 1}]
    result = make_agent([
        Response([
            ToolBlock("1", "search_catalog", {"category": "Sofa"}),
            ToolBlock("2", "check_budget", {"items": items, "budget_inr": 250000}),
            ToolBlock("3", "check_fit", {"items": items, "room_length_cm": 480, "room_width_cm": 360, "room_type": "Living Room"}),
        ]),
        Response([TextBlock(plan(items))]),
    ]).run(brief())
    assert len(result.trace) == 3


def test_replanning_after_fit_failure_is_visible() -> None:
    bad = [{"item_id": "SOF-004", "quantity": 1}]
    good = [{"item_id": "SOF-008", "quantity": 1}]
    result = make_agent([
        Response([ToolBlock("1", "search_catalog", {"category": "Sofa"})]),
        Response([ToolBlock("2", "check_budget", {"items": bad, "budget_inr": 250000}), ToolBlock("3", "check_fit", {"items": bad, "room_length_cm": 240, "room_width_cm": 210, "room_type": "Living Room"})]),
        Response([ToolBlock("4", "check_budget", {"items": good, "budget_inr": 250000}), ToolBlock("5", "check_fit", {"items": good, "room_length_cm": 480, "room_width_cm": 360, "room_type": "Living Room"})]),
        Response([TextBlock(plan(good))]),
    ]).run({**brief(), "length_cm": 480, "width_cm": 360})
    assert result.trace[2].result["fits"] is False
    assert [entry.input.get("items") for entry in result.trace if entry.tool == "check_fit"][-1] == good
    assert "stale_fit_check" not in {issue.code for issue in result.validated.issues}


def test_malformed_terminal_json_becomes_flagged_partial() -> None:
    result = make_agent([Response([TextBlock("{not json")])]).run(brief())
    assert result.raw_plan.status.value == "partial"
    assert "agent_loop_issue" in {issue.code for issue in result.validated.issues}


def test_fenced_json_is_parsed() -> None:
    items = [{"item_id": "SOF-001", "quantity": 1}]
    result = make_agent([
        Response([ToolBlock("1", "search_catalog", {"category": "Sofa"}), ToolBlock("2", "check_budget", {"items": items, "budget_inr": 250000}), ToolBlock("3", "check_fit", {"items": items, "room_length_cm": 480, "room_width_cm": 360, "room_type": "Living Room"})]),
        Response([TextBlock("```json\n" + plan(items) + "\n```")]),
    ]).run(brief())
    assert result.raw_plan.items[0].item_id == "SOF-001"


def test_iteration_cap_fallback_uses_last_checked_items() -> None:
    items = [{"item_id": "SOF-001", "quantity": 1}]
    result = make_agent([Response([ToolBlock("1", "check_budget", {"items": items, "budget_inr": 250000})])], max_iterations=1).run(brief())
    assert result.raw_plan.status.value == "partial"
    assert result.raw_plan.items[0].item_id == "SOF-001"


def test_unknown_tool_call_returns_model_readable_result() -> None:
    result = make_agent([Response([ToolBlock("1", "bogus_tool", {})])], max_iterations=1).run(brief())
    assert result.trace[0].result["ok"] is False


def test_tool_exception_is_returned_as_result() -> None:
    result = make_agent([Response([ToolBlock("1", "check_budget", {"items": "bad", "budget_inr": 1})])], max_iterations=1).run(brief())
    assert result.trace[0].result["ok"] is False
    assert result.trace[0].result["error"]["code"] == "invalid_tool_input"


def test_terminal_answer_with_zero_tool_calls_is_invalid() -> None:
    result = make_agent([Response([TextBlock(plan())])]).run(brief())
    assert result.converged is False
    assert "zero_tool_complete" in {issue.code for issue in result.validated.issues}


def test_partial_plan_constructed_from_last_checked_candidate_set() -> None:
    items = [{"item_id": "SOF-001", "quantity": 1}, {"item_id": "CFT-001", "quantity": 1}]
    result = make_agent([Response([ToolBlock("1", "check_fit", {"items": items, "room_length_cm": 480, "room_width_cm": 360, "room_type": "Living Room"})])], max_iterations=1).run(brief())
    assert [item.item_id for item in result.raw_plan.items] == ["SOF-001", "CFT-001"]


def test_live_requests_keep_cache_control_under_anthropic_limit() -> None:
    items = [{"item_id": "SOF-001", "quantity": 1}]
    client = ScriptedClient([
        Response([ToolBlock("1", "search_catalog", {"category": "Sofa"})]),
        Response([ToolBlock("2", "check_budget", {"items": items, "budget_inr": 250000})]),
        Response([ToolBlock("3", "check_fit", {"items": items, "room_length_cm": 480, "room_width_cm": 360, "room_type": "Living Room"})]),
        Response([TextBlock(plan(items))]),
    ])
    r = repo()
    agent = InteriorDesignAgent(
        tools=AgentTools(r),
        validator=PlanValidator(r),
        api_key="",
        model="fake-model",
        max_iterations=10,
        client=client,
    )
    agent.run(brief())

    def count_cache_controls(value: Any) -> int:
        if isinstance(value, dict):
            return int("cache_control" in value) + sum(count_cache_controls(child) for child in value.values())
        if isinstance(value, list):
            return sum(count_cache_controls(child) for child in value)
        return 0

    assert client.messages.requests
    assert max(count_cache_controls(request) for request in client.messages.requests) <= 4
