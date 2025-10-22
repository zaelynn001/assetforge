# Rev 1.0.0

"""SQLite repository for managing locations."""
from __future__ import annotations

from typing import Dict, List, Optional
import sqlite3


class SQLiteLocationsRepository:
    def __init__(self, db_or_conn) -> None:
        self._db = db_or_conn

    def _conn(self) -> sqlite3.Connection:
        if isinstance(self._db, sqlite3.Connection):
            return self._db
        if hasattr(self._db, "conn"):
            return self._db.conn
        raise RuntimeError("SQLiteLocationsRepository expects Database or Connection.")

    def list_locations(self, *, order_by: str = "name") -> List[Dict[str, str]]:
        cur = self._conn().execute(
            f"SELECT id, name, parent_id FROM locations ORDER BY {order_by}"
        )
        return [dict(row) for row in cur.fetchall()]

    def get(self, location_id: int) -> Optional[Dict[str, str]]:
        cur = self._conn().execute(
            "SELECT id, name, parent_id FROM locations WHERE id = ?", (location_id,)
        )
        row = cur.fetchone()
        return dict(row) if row else None

    def find_by_name(self, name: str) -> Optional[Dict[str, str]]:
        cur = self._conn().execute(
            "SELECT id, name, parent_id FROM locations WHERE lower(name) = lower(?)",
            (name,),
        )
        row = cur.fetchone()
        return dict(row) if row else None

    def ensure(self, name: str) -> Dict[str, str]:
        existing = self.find_by_name(name)
        if existing:
            return existing
        new_id = self.create(name=name)
        return {"id": new_id, "name": name, "parent_id": None}

    def create(self, *, name: str, parent_id: Optional[int] = None) -> int:
        conn = self._conn()
        with conn:
            cur = conn.execute(
                "INSERT INTO locations(name, parent_id) VALUES (?, ?)",
                (name, parent_id),
            )
            return cur.lastrowid

    def rename(self, location_id: int, name: str) -> bool:
        conn = self._conn()
        with conn:
            cur = conn.execute(
                "UPDATE locations SET name = ? WHERE id = ?", (name, location_id)
            )
            return cur.rowcount > 0

    def reparent(self, location_id: int, parent_id: Optional[int]) -> bool:
        conn = self._conn()
        with conn:
            cur = conn.execute(
                "UPDATE locations SET parent_id = ? WHERE id = ?",
                (parent_id, location_id),
            )
            return cur.rowcount > 0

    def delete(self, location_id: int) -> bool:
        conn = self._conn()
        with conn:
            cur = conn.execute("DELETE FROM locations WHERE id = ?", (location_id,))
            return cur.rowcount > 0
