"""
config.py
---------
Single place to load pipeline configuration.

Priority (highest wins):
    1. Environment variables (for secrets: DB password, API keys)
    2. config.yaml (for non-secret, project-level settings)

Usage:
    from etl_toolkit.config import load_config
    cfg = load_config("config/config.yaml")
    cfg.db.server, cfg.db.database, cfg.get("api.happyendpoint.base_url")
"""

import os
import yaml
from dotenv import load_dotenv


class Config:
    """Thin dict-wrapper with dot-style access and env-var override support."""

    def __init__(self, data: dict):
        self._data = data or {}

    def get(self, dotted_key: str, default=None):
        """Fetch nested value using 'a.b.c' notation."""
        node = self._data
        for part in dotted_key.split("."):
            if isinstance(node, dict) and part in node:
                node = node[part]
            else:
                return default
        return node

    def __getattr__(self, item):
        if item in self._data:
            val = self._data[item]
            return Config(val) if isinstance(val, dict) else val
        raise AttributeError(f"No config key '{item}'")

    def as_dict(self):
        return self._data

    def __repr__(self):
        return f"Config({self._data})"


def _resolve_env_placeholders(data):
    """
    Recursively replace values like '${ENV_VAR_NAME}' with the actual
    environment variable, so secrets never live in the yaml file itself.
    """
    if isinstance(data, dict):
        return {k: _resolve_env_placeholders(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_resolve_env_placeholders(v) for v in data]
    if isinstance(data, str) and data.startswith("${") and data.endswith("}"):
        env_key = data[2:-1]
        return os.environ.get(env_key, "")
    return data


def load_config(config_path: str = "config/config.yaml", env_path: str = ".env") -> Config:
    """
    Loads .env first (so ${VARS} in yaml resolve), then parses the yaml file.
    """
    if os.path.exists(env_path):
        load_dotenv(env_path)

    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    resolved = _resolve_env_placeholders(raw)
    return Config(resolved)
