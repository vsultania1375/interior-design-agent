from __future__ import annotations

import json

from interior_agent.agent import AgentRunResult
from interior_agent.db import CatalogRepository
from interior_agent.schemas import DesignPlan, TraceEntry
from interior_agent.tools import AgentTools
from interior_agent.validator import PlanValidator


DEMO_ITEM_IDS = ["SOF-001", "CFT-001", "TVU-001", "RUG-002", "LMP-002", "SDT-001"]


def make_demo_result(repo: CatalogRepository, brief: dict[str, object] | None = None) -> AgentRunResult:
    source = dict(brief or repo.get_brief("BR-01") or {})
    if not source:
        raise ValueError("BR-01 sample brief is required for demo mode.")
    source["brief_id"] = source.get("brief_id") or "BR-01"
    source["room_type"] = "Living Room"
    source["must_haves"] = source.get("must_haves") or "3-seater sofa, coffee table, TV unit, rug, lighting"
    source["budget_inr"] = int(source.get("budget_inr") or 250000)

    selected = [{"item_id": item_id, "quantity": 1} for item_id in DEMO_ITEM_IDS]
    records = repo.get_items(DEMO_ITEM_IDS)
    tools = AgentTools(repo)
    trace = [
        TraceEntry(iteration=1, tool="search_catalog", input={"category": "Sofa", "room_type": "Living Room", "limit": 5}, result=tools.search_catalog(category="Sofa", room_type="Living Room", limit=5)),
        TraceEntry(iteration=2, tool="check_budget", input={"items": selected, "budget_inr": source["budget_inr"]}, result=tools.check_budget(items=selected, budget_inr=source["budget_inr"])),
        TraceEntry(iteration=3, tool="check_fit", input={"items": selected, "room_length_cm": source["length_cm"], "room_width_cm": source["width_cm"], "room_type": "Living Room"}, result=tools.check_fit(items=selected, room_length_cm=source["length_cm"], room_width_cm=source["width_cm"], room_type="Living Room")),
    ]
    plan = DesignPlan.model_validate({
        "brief_id": source["brief_id"],
        "room_type": "Living Room",
        "status": "complete",
        "design_summary": "A calm Scandinavian living room with a fabric sofa, grounded rug, practical media storage, warm wood coffee table, and layered lighting.",
        "budget_inr": source["budget_inr"],
        "items": [
            {
                "item_id": item_id,
                "quantity": 1,
                "rationale": f"Selected from the real catalog for a balanced living-room plan: {records[item_id]['name']}.",
                "placement_note": _placement(records[item_id]["category"]),
            }
            for item_id in DEMO_ITEM_IDS
        ],
        "tradeoffs": ["Offline demo preview; run the live agent after review for a model-generated plan."],
        "flags": ["Offline demo preview using real catalog rows."],
        "assumptions": ["Conceptual layout based on an empty rectangular room."],
        "style_relaxations": [],
        "declined_scope": [],
    })
    validator = PlanValidator(repo)
    validated = validator.validate(
        plan,
        room_length_cm=int(source["length_cm"]),
        room_width_cm=int(source["width_cm"]),
        must_haves=str(source["must_haves"]),
        brief_text=json.dumps(source, ensure_ascii=False),
        trace=trace,
    )
    return AgentRunResult(plan, validated, trace, 3, True, [])


def _placement(category: str) -> str:
    return {
        "Sofa": "Centre it along the main seating wall.",
        "Coffee Table": "Place it in the middle of the seating zone.",
        "TV Unit": "Keep it opposite the sofa on the facing wall.",
        "Rug": "Anchor the sofa and coffee table with the front legs touching the rug.",
        "Floor Lamp": "Place beside the sofa for soft evening light.",
        "Side Table": "Keep near the sofa arm for daily use.",
    }.get(category, "Place where it supports the main seating arrangement.")
