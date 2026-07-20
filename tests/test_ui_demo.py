from __future__ import annotations

from pathlib import Path

from interior_agent.db import CatalogRepository
from interior_agent.ui.demo import make_demo_result
from interior_agent.ui.presenter import normal_result_text


def _repo() -> CatalogRepository:
    return CatalogRepository(Path(__file__).resolve().parents[1] / "data" / "interior_company_catalog.db")


def test_demo_mode_uses_real_catalog_and_no_anthropic_client() -> None:
    result = make_demo_result(_repo())
    assert result.converged is True
    assert {entry.tool for entry in result.trace} == {"search_catalog", "check_budget", "check_fit"}
    assert all(line.item_id for line in result.validated.boq)


def test_normal_result_presenter_hides_raw_json() -> None:
    result = make_demo_result(_repo())
    text = normal_result_text(result.validated)
    assert "summary" in text
    assert "raw" not in text
    assert "{" not in " ".join(str(value) for value in text.values())


def test_normal_result_shows_budget_left_when_within_budget() -> None:
    result = make_demo_result(_repo())
    validated = result.validated.model_copy(update={"remaining_inr": 5000, "over_budget": False})
    text = normal_result_text(validated)
    assert text["over_budget"] is False
    assert text["remaining_label"] == "Budget left"
    assert text["remaining"] == "₹5,000"
    assert "-" not in text["remaining"]


def test_normal_result_shows_over_budget_by_when_negative() -> None:
    result = make_demo_result(_repo())
    validated = result.validated.model_copy(update={"remaining_inr": -136490, "over_budget": True})
    text = normal_result_text(validated)
    assert text["over_budget"] is True
    assert text["remaining_label"] == "Over budget by"
    assert text["remaining"] == "₹1,36,490"
    assert "-" not in text["remaining"]
