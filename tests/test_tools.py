from __future__ import annotations

from pathlib import Path

import pytest

from interior_agent.db import CatalogRepository
from interior_agent.tools import AgentTools, TOOL_SCHEMAS


@pytest.fixture()
def repo() -> CatalogRepository:
    return CatalogRepository(Path(__file__).resolve().parents[1] / "data" / "interior_company_catalog.db")


@pytest.fixture()
def tools(repo: CatalogRepository) -> AgentTools:
    return AgentTools(repo)


def test_database_counts(repo: CatalogRepository) -> None:
    assert len(repo.all_item_ids()) == 72
    assert len(repo.list_briefs()) == 14


def test_scandinavian_sofa_search(repo: CatalogRepository) -> None:
    ids = {item["item_id"] for item in repo.search_catalog(category="Sofa", style="Scandinavian")}
    assert {"SOF-001", "SOF-002"}.issubset(ids)


def test_stock_filter_excludes_premium_sofa(repo: CatalogRepository) -> None:
    ids = {item["item_id"] for item in repo.search_catalog(category="Sofa", style="Contemporary", in_stock_only=True)}
    assert "SOF-006" not in ids


def test_budget_multiplies_quantity(tools: AgentTools) -> None:
    result = tools.check_budget(items=[{"item_id": "DNC-003", "quantity": 8}], budget_inr=40000)
    assert result["known_total_inr"] == 33_600
    assert result["remaining_inr"] == 6_400


def test_null_price_is_not_zero(tools: AgentTools) -> None:
    result = tools.check_budget(items=[{"item_id": "CFT-004", "quantity": 1}], budget_inr=100000)
    assert result["known_total_inr"] == 0
    assert result["has_unknown_prices"] is True
    assert result["unknown_price_items"] == ["CFT-004"]


def test_large_sectional_fails_tiny_room(tools: AgentTools) -> None:
    result = tools.check_fit(
        items=[{"item_id": "SOF-004", "quantity": 1}],
        room_length_cm=240,
        room_width_cm=210,
        room_type="Living Room",
    )
    assert result["fits"] is False
    assert any(row["item_id"] == "SOF-004" for row in result["hard_violations"])


def test_small_sofa_just_passes_boundary(tools: AgentTools) -> None:
    result = tools.check_fit(
        items=[{"item_id": "SOF-008", "quantity": 1}],
        room_length_cm=220,
        room_width_cm=175,
        room_type="Living Room",
    )
    assert result["fits"] is True


def test_small_sofa_just_misses_boundary(tools: AgentTools) -> None:
    result = tools.check_fit(
        items=[{"item_id": "SOF-008", "quantity": 1}],
        room_length_cm=219,
        room_width_cm=174,
        room_type="Living Room",
    )
    assert result["fits"] is False


def test_eight_seater_table_fails_br13_room(tools: AgentTools) -> None:
    result = tools.check_fit(
        items=[{"item_id": "DNT-004", "quantity": 1}],
        room_length_cm=340,
        room_width_cm=280,
        room_type="Dining",
    )
    assert result["fits"] is False


def test_six_seater_table_passes_br13_room(tools: AgentTools) -> None:
    result = tools.check_fit(
        items=[{"item_id": "DNT-001", "quantity": 1}],
        room_length_cm=340,
        room_width_cm=280,
        room_type="Dining",
    )
    assert result["fits"] is True


def test_anthropic_tool_schemas_avoid_unsupported_numeric_bounds() -> None:
    def walk(value):
        if isinstance(value, dict):
            assert "minimum" not in value
            assert "maximum" not in value
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(TOOL_SCHEMAS)
