from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


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
    history: list[dict[str, str]] = field(default_factory=list)
    generated_result: Any | None = None
    developer_mode: bool = False
    active_tab: str = "Room Layout"


def initial_state() -> ConsultationState:
    return ConsultationState(history=[{
        "role": "assistant",
        "content": "Hi, I’ll help you create a practical living-room plan using real products that fit your room and budget.",
    }])


def next_step(step: ConsultationStep) -> ConsultationStep:
    index = STEP_ORDER.index(step)
    return STEP_ORDER[min(index + 1, len(STEP_ORDER) - 1)]


def previous_step(step: ConsultationStep) -> ConsultationStep:
    index = STEP_ORDER.index(step)
    return STEP_ORDER[max(index - 1, 0)]


def answer(state: ConsultationState, label: str, *, next_to: ConsultationStep | None = None) -> ConsultationState:
    state.history.append({"role": "user", "content": label})
    state.step = next_to or next_step(state.step)
    return state


def back(state: ConsultationState) -> ConsultationState:
    state.step = previous_step(state.step)
    if state.history and state.history[-1]["role"] == "user":
        state.history.pop()
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
    state.step = ConsultationStep.review
    state.history.append({"role": "user", "content": f"Try sample room: {sample_name}"})
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
