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
    ip_repo,
    sub_types_repo,
    items_repo,
) -> Tuple[int, List[str]]:
    """Import inventory rows from CSV, creating items."""
    rows = load_csv_rows(path)
    if not rows:
        return 0, []

    type_lookup = _build_type_lookup(types_repo.list_types())
    landline = types_repo.find_by_code("TP")
    landline_type_id = int(landline["id"]) if landline else None
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
            ip_address_raw = row.get("ip") or row.get("ip_address") or None
            ip_address = None
            if ip_address_raw:
                stripped = ip_address_raw.strip()
                if stripped.lower() not in {"none", ""}:
                    ip_address = stripped
            location_name = row.get("location") or None
            user_name = row.get("user") or None
            group_name = row.get("group") or row.get("group_name") or None
            sub_type_name = row.get("sub_type") or row.get("subtype") or None
            note_text = row.get("notes") or None
            extension_raw = row.get("extension") or row.get("phone_extension") or None

            location_id = None
            if location_name:
                location_id = locations_repo.ensure(location_name)["id"]

            if user_name:
                raise InventoryImportError(
                    "User column is not supported. Assign users manually after import."
                )

            if group_name:
                raise InventoryImportError(
                    "Group column is not supported. Assign groups manually after import."
                )

            sub_type_id = None
            if sub_type_name:
                sub_type = sub_types_repo.find_by_name(sub_type_name)
                if not sub_type:
                    raise InventoryImportError(
                        f"Sub type '{sub_type_name}' is not recognized. Update the catalog first."
                    )
                sub_type_id = sub_type["id"]

            extension_value = None
            if landline_type_id is not None and type_id == landline_type_id:
                extension_value = (extension_raw or "").strip() or None
            else:
                extension_value = None

            if ip_address:
                ip_record = ip_repo.find(ip_address)
                if not ip_record:
                    raise InventoryImportError(
                        f"IP address '{ip_address}' is not available. Seed it first."
                    )

            item = items_repo.create(
                name=name,
                type_id=type_id,
                model=model,
                mac_address=mac,
                ip_address=ip_address,
                location_id=location_id,
                user_id=None,
                group_id=None,
                sub_type_id=sub_type_id,
                notes=note_text,
                extension=extension_value,
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
