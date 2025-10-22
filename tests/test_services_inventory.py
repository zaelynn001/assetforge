# Rev 1.0.0

from __future__ import annotations

import csv
from pathlib import Path
from zipfile import ZipFile

from src.repositories.db import Database
from src.repositories.sqlite_items_repo import SQLiteItemsRepository
from src.repositories.sqlite_types_repo import SQLiteTypesRepository
from src.repositories.sqlite_locations_repo import SQLiteLocationsRepository
from src.repositories.sqlite_users_repo import SQLiteUsersRepository
from src.repositories.sqlite_groups_repo import SQLiteGroupsRepository
from src.services.export_xlsx import export_inventory
from src.services.import_inventory import import_inventory_csv
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
        items_repo.create(name="Laptop", type_id=laptop_type)

        out_path = tmp_path / "inventory.xlsx"
        items = items_repo.list_items()
        export_inventory(out_path, items=items, attributes_map={item["id"]: [] for item in items})

        assert out_path.exists()
        with ZipFile(out_path) as zf:
            assert "xl/worksheets/sheet1.xml" in zf.namelist()
            assert "xl/worksheets/sheet2.xml" in zf.namelist()
            sheet1 = zf.read("xl/worksheets/sheet1.xml").decode()
            assert "Laptop" in sheet1
            sheet2 = zf.read("xl/worksheets/sheet2.xml").decode()
            assert "Attribute" in sheet2
            assert sheet2.count("<row") == 1
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

        csv_path = tmp_path / "import.csv"
        with csv_path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(["name", "type", "location", "user", "group", "attr:cpu"])
            writer.writerow(["Workstation", "PC", "HQ", "Pat", "IT", "Ryzen"])

        created, notes = import_inventory_csv(
            csv_path,
            types_repo=types_repo,
            locations_repo=locations_repo,
            users_repo=users_repo,
            groups_repo=groups_repo,
            items_repo=items_repo,
        )

        assert created == 1
        assert not notes
        items = items_repo.list_items()
        assert len(items) == 1
        assert items[0]["name"] == "Workstation"
    finally:
        db.close()
