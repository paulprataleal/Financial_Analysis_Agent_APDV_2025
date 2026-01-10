# app.py

"""
Sequential Financial Analysis Streamlit App
-------------------------------------------

Supports multi-step workflows with state visualization.
"""

import os
from pathlib import Path

import plotly.graph_objects as go
import polars as pl
import streamlit as st

from src.agent.orchestrator import FinancialAnalysisAgent
from src.agent.planner import explain_plan

# ============================================================
# Page Configuration
# ============================================================

st.set_page_config(
    page_title="Financial Consultant", layout="wide", initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown(
    """
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .report-container {
        background-color: white;
        padding: 30px;
        border-radius: 15px;
        border: 1px solid #e0e0e0;
    }
    .step-indicator {
        background-color: #e3f2fd;
        padding: 10px;
        border-radius: 5px;
        border-left: 4px solid #2196F3;
        margin: 10px 0;
    }
    .success-box {
        background-color: #e8f5e9;
        padding: 15px;
        border-radius: 5px;
        border-left: 4px solid #4caf50;
    }
    .warning-box {
        background-color: #fff3e0;
        padding: 15px;
        border-radius: 5px;
        border-left: 4px solid #ff9800;
    }
    .error-box {
        background-color: #ffebee;
        padding: 15px;
        border-radius: 5px;
        border-left: 4px solid #f44336;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# Session State Initialization
# ============================================================

if "agent" not in st.session_state:
    st.session_state.agent = FinancialAnalysisAgent(
        data_path="data/processed.csv", model="mistral:latest", verbose=False
    )

if "execution_history" not in st.session_state:
    st.session_state.execution_history = []

if "show_advanced" not in st.session_state:
    st.session_state.show_advanced = False


# ============================================================
# Helper Functions
# ============================================================


def display_execution_plan(plan):
    """Display the execution plan in a formatted way."""

    if "steps" not in plan:
        st.info("Single-step plan")
        return

    st.markdown("### 📋 Execution Plan")

    for i, step in enumerate(plan["steps"], 1):
        action = step.get("action", "unknown")

        with st.expander(f"Step {i}: **{action}**", expanded=False):
            st.json(step)


def display_execution_state(state):
    """Display the execution state results."""

    if state is None:
        st.error("No results to display")
        return

    # Get summary
    summary = state.get_summary()

    # Display metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("DataFrame Rows", f"{summary['dataframe_shape'][0]:,}", delta=None)

    with col2:
        st.metric("DataFrame Columns", summary["dataframe_shape"][1], delta=None)

    with col3:
        st.metric("Visualizations", summary["num_visualizations"], delta=None)

    with col4:
        st.metric("Exports", summary["num_exports"], delta=None)

    # Display visualizations
    if state.visualizations:
        st.markdown("---")
        st.markdown("### 📊 Visualizations")

        for i, viz in enumerate(state.visualizations):
            title = viz.get("title", f"Visualization {i + 1}")
            fig = viz["figure"]

            st.markdown(f"**{title}**")
            st.plotly_chart(fig, use_container_width=True)

            if i < len(state.visualizations) - 1:
                st.markdown("---")

    # Display tables
    if state.tables:
        st.markdown("---")
        st.markdown("### 📋 Summary Tables")

        for i, table in enumerate(state.tables):
            title = table.get("title", f"Table {i + 1}")
            data = table["data"]

            st.markdown(f"**{title}**")

            # Display as dataframe if it's a Polars DataFrame
            if isinstance(data, pl.DataFrame):
                st.dataframe(data, use_container_width=True)
            else:
                st.write(data)

            if i < len(state.tables) - 1:
                st.markdown("---")

    # Display exports
    if state.exports:
        st.markdown("---")
        st.markdown("### 💾 Exported Files")

        for filepath in state.exports:
            st.success(f"✅ Exported to: `{filepath}`")

    # Display current DataFrame preview
    if st.session_state.show_advanced:
        st.markdown("---")
        st.markdown("### 🔍 Current DataFrame Preview")

        with st.expander("View Data", expanded=False):
            st.dataframe(state.df.head(20), use_container_width=True)

            st.markdown(f"**Shape:** {state.df.shape}")
            st.markdown(f"**Columns:** {', '.join(state.df.columns)}")


def display_warnings(warnings):
    """Display warning messages."""

    if not warnings:
        return

    st.markdown("### ⚠️ Warnings")

    for warning in warnings:
        st.warning(warning)


def display_warnings(warnings):
    """Display warning messages."""

    if not warnings:
        return

    st.markdown("### ⚠️ Warnings")

    for warning in warnings:
        st.warning(warning)


# ============================================================
# Main Interface
# ============================================================

st.title("🏦 Financial Consultant")
st.subheader("AI-Powered Sequential Analysis & Reporting")

# Example queries
with st.expander("💡 Example Queries", expanded=False):
    st.markdown("""
    **Simple Queries:**
    - "Show revenue trends for companies 1, 2, and 3"
    - "Compare net income across companies in 2023"
    - "Plot correlation between revenue, assets, and equity"

    **Sequential Workflows:**
    - "Filter to companies 1-5, calculate profit margins, and plot trends"
    - "Show summary statistics for revenue in 2023, then export to CSV"
    - "Filter to 2020-2023, compute ROE, plot trends, and create a report"

    **Complex Analysis:**
    - "Filter to year >= 2020, compute 3-year rolling average of revenue, plot trends, and export to Excel"
    - "Calculate profit margins for all companies, filter to top 10, show comparison chart and summary stats"
    - "Compute ROE and ROA, show correlation with revenue, export results to CSV"
    """)

# Query input
user_input = st.text_input(
    label="Query Input",
    label_visibility="collapsed",
    placeholder="e.g., Filter to companies 1-5, calculate profit margins, plot trends, and export to CSV",
    key="query_input",
)

# Execution controls
col1, col2, col3 = st.columns([2, 1, 1])

with col2:
    show_plan = st.checkbox("Show Plan", value=True)

with col3:
    st.session_state.show_advanced = st.checkbox(
        "Advanced View", value=st.session_state.show_advanced
    )

# Process query
if user_input:
    with st.spinner("🤔 Planning and executing..."):
        try:
            # Import planner to show plan separately
            from src.agent.planner import create_plan

            # Create plan
            plan = create_plan(user_input, model="mistral:latest")

            # Show plan if requested
            if show_plan:
                display_execution_plan(plan)
                st.markdown("---")

            # Execute plan
            from src.agent.executor import execute_sequential_plan

            result = execute_sequential_plan(
                plan, data_path="data/processed.csv", verbose=False
            )

            # Display results
            if result.success:
                st.markdown(
                    '<div class="success-box">✅ <b>Execution completed successfully!</b></div>',
                    unsafe_allow_html=True,
                )
                st.markdown("")

                # Show warnings if any
                if result.warnings:
                    display_warnings(result.warnings)
                    st.markdown("---")

                # Display execution state
                display_execution_state(result.state)

                # Save to history
                st.session_state.execution_history.append(
                    {
                        "query": user_input,
                        "plan": plan,
                        "success": True,
                        "summary": result.state.get_summary(),
                    }
                )

            else:
                st.markdown(
                    f'<div class="error-box">❌ <b>Execution failed:</b> {result.error_type}</div>',
                    unsafe_allow_html=True,
                )
                st.error(result.error)

                # Save to history
                st.session_state.execution_history.append(
                    {
                        "query": user_input,
                        "plan": plan,
                        "success": False,
                        "error": result.error,
                    }
                )

        except Exception as e:
            st.markdown(
                f'<div class="error-box">❌ <b>Error:</b> {str(e)}</div>',
                unsafe_allow_html=True,
            )

            import traceback

            with st.expander("Show Traceback"):
                st.code(traceback.format_exc())


# ============================================================
# Sidebar
# ============================================================

with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3135/3135706.png", width=100)
    st.title("Advisor Panel")

    st.markdown("""
    **System Status:** 🟢 Online
    **Database:** `data/processed.csv`
    **AI Model:** Mistral Large
    **Mode:** Sequential Execution
    """)

    st.markdown("---")

    # Analysis Capabilities
    st.markdown("### 🎯 Capabilities")

    with st.expander("Data Operations", expanded=False):
        st.markdown("""
        - 🔍 Filter data by conditions
        - 📊 Summary statistics
        - 💾 Export to CSV/Excel
        """)

    with st.expander("Analysis Tools", expanded=False):
        st.markdown("""
        - 📈 YoY growth rates
        - 📉 Rolling averages
        - 🔢 Margin calculations
        - 📊 Share computations
        """)

    with st.expander("Visualizations", expanded=False):
        st.markdown("""
        - 📈 Trend plots (time series)
        - 📊 Company comparisons
        - 🔥 Correlation heatmaps
        """)

    st.markdown("---")

    # Execution History
    st.markdown("### 📜 History")

    if st.session_state.execution_history:
        total = len(st.session_state.execution_history)
        successful = sum(
            1 for h in st.session_state.execution_history if h.get("success", False)
        )

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total", total)
        with col2:
            st.metric("Success", successful)

        # Show recent queries
        st.markdown("**Recent Queries:**")

        for i, entry in enumerate(reversed(st.session_state.execution_history[-5:]), 1):
            query = entry["query"]
            success = entry.get("success", False)
            icon = "✅" if success else "❌"

            # Truncate long queries
            if len(query) > 40:
                query = query[:40] + "..."

            st.markdown(f"{icon} {query}")

    else:
        st.info("No queries executed yet")

    st.markdown("---")

    # Actions
    st.markdown("### ⚙️ Actions")

    if st.button("🗑️ Clear History", use_container_width=True):
        st.session_state.execution_history = []
        st.session_state.agent.clear_history()
        st.rerun()

    if st.button("📊 Show Statistics", use_container_width=True):
        st.session_state.agent.show_statistics()

    if st.button("💾 Export History", use_container_width=True):
        st.session_state.agent.export_history("streamlit_history.json")
        st.success("History exported to outputs/streamlit_history.json")

    st.markdown("---")

    # Settings
    with st.expander("⚙️ Settings", expanded=False):
        st.markdown("**Data Path:**")
        st.code("data/processed.csv", language="text")

        st.markdown("**Model:**")
        st.code("mistral:latest", language="text")

        st.markdown("**Capabilities:**")
        st.markdown("✅ Sequential execution")
        st.markdown("✅ State management")
        st.markdown("✅ Multi-step workflows")


# ============================================================
# Footer
# ============================================================

st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666; padding: 20px;'>
        <p>Financial Consultant v2.0 | Sequential Analysis Engine</p>
        <p>Powered by Mistral AI & Polars | Built with Streamlit</p>
    </div>
    """,
    unsafe_allow_html=True,
)
