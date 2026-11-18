"""Load the data into DuckDB and query metrics by name.

    from metrics import connect, query_metrics
    con = connect()
    query_metrics(con, ["checkout_conversion", "refund_rate"], by=["week"])

Command line:
    python metrics.py checkout_conversion authorization_rate --by week device
"""
import argparse
from pathlib import Path

import duckdb
import pandas as pd
import yaml

ROOT = Path(__file__).parent
TABLES = ["merchants", "sessions", "charges", "refunds", "disputes"]


def load_metrics() -> dict:
    return yaml.safe_load((ROOT / "metrics.yml").read_text())["metrics"]


def connect() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    for t in TABLES:
        con.execute(f"create view {t} as select * from read_parquet('{ROOT / 'data' / t}.parquet')")
    con.execute((ROOT / "sql" / "session_facts.sql").read_text())
    return con


def metric_sql(names: list[str], by: list[str] | None = None, where: str | None = None) -> str:
    """Build one SQL query from metric definitions, so no report re-types a formula."""
    defs = load_metrics()
    unknown = [n for n in names if n not in defs]
    if unknown:
        raise KeyError(f"Not in metrics.yml: {unknown}")
    by = by or []
    cols = [*by]
    for n in names:
        d = defs[n]
        cols += [f"{d['numerator']} as {n}__num", f"{d['denominator']} as {n}__den",
                 f"{d['numerator']} / nullif({d['denominator']}, 0) as {n}"]
    sql = "select " + ",\n       ".join(cols) + "\nfrom session_facts"
    if where:
        sql += f"\nwhere {where}"
    if by:
        sql += "\ngroup by " + ", ".join(by) + "\norder by " + ", ".join(by)
    return sql


def query_metrics(con, names, by=None, where=None) -> pd.DataFrame:
    return con.execute(metric_sql(names, by, where)).df()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("metrics", nargs="+")
    ap.add_argument("--by", nargs="*", default=[])
    ap.add_argument("--show-sql", action="store_true")
    a = ap.parse_args()
    if a.show_sql:
        print(metric_sql(a.metrics, a.by))
    df = query_metrics(connect(), a.metrics, a.by)
    print(df[[*a.by, *a.metrics]].to_string(index=False))


if __name__ == "__main__":
    main()
