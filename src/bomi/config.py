"""Configuration loading and path management.

Data layout:
  Global:  ~/Library/Application Support/bomi/ (macOS)
           ~/.local/share/bomi/ (Linux)
  Project: .bomi/project.yaml (in project dir)
"""

import os
import sys
from pathlib import Path

import yaml


def _data_dir() -> Path:
    """Return OS-appropriate global data directory for bomi."""
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "bomi"


def get_data_dir() -> Path:
    """Return global data directory, creating it if needed."""
    d = _data_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_db_path() -> Path:
    """Return path to the global SQLite parts cache."""
    return get_data_dir() / "parts.db"


def _global_config_path() -> Path:
    return _data_dir() / "config.yaml"


def load_global_config() -> dict:
    """Load global config.yaml from the data directory."""
    path = _global_config_path()
    if not path.exists():
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}


def get_config(key: str, default=None):
    """Get a config value. Checks env vars first, then global config.yaml."""
    env_key = f"BOMI_{key.upper()}"
    env_val = os.environ.get(env_key)
    if env_val is not None:
        return env_val
    return load_global_config().get(key, default)


def get_secret(key: str) -> str | None:
    """Get an API key. Checks env vars first, then global config.yaml."""
    return get_config(key)


def find_project_dir(override: str | None = None) -> Path | None:
    """Find project directory containing .bomi/project.yaml.

    Resolution order:
      1. Explicit override (--project CLI option)
      2. BOMI_PROJECT env var
      3. Walk up from cwd looking for .bomi/project.yaml
    """
    # 1. Explicit override
    if override:
        p = Path(override)
        if (p / ".bomi" / "project.yaml").exists():
            return p
        return None

    # 2. Env var
    env = os.environ.get("BOMI_PROJECT")
    if env:
        p = Path(env)
        if (p / ".bomi" / "project.yaml").exists():
            return p
        return None

    # 3. Walk up from cwd
    path = Path.cwd()
    for parent in [path, *path.parents]:
        if (parent / ".bomi" / "project.yaml").exists():
            return parent

    return None
