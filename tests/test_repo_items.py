# Rev 1.2.0 - Distro

"""Repository integration tests for items and related helpers."""
from __future__ import annotations

from pathlib import Path

import pytest

from src.repositories.db import Database
from src.repositories.sqlite_items_repo import SQLiteItemsRepository
from src.repositories.sqlite_types_repo import SQLiteTypesRepository
from src.repositories.sqlite_users_repo import SQLiteUsersRepository
from src.repositories.sqlite_groups_repo import SQLiteGroupsRepository
from src.repositories.sqlite_locations_repo import SQLiteLocationsRepository
from src.repositories.sqlite_sub_types_repo import SQLiteSubTypesRepository
from src.repositories.sqlite_ip_addresses_repo import SQLiteIPAddressesRepository
from src.utils.paths import MIGRATIONS_DIR


def _db(tmp_path: Path) -> Database:
    db = Database(tmp_path / "inventory.db")
    db.run_migrations(MIGRATIONS_DIR)
    return db


def _type_id(db: Database, code: str) -> int:
    types = SQLiteTypesRepository(db)
    rec = types.find_by_code(code)
    assert rec is not None, "expected seed hardware type"
    return rec["id"]


def test_create_item_generates_asset_tag_and_audit(tmp_path: Path) -> None:
    db = _db(tmp_path)
    items = SQLiteItemsRepository(db)

    item = items.create(
        name="Demo Laptop",
        type_id=_type_id(db, "PC"),
        model="ThinkPad",
        mac_address="aa:bb:cc:dd:ee:ff",
        note="Initial seed",
    )

    assert item["id"] == 1
    assert item["asset_tag"].startswith("SDMM-PC-")
    assert item.get("ip_address") is None
    assert item.get("sub_type_id") is None
    history = items.history_for_item(item["id"])
    assert history and history[0]["reason"] == "create"

    db.close()


def test_create_rejects_duplicate_ip(tmp_path: Path) -> None:
    db = _db(tmp_path)
    items = SQLiteItemsRepository(db)

    ip = "192.168.120.10"
    items.create(name="Router", type_id=_type_id(db, "NX"), ip_address=ip)

    with pytest.raises(ValueError):
        items.create(name="Switch", type_id=_type_id(db, "NX"), ip_address=ip)

    db.close()


def test_create_requires_seeded_ip(tmp_path: Path) -> None:
    db = _db(tmp_path)
    items = SQLiteItemsRepository(db)

    with pytest.raises(ValueError):
        items.create(name="Unknown", type_id=_type_id(db, "PC"), ip_address="10.0.0.1")

    db.close()


def test_update_item_tracks_changed_fields(tmp_path: Path) -> None:
    db = _db(tmp_path)
    items = SQLiteItemsRepository(db)

    item = items.create(name="Switch", type_id=_type_id(db, "NX"))
    before_updated = item["updated_at_utc"]

    items.update(item["id"], notes="Mounted in rack", note="rack install")
    refreshed = items.get(item["id"])
    assert refreshed["notes"] == "Mounted in rack"
    assert refreshed["updated_at_utc"] >= before_updated

    history = items.history_for_item(item["id"])
    assert any(
        entry["reason"] == "update" and "notes" in (entry["changed_fields"] or "")
        for entry in history
    )

    db.close()


def test_assign_and_move_helpers_record_history(tmp_path: Path) -> None:
    db = _db(tmp_path)
    items = SQLiteItemsRepository(db)
    types_repo = SQLiteTypesRepository(db)
    users_repo = SQLiteUsersRepository(db)
    groups_repo = SQLiteGroupsRepository(db)
    locations_repo = SQLiteLocationsRepository(db)

    laptop_type = _type_id(db, "PC")
    user_id = users_repo.create(name="Alice")
    group_id = groups_repo.create(name="Engineering")
    location_id = locations_repo.create(name="HQ")

    item = items.create(name="Laptop", type_id=laptop_type)

    assert items.assign(item["id"], user_id=user_id, group_id=None, note="checked out")
    assert items.assign(item["id"], group_id=group_id)
    assert items.move_location(item["id"], location_id=location_id, note="moved")

    refreshed = items.get(item["id"])
    assert refreshed["user_id"] == user_id
    assert refreshed["group_id"] == group_id
    assert refreshed["location_id"] == location_id

    history = items.history_for_item(item["id"], limit=10)
    reasons = [entry["reason"] for entry in history]
    assert "assign" in reasons
    assert "move" in reasons

    db.close()


def test_list_records_filters_and_search(tmp_path: Path) -> None:
    db = _db(tmp_path)
    items = SQLiteItemsRepository(db)
    types_repo = SQLiteTypesRepository(db)

    laptop_type = _type_id(db, "PC")
    network_type = _type_id(db, "NX")

    laptop = items.create(name="Alpha Laptop", type_id=laptop_type)
    switch = items.create(name="Beta Switch", type_id=network_type, mac_address="bb:bb:bb:bb:bb:02")

    filtered = items.list_records(type_ids=[laptop_type])
    assert [record.id for record in filtered] == [laptop["id"]]
    assert filtered[0].type_serial == 1

    search_match = items.list_records(search="beta")
    assert [record.id for record in search_match] == [switch["id"]]
    assert search_match[0].type_serial == 1

    items.archive(switch["id"])
    assert not items.list_records(search="beta")

    db.close()


def test_ip_repository_tracks_allocations(tmp_path: Path) -> None:
    db = _db(tmp_path)
    items = SQLiteItemsRepository(db)
    types_repo = SQLiteTypesRepository(db)
    ip_repo = SQLiteIPAddressesRepository(db)

    laptop_type = _type_id(db, "PC")
    ip_repo.ensure("192.168.120.40")

    items.create(name="Gateway", type_id=laptop_type, ip_address="192.168.120.40")

    available = ip_repo.list_available()
    assert "192.168.120.40" not in available

    available_with_include = ip_repo.list_available(include="192.168.120.40")
    assert "192.168.120.40" in available_with_include

    db.close()


def test_type_change_reassigns_serial_and_extension_rules(tmp_path: Path) -> None:
    db = _db(tmp_path)
    items = SQLiteItemsRepository(db)

    pc_type = _type_id(db, "PC")
    nx_type = _type_id(db, "NX")
    landline_type = _type_id(db, "TP")

    item = items.create(name="Convertible", type_id=pc_type)
    assert item["asset_tag"] == "SDMM-PC-0001"
    assert item["extension"] is None

    items.update(item["id"], type_id=landline_type, extension="5678", note="retag")
    updated = items.get(item["id"])
    assert updated["asset_tag"].startswith("SDMM-TP-")
    assert updated["extension"] == "5678"

    items.update(item["id"], type_id=nx_type)
    retagged = items.get(item["id"])
    assert retagged["asset_tag"] == "SDMM-NX-0001"
    assert retagged["extension"] is None

    second_pc = items.create(name="Another Laptop", type_id=pc_type)
    assert second_pc["asset_tag"] == "SDMM-PC-0002"
    assert second_pc["extension"] is None

    phone = items.create(name="Desk Phone", type_id=landline_type, extension="1111")
    assert phone["extension"] == "1111"

    laptop = items.create(name="No Extension Laptop", type_id=pc_type, extension="9999")
    assert laptop["extension"] is None

    db.close()


def test_delete_moves_item_to_archive(tmp_path: Path) -> None:
    db = _db(tmp_path)
    items = SQLiteItemsRepository(db)

    sub_types_repo = SQLiteSubTypesRepository(db)
    sub_type_id = sub_types_repo.ensure("Color Printer")["id"]
    item = items.create(
        name="Legacy Printer",
        type_id=_type_id(db, "PX"),
        notes="to be retired",
        ip_address="192.168.120.30",
        sub_type_id=sub_type_id,
    )
    asset_tag = item["asset_tag"]

    assert items.delete(item["id"], note="retired from service")
    assert items.get(item["id"]) is None

    archive_entry = db.conn.execute(
        "SELECT * FROM archive WHERE asset_tag = ?", (asset_tag,)
    ).fetchone()
    assert archive_entry is not None
    assert archive_entry["name"] == "Legacy Printer"
    assert int(archive_entry["archived"]) == 1
    assert archive_entry["ip_address"] == "192.168.120.30"
    assert archive_entry["sub_type_id"] == sub_type_id

    remaining = db.conn.execute(
        "SELECT COUNT(*) AS total FROM items WHERE id = ?", (item["id"],)
    ).fetchone()
    assert remaining["total"] == 0

    db.close()
