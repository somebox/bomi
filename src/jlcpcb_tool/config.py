"""Configuration loading from secrets.yaml and path management."""

import os
from pathlib import Path

import yaml


def _find_project_root() -> Path:
    """Walk up from cwd to find directory containing pyproject.toml."""
    path = Path.cwd()
    for parent in [path, *path.parents]:
        if (parent / "pyproject.toml").exists():
            return parent
    return path


PROJECT_ROOT = _find_project_root()
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "parts.db"
SECRETS_PATH = PROJECT_ROOT / "secrets.yaml"


def get_db_path() -> Path:
    """Return path to SQLite database, creating data dir if needed."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DB_PATH


def load_secrets() -> dict:
    """Load API keys from secrets.yaml."""
    if not SECRETS_PATH.exists():
        return {}
    with open(SECRETS_PATH) as f:
        return yaml.safe_load(f) or {}


def get_secret(key: str) -> str | None:
    """Get a specific secret by key."""
    return load_secrets().get(key)
