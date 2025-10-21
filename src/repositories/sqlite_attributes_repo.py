# Rev 0.1.0

"""SQLite repository for item attribute key/value pairs."""
from __future__ import annotations

import json
from typing import Dict, List, Optional
import sqlite3

from .sqlite_updates_repo import SQLiteUpdatesRepository


class SQLiteAttributesRepository:
    def __init__(self, db_or_conn, updates_repo: SQLiteUpdatesRepository | None = None) -> None:
        self._db = db_or_conn
        self._updates_repo = updates_repo or SQLiteUpdatesRepository(db_or_conn)

    def _conn(self) -> sqlite3.Connection:
        if isinstance(self._db, sqlite3.Connection):
            return self._db
        if hasattr(self._db, "conn"):
            return self._db.conn
        raise RuntimeError("SQLiteAttributesRepository expects Database or Connection.")

    def list_for_item(self, item_id: int) -> List[Dict[str, str]]:
        cur = self._conn().execute(
            """
            SELECT id, item_id, attr_key, attr_value, created_at_utc, updated_at_utc
            FROM item_attributes
            WHERE item_id = ?
            ORDER BY attr_key
            """,
            (item_id,),
        )
        return [dict(row) for row in cur.fetchall()]

    def get(self, item_id: int, key: str) -> Optional[Dict[str, str]]:
        cur = self._conn().execute(
            """
            SELECT id, item_id, attr_key, attr_value, created_at_utc, updated_at_utc
            FROM item_attributes
            WHERE item_id = ? AND attr_key = ?
            """,
            (item_id, key),
        )
        row = cur.fetchone()
        return dict(row) if row else None

    def set_attribute(
        self,
        *,
        item_id: int,
        key: str,
        value: Optional[str],
        note: Optional[str] = None,
    ) -> bool:
        conn = self._conn()
        existing = self.get(item_id, key)
        reason = "attribute_add" if existing is None else "attribute_update"

        with conn:
            if existing is None:
                conn.execute(
                    """
                    INSERT INTO item_attributes(item_id, attr_key, attr_value)
                    VALUES (?, ?, ?)
                    """,
                    (item_id, key, value),
                )
            else:
                if existing["attr_value"] == value:
                    return False
                conn.execute(
                    """
                    UPDATE item_attributes
                       SET attr_value = ?, updated_at_utc = strftime('%Y-%m-%dT%H:%M:%SZ','now')
                     WHERE item_id = ? AND attr_key = ?
                    """,
                    (value, item_id, key),
                )

        before_json = json.dumps(existing) if existing else None
        after = self.get(item_id, key)
        after_json = json.dumps(after) if after else None

        self._updates_repo.record(
            item_id=item_id,
            reason=reason,
            note=note,
            changed_fields=[f"attr:{key}"],
            snapshot_before_json=before_json,
            snapshot_after_json=after_json,
        )
        return True

    def delete_attribute(self, *, item_id: int, key: str, note: Optional[str] = None) -> bool:
        existing = self.get(item_id, key)
        if not existing:
            return False
        conn = self._conn()
        with conn:
            conn.execute(
                "DELETE FROM item_attributes WHERE item_id = ? AND attr_key = ?",
                (item_id, key),
            )
        self._updates_repo.record(
            item_id=item_id,
            reason="attribute_remove",
            note=note,
            changed_fields=[f"attr:{key}"],
            snapshot_before_json=json.dumps(existing),
            snapshot_after_json=None,
        )
        return True
