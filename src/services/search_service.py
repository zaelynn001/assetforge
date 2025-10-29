# Rev 1.2.0 - Distro

"""Search parsing helpers for advanced query tokens."""
from __future__ import annotations

from typing import Dict, Tuple


def parse_query(query: str) -> Tuple[str, Dict[str, str]]:
    """Split a free-form query into plain text and directive filters."""
    filters: Dict[str, str] = {}
    terms = []
    for token in query.split():
        if ":" in token:
            key, value = token.split(":", 1)
            key = key.lower().strip()
            value = value.strip()
            if key and value:
                if key in {"type", "mac", "mac_address", "loc", "location", "tag", "asset", "asset_tag", "user", "group"}:
                    filters[key] = value
                    continue
        terms.append(token)
    return " ".join(terms).strip(), filters
