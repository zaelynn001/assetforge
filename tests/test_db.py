# Rev 0.1.0

"""Database smoke tests covering migrations and triggers."""
from __future__ import annotations

from pathlib import Path

from src.repositories.db import Database
from src.utils.paths import MIGRATIONS_DIR


def _db(tmp_path: Path) -> Database:
    return Database(tmp_path / "inventory.db")


def test_run_migrations_seeds_reference_data(tmp_path: Path) -> None:
    db = _db(tmp_path)
    try:
        applied = db.run_migrations(MIGRATIONS_DIR)
        assert "0001_init.sql" in applied

        codes = [
            row["code"]
            for row in db.conn.execute("SELECT code FROM hardware_types ORDER BY code")
        ]
        assert {"AP", "DT", "LT", "SW"}.issubset(set(codes))

        # Second run should be idempotent
        assert db.run_migrations(MIGRATIONS_DIR) == []
    finally:
        db.close()


def test_asset_tag_trigger_generates_expected_value(tmp_path: Path) -> None:
    db = _db(tmp_path)
    try:
        db.run_migrations(MIGRATIONS_DIR)

        type_id = db.conn.execute(
            "SELECT id FROM hardware_types WHERE code = ?", ("LT",)
        ).fetchone()["id"]

        db.conn.execute(
            """
            INSERT INTO hardware_items(name, model, type_id, mac_address, asset_tag)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("M1 Laptop", "ThinkPad X1", type_id, None, "SDMM-LT-0000"),
        )

        row = db.conn.execute(
            "SELECT id, asset_tag FROM hardware_items LIMIT 1"
        ).fetchone()

        assert row["id"] == 1
        assert row["asset_tag"] == "SDMM-LT-0001"
    finally:
        db.close()
