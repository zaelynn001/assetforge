# Rev 0.1.0

"""Filesystem path helpers for AssetForge."""
from __future__ import annotations
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
MIGRATIONS_DIR = DATA_DIR / "migrations"
EXPORT_DIR = ROOT / "exports"
LOG_DIR = ROOT / "logs"
DB_PATH = DATA_DIR / "inventory.db"


def ensure_runtime_dirs() -> None:
    """Make sure writable directories exist before the app touches them."""
    for path in (DATA_DIR, MIGRATIONS_DIR, EXPORT_DIR, LOG_DIR):
        path.mkdir(parents=True, exist_ok=True)
