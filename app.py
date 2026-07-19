from __future__ import annotations

import os
import sys
from html import escape
from pathlib import Path
from typing import Any

import streamlit as st
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
DEMO_MODE = os.getenv("INTERIOR_UI_DEMO_MODE") == "1"
if not DEMO_MODE and os.getenv("INTERIOR_SKIP_DOTENV") != "1":
    load_dotenv(PROJECT_ROOT / ".env")

from interior_agent.agent import InteriorDesignAgent  # noqa: E402
from interior_agent.config import ConfigurationError, Settings  # noqa: E402
from interior_agent.db import CatalogRepository  # noqa: E402
from interior_agent.schemas import BOQLine, TraceEntry  # noqa: E402
from interior_agent.tools import AgentTools  # noqa: E402
from interior_agent.ui.chat import START_CHOICES, close_question_shell, render_messages, render_question_shell  # noqa: E402
from interior_agent.ui.demo import make_demo_result  # noqa: E402
from interior_agent.ui.input_parser import parse_budget, parse_dimensions, parse_multi_value_text, parse_style  # noqa: E402
from interior_agent.ui.layout import generate_living_room_layout, render_layout_svg  # noqa: E402
from interior_agent.ui.presenter import availability_copy, brief_summary, format_inr, line_total_copy, normal_result_text, price_copy, sample_display_name  # noqa: E402
from interior_agent.ui.state import ConsultationStep, add_result_message, add_review_message, answer, back, brief_ready, demo_preview_allowed, developer_mode_allowed, initial_state, populate_from_sample, reset, to_agent_brief  # noqa: E402
from interior_agent.validator import PlanValidator  # noqa: E402


st.set_page_config(page_title="Interior Planner", page_icon="home", layout="wide", initial_sidebar_state="collapsed")


def _css() -> None:
    st.markdown(
        """
        <style>
        #MainMenu, footer, header, [data-testid="stToolbar"], [data-testid="stDecoration"], [data-testid="stStatusWidget"] { display:none !important; }
        .stApp { background:#f6f1e9; color:#26221e; }
        .block-container { padding:.55rem 1.1rem 1.4rem; max-width:1180px; }
        [data-testid="stSidebar"] { display:none; }
        .topbar { display:flex; justify-content:space-between; align-items:center; min-height:38px; margin-bottom:.45rem; }
        .brand { display:flex; align-items:center; gap:.55rem; font-weight:760; font-size:1rem; }
        .mark { width:28px; height:28px; border-radius:9px; background:#2f6b4f; color:white; display:inline-flex; align-items:center; justify-content:center; font-size:14px; }
        .preview-mode { color:#736a60; font-size:.82rem; margin-right:.6rem; }
        .app-grid { align-items:start; }
        .chat-panel, .side-panel, .result-card, .product-card { background:#fffdf9; border:1px solid #e4dbcf; border-radius:16px; box-shadow:0 14px 34px rgba(71,55,38,.07); }
        .chat-panel { padding:.85rem; min-height:660px; display:flex; flex-direction:column; }
        .side-panel { padding:.85rem; }
        .intro { padding:.35rem .2rem .55rem; }
        .intro h1 { font-size:1.55rem; margin:.1rem 0 .25rem; line-height:1.08; }
        .intro p { color:#695f55; margin:0; font-size:.94rem; }
        .trust-row { display:flex; flex-wrap:wrap; gap:.35rem; margin-top:.5rem; }
        .pill, .badge { display:inline-flex; align-items:center; border:1px solid #ded5c9; border-radius:999px; padding:.22rem .52rem; background:#fffaf3; color:#5d544a; font-size:.78rem; }
        .badge-green { background:#edf8f0; border-color:#b8ddc0; color:#27633a; }
        .badge-amber { background:#fff8e5; border-color:#e7ce91; color:#725617; }
        .badge-red { background:#fff0ee; border-color:#ebb5ad; color:#8a2f24; }
        .messages { display:flex; flex-direction:column; gap:.42rem; margin:.2rem 0 .62rem; }
        .chat-row { display:flex; }
        .chat-row.user { justify-content:flex-end; }
        .chat-bubble { max-width:82%; border-radius:15px; padding:.48rem .68rem; font-size:.92rem; line-height:1.34; }
        .chat-bubble.assistant { background:#f7f0e7; color:#2b2621; border:1px solid #eadfd2; border-bottom-left-radius:6px; }
        .chat-bubble.user { background:#2f6b4f; color:white; border-bottom-right-radius:6px; }
        .active-card { border:1px solid #ded5c9; background:#fffaf4; border-radius:16px; padding:.75rem; margin:.2rem 0 .55rem; }
        .active-head { display:flex; justify-content:space-between; gap:1rem; color:#28231f; font-weight:780; font-size:1.05rem; }
        .active-head span:last-child { color:#2f6b4f; font-size:.82rem; white-space:nowrap; }
        .active-helper { color:#746b60; font-size:.86rem; margin:.18rem 0 .52rem; }
        div.stButton > button { border-radius:12px; border:1px solid #ded5c9; background:#fffefb; color:#28231f; min-height:2.55rem; box-shadow:0 5px 13px rgba(71,55,38,.04); font-size:.9rem; line-height:1.17; white-space:pre-wrap; text-align:left; padding:.42rem .62rem; }
        div.stButton > button:hover, div.stButton > button:focus { border-color:#2f6b4f; box-shadow:0 0 0 3px rgba(47,107,79,.13); color:#20392d; }
        div.stButton > button[kind="primary"] { background:#2f6b4f; border-color:#2f6b4f; color:white; text-align:center; min-height:2.55rem; }
        .top-action div.stButton > button { min-height:2.25rem; box-shadow:none; background:#fffaf3; font-size:.82rem; text-align:center; padding:.3rem .6rem; }
        .row-button div.stButton > button { width:100%; min-height:2.7rem; }
        .composer { margin-top:auto; border-top:1px solid #efe5d9; padding-top:.55rem; }
        .composer div.stTextInput input { border-radius:999px !important; border-color:#ded5c9 !important; background:#fffefb !important; min-height:2.55rem; }
        .compact-note { color:#746b60; font-size:.8rem; margin:.3rem 0 0; }
        .side-title { color:#2f6b4f; font-weight:780; font-size:.95rem; margin-bottom:.15rem; }
        .side-copy { color:#736a60; font-size:.86rem; margin-bottom:.55rem; }
        .kv { display:flex; justify-content:space-between; gap:.75rem; padding:.31rem 0; border-bottom:1px solid #efe7dc; font-size:.88rem; }
        .kv:last-child { border-bottom:0; }
        .kv span:first-child { color:#736a5f; }
        .kv span:last-child { text-align:right; font-weight:690; color:#2f2923; }
        .placeholder-room { height:145px; border:1px dashed #d8cfc3; border-radius:14px; background:linear-gradient(135deg,#fffdf9,#f7f0e6); display:flex; align-items:center; justify-content:center; color:#6d6358; text-align:center; padding:.8rem; font-size:.88rem; margin-top:.55rem; }
        .room-sketch { width:96px; height:66px; border:2px solid #d6c7b4; border-radius:10px; margin:0 auto .45rem; position:relative; }
        .room-sketch:after { content:""; position:absolute; width:32px; height:19px; border:2px solid #b8a78f; border-radius:7px; left:30px; top:22px; }
        .review-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:.4rem; margin:.45rem 0 .65rem; }
        .review-cell { background:#fffdf9; border:1px solid #eee3d7; border-radius:12px; padding:.45rem .55rem; }
        .review-label { color:#746b60; font-size:.74rem; margin-bottom:.08rem; }
        .review-value { color:#2f2923; font-size:.9rem; font-weight:700; line-height:1.2; }
        .result-card { padding:.8rem; margin:.55rem 0; }
        .product-card { padding:.7rem; margin-bottom:.5rem; }
        .product-title { font-weight:780; font-size:.97rem; }
        .product-meta { color:#746b60; font-size:.82rem; }
        .shape-icon { width:30px; height:21px; display:inline-block; border-radius:7px; background:#d8b980; border:1px solid #a88b50; vertical-align:middle; margin-right:.42rem; }
        div[data-baseweb="textarea"] textarea, div[data-baseweb="input"] input { border-radius:12px !important; border-color:#ded5c9 !important; background:#fffefb !important; }
        div[data-baseweb="tab-list"] { gap:.35rem; border-bottom:1px solid #e7ded3; }
        button[data-baseweb="tab"] { border-radius:999px 999px 0 0; padding:.42rem .75rem; color:#5d544a; }
        button[data-baseweb="tab"][aria-selected="true"] { color:#2f6b4f; background:#fffdf9; }
        @media (max-width:760px) {
          .block-container { padding:.55rem .8rem 1rem; }
          .chat-panel { min-height:auto; }
          .review-grid { grid-template-columns:1fr; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _state():
    if "consultation" not in st.session_state:
        st.session_state["consultation"] = initial_state()
    return st.session_state["consultation"]


def _set_state(state) -> None:
    st.session_state["consultation"] = state
    st.rerun()


def _living_room_briefs(repo: CatalogRepository) -> list[dict[str, Any]]:
    return [brief for brief in repo.list_briefs() if str(brief.get("room_type", "")).lower() == "living room"]


def _choice(title: str, description: str, key: str, *, primary: bool = False) -> bool:
    return st.button(f"{title}\n{description}", key=key, type="primary" if primary else "secondary", use_container_width=True)


def _topbar(state, demo_mode: bool, developer_available: bool) -> None:
    left, right = st.columns([1, 1])
    with left:
        st.markdown('<div class="topbar"><div class="brand"><span class="mark">⌂</span><span>Interior Planner</span></div></div>', unsafe_allow_html=True)
    with right:
        a, b = st.columns([1, .36])
        with a:
            if demo_mode:
                st.markdown('<div style="text-align:right;"><span class="preview-mode">Preview mode</span></div>', unsafe_allow_html=True)
        with b:
            st.markdown('<div class="top-action">', unsafe_allow_html=True)
            if st.button("Start over", key="top_start_over", use_container_width=True):
                _set_state(reset())
            st.markdown("</div>", unsafe_allow_html=True)
    if developer_available:
        st.session_state["developer_mode_enabled"] = st.toggle("Developer Mode", value=st.session_state.get("developer_mode_enabled", False))
    else:
        st.session_state["developer_mode_enabled"] = False


def _intro() -> None:
    st.markdown(
        """
        <div class="intro">
          <h1>Design your living room in 3 minutes</h1>
          <p>Answer a few simple questions. We’ll create a practical plan using real products that fit your room and budget.</p>
          <div class="trust-row">
            <span class="pill">Real catalog products</span>
            <span class="pill">Budget checked</span>
            <span class="pill">Room fit checked</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _messages(state) -> None:
    st.markdown('<div class="messages">', unsafe_allow_html=True)
    render_messages(state.messages)
    st.markdown("</div>", unsafe_allow_html=True)


def _welcome_question(state) -> None:
    render_question_shell(ConsultationStep.room_size, "How would you like to begin?", "Choose the path that fits your visit today.")
    col_a, col_b = st.columns(2)
    with col_a:
        if _choice(START_CHOICES[0][0], START_CHOICES[0][1], "start_custom", primary=True):
            answer(state, "I want to design my own living room.", next_to=ConsultationStep.room_size)
            _set_state(state)
    with col_b:
        if _choice(START_CHOICES[1][0], START_CHOICES[1][1], "start_demo"):
            answer(state, "I want to try a demo room.", next_to=ConsultationStep.sample_or_custom)
            _set_state(state)
    close_question_shell()


def _sample_question(state, repo: CatalogRepository) -> None:
    render_question_shell(ConsultationStep.room_size, "Choose a demo living room", "Preview a ready-made room plan without using credits.")
    for index, brief in enumerate(_living_room_briefs(repo)[:6]):
        name = sample_display_name(brief)
        requirements = ", ".join([part.strip() for part in str(brief.get("must_haves") or "").split(",") if part.strip()][:3])
        if _choice(name, f"{brief['length_cm']} × {brief['width_cm']} cm · {brief.get('style_preference')} · {format_inr(brief.get('budget_inr'))} · {requirements}", f"sample_{index}", primary=index == 0):
            populate_from_sample(state, brief, name)
            state.generated_result = make_demo_result(repo, to_agent_brief(state.brief))
            add_result_message(state)
            _set_state(state)
    close_question_shell()


def _room_question(state) -> None:
    render_question_shell(ConsultationStep.room_size, "How large is your living room?", "Select a size or type exact measurements below.")
    sizes = [
        ("Small", "Around 10 × 10 ft", 10, 10),
        ("Medium", "Around 12 × 15 ft", 15, 12),
        ("Large", "Around 15 × 18 ft", 18, 15),
        ("I’m not sure", "Use a practical starter size", 12, 10),
    ]
    cols = st.columns(2)
    for index, (title, desc, length_ft, width_ft) in enumerate(sizes):
        with cols[index % 2]:
            if _choice(title, desc, f"room_{index}", primary=index == 1):
                state.brief.length_cm = int(round(length_ft * 30.48))
                state.brief.width_cm = int(round(width_ft * 30.48))
                answer(state, f"My living room is approximately {length_ft} × {width_ft} ft.", next_to=ConsultationStep.budget)
                _set_state(state)
    with st.expander("Enter exact measurements"):
        unit = st.radio("Unit", ["feet", "cm"], horizontal=True, key="exact_unit")
        c1, c2, c3 = st.columns(3)
        length = c1.number_input("Length", min_value=1.0, value=15.0 if unit == "feet" else 455.0, step=.5)
        width = c2.number_input("Width", min_value=1.0, value=12.0 if unit == "feet" else 365.0, step=.5)
        ceiling = c3.number_input("Ceiling optional", min_value=0.0, value=0.0, step=.5)
        if st.button("Use measurements", key="use_exact", type="primary"):
            parsed = parse_dimensions(f"{length} x {width} {ceiling if ceiling else ''} {unit}")
            if parsed:
                state.brief.length_cm, state.brief.width_cm, state.brief.ceiling_cm = parsed
                answer(state, f"My living room is approximately {length:g} × {width:g} {unit}.", next_to=ConsultationStep.budget)
                _set_state(state)
    close_question_shell()


def _budget_question(state) -> None:
    render_question_shell(ConsultationStep.budget, "What total budget should I work within?", "I’ll avoid silently exceeding this budget.")
    options = [
        ("Under ₹50,000", "Starter essentials", 50000),
        ("₹50,000–₹1,00,000", "Compact room plan", 100000),
        ("₹1,00,000–₹2,50,000", "Balanced complete room", 250000),
        ("₹2,50,000–₹5,00,000", "Premium finish", 500000),
    ]
    cols = st.columns(2)
    for index, (title, desc, value) in enumerate(options):
        with cols[index % 2]:
            if _choice(title, desc, f"budget_{value}", primary=value == 250000):
                state.brief.budget_inr = value
                answer(state, f"My total budget is {format_inr(value)}.", next_to=ConsultationStep.style)
                st.session_state["assistant_budget_note"] = True
                _set_state(state)
    with st.expander("Enter another amount"):
        amount = st.text_input("Budget", placeholder="Example: 2.5 lakh")
        if st.button("Use budget", key="use_budget", type="primary"):
            parsed = parse_budget(amount)
            if parsed:
                state.brief.budget_inr = parsed
                answer(state, f"My total budget is {format_inr(parsed)}.", next_to=ConsultationStep.style)
                _set_state(state)
            else:
                st.error("Please enter a budget such as 250000 or 2.5 lakh.")
    close_question_shell()


def _style_question(state) -> None:
    render_question_shell(ConsultationStep.style, "What kind of look do you prefer?", "Choose the closest style direction.")
    styles = [
        ("Scandinavian", "Light woods, soft neutrals, and uncluttered forms."),
        ("Modern", "Clean lines and practical comfort."),
        ("Minimal", "Fewer pieces and airy spacing."),
        ("Mid-Century", "Warm wood and classic low profiles."),
        ("Bohemian", "Texture, rugs, plants, and warmth."),
        ("Industrial", "Metal, wood, and deeper tones."),
        ("Not sure — suggest one", "Use a practical direction."),
    ]
    cols = st.columns(2)
    for index, (title, desc) in enumerate(styles):
        with cols[index % 2]:
            if _choice(title, desc, f"style_{index}", primary=index == 0):
                style = "Scandinavian" if title.startswith("Not sure") else title
                state.brief.style_preference = style
                answer(state, f"I prefer a {style} look.", next_to=ConsultationStep.must_haves)
                _set_state(state)
    close_question_shell()


def _requirements_question(state) -> None:
    render_question_shell(ConsultationStep.must_haves, "What must the room include?", "Choose all that matter, then continue.")
    options = ["Sofa", "Coffee table", "TV unit", "Rug", "Lighting", "Storage", "Reading chair", "Side table", "Plants", "Something else"]
    current = set(state.brief.must_haves)
    cols = st.columns(2)
    for index, option in enumerate(options):
        with cols[index % 2]:
            selected = option in current
            if st.button(("✓ " if selected else "") + option, key=f"req_{index}", type="primary" if selected else "secondary", use_container_width=True):
                if selected:
                    current.remove(option)
                else:
                    current.add(option)
                state.brief.must_haves = list(current)
                _set_state(state)
    other = ""
    if "Something else" in current:
        other = st.text_input("What else should be included?", key="req_other")
    if st.button("Continue", key="req_continue", type="primary"):
        values = [item for item in state.brief.must_haves if item != "Something else"]
        if other.strip():
            values.append(other.strip())
        if not values:
            st.error("Choose at least one requirement to continue.")
        else:
            state.brief.must_haves = values
            answer(state, "I need " + _join_list(values) + ".", next_to=ConsultationStep.constraints)
            _set_state(state)
    close_question_shell()


def _context_question(state) -> None:
    render_question_shell(ConsultationStep.constraints, "Anything important about how you use the room?", "Select any that apply or add a short note.")
    options = ["We have young children", "We have pets", "It is a rented home", "We need more storage", "We entertain guests", "Fast delivery matters", "No special constraint"]
    current = set(state.brief.constraints)
    cols = st.columns(2)
    for index, option in enumerate(options):
        with cols[index % 2]:
            selected = option in current
            if st.button(("✓ " if selected else "") + option, key=f"ctx_{index}", type="primary" if selected else "secondary", use_container_width=True):
                if option == "No special constraint":
                    current = set() if selected else {option}
                elif selected:
                    current.remove(option)
                else:
                    current.discard("No special constraint")
                    current.add(option)
                state.brief.constraints = list(current)
                _set_state(state)
    note = st.text_area("Optional note", value=state.brief.customer_note, height=70)
    if st.button("Review my answers", key="ctx_continue", type="primary"):
        state.brief.constraints = [] if "No special constraint" in current else list(current)
        state.brief.customer_note = note.strip()
        text = "There is no special context." if not state.brief.constraints and not state.brief.customer_note else "Important context: " + _join_list(state.brief.constraints + ([state.brief.customer_note] if state.brief.customer_note else [])) + "."
        answer(state, text, next_to=ConsultationStep.review)
        add_review_message(state)
        _set_state(state)
    close_question_shell()


def _review_question(state, can_run_live: bool) -> None:
    render_question_shell(ConsultationStep.review, "Great — here’s what I understood.", "Create your plan or change one answer.")
    _review_grid(state)
    ready, _ = brief_ready(state.brief)
    c1, c2 = st.columns([.58, .42])
    with c1:
        disabled = not ready or (DEMO_MODE and not demo_preview_allowed(state.brief)) or (not DEMO_MODE and not can_run_live) or state.agent_running or state.generated_result is not None
        if st.button("Create my room plan", key="create_plan", type="primary", disabled=disabled, use_container_width=True):
            state.generation_requested = True
            state.step = ConsultationStep.generating
            _set_state(state)
    with c2:
        if st.button("Change an answer", key="change_answer", use_container_width=True):
            st.session_state["show_edit_selector"] = True
    if DEMO_MODE and ready and not demo_preview_allowed(state.brief):
        st.markdown('<div class="compact-note">Custom plan generation is available in live mode.</div>', unsafe_allow_html=True)
    if st.session_state.get("show_edit_selector"):
        cols = st.columns(5)
        targets = [
            ("Room", ConsultationStep.room_size),
            ("Budget", ConsultationStep.budget),
            ("Style", ConsultationStep.style),
            ("Requirements", ConsultationStep.must_haves),
            ("Context", ConsultationStep.constraints),
        ]
        for index, (label, step) in enumerate(targets):
            with cols[index]:
                if st.button(label, key=f"edit_{label}"):
                    state.step = step
                    st.session_state["show_edit_selector"] = False
                    _set_state(state)
    close_question_shell()


def _review_grid(state) -> None:
    cells = []
    for label, value in brief_summary(state.brief):
        cells.append(f'<div class="review-cell"><div class="review-label">{escape(label)}</div><div class="review-value">{escape(value)}</div></div>')
    if state.brief.customer_note:
        cells.append(f'<div class="review-cell"><div class="review-label">Extra note</div><div class="review-value">{escape(state.brief.customer_note)}</div></div>')
    st.markdown('<div class="review-grid">' + "".join(cells) + "</div>", unsafe_allow_html=True)


def _composer(state) -> None:
    if state.step in {ConsultationStep.sample_or_custom, ConsultationStep.generating, ConsultationStep.result}:
        return
    st.markdown('<div class="composer">', unsafe_allow_html=True)
    c1, c2 = st.columns([.82, .18])
    with c1:
        typed = st.text_input("Typed answer", placeholder="Or type your answer…", label_visibility="collapsed", key=f"composer_{state.step.value}")
    with c2:
        sent = st.button("Send", key=f"send_{state.step.value}", type="primary", use_container_width=True)
    if sent:
        _handle_typed_answer(state, typed)
    st.markdown("</div>", unsafe_allow_html=True)


def _handle_typed_answer(state, typed: str) -> None:
    text = typed.strip()
    if not text:
        return
    if state.step == ConsultationStep.welcome:
        if "demo" in text.lower() or "example" in text.lower():
            answer(state, "I want to try a demo room.", next_to=ConsultationStep.sample_or_custom)
        else:
            answer(state, "I want to design my own living room.", next_to=ConsultationStep.room_size)
    elif state.step == ConsultationStep.room_size:
        parsed = parse_dimensions(text)
        if not parsed:
            st.error("Please enter dimensions like 15 by 12 ft or 450 x 360 cm.")
            return
        state.brief.length_cm, state.brief.width_cm, state.brief.ceiling_cm = parsed
        answer(state, f"My living room is {escape(text)}.", next_to=ConsultationStep.budget)
    elif state.step == ConsultationStep.budget:
        parsed = parse_budget(text)
        if not parsed:
            st.error("Please enter a budget such as 250000 or 2.5 lakh.")
            return
        state.brief.budget_inr = parsed
        answer(state, f"My total budget is {format_inr(parsed)}.", next_to=ConsultationStep.style)
    elif state.step == ConsultationStep.style:
        parsed = parse_style(text)
        if not parsed:
            st.error("Choose one of the listed styles or type a close match.")
            return
        state.brief.style_preference = parsed
        answer(state, f"I prefer a {parsed} look.", next_to=ConsultationStep.must_haves)
    elif state.step == ConsultationStep.must_haves:
        values = parse_multi_value_text(text)
        if not values:
            st.error("Please enter at least one requirement.")
            return
        state.brief.must_haves = values
        answer(state, "I need " + _join_list(values) + ".", next_to=ConsultationStep.constraints)
    elif state.step == ConsultationStep.constraints:
        values = parse_multi_value_text(text)
        state.brief.customer_note = text
        answer(state, "Important context: " + _join_list(values or [text]) + ".", next_to=ConsultationStep.review)
        add_review_message(state)
    _set_state(state)


def _join_list(values: list[str]) -> str:
    clean = [value for value in values if value]
    if not clean:
        return ""
    if len(clean) == 1:
        return clean[0]
    return ", ".join(clean[:-1]) + ", and " + clean[-1]


def _progress_label(entry: TraceEntry) -> str:
    return {
        "search_catalog": "Searching suitable products",
        "check_budget": "Checking your budget",
        "check_fit": "Checking furniture fit",
    }.get(entry.tool, "Preparing your final plan")


def _run_generation(state, repo: CatalogRepository, settings: Settings, api_key: str, model: str) -> None:
    if state.generated_result is not None:
        state.step = ConsultationStep.result
        return
    if not state.generation_requested:
        state.step = ConsultationStep.review
        return
    state.agent_running = True
    progress = st.empty()
    brief = to_agent_brief(state.brief)
    try:
        if DEMO_MODE:
            if not demo_preview_allowed(state.brief):
                state.step = ConsultationStep.review
                return
            progress.write("Preparing your final plan")
            result = make_demo_result(repo, brief)
        else:
            append_message(state, "assistant", "Understanding your room", ConsultationStep.generating, message_type="progress", stable_key="progress_start")
            tools = AgentTools(repo)
            validator = PlanValidator(repo)
            agent = InteriorDesignAgent(
                tools=tools,
                validator=validator,
                api_key=api_key,
                model=model,
                max_iterations=settings.max_iterations,
                max_tokens=settings.anthropic_max_tokens,
            )

            def on_trace(entry: TraceEntry) -> None:
                append_message(state, "assistant", _progress_label(entry), ConsultationStep.generating, message_type="progress", stable_key=f"progress_{entry.tool}")
                progress.write(_progress_label(entry))

            result = agent.run(brief, on_trace=on_trace)
        state.generated_result = result
        add_result_message(state)
        state.step = ConsultationStep.result
    except Exception as exc:
        append_message(state, "assistant", "We couldn’t finish your plan right now. Your room details are still here.", ConsultationStep.generating, message_type="error", stable_key="generation_error")
        if st.session_state.get("developer_mode_enabled"):
            st.exception(exc)
        state.step = ConsultationStep.review
    finally:
        state.agent_running = False
        state.generation_requested = False
        _set_state(state)


def _catalog_records_for_boq(repo: CatalogRepository, lines: list[BOQLine]) -> list[dict[str, Any]]:
    records = repo.get_items(line.item_id for line in lines)
    items: list[dict[str, Any]] = []
    for line in lines:
        record = dict(records.get(line.item_id, {}))
        if record:
            record["quantity"] = line.quantity
            items.extend([record] * line.quantity)
    return items


def _result_sections(state, repo: CatalogRepository) -> None:
    result = state.generated_result
    if result is None:
        return
    validated = result.validated
    text = normal_result_text(validated)
    status_ok = validated.is_valid and validated.plan.status.value == "complete" and result.converged
    st.markdown('<div class="result-card">', unsafe_allow_html=True)
    st.markdown(f"<strong>{escape(text['title'])}</strong>")
    st.write(text["summary"])
    st.markdown(
        " ".join([
            f'<span class="badge {"badge-green" if validated.fit_result.get("fits") else "badge-amber"}">{"Fits your room" if validated.fit_result.get("fits") else "Fit needs review"}</span>',
            f'<span class="badge {"badge-green" if not validated.over_budget else "badge-red"}">{"Within budget" if not validated.over_budget else "Over budget"}</span>',
            f'<span class="badge {"badge-green" if status_ok else "badge-amber"}">{"Requirements covered" if status_ok else "Review trade-offs"}</span>',
        ]),
        unsafe_allow_html=True,
    )
    c1, c2, c3 = st.columns(3)
    c1.metric("Estimated cost", text["estimated_cost"])
    c2.metric(text["remaining_label"], text["remaining"])
    c3.metric("Products", text["product_count"])
    st.markdown("</div>", unsafe_allow_html=True)
    tab_layout, tab_shop, tab_budget, tab_details = st.tabs(["Room Layout", "Shopping List", "Budget", "Details"])
    with tab_layout:
        layout = generate_living_room_layout(
            int(validated.fit_result.get("room_length_cm") or state.brief.length_cm or 0),
            int(validated.fit_result.get("room_width_cm") or state.brief.width_cm or 0),
            _catalog_records_for_boq(repo, validated.boq),
        )
        st.markdown(render_layout_svg(layout), unsafe_allow_html=True)
        st.markdown('<div class="compact-note">Conceptual layout based on an empty rectangular room. Doors, windows, columns and electrical points are not represented. Confirm site conditions before purchase or installation.</div>', unsafe_allow_html=True)
    with tab_shop:
        for line in validated.boq:
            st.markdown('<div class="product-card">', unsafe_allow_html=True)
            st.markdown(f'<div class="product-title"><span class="shape-icon"></span>{escape(line.name)}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="product-meta">{escape(line.category)} • {escape(line.item_id)}</div>', unsafe_allow_html=True)
            cols = st.columns(3)
            cols[0].write(f"Quantity: **{line.quantity}**")
            cols[1].write(f"Price: **{price_copy(line)}**")
            cols[2].write(availability_copy(line))
            st.write(f"Dimensions: {line.dimensions_cm} cm")
            st.write(line.rationale)
            if line.placement_note:
                st.caption(line.placement_note)
            st.markdown("</div>", unsafe_allow_html=True)
    with tab_budget:
        budget = max(validated.plan.budget_inr, 1)
        st.progress(min(max(validated.known_total_inr, 0) / budget, 1.0), text=f"{format_inr(validated.known_total_inr)} of {format_inr(budget)}")
        for line in validated.boq:
            st.write(f"{line.category}: {line.name} × {line.quantity} — {line_total_copy(line)}")
        if validated.has_unknown_prices:
            st.warning("Price on request — not included in the estimated total.")
    with tab_details:
        for title, values in (
            ("Design rationale", [validated.plan.design_summary]),
            ("Layout instructions", [line.placement_note for line in validated.boq if line.placement_note]),
            ("Trade-offs", validated.plan.tradeoffs),
            ("Assumptions", validated.plan.assumptions),
            ("Warnings", validated.plan.flags),
            ("What needs a professional", [f"{decline.category}: {decline.message}" for decline in validated.plan.declined_scope]),
            ("Things to review", [issue.message for issue in validated.issues]),
        ):
            clean = [value for value in values if value]
            if clean:
                st.subheader(title)
                for value in clean:
                    st.write(f"- {value}")
    if st.session_state.get("developer_mode_enabled"):
        with st.expander("Developer trace and structured output"):
            st.write(f"Iterations: {result.iterations}; converged: {result.converged}")
            st.json([entry.model_dump(mode="json") for entry in result.trace])
            st.json(validated.model_dump(mode="json"))
            st.json(result.usage.as_dict())


def _side_panel(state, repo: CatalogRepository) -> None:
    st.markdown('<div class="side-panel">', unsafe_allow_html=True)
    st.markdown('<div class="side-title">Your room preview</div>', unsafe_allow_html=True)
    st.markdown('<div class="side-copy">Complete the consultation to build your plan.</div>', unsafe_allow_html=True)
    for label, value in brief_summary(state.brief):
        st.markdown(f'<div class="kv"><span>{escape(label)}</span><span>{escape(value)}</span></div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    if state.step == ConsultationStep.result and state.generated_result is not None:
        validated = state.generated_result.validated
        layout = generate_living_room_layout(
            int(validated.fit_result.get("room_length_cm") or state.brief.length_cm or 0),
            int(validated.fit_result.get("room_width_cm") or state.brief.width_cm or 0),
            _catalog_records_for_boq(repo, validated.boq),
        )
        st.markdown(render_layout_svg(layout, max_px=360, min_width=230, min_height=155), unsafe_allow_html=True)
    elif state.brief.length_cm and state.brief.width_cm:
        layout = generate_living_room_layout(state.brief.length_cm, state.brief.width_cm, [])
        st.markdown(render_layout_svg(layout, max_px=330, min_width=220, min_height=145), unsafe_allow_html=True)
        st.caption("Furniture placement will appear after your plan is created.")
    else:
        st.markdown(
            """
            <div class="placeholder-room">
              <div>
                <div class="room-sketch"></div>
                <strong>Add your room size to see the space take shape.</strong>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _active_question(state, repo: CatalogRepository, settings: Settings, api_key: str, model: str, can_run_live: bool) -> None:
    if state.step == ConsultationStep.welcome:
        _welcome_question(state)
    elif state.step == ConsultationStep.sample_or_custom:
        _sample_question(state, repo)
    elif state.step == ConsultationStep.room_size:
        _room_question(state)
    elif state.step == ConsultationStep.budget:
        _budget_question(state)
    elif state.step == ConsultationStep.style:
        _style_question(state)
    elif state.step == ConsultationStep.must_haves:
        _requirements_question(state)
    elif state.step == ConsultationStep.constraints:
        _context_question(state)
    elif state.step == ConsultationStep.review:
        _review_question(state, can_run_live)
    elif state.step == ConsultationStep.generating:
        _run_generation(state, repo, settings, api_key, model)


def main() -> None:
    _css()
    try:
        settings = Settings.from_env(PROJECT_ROOT)
        repo = CatalogRepository(settings.db_path)
    except (ConfigurationError, FileNotFoundError) as exc:
        st.error(f"Setup error: {exc}")
        st.stop()
    secret_key = None
    secret_model = None
    try:
        secret_key = st.secrets.get("ANTHROPIC_API_KEY")
        secret_model = st.secrets.get("ANTHROPIC_MODEL")
    except Exception:
        pass
    api_key = "" if DEMO_MODE else (secret_key or os.getenv("ANTHROPIC_API_KEY") or "")
    model = secret_model or settings.anthropic_model
    state = _state()
    developer_available = developer_mode_allowed(os.environ, dict(st.query_params))
    _topbar(state, DEMO_MODE, developer_available)
    left, right = st.columns([0.58, 0.42], gap="large")
    with left:
        st.markdown('<div class="chat-panel">', unsafe_allow_html=True)
        _intro()
        _messages(state)
        if state.step != ConsultationStep.result:
            _active_question(state, repo, settings, api_key, model, bool(api_key))
            if state.step not in {ConsultationStep.welcome, ConsultationStep.sample_or_custom, ConsultationStep.generating}:
                if st.button("Back", key="chat_back"):
                    _set_state(back(state))
        else:
            _result_sections(state, repo)
        _composer(state)
        st.markdown("</div>", unsafe_allow_html=True)
    with right:
        _side_panel(state, repo)


main()
