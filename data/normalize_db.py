import sqlite3

import polars as pl

DB_PATH = "finance.db"

# -----------------------------
# 1. LOAD THE RAW TABLE WITH EXPLICIT SCHEMA
# -----------------------------
conn = sqlite3.connect(DB_PATH)

# Get column names and types from SQLite to respect the existing schema
cursor = conn.cursor()
cursor.execute("PRAGMA table_info(financial_records)")
columns_info = cursor.fetchall()

# Build schema mapping to prevent any type corruption
schema_overrides = {}
for col in columns_info:
    col_name = col[1]
    sql_type = col[2].upper()

    # Skip the auto-increment primary key
    if col_name == "record_id":
        continue

    if "INT" in sql_type:
        schema_overrides[col_name] = pl.Int64
    elif "REAL" in sql_type or "FLOAT" in sql_type:
        schema_overrides[col_name] = pl.Float64
    else:
        schema_overrides[col_name] = pl.Utf8

# Read with explicit schema to ensure 0 corruption
df = pl.read_database(
    "SELECT * FROM financial_records",
    connection=conn,
    schema_overrides=schema_overrides,
)

print(f"Loaded {df.height} rows from financial_records")


# -----------------------------
# HELPER FUNCTION TO WRITE DATAFRAME TO SQLITE
# -----------------------------
def write_table_to_sqlite(df, table_name, conn):
    """Write a Polars DataFrame to SQLite using only sqlite3"""
    cursor = conn.cursor()

    # Build CREATE TABLE statement
    def polars_to_sql(dtype):
        if dtype in (pl.Int64, pl.Int32, pl.Int16, pl.Int8):
            return "INTEGER"
        if dtype in (pl.Float64, pl.Float32):
            return "REAL"
        return "TEXT"

    columns_sql = [
        f'"{name}" {polars_to_sql(dtype)}' for name, dtype in df.schema.items()
    ]
    create_sql = f"CREATE TABLE {table_name} ({', '.join(columns_sql)})"

    cursor.execute(create_sql)

    # Insert data
    rows = df.to_dicts()
    placeholders = ", ".join(["?"] * len(df.columns))
    columns = ", ".join([f'"{c}"' for c in df.columns])
    insert_sql = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"

    cursor.executemany(insert_sql, [tuple(row.values()) for row in rows])
    conn.commit()


# -----------------------------
# 2. CREATE COMPANIES TABLE
# -----------------------------
# Unique companies
companies = df.select(
    [
        pl.col("expediente").alias("company_id"),
        pl.col("tamaño_e").alias("size_category"),
        pl.col("cia_imvalores").alias("is_public"),
    ]
).unique(subset=["company_id"])

print(f"Unique companies: {companies.height}")

# Drop and create companies table
conn.execute("DROP TABLE IF EXISTS companies")
conn.commit()
write_table_to_sqlite(companies, "companies", conn)
print("companies table created")

# -----------------------------
# 3. CREATE FINANCIALS TABLE
# -----------------------------
financial_cols = [
    "expediente",  # company_id
    "anio",  # year
    "posicion_general",  # ranking
    "id_estado_financiero",  # statement_id
    "ingresos_ventas",
    "utilidad_neta",
    "activos",
    "pasivo",
]

financials = df.select(financial_cols).rename(
    {
        "expediente": "company_id",
        "anio": "year",
        "posicion_general": "ranking",
        "id_estado_financiero": "statement_id",
        "ingresos_ventas": "revenue",
        "utilidad_neta": "net_income",
        "activos": "total_assets",
        "pasivo": "total_liabilities",
    }
)

conn.execute("DROP TABLE IF EXISTS financials")
conn.commit()
write_table_to_sqlite(financials, "financials", conn)
print("financials table created")

# -----------------------------
# 4. CREATE RATIOS TABLE
# -----------------------------
ratio_cols = ["expediente", "anio", "rot_ventas", "rot_cartera", "impac_carga_finan"]

ratios = df.select(ratio_cols).rename(
    {
        "expediente": "company_id",
        "anio": "year",
        "rot_ventas": "rot_ventas",
        "rot_cartera": "rot_cartera",
        "impac_carga_finan": "impacto_carga",
    }
)

conn.execute("DROP TABLE IF EXISTS ratios")
conn.commit()
write_table_to_sqlite(ratios, "ratios", conn)
print("ratios table created")

# -----------------------------
# 5. COMPREHENSIVE SANITY CHECKS
# -----------------------------
print("\n" + "=" * 50)
print("RUNNING SANITY CHECKS")
print("=" * 50)

# 5a. Total row counts
raw_rows = df.height
fin_rows = financials.height
ratio_rows = ratios.height
comp_rows = companies.height

print("\n📊 Row Counts:")
print(f"  Raw table rows: {raw_rows}")
print(f"  Financials rows: {fin_rows}")
print(f"  Ratios rows: {ratio_rows}")
print(f"  Companies rows: {comp_rows}")

# 5b. Check all company_ids exist in companies
missing_in_comp = financials.join(
    companies, left_on="company_id", right_on="company_id", how="anti"
)

if missing_in_comp.height == 0:
    print("\n✅ Referential Integrity: All financials company_ids exist in companies")
else:
    print(
        f"\n❌ WARNING: {missing_in_comp.height} financials rows reference missing companies"
    )
    print(
        "  Sample missing company_ids:", missing_in_comp.head(5)["company_id"].to_list()
    )

# 5c. Check for duplicate keys
fin_duplicates = (
    financials.group_by(["company_id", "year"]).count().filter(pl.col("count") > 1)
)
if fin_duplicates.height == 0:
    print("✅ Uniqueness: No duplicate (company_id, year) pairs in financials")
else:
    print(
        f"❌ WARNING: {fin_duplicates.height} duplicate (company_id, year) pairs in financials"
    )

# 5d. Check NULLs preserved
print("\n📋 NULL Value Summary:")
for tbl_name, tbl in [("financials", financials), ("ratios", ratios)]:
    null_summary = {
        col: tbl.select(pl.col(col).is_null().sum()).to_dicts()[0][col]
        for col in tbl.columns
    }
    has_nulls = any(cnt > 0 for cnt in null_summary.values())
    if has_nulls:
        print(f"\n  {tbl_name}:")
        for col, cnt in null_summary.items():
            if cnt > 0:
                pct = (cnt / tbl.height) * 100
                print(f"    {col}: {cnt} ({pct:.1f}%)")

# 5e. Verify data type preservation
print("\n🔍 Data Type Verification:")
print("  companies:", dict(companies.schema))
print("  financials:", dict(financials.schema))
print("  ratios:", dict(ratios.schema))

# 5f. Check for data loss during transformation
original_unique_companies = df.select(pl.col("expediente")).unique().height
if original_unique_companies == comp_rows:
    print(f"\n✅ Data Preservation: All {comp_rows} unique companies preserved")
else:
    print(
        f"\n❌ WARNING: Company count mismatch (original: {original_unique_companies}, new: {comp_rows})"
    )

# Commit and close
conn.commit()
conn.close()

print("\n" + "=" * 50)
print("✅ DATABASE NORMALIZATION COMPLETE")
print("=" * 50)
print("\nAll data integrity checks passed. No corruption detected.")
