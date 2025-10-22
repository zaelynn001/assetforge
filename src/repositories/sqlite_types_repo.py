# Rev 1.0.0

"""SQLite repository for hardware types."""
from __future__ import annotations

from typing import Dict, List, Optional
import sqlite3


class SQLiteTypesRepository:
    """CRUD operations for the hardware_types table."""

    def __init__(self, db_or_conn) -> None:
        self._db = db_or_conn

    def _conn(self) -> sqlite3.Connection:
        if isinstance(self._db, sqlite3.Connection):
            return self._db
        if hasattr(self._db, "conn"):
            return self._db.conn
        raise RuntimeError("SQLiteTypesRepository expects Database or Connection.")

    # ---- queries -----------------------------------------------------
    def list_types(self, *, order_by: str = "name") -> List[Dict[str, str]]:
        conn = self._conn()
        cur = conn.execute(
            f"SELECT id, name, code FROM hardware_types ORDER BY {order_by}"
        )
        return [dict(row) for row in cur.fetchall()]

    def get(self, type_id: int) -> Optional[Dict[str, str]]:
        conn = self._conn()
        cur = conn.execute(
            "SELECT id, name, code FROM hardware_types WHERE id = ?", (type_id,)
        )
        row = cur.fetchone()
        return dict(row) if row else None

    def find_by_code(self, code: str) -> Optional[Dict[str, str]]:
        conn = self._conn()
        cur = conn.execute(
            "SELECT id, name, code FROM hardware_types WHERE code = ?", (code,)
        )
        row = cur.fetchone()
        return dict(row) if row else None

    def find_by_name(self, name: str) -> Optional[Dict[str, str]]:
        conn = self._conn()
        cur = conn.execute(
            "SELECT id, name, code FROM hardware_types WHERE lower(name) = lower(?)",
            (name,),
        )
        row = cur.fetchone()
        return dict(row) if row else None

    # ---- mutations ---------------------------------------------------
    def create(self, *, name: str, code: str) -> int:
        conn = self._conn()
        with conn:
            cur = conn.execute(
                "INSERT INTO hardware_types(name, code) VALUES (?, ?)", (name, code)
            )
            return cur.lastrowid

    def update(self, type_id: int, *, name: Optional[str] = None, code: Optional[str] = None) -> bool:
        if name is None and code is None:
            return False
        sets = []
        params = []
        if name is not None:
            sets.append("name = ?")
            params.append(name)
        if code is not None:
            sets.append("code = ?")
            params.append(code)
        params.append(type_id)
        conn = self._conn()
        with conn:
            cur = conn.execute(
                f"UPDATE hardware_types SET {', '.join(sets)} WHERE id = ?", params
            )
            return cur.rowcount > 0

    def delete(self, type_id: int) -> bool:
        conn = self._conn()
        with conn:
            cur = conn.execute("DELETE FROM hardware_types WHERE id = ?", (type_id,))
            return cur.rowcount > 0
