from __future__ import annotations

from html import escape
from typing import Iterable

import streamlit as st

from .state import ChatMessage, ConsultationStep, step_number


START_CHOICES = [
    ("Design my own room", "Answer five quick questions about your space."),
    ("Try a demo room", "Preview a ready-made living-room plan."),
]


def render_message(message: ChatMessage) -> None:
    role_class = "user" if message.role == "user" else "assistant"
    st.markdown(
        f'<div class="chat-row {role_class}"><div class="chat-bubble {role_class}">{escape(message.content)}</div></div>',
        unsafe_allow_html=True,
    )


def render_messages(messages: Iterable[ChatMessage]) -> None:
    for message in messages:
        if message.message_type in {"review", "result"}:
            render_message(message)
        elif message.role in {"assistant", "user"}:
            render_message(message)


def render_qa_summary_card(qa_pairs: list[tuple[str, str]]) -> None:
    pairs_html = "".join(
        f'<div class="qa-pair"><div class="qa-question">Q: {escape(question)}</div>'
        f'<div class="qa-answer">A: {escape(answer)}</div></div>'
        for question, answer in qa_pairs
    )
    st.markdown(
        '<div class="qa-summary-card">'
        '<div class="qa-summary-intro">Here’s what I understood about your room.</div>'
        f'{pairs_html}'
        '</div>',
        unsafe_allow_html=True,
    )


def render_question_shell(step: ConsultationStep, title: str, helper: str = "") -> None:
    number = step_number(step)
    container = st.container(key=f"active_card_{step.value}", border=True)
    container.__enter__()
    st.session_state["_active_card_cm"] = container
    st.markdown(
        f'<div class="active-head"><span>{escape(title)}</span><span>{number} of 5</span></div>',
        unsafe_allow_html=True,
    )
    if helper:
        st.markdown(f'<div class="active-helper">{escape(helper)}</div>', unsafe_allow_html=True)


def close_question_shell() -> None:
    container = st.session_state.pop("_active_card_cm", None)
    if container is not None:
        container.__exit__(None, None, None)
