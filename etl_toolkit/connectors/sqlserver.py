"""
sqlserver.py
------------
SQL Server connector built around pyodbc, with fast_executemany enabled
by default (this is the pattern already used in dld_etl_pipeline / dubai_pulse_V1).
"""

import pyodbc
from sqlalchemy import create_engine
from urllib.parse import quote_plus

from .base import BaseConnector


class SQLServerConnector(BaseConnector):
    """
    config expects:
        server, database, username, password, driver (optional),
        trusted_connection (optional, bool)
    """

    def connect(self):
        cfg = self.config
        driver = cfg.get("driver", "ODBC Driver 17 for SQL Server")

        if cfg.get("trusted_connection"):
            conn_str = (
                f"DRIVER={{{driver}}};SERVER={cfg['server']};"
                f"DATABASE={cfg['database']};Trusted_Connection=yes;"
            )
        else:
            conn_str = (
                f"DRIVER={{{driver}}};SERVER={cfg['server']};"
                f"DATABASE={cfg['database']};UID={cfg['username']};PWD={cfg['password']};"
            )

        self.conn = pyodbc.connect(conn_str)
        return self.conn

    def get_cursor(self, fast_executemany: bool = True):
        if self.conn is None:
            self.connect()
        cur = self.conn.cursor()
        cur.fast_executemany = fast_executemany
        return cur

    def get_engine(self):
        cfg = self.config
        driver = cfg.get("driver", "ODBC Driver 17 for SQL Server").replace(" ", "+")
        if cfg.get("trusted_connection"):
            odbc_str = (
                f"DRIVER={{{cfg.get('driver', 'ODBC Driver 17 for SQL Server')}}};"
                f"SERVER={cfg['server']};DATABASE={cfg['database']};Trusted_Connection=yes;"
            )
            params = quote_plus(odbc_str)
            url = f"mssql+pyodbc:///?odbc_connect={params}"
        else:
            user = quote_plus(cfg["username"])
            pwd = quote_plus(cfg["password"])
            url = (
                f"mssql+pyodbc://{user}:{pwd}@{cfg['server']}/{cfg['database']}"
                f"?driver={driver}"
            )
        return create_engine(url, fast_executemany=True)
