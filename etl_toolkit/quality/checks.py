"""
checks.py
---------
Atomic data-quality checks. Each returns a dict:
    {"check": name, "column": col_or_None, "status": "PASS"/"FAIL"/"WARN",
     "details": str, "value": numeric_or_None}

These are composed by monitor.py into a full DQ run.
"""

import pandas as pd


def check_row_count(df: pd.DataFrame, min_rows: int = 1) -> dict:
    n = len(df)
    status = "PASS" if n >= min_rows else "FAIL"
    return {"check": "row_count", "column": None, "status": status,
            "details": f"{n} rows (min expected {min_rows})", "value": n}


def check_not_null(df: pd.DataFrame, column: str, threshold_pct: float = 0.0) -> dict:
    """threshold_pct = max allowed % of nulls, e.g. 0 means zero nulls allowed."""
    if column not in df.columns:
        return {"check": "not_null", "column": column, "status": "FAIL",
                "details": "column not found", "value": None}
    null_pct = df[column].isna().mean() * 100
    status = "PASS" if null_pct <= threshold_pct else "FAIL"
    return {"check": "not_null", "column": column, "status": status,
            "details": f"{null_pct:.2f}% null (threshold {threshold_pct}%)", "value": round(null_pct, 2)}


def check_unique(df: pd.DataFrame, columns) -> dict:
    """columns: str or list -- checks uniqueness on single or composite key."""
    cols = [columns] if isinstance(columns, str) else list(columns)
    missing = [c for c in cols if c not in df.columns]
    if missing:
        return {"check": "unique", "column": cols, "status": "FAIL",
                "details": f"columns not found: {missing}", "value": None}
    dupe_count = df.duplicated(subset=cols).sum()
    status = "PASS" if dupe_count == 0 else "FAIL"
    return {"check": "unique", "column": cols, "status": status,
            "details": f"{dupe_count} duplicate rows on {cols}", "value": int(dupe_count)}


def check_value_range(df: pd.DataFrame, column: str, min_val=None, max_val=None) -> dict:
    if column not in df.columns:
        return {"check": "value_range", "column": column, "status": "FAIL",
                "details": "column not found", "value": None}
    series = pd.to_numeric(df[column], errors="coerce")
    out_of_range = 0
    if min_val is not None:
        out_of_range += (series < min_val).sum()
    if max_val is not None:
        out_of_range += (series > max_val).sum()
    status = "PASS" if out_of_range == 0 else "FAIL"
    return {"check": "value_range", "column": column, "status": status,
            "details": f"{out_of_range} rows outside [{min_val}, {max_val}]", "value": int(out_of_range)}


def check_allowed_values(df: pd.DataFrame, column: str, allowed: list) -> dict:
    if column not in df.columns:
        return {"check": "allowed_values", "column": column, "status": "FAIL",
                "details": "column not found", "value": None}
    invalid_mask = ~df[column].isin(allowed) & df[column].notna()
    invalid_count = invalid_mask.sum()
    status = "PASS" if invalid_count == 0 else "FAIL"
    sample = df.loc[invalid_mask, column].unique()[:5].tolist()
    return {"check": "allowed_values", "column": column, "status": status,
            "details": f"{invalid_count} invalid values, sample: {sample}", "value": int(invalid_count)}


def check_schema(df: pd.DataFrame, expected_columns: list) -> dict:
    missing = [c for c in expected_columns if c not in df.columns]
    status = "PASS" if not missing else "FAIL"
    return {"check": "schema", "column": None, "status": status,
            "details": f"missing columns: {missing}" if missing else "all expected columns present",
            "value": len(missing)}


def check_row_count_drift(current_count: int, previous_count: int, max_drift_pct: float = 20.0) -> dict:
    """
    Compare today's row count against the last successful run to catch
    silent extraction failures (API returning partial data, pagination bugs).
    """
    if previous_count in (0, None):
        return {"check": "row_count_drift", "column": None, "status": "WARN",
                "details": "no previous run to compare against", "value": None}
    drift_pct = abs(current_count - previous_count) / previous_count * 100
    status = "PASS" if drift_pct <= max_drift_pct else "FAIL"
    return {"check": "row_count_drift", "column": None, "status": status,
            "details": f"{drift_pct:.1f}% drift vs previous run ({previous_count} -> {current_count})",
            "value": round(drift_pct, 2)}


def check_referential_integrity(df: pd.DataFrame, column: str, ref_values: set) -> dict:
    """Check that all values in `column` exist in a reference set (e.g. valid project_numbers)."""
    if column not in df.columns:
        return {"check": "referential_integrity", "column": column, "status": "FAIL",
                "details": "column not found", "value": None}
    orphan_mask = ~df[column].isin(ref_values) & df[column].notna()
    orphan_count = orphan_mask.sum()
    status = "PASS" if orphan_count == 0 else "WARN"
    return {"check": "referential_integrity", "column": column, "status": status,
            "details": f"{orphan_count} rows with no matching reference", "value": int(orphan_count)}
