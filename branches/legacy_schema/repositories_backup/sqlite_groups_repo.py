# Rev 1.2.0 - Distro

"""SQLite repository for managing groups."""
from __future__ import annotations

from typing import Dict, List, Optional
import sqlite3


class SQLiteGroupsRepository:
    def __init__(self, db_or_conn) -> None:
        self._db = db_or_conn

    def _conn(self) -> sqlite3.Connection:
        if isinstance(self._db, sqlite3.Connection):
            return self._db
        if hasattr(self._db, "conn"):
            return self._db.conn
        raise RuntimeError("SQLiteGroupsRepository expects Database or Connection.")

    def list_groups(self, *, order_by: str = "name") -> List[Dict[str, str]]:
        cur = self._conn().execute(
            f"SELECT id, name FROM groups ORDER BY {order_by}"
        )
        return [dict(row) for row in cur.fetchall()]

    def get(self, group_id: int) -> Optional[Dict[str, str]]:
        cur = self._conn().execute(
            "SELECT id, name FROM groups WHERE id = ?", (group_id,)
        )
        row = cur.fetchone()
        return dict(row) if row else None

    def find_by_name(self, name: str) -> Optional[Dict[str, str]]:
        cur = self._conn().execute(
            "SELECT id, name FROM groups WHERE lower(name) = lower(?)",
            (name,),
        )
        row = cur.fetchone()
        return dict(row) if row else None

    def ensure(self, name: str) -> Dict[str, str]:
        existing = self.find_by_name(name)
        if existing:
            return existing
        new_id = self.create(name=name)
        return {"id": new_id, "name": name}

    def create(self, *, name: str) -> int:
        conn = self._conn()
        with conn:
            cur = conn.execute("INSERT INTO groups(name) VALUES (?)", (name,))
            return cur.lastrowid

    def rename(self, group_id: int, name: str) -> bool:
        conn = self._conn()
        with conn:
            cur = conn.execute(
                "UPDATE groups SET name = ? WHERE id = ?", (name, group_id)
            )
            return cur.rowcount > 0

    def delete(self, group_id: int) -> bool:
        conn = self._conn()
        with conn:
            cur = conn.execute("DELETE FROM groups WHERE id = ?", (group_id,))
            return cur.rowcount > 0
