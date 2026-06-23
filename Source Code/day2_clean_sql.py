from __future__ import annotations

import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy import create_engine


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "Datasets" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "Datasets" / "processed"
DOCUMENTATION_DIR = PROJECT_ROOT / "Documentation"
SCHEMA_PATH = PROJECT_ROOT / "Source Code" / "schema.sql"
QUERIES_PATH = PROJECT_ROOT / "Source Code" / "queries.sql"
DATA_DICTIONARY_PATH = DOCUMENTATION_DIR / "data_dictionary.md"
DB_PATH = PROJECT_ROOT / "bluestock_mf.db"

VALID_TRANSACTION_TYPES = {"SIP", "Lumpsum", "Redemption"}
VALID_KYC_STATUSES = {"Verified", "Pending", "Rejected"}


RAW_FILES = {
    "fund_master": "01_fund_master.csv",
    "nav": "02_nav_history.csv",
    "aum": "03_aum_by_fund_house.csv",
    "sip": "04_monthly_sip_inflows.csv",
    "category_inflows": "05_category_inflows.csv",
    "folios": "06_industry_folio_count.csv",
    "performance": "07_scheme_performance.csv",
    "transactions": "08_investor_transactions.csv",
    "holdings": "09_portfolio_holdings.csv",
    "benchmarks": "10_benchmark_indices.csv",
}


TABLE_TO_CLEAN_CSV = {
    "dim_fund": "clean_fund_master.csv",
    "fact_nav": "clean_nav.csv",
    "fact_aum": "clean_aum_by_fund_house.csv",
    "fact_sip_inflows": "clean_monthly_sip_inflows.csv",
    "fact_category_inflows": "clean_category_inflows.csv",
    "fact_industry_folios": "clean_industry_folio_count.csv",
    "fact_performance": "clean_performance.csv",
    "fact_transactions": "clean_transactions.csv",
    "fact_portfolio_holdings": "clean_portfolio_holdings.csv",
    "fact_benchmark_indices": "clean_benchmark_indices.csv",
}


def read_raw(name: str) -> pd.DataFrame:
    return pd.read_csv(RAW_DIR / RAW_FILES[name], low_memory=False)


def clean_text_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for column in df.columns:
        if not (pd.api.types.is_object_dtype(df[column]) or pd.api.types.is_string_dtype(df[column])):
            continue
        df[column] = df[column].astype("string").str.strip()
        df[column] = df[column].replace({"": pd.NA})
    return df


def as_code(series: pd.Series) -> pd.Series:
    return series.astype("string").str.strip().str.replace(r"\.0$", "", regex=True)


def parse_date(series: pd.Series, *, month_start: bool = False) -> pd.Series:
    parsed = pd.to_datetime(series, errors="coerce", format="mixed")
    if parsed.isna().sum():
        parsed_dayfirst = pd.to_datetime(series, errors="coerce", format="mixed", dayfirst=True)
        if parsed_dayfirst.isna().sum() < parsed.isna().sum():
            parsed = parsed_dayfirst
    if month_start:
        parsed = parsed.dt.to_period("M").dt.to_timestamp()
    return parsed.dt.strftime("%Y-%m-%d")


def clean_fund_master() -> pd.DataFrame:
    df = clean_text_columns(read_raw("fund_master"))
    df["amfi_code"] = as_code(df["amfi_code"])
    df["launch_date"] = parse_date(df["launch_date"])
    numeric_columns = [
        "expense_ratio_pct",
        "exit_load_pct",
        "min_sip_amount",
        "min_lumpsum_amount",
    ]
    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    df["min_sip_amount"] = df["min_sip_amount"].astype("Int64")
    df["min_lumpsum_amount"] = df["min_lumpsum_amount"].astype("Int64")
    df = df.drop_duplicates(subset=["amfi_code"], keep="first")
    required = ["amfi_code", "fund_house", "scheme_name", "category"]
    df = df.dropna(subset=required)
    return df.sort_values("amfi_code").reset_index(drop=True)


def clean_nav() -> pd.DataFrame:
    df = read_raw("nav")
    df["amfi_code"] = as_code(df["amfi_code"])
    df["nav_date"] = parse_date(df["date"])
    df["nav"] = pd.to_numeric(df["nav"], errors="coerce")
    df = df.drop(columns=["date"])
    df = df.dropna(subset=["amfi_code", "nav_date"])
    df = df.sort_values(["amfi_code", "nav_date"])
    df["nav"] = df.groupby("amfi_code", group_keys=False)["nav"].ffill()
    df = df[df["nav"] > 0]
    df = df.drop_duplicates(subset=["amfi_code", "nav_date"], keep="last")
    df["daily_return"] = df.groupby("amfi_code")["nav"].pct_change()
    return df[["amfi_code", "nav_date", "nav", "daily_return"]].reset_index(drop=True)


def clean_aum() -> pd.DataFrame:
    df = clean_text_columns(read_raw("aum"))
    df["aum_date"] = parse_date(df["date"])
    df = df.drop(columns=["date"])
    for column in ["aum_lakh_crore", "aum_crore", "num_schemes"]:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    df["aum_crore"] = df["aum_crore"].astype("Int64")
    df["num_schemes"] = df["num_schemes"].astype("Int64")
    df = df.dropna(subset=["aum_date", "fund_house"])
    return df.drop_duplicates(["aum_date", "fund_house"]).reset_index(drop=True)


def clean_monthly_sip() -> pd.DataFrame:
    df = read_raw("sip")
    df["month"] = parse_date(df["month"], month_start=True)
    for column in df.columns.drop("month"):
        df[column] = pd.to_numeric(df[column], errors="coerce")
    df = df.dropna(subset=["month"]).drop_duplicates(["month"])
    return df.sort_values("month").reset_index(drop=True)


def clean_category_inflows() -> pd.DataFrame:
    df = clean_text_columns(read_raw("category_inflows"))
    df["month"] = parse_date(df["month"], month_start=True)
    df["net_inflow_crore"] = pd.to_numeric(df["net_inflow_crore"], errors="coerce")
    df = df.dropna(subset=["month", "category"])
    return df.drop_duplicates(["month", "category"]).reset_index(drop=True)


def clean_folios() -> pd.DataFrame:
    df = read_raw("folios")
    df["month"] = parse_date(df["month"], month_start=True)
    for column in df.columns.drop("month"):
        df[column] = pd.to_numeric(df[column], errors="coerce")
    df = df.dropna(subset=["month"]).drop_duplicates(["month"])
    return df.sort_values("month").reset_index(drop=True)


def clean_performance() -> pd.DataFrame:
    df = clean_text_columns(read_raw("performance"))
    df["amfi_code"] = as_code(df["amfi_code"])
    numeric_columns = [
        "return_1yr_pct",
        "return_3yr_pct",
        "return_5yr_pct",
        "benchmark_3yr_pct",
        "alpha",
        "beta",
        "sharpe_ratio",
        "sortino_ratio",
        "std_dev_ann_pct",
        "max_drawdown_pct",
        "aum_crore",
        "expense_ratio_pct",
        "morningstar_rating",
    ]
    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    df["negative_sharpe_flag"] = np.where(df["sharpe_ratio"] < 0, 1, 0)
    df["expense_ratio_out_of_range_flag"] = np.where(
        df["expense_ratio_pct"].between(0.1, 2.5, inclusive="both"), 0, 1
    )
    df["aum_crore"] = df["aum_crore"].astype("Int64")
    df["morningstar_rating"] = df["morningstar_rating"].astype("Int64")
    df = df.dropna(subset=["amfi_code"]).drop_duplicates(["amfi_code"])
    columns = [
        "amfi_code",
        "scheme_name",
        "fund_house",
        "category",
        "plan",
        "return_1yr_pct",
        "return_3yr_pct",
        "return_5yr_pct",
        "benchmark_3yr_pct",
        "alpha",
        "beta",
        "sharpe_ratio",
        "negative_sharpe_flag",
        "sortino_ratio",
        "std_dev_ann_pct",
        "max_drawdown_pct",
        "aum_crore",
        "expense_ratio_pct",
        "expense_ratio_out_of_range_flag",
        "morningstar_rating",
        "risk_grade",
    ]
    return df[columns].sort_values("amfi_code").reset_index(drop=True)


def normalize_transaction_type(value: object) -> str | pd.NA:
    if pd.isna(value):
        return pd.NA
    normalized = str(value).strip().lower()
    compact = normalized.replace(" ", "").replace("_", "")
    if compact == "sip":
        return "SIP"
    if compact in {"lumpsum", "lumpsumpurchase", "purchase"}:
        return "Lumpsum"
    if compact in {"redemption", "redeem"}:
        return "Redemption"
    return str(value).strip().title()


def clean_transactions() -> pd.DataFrame:
    df = clean_text_columns(read_raw("transactions"))
    df["transaction_date"] = parse_date(df["transaction_date"])
    df["amfi_code"] = as_code(df["amfi_code"])
    df["transaction_type"] = df["transaction_type"].map(normalize_transaction_type)
    df["amount_inr"] = pd.to_numeric(df["amount_inr"], errors="coerce")
    df["annual_income_lakh"] = pd.to_numeric(df["annual_income_lakh"], errors="coerce")
    df["kyc_status"] = df["kyc_status"].astype("string").str.strip().str.title()
    df["kyc_status_valid"] = df["kyc_status"].isin(VALID_KYC_STATUSES).astype(int)
    df = df[df["transaction_type"].isin(VALID_TRANSACTION_TYPES)]
    df = df[df["amount_inr"] > 0]
    df = df.dropna(subset=["investor_id", "transaction_date", "amfi_code", "kyc_status"])
    df = df.drop_duplicates()
    df = df.sort_values(["transaction_date", "investor_id", "amfi_code", "amount_inr"]).reset_index(drop=True)
    df.insert(0, "transaction_id", ["TXN" + str(index + 1).zfill(8) for index in range(len(df))])
    df["amount_inr"] = df["amount_inr"].astype("Int64")
    columns = [
        "transaction_id",
        "investor_id",
        "transaction_date",
        "amfi_code",
        "transaction_type",
        "amount_inr",
        "state",
        "city",
        "city_tier",
        "age_group",
        "gender",
        "annual_income_lakh",
        "payment_mode",
        "kyc_status",
        "kyc_status_valid",
    ]
    return df[columns]


def clean_holdings() -> pd.DataFrame:
    df = clean_text_columns(read_raw("holdings"))
    df["amfi_code"] = as_code(df["amfi_code"])
    df["portfolio_date"] = parse_date(df["portfolio_date"])
    for column in ["weight_pct", "market_value_cr", "current_price_inr"]:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    df = df.dropna(subset=["amfi_code", "stock_symbol", "portfolio_date"])
    df = df.drop_duplicates(["amfi_code", "stock_symbol", "portfolio_date"])
    return df.reset_index(drop=True)


def clean_benchmarks() -> pd.DataFrame:
    df = clean_text_columns(read_raw("benchmarks"))
    df["index_date"] = parse_date(df["date"])
    df["close_value"] = pd.to_numeric(df["close_value"], errors="coerce")
    df = df.drop(columns=["date"])
    df = df.dropna(subset=["index_date", "index_name"])
    df = df[df["close_value"] > 0]
    df = df.sort_values(["index_name", "index_date"])
    df["daily_return"] = df.groupby("index_name")["close_value"].pct_change()
    df = df.drop_duplicates(["index_date", "index_name"])
    return df[["index_date", "index_name", "close_value", "daily_return"]].reset_index(drop=True)


def write_clean_csvs(tables: dict[str, pd.DataFrame]) -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    for table, df in tables.items():
        output_path = PROCESSED_DIR / TABLE_TO_CLEAN_CSV[table]
        df.to_csv(output_path, index=False)
        print(f"Wrote {output_path} ({len(df):,} rows)")


def sqlite_safe(df: pd.DataFrame) -> pd.DataFrame:
    safe = df.copy()
    for column in safe.select_dtypes(include=["Int64"]).columns:
        safe[column] = safe[column].astype("object")
    safe = safe.replace({pd.NA: None, np.nan: None})
    return safe


def create_database(tables: dict[str, pd.DataFrame]) -> None:
    if DB_PATH.exists():
        DB_PATH.unlink()
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    connection = sqlite3.connect(DB_PATH)
    try:
        connection.executescript(schema_sql)
        connection.commit()
    finally:
        connection.close()

    engine = create_engine(f"sqlite:///{DB_PATH}")
    load_order = [
        "dim_fund",
        "fact_nav",
        "fact_aum",
        "fact_sip_inflows",
        "fact_category_inflows",
        "fact_industry_folios",
        "fact_performance",
        "fact_transactions",
        "fact_portfolio_holdings",
        "fact_benchmark_indices",
    ]
    for table in load_order:
        sqlite_safe(tables[table]).to_sql(table, engine, if_exists="append", index=False)
        print(f"Loaded {table} into {DB_PATH}")


def run_query(connection: sqlite3.Connection, sql: str) -> pd.DataFrame:
    return pd.read_sql_query(sql, connection)


def write_queries_sql() -> None:
    queries = [
        (
            "Top 5 funds by AUM",
            """
SELECT scheme_name, fund_house, aum_crore
FROM fact_performance
ORDER BY aum_crore DESC
LIMIT 5;
""",
        ),
        (
            "Average NAV per month",
            """
SELECT amfi_code, substr(nav_date, 1, 7) AS month, ROUND(AVG(nav), 4) AS avg_nav
FROM fact_nav
GROUP BY amfi_code, month
ORDER BY amfi_code, month
LIMIT 20;
""",
        ),
        (
            "SIP inflow YoY growth",
            """
SELECT month, sip_inflow_crore, yoy_growth_pct
FROM fact_sip_inflows
WHERE yoy_growth_pct IS NOT NULL
ORDER BY month;
""",
        ),
        (
            "Transactions by state",
            """
SELECT state, COUNT(*) AS transaction_count, SUM(amount_inr) AS total_amount_inr
FROM fact_transactions
GROUP BY state
ORDER BY transaction_count DESC, total_amount_inr DESC;
""",
        ),
        (
            "Funds with expense ratio below 1 percent",
            """
SELECT amfi_code, scheme_name, fund_house, expense_ratio_pct
FROM dim_fund
WHERE expense_ratio_pct < 1
ORDER BY expense_ratio_pct ASC;
""",
        ),
        (
            "Top categories by net inflow",
            """
SELECT category, ROUND(SUM(net_inflow_crore), 2) AS total_net_inflow_crore
FROM fact_category_inflows
GROUP BY category
ORDER BY total_net_inflow_crore DESC
LIMIT 10;
""",
        ),
        (
            "Best 3 year return funds",
            """
SELECT scheme_name, fund_house, return_3yr_pct, sharpe_ratio
FROM fact_performance
ORDER BY return_3yr_pct DESC
LIMIT 10;
""",
        ),
        (
            "Monthly transaction amount by type",
            """
SELECT substr(transaction_date, 1, 7) AS month, transaction_type, SUM(amount_inr) AS total_amount_inr
FROM fact_transactions
GROUP BY month, transaction_type
ORDER BY month, transaction_type
LIMIT 30;
""",
        ),
        (
            "Top portfolio sectors by market value",
            """
SELECT sector, ROUND(SUM(market_value_cr), 2) AS total_market_value_cr
FROM fact_portfolio_holdings
GROUP BY sector
ORDER BY total_market_value_cr DESC
LIMIT 10;
""",
        ),
        (
            "Latest NAV with fund metadata",
            """
WITH latest_nav AS (
    SELECT amfi_code, MAX(nav_date) AS latest_date
    FROM fact_nav
    GROUP BY amfi_code
)
SELECT f.amfi_code, f.scheme_name, n.nav_date, n.nav, n.daily_return
FROM latest_nav l
JOIN fact_nav n ON n.amfi_code = l.amfi_code AND n.nav_date = l.latest_date
JOIN dim_fund f ON f.amfi_code = n.amfi_code
ORDER BY f.scheme_name
LIMIT 20;
""",
        ),
    ]

    connection = sqlite3.connect(DB_PATH)
    lines = [
        "-- Day 2 basic analytics queries and tested result samples",
        f"-- Database: {DB_PATH.name}",
        "",
    ]
    try:
        for index, (title, sql) in enumerate(queries, start=1):
            result = run_query(connection, sql)
            lines.append(f"-- Query {index}: {title}")
            lines.append(sql.strip())
            lines.append("-- Result sample:")
            result_csv = result.to_csv(index=False).strip()
            for line in result_csv.splitlines():
                lines.append(f"-- {line}")
            lines.append("")
    finally:
        connection.close()

    QUERIES_PATH.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    print(f"Wrote tested SQL queries to {QUERIES_PATH}")


def write_data_dictionary(tables: dict[str, pd.DataFrame]) -> None:
    source_map = {
        "dim_fund": RAW_FILES["fund_master"],
        "fact_nav": RAW_FILES["nav"],
        "fact_aum": RAW_FILES["aum"],
        "fact_sip_inflows": RAW_FILES["sip"],
        "fact_category_inflows": RAW_FILES["category_inflows"],
        "fact_industry_folios": RAW_FILES["folios"],
        "fact_performance": RAW_FILES["performance"],
        "fact_transactions": RAW_FILES["transactions"],
        "fact_portfolio_holdings": RAW_FILES["holdings"],
        "fact_benchmark_indices": RAW_FILES["benchmarks"],
    }
    descriptions = {
        "dim_fund": "Fund and scheme master dimension.",
        "fact_nav": "Daily NAV history with computed daily returns.",
        "fact_aum": "Fund-house AUM snapshots.",
        "fact_sip_inflows": "Monthly SIP industry metrics.",
        "fact_category_inflows": "Monthly category-level net inflows.",
        "fact_industry_folios": "Industry folio counts by month.",
        "fact_performance": "Scheme performance and risk metrics.",
        "fact_transactions": "Investor transaction facts with standardized types and KYC validation.",
        "fact_portfolio_holdings": "Scheme equity holdings by stock and sector.",
        "fact_benchmark_indices": "Benchmark index levels with computed daily returns.",
    }
    lines = [
        "# Data Dictionary",
        "",
        "Generated by `Source Code/day2_clean_sql.py`.",
        "",
    ]
    for table, df in tables.items():
        lines.append(f"## {table}")
        lines.append("")
        lines.append(f"- Source: `{source_map[table]}`")
        lines.append(f"- Clean CSV: `Datasets/processed/{TABLE_TO_CLEAN_CSV[table]}`")
        lines.append(f"- Description: {descriptions[table]}")
        lines.append(f"- Row count: {len(df):,}")
        lines.append("")
        lines.append("| Column | Type | Nulls | Notes |")
        lines.append("|---|---:|---:|---|")
        for column in df.columns:
            nulls = int(df[column].isna().sum())
            notes = ""
            if column == "amfi_code":
                notes = "AMFI scheme identifier stored as text."
            elif column.endswith("_date") or column == "month" or column == "launch_date":
                notes = "ISO date string."
            elif column == "daily_return":
                notes = "Computed percent change as decimal."
            elif column.endswith("_flag") or column == "kyc_status_valid":
                notes = "1 = true, 0 = false."
            lines.append(f"| `{column}` | `{df[column].dtype}` | {nulls} | {notes} |")
        lines.append("")
    DATA_DICTIONARY_PATH.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    print(f"Wrote data dictionary to {DATA_DICTIONARY_PATH}")


def validate_outputs(tables: dict[str, pd.DataFrame]) -> None:
    assert len(tables["fact_nav"]) == 46000, "clean_nav.csv should retain 46K rows"
    assert (tables["fact_nav"]["nav"] > 0).all(), "NAV must be positive"
    assert tables["fact_nav"].duplicated(["amfi_code", "nav_date"]).sum() == 0
    assert tables["fact_transactions"]["transaction_type"].isin(VALID_TRANSACTION_TYPES).all()
    assert (tables["fact_transactions"]["amount_inr"] > 0).all()
    assert tables["fact_transactions"]["kyc_status_valid"].isin([0, 1]).all()
    assert tables["fact_performance"]["expense_ratio_pct"].between(0.1, 2.5).all()

    connection = sqlite3.connect(DB_PATH)
    try:
        for table, df in tables.items():
            count = connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            assert count == len(df), f"{table} row count mismatch: DB={count}, CSV={len(df)}"
    finally:
        connection.close()


def main() -> int:
    tables = {
        "dim_fund": clean_fund_master(),
        "fact_nav": clean_nav(),
        "fact_aum": clean_aum(),
        "fact_sip_inflows": clean_monthly_sip(),
        "fact_category_inflows": clean_category_inflows(),
        "fact_industry_folios": clean_folios(),
        "fact_performance": clean_performance(),
        "fact_transactions": clean_transactions(),
        "fact_portfolio_holdings": clean_holdings(),
        "fact_benchmark_indices": clean_benchmarks(),
    }
    write_clean_csvs(tables)
    create_database(tables)
    validate_outputs(tables)
    write_queries_sql()
    write_data_dictionary(tables)
    print("Day 2 cleaning, SQLite load, and query validation complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
