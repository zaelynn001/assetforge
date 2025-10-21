# Rev 0.1.0

"""Placeholder search service."""
from __future__ import annotations
from typing import Iterable, Dict, List


def search(rows: Iterable[Dict[str, str]], term: str) -> List[Dict[str, str]]:
    term_lower = term.lower()
    return [row for row in rows if term_lower in " ".join(row.values()).lower()]
