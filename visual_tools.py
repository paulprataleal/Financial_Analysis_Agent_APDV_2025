import pandas as pd
import matplotlib.pyplot as plt
from typing import List

def plot_line(
    df: pd.DataFrame,
    x_col: str,
    y_cols: List[str],
    title: str | None = None
):
    """
    Plots one or multiple time series as a line chart.
    """
    plt.figure(figsize=(8, 4))

    for col in y_cols:
        plt.plot(df[x_col], df[col], label=col)

    plt.xlabel(x_col)
    plt.ylabel("Value")
    plt.title(title or "Line Chart")
    plt.legend()
    plt.tight_layout()
    plt.show()

def plot_bar(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    title: str | None = None
):
    """
    Plots a bar chart for comparison across categories or periods.
    """
    plt.figure(figsize=(8, 4))
    plt.bar(df[x_col], df[y_col])

    plt.xlabel(x_col)
    plt.ylabel(y_col)
    plt.title(title or "Bar Chart")
    plt.tight_layout()
    plt.show()

# Example data
data = {
    "year": [2020, 2021, 2022, 2023],
    "sales": [100, 120, 90, 130],
    "profit": [20, 25, 15, 30]
}

df = pd.DataFrame(data)
