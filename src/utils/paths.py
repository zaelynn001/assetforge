# Rev 1.2.0 - Distro

"""Filesystem path helpers for AssetForge."""
from __future__ import annotations

import os
from pathlib import Path


APP_NAME = "assetforge"

ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS_DIR = ROOT / "data" / "migrations"


def _xdg_dir(env_var: str, default: Path) -> Path:
    value = os.environ.get(env_var)
    return Path(value) if value else default


def _resolve_data_home() -> Path:
    override = os.environ.get("ASSETFORGE_DATA_DIR")
    if override:
        return Path(override)
    data_home = _xdg_dir("XDG_DATA_HOME", Path.home() / ".local" / "share")
    return data_home / APP_NAME


def _resolve_state_home() -> Path:
    override = os.environ.get("ASSETFORGE_STATE_DIR")
    if override:
        return Path(override)
    state_home = _xdg_dir("XDG_STATE_HOME", Path.home() / ".local" / "state")
    return state_home / APP_NAME


DATA_HOME = _resolve_data_home()
STATE_HOME = _resolve_state_home()

DB_PATH = DATA_HOME / "inventory.db"
EXPORT_DIR = DATA_HOME / "exports"
LOG_DIR = STATE_HOME / "logs"


def ensure_runtime_dirs() -> None:
    """Ensure user-writable directories exist before the app starts."""
    for path in (
        DATA_HOME,
        EXPORT_DIR,
        LOG_DIR,
        DB_PATH.parent,
    ):
        path.mkdir(parents=True, exist_ok=True)
