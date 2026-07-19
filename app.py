from __future__ import annotations

import os
import sys
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
load_dotenv(PROJECT_ROOT / ".env")

from interior_agent.agent import InteriorDesignAgent  # noqa: E402
from interior_agent.config import ConfigurationError, Settings  # noqa: E402
from interior_agent.db import CatalogRepository  # noqa: E402
from interior_agent.tools import AgentTools  # noqa: E402
from interior_agent.validator import PlanValidator  # noqa: E402


st.set_page_config(page_title="Interior Design AI Agent", page_icon="🛋️", layout="wide")
st.title("Interior Design AI Agent")
st.caption("Catalog-grounded room plan + BOQ with visible tool use, budget checks, fit checks, and deterministic validation.")

try:
    settings = Settings.from_env(PROJECT_ROOT)
    repo = CatalogRepository(settings.db_path)
except (ConfigurationError, FileNotFoundError) as exc:
    st.error(f"Setup error: {exc}")
    st.stop()
briefs = repo.list_briefs()
brief_map = {brief["brief_id"]: brief for brief in briefs}

with st.sidebar:
    st.header("Brief")
    brief_id = st.selectbox("Database brief", list(brief_map), index=0)
    base = brief_map[brief_id]
    room_type = st.text_input("Room type", base["room_type"])
    col_a, col_b = st.columns(2)
    with col_a:
        length_cm = st.number_input("Length (cm)", min_value=100, value=int(base["length_cm"]), step=10)
    with col_b:
        width_cm = st.number_input("Width (cm)", min_value=100, value=int(base["width_cm"]), step=10)
    budget_inr = st.number_input("Budget (INR)", min_value=0, value=int(base["budget_inr"]), step=5000)
    style = st.text_input("Style", base["style_preference"])
    must_haves = st.text_area("Must-haves", base["must_haves"], height=100)
    constraints = st.text_area("Constraints", base["constraints"] or "", height=80)
    customer_note = st.text_area("Customer note", base["customer_note"] or "", height=100)

    secret_key = None
    secret_model = None
    try:
        secret_key = st.secrets.get("ANTHROPIC_API_KEY")
        secret_model = st.secrets.get("ANTHROPIC_MODEL")
    except Exception:
        pass
    api_key = secret_key or os.getenv("ANTHROPIC_API_KEY")
    configured_model = secret_model or settings.anthropic_model
    can_run = bool(api_key)
    if not can_run:
        st.warning("Add ANTHROPIC_API_KEY to .env or Streamlit Secrets to run the live agent.")
    st.caption(f"Configured model: `{configured_model}`")
    run_clicked = st.button("Generate plan", type="primary", disabled=not can_run or st.session_state.get("agent_running", False), use_container_width=True)

brief = {
    "brief_id": brief_id,
    "room_type": room_type,
    "length_cm": int(length_cm),
    "width_cm": int(width_cm),
    "ceiling_cm": int(base.get("ceiling_cm") or 0),
    "budget_inr": int(budget_inr),
    "style_preference": style,
    "must_haves": must_haves,
    "constraints": constraints,
    "customer_note": customer_note,
}

left, right = st.columns([1, 1])
with left:
    st.subheader("Selected brief")
    st.json(brief)
with right:
    st.subheader("What will be enforced")
    st.markdown(
        "- Real catalog item IDs only\n"
        "- Quantity-aware BOQ and unknown-price handling\n"
        "- Budget and fit re-checks in code\n"
        "- Required scope refusals and guarantee disclaimers\n"
        "- Must-have coverage via a deterministic synonym map"
    )

if run_clicked:
    st.session_state["agent_running"] = True
    tools = AgentTools(repo)
    validator = PlanValidator(repo)
    agent = InteriorDesignAgent(
        tools=tools,
        validator=validator,
        api_key=api_key,
        model=configured_model,
        max_iterations=settings.max_iterations,
        max_tokens=settings.anthropic_max_tokens,
    )

    st.subheader("Live agent trace")
    trace_container = st.container(border=True)

    def show_trace(entry):
        with trace_container:
            with st.expander(f"Iteration {entry.iteration}: {entry.tool}", expanded=True):
                st.write("Input")
                st.json(entry.input)
                st.write("Result")
                st.json(entry.result)

    with st.spinner("Searching, checking budget, checking fit, and validating..."):
        try:
            result = agent.run(brief, on_trace=show_trace)
        except Exception as exc:
            st.session_state["agent_running"] = False
            st.exception(exc)
            st.stop()
    st.session_state["agent_running"] = False

    validated = result.validated
    st.caption("Layout/fit is a heuristic based on an empty rectangular room; doors, windows, columns, services, and exact placement geometry are not represented.")
    st.subheader("Design plan")
    st.write(validated.plan.design_summary)
    metric_a, metric_b, metric_c, metric_d = st.columns(4)
    metric_a.metric("Budget", f"₹{validated.plan.budget_inr:,.0f}")
    metric_b.metric("Known total", f"₹{validated.known_total_inr:,.0f}")
    metric_c.metric("Known-price remaining" if validated.has_unknown_prices else "Remaining", f"₹{validated.remaining_inr:,.0f}")
    if not result.converged:
        status_label = "AGENT LOOP FAILURE"
    elif validated.is_valid and validated.plan.status.value == "complete":
        status_label = "VALID COMPLETE"
    elif validated.is_valid:
        status_label = "VALID PARTIAL/IMPOSSIBLE"
    else:
        status_label = "VALIDATOR REVIEW"
    metric_d.metric("Validation", status_label)
    st.write(f"Iterations: {result.iterations}; converged: {result.converged}")

    if validated.boq:
        st.subheader("Bill of Quantities")
        rows = []
        for line in validated.boq:
            row = line.model_dump()
            row["unit_price_inr"] = "Price on request" if line.unit_price_inr is None else f"₹{line.unit_price_inr:,.0f}"
            row["line_total_inr"] = "Price on request" if line.line_total_inr is None else f"₹{line.line_total_inr:,.0f}"
            rows.append(row)
        st.dataframe(rows, use_container_width=True, hide_index=True)

    if validated.plan.tradeoffs:
        st.subheader("Trade-offs")
        for tradeoff in validated.plan.tradeoffs:
            st.write(f"- {tradeoff}")
    for title, values in (("Flags", validated.plan.flags), ("Assumptions", validated.plan.assumptions), ("Style relaxations", validated.plan.style_relaxations)):
        if values:
            st.subheader(title)
            for value in values:
                st.write(f"- {value}")
    if validated.plan.declined_scope:
        st.subheader("Declined scope")
        for decline in validated.plan.declined_scope:
            st.write(f"- {decline.category}: {decline.message}")

    if validated.issues:
        st.subheader("Validator findings")
        for issue in validated.issues:
            if issue.severity == "error":
                st.error(f"{issue.code}: {issue.message}")
            elif issue.severity == "warning":
                st.warning(f"{issue.code}: {issue.message}")
            else:
                st.info(f"{issue.code}: {issue.message}")

    with st.expander("Fit details"):
        st.json(validated.fit_result)
    with st.expander("Must-have coverage"):
        st.json(validated.must_have_result)
    with st.expander("Raw structured plan"):
        st.json(validated.plan.model_dump(mode="json"))
