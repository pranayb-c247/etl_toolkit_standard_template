"""
postgres.py
-----------
PostgreSQL connector using psycopg2 + SQLAlchemy engine.
"""

import psycopg2
from sqlalchemy import create_engine
from urllib.parse import quote_plus

from .base import BaseConnector


class PostgresConnector(BaseConnector):
    """
    config expects: host, port (default 5432), database, username, password
    """

    def connect(self):
        cfg = self.config
        self.conn = psycopg2.connect(
            host=cfg["host"],
            port=cfg.get("port", 5432),
            dbname=cfg["database"],
            user=cfg["username"],
            password=cfg["password"],
        )
        return self.conn

    def get_engine(self):
        cfg = self.config
        user = quote_plus(cfg["username"])
        pwd = quote_plus(cfg["password"])
        url = f"postgresql+psycopg2://{user}:{pwd}@{cfg['host']}:{cfg.get('port', 5432)}/{cfg['database']}"
        return create_engine(url)
