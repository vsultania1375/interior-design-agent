from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4


class ConsultationStep(str, Enum):
    welcome = "welcome"
    sample_or_custom = "sample_or_custom"
    room_size = "room_size"
    budget = "budget"
    style = "style"
    must_haves = "must_haves"
    constraints = "constraints"
    review = "review"
    generating = "generating"
    result = "result"


CUSTOMER_STEPS = [
    ConsultationStep.room_size,
    ConsultationStep.budget,
    ConsultationStep.style,
    ConsultationStep.must_haves,
    ConsultationStep.constraints,
]


STEP_ORDER = [
    ConsultationStep.welcome,
    ConsultationStep.sample_or_custom,
    ConsultationStep.room_size,
    ConsultationStep.budget,
    ConsultationStep.style,
    ConsultationStep.must_haves,
    ConsultationStep.constraints,
    ConsultationStep.review,
    ConsultationStep.generating,
    ConsultationStep.result,
]


@dataclass
class ChatMessage:
    id: str
    role: str
    content: str
    step: ConsultationStep
    message_type: str = "text"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class BriefState:
    room_type: str = "Living Room"
    length_cm: int | None = None
    width_cm: int | None = None
    ceiling_cm: int | None = None
    budget_inr: int | None = None
    style_preference: str = ""
    must_haves: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    customer_note: str = ""
    source_brief_id: str | None = None
    sample_name: str | None = None


@dataclass
class ConsultationState:
    step: ConsultationStep = ConsultationStep.welcome
    brief: BriefState = field(default_factory=BriefState)
    messages: list[ChatMessage] = field(default_factory=list)
    generated_result: Any | None = None
    developer_mode: bool = False
    active_tab: str = "Room Layout"
    answer_message_ids: dict[str, str] = field(default_factory=dict)
    step_answers: dict[str, dict[str, str]] = field(default_factory=dict)
    generation_requested: bool = False
    agent_running: bool = False
    pending_feedback: str = ""
    pending_low_budget: int | None = None

    @property
    def history(self) -> list[dict[str, str]]:
        return [{"role": message.role, "content": message.content} for message in self.messages]


def initial_state() -> ConsultationState:
    state = ConsultationState()
    append_message(
        state,
        "assistant",
        "Hi, I’ll help you create a practical living-room plan using real products that fit your room and budget.",
        ConsultationStep.welcome,
    )
    return state


def append_message(
    state: ConsultationState,
    role: str,
    content: str,
    step: ConsultationStep,
    *,
    message_type: str = "text",
    metadata: dict[str, Any] | None = None,
    stable_key: str | None = None,
) -> ChatMessage:
    if stable_key:
        existing_id = state.answer_message_ids.get(stable_key)
        if existing_id:
            for message in state.messages:
                if message.id == existing_id:
                    message.role = role
                    message.content = content
                    message.step = step
                    message.message_type = message_type
                    message.metadata = metadata or {}
                    return message
    message = ChatMessage(
        id=f"msg-{uuid4().hex[:10]}",
        role=role,
        content=content,
        step=step,
        message_type=message_type,
        metadata=metadata or {},
    )
    state.messages.append(message)
    if stable_key:
        state.answer_message_ids[stable_key] = message.id
    return message


def ensure_question_message(state: ConsultationState, step: ConsultationStep, text: str) -> None:
    append_message(state, "assistant", text, step, message_type="text", stable_key=f"question_{step.value}")


def record_step_answer(state: ConsultationState, question: str, answer_text: str, *, next_to: ConsultationStep | None = None) -> ConsultationState:
    state.step_answers[state.step.value] = {"question": question, "answer": answer_text}
    state.step = next_to or next_step(state.step)
    return state


def remove_answer_for_step(state: ConsultationState, step: ConsultationStep) -> None:
    state.step_answers.pop(step.value, None)


def next_step(step: ConsultationStep) -> ConsultationStep:
    index = STEP_ORDER.index(step)
    return STEP_ORDER[min(index + 1, len(STEP_ORDER) - 1)]


def previous_step(step: ConsultationStep) -> ConsultationStep:
    index = STEP_ORDER.index(step)
    return STEP_ORDER[max(index - 1, 0)]


def answer(state: ConsultationState, label: str, *, next_to: ConsultationStep | None = None) -> ConsultationState:
    append_message(state, "user", label, state.step, message_type="answer_summary", stable_key=state.step.value)
    state.step = next_to or next_step(state.step)
    return state


def back(state: ConsultationState) -> ConsultationState:
    previous = previous_step(state.step)
    state.step = previous
    remove_answer_for_step(state, previous)
    return state


def reset() -> ConsultationState:
    return initial_state()


def developer_mode_allowed(environ: dict[str, str], query_params: dict[str, Any] | None = None) -> bool:
    if environ.get("INTERIOR_SHOW_DEVELOPER_MODE") == "1":
        return True
    params = query_params or {}
    value = params.get("developer")
    if isinstance(value, list):
        value = value[0] if value else ""
    return str(value).lower() in {"1", "true", "yes"}


def feet_to_cm(value: float) -> int:
    return int(round(value * 30.48))


def populate_from_sample(state: ConsultationState, brief: dict[str, Any], sample_name: str) -> ConsultationState:
    state.brief = BriefState(
        room_type="Living Room",
        length_cm=int(brief["length_cm"]),
        width_cm=int(brief["width_cm"]),
        ceiling_cm=int(brief.get("ceiling_cm") or 0) or None,
        budget_inr=int(brief["budget_inr"]),
        style_preference=str(brief.get("style_preference") or ""),
        must_haves=[part.strip() for part in str(brief.get("must_haves") or "").split(",") if part.strip()],
        constraints=[str(brief.get("constraints") or "").strip()] if brief.get("constraints") else [],
        customer_note=str(brief.get("customer_note") or ""),
        source_brief_id=str(brief.get("brief_id") or ""),
        sample_name=sample_name,
    )
    append_message(state, "user", f"I’d like to try {sample_name}.", ConsultationStep.sample_or_custom, message_type="answer_summary", stable_key=ConsultationStep.sample_or_custom.value)
    append_message(state, "assistant", f"I’ve loaded a sample {state.brief.style_preference} living room.", ConsultationStep.review, message_type="text", stable_key="sample_loaded")
    state.step = ConsultationStep.result
    return state


def brief_ready(brief: BriefState) -> tuple[bool, list[str]]:
    missing: list[str] = []
    if not brief.length_cm or not brief.width_cm:
        missing.append("room size")
    if not brief.budget_inr:
        missing.append("budget")
    if not brief.style_preference:
        missing.append("style")
    if not brief.must_haves:
        missing.append("at least one must-have")
    return not missing, missing


def demo_preview_allowed(brief: BriefState) -> bool:
    return bool(brief.source_brief_id)


def review_qa_pairs(state: ConsultationState) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for step in CUSTOMER_STEPS:
        entry = state.step_answers.get(step.value)
        if entry:
            pairs.append((entry["question"], entry["answer"]))
    return pairs


def add_submitted_answers_message(state: ConsultationState, qa_pairs: list[tuple[str, str]]) -> None:
    lines = [f"Q: {question}\nA: {answer_text}" for question, answer_text in qa_pairs]
    append_message(
        state,
        "user",
        "\n\n".join(lines),
        state.step,
        message_type="answer_summary",
        stable_key="submitted_answers",
    )


def add_feedback_message(state: ConsultationState, feedback_text: str) -> None:
    # No stable_key: every feedback submission is its own new message.
    append_message(state, "user", feedback_text, state.step, message_type="feedback")


def add_review_message(state: ConsultationState, qa_pairs: list[tuple[str, str]] | None = None) -> None:
    lines = ["Great — here’s what I understood."]
    for question, answer_text in qa_pairs or []:
        lines.append(f"Q: {question}\nA: {answer_text}")
    append_message(
        state,
        "assistant",
        "\n\n".join(lines),
        ConsultationStep.review,
        message_type="review",
        stable_key="review",
    )


def add_result_message(state: ConsultationState, summary_text: str | None = None) -> None:
    # No stable_key: each generation (including a later regeneration after user
    # feedback) appends a fresh message rather than overwriting the prior one.
    append_message(
        state,
        "assistant",
        summary_text or "Your room plan is ready.",
        ConsultationStep.result,
        message_type="result",
    )


def step_number(step: ConsultationStep) -> int:
    if step in {ConsultationStep.welcome, ConsultationStep.sample_or_custom}:
        return 1
    if step in CUSTOMER_STEPS:
        return CUSTOMER_STEPS.index(step) + 1
    return 5


def to_agent_brief(brief: BriefState) -> dict[str, Any]:
    return {
        "brief_id": brief.source_brief_id or "UI-LIVING-ROOM",
        "room_type": "Living Room",
        "length_cm": int(brief.length_cm or 0),
        "width_cm": int(brief.width_cm or 0),
        "ceiling_cm": int(brief.ceiling_cm or 0),
        "budget_inr": int(brief.budget_inr or 0),
        "style_preference": brief.style_preference,
        "must_haves": ", ".join(brief.must_haves),
        "constraints": ", ".join(brief.constraints),
        "customer_note": brief.customer_note,
    }
