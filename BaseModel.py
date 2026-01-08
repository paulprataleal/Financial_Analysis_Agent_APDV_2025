import pandas as pd
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
# Financial Tools
# ----------------------------
def _check_columns(df: pd.DataFrame, cols: List[str]):
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")

def yoy_growth(df, value_col, periods=1, output_col=None):
    _check_columns(df, [value_col])
    out = df.copy()
    output_col = output_col or f"{value_col}_yoy_growth"
    out[output_col] = out[value_col].pct_change(periods=periods)
    return out

def rolling_average(df, value_col, window, output_col=None):
    _check_columns(df, [value_col])
    out = df.copy()
    output_col = output_col or f"{value_col}_rolling_{window}"
    out[output_col] = out[value_col].rolling(window=window).mean()
    return out

def period_growth(df, value_col, periods=1, output_col=None):
    _check_columns(df, [value_col])
    out = df.copy()
    output_col = output_col or f"{value_col}_period_growth"
    out[output_col] = out[value_col].pct_change(periods=periods)
    return out

def compute_margin(df, numerator_col, denominator_col, output_col):
    _check_columns(df, [numerator_col, denominator_col])
    out = df.copy()
    out[output_col] = out[numerator_col] / out[denominator_col]
    return out

def compute_share(df, value_col, total_col, output_col):
    _check_columns(df, [value_col, total_col])
    out = df.copy()
    out[output_col] = out[value_col] / out[total_col]
    return out

def index_series(df, value_col, base_period=0, output_col=None):
    _check_columns(df, [value_col])
    out = df.copy()
    output_col = output_col or f"{value_col}_index"
    base_value = out[value_col].iloc[base_period]
    out[output_col] = (out[value_col] / base_value) * 100
    return out

def flag_invalid_values(df, cols, allow_zero=False):
    out = df.copy()
    for col in cols:
        if allow_zero:
            out[f"{col}_invalid"] = out[col] < 0
        else:
            out[f"{col}_invalid"] = out[col] <= 0
    return out

def flag_anomalous_margin(df, net_income_col, total_income_col, output_col="anomalous_margin"):
    out = df.copy()
    out[output_col] = out[net_income_col] > out[total_income_col]
    return out

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

# ----------------------------
# SYSTEM PROMPT (ROBUSTO)
# ----------------------------
SYSTEM_PROMPT = f"""
You are a financial analyst assistant.
Return STRICT JSON only. No markdown, no explanations.

Dataset columns available:
{AVAILABLE_COLUMNS}

Rules:
- You MUST use only these columns. Never invent new columns.
- If the user asks for "growth", "increase", "trend", or "evolution", use the yoy_growth tool.
- If the user mentions a metric (e.g., "roa growth"), apply the tool to that exact column.
- Do NOT change the metric name unless explicitly asked.
- Do NOT use columns that are not in the dataset.

Available tools and their required parameters:

1. yoy_growth:
   - value_col (string)
   - periods (int, optional)
   - output_col (string, optional)

2. period_growth:
   - value_col (string)
   - periods (int, optional)
   - output_col (string, optional)

3. rolling_average:
   - value_col (string)
   - window (int)
   - output_col (string, optional)

4. compute_margin:
   - numerator_col (string)
   - denominator_col (string)
   - output_col (string)

5. compute_share:
   - value_col (string)
   - total_col (string)
   - output_col (string)

6. index_series:
   - value_col (string)
   - base_period (int, optional)
   - output_col (string, optional)

7. flag_invalid_values:
   - cols (list of strings)
   - allow_zero (bool, optional)

8. flag_anomalous_margin:
   - net_income_col (string)
   - total_income_col (string)
   - output_col (string, optional)

Default interpretation rule:
If the user asks for "growth", "increase", "trend", "evolution", or "change" of a metric:
- Use the yoy_growth tool.
- Set value_col to the metric mentioned by the user.
- Set periods = 1.
- Set output_col = "<metric>_yoy_growth".
- Do NOT invent new metrics or columns.
- Do NOT use any other tool unless explicitly requested.

"""

# ----------------------------
# Semantic Validation
# ----------------------------
def validate_plan_semantics(plan: Plan):
    errors = []

    # 1. Metrics must exist
    for m in plan.metrics:
        if m not in AVAILABLE_COLUMNS:
            errors.append(f"Metric '{m}' does not exist in dataset.")

    # 2. Tools must use valid columns
    for tool in plan.tools:
        params = tool.params or {}
        for key, value in params.items():
            if isinstance(value, str) and value in AVAILABLE_COLUMNS:
                continue
            if isinstance(value, list):
                for v in value:
                    if isinstance(v, str) and v not in AVAILABLE_COLUMNS:
                        errors.append(f"Column '{v}' in tool {tool.name} does not exist.")
            # If it's a string but not a column, ignore (could be output_col)

    return errors

# ----------------------------
# Safe Plan with semantic retry
# ----------------------------
def safe_plan(client, user_prompt, retries=3):
    for attempt in range(retries):
        resp = client.chat(
            model="mistral",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ]
        )
        raw = resp["message"]["content"]

        try:
            data = json.loads(raw)

            for tool in data.get("tools", []):
                if "params" not in tool or tool["params"] is None:
                    tool["params"] = {}

            plan = Plan.model_validate(data)

            errors = validate_plan_semantics(plan)
            if not errors:
                return plan

        except Exception:
            pass

    # ---------- FALLBACK AUTOMÁTICO ----------
    if "roa" in user_prompt.lower() and "growth" in user_prompt.lower():
        return Plan(
            action="compute",
            metrics=["roa"],
            tools=[
                ToolCall(
                    name="yoy_growth",
                    params={
                        "value_col": "roa",
                        "periods": 1,
                        "output_col": "roa_yoy_growth"
                    }
                )
            ]
        )

    raise RuntimeError(f"Could not generate a valid plan after {retries} attempts.")
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
            params.setdefault("value_col", plan.metrics[0])
            params.setdefault("output_col", f"{params['value_col']}_{tool.name}")

        try:
            results = func(results, **params)
        except Exception as e:
            print(f"⚠️ Skipping tool {tool.name} due to error: {e}")

    return results

# ----------------------------
# Main
# ----------------------------
if __name__ == "__main__":
    client = Client()
    user_question = input("💬 Enter your financial question: ")
    plan = safe_plan(client, user_question)

    print("Generated plan:")
    print(plan.model_dump_json(indent=2))

    df_result = execute_tools(df_example, plan)
    print("DataFrame results:")
    print(df_result)