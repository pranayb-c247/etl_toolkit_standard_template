"""
factory.py
----------
Single entry point to get the right connector based on config.

Usage:
    from etl_toolkit.connectors.factory import get_connector
    conn = get_connector(cfg.get("db"))   # cfg.db.type = "sqlserver" | "postgres" | "mysql"
"""

from .sqlserver import SQLServerConnector
from .postgres import PostgresConnector
from .mysql import MySQLConnector

_REGISTRY = {
    "sqlserver": SQLServerConnector,
    "mssql": SQLServerConnector,
    "postgres": PostgresConnector,
    "postgresql": PostgresConnector,
    "mysql": MySQLConnector,
}


def get_connector(db_config: dict):
    """
    db_config must contain a 'type' key: sqlserver | postgres | mysql
    """
    db_type = (db_config.get("type") or "").lower()
    if db_type not in _REGISTRY:
        raise ValueError(
            f"Unsupported db type '{db_type}'. Supported: {list(_REGISTRY.keys())}"
        )
    return _REGISTRY[db_type](db_config)
