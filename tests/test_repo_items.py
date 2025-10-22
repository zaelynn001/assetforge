# Rev 1.0.0

"""Repository integration tests for items and related helpers."""
from __future__ import annotations

from pathlib import Path

from src.repositories.db import Database
from src.repositories.sqlite_items_repo import SQLiteItemsRepository
from src.repositories.sqlite_types_repo import SQLiteTypesRepository
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
    items = SQLiteItemsRepository(db)

    item = items.create(
        name="Demo Laptop",
        type_id=_type_id(db, "PC"),
        model="ThinkPad",
        mac_address="aa:bb:cc:dd:ee:ff",
        note="Initial seed",
    )

    assert item["id"] == 1
    assert item["master_id"] is not None
    assert item["asset_tag"].startswith("SDMM-PC-")
    history = items.history_for_item(item["id"])
    assert history and history[0]["reason"] == "create"

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
    assert refreshed["master_id"] == item["master_id"]

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
    original_master = item["master_id"]

    assert items.assign(item["id"], user_id=user_id, group_id=None, note="checked out")
    assert items.assign(item["id"], group_id=group_id)
    assert items.move_location(item["id"], location_id=location_id, note="moved")

    refreshed = items.get(item["id"])
    assert refreshed["master_id"] == original_master

    history = items.history_for_item(item["id"], limit=10)
    reasons = [entry["reason"] for entry in history]
    assert "assign" in reasons
    assert "move" in reasons

    db.close()
