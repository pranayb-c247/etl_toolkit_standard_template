"""
sql_loader.py
-------------
Standard load patterns used across office pipelines:
    1. bulk_insert_staging  -> fast load raw/staging table (truncate + load)
    2. merge_staging_to_main -> SQL Server MERGE (upsert) from staging into main
    3. append_only_load     -> simple append (for log/history tables)

All loaders accept an already-connected `connector` (see connectors/factory.py).
"""

import logging
import pandas as pd
import pyodbc

logger = logging.getLogger("etl_toolkit.loaders")


def _sql_bigint_columns(cursor, df: pd.DataFrame, bigint_columns: list):
    """
    Explicitly set input sizes for BIGINT columns so pyodbc's fast_executemany
    doesn't mis-infer them as INT and truncate/overflow (root cause of the
    13-digit DLD property ID load failures).
    """
    if not bigint_columns:
        return
    col_positions = [df.columns.get_loc(c) for c in bigint_columns if c in df.columns]
    input_sizes = [(pyodbc.SQL_BIGINT, 0, 0) if i in col_positions else None
                   for i in range(len(df.columns))]
    # pyodbc.setinputsizes expects one entry per parameter marker, in order
    if any(input_sizes):
        cursor.setinputsizes([s for s in input_sizes if s is not None] or None)


def bulk_insert_staging(connector, df: pd.DataFrame, table_name: str,
                         truncate_first: bool = True, bigint_columns: list = None,
                         batch_size: int = 5000):
    """
    Truncate-and-load a staging table using fast_executemany.
    Use this for raw landing / staging tables that get fully refreshed each run.
    """
    if df.empty:
        logger.info("bulk_insert_staging: dataframe empty, nothing to load into %s", table_name)
        return 0

    if connector.conn is None:
        connector.connect()
    cur = connector.conn.cursor()
    cur.fast_executemany = True

    if truncate_first:
        cur.execute(f"TRUNCATE TABLE {table_name}")

    cols = list(df.columns)
    placeholders = ", ".join(["?"] * len(cols))
    col_list = ", ".join(cols)
    insert_sql = f"INSERT INTO {table_name} ({col_list}) VALUES ({placeholders})"

    # convert NaN/NaT to None for pyodbc
    data = df.where(pd.notnull(df), None).values.tolist()

    total = 0
    for start in range(0, len(data), batch_size):
        batch = data[start:start + batch_size]
        cur.executemany(insert_sql, batch)
        total += len(batch)

    connector.conn.commit()
    logger.info("bulk_insert_staging: loaded %d rows into %s", total, table_name)
    return total


def append_only_load(connector, df: pd.DataFrame, table_name: str, batch_size: int = 5000):
    """Append rows without truncating - for history/log tables."""
    return bulk_insert_staging(connector, df, table_name, truncate_first=False, batch_size=batch_size)


def merge_staging_to_main(connector, staging_table: str, main_table: str,
                           key_columns: list, update_columns: list, insert_columns: list):
    """
    Runs a SQL Server MERGE: matched rows are updated, unmatched are inserted.
    key_columns    -> natural key used to match staging <-> main (composite-key safe)
    update_columns -> columns to overwrite on match
    insert_columns -> full column list to insert on new rows
    """
    if connector.conn is None:
        connector.connect()
    cur = connector.conn.cursor()

    on_clause = " AND ".join([f"target.{k} = source.{k}" for k in key_columns])
    update_clause = ", ".join([f"target.{c} = source.{c}" for c in update_columns])
    insert_cols = ", ".join(insert_columns)
    insert_vals = ", ".join([f"source.{c}" for c in insert_columns])

    merge_sql = f"""
        MERGE {main_table} AS target
        USING {staging_table} AS source
        ON {on_clause}
        WHEN MATCHED THEN
            UPDATE SET {update_clause}
        WHEN NOT MATCHED BY TARGET THEN
            INSERT ({insert_cols}) VALUES ({insert_vals});
    """
    cur.execute(merge_sql)
    connector.conn.commit()
    logger.info("merge_staging_to_main: merged %s -> %s on key %s", staging_table, main_table, key_columns)
    return cur.rowcount
