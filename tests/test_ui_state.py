from __future__ import annotations

from interior_agent.ui.presenter import format_inr, price_copy, sample_display_name
from interior_agent.ui.state import ConsultationStep, answer, back, brief_ready, feet_to_cm, initial_state, populate_from_sample, reset, to_agent_brief


def test_initial_brief_state() -> None:
    state = initial_state()
    assert state.step == ConsultationStep.welcome
    assert state.brief.room_type == "Living Room"
    assert state.developer_mode is False
    assert state.messages[0].role == "assistant"


def test_required_field_readiness() -> None:
    state = initial_state()
    ready, missing = brief_ready(state.brief)
    assert ready is False
    assert "room size" in missing
    state.brief.length_cm = 365
    state.brief.width_cm = 305
    state.brief.budget_inr = 150000
    state.brief.style_preference = "Modern"
    state.brief.must_haves = ["Sofa"]
    assert brief_ready(state.brief) == (True, [])


def test_back_transition_and_reset() -> None:
    state = initial_state()
    state.step = ConsultationStep.room_size
    answer(state, "Medium", next_to=ConsultationStep.budget)
    back(state)
    assert state.step == ConsultationStep.room_size
    assert state.history[-1]["role"] == "assistant"
    assert reset().step == ConsultationStep.welcome


def test_sample_population_hides_id_in_display_name() -> None:
    state = initial_state()
    brief = {
        "brief_id": "BR-01",
        "length_cm": 480,
        "width_cm": 360,
        "budget_inr": 250000,
        "style_preference": "Scandinavian",
        "must_haves": "Sofa, rug",
        "constraints": "Natural light",
    }
    name = sample_display_name(brief)
    populate_from_sample(state, brief, name)
    assert "BR-01" not in name
    assert state.step == ConsultationStep.result
    assert state.brief.source_brief_id == "BR-01"
    assert to_agent_brief(state.brief)["room_type"] == "Living Room"


def test_feet_to_centimetre_conversion() -> None:
    assert feet_to_cm(10) == 305


def test_budget_formatting_indian_grouping() -> None:
    assert format_inr(250000) == "₹2,50,000"


def test_unknown_price_copy_is_customer_facing() -> None:
    class Line:
        unit_price_inr = None

    assert price_copy(Line()).startswith("Price on request")
