# Rev 1.2.0 - Distro

"""Utility functions for presenting diff entries in history panel."""
from __future__ import annotations

from typing import Dict, Iterable, List


EXCLUDE_KEYS = {"updated_at_utc", "created_at_utc"}


def summarize_changes(entry: dict) -> List[str]:
    lines: List[str] = []
    before = entry.get("snapshot_before", {}) or {}
    after = entry.get("snapshot_after", {}) or {}
    keys = set(before) | set(after)
    for key in sorted(keys):
        if key in EXCLUDE_KEYS:
            continue
        old = before.get(key)
        new = after.get(key)
        if old == new:
            continue
        lines.append(f"{key}: {format_value(old)} → {format_value(new)}")
    return lines


def format_value(value) -> str:
    if value in (None, ""):
        return "—"
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)
