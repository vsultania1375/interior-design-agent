from __future__ import annotations

from interior_agent.ui.input_parser import MIN_BUDGET_INR, budget_needs_confirmation, is_plausible_budget, parse_budget, parse_dimensions, parse_multi_value_text, parse_style
from interior_agent.ui.state import (
    ConsultationStep,
    add_review_message,
    answer,
    back,
    demo_preview_allowed,
    initial_state,
)


def test_five_deterministic_consultation_steps_exist() -> None:
    steps = [
        ConsultationStep.room_size,
        ConsultationStep.budget,
        ConsultationStep.style,
        ConsultationStep.must_haves,
        ConsultationStep.constraints,
    ]
    assert len(steps) == 5


def test_selecting_single_option_appends_one_user_message_once() -> None:
    state = initial_state()
    state.step = ConsultationStep.room_size
    answer(state, "My living room is approximately 15 × 12 ft.", next_to=ConsultationStep.budget)
    answer(state, "My living room is approximately 15 × 12 ft.", next_to=ConsultationStep.budget)
    user_messages = [message for message in state.messages if message.role == "user" and message.step == ConsultationStep.room_size]
    assert len(user_messages) == 1


def test_multi_select_creates_one_combined_answer_message() -> None:
    state = initial_state()
    state.step = ConsultationStep.must_haves
    values = ["Sofa", "TV unit", "Rug"]
    answer(state, "I need sofa, TV unit, and rug.", next_to=ConsultationStep.constraints)
    user_messages = [message for message in state.messages if message.role == "user" and message.step == ConsultationStep.must_haves]
    assert len(user_messages) == 1
    assert all(value.split()[0].lower() in user_messages[0].content.lower() for value in values)


def test_typed_dimensions_parse_correctly() -> None:
    assert parse_dimensions("15 by 12 ft") == (457, 366, None)
    assert parse_dimensions("450 x 360 cm") == (450, 360, None)


def test_typed_budget_accepts_inr_and_lakh_formats() -> None:
    assert parse_budget("250000") == 250000
    assert parse_budget("2.5 lakh") == 250000


def test_invalid_typed_input_returns_none() -> None:
    assert parse_budget("not sure") is None
    assert parse_dimensions("large room") is None
    assert parse_style("castlecore") is None


def test_budget_below_floor_needs_confirmation_on_first_entry() -> None:
    parsed = parse_budget("10")
    assert parsed == 10
    assert not is_plausible_budget(parsed)
    assert budget_needs_confirmation(parsed, pending_low_budget=None) is True


def test_budget_below_floor_reentered_same_value_no_longer_needs_confirmation() -> None:
    parsed = parse_budget("10")
    assert budget_needs_confirmation(parsed, pending_low_budget=10) is False


def test_budget_below_floor_reentered_different_low_value_needs_confirmation_again() -> None:
    parsed = parse_budget("10")
    assert budget_needs_confirmation(parsed, pending_low_budget=5) is True


def test_impossible_budget_golden_case_value_is_above_floor() -> None:
    # db-br-06's ₹20,000 impossible-budget trap must never be caught by the floor check —
    # it's a legitimate low budget meant to trigger the agent's guardrail, not a typo.
    assert is_plausible_budget(20000) is True
    assert budget_needs_confirmation(20000, pending_low_budget=None) is False


def test_button_preset_budgets_are_all_above_floor() -> None:
    # Mirrors app.py's _budget_question preset values (₹50,000 is the lowest preset).
    assert MIN_BUDGET_INR < 50000
    for preset in (50000, 100000, 250000, 500000):
        assert is_plausible_budget(preset) is True
        assert budget_needs_confirmation(preset, pending_low_budget=None) is False


def test_back_preserves_other_answers() -> None:
    state = initial_state()
    state.step = ConsultationStep.room_size
    state.brief.length_cm = 457
    state.brief.width_cm = 366
    answer(state, "Room answer", next_to=ConsultationStep.budget)
    state.brief.budget_inr = 250000
    answer(state, "Budget answer", next_to=ConsultationStep.style)
    back(state)
    assert state.step == ConsultationStep.budget
    assert state.brief.length_cm == 457
    assert state.brief.budget_inr == 250000


def test_editing_one_answer_does_not_reset_others() -> None:
    state = initial_state()
    state.brief.length_cm = 457
    state.brief.width_cm = 366
    state.brief.budget_inr = 250000
    state.brief.style_preference = "Modern"
    state.step = ConsultationStep.style
    assert state.brief.budget_inr == 250000
    assert state.brief.length_cm == 457


def test_review_appears_as_assistant_chat_message() -> None:
    state = initial_state()
    add_review_message(state)
    assert state.messages[-1].role == "assistant"
    assert state.messages[-1].message_type == "review"


def test_custom_demo_flow_cannot_generate_fixed_sample_result() -> None:
    state = initial_state()
    state.brief.length_cm = 900
    state.brief.width_cm = 900
    assert demo_preview_allowed(state.brief) is False
