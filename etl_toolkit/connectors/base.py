"""
base.py
-------
Abstract connector interface. Every DB connector (SQL Server / Postgres / MySQL)
implements this so the rest of the framework (loaders, quality checks) never
needs to know which DB engine it's talking to.
"""

from abc import ABC, abstractmethod


class BaseConnector(ABC):
    def __init__(self, config: dict):
        self.config = config
        self.conn = None

    @abstractmethod
    def connect(self):
        """Open the DB connection. Must set self.conn."""
        raise NotImplementedError

    @abstractmethod
    def get_engine(self):
        """Return a SQLAlchemy engine (used by pandas.to_sql / read_sql)."""
        raise NotImplementedError

    def close(self):
        if self.conn is not None:
            try:
                self.conn.close()
            finally:
                self.conn = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
