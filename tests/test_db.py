# Rev 1.2.0 - Distro

"""Database smoke tests covering migrations and triggers."""
from __future__ import annotations

from pathlib import Path

from src.repositories.db import Database
from src.repositories.sqlite_items_repo import SQLiteItemsRepository
from src.utils.paths import MIGRATIONS_DIR


def _db(tmp_path: Path) -> Database:
    return Database(tmp_path / "inventory.db")


def test_run_migrations_seeds_reference_data(tmp_path: Path) -> None:
    db = _db(tmp_path)
    try:
        applied = db.run_migrations(MIGRATIONS_DIR)
        assert "0001_init.sql" in applied
        assert "0002_flatten_items.sql" in applied
        assert "0003_items_constraints.sql" in applied

        codes = [
            row["code"]
            for row in db.conn.execute("SELECT code FROM hardware_types ORDER BY code")
        ]
        expected = {"PC", "NX", "TP", "PX", "CC", "LX", "EX", "PD", "AP", "MX"}
        assert expected.issubset(set(codes))

        # Second run should be idempotent
        assert db.run_migrations(MIGRATIONS_DIR) == []
    finally:
        db.close()


def test_asset_tag_trigger_generates_expected_value(tmp_path: Path) -> None:
    db = _db(tmp_path)
    try:
        db.run_migrations(MIGRATIONS_DIR)

        items_repo = SQLiteItemsRepository(db)
        laptop_type = db.conn.execute(
            "SELECT id FROM hardware_types WHERE code = ?", ("PC",)
        ).fetchone()["id"]

        item = items_repo.create(
            name="M1 Laptop",
            model="ThinkPad X1",
            type_id=laptop_type,
        )

        assert item["id"] == 1
        assert item["asset_tag"] == "SDMM-PC-0001"
    finally:
        db.close()
