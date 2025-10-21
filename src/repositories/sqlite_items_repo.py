# Rev 0.1.0

"""SQLite repository for inventory items."""
from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List, Optional
import sqlite3

from .sqlite_attributes_repo import SQLiteAttributesRepository
from .sqlite_updates_repo import SQLiteUpdatesRepository


class SQLiteItemsRepository:
    """CRUD operations plus audit recording for hardware_items."""

    _AUDIT_FIELDS = (
        "name",
        "model",
        "type_id",
        "mac_address",
        "location_id",
        "user_id",
        "group_id",
        "notes",
    )

    def __init__(
        self,
        db_or_conn,
        *,
        updates_repo: SQLiteUpdatesRepository | None = None,
        attributes_repo: SQLiteAttributesRepository | None = None,
    ) -> None:
        self._db = db_or_conn
        self._updates = updates_repo or SQLiteUpdatesRepository(db_or_conn)
        self._attributes = attributes_repo or SQLiteAttributesRepository(
            db_or_conn, self._updates
        )

    def _conn(self) -> sqlite3.Connection:
        if isinstance(self._db, sqlite3.Connection):
            return self._db
        if hasattr(self._db, "conn"):
            return self._db.conn
        raise RuntimeError("SQLiteItemsRepository expects Database or Connection.")

    # ---- queries -----------------------------------------------------
    def list_items(
        self,
        *,
        order_by: str = "hi.updated_at_utc DESC",
        type_ids: Optional[Iterable[int]] = None,
        location_ids: Optional[Iterable[int]] = None,
        user_ids: Optional[Iterable[int]] = None,
        group_ids: Optional[Iterable[int]] = None,
        search: Optional[str] = None,
        limit: int = 500,
    ) -> List[Dict[str, Any]]:
        where: List[str] = []
        params: List[Any] = []

        def _in_clause(column: str, values: Iterable[int]) -> str:
            placeholders = ", ".join("?" for _ in values)
            return f"{column} IN ({placeholders})"

        if type_ids:
            values = [v for v in type_ids if v is not None]
            if values:
                where.append(_in_clause("hi.type_id", values))
                params.extend(values)
        if location_ids:
            values = [v for v in location_ids if v is not None]
            if values:
                where.append(_in_clause("hi.location_id", values))
                params.extend(values)
        if user_ids:
            values = [v for v in user_ids if v is not None]
            if values:
                where.append(_in_clause("hi.user_id", values))
                params.extend(values)
        if group_ids:
            values = [v for v in group_ids if v is not None]
            if values:
                where.append(_in_clause("hi.group_id", values))
                params.extend(values)

        if search:
            like = f"%{search.lower()}%"
            where.append(
                """
                (
                    lower(hi.name) LIKE ?
                    OR lower(COALESCE(hi.model, '')) LIKE ?
                    OR lower(COALESCE(hi.mac_address, '')) LIKE ?
                    OR lower(hi.asset_tag) LIKE ?
                )
                """
            )
            params.extend([like, like, like, like])

        where_clause = "WHERE " + " AND ".join(where) if where else ""

        sql = f"""
            SELECT
                hi.id,
                hi.name,
                hi.model,
                hi.type_id,
                hi.mac_address,
                hi.location_id,
                hi.user_id,
                hi.group_id,
                hi.notes,
                hi.asset_tag,
                hi.created_at_utc,
                hi.updated_at_utc,
                ht.name AS type_name,
                ht.code AS type_code,
                loc.name AS location_name,
                usr.name AS user_name,
                grp.name AS group_name
            FROM hardware_items AS hi
            LEFT JOIN hardware_types AS ht ON hi.type_id = ht.id
            LEFT JOIN locations AS loc ON hi.location_id = loc.id
            LEFT JOIN users AS usr ON hi.user_id = usr.id
            LEFT JOIN groups AS grp ON hi.group_id = grp.id
            {where_clause}
            ORDER BY {order_by}
            LIMIT ?
        """
        params.append(limit)
        cur = self._conn().execute(sql, params)
        return [dict(row) for row in cur.fetchall()]

    def get(self, item_id: int) -> Optional[Dict[str, Any]]:
        cur = self._conn().execute(
            """
            SELECT id, name, model, type_id, mac_address,
                   location_id, user_id, group_id, notes,
                   asset_tag, created_at_utc, updated_at_utc
            FROM hardware_items
            WHERE id = ?
            """,
            (item_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None

    def get_details(self, item_id: int) -> Optional[Dict[str, Any]]:
        cur = self._conn().execute(
            """
            SELECT
                hi.id,
                hi.name,
                hi.model,
                hi.type_id,
                hi.mac_address,
                hi.location_id,
                hi.user_id,
                hi.group_id,
                hi.notes,
                hi.asset_tag,
                hi.created_at_utc,
                hi.updated_at_utc,
                ht.name AS type_name,
                ht.code AS type_code,
                loc.name AS location_name,
                usr.name AS user_name,
                usr.email AS user_email,
                grp.name AS group_name
            FROM hardware_items AS hi
            LEFT JOIN hardware_types AS ht ON hi.type_id = ht.id
            LEFT JOIN locations AS loc ON hi.location_id = loc.id
            LEFT JOIN users AS usr ON hi.user_id = usr.id
            LEFT JOIN groups AS grp ON hi.group_id = grp.id
            WHERE hi.id = ?
            """,
            (item_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None

    # ---- mutations ---------------------------------------------------
    def create(
        self,
        *,
        name: str,
        type_id: int,
        model: Optional[str] = None,
        mac_address: Optional[str] = None,
        location_id: Optional[int] = None,
        user_id: Optional[int] = None,
        group_id: Optional[int] = None,
        notes: Optional[str] = None,
        attributes: Optional[Dict[str, Optional[str]]] = None,
        note: Optional[str] = None,
    ) -> Dict[str, Any]:
        conn = self._conn()
        type_code = self._type_code(type_id)
        placeholder_tag = f"SDMM-{type_code}-0000"
        mac_norm = self._normalize_mac(mac_address)

        with conn:
            cur = conn.execute(
                """
                INSERT INTO hardware_items(
                    name, model, type_id, mac_address,
                    location_id, user_id, group_id, notes, asset_tag
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    name,
                    model,
                    type_id,
                    mac_norm,
                    location_id,
                    user_id,
                    group_id,
                    notes,
                    placeholder_tag,
                ),
            )
            item_id = cur.lastrowid

        if attributes:
            for key, value in attributes.items():
                self._attributes.set_attribute(
                    item_id=item_id,
                    key=key,
                    value=value,
                    note="set during create",
                )

        item = self.get(item_id)
        self._record_audit(
            item_id=item_id,
            reason="create",
            note=note,
            changed_fields=self._AUDIT_FIELDS,
            snapshot_after=item,
        )
        return item

    def update(
        self,
        item_id: int,
        *,
        name: Optional[str] = None,
        model: Optional[str] = None,
        type_id: Optional[int] = None,
        mac_address: Optional[str] = None,
        location_id: Optional[int] = None,
        user_id: Optional[int] = None,
        group_id: Optional[int] = None,
        notes: Optional[str] = None,
        note: Optional[str] = None,
        reason: str = "update",
    ) -> bool:
        fields = {
            "name": name,
            "model": model,
            "type_id": type_id,
            "mac_address": self._normalize_mac(mac_address) if mac_address is not None else None,
            "location_id": location_id,
            "user_id": user_id,
            "group_id": group_id,
            "notes": notes,
        }
        fields = {k: v for k, v in fields.items() if v is not None}
        if not fields and note is None:
            return False

        before = self.get(item_id)
        if not before:
            raise ValueError(f"Item {item_id} not found")

        sets = []
        params: List[Any] = []
        for column, value in fields.items():
            sets.append(f"{column} = ?")
            params.append(value)

        changed_columns: List[str] = []
        conn = self._conn()
        with conn:
            if sets:
                params.append(item_id)
                cur = conn.execute(
                    f"UPDATE hardware_items SET {', '.join(sets)} WHERE id = ?",
                    params,
                )
                if cur.rowcount == 0:
                    return False
                changed_columns = [
                    column for column in fields
                    if before.get(column) != fields[column]
                ]

        after = self.get(item_id)
        if changed_columns or note:
            self._record_audit(
                item_id=item_id,
                reason=reason,
                note=note,
                changed_fields=changed_columns or None,
                snapshot_before=before,
                snapshot_after=after,
            )
        return bool(changed_columns)

    def delete(self, item_id: int, *, note: Optional[str] = None) -> bool:
        before = self.get(item_id)
        if not before:
            return False
        conn = self._conn()
        with conn:
            conn.execute("DELETE FROM hardware_items WHERE id = ?", (item_id,))
        self._record_audit(
            item_id=item_id,
            reason="delete",
            note=note,
            changed_fields=self._AUDIT_FIELDS,
            snapshot_before=before,
            snapshot_after=None,
        )
        return True

    # ---- helpers -----------------------------------------------------
    def assign(
        self,
        item_id: int,
        *,
        user_id: Optional[int] = None,
        group_id: Optional[int] = None,
        note: Optional[str] = None,
    ) -> bool:
        before = self.get(item_id)
        if not before:
            raise ValueError(f"Item {item_id} not found")

        updates: Dict[str, Any] = {}
        if user_id is not None or (user_id is None and before.get("user_id") is not None):
            updates["user_id"] = user_id
        if group_id is not None or (group_id is None and before.get("group_id") is not None):
            updates["group_id"] = group_id

        if not updates:
            return False

        self.update(item_id, **updates, reason="assign", note=note)
        return True

    def move_location(
        self,
        item_id: int,
        *,
        location_id: Optional[int],
        note: Optional[str] = None,
    ) -> bool:
        before = self.get(item_id)
        if not before:
            raise ValueError(f"Item {item_id} not found")

        if before.get("location_id") == location_id:
            return False

        self.update(item_id, location_id=location_id, reason="move", note=note)
        return True

    def _type_code(self, type_id: int) -> str:
        cur = self._conn().execute(
            "SELECT code FROM hardware_types WHERE id = ?", (type_id,)
        )
        row = cur.fetchone()
        if not row:
            raise ValueError(f"hardware_type id {type_id} not found")
        return row["code"]

    @staticmethod
    def _normalize_mac(mac: Optional[str]) -> Optional[str]:
        if mac is None:
            return None
        return mac.replace("-", "").replace(":", "").upper()

    def _record_audit(
        self,
        *,
        item_id: int,
        reason: str,
        note: Optional[str],
        changed_fields: Optional[Iterable[str]],
        snapshot_before: Optional[Dict[str, Any]] = None,
        snapshot_after: Optional[Dict[str, Any]] = None,
    ) -> None:
        before_json = json.dumps(snapshot_before) if snapshot_before else None
        after_json = json.dumps(snapshot_after) if snapshot_after else None
        self._updates.record(
            item_id=item_id,
            reason=reason,
            note=note,
            changed_fields=changed_fields,
            snapshot_before_json=before_json,
            snapshot_after_json=after_json,
        )
