# Rev 1.2.0 - Distro

"""Timestamp helpers."""
from __future__ import annotations
from datetime import datetime, timezone


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
