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
    assert "st.sidebar" not in source
    assert "Developer Mode" in source
    assert "developer_mode_allowed" in source


def test_first_step_has_no_bottom_back_control() -> None:
    assert ConsultationStep.welcome.value == "welcome"
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    assert "state.step not in {ConsultationStep.welcome, ConsultationStep.result}" in source
