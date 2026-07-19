from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import streamlit as st
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
if os.getenv("INTERIOR_SKIP_DOTENV") != "1":
    load_dotenv(PROJECT_ROOT / ".env")

from interior_agent.agent import InteriorDesignAgent  # noqa: E402
from interior_agent.config import ConfigurationError, Settings  # noqa: E402
from interior_agent.db import CatalogRepository  # noqa: E402
from interior_agent.schemas import BOQLine, TraceEntry  # noqa: E402
from interior_agent.tools import AgentTools  # noqa: E402
from interior_agent.ui.demo import make_demo_result  # noqa: E402
from interior_agent.ui.layout import generate_living_room_layout, render_layout_svg  # noqa: E402
from interior_agent.ui.presenter import availability_copy, brief_summary, format_inr, line_total_copy, normal_result_text, price_copy, sample_display_name  # noqa: E402
from interior_agent.ui.state import ConsultationStep, answer, back, brief_ready, feet_to_cm, initial_state, populate_from_sample, reset, to_agent_brief  # noqa: E402
from interior_agent.validator import PlanValidator  # noqa: E402


st.set_page_config(page_title="Living Room Design Agent", page_icon="LR", layout="wide")


def _css() -> None:
    st.markdown(
        """
        <style>
        .stApp { background: #f7f3ed; color: #2f2923; }
        [data-testid="stSidebar"] { background: #fffaf3; }
        .block-container { padding-top: 1.5rem; max-width: 1420px; }
        .hero-title { font-size: 2rem; font-weight: 750; margin-bottom: .15rem; color: #2f2923; }
        .subtle { color: #736b61; font-size: .95rem; }
        .badge { display:inline-flex; align-items:center; gap:.35rem; border:1px solid #d8d0c5; border-radius:999px; padding:.22rem .6rem; background:#fffaf4; color:#63584c; font-size:.78rem; margin-right:.35rem; }
        .badge-green { background:#edf8f0; border-color:#b8ddc0; color:#27633a; }
        .badge-amber { background:#fff6df; border-color:#edcf8a; color:#7a5717; }
        .badge-red { background:#fff0ee; border-color:#ebb5ad; color:#8a2f24; }
        .panel { border:1px solid #e1d9cf; background:#fffdf9; border-radius:14px; padding:1rem; }
        .kv { display:flex; justify-content:space-between; gap:1rem; padding:.45rem 0; border-bottom:1px solid #eee6dc; }
        .kv:last-child { border-bottom:0; }
        .kv span:first-child { color:#756c62; }
        .kv span:last-child { text-align:right; font-weight:650; color:#332d27; }
        .product-card { border:1px solid #e0d8cf; background:#fffefb; border-radius:14px; padding:1rem; margin-bottom:.75rem; }
        .product-title { font-weight:760; font-size:1.03rem; margin-bottom:.15rem; }
        .product-meta { color:#756c62; font-size:.88rem; }
        .shape-icon { width:38px; height:28px; display:inline-block; border-radius:8px; background:#d8b980; border:1px solid #a88b50; vertical-align:middle; margin-right:.5rem; }
        div.stButton > button { border-radius:12px; border-color:#d9d0c5; background:#fffdf9; color:#2f2923; min-height:2.75rem; }
        div.stButton > button[kind="primary"] { background:#2f6b4f; border-color:#2f6b4f; color:white; }
        div.stMultiSelect [data-baseweb="tag"] { background:#edf8f0; color:#245c37; }
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


def _card_button(label: str, caption: str = "", *, key: str, primary: bool = False) -> bool:
    st.markdown(f"**{label}**")
    if caption:
        st.caption(caption)
    return st.button(label, key=key, type="primary" if primary else "secondary", use_container_width=True)


def _render_history(state) -> None:
    for entry in state.history:
        with st.chat_message(entry["role"]):
            st.write(entry["content"])


def _render_welcome(state) -> None:
    with st.chat_message("assistant"):
        st.write("Would you like to design your own living room or try a sample first?")
    col_a, col_b = st.columns(2)
    with col_a:
        if _card_button("Design my own room", "Answer a few quick questions.", key="design_custom", primary=True):
            state.step = ConsultationStep.room_size
            answer(state, "Design my own room", next_to=ConsultationStep.room_size)
            _set_state(state)
    with col_b:
        if _card_button("Try a sample room", "Preview the flow with catalog-backed sample data.", key="try_sample"):
            answer(state, "Try a sample room", next_to=ConsultationStep.sample_or_custom)
            _set_state(state)


def _render_samples(state, repo: CatalogRepository) -> None:
    with st.chat_message("assistant"):
        st.write("Choose a sample living room. I’ll hide internal database labels and show it as a customer brief.")
    for index, brief in enumerate(_living_room_briefs(repo)):
        name = sample_display_name(brief)
        cols = st.columns([3, 2, 2])
        with cols[0]:
            st.markdown(f"**{name}**")
            st.caption(str(brief.get("must_haves", "")))
        with cols[1]:
            st.write(f"{brief['length_cm']} × {brief['width_cm']} cm")
            st.caption(str(brief.get("style_preference") or ""))
        with cols[2]:
            st.write(format_inr(brief.get("budget_inr")))
            if st.button("Use this sample", key=f"sample_{index}", use_container_width=True):
                _set_state(populate_from_sample(state, brief, name))


def _render_room_size(state) -> None:
    with st.chat_message("assistant"):
        st.write("How large is your living room?")
    options = [
        ("Small — around 10 × 10 ft", feet_to_cm(10), feet_to_cm(10)),
        ("Medium — around 12 × 15 ft", feet_to_cm(15), feet_to_cm(12)),
        ("Large — around 15 × 18 ft", feet_to_cm(18), feet_to_cm(15)),
        ("I’m not sure", feet_to_cm(12), feet_to_cm(10)),
    ]
    cols = st.columns(2)
    for index, (label, length, width) in enumerate(options):
        with cols[index % 2]:
            if st.button(label, key=f"size_{index}", use_container_width=True):
                state.brief.length_cm = length
                state.brief.width_cm = width
                answer(state, label, next_to=ConsultationStep.budget)
                _set_state(state)
    with st.expander("Enter exact measurements"):
        unit = st.radio("Unit", ["feet", "cm"], horizontal=True, key="size_unit")
        col_l, col_w, col_c = st.columns(3)
        length = col_l.number_input("Length", min_value=1.0, value=12.0 if unit == "feet" else 365.0, step=0.5)
        width = col_w.number_input("Width", min_value=1.0, value=15.0 if unit == "feet" else 455.0, step=0.5)
        ceiling = col_c.number_input("Ceiling height optional", min_value=0.0, value=0.0, step=0.5)
        if st.button("Use these measurements", key="exact_measurements", type="primary"):
            state.brief.length_cm = feet_to_cm(length) if unit == "feet" else int(round(length))
            state.brief.width_cm = feet_to_cm(width) if unit == "feet" else int(round(width))
            state.brief.ceiling_cm = None if ceiling <= 0 else (feet_to_cm(ceiling) if unit == "feet" else int(round(ceiling)))
            answer(state, f"{state.brief.length_cm} × {state.brief.width_cm} cm", next_to=ConsultationStep.budget)
            _set_state(state)


def _render_budget(state) -> None:
    with st.chat_message("assistant"):
        st.write("What total budget should I work within?")
    options = [
        ("Under ₹50,000", 50000),
        ("₹50,000–₹1,00,000", 100000),
        ("₹1,00,000–₹2,50,000", 250000),
        ("₹2,50,000–₹5,00,000", 500000),
    ]
    for label, value in options:
        if st.button(label, key=f"budget_{value}", use_container_width=True):
            state.brief.budget_inr = value
            answer(state, f"{label}. I’ll avoid silently exceeding this budget.", next_to=ConsultationStep.style)
            _set_state(state)
    with st.expander("Enter another amount"):
        amount = st.number_input("Budget in INR", min_value=1000, value=int(state.brief.budget_inr or 150000), step=5000)
        if st.button("Use this budget", key="custom_budget", type="primary"):
            state.brief.budget_inr = int(amount)
            answer(state, f"{format_inr(amount)}. I’ll avoid silently exceeding this budget.", next_to=ConsultationStep.style)
            _set_state(state)


def _render_style(state) -> None:
    with st.chat_message("assistant"):
        st.write("What kind of look do you prefer?")
    styles = {
        "Scandinavian": "Light woods, soft neutrals, uncluttered.",
        "Modern": "Clean lines, practical comfort, balanced contrast.",
        "Minimal": "Fewer pieces, calm surfaces, airy spacing.",
        "Mid-Century": "Warm wood, low profiles, classic shapes.",
        "Bohemian": "Texture, rugs, plants, collected warmth.",
        "Industrial": "Metal, wood, deeper tones, open shelving.",
        "Not sure — suggest one": "Let the planner choose a practical direction.",
    }
    cols = st.columns(2)
    for index, (label, hint) in enumerate(styles.items()):
        with cols[index % 2]:
            if _card_button(label, hint, key=f"style_{index}"):
                state.brief.style_preference = "Scandinavian" if label.startswith("Not sure") else label
                answer(state, label, next_to=ConsultationStep.must_haves)
                _set_state(state)


def _render_must_haves(state) -> None:
    with st.chat_message("assistant"):
        st.write("What must the room include?")
    options = ["Sofa", "Coffee table", "TV unit", "Rug", "Lighting", "Storage", "Reading chair", "Side table", "Plants", "Something else"]
    selected = st.multiselect("Choose at least one", options, default=state.brief.must_haves)
    st.caption(f"{len(selected)} selected")
    other = ""
    if "Something else" in selected:
        other = st.text_input("What else should be included?", key="must_have_other")
    if st.button("Continue", key="must_continue", type="primary", disabled=not selected):
        state.brief.must_haves = [item for item in selected if item != "Something else"]
        if other.strip():
            state.brief.must_haves.append(other.strip())
        answer(state, ", ".join(state.brief.must_haves), next_to=ConsultationStep.constraints)
        _set_state(state)


def _render_constraints(state) -> None:
    with st.chat_message("assistant"):
        st.write("Anything important about how you use the room?")
    options = [
        "We have young children",
        "We have pets",
        "It is a rented home",
        "We need more storage",
        "We entertain guests",
        "Fast delivery matters",
        "No special constraint",
    ]
    selected = st.multiselect("Select any that apply", options, default=state.brief.constraints)
    note = st.text_area("Or describe anything else…", value=state.brief.customer_note, height=90)
    if st.button("Review my brief", key="constraints_continue", type="primary"):
        state.brief.constraints = [] if "No special constraint" in selected else selected
        state.brief.customer_note = note.strip()
        answer(state, "Review my brief", next_to=ConsultationStep.review)
        _set_state(state)


def _render_review(state, demo_mode: bool, can_run_live: bool, settings: Settings, repo: CatalogRepository) -> None:
    ready, missing = brief_ready(state.brief)
    with st.chat_message("assistant"):
        st.write("Great — here’s what I understood.")
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    for label, value in brief_summary(state.brief):
        st.markdown(f'<div class="kv"><span>{label}</span><span>{value}</span></div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    if missing:
        st.warning("Please add: " + ", ".join(missing))
    c1, c2, c3 = st.columns(3)
    with c1:
        label = "Create Demo Plan" if demo_mode else "Create My Room Plan"
        disabled = not ready or (not demo_mode and not can_run_live) or st.session_state.get("agent_running", False)
        if st.button(label, key="create_plan", type="primary", disabled=disabled, use_container_width=True):
            state.step = ConsultationStep.generating
            _set_state(state)
    with c2:
        if st.button("Change Something", key="change_something", use_container_width=True):
            state.step = ConsultationStep.room_size
            _set_state(state)
    with c3:
        if st.button("Start Over", key="start_over_review", use_container_width=True):
            _set_state(reset())
    if not demo_mode and not can_run_live:
        st.info("Add the server-side Anthropic key to create a live plan. You can still review and edit the brief.")
    st.caption(f"Configured model: {settings.anthropic_model}")


def _progress_label(entry: TraceEntry) -> str:
    return {
        "search_catalog": "Searching suitable products",
        "check_budget": "Checking your budget",
        "check_fit": "Checking furniture fit",
    }.get(entry.tool, "Preparing your final plan")


def _run_generation(state, repo: CatalogRepository, settings: Settings, api_key: str, model: str, demo_mode: bool) -> None:
    st.info("Offline demo preview" if demo_mode else "Creating your room plan after your confirmation.")
    progress = st.empty()
    trace_holder: list[TraceEntry] = []
    brief = to_agent_brief(state.brief)
    try:
        if demo_mode:
            progress.write("Searching suitable products")
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
                trace_holder.append(entry)
                progress.write(_progress_label(entry))

            result = agent.run(brief, on_trace=on_trace)
        state.generated_result = result
        state.step = ConsultationStep.result
        _set_state(state)
    except Exception as exc:
        st.session_state["agent_running"] = False
        st.error("We couldn’t finish your plan right now. Your room details are still here.")
        if state.developer_mode:
            st.exception(exc)


def _catalog_records_for_boq(repo: CatalogRepository, lines: list[BOQLine]) -> list[dict[str, Any]]:
    records = repo.get_items(line.item_id for line in lines)
    items: list[dict[str, Any]] = []
    for line in lines:
        record = dict(records.get(line.item_id, {}))
        if record:
            record["quantity"] = line.quantity
            items.extend([record] * line.quantity)
    return items


def _render_result(state, repo: CatalogRepository, demo_mode: bool) -> None:
    result = state.generated_result
    if result is None:
        st.warning("No result yet. Return to review and create a plan.")
        return
    validated = result.validated
    text = normal_result_text(validated)
    status_ok = validated.is_valid and validated.plan.status.value == "complete" and result.converged
    st.markdown(f'<div class="hero-title">{text["title"]}</div>', unsafe_allow_html=True)
    st.write(text["summary"])
    st.markdown(
        " ".join([
            f'<span class="badge {"badge-green" if validated.fit_result.get("fits") else "badge-amber"}">{"Fits your room" if validated.fit_result.get("fits") else "Fit needs review"}</span>',
            f'<span class="badge {"badge-green" if not validated.over_budget else "badge-red"}">{"Within budget" if not validated.over_budget else "Over budget"}</span>',
            f'<span class="badge {"badge-green" if status_ok else "badge-amber"}">{"Requirements covered" if status_ok else "Review trade-offs"}</span>',
            '<span class="badge badge-amber">Offline demo preview</span>' if demo_mode else "",
        ]),
        unsafe_allow_html=True,
    )
    m1, m2, m3 = st.columns(3)
    m1.metric("Estimated furniture cost", text["estimated_cost"])
    m2.metric(text["remaining_label"], text["remaining"])
    m3.metric("Products selected", text["product_count"])

    tab_layout, tab_shop, tab_budget, tab_details = st.tabs(["Room Layout", "Shopping List", "Budget", "Details"])
    with tab_layout:
        layout = generate_living_room_layout(
            validated.fit_result.get("room_length_cm") or to_agent_brief(state.brief)["length_cm"],
            validated.fit_result.get("room_width_cm") or to_agent_brief(state.brief)["width_cm"],
            _catalog_records_for_boq(repo, validated.boq),
        )
        st.markdown(render_layout_svg(layout), unsafe_allow_html=True)
        st.info("Conceptual layout based on an empty rectangular room. Doors, windows, columns and electrical points are not represented. Confirm site conditions before purchase or installation.")
        if layout.warnings:
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

    if state.developer_mode:
        with st.expander("Developer trace and structured output"):
            st.write(f"Iterations: {result.iterations}; converged: {result.converged}")
            st.json([entry.model_dump(mode="json") for entry in result.trace])
            st.json(validated.model_dump(mode="json"))
            st.json(result.usage.as_dict())


def _right_preview(state, repo: CatalogRepository) -> None:
    st.markdown("### Live Preview")
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    for label, value in brief_summary(state.brief):
        st.markdown(f'<div class="kv"><span>{label}</span><span>{value}</span></div>', unsafe_allow_html=True)
    ready, missing = brief_ready(state.brief)
    badge = "badge-green" if ready else "badge-amber"
    status = "Ready for review" if ready else "Needs " + ", ".join(missing)
    st.markdown(f'<span class="badge {badge}">{status}</span>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    if state.generated_result is None:
        length = state.brief.length_cm or 365
        width = state.brief.width_cm or 305
        layout = generate_living_room_layout(length, width, [])
        st.markdown(render_layout_svg(layout), unsafe_allow_html=True)
        st.caption("Furniture placement will appear after the plan is created.")
    else:
        validated = state.generated_result.validated
        layout = generate_living_room_layout(
            state.brief.length_cm or 365,
            state.brief.width_cm or 305,
            _catalog_records_for_boq(repo, validated.boq),
        )
        st.markdown(render_layout_svg(layout), unsafe_allow_html=True)


def main() -> None:
    _css()
    demo_mode = os.getenv("INTERIOR_UI_DEMO_MODE") == "1"
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
    api_key = secret_key or os.getenv("ANTHROPIC_API_KEY") or ""
    configured_model = secret_model or settings.anthropic_model
    can_run_live = bool(api_key)
    state = _state()
    state.developer_mode = st.sidebar.toggle("Developer Mode", value=state.developer_mode)
    if st.sidebar.button("Start over"):
        _set_state(reset())
    st.sidebar.caption(f"Mode: {'Offline demo preview' if demo_mode else 'Live after review'}")
    st.sidebar.caption(f"Model: {configured_model}")

    st.markdown('<div class="hero-title">Living Room Design Consultation</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtle">Have a short consultation, confirm the brief, then receive an actionable catalog-grounded room plan.</div>', unsafe_allow_html=True)
    if demo_mode:
        st.markdown('<span class="badge badge-amber">Offline demo preview</span>', unsafe_allow_html=True)

    left, right = st.columns([0.55, 0.45], gap="large")
    with left:
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
            _render_review(state, demo_mode, can_run_live, settings, repo)
        elif state.step == ConsultationStep.generating:
            _run_generation(state, repo, settings, api_key, configured_model, demo_mode)
        elif state.step == ConsultationStep.result:
            _render_result(state, repo, demo_mode)

        nav_a, nav_b = st.columns(2)
        if nav_a.button("Back", disabled=state.step in {ConsultationStep.welcome, ConsultationStep.result}, use_container_width=True):
            _set_state(back(state))
        if nav_b.button("Start Over", use_container_width=True):
            _set_state(reset())
    with right:
        _right_preview(state, repo)


main()
