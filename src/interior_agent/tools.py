from __future__ import annotations

from typing import Any

from .db import CatalogRepository
from .fit import check_fit as run_fit_check


def normalize_selections(raw_items: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    merged: dict[str, int] = {}
    for raw in raw_items or []:
        if not isinstance(raw, dict):
            continue
        item_id = str(raw.get("item_id", "")).strip().upper()
        if not item_id:
            continue
        quantity = max(1, min(int(raw.get("quantity", 1)), 20))
        merged[item_id] = min(20, merged.get(item_id, 0) + quantity)
    return [{"item_id": item_id, "quantity": quantity} for item_id, quantity in merged.items()]


def _tool_error(message: str, *, code: str = "invalid_tool_input") -> dict[str, Any]:
    return {"ok": False, "error": {"code": code, "message": message}}


class AgentTools:
    def __init__(self, repository: CatalogRepository):
        self.repository = repository

    def search_catalog(self, **kwargs: Any) -> dict[str, Any]:
        try:
            results = self.repository.search_catalog(**kwargs)
            return {"ok": True, "count": len(results), "items": results}
        except Exception as exc:  # tool boundary: return a model-readable error, do not crash the loop
            return {"ok": False, "error": str(exc), "items": []}

    def check_budget(self, *, items: list[dict[str, Any]], budget_inr: int) -> dict[str, Any]:
        if not isinstance(items, list):
            return _tool_error("items must be a list of {item_id, quantity} objects.")
        if int(budget_inr) < 0:
            return _tool_error("budget_inr must be a non-negative integer.")
        selections = normalize_selections(items)
        records = self.repository.get_items(selection["item_id"] for selection in selections)
        missing = [selection["item_id"] for selection in selections if selection["item_id"] not in records]
        lines: list[dict[str, Any]] = []
        known_total = 0
        unknown_price_items: list[str] = []

        for selection in selections:
            item = records.get(selection["item_id"])
            if not item:
                continue
            quantity = selection["quantity"]
            price = item.get("price_inr")
            line_total = None if price is None else price * quantity
            if line_total is None:
                unknown_price_items.append(item["item_id"])
            else:
                known_total += line_total
            lines.append({
                "item_id": item["item_id"],
                "name": item["name"],
                "quantity": quantity,
                "unit_price_inr": price,
                "line_total_inr": line_total,
                "in_stock": item["in_stock"],
            })

        return {
            "ok": not missing,
            "budget_inr": int(budget_inr),
            "known_total_inr": known_total,
            "remaining_inr": int(budget_inr) - known_total,
            "over_budget": known_total > int(budget_inr),
            "has_unknown_prices": bool(unknown_price_items),
            "unknown_price_items": unknown_price_items,
            "missing_item_ids": missing,
            "lines": lines,
            "note": "Unknown prices are never treated as zero; the known total is incomplete when has_unknown_prices is true.",
        }

    def check_fit(
        self,
        *,
        items: list[dict[str, Any]],
        room_length_cm: int,
        room_width_cm: int,
        room_type: str,
    ) -> dict[str, Any]:
        if not isinstance(items, list):
            return _tool_error("items must be a list of {item_id, quantity} objects.")
        if int(room_length_cm) <= 0 or int(room_width_cm) <= 0:
            return _tool_error("room_length_cm and room_width_cm must be positive integers.")
        selections = normalize_selections(items)
        records = self.repository.get_items(selection["item_id"] for selection in selections)
        missing = [selection["item_id"] for selection in selections if selection["item_id"] not in records]
        selected_records = [
            {"item": records[selection["item_id"]], "quantity": selection["quantity"]}
            for selection in selections
            if selection["item_id"] in records
        ]
        result = run_fit_check(
            selected_records,
            room_length_cm=int(room_length_cm),
            room_width_cm=int(room_width_cm),
            room_type=room_type,
        )
        result["ok"] = not missing
        result["missing_item_ids"] = missing
        return result

    def execute(self, tool_name: str, tool_input: dict[str, Any]) -> dict[str, Any]:
        try:
            if not isinstance(tool_input, dict):
                return _tool_error("Tool input must be a JSON object.")
            if tool_name == "search_catalog":
                return self.search_catalog(**tool_input)
            if tool_name == "check_budget":
                return self.check_budget(**tool_input)
            if tool_name == "check_fit":
                return self.check_fit(**tool_input)
        except (TypeError, ValueError, KeyError) as exc:
            return _tool_error(str(exc))
        return {"ok": False, "error": f"Unknown tool: {tool_name}"}


TOOL_SCHEMAS = [
    {
        "name": "search_catalog",
        "description": "Search the real SQLite catalog by category and optional style, price, room, dimensions, and stock filters. Never invent items outside these results.",
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {"type": "string"},
                "style": {"type": "string"},
                "min_price": {"type": "integer"},
                "max_price": {"type": "integer"},
                "room_type": {"type": "string"},
                "max_width_cm": {"type": "integer"},
                "max_depth_cm": {"type": "integer"},
                "in_stock_only": {"type": "boolean", "default": True},
                "include_null_price": {"type": "boolean", "default": True},
                "limit": {"type": "integer", "default": 20},
            },
            "required": ["category"],
            "additionalProperties": False,
        },
    },
    {
        "name": "check_budget",
        "description": "Compute the BOQ total for selected catalog items and quantities, compare it with the budget, and flag unknown prices. Call this before finalizing and again after any item change.",
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "item_id": {"type": "string"},
                            "quantity": {"type": "integer"},
                        },
                        "required": ["item_id", "quantity"],
                        "additionalProperties": False,
                    },
                },
                "budget_inr": {"type": "integer"},
            },
            "required": ["items", "budget_inr"],
            "additionalProperties": False,
        },
    },
    {
        "name": "check_fit",
        "description": "Check individual dimensions, category-specific clearance, and aggregate occupancy against an empty rectangular room. Call this before finalizing and re-plan if it fails.",
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "item_id": {"type": "string"},
                            "quantity": {"type": "integer"},
                        },
                        "required": ["item_id", "quantity"],
                        "additionalProperties": False,
                    },
                },
                "room_length_cm": {"type": "integer"},
                "room_width_cm": {"type": "integer"},
                "room_type": {"type": "string"},
            },
            "required": ["items", "room_length_cm", "room_width_cm", "room_type"],
            "additionalProperties": False,
        },
    },
]
