# Financial Analysis Agent 📊

## TO CHANGE

# Sequential Financial Analysis Agent - Usage Guide

## 🎯 What Changed?

### Previous Architecture (Single Action)
```
User Query → Planner → Single Action → Executor → Result
```

### New Architecture (Sequential)
```
User Query → Planner → Multi-Step Plan → Sequential Executor → Results
                                              ↓
                                    State flows between steps
                                    (DataFrame, visualizations, tables)
```

## 📋 Architecture Overview

### 1. **Planner** (`agent/planner.py`)
**Changed**: Now outputs `{"steps": [...]}` instead of single action

- Creates multi-step execution plans
- Each step can use outputs from previous steps
- Validates all steps upfront
- Supports 11 different action types

### 2. **Executor** (`agent/executor.py`)
**Changed**: Now maintains state across steps

- `ExecutionState` class tracks:
  - Current DataFrame (modified by each step)
  - Generated visualizations
  - Summary tables
  - Exported files
  
- Executes steps sequentially
- Each step updates state for next step
- Comprehensive error handling per step

### 3. **Orchestrator** (`agent/orchestrator.py`)
**Changed**: Now coordinates multi-step execution

- Manages the complete pipeline
- Displays results progressively
- Tracks execution history
- Provides usage statistics

## 🚀 Usage Examples

### Example 1: Simple Sequential Workflow
```python
from agent.orchestrator import quick_query

state = quick_query(
    "Filter to companies 1-5, calculate profit margins, and plot the trend"
)

# Behind the scenes, this creates a plan like:
{
  "steps": [
    {
      "action": "filter_data",
      "conditions": [{"column": "company_id", "operator": "in", "value": [1,2,3,4,5]}]
    },
    {
      "action": "compute_margin",
      "numerator": "net_income",
      "denominator": "revenue",
      "output_col": "profit_margin"
    },
    {
      "action": "plot_trend",
      "metric": "profit_margin"
    }
  ]
}
```

### Example 2: Data Analysis Pipeline
```python
state = quick_query(
    "Filter to 2023, show summary statistics for revenue and assets, "
    "then export to CSV"
)

# Access results:
print(f"Tables generated: {len(state.tables)}")
print(f"Files exported: {state.exports}")
```

### Example 3: Complex Multi-Step Analysis
```python
from agent.orchestrator import FinancialAnalysisAgent

agent = FinancialAnalysisAgent()

state = agent.query(
    "Filter to years 2020-2023, compute ROE for each company, "
    "calculate 3-year rolling averages, plot the trends, "
    "show correlation with revenue, and create a comprehensive report"
)

# The planner will create ~5-6 steps
# The executor will run them sequentially
# Results accumulate in the state
```

### Example 4: Batch Processing
```python
agent = FinancialAnalysisAgent()

queries = [
    "Compare revenue across companies in 2023",
    "Calculate profit margins and show trends",
    "Export top 10 companies by ROE to Excel"
]

results = agent.batch_query(queries)

# Show statistics
agent.show_statistics()
```

### Example 5: Interactive Mode
```python
from agent.orchestrator import interactive_mode

interactive_mode()

# Then type queries like:
# "Filter to tech companies and plot revenue trends"
# "Calculate YoY growth and export to CSV"
# "stats" - to see usage
# "quit" - to exit
```

## 🔧 Available Actions (11 Total)

### Data Operations
1. **filter_data** - Subset data by conditions
2. **compute_summary_stats** - Calculate mean, median, std, etc.
3. **export_table** - Save to CSV/Excel

### Analysis Operations
4. **yoy_growth** - Year-over-year growth rates
5. **rolling_average** - Moving averages
6. **compute_margin** - Ratios between metrics
7. **compute_share** - Percentage calculations

### Visualization Operations
8. **plot_trend** - Time series line charts
9. **compare_companies** - Cross-sectional bar charts
10. **correlation** - Correlation heatmaps

### Reporting
11. **create_report** - Compile all results

## 📊 State Management

### ExecutionState Class
```python
class ExecutionState:
    df: pl.DataFrame              # Current working data
    visualizations: List[Figure]  # Generated plots
    tables: List[Dict]            # Summary tables
    exports: List[str]            # Exported file paths
    metadata: Dict                # Additional info
```

### How State Flows
```
Step 1: filter_data
  Input: Original DataFrame
  Output: Filtered DataFrame
  State: df updated

Step 2: compute_margin
  Input: Filtered DataFrame
  Output: DataFrame + new margin column
  State: df updated

Step 3: plot_trend
  Input: DataFrame with margin column
  Output: Plotly Figure
  State: visualization added

Step 4: export_table
  Input: Current DataFrame
  Output: CSV file
  State: export path added
```

## 🎨 Example Workflows

### Workflow 1: Financial Ratio Analysis
```
User: "Calculate profit margins for 2023 and compare top 5 companies"

Plan:
1. filter_data (year == 2023)
2. compute_margin (net_income / revenue)
3. filter_data (top 5 by margin)
4. compare_companies (profit_margin, 2023)
```

### Workflow 2: Time Series Analysis
```
User: "Show 3-year moving average of revenue for companies 1-10"

Plan:
1. filter_data (company_id in [1...10])
2. rolling_average (revenue, window=3)
3. plot_trend (revenue_rolling_3)
```

### Workflow 3: Comprehensive Report
```
User: "Filter to 2020-2023, compute ROE, show stats and trends, export everything"

Plan:
1. filter_data (2020 <= year <= 2023)
2. compute_margin (net_income / equity → ROE)
3. compute_summary_stats (ROE, group_by=year


AI-powered financial data analysis agent using Mistral LLM via Ollama. Query financial data using natural language and get comprehensive analysis with visualizations.

## Features

- 🤖 **Natural Language Interface**: Ask questions in plain English
- 📈 **Automated Visualizations**: Revenue trends, profitability ratios, comparative analysis
- 🔍 **Intelligent Planning**: Mistral LLM creates optimal execution plans
- 📊 **Interactive Dashboard**: Streamlit-based UI with chat interface
- 🛠️ **Extensible Tools**: Modular plotting and calculation functions

## Project Structure

```
.
├── agent/                  # Agent core logic
│   ├── orchestrator.py     # Main orchestrator
│   ├── planner.py          # LLM-based planning
│   ├── executor.py         # Tool execution
├── tools/                  # Analysis tools
│   ├── visualization.py    # Plotly visualizations
│   ├── mapping.py          # Tool mapping
│   ├── reporting.py        # Report creation
│   └── analysis.py         # Financial calculations
├── scripts/               # Setup scripts
│   └── clean_dataset.py   # Data preprocessing
├── data/                  # Data directory
│   ├── processed.csv      # Processed data
│   └── raw.csv            # Raw CSV data
└── app.py                 # Streamlit app

```

## Setup

### Prerequisites

- Python 3.12+
- Ollama
- Mistral model for Ollama

### 1. Install Dependencies

```bash
pip install polars plotly streamlit requests
```

### 2. Install and Setup Ollama

```bash
# Install Ollama (macOS/Linux)
curl -fsSL https://ollama.ai/install.sh | sh

# Start Ollama server
ollama serve

# In another terminal, pull Mistral
ollama pull mistral
```

### 3. Initialize Database

```bash
# Create database from CSV
python scripts/init_db.py

# Normalize into proper tables
python scripts/normalize_db.py
```

### 4. Verify Setup

```bash
# Test the CLI agent
python agent/runner.py
```

## Usage

### Streamlit App (Recommended)

```bash
streamlit run app.py
```

Then open your browser to `http://localhost:8501`

### CLI Interface

```bash
python agent/runner.py
```

### Example Queries

**Revenue Analysis:**
- "Show me the revenue trend for companies 1, 2, and 3 from 2015 to 2020"
- "How has company 1's revenue grown from 2015 to 2020?"

**Profitability Analysis:**
- "Compare the ROE of companies 1, 2, 3 in 2020"
- "What is the average ROA across all companies in 2020?"
- "Show profitability ratios for company 1 from 2018 to 2020"

**Comparative Analysis:**
- "Compare company 1's ROE against its industry in 2020"
- "Which companies have the highest revenue in 2020?"

**Dashboards:**
- "Show me a dashboard for company 1 in 2020"
- "Create a financial health overview for company 5 in 2019"

## Available Tools

### Plotting Tools

- `plot_revenue_trend()` - Revenue over time
- `plot_profitability()` - ROE, ROA, Net Margin
- `plot_net_income_trend()` - Net income over time
- `plot_comparison()` - Compare companies on a metric
- `plot_industry_benchmark()` - Company vs industry
- `plot_dashboard()` - Comprehensive financial dashboard
- `plot_correlation()` - Metric correlations

### Calculation Tools

- `query_database()` - Execute SQL queries
- `calculate_growth_rate()` - CAGR and growth metrics
- `calculate_aggregate_stats()` - Statistical aggregations

## Configuration

Edit `utils/config.py` or set environment variables:

```bash
export FINANCE_DB_PATH="../data/finance.db"
export OLLAMA_URL="http://localhost:11434"
export OLLAMA_MODEL="mistral"
export AGENT_MAX_RETRIES=2
```

## Architecture

### 1. User Query
User asks a natural language question via Streamlit or CLI

### 2. Planning Phase
`AgentPlanner` uses Mistral to:
- Analyze the query
- Break it into steps
- Select appropriate tools
- Generate execution plan

### 3. Execution Phase
`ToolExecutor` runs the plan:
- Executes SQL queries
- Generates visualizations
- Performs calculations
- Collects results

### 4. Response Generation
`FinancialAgent` synthesizes:
- Tool results into natural language
- Displays plots and tables
- Returns comprehensive response

## Agent Flow

```
User Query
    ↓
[AgentPlanner]
    ↓
Execution Plan
    ↓
[ToolExecutor]
    ↓
Tool Results
    ↓
[Response Generator]
    ↓
Final Answer + Visualizations
```

## Extending the Agent

### Add New Plotting Function

1. Add function to `tools/plotting.py`
2. Define tool schema in `agent/schema.py`
3. Add routing in `agent/executor.py`

### Add New Calculation

1. Add function to `tools/calculations.py`
2. Define tool schema in `agent/schema.py`
3. Add routing in `agent/executor.py`

## Troubleshooting

### "Ollama is not running"
```bash
# Start Ollama
ollama serve
```

### "Model 'mistral' not found"
```bash
# Pull the model
ollama pull mistral
```

### "Database not found"
```bash
# Check database path
ls -la data/finance.db

# Reinitialize if needed
python scripts/init_db.py
python scripts/normalize_db.py
```

### "No module named 'polars'"
```bash
# Install dependencies
pip install polars plotly streamlit requests
```

## Performance Tips

- **Limit company_ids**: Query fewer companies for faster responses
- **Use specific years**: Narrow date ranges reduce processing time
- **Cache results**: The database has indexes on key columns

## Known Limitations

- No support for localStorage (runs in standard Python environment)
- Requires local Ollama installation
- Database must fit in memory for Polars operations
- Single-user operation (no concurrent request handling)

## Future Enhancements

- [ ] Add more financial metrics (P/E ratio, debt ratios, etc.)
- [ ] Support for custom metric definitions
- [ ] Export reports to PDF/Excel
- [ ] Multi-year comparative analysis
- [ ] Industry sector analysis
- [ ] Forecasting and trend prediction
- [ ] API endpoint for programmatic access

## License

MIT License - feel free to use and modify for your needs

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## Support

For issues and questions:
- Check the troubleshooting section above
- Review example queries in the sidebar
- Inspect agent execution details in Streamlit
