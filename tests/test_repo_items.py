# Rev 0.1.0

"""Repository integration tests for items and related helpers."""
from __future__ import annotations

from pathlib import Path

from src.repositories.db import Database
from src.repositories.sqlite_items_repo import SQLiteItemsRepository
from src.repositories.sqlite_types_repo import SQLiteTypesRepository
from src.repositories.sqlite_attributes_repo import SQLiteAttributesRepository
from src.repositories.sqlite_updates_repo import SQLiteUpdatesRepository
from src.repositories.sqlite_users_repo import SQLiteUsersRepository
from src.repositories.sqlite_groups_repo import SQLiteGroupsRepository
from src.repositories.sqlite_locations_repo import SQLiteLocationsRepository
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
    updates = SQLiteUpdatesRepository(db)
    items = SQLiteItemsRepository(db, updates_repo=updates)

    item = items.create(
        name="Demo Laptop",
        type_id=_type_id(db, "LT"),
        model="ThinkPad",
        mac_address="aa:bb:cc:dd:ee:ff",
        note="Initial seed",
    )

    assert item["id"] == 1
    assert item["asset_tag"].startswith("SDMM-LT-")
    history = updates.list_for_item(item["id"])
    assert history and history[0]["reason"] == "create"

    db.close()


def test_update_item_tracks_changed_fields(tmp_path: Path) -> None:
    db = _db(tmp_path)
    updates = SQLiteUpdatesRepository(db)
    items = SQLiteItemsRepository(db, updates_repo=updates)

    item = items.create(name="Switch", type_id=_type_id(db, "SW"))
    before_updated = item["updated_at_utc"]

    items.update(item["id"], notes="Mounted in rack", note="rack install")
    refreshed = items.get(item["id"])
    assert refreshed["notes"] == "Mounted in rack"
    assert refreshed["updated_at_utc"] >= before_updated

    history = updates.list_for_item(item["id"])
    assert any(
        entry["reason"] == "update" and "notes" in (entry["changed_fields"] or "")
        for entry in history
    )

    db.close()


def test_attribute_helpers_record_history(tmp_path: Path) -> None:
    db = _db(tmp_path)
    updates = SQLiteUpdatesRepository(db)
    items = SQLiteItemsRepository(db, updates_repo=updates)
    attrs = SQLiteAttributesRepository(db, updates_repo=updates)

    item = items.create(name="Server", type_id=_type_id(db, "SR"))
    attrs.set_attribute(item_id=item["id"], key="cpu", value="Xeon")
    attrs.set_attribute(
        item_id=item["id"], key="cpu", value="Xeon Gold", note="upgraded"
    )
    rows = attrs.list_for_item(item["id"])
    assert rows[0]["attr_value"] == "Xeon Gold"

    history = updates.list_for_item(item["id"])
    reasons = {entry["reason"] for entry in history}
    assert {"attribute_add", "attribute_update"}.issubset(reasons)

    db.close()


def test_assign_and_move_helpers_record_history(tmp_path: Path) -> None:
    db = _db(tmp_path)
    updates = SQLiteUpdatesRepository(db)
    items = SQLiteItemsRepository(db, updates_repo=updates)
    types_repo = SQLiteTypesRepository(db)
    users_repo = SQLiteUsersRepository(db)
    groups_repo = SQLiteGroupsRepository(db)
    locations_repo = SQLiteLocationsRepository(db)

    laptop_type = _type_id(db, "LT")
    user_id = users_repo.create(name="Alice")
    group_id = groups_repo.create(name="Engineering")
    location_id = locations_repo.create(name="HQ")

    item = items.create(name="Laptop", type_id=laptop_type)

    assert items.assign(item["id"], user_id=user_id, group_id=None, note="checked out")
    assert items.assign(item["id"], group_id=group_id)
    assert items.move_location(item["id"], location_id=location_id, note="moved")

    history = updates.list_for_item(item["id"], limit=10)
    reasons = [entry["reason"] for entry in history]
    assert "assign" in reasons
    assert "move" in reasons

    db.close()
