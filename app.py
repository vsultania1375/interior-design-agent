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
from interior_agent.ui.demo import make_demo_result  # noqa: E402
from interior_agent.ui.layout import generate_living_room_layout, render_layout_svg  # noqa: E402
from interior_agent.ui.presenter import availability_copy, brief_summary, format_inr, line_total_copy, normal_result_text, price_copy, sample_display_name  # noqa: E402
from interior_agent.ui.state import ConsultationStep, answer, back, brief_ready, demo_preview_allowed, developer_mode_allowed, feet_to_cm, initial_state, populate_from_sample, reset, to_agent_brief  # noqa: E402
from interior_agent.validator import PlanValidator  # noqa: E402


st.set_page_config(page_title="Interior Planner", page_icon="home", layout="wide", initial_sidebar_state="collapsed")


CUSTOMER_STEPS = {
    ConsultationStep.welcome: (1, "Room"),
    ConsultationStep.sample_or_custom: (1, "Room"),
    ConsultationStep.room_size: (1, "Room"),
    ConsultationStep.budget: (2, "Budget"),
    ConsultationStep.style: (3, "Style"),
    ConsultationStep.must_haves: (4, "Requirements"),
    ConsultationStep.constraints: (4, "Requirements"),
    ConsultationStep.review: (5, "Review"),
    ConsultationStep.generating: (5, "Review"),
    ConsultationStep.result: (5, "Review"),
}


def _css() -> None:
    st.markdown(
        """
        <style>
        #MainMenu, footer, header, [data-testid="stToolbar"], [data-testid="stDecoration"], [data-testid="stStatusWidget"] { display: none !important; }
        .stApp { background: #f6f1e9; color: #26221e; }
        .block-container { padding: .65rem 1.15rem 1.5rem; max-width: 1160px; }
        [data-testid="stSidebar"] { display: none; }
        .topbar { display:flex; justify-content:space-between; align-items:center; margin-bottom:.45rem; min-height:42px; }
        .brand { display:flex; align-items:center; gap:.55rem; font-weight:760; font-size:1rem; color:#292520; }
        .mark { width:28px; height:28px; border-radius:9px; background:#2f6b4f; display:inline-flex; align-items:center; justify-content:center; color:#fff; font-size:14px; }
        .preview-mode { color:#746b60; font-size:.82rem; margin-right:.5rem; line-height:2.3rem; }
        .hero { max-width: 940px; margin: .15rem auto .85rem; text-align:center; }
        .hero h1 { font-size: clamp(1.85rem, 4.4vw, 3.35rem); line-height:1.02; letter-spacing:0; margin:.1rem 0 .55rem; color:#24201c; }
        .hero p { font-size:1.02rem; color:#665d53; max-width:720px; margin:0 auto .65rem; }
        .trust-row { display:flex; justify-content:center; flex-wrap:wrap; gap:.38rem; }
        .trust-pill, .badge { display:inline-flex; align-items:center; border:1px solid #ded5c9; border-radius:999px; padding:.26rem .58rem; background:#fffaf3; color:#5d544a; font-size:.82rem; }
        .badge-green { background:#edf8f0; border-color:#b8ddc0; color:#27633a; }
        .badge-amber { background:#fff8e5; border-color:#e7ce91; color:#725617; }
        .badge-red { background:#fff0ee; border-color:#ebb5ad; color:#8a2f24; }
        .shell { align-items:start; }
        .question-card, .preview-card, .result-card, .product-card { background:#fffdf9; border:1px solid #e4dbcf; border-radius:16px; box-shadow:0 14px 34px rgba(71,55,38,.07); }
        .question-card { padding:.9rem 1rem; }
        .preview-card, .result-card { padding:.82rem .9rem; }
        .eyebrow { color:#2f6b4f; font-weight:760; font-size:.78rem; margin-bottom:.15rem; }
        .question-title { font-size:1.26rem; line-height:1.16; font-weight:780; margin:0 0 .22rem; color:#27221e; }
        .helper { color:#746b60; font-size:.92rem; margin-bottom:.65rem; }
        .history { display:flex; flex-wrap:wrap; gap:.32rem; margin-bottom:.55rem; }
        .history-chip { background:#eef5ef; color:#305b41; border:1px solid #c9decf; border-radius:999px; padding:.18rem .52rem; font-size:.78rem; }
        .step-line { display:flex; align-items:center; gap:.58rem; margin-bottom:.55rem; color:#746b60; font-size:.82rem; }
        .progress-track { flex:1; height:5px; border-radius:999px; background:#eadfd2; overflow:hidden; }
        .progress-fill { height:100%; background:#2f6b4f; border-radius:999px; }
        .option-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:.5rem; }
        .sample-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:.55rem; }
        div.stButton > button { border-radius:13px; border:1px solid #ded5c9; background:#fffefb; color:#28231f; min-height:2.85rem; box-shadow:0 6px 14px rgba(71,55,38,.045); font-size:.92rem; line-height:1.18; white-space:pre-wrap; text-align:left; padding:.48rem .72rem; }
        div.stButton > button:hover, div.stButton > button:focus { border-color:#2f6b4f; box-shadow:0 0 0 3px rgba(47,107,79,.13); color:#20392d; }
        div.stButton > button[kind="primary"] { background:#2f6b4f; border-color:#2f6b4f; color:white; text-align:center; min-height:2.85rem; }
        .top-action div.stButton > button { min-height:2.35rem; box-shadow:none; background:#fffaf3; border-color:#e0d8cf; font-size:.84rem; text-align:center; padding:.35rem .6rem; }
        .subtle-button div.stButton > button { min-height:2.15rem; box-shadow:none; background:transparent; border-color:transparent; color:#5d544a; text-align:center; padding:.25rem .45rem; }
        .compact-actions div.stButton > button { min-height:2.75rem; }
        .kv { display:flex; justify-content:space-between; gap:.75rem; padding:.32rem 0; border-bottom:1px solid #efe7dc; font-size:.9rem; }
        .kv:last-child { border-bottom:0; }
        .kv span:first-child { color:#736a5f; }
        .kv span:last-child { text-align:right; font-weight:690; color:#2f2923; }
        .review-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:.45rem .8rem; margin:.45rem 0 .7rem; }
        .review-cell { background:#fffaf3; border:1px solid #eee3d7; border-radius:12px; padding:.48rem .6rem; min-height:3.1rem; }
        .review-label { color:#746b60; font-size:.76rem; margin-bottom:.1rem; }
        .review-value { color:#2f2923; font-size:.93rem; font-weight:700; line-height:1.2; }
        .compact-note { color:#746b60; font-size:.82rem; margin:.35rem 0 0; }
        .placeholder-room { height:155px; border:1px dashed #d8cfc3; border-radius:14px; background:linear-gradient(135deg,#fffdf9,#f7f0e6); display:flex; align-items:center; justify-content:center; color:#6d6358; text-align:center; padding:.8rem; font-size:.92rem; }
        .room-sketch { width:104px; height:72px; border:2px solid #d6c7b4; border-radius:10px; margin:0 auto .55rem; position:relative; }
        .room-sketch:after { content:""; position:absolute; width:34px; height:20px; border:2px solid #b8a78f; border-radius:7px; left:33px; top:24px; }
        .product-card { padding:.75rem; margin-bottom:.55rem; }
        .product-title { font-weight:780; font-size:.98rem; margin-bottom:.05rem; }
        .product-meta { color:#746b60; font-size:.82rem; }
        .shape-icon { width:31px; height:22px; display:inline-block; border-radius:7px; background:#d8b980; border:1px solid #a88b50; vertical-align:middle; margin-right:.45rem; }
        div[data-baseweb="select"] > div, div[data-baseweb="textarea"] textarea, div[data-baseweb="input"] input { border-radius:12px !important; border-color:#ded5c9 !important; background:#fffefb !important; }
        div[data-baseweb="tab-list"] { gap:.35rem; border-bottom:1px solid #e7ded3; }
        button[data-baseweb="tab"] { border-radius:999px 999px 0 0; padding:.45rem .8rem; color:#5d544a; }
        button[data-baseweb="tab"][aria-selected="true"] { color:#2f6b4f; background:#fffdf9; }
        @media (max-width: 760px) {
          .block-container { padding-left:.9rem; padding-right:.9rem; }
          .hero { text-align:left; margin-top:.3rem; }
          .trust-row { justify-content:flex-start; }
          .option-grid, .sample-grid { grid-template-columns:1fr; }
          .topbar { margin-bottom:.8rem; }
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


def _option_card(title: str, description: str, *, key: str, primary: bool = False) -> bool:
    icon = "● " if primary else "○ "
    return st.button(f"{icon}{title}\n{description}", key=key, type="primary" if primary else "secondary", use_container_width=True)


def _step_indicator(step: ConsultationStep) -> None:
    number, label = CUSTOMER_STEPS[step]
    pct = min(number / 5, 1.0) * 100
    st.markdown(
        f'<div class="step-line"><span>Step {number} of 5 · {label}</span><div class="progress-track"><div class="progress-fill" style="width:{pct:.0f}%"></div></div></div>',
        unsafe_allow_html=True,
    )


def _render_topbar(state, demo_mode: bool, developer_available: bool) -> None:
    left, right = st.columns([1, 1])
    with left:
        st.markdown('<div class="topbar"><div class="brand"><span class="mark">⌂</span><span>Interior Planner</span></div></div>', unsafe_allow_html=True)
    with right:
        a, b = st.columns([1, 0.45])
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


def _render_hero() -> None:
    st.markdown(
        """
        <section class="hero">
          <h1>Design your living room in 3 minutes</h1>
          <p>Answer a few simple questions. We’ll create a practical plan using real products that fit your room and budget.</p>
          <div class="trust-row">
            <span class="trust-pill">Real catalog products</span>
            <span class="trust-pill">Budget checked</span>
            <span class="trust-pill">Room fit checked</span>
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def _render_history(state) -> None:
    user_entries = [entry["content"] for entry in state.history if entry["role"] == "user"]
    if not user_entries:
        return
    st.markdown('<div class="history">' + "".join(f'<span class="history-chip">{entry}</span>' for entry in user_entries[-4:]) + "</div>", unsafe_allow_html=True)


def _question_start(title: str, helper: str) -> None:
    st.markdown('<div class="question-card">', unsafe_allow_html=True)
    st.markdown('<div class="eyebrow">Interior Planner</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="question-title">{title}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="helper">{helper}</div>', unsafe_allow_html=True)


def _question_end() -> None:
    st.markdown("</div>", unsafe_allow_html=True)


def _render_welcome(state) -> None:
    _question_start("How would you like to begin?", "Let’s start with your room.")
    col_a, col_b = st.columns(2)
    with col_a:
        if _option_card("Design my room", "Answer a few quick questions about your space.", key="design_custom", primary=True):
            answer(state, "Design my room", next_to=ConsultationStep.room_size)
            _set_state(state)
    with col_b:
        if _option_card("Try an example", "Preview a ready-made living-room plan.", key="try_sample"):
            answer(state, "Try an example", next_to=ConsultationStep.sample_or_custom)
            _set_state(state)
    _question_end()


def _render_samples(state, repo: CatalogRepository) -> None:
    _question_start("Choose an example living room", "Each example uses a real room brief and real catalog-backed products.")
    st.markdown('<div class="sample-grid">', unsafe_allow_html=True)
    for index, brief in enumerate(_living_room_briefs(repo)):
        name = sample_display_name(brief)
        requirements = [part.strip() for part in str(brief.get("must_haves") or "").split(",") if part.strip()][:3]
        with st.container():
            st.markdown('<div class="product-card">', unsafe_allow_html=True)
            st.markdown(f"**{name}**")
            st.caption(f"{brief.get('style_preference')} · {brief['length_cm']} × {brief['width_cm']} cm · {format_inr(brief.get('budget_inr'))}")
            st.write(", ".join(requirements))
            if st.button("Use this room", key=f"sample_{index}", type="primary", use_container_width=True):
                _set_state(populate_from_sample(state, brief, name))
            st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    _question_end()


def _render_room_size(state) -> None:
    _question_start("How large is your living room?", "Pick a close size now; exact dimensions are optional.")
    options = [
        ("Small", "Around 10 × 10 ft", feet_to_cm(10), feet_to_cm(10)),
        ("Medium", "Around 12 × 15 ft", feet_to_cm(15), feet_to_cm(12)),
        ("Large", "Around 15 × 18 ft", feet_to_cm(18), feet_to_cm(15)),
        ("I’m not sure", "Use a practical starter size", feet_to_cm(12), feet_to_cm(10)),
    ]
    cols = st.columns(2)
    for index, (title, desc, length, width) in enumerate(options):
        with cols[index % 2]:
            if _option_card(title, desc, key=f"size_{index}", primary=index == 1):
                state.brief.length_cm = length
                state.brief.width_cm = width
                answer(state, f"{title} room", next_to=ConsultationStep.budget)
                _set_state(state)
    with st.expander("Enter exact measurements"):
        unit = st.radio("Unit", ["feet", "cm"], horizontal=True, key="size_unit")
        col_l, col_w, col_c = st.columns(3)
        length = col_l.number_input("Length", min_value=1.0, value=12.0 if unit == "feet" else 365.0, step=0.5)
        width = col_w.number_input("Width", min_value=1.0, value=15.0 if unit == "feet" else 455.0, step=0.5)
        ceiling = col_c.number_input("Ceiling optional", min_value=0.0, value=0.0, step=0.5)
        if st.button("Use these measurements", key="exact_measurements", type="primary"):
            state.brief.length_cm = feet_to_cm(length) if unit == "feet" else int(round(length))
            state.brief.width_cm = feet_to_cm(width) if unit == "feet" else int(round(width))
            state.brief.ceiling_cm = None if ceiling <= 0 else (feet_to_cm(ceiling) if unit == "feet" else int(round(ceiling)))
            answer(state, f"{state.brief.length_cm} × {state.brief.width_cm} cm", next_to=ConsultationStep.budget)
            _set_state(state)
    _question_end()


def _render_budget(state) -> None:
    _question_start("What total budget should I work within?", "I’ll avoid silently exceeding this budget.")
    options = [
        ("Under ₹50,000", "Starter essentials", 50000),
        ("₹50,000–₹1,00,000", "Compact room plan", 100000),
        ("₹1,00,000–₹2,50,000", "Balanced complete room", 250000),
        ("₹2,50,000–₹5,00,000", "Premium finish", 500000),
    ]
    cols = st.columns(2)
    for index, (title, desc, value) in enumerate(options):
        with cols[index % 2]:
            if _option_card(title, desc, key=f"budget_{value}", primary=value == 250000):
                state.brief.budget_inr = value
                answer(state, title, next_to=ConsultationStep.style)
                _set_state(state)
    with st.expander("Enter another amount"):
        amount = st.number_input("Budget in INR", min_value=1000, value=int(state.brief.budget_inr or 150000), step=5000)
        if st.button("Use this budget", key="custom_budget", type="primary"):
            state.brief.budget_inr = int(amount)
            answer(state, format_inr(amount), next_to=ConsultationStep.style)
            _set_state(state)
    _question_end()


def _render_style(state) -> None:
    _question_start("What kind of look do you prefer?", "Choose the direction that feels closest.")
    styles = {
        "Scandinavian": "Light woods, soft neutrals, uncluttered.",
        "Modern": "Clean lines and practical comfort.",
        "Minimal": "Fewer pieces and airy spacing.",
        "Mid-Century": "Warm wood and classic low profiles.",
        "Bohemian": "Texture, rugs, plants, warmth.",
        "Industrial": "Metal, wood, deeper tones.",
        "Not sure": "Suggest a practical direction.",
    }
    cols = st.columns(2)
    for index, (label, hint) in enumerate(styles.items()):
        with cols[index % 2]:
            if _option_card(label, hint, key=f"style_{index}", primary=label == "Scandinavian"):
                state.brief.style_preference = "Scandinavian" if label == "Not sure" else label
                answer(state, label, next_to=ConsultationStep.must_haves)
                _set_state(state)
    _question_end()


def _render_must_haves(state) -> None:
    _question_start("What must the room include?", "Select at least one. You can add a custom item too.")
    options = ["Sofa", "Coffee table", "TV unit", "Rug", "Lighting", "Storage", "Reading chair", "Side table", "Plants", "Something else"]
    selected = st.multiselect("Requirements", options, default=state.brief.must_haves, label_visibility="collapsed")
    st.caption(f"{len(selected)} selected")
    other = ""
    if "Something else" in selected:
        other = st.text_input("What else should be included?", key="must_have_other")
    if st.button("Continue", key="must_continue", type="primary"):
        if not selected:
            st.error("Choose at least one requirement to continue.")
        else:
            state.brief.must_haves = [item for item in selected if item != "Something else"]
            if other.strip():
                state.brief.must_haves.append(other.strip())
            answer(state, ", ".join(state.brief.must_haves), next_to=ConsultationStep.constraints)
            _set_state(state)
    _question_end()


def _render_constraints(state) -> None:
    _question_start("Anything important about how you use the room?", "This helps choose practical, livable products.")
    options = [
        "We have young children",
        "We have pets",
        "It is a rented home",
        "We need more storage",
        "We entertain guests",
        "Fast delivery matters",
        "No special constraint",
    ]
    selected = st.multiselect("Context", options, default=state.brief.constraints, label_visibility="collapsed")
    note = st.text_area("Or describe anything else…", value=state.brief.customer_note, height=90)
    if st.button("Review my plan", key="constraints_continue", type="primary"):
        state.brief.constraints = [] if "No special constraint" in selected else selected
        state.brief.customer_note = note.strip()
        answer(state, "Ready to review", next_to=ConsultationStep.review)
        _set_state(state)
    _question_end()


def _demo_can_preview(state) -> bool:
    return DEMO_MODE and demo_preview_allowed(state.brief)


def _render_review(state, can_run_live: bool) -> None:
    ready, missing = brief_ready(state.brief)
    _question_start("Here’s what I understood", "Confirm the details before creating your room plan.")
    sections = brief_summary(state.brief)
    cells = []
    for label, value in sections:
        cells.append(f'<div class="review-cell"><div class="review-label">{escape(label)}</div><div class="review-value">{escape(value)}</div></div>')
    if state.brief.customer_note:
        cells.append(f'<div class="review-cell"><div class="review-label">Extra note</div><div class="review-value">{escape(state.brief.customer_note)}</div></div>')
    st.markdown('<div class="review-grid">' + "".join(cells) + "</div>", unsafe_allow_html=True)
    if missing:
        st.error("Please complete the missing details before creating a plan.")

    cta_label = "Preview sample plan" if DEMO_MODE else "Create my room plan"
    disabled = not ready or (DEMO_MODE and not _demo_can_preview(state)) or (not DEMO_MODE and not can_run_live) or st.session_state.get("agent_running", False)
    st.markdown('<div class="compact-actions">', unsafe_allow_html=True)
    col_a, col_b = st.columns([0.58, 0.42])
    with col_a:
        if st.button(cta_label, key="create_plan", type="primary", disabled=disabled, use_container_width=True):
            state.step = ConsultationStep.generating
            _set_state(state)
    with col_b:
        if st.button("Edit answers", key="change_something", use_container_width=True):
            state.step = ConsultationStep.room_size
            _set_state(state)
    st.markdown("</div>", unsafe_allow_html=True)
    if DEMO_MODE and ready and not _demo_can_preview(state):
        st.markdown('<div class="compact-note">Custom plan generation is available in live mode. Use an example room to preview a sample plan.</div>', unsafe_allow_html=True)
    elif not DEMO_MODE and not can_run_live:
        st.markdown('<div class="compact-note">Plan creation is available once setup is complete.</div>', unsafe_allow_html=True)
    _question_end()


def _progress_label(entry: TraceEntry) -> str:
    return {
        "search_catalog": "Searching suitable products",
        "check_budget": "Checking your budget",
        "check_fit": "Checking furniture fit",
    }.get(entry.tool, "Preparing your final plan")


def _run_generation(state, repo: CatalogRepository, settings: Settings, api_key: str, model: str) -> None:
    st.markdown('<div class="question-card">', unsafe_allow_html=True)
    progress = st.empty()
    brief = to_agent_brief(state.brief)
    try:
        if DEMO_MODE:
            if not _demo_can_preview(state):
                st.markdown('<div class="compact-note">Custom plan generation is available in live mode.</div>', unsafe_allow_html=True)
                state.step = ConsultationStep.review
                return
            progress.write("Preparing your sample plan")
            result = make_demo_result(repo, brief)
        else:
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
                progress.write(_progress_label(entry))

            result = agent.run(brief, on_trace=on_trace)
        state.generated_result = result
        state.step = ConsultationStep.result
        _set_state(state)
    except Exception as exc:
        st.error("We couldn’t finish your plan right now. Your room details are still here.")
        if st.session_state.get("developer_mode_enabled"):
            st.exception(exc)
    finally:
        st.markdown("</div>", unsafe_allow_html=True)


def _catalog_records_for_boq(repo: CatalogRepository, lines: list[BOQLine]) -> list[dict[str, Any]]:
    records = repo.get_items(line.item_id for line in lines)
    items: list[dict[str, Any]] = []
    for line in lines:
        record = dict(records.get(line.item_id, {}))
        if record:
            record["quantity"] = line.quantity
            items.extend([record] * line.quantity)
    return items


def _render_result(state, repo: CatalogRepository) -> None:
    result = state.generated_result
    if result is None:
        st.warning("No result yet. Return to review and create a plan.")
        return
    validated = result.validated
    text = normal_result_text(validated)
    status_ok = validated.is_valid and validated.plan.status.value == "complete" and result.converged
    st.markdown('<div class="result-card">', unsafe_allow_html=True)
    st.markdown(f'<div class="eyebrow">Your plan</div><div class="question-title">{text["title"]}</div>', unsafe_allow_html=True)
    st.write(text["summary"])
    st.markdown(
        " ".join([
            f'<span class="badge {"badge-green" if validated.fit_result.get("fits") else "badge-amber"}">{"Fits your room" if validated.fit_result.get("fits") else "Fit needs review"}</span>',
            f'<span class="badge {"badge-green" if not validated.over_budget else "badge-red"}">{"Within budget" if not validated.over_budget else "Over budget"}</span>',
            f'<span class="badge {"badge-green" if status_ok else "badge-amber"}">{"Requirements covered" if status_ok else "Review trade-offs"}</span>',
        ]),
        unsafe_allow_html=True,
    )
    m1, m2, m3 = st.columns(3)
    m1.metric("Estimated furniture cost", text["estimated_cost"])
    m2.metric(text["remaining_label"], text["remaining"])
    m3.metric("Products selected", text["product_count"])
    st.markdown("</div>", unsafe_allow_html=True)

    tab_layout, tab_shop, tab_budget, tab_details = st.tabs(["Room Layout", "Shopping List", "Budget", "Details"])
    with tab_layout:
        layout = generate_living_room_layout(
            validated.fit_result.get("room_length_cm") or to_agent_brief(state.brief)["length_cm"],
            validated.fit_result.get("room_width_cm") or to_agent_brief(state.brief)["width_cm"],
            _catalog_records_for_boq(repo, validated.boq),
        )
        st.markdown(render_layout_svg(layout), unsafe_allow_html=True)
        st.markdown('<div class="compact-note">Conceptual layout based on an empty rectangular room. Doors, windows, columns and electrical points are not represented. Confirm site conditions before purchase or installation.</div>', unsafe_allow_html=True)
        for warning in layout.warnings:
            st.warning(warning)
        if layout.unplaced_item_ids:
            st.caption("Not visualised: " + ", ".join(layout.unplaced_item_ids))
    with tab_shop:
        for line in validated.boq:
            st.markdown('<div class="product-card">', unsafe_allow_html=True)
            st.markdown(f'<div class="product-title"><span class="shape-icon"></span>{line.name}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="product-meta">{line.category} • {line.item_id}</div>', unsafe_allow_html=True)
            c1, c2, c3 = st.columns(3)
            c1.write(f"Quantity: **{line.quantity}**")
            c2.write(f"Price: **{price_copy(line)}**")
            c3.write(availability_copy(line))
            st.write(f"Dimensions: {line.dimensions_cm} cm")
            st.write(line.rationale)
            if line.placement_note:
                st.caption(line.placement_note)
            st.markdown("</div>", unsafe_allow_html=True)
    with tab_budget:
        known_total = max(validated.known_total_inr, 0)
        budget = max(validated.plan.budget_inr, 1)
        st.progress(min(known_total / budget, 1.0), text=f"{format_inr(known_total)} of {format_inr(budget)}")
        by_category: dict[str, int] = {}
        for line in validated.boq:
            if line.line_total_inr is not None:
                by_category[line.category] = by_category.get(line.category, 0) + line.line_total_inr
            st.write(f"{line.category}: {line.name} × {line.quantity} — {line_total_copy(line)}")
        st.divider()
        for category, total in sorted(by_category.items()):
            st.write(f"**{category}**: {format_inr(total)}")
        st.metric(text["remaining_label"], text["remaining"])
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


def _completion_count(state) -> int:
    checks = [
        bool(state.brief.length_cm and state.brief.width_cm),
        bool(state.brief.budget_inr),
        bool(state.brief.style_preference),
        bool(state.brief.must_haves),
    ]
    return sum(checks)


def _right_preview(state, repo: CatalogRepository) -> None:
    st.markdown('<div class="preview-card">', unsafe_allow_html=True)
    st.markdown('<div class="eyebrow">Your room preview</div>', unsafe_allow_html=True)
    completed = _completion_count(state)
    st.caption(f"{completed} of 4 details completed" if completed else "Complete the questions to create your plan.")
    for label, value in brief_summary(state.brief):
        st.markdown(f'<div class="kv"><span>{label}</span><span>{value}</span></div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    if state.generated_result is not None:
        validated = state.generated_result.validated
        layout = generate_living_room_layout(
            state.brief.length_cm or int(validated.fit_result.get("room_length_cm") or 0),
            state.brief.width_cm or int(validated.fit_result.get("room_width_cm") or 0),
            _catalog_records_for_boq(repo, validated.boq),
        )
        st.markdown(render_layout_svg(layout, max_px=330, min_width=210, min_height=145), unsafe_allow_html=True)
    elif state.brief.length_cm and state.brief.width_cm:
        layout = generate_living_room_layout(state.brief.length_cm, state.brief.width_cm, [])
        st.markdown(render_layout_svg(layout, max_px=330, min_width=210, min_height=145), unsafe_allow_html=True)
        st.caption("Furniture placement will appear after the plan is created.")
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
    configured_model = secret_model or settings.anthropic_model
    can_run_live = bool(api_key)
    state = _state()
    developer_available = developer_mode_allowed(os.environ, dict(st.query_params))

    _render_topbar(state, DEMO_MODE, developer_available)
    if state.step in {ConsultationStep.welcome, ConsultationStep.sample_or_custom}:
        _render_hero()

    left, right = st.columns([0.56, 0.44], gap="large")
    with left:
        _step_indicator(state.step)
        if state.step not in {ConsultationStep.welcome, ConsultationStep.result}:
            _render_history(state)
        if state.step == ConsultationStep.welcome:
            _render_welcome(state)
        elif state.step == ConsultationStep.sample_or_custom:
            _render_samples(state, repo)
        elif state.step == ConsultationStep.room_size:
            _render_room_size(state)
        elif state.step == ConsultationStep.budget:
            _render_budget(state)
        elif state.step == ConsultationStep.style:
            _render_style(state)
        elif state.step == ConsultationStep.must_haves:
            _render_must_haves(state)
        elif state.step == ConsultationStep.constraints:
            _render_constraints(state)
        elif state.step == ConsultationStep.review:
            _render_review(state, can_run_live)
        elif state.step == ConsultationStep.generating:
            _run_generation(state, repo, settings, api_key, configured_model)
        elif state.step == ConsultationStep.result:
            _render_result(state, repo)

        if state.step not in {ConsultationStep.welcome, ConsultationStep.result}:
            st.markdown('<div class="subtle-button">', unsafe_allow_html=True)
            if st.button("Back", key="bottom_back"):
                _set_state(back(state))
            st.markdown("</div>", unsafe_allow_html=True)
    with right:
        _right_preview(state, repo)

    if st.session_state.get("developer_mode_enabled"):
        st.caption(f"Developer: model {configured_model}")


main()
