# Rev 1.0.0

"""Utility helpers for barcode and scanner input detection."""
from __future__ import annotations

import re
from typing import Dict, Optional


_ASSET_TAG_RE = re.compile(r"^SDMM-[A-Z]{2}-\d{4}$", re.IGNORECASE)
_MAC_RE = re.compile(r"^([0-9A-F]{2}[:-]){5}[0-9A-F]{2}$", re.IGNORECASE)


def sanitize(raw: str) -> str:
    return raw.strip()


def analyze(raw: str) -> Dict[str, Optional[str]]:
    cleaned = sanitize(raw)
    if not cleaned:
        return {"text": ""}
    if _ASSET_TAG_RE.match(cleaned):
        return {"asset_tag": cleaned.upper()}
    if _MAC_RE.match(cleaned):
        mac = cleaned.replace(":", "").replace("-", "").upper()
        return {"mac_address": mac}
    return {"text": cleaned}
