import sqlite3

import polars as pl

DB_PATH = "finance.db"
CSV_PATH = "./raw.csv"

# -----------------------------
# 0. READ CSV (TRUTHFUL INGEST)
# -----------------------------
df = pl.read_csv(CSV_PATH, separator=";", null_values=["", " "], infer_schema_length=0)

print("CSV loaded")
print("Columns:", len(df.columns))

# -----------------------------
# 1. FULL COLUMN RENAME MAP
# -----------------------------

COLUMN_RENAME_MAP = {
    # Identifiers & time
    "anio": "year",
    "expediente": "company_id",
    "posicion_general": "ranking",
    "cia_imvalores": "is_public",
    "id_estado_financiero": "statement_id",
    "tamaño_e": "company_size",
    # Core financials
    "ingresos_ventas": "revenue",
    "ingresos_totales": "total_income",
    "utilidad_neta": "net_income",
    "utilidad_ejercicio": "operating_income",
    "utilidad_an_imp": "income_before_tax",
    "impuesto_renta": "income_tax",
    # Balance sheet
    "activos": "total_assets",
    "pasivo": "total_liabilities",
    "patrimonio": "equity",
    "deuda_total": "total_debt",
    "deuda_total_c_plazo": "short_term_debt",
    # Liquidity & leverage
    "liquidez_corriente": "current_ratio",
    "prueba_acida": "quick_ratio",
    "end_activo": "asset_leverage",
    "end_patrimonial": "equity_leverage",
    "end_activo_fijo": "fixed_assets",
    "end_corto_plazo": "short_term_assets",
    "end_largo_plazo": "long_term_assets",
    "cobertura_interes": "interest_coverage",
    "apalancamiento": "leverage",
    "apalancamiento_financiero": "financial_leverage",
    "end_patrimonial_ct": "current_equity",
    "end_patrimonial_nct": "non_current_equity",
    "apalancamiento_c_l_plazo": "short_long_term_leverage",
    # Performance ratios
    "rot_cartera": "receivables_turnover",
    "rot_activo_fijo": "fixed_assets_turnover",
    "rot_ventas": "asset_turnover",
    "per_med_cobranza": "avg_collection_period",
    "per_med_pago": "avg_payment_period",
    "impac_gasto_a_v": "sales_expense_impact",
    "impac_carga_finan": "financial_burden",
    "rent_neta_activo": "roe_assets",
    "margen_bruto": "gross_margin",
    "margen_operacional": "operating_margin",
    "rent_neta_ventas": "net_sales_margin",
    "rent_ope_patrimonio": "roe_equity",
    "rent_ope_activo": "roe_assets_calc",
    "roe": "roe",
    "roa": "roa",
    "fortaleza_patrimonial": "equity_strength",
    # Costs & expenses
    "gastos_financieros": "financial_expenses",
    "gastos_admin_ventas": "sgna_expenses",
    "depreciaciones": "depreciation",
    "amortizaciones": "amortization",
    "costos_ventas_prod": "cost_of_goods_sold",
    "total_gastos": "total_expenses",
    # Additional / helper
    "n_empleados": "employee_count",
    "n": "n",
    "max": "max",
    "cod_segmento": "segment_code",
    "ciiu_n1": "industry_code_level1",
    "ciiu_n6": "industry_code_level6",
    "x": "x",
    "y": "y",
    # "_1" columns (duplicates / adjusted)
    "roa_1": "roa_1",
    "roe_1": "roe_1",
    "margen_bruto_1": "gross_margin_1",
    "end_activo_1": "asset_leverage_1",
    "end_patrimonial_1": "equity_leverage_1",
    "apalancamiento_1": "leverage_1",
    "rot_ventas_1": "asset_turnover_1",
    # Missing value flags
    "missing_roa": "missing_roa",
    "missing_roe": "missing_roe",
    "missing_margen_bruto": "missing_gross_margin",
    "missing_roa_1": "missing_roa_1",
    "missing_roe_1": "missing_roe_1",
    "missing_liquidez_corriente": "missing_current_ratio",
    "missing_end_activo": "missing_asset_leverage",
    "missing_end_activo_1": "missing_asset_leverage_1",
    "missing_end_patrimonial": "missing_equity_leverage",
    "missing_end_patrimonial_1": "missing_equity_leverage_1",
    "missing_end_activo_fijo": "missing_fixed_assets",
    "missing_apalancamiento": "missing_leverage",
    "missing_apalancamiento_1": "missing_leverage_1",
    "missing_fortaleza_patrimonial": "missing_equity_strength",
    "missing_rot_ventas": "missing_asset_turnover",
    "missing_rot_ventas_1": "missing_asset_turnover_1",
    "missing_rot_cartera": "missing_receivables_turnover",
    "missing_impac_carga_finan": "missing_financial_burden",
}

# -----------------------------
# 2. CATEGORY MAP
# -----------------------------
#
COLUMN_CATEGORIES = {
    # Identifiers & time
    "year": "time",
    "company_id": "entity",
    "ranking": "entity",
    "is_public": "entity",
    "statement_id": "entity",
    "company_size": "entity",
    "segment_code": "entity",
    "industry_code_level1": "entity",
    "industry_code_level6": "entity",
    "n": "meta",
    "max": "meta",
    "x": "meta",
    "y": "meta",
    # Financial statements
    "revenue": "income_statement",
    "total_income": "income_statement",
    "net_income": "income_statement",
    "operating_income": "income_statement",
    "income_before_tax": "income_statement",
    "income_tax": "income_statement",
    "total_assets": "balance_sheet",
    "equity": "balance_sheet",
    "total_liabilities": "balance_sheet",
    "total_debt": "balance_sheet",
    "short_term_debt": "balance_sheet",
    "fixed_assets": "balance_sheet",
    "short_term_assets": "balance_sheet",
    "long_term_assets": "balance_sheet",
    "current_equity": "balance_sheet",
    "non_current_equity": "balance_sheet",
    # Liquidity & leverage
    "current_ratio": "liquidity_ratio",
    "quick_ratio": "liquidity_ratio",
    "asset_leverage": "leverage_ratio",
    "equity_leverage": "leverage_ratio",
    "leverage": "leverage_ratio",
    "financial_leverage": "leverage_ratio",
    "short_long_term_leverage": "leverage_ratio",
    "interest_coverage": "leverage_ratio",
    # Performance ratios
    "asset_turnover": "efficiency_ratio",
    "receivables_turnover": "efficiency_ratio",
    "fixed_assets_turnover": "efficiency_ratio",
    "avg_collection_period": "efficiency_ratio",
    "avg_payment_period": "efficiency_ratio",
    "sales_expense_impact": "efficiency_ratio",
    "financial_burden": "efficiency_ratio",
    "roe_assets": "profitability_ratio",
    "roe_equity": "profitability_ratio",
    "roe_assets_calc": "profitability_ratio",
    "roe": "profitability_ratio",
    "roa": "profitability_ratio",
    "gross_margin": "profitability_ratio",
    "operating_margin": "profitability_ratio",
    "net_sales_margin": "profitability_ratio",
    "equity_strength": "profitability_ratio",
    # Costs & expenses
    "financial_expenses": "expense",
    "sgna_expenses": "expense",
    "depreciation": "expense",
    "amortization": "expense",
    "cost_of_goods_sold": "expense",
    "total_expenses": "expense",
    # Workforce
    "employee_count": "meta",
    # "_1" duplicates / adjusted
    "roa_1": "profitability_ratio",
    "roe_1": "profitability_ratio",
    "gross_margin_1": "profitability_ratio",
    "asset_leverage_1": "leverage_ratio",
    "equity_leverage_1": "leverage_ratio",
    "leverage_1": "leverage_ratio",
    "asset_turnover_1": "efficiency_ratio",
    # Missing value flags
    "missing_roa": "missing_flag",
    "missing_roe": "missing_flag",
    "missing_gross_margin": "missing_flag",
    "missing_roa_1": "missing_flag",
    "missing_roe_1": "missing_flag",
    "missing_current_ratio": "missing_flag",
    "missing_asset_leverage": "missing_flag",
    "missing_asset_leverage_1": "missing_flag",
    "missing_equity_leverage": "missing_flag",
    "missing_equity_leverage_1": "missing_flag",
    "missing_fixed_assets": "missing_flag",
    "missing_leverage": "missing_flag",
    "missing_leverage_1": "missing_flag",
    "missing_equity_strength": "missing_flag",
    "missing_asset_turnover": "missing_flag",
    "missing_asset_turnover_1": "missing_flag",
    "missing_receivables_turnover": "missing_flag",
    "missing_financial_burden": "missing_flag",
}

df = df.rename(
    {old: new for old, new in COLUMN_RENAME_MAP.items() if old in df.columns}
)

print("Columns renamed")

# -----------------------------
# 3. DEFINE COLUMN TYPES
# -----------------------------

INT_COLS = [
    # Identifiers & time
    "year",
    "company_id",
    "ranking",
    "is_public",
    "statement_id",
    "company_size",
    # Metadata / helpers
    "n",
    "max",
    # Workforce
    "employee_count",
    # Categorical codes
    "segment_code",
    "industry_code_level1",
    "industry_code_level6",
]

FLOAT_COLS = [
    # Income statement
    "revenue",
    "total_income",
    "net_income",
    "operating_income",
    "income_before_tax",
    "income_tax",
    # Balance sheet
    "total_assets",
    "total_assets_end",
    "total_assets_end_adjusted",
    "total_liabilities",
    "equity",
    "equity_strength",
    "fixed_assets",
    "short_term_assets",
    "long_term_assets",
    "equity_current",
    "equity_non_current",
    "total_equity_end",
    "total_equity_end_adjusted",
    # Debt / leverage
    "total_debt",
    "short_term_debt",
    "leverage",
    "financial_leverage",
    "short_long_term_leverage",
    "leverage_adjusted",
    "asset_leverage",
    "asset_leverage_1",
    "equity_leverage",
    "equity_leverage_1",
    # Liquidity
    "current_ratio",
    "quick_ratio",
    # Performance / efficiency
    "asset_turnover",
    "asset_turnover_1",
    "receivables_turnover",
    "fixed_assets_turnover",
    "avg_collection_period",
    "avg_payment_period",
    "sales_expense_impact",
    "financial_burden",
    # Profitability
    "roe_assets",
    "roe_equity",
    "roe_assets_calc",
    "roe",
    "roa",
    "roe_adjusted",
    "roa_adjusted",
    "gross_margin",
    "gross_margin_adjusted",
    "operating_margin",
    "net_sales_margin",
    # Costs / expenses
    "financial_expenses",
    "sgna_expenses",
    "depreciation",
    "amortization",
    "cost_of_goods_sold",
    "total_expenses",
    # Helper / coordinates
    "x",
    "y",
]

# -----------------------------
# 3. EUROPEAN DECIMAL CONVERSION
# -----------------------------


def euro_float(col):
    return (
        pl.when(pl.col(col).is_null())
        .then(None)
        .otherwise(
            pl.col(col)
            .str.replace(r"^,", "0,", literal=False)  # Replace leading comma with "0,"
            .str.replace(".", "", literal=True)  # Remove thousands separator
            .str.replace(",", ".", literal=True)  # Replace decimal comma with dot
            .cast(pl.Float64, strict=True)
        )
    )


df = df.with_columns(
    [
        pl.col(c).cast(pl.Int64, strict=False).alias(c)
        for c in INT_COLS
        if c in df.columns
    ]
)

df = df.with_columns([euro_float(c).alias(c) for c in FLOAT_COLS if c in df.columns])

print("Type conversion done")

# -----------------------------
# 4. CREATE SQLITE TABLE
# -----------------------------


def polars_to_sql(dtype):
    if dtype in (pl.Int64, pl.Int32):
        return "INTEGER"
    if dtype in (pl.Float64, pl.Float32):
        return "REAL"
    return "TEXT"


columns_sql = [f'"{name}" {polars_to_sql(dtype)}' for name, dtype in df.schema.items()]

create_sql = f"""
CREATE TABLE IF NOT EXISTS financial_records (
    record_id INTEGER PRIMARY KEY AUTOINCREMENT,
    {", ".join(columns_sql)}
);
"""

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
cursor.execute(create_sql)
conn.commit()

print("SQLite table created")

# -----------------------------
# 5. INSERT DATA
# -----------------------------

rows = df.to_dicts()

placeholders = ", ".join(["?"] * len(df.columns))
columns = ", ".join([f'"{c}"' for c in df.columns])

insert_sql = f"""
INSERT INTO financial_records ({columns})
VALUES ({placeholders})
"""

cursor.executemany(insert_sql, [tuple(row.values()) for row in rows])

conn.commit()
conn.close()

print("All data inserted successfully")
