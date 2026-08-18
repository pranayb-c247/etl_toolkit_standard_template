"""
mysql.py
--------
MySQL connector using mysql-connector-python + SQLAlchemy engine.
"""

import mysql.connector
from sqlalchemy import create_engine
from urllib.parse import quote_plus

from .base import BaseConnector


class MySQLConnector(BaseConnector):
    """
    config expects: host, port (default 3306), database, username, password
    """

    def connect(self):
        cfg = self.config
        self.conn = mysql.connector.connect(
            host=cfg["host"],
            port=cfg.get("port", 3306),
            database=cfg["database"],
            user=cfg["username"],
            password=cfg["password"],
        )
        return self.conn

    def get_engine(self):
        cfg = self.config
        user = quote_plus(cfg["username"])
        pwd = quote_plus(cfg["password"])
        url = f"mysql+mysqlconnector://{user}:{pwd}@{cfg['host']}:{cfg.get('port', 3306)}/{cfg['database']}"
        return create_engine(url)
