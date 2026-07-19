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
