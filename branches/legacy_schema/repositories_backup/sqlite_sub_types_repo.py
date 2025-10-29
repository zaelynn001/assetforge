# Rev 1.2.0 - Distro

"""SQLite repository for hardware sub-types."""
from __future__ import annotations

from typing import Dict, Optional

from .db import Database


class SQLiteSubTypesRepository:
    def __init__(self, database: Database) -> None:
        if not isinstance(database, Database):
            raise RuntimeError("SQLiteSubTypesRepository expects a Database instance.")
        self._db = database
        self._conn = database.conn

    def list_sub_types(self, order_by: str = "name") -> list[Dict[str, str]]:
        cur = self._conn.execute(f"SELECT id, name FROM sub_types ORDER BY {order_by}")
        return [dict(row) for row in cur.fetchall()]

    def find_by_name(self, name: str) -> Optional[Dict[str, str]]:
        cur = self._conn.execute(
            "SELECT id, name FROM sub_types WHERE lower(name) = lower(?)",
            (name.strip(),),
        )
        row = cur.fetchone()
        return dict(row) if row else None

    def get(self, sub_type_id: int) -> Optional[Dict[str, str]]:
        cur = self._conn.execute(
            "SELECT id, name FROM sub_types WHERE id = ?",
            (sub_type_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None

    def create(self, name: str) -> Dict[str, str]:
        normalized = name.strip()
        with self._conn:
            cur = self._conn.execute(
                "INSERT INTO sub_types(name) VALUES (?)",
                (normalized,),
            )
        return {"id": int(cur.lastrowid), "name": normalized}

    def update(self, sub_type_id: int, *, name: str) -> Dict[str, str]:
        normalized = name.strip()
        with self._conn:
            self._conn.execute(
                "UPDATE sub_types SET name = ? WHERE id = ?",
                (normalized, sub_type_id),
            )
        record = self.get(sub_type_id)
        if record is None:
            raise ValueError(f"Sub-type {sub_type_id} not found")
        return record

    def delete(self, sub_type_id: int) -> bool:
        with self._conn:
            cur = self._conn.execute(
                "DELETE FROM sub_types WHERE id = ?",
                (sub_type_id,),
            )
        return cur.rowcount > 0

    def ensure(self, name: str) -> Dict[str, str]:
        existing = self.find_by_name(name)
        if existing:
            return existing
        return self.create(name)
