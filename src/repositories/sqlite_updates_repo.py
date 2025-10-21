# Rev 0.1.0

"""SQLite repository for audit history entries."""
from __future__ import annotations

from typing import Dict, Iterable, List, Optional
from datetime import datetime, timezone
import sqlite3


class SQLiteUpdatesRepository:
    """Handles item_updates CRUD."""

    def __init__(self, db_or_conn) -> None:
        self._db = db_or_conn

    def _conn(self) -> sqlite3.Connection:
        if isinstance(self._db, sqlite3.Connection):
            return self._db
        if hasattr(self._db, "conn"):
            return self._db.conn
        raise RuntimeError("SQLiteUpdatesRepository expects Database or Connection.")

    def record(
        self,
        *,
        item_id: int,
        reason: str,
        note: Optional[str] = None,
        changed_fields: Optional[Iterable[str]] = None,
        snapshot_before_json: Optional[str] = None,
        snapshot_after_json: Optional[str] = None,
    ) -> int:
        conn = self._conn()
        with conn:
            cur = conn.execute(
                """
                INSERT INTO item_updates(
                    item_id,
                    reason,
                    note,
                    changed_fields,
                    snapshot_before_json,
                    snapshot_after_json,
                    created_at_utc
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item_id,
                    reason,
                    note,
                    ",".join(changed_fields) if changed_fields else None,
                    snapshot_before_json,
                    snapshot_after_json,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            return cur.lastrowid

    def list_for_item(self, item_id: int, *, limit: int = 50) -> List[Dict[str, str]]:
        cur = self._conn().execute(
            """
            SELECT id, item_id, reason, note, changed_fields,
                   snapshot_before_json, snapshot_after_json, created_at_utc
            FROM item_updates
            WHERE item_id = ?
            ORDER BY datetime(created_at_utc) DESC, id DESC
            LIMIT ?
            """,
            (item_id, limit),
        )
        return [dict(row) for row in cur.fetchall()]
