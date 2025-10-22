"""CSV import helpers for AssetForge inventory."""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


class InventoryImportError(Exception):
    """Domain-specific exception for import failures."""


def load_csv_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        raise InventoryImportError(f"CSV file not found: {path}")
    rows: List[Dict[str, str]] = []
    with path.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        if not reader.fieldnames:
            raise InventoryImportError("CSV must have a header row")
        for raw in reader:
            # normalize keys to lowercase
            rows.append({(k or "").strip().lower(): (v or "").strip() for k, v in raw.items()})
    return rows


def import_inventory_csv(
    path: Path,
    *,
    types_repo,
    locations_repo,
    users_repo,
    groups_repo,
    items_repo,
) -> Tuple[int, List[str]]:
    """Import inventory rows from CSV, creating items."""
    rows = load_csv_rows(path)
    if not rows:
        return 0, []

    type_lookup = _build_type_lookup(types_repo.list_types())
    notes: List[str] = []
    created = 0

    for row in rows:
        try:
            name = row.get("name")
            if not name:
                raise InventoryImportError("Missing 'name'")

            type_token = row.get("type")
            if not type_token:
                raise InventoryImportError("Missing 'type'")

            type_id = type_lookup.get(type_token.lower())
            if type_id is None:
                raise InventoryImportError(f"Unknown type '{type_token}'")

            model = row.get("model") or None
            mac = row.get("mac") or row.get("mac_address") or None
            location_name = row.get("location") or None
            user_name = row.get("user") or None
            group_name = row.get("group") or row.get("group_name") or None
            note_text = row.get("notes") or None

            location_id = None
            if location_name:
                location_id = locations_repo.ensure(location_name)["id"]

            user_id = None
            if user_name:
                user_id = users_repo.ensure(user_name)["id"]

            group_id = None
            if group_name:
                group_id = groups_repo.ensure(group_name)["id"]

            item = items_repo.create(
                name=name,
                type_id=type_id,
                model=model,
                mac_address=mac,
                location_id=location_id,
                user_id=user_id,
                group_id=group_id,
                notes=note_text,
                note="imported via CSV",
            )

            created += 1

        except InventoryImportError as exc:
            notes.append(f"Row skipped: {exc}")
        except Exception as exc:
            notes.append(f"Row skipped due to error: {exc}")

    return created, notes


def _build_type_lookup(types: Iterable[Dict[str, str]]) -> Dict[str, int]:
    lookup: Dict[str, int] = {}
    for row in types:
        tid = int(row["id"])
        name = str(row.get("name", "")).lower()
        code = str(row.get("code", "")).lower()
        if name:
            lookup[name] = tid
        if code:
            lookup[code] = tid
    return lookup
