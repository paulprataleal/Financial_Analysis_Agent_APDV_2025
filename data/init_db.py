import sqlite3

import polars as pl

DB_PATH = "finance.db"
CSV_PATH = "./raw.csv"

# -----------------------------
# 1. READ CSV (TRUTHFUL INGEST)
# -----------------------------
df = pl.read_csv(CSV_PATH, separator=";", null_values=["", " "], infer_schema_length=0)

print("CSV loaded")
print("Columns:", len(df.columns))

# -----------------------------
# 2. DEFINE COLUMN TYPES
# -----------------------------

INT_COLS = [
    "anio",
    "expediente",
    "posicion_general",
    "cia_imvalores",
    "id_estado_financiero",
    "n_empleados",
    "n",
    "max",
    "tamaño_e",
]

FLOAT_COLS = [
    "ingresos_ventas",
    "activos",
    "patrimonio",
    "pasivo",
    "utilidad_an_imp",
    "impuesto_renta",
    "ingresos_totales",
    "utilidad_ejercicio",
    "utilidad_neta",
    "liquidez_corriente",
    "prueba_acida",
    "end_activo",
    "end_patrimonial",
    "end_activo_fijo",
    "end_corto_plazo",
    "end_largo_plazo",
    "cobertura_interes",
    "apalancamiento",
    "apalancamiento_financiero",
    "end_patrimonial_ct",
    "end_patrimonial_nct",
    "apalancamiento_c_l_plazo",
    "rot_cartera",
    "rot_activo_fijo",
    "rot_ventas",
    "per_med_cobranza",
    "per_med_pago",
    "impac_gasto_a_v",
    "impac_carga_finan",
    "rent_neta_activo",
    "margen_bruto",
    "margen_operacional",
    "rent_neta_ventas",
    "rent_ope_patrimonio",
    "rent_ope_activo",
    "roe",
    "roa",
    "fortaleza_patrimonial",
    "gastos_financieros",
    "gastos_admin_ventas",
    "depreciaciones",
    "amortizaciones",
    "costos_ventas_prod",
    "deuda_total",
    "deuda_total_c_plazo",
    "total_gastos",
    "roa_1",
    "roe_1",
    "x",
    "y",
    "margen_bruto_1",
    "end_activo_1",
    "end_patrimonial_1",
    "apalancamiento_1",
    "rot_ventas_1",
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
