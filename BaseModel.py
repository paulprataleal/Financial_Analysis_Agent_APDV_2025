import pandas as pd
import matplotlib.pyplot as plt
from reporting_tool import generate_pdf_report
from financial_tools import (
    yoy_growth,
    rolling_average,
    period_growth,
    compute_margin,
    compute_share,
    index_series,
    flag_invalid_values,
    flag_anomalous_margin,
)
from visual_tools import plot_line, plot_bar
from typing import List, Optional, Dict, Union
from ollama import Client
from pydantic import BaseModel
from typing import Literal
import json

# ----------------------------
# Example DataFrame
# ----------------------------
df_example = pd.DataFrame({
    "date": pd.date_range("2022-12-31", periods=5, freq="YE"),
    "revenue": [100, 120, 130, 150, 160],
    "cost": [60, 70, 75, 80, 90],
    "net_income": [30, 35, 40, 50, 55],
    "total_income": [100, 120, 130, 150, 160],
    "roa": [0.10, 0.12, 0.11, 0.13, 0.14]
})

AVAILABLE_COLUMNS = list(df_example.columns)

# ----------------------------
# Pydantic Models
# ----------------------------
class ToolCall(BaseModel):
    name: Literal[
        "yoy_growth", "period_growth", "rolling_average",
        "compute_margin", "compute_share", "index_series",
        "flag_invalid_values", "flag_anomalous_margin"
    ]
    params: Optional[Dict[str, Union[str, int, float, List[Union[str,int,float]]]]] = {}

class Plan(BaseModel):
    action: Literal["compute", "visualize"]
    metrics: List[str]
    tools: List[ToolCall]

class Visualization(BaseModel):
    type: Literal["line", "bar"]
    x_col: str
    y_cols: List[str]
    title: Optional[str] = None

class Plan(BaseModel):
    action: Literal["compute", "visualize"]
    metrics: List[str]
    tools: List[ToolCall]
    visualization: Optional[Visualization] = None

# ----------------------------
# SYSTEM PROMPT (ROBUSTO)
# ----------------------------
SYSTEM_PROMPT = f"""
You are a financial analyst assistant.

STRICT INSTRUCTIONS:
- Return STRICT JSON ONLY. No markdown, explanations, or extra text.
- JSON format MUST be:
{{
  "action": "compute" or "visualize",
  "metrics": [list of metric names exactly as in dataset],
  "tools": [
    {{
      "name": "tool_function_name",
      "params": {{}}
    }}
  ]
}}

Dataset columns available:
{AVAILABLE_COLUMNS}

Available tools and parameters:
- yoy_growth: value_col, periods (int, optional), output_col (optional)
- period_growth: value_col, periods (int, optional), output_col (optional)
- rolling_average: value_col, window, output_col (optional)
- compute_margin: numerator_col, denominator_col, output_col
- compute_share: value_col, total_col, output_col
- index_series: value_col, base_period (int, optional), output_col (optional)
- flag_invalid_values: cols (list of strings), allow_zero (bool, optional)
- flag_anomalous_margin: net_income_col, total_income_col, output_col (optional)

RULES:
- Only use columns in the dataset.
- For "growth", "trend", "increase", "evolution", or "change", use yoy_growth.
- For "rolling average" or "trend over periods", use rolling_average with window=5 by default.
- For margins or ratios, use compute_margin or compute_share with proper columns.
- For invalid values or anomalies, use flag_invalid_values or flag_anomalous_margin.
- Never return results; only a plan.

EXAMPLE JSON:
{{
  "action": "compute",
  "metrics": ["revenue"],
  "tools": [
    {{
      "name": "yoy_growth",
      "params": {{
        "value_col": "revenue",
        "periods": 1,
        "output_col": "revenue_yoy_growth"
      }}
    }}
  ]
}}

If the user asks for a chart or trend visualization:
- Add a "visualization" object to the plan.
- type: "line" or "bar" depending on the request.
- x_col: the column representing time, usually "date".
- y_cols: list of metrics to visualize.
- title: optional, a short descriptive title.
Always return STRICT JSON only. Do NOT include explanations.

"""

# ----------------------------
# Semantic Validation
# ----------------------------
def validate_plan_semantics(plan: Plan):
    errors = []
    for m in plan.metrics:
        if m not in AVAILABLE_COLUMNS:
            errors.append(f"Metric '{m}' does not exist in dataset.")
    for tool in plan.tools:
        params = tool.params or {}
        for key, value in params.items():
            if isinstance(value, str) and value in AVAILABLE_COLUMNS:
                continue
            if isinstance(value, list):
                for v in value:
                    if isinstance(v, str) and v not in AVAILABLE_COLUMNS:
                        errors.append(f"Column '{v}' in tool {tool.name} does not exist.")
    return errors

# ----------------------------
# Safe Plan (Robust)
# ----------------------------
def safe_plan(client, user_prompt, retries=3):
    for attempt in range(retries):
        try:
            resp = client.chat(
                model="mistral",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ]
            )
        except Exception as e:
            print(f"⚠️ LLM error attempt {attempt+1}: {e}")
            if attempt == retries-1:
                return Plan(action="compute", metrics=[], tools=[])
            continue

        raw = resp["message"]["content"]
        print("\n--- RAW MODEL OUTPUT ---")
        print(raw)
        print("------------------------\n")

        # Attempt to parse JSON
        try:
            data = json.loads(raw)
            # If tools missing, fallback to empty list
            if "tools" not in data:
                data["tools"] = []
            plan = Plan.model_validate(data)

            errors = validate_plan_semantics(plan)
            if not errors:
                return plan
        except Exception:
            pass

    # ---------- GENERIC FALLBACK ----------
    # Detect first column mentioned in the prompt that exists
    metric = next((col for col in AVAILABLE_COLUMNS if col in user_prompt.lower()), None)
    if metric:
        return Plan(
            action="compute",
            metrics=[metric],
            tools=[ToolCall(
                name="yoy_growth",
                params={"value_col": metric, "periods": 1, "output_col": f"{metric}_yoy_growth"}
            )]
        )
    # If no column found, return empty plan
    return Plan(action="compute", metrics=[], tools=[])

# ----------------------------
# Execute tools
# ----------------------------
def execute_tools(df, plan):
    TOOL_MAP = {
        "yoy_growth": yoy_growth,
        "period_growth": period_growth,
        "rolling_average": rolling_average,
        "compute_margin": compute_margin,
        "compute_share": compute_share,
        "index_series": index_series,
        "flag_invalid_values": flag_invalid_values,
        "flag_anomalous_margin": flag_anomalous_margin
    }

    results = df.copy()
    for tool in plan.tools:
        func = TOOL_MAP.get(tool.name)
        params = tool.params.copy()
        if tool.name in ["yoy_growth", "rolling_average", "period_growth", "index_series"]:
            params.setdefault("value_col", plan.metrics[0] if plan.metrics else None)
            params.setdefault("output_col", f"{params['value_col']}_{tool.name}" if params["value_col"] else None)
        try:
            results = func(results, **params)
        except Exception as e:
            print(f"⚠️ Skipping tool {tool.name} due to error: {e}")
    return results

def execute_visualization(df: pd.DataFrame, visualization: Visualization):
    if visualization.type == "line":
        plot_line(
            df,
            x_col=visualization.x_col,
            y_cols=visualization.y_cols,
            title=visualization.title
        )

    elif visualization.type == "bar":
        plot_bar(
            df,
            x_col=visualization.x_col,
            y_col=visualization.y_cols[0],
            title=visualization.title
        )


# ----------------------------
# Main
# ----------------------------
def dataframe_to_image_plotly(df, filename="results_table.png"):
    """
    Converts DataFrame to professional table using Plotly
    """
    import plotly.graph_objects as go
    import plotly.io as pio
    
    # Round numeric columns to 2 decimals
    df_display = df.copy()
    for col in df_display.columns:
        if df_display[col].dtype in ['float64', 'float32']:
            df_display[col] = df_display[col].round(2)
    
    # Create table
    fig = go.Figure(data=[go.Table(
        header=dict(
            values=list(df_display.columns),
            fill_color='#4472C4',
            align='center',
            font=dict(color='white', size=12, family='Arial', weight='bold')
        ),
        cells=dict(
            values=[df_display[col] for col in df_display.columns],
            fill_color=[['white', '#F2F2F2'] * len(df_display)],  # Alternating rows
            align='center',
            font=dict(color='black', size=10, family='Arial'),
            height=35
        )
    )])
    
    # Layout settings
    fig.update_layout(
        width=1000,
        height=max(300, len(df_display) * 45 + 120),
        margin=dict(l=10, r=10, t=30, b=10)
    )
    
    # Save as PNG
    pio.write_image(fig, filename, scale=2)
    
    return filename



if __name__ == "__main__":
    client = Client()
    question = input("💬 Financial question: ")

    plan = safe_plan(client, question)

    df_result = execute_tools(df_example, plan)

    # Print results
    print("\n📊 Calculated Results:")
    print(df_result.to_string(index=False))

    # Convert table to image
    table_image = dataframe_to_image_plotly(df_result)

    pdf = generate_pdf_report(
        analysis_text="Calculated Results",
        lang="English",
        image_paths=[table_image],
        custom_filename="Company_Analysis"
    )

    print(f"📄 Report generated: {pdf}")
