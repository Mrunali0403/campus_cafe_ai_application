"""Streamlit interface for the Campus Café CrewAI launch-planning workflow."""

import math
import os

import streamlit as st

if not os.getenv("CREWAI_API_KEY"):
    try:
        secret_api_key = st.secrets.get("CREWAI_API_KEY")
    except (FileNotFoundError, KeyError):
        secret_api_key = None
    if secret_api_key:
        os.environ["CREWAI_API_KEY"] = str(secret_api_key)

import campus_cafe_crew


st.set_page_config(page_title="Campus Café Launch Planner", page_icon="☕")
st.markdown(
    """
    <style>
    :root {
        color-scheme: dark;
        --cafe-bg: #0b1220;
        --cafe-panel: #111c2b;
        --cafe-border: #26364a;
        --cafe-text: #f1f5f9;
        --cafe-muted: #a7b6c8;
        --cafe-accent: #58d6c5;
    }
    [data-testid="stAppViewContainer"] {
        background:
            radial-gradient(ellipse at 15% 0%, #16394a 0, transparent 32rem),
            linear-gradient(145deg, #0b1220 0%, #101b2a 55%, #0b1220 100%);
        color: var(--cafe-text);
    }
    [data-testid="stHeader"] { background: transparent; }
    [data-testid="stMainBlockContainer"] {
        max-width: 1080px;
        padding-top: 1.8rem;
        padding-bottom: 4rem;
    }
    h1, h2, h3 {
        color: var(--cafe-text);
        letter-spacing: -0.035em;
        line-height: 1.2;
    }
    h1 { font-size: clamp(2.25rem, 5vw, 3.5rem); margin-bottom: .35rem; }
    h2 { font-size: clamp(1.35rem, 3vw, 1.75rem); margin-top: .4rem; }
    h3 { font-size: 1.05rem; }
    [data-testid="stMarkdownContainer"] p,
    [data-testid="stCaptionContainer"] { color: var(--cafe-muted); }
    [data-testid="stForm"] {
        background: transparent;
        border: 0;
        padding: 0;
        box-shadow: none;
    }
    [data-testid="stVerticalBlockBorderWrapper"] {
        background: color-mix(in srgb, var(--cafe-panel) 94%, transparent);
        border: 1px solid var(--cafe-border);
        border-radius: 16px;
        padding: 1.15rem 1.25rem;
        box-shadow: 0 14px 36px #02081740;
    }
    [data-testid="stMetric"] {
        background: linear-gradient(145deg, #142437, #111c2b);
        border: 1px solid var(--cafe-border);
        border-radius: 14px;
        padding: 1rem 1.05rem;
        min-height: 112px;
    }
    [data-testid="stMetricLabel"] {
        color: var(--cafe-muted);
        font-size: .84rem;
    }
    [data-testid="stMetricValue"] {
        color: var(--cafe-accent);
        font-weight: 700;
    }
    [data-testid="stTextInput"] input,
    [data-testid="stTextArea"] textarea,
    [data-testid="stNumberInput"] input {
        background: #0c1624;
        border: 1px solid #34475c;
        border-radius: 9px;
        color: var(--cafe-text);
    }
    [data-testid="stTextInput"] input:focus,
    [data-testid="stTextArea"] textarea:focus,
    [data-testid="stNumberInput"] input:focus {
        border-color: var(--cafe-accent);
        box-shadow: 0 0 0 1px var(--cafe-accent);
    }
    .stButton > button, .stDownloadButton > button,
    [data-testid="stFormSubmitButton"] button {
        min-height: 2.9rem;
        border: 1px solid var(--cafe-accent);
        border-radius: 9px;
        background: var(--cafe-accent);
        color: #071722;
        font-weight: 700;
    }
    .stButton > button:hover, .stDownloadButton > button:hover,
    [data-testid="stFormSubmitButton"] button:hover {
        background: #83e5d8;
        border-color: #83e5d8;
        color: #071722;
    }
    [data-testid="stStatusWidget"] {
        border: 1px solid var(--cafe-border);
        border-radius: 12px;
        background: var(--cafe-panel);
    }
    [data-testid="stAlert"] { border-radius: 12px; }
    [data-testid="stMarkdownContainer"] table {
        border-color: var(--cafe-border) !important;
        width: 100%;
    }
    [data-testid="stMarkdownContainer"] th {
        background: #17283a;
        color: var(--cafe-text);
    }
    [data-testid="stMarkdownContainer"] td {
        color: #dce6ef;
    }
    .cafe-eyebrow {
        color: var(--cafe-accent);
        font-size: .78rem;
        font-weight: 700;
        letter-spacing: .14em;
        text-transform: uppercase;
        margin: .35rem 0 .5rem;
    }
    .cafe-subtitle {
        max-width: 720px;
        color: var(--cafe-muted);
        font-size: 1.05rem;
        line-height: 1.65;
    }
    @media (max-width: 640px) {
        [data-testid="stMainBlockContainer"] { padding: 1rem .85rem 2.5rem; }
        [data-testid="stVerticalBlockBorderWrapper"] { padding: .9rem; }
        [data-testid="stMetric"] { padding: .8rem; min-height: 96px; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)
st.markdown('<div class="cafe-eyebrow">Launch planning studio</div>', unsafe_allow_html=True)
st.title("Campus Café Launch Team")
st.markdown(
    '<div class="cafe-subtitle">'
    "Build a source-conscious launch plan with a four-agent research, "
    "financial-analysis, writing, and review team."
    "</div>",
    unsafe_allow_html=True,
)

with st.form("launch_plan_form"):
    with st.container(border=True):
        st.subheader("01 · Café concept")
        st.caption("Describe the scenario the research team should investigate.")
        concept_location = st.text_input(
            "Café concept and location",
            value="A student-focused café near the main campus library",
            help="Example only. Replace it with your own concept and location.",
        )
        target_customers = st.text_area(
            "Target customers",
            value="Students, faculty, and campus staff",
            help="Example only. These are planning assumptions, not verified demand.",
            height=80,
        )

    with st.container(border=True):
        st.subheader("02 · Financial assumptions")
        st.caption(
            "Editable examples in USD. These are user-provided planning "
            "assumptions, not verified market data."
        )
        cost_column, pricing_column = st.columns(2)
        with cost_column:
            startup_costs = st.number_input(
                "Estimated one-time startup costs (USD)",
                min_value=0.0,
                value=85000.0,
                step=1000.0,
                format="%.2f",
            )
            monthly_fixed_costs = st.number_input(
                "Estimated monthly fixed costs (USD)",
                min_value=0.0,
                value=24000.0,
                step=500.0,
                format="%.2f",
            )
            operating_days_per_month = st.number_input(
                "Expected operating days per month",
                min_value=1,
                max_value=31,
                value=26,
                step=1,
            )
        with pricing_column:
            average_selling_price = st.number_input(
                "Average selling price per customer (USD)",
                min_value=0.01,
                value=8.50,
                step=0.25,
                format="%.2f",
            )
            variable_cost_per_customer = st.number_input(
                "Variable cost per customer (USD)",
                min_value=0.0,
                value=3.25,
                step=0.25,
                format="%.2f",
            )

    submitted = st.form_submit_button(
        "Generate launch plan",
        type="primary",
        use_container_width=True,
    )

if submitted:
    st.session_state.pop("launch_brief", None)
    st.session_state.pop("launch_metrics", None)
    st.session_state.pop("launch_error", None)

    if not concept_location.strip():
        st.session_state["launch_error"] = "Enter a café concept and location."
    elif not target_customers.strip():
        st.session_state["launch_error"] = "Describe the target customers."
    elif variable_cost_per_customer >= average_selling_price:
        st.session_state["launch_error"] = (
            "Variable cost per customer must be less than the average selling price."
        )
    elif not os.getenv("CREWAI_API_KEY"):
        st.session_state["launch_error"] = (
            "CREWAI_API_KEY is not configured. Add it to your environment, "
            "then restart the app."
        )
    else:
        inputs = {
            "concept_location": concept_location,
            "target_customers": target_customers,
            "startup_costs": startup_costs,
            "monthly_fixed_costs": monthly_fixed_costs,
            "average_selling_price": average_selling_price,
            "variable_cost_per_customer": variable_cost_per_customer,
            "operating_days_per_month": operating_days_per_month,
        }
        try:
            with st.status("Generating the launch plan…", expanded=True) as status:
                try:
                    st.write("Researching sources and evidence gaps")
                    st.write("Calculating break-even from your assumptions")
                    st.write("Drafting and reviewing the brief")
                    brief = campus_cafe_crew.run_launch_team(inputs)
                    contribution = average_selling_price - variable_cost_per_customer
                    monthly_customers = monthly_fixed_costs / contribution
                    daily_customers = math.ceil(
                        monthly_customers / operating_days_per_month
                    )
                    monthly_revenue = monthly_customers * average_selling_price
                except Exception:
                    status.update(
                        label="Analysis failed; no final brief was generated",
                        state="error",
                        expanded=True,
                    )
                    raise
                st.session_state["launch_brief"] = brief
                st.session_state["launch_metrics"] = {
                    "contribution": contribution,
                    "monthly_customers": monthly_customers,
                    "daily_customers": daily_customers,
                    "monthly_revenue": monthly_revenue,
                }
                status.update(
                    label="Launch plan generated successfully",
                    state="complete",
                    expanded=False,
                )
        except (ValueError, RuntimeError) as error:
            message = str(error)
            if "CREWAI_API_KEY" not in message and "did not start" not in message:
                message = campus_cafe_crew._failure_message(error)
            st.session_state["launch_error"] = message
        except Exception as error:
            st.session_state["launch_error"] = (
                campus_cafe_crew._failure_message(error)
            )

if error_message := st.session_state.get("launch_error"):
    st.error(f"Launch plan was not generated. {error_message}")

if brief := st.session_state.get("launch_brief"):
    st.header("Break-even snapshot")
    st.caption(
        "Calculated from your user-provided assumptions. Startup costs are "
        "excluded from monthly operating break-even."
    )
    metrics = st.session_state["launch_metrics"]
    metric_columns = st.columns(4)
    metric_columns[0].metric(
        "Contribution / customer", f"${metrics['contribution']:,.2f}"
    )
    metric_columns[1].metric(
        "Monthly break-even customers",
        f"{metrics['monthly_customers']:,.1f}",
    )
    metric_columns[2].metric(
        "Daily break-even customers",
        f"{metrics['daily_customers']:,}",
    )
    metric_columns[3].metric(
        "Break-even monthly revenue",
        f"${metrics['monthly_revenue']:,.2f}",
    )

    st.header("Final launch brief")
    with st.container(border=True):
        st.markdown(brief)
        st.download_button(
            "Download final_brief.md",
            data=brief.encode("utf-8"),
            file_name="final_brief.md",
            mime="text/markdown",
            use_container_width=True,
        )
elif not submitted:
    st.info(
        "Enter your planning assumptions and select **Generate launch plan**. "
        "A final brief appears here only after the backend completes successfully."
    )
