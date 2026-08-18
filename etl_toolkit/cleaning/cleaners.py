"""
cleaners.py
-----------
Reusable, dataframe-in / dataframe-out cleaning functions. Import only what
you need per pipeline; nothing here is auto-applied.

NOTE on dedup: dedup_dataframe() always requires an explicit key_cols list.
Do NOT dedupe on a single field when the table's real natural key is
composite (this caused the silent row-drop bug in dld_etl_pipeline_V1 on
the `projects` table). Always pass the FULL natural key.
"""

import logging
import pandas as pd
import numpy as np

logger = logging.getLogger("etl_toolkit.cleaning")


def strip_whitespace(df: pd.DataFrame, columns: list = None) -> pd.DataFrame:
    """Trim leading/trailing whitespace on string columns."""
    cols = columns or df.select_dtypes(include="object").columns.tolist()
    for c in cols:
        df[c] = df[c].astype(str).str.strip().replace({"nan": np.nan, "None": np.nan})
    return df


def standardize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """snake_case, no leading/trailing spaces, no double underscores."""
    df.columns = (
        df.columns.str.strip()
        .str.lower()
        .str.replace(r"[^0-9a-zA-Z]+", "_", regex=True)
        .str.strip("_")
    )
    return df


def parse_dates(df: pd.DataFrame, columns: list, input_formats: list = None) -> pd.DataFrame:
    """
    Safely parse date columns and NEVER silently null them out.
    Tries each format in input_formats in order; falls back to pandas'
    flexible parser; logs a warning with a sample of unparsed values
    instead of failing silently (this was the root cause of NULL date
    columns in dubai_pulse_V1 - wrong strptime format strings).
    """
    input_formats = input_formats or ["%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y", "%Y-%m-%dT%H:%M:%S"]
    for col in columns:
        if col not in df.columns:
            continue
        original = df[col].copy()
        parsed = pd.to_datetime(df[col], errors="coerce")
        # if the generic parse mostly failed, try explicit formats
        if parsed.isna().mean() > 0.3:
            for fmt in input_formats:
                trial = pd.to_datetime(df[col], format=fmt, errors="coerce")
                if trial.isna().mean() < parsed.isna().mean():
                    parsed = trial
        newly_null = parsed.isna() & original.notna()
        if newly_null.any():
            sample = original[newly_null].unique()[:5].tolist()
            logger.warning(
                "parse_dates: %d values in '%s' could not be parsed. Sample: %s",
                newly_null.sum(), col, sample,
            )
        df[col] = parsed
    return df


def cast_numeric(df: pd.DataFrame, columns: list, decimal_places: int = None) -> pd.DataFrame:
    """Coerce to numeric; optionally round to a fixed decimal precision
    (use this before loading into DECIMAL(18,2)-style columns to avoid
    precision/overflow errors at load time)."""
    for col in columns:
        if col not in df.columns:
            continue
        df[col] = pd.to_numeric(df[col], errors="coerce")
        if decimal_places is not None:
            df[col] = df[col].round(decimal_places)
    return df


def fill_missing(df: pd.DataFrame, strategy: dict) -> pd.DataFrame:
    """
    strategy = {"column_name": "value_or_'mean'_or_'median'_or_'mode'"}
    """
    for col, rule in strategy.items():
        if col not in df.columns:
            continue
        if rule == "mean":
            df[col] = df[col].fillna(df[col].mean())
        elif rule == "median":
            df[col] = df[col].fillna(df[col].median())
        elif rule == "mode":
            mode_val = df[col].mode()
            df[col] = df[col].fillna(mode_val.iloc[0] if not mode_val.empty else None)
        else:
            df[col] = df[col].fillna(rule)
    return df


def dedup_dataframe(df: pd.DataFrame, key_cols: list, keep: str = "last") -> pd.DataFrame:
    """
    Explicit, composite-key-aware dedup. ALWAYS pass the full natural key
    (e.g. ['project_number', 'project_status', 'zoning_authority_en']),
    never a single column, unless that column really is unique on its own.
    """
    missing = [c for c in key_cols if c not in df.columns]
    if missing:
        raise ValueError(f"dedup_dataframe: key columns not found in df: {missing}")

    before = len(df)
    deduped = df.drop_duplicates(subset=key_cols, keep=keep)
    dropped = before - len(deduped)
    if dropped:
        logger.info("dedup_dataframe: dropped %d duplicate rows on key %s", dropped, key_cols)
    return deduped


def enforce_dtype_for_bigint(df: pd.DataFrame, columns: list) -> pd.DataFrame:
    """
    Force columns holding large integer IDs (e.g. 13-digit DLD property IDs)
    to a pandas nullable Int64 dtype so downstream loaders can correctly
    set SQL_BIGINT via setinputsizes instead of mis-inferring INT.
    """
    for col in columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
    return df


def drop_empty_rows(df: pd.DataFrame, required_cols: list) -> pd.DataFrame:
    """Drop rows where ALL required_cols are null (garbage rows)."""
    before = len(df)
    df = df.dropna(subset=required_cols, how="all")
    dropped = before - len(df)
    if dropped:
        logger.info("drop_empty_rows: dropped %d fully-empty rows", dropped)
    return df


def clean_pipeline(df: pd.DataFrame, steps: list) -> pd.DataFrame:
    """
    Run a declarative list of cleaning steps, e.g.:
        steps = [
            ("standardize_column_names", {}),
            ("strip_whitespace", {}),
            ("parse_dates", {"columns": ["contract_date"]}),
            ("dedup_dataframe", {"key_cols": ["project_number", "project_status"]}),
        ]
    Keeps pipeline scripts short and declarative instead of copy-pasted cleaning code.
    """
    fn_map = {
        "strip_whitespace": strip_whitespace,
        "standardize_column_names": standardize_column_names,
        "parse_dates": parse_dates,
        "cast_numeric": cast_numeric,
        "fill_missing": fill_missing,
        "dedup_dataframe": dedup_dataframe,
        "enforce_dtype_for_bigint": enforce_dtype_for_bigint,
        "drop_empty_rows": drop_empty_rows,
    }
    for step_name, kwargs in steps:
        if step_name not in fn_map:
            raise ValueError(f"Unknown cleaning step '{step_name}'")
        df = fn_map[step_name](df, **kwargs)
    return df
