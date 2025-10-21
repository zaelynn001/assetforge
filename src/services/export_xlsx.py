# Rev 0.1.0

"""Placeholder export service."""
from __future__ import annotations
from pathlib import Path
from typing import Iterable, Dict


def export_to_xlsx(rows: Iterable[Dict[str, str]], target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as fh:
        fh.write("assetforge export placeholder\n")
        for row in rows:
            fh.write(",".join(f"{k}={v}" for k, v in row.items()))
            fh.write("\n")
