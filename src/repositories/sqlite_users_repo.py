# Rev 0.1.0

"""SQLite repository for managing users."""
from __future__ import annotations

from typing import Dict, List, Optional
import sqlite3


class SQLiteUsersRepository:
    def __init__(self, db_or_conn) -> None:
        self._db = db_or_conn

    def _conn(self) -> sqlite3.Connection:
        if isinstance(self._db, sqlite3.Connection):
            return self._db
        if hasattr(self._db, "conn"):
            return self._db.conn
        raise RuntimeError("SQLiteUsersRepository expects Database or Connection.")

    def list_users(self, *, order_by: str = "name") -> List[Dict[str, str]]:
        cur = self._conn().execute(
            f"SELECT id, name, email FROM users ORDER BY {order_by}"
        )
        return [dict(row) for row in cur.fetchall()]

    def get(self, user_id: int) -> Optional[Dict[str, str]]:
        cur = self._conn().execute(
            "SELECT id, name, email FROM users WHERE id = ?", (user_id,)
        )
        row = cur.fetchone()
        return dict(row) if row else None

    def create(self, *, name: str, email: Optional[str] = None) -> int:
        conn = self._conn()
        with conn:
            cur = conn.execute(
                "INSERT INTO users(name, email) VALUES (?, ?)", (name, email)
            )
            return cur.lastrowid

    def update(self, user_id: int, *, name: Optional[str] = None, email: Optional[str] = None) -> bool:
        if name is None and email is None:
            return False
        sets = []
        params = []
        if name is not None:
            sets.append("name = ?")
            params.append(name)
        if email is not None:
            sets.append("email = ?")
            params.append(email)
        params.append(user_id)
        conn = self._conn()
        with conn:
            cur = conn.execute(
                f"UPDATE users SET {', '.join(sets)} WHERE id = ?", params
            )
            return cur.rowcount > 0

    def delete(self, user_id: int) -> bool:
        conn = self._conn()
        with conn:
            cur = conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
            return cur.rowcount > 0
