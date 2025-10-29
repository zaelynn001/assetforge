# Rev 1.2.0 - Distro

from __future__ import annotations

import csv
from pathlib import Path
from zipfile import ZipFile

import pytest

from src.repositories.db import Database
from src.repositories.sqlite_items_repo import SQLiteItemsRepository
from src.repositories.sqlite_types_repo import SQLiteTypesRepository
from src.repositories.sqlite_locations_repo import SQLiteLocationsRepository
from src.repositories.sqlite_users_repo import SQLiteUsersRepository
from src.repositories.sqlite_groups_repo import SQLiteGroupsRepository
from src.repositories.sqlite_ip_addresses_repo import SQLiteIPAddressesRepository
from src.repositories.sqlite_sub_types_repo import SQLiteSubTypesRepository
from src.services.export_xlsx import export_inventory
from src.services.import_inventory import import_inventory_csv, InventoryImportError
from src.utils.paths import MIGRATIONS_DIR


def _database(tmp_path: Path) -> Database:
    db = Database(tmp_path / "inventory.db")
    db.run_migrations(MIGRATIONS_DIR)
    return db


def test_export_inventory_generates_xlsx(tmp_path: Path) -> None:
    db = _database(tmp_path)
    try:
        items_repo = SQLiteItemsRepository(db)
        types_repo = SQLiteTypesRepository(db)

        laptop_type = types_repo.find_by_code("PC")["id"]
        items_repo.create(name="Laptop", type_id=laptop_type, ip_address="192.168.120.11")

        out_path = tmp_path / "inventory.xlsx"
        items = items_repo.list_items()
        export_inventory(out_path, items=items)

        assert out_path.exists()
        with ZipFile(out_path) as zf:
            assert "xl/worksheets/sheet1.xml" in zf.namelist()
            sheet1 = zf.read("xl/worksheets/sheet1.xml").decode()
            assert "Laptop" in sheet1
            assert "IP Address" in sheet1
            assert "Sub Type" in sheet1
    finally:
        db.close()


def test_import_inventory_csv_creates_records(tmp_path: Path) -> None:
    db = _database(tmp_path)
    try:
        items_repo = SQLiteItemsRepository(db)
        types_repo = SQLiteTypesRepository(db)
        locations_repo = SQLiteLocationsRepository(db)
        users_repo = SQLiteUsersRepository(db)
        groups_repo = SQLiteGroupsRepository(db)
        ip_repo = SQLiteIPAddressesRepository(db)
        sub_types_repo = SQLiteSubTypesRepository(db)

        csv_path = tmp_path / "import.csv"
        with csv_path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(["name", "type", "location", "ip_address", "sub_type"])
            writer.writerow(["Workstation", "PC", "HQ", "192.168.120.20", "Desktop"])

        created, notes = import_inventory_csv(
            csv_path,
            types_repo=types_repo,
            locations_repo=locations_repo,
            users_repo=users_repo,
            groups_repo=groups_repo,
            ip_repo=ip_repo,
            sub_types_repo=sub_types_repo,
            items_repo=items_repo,
        )

        assert created == 1
        assert not notes
        items = items_repo.list_items()
        assert len(items) == 1
        assert items[0]["name"] == "Workstation"
        assert items[0]["ip_address"] == "192.168.120.20"
        assert items[0]["sub_type_name"] == "Desktop"
        assert items[0]["user_name"] is None
        assert items[0]["group_name"] is None
        assert items[0]["extension"] is None
    finally:
        db.close()


def test_import_inventory_csv_rejects_unknown_ip(tmp_path: Path) -> None:
    db = _database(tmp_path)
    try:
        items_repo = SQLiteItemsRepository(db)
        types_repo = SQLiteTypesRepository(db)
        locations_repo = SQLiteLocationsRepository(db)
        users_repo = SQLiteUsersRepository(db)
        groups_repo = SQLiteGroupsRepository(db)
        sub_types_repo = SQLiteSubTypesRepository(db)
        ip_repo = SQLiteIPAddressesRepository(db)

        csv_path = tmp_path / "import_bad_ip.csv"
        with csv_path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(["name", "type", "ip_address"])
            writer.writerow(["BadDevice", "PC", "10.0.0.1"])
            writer.writerow(["ClearsIP", "PC", "None"])

        created, notes = import_inventory_csv(
            csv_path,
            types_repo=types_repo,
            locations_repo=locations_repo,
            users_repo=users_repo,
            groups_repo=groups_repo,
            ip_repo=ip_repo,
            sub_types_repo=sub_types_repo,
            items_repo=items_repo,
        )

        assert created == 1
        assert notes and "IP address '10.0.0.1'" in notes[0]
        items = items_repo.list_items()
        assert len(items) == 1
        assert items[0]["name"] == "ClearsIP"
        assert items[0]["ip_address"] is None
    finally:
        db.close()


def test_import_inventory_csv_rejects_unknown_sub_type(tmp_path: Path) -> None:
    db = _database(tmp_path)
    try:
        items_repo = SQLiteItemsRepository(db)
        types_repo = SQLiteTypesRepository(db)
        locations_repo = SQLiteLocationsRepository(db)
        users_repo = SQLiteUsersRepository(db)
        groups_repo = SQLiteGroupsRepository(db)
        sub_types_repo = SQLiteSubTypesRepository(db)
        ip_repo = SQLiteIPAddressesRepository(db)

        csv_path = tmp_path / "import_bad_subtype.csv"
        with csv_path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(["name", "type", "sub_type"])
            writer.writerow(["Mystery", "PC", "Nonexistent SubType"])

        created, notes = import_inventory_csv(
            csv_path,
            types_repo=types_repo,
            locations_repo=locations_repo,
            users_repo=users_repo,
            groups_repo=groups_repo,
            ip_repo=ip_repo,
            sub_types_repo=sub_types_repo,
            items_repo=items_repo,
        )

        assert created == 0
        assert notes and "Sub type 'Nonexistent SubType'" in notes[0]
        assert not items_repo.list_items()
    finally:
        db.close()
