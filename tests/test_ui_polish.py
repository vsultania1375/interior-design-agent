from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

from interior_agent.ui.presenter import brief_summary
from interior_agent.ui.state import BriefState, ConsultationStep, demo_preview_allowed, developer_mode_allowed


ROOT = Path(__file__).resolve().parents[1]


def test_developer_controls_hidden_by_default() -> None:
    assert developer_mode_allowed({}) is False


def test_developer_controls_enabled_only_with_explicit_flag() -> None:
    assert developer_mode_allowed({"INTERIOR_SHOW_DEVELOPER_MODE": "1"}) is True
    assert developer_mode_allowed({}, {"developer": "1"}) is True


def test_demo_mode_skips_dotenv_loading(monkeypatch: pytest.MonkeyPatch) -> None:
    pytest.importorskip("streamlit")
    dotenv = pytest.importorskip("dotenv")
    calls: list[str] = []

    def fake_load_dotenv(*args, **kwargs):
        calls.append("called")
        return True

    monkeypatch.setenv("INTERIOR_UI_DEMO_MODE", "1")
    monkeypatch.delenv("INTERIOR_SKIP_DOTENV", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(dotenv, "load_dotenv", fake_load_dotenv)
    sys.modules.pop("app", None)
    importlib.import_module("app")
    assert calls == []


def test_initial_labels_are_customer_friendly() -> None:
    summary = dict(brief_summary(BriefState()))
    assert summary["Size"] == "Not added yet"
    assert summary["Budget"] == "Not added yet"
    assert summary["Style"] == "Not selected"
    assert summary["Requirements"] == "None selected"
    assert "Price on request" not in summary.values()


def test_custom_demo_flow_cannot_use_fixed_sample_result() -> None:
    custom = BriefState(length_cm=900, width_cm=900, budget_inr=999999, style_preference="Modern", must_haves=["Sofa"])
    sample = BriefState(source_brief_id="BR-01")
    assert demo_preview_allowed(custom) is False
    assert demo_preview_allowed(sample) is True


def test_customer_app_source_hides_technical_default_controls() -> None:
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    assert "Live after review" not in source
    assert "Configured model" not in source
    assert "model ID" not in source
    assert "st.sidebar" not in source
    assert "Developer Mode" in source
    assert "developer_mode_allowed" in source


def test_first_step_has_no_bottom_back_control() -> None:
    assert ConsultationStep.welcome.value == "welcome"
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    assert "state.step not in {ConsultationStep.welcome, ConsultationStep.sample_or_custom, ConsultationStep.generating}" in source


def test_compact_start_over_exists_in_topbar_only() -> None:
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    assert source.count("Start over") == 1
    assert "top_start_over" in source
    assert "top-action" in source


def test_review_helper_note_is_compact_not_info_alert() -> None:
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    assert "Custom plan generation is available in live mode" in source
    assert "compact-note" in source
    assert 'st.info("Custom plan generation is available in live mode' not in source


def test_compact_preview_map_is_used_outside_result() -> None:
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    assert "max_px=330" in source
    assert "placeholder-room" in source


def test_live_generation_trigger_is_explicit_create_button() -> None:
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    assert '"Create my room plan"' in source
    assert "generation_requested = True" in source
    assert "InteriorDesignAgent(" in source


def test_generated_result_prevents_duplicate_generation() -> None:
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    assert "if state.generated_result is not None:" in source
    assert "if not state.generation_requested:" in source


def test_right_preview_has_no_furniture_before_result() -> None:
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    assert "state.step == ConsultationStep.result and state.generated_result is not None" in source


def test_first_screen_has_exactly_two_start_choices() -> None:
    from interior_agent.ui.chat import START_CHOICES

    assert [choice[0] for choice in START_CHOICES] == ["Design my own room", "Try a demo room"]


def test_customer_copy_does_not_use_internal_terms() -> None:
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    forbidden = ["Claude", "tool schema", "database brief", "API status", "Sonnet"]
    assert not any(term in source for term in forbidden)
