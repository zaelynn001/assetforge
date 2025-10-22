# Rev 1.0.0

"""SQLite repository for inventory items stored in per-type tables."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

import sqlite3

from .db import Database, TypeTableManager
from .sqlite_updates_repo import SQLiteUpdatesRepository


class SQLiteItemsRepository:
    """CRUD operations plus audit recording for hardware items across type tables."""

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
        database: Database,
        *,
        updates_repo: SQLiteUpdatesRepository | None = None,
    ) -> None:
        if not isinstance(database, Database):
            raise RuntimeError("SQLiteItemsRepository expects a Database instance.")

        self._db = database
        self._conn = database.conn
        self._type_manager: TypeTableManager = database.type_manager
        self._updates = updates_repo or SQLiteUpdatesRepository(database)

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
        type_filter = self._normalize_ids(type_ids)
        candidate_types = type_filter or self._type_manager.available_type_ids()
        if not candidate_types:
            return []

        column, descending = self._parse_order(order_by)
        where_clause, base_params = self._build_filters(
            location_ids=location_ids,
            user_ids=user_ids,
            group_ids=group_ids,
            search=search,
        )
        metadata = self._metadata_maps()

        results: List[Dict[str, Any]] = []
        for type_id in candidate_types:
            table = self._type_manager.ensure_table(type_id)
            params = list(base_params)
            params.append(limit)
            cur = self._conn.execute(
                f"""
                SELECT
                    hi.id,
                    hi.master_id,
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
                    COALESCE(ml.archived, 0) AS archived
                FROM {table} AS hi
                LEFT JOIN master_list AS ml
                  ON hi.master_id = ml.master_id
                {where_clause}
                LIMIT ?
                """,
                params,
            )
            for row in cur.fetchall():
                item = dict(row)
                self._augment_item_display(item, metadata)
                results.append(item)

        if not results:
            return []

        results.sort(
            key=lambda row: self._sort_value(row, column),
            reverse=descending,
        )
        return results[:limit]

    def get(self, item_id: int) -> Optional[Dict[str, Any]]:
        type_id = self._type_manager.get_item_type(item_id)
        if type_id is None:
            return None
        table = self._type_manager.ensure_table(type_id)
        cur = self._conn.execute(
            f"""
            SELECT
                hi.id,
                hi.master_id,
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
                COALESCE(ml.archived, 0) AS archived
            FROM {table} AS hi
            LEFT JOIN master_list AS ml
              ON hi.master_id = ml.master_id
            WHERE hi.id = ?
            """,
            (item_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None

    def get_details(self, item_id: int) -> Optional[Dict[str, Any]]:
        item = self.get(item_id)
        if not item:
            return None
        metadata = self._metadata_maps()
        self._augment_item_display(item, metadata)
        return item

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
        note: Optional[str] = None,
    ) -> Dict[str, Any]:
        mac_norm = self._normalize_mac(mac_address)
        type_code = self._type_code(type_id)
        placeholder_tag = f"SDMM-{type_code}-0000"

        table = self._type_manager.ensure_table(type_id)

        with self._conn:
            cur = self._conn.execute(
                f"""
                INSERT INTO {table}(
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
            item_id = int(cur.lastrowid)

        master_id: Optional[int] = None
        try:
            per_type_row = self._type_manager.fetch_item_row(type_id, item_id)
            if per_type_row is None:
                raise RuntimeError("Failed to load newly created item")

            master_id = self._type_manager.insert_master_record(
                name=per_type_row["name"],
                model=per_type_row["model"],
                type_id=type_id,
                mac_address=per_type_row["mac_address"],
                location_id=per_type_row["location_id"],
                user_id=per_type_row["user_id"],
                group_id=per_type_row["group_id"],
                notes=per_type_row["notes"],
                asset_tag=per_type_row["asset_tag"],
                created_at_utc=per_type_row["created_at_utc"],
                updated_at_utc=per_type_row["updated_at_utc"],
            )

            with self._conn:
                self._conn.execute(
                    f"UPDATE {table} SET master_id = ? WHERE id = ?",
                    (master_id, item_id),
                )

            self._type_manager.index_item(item_id=item_id, type_id=type_id)

            updated_row = self._type_manager.fetch_item_row(type_id, item_id)
            if updated_row is not None:
                self._type_manager.sync_master_from_row(updated_row)
        except Exception:
            with self._conn:
                self._conn.execute(f"DELETE FROM {table} WHERE id = ?", (item_id,))
            if master_id is not None:
                self._type_manager.delete_master_row(master_id)
            self._type_manager.delete_item_entry(item_id)
            raise

        item = self.get(item_id)
        self._record_audit(
            type_id=type_id,
            item_id=item_id,
            reason="create",
            note=note,
            changed_fields=self._AUDIT_FIELDS,
            snapshot_after=item,
        )
        return item or {}

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
        current_type_id = self._type_manager.get_item_type(item_id)
        if current_type_id is None:
            raise ValueError(f"Item {item_id} not found")

        fields = {
            "name": name,
            "model": model,
            "type_id": type_id,
            "mac_address": self._normalize_mac(mac_address)
            if mac_address is not None
            else None,
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

        target_type_id = int(type_id) if type_id is not None else current_type_id
        changed_columns: List[str] = []

        if target_type_id != current_type_id:
            merged = dict(before)
            for column, value in fields.items():
                if column == "type_id":
                    continue
                merged[column] = value
            merged["type_id"] = target_type_id
            self._relocate_item(
                item_id=item_id,
                source_type_id=current_type_id,
                dest_type_id=target_type_id,
                merged_row=merged,
            )
            after = self.get(item_id)
            changed_columns = [
                column
                for column in self._AUDIT_FIELDS
                if (before.get(column) != (after or {}).get(column))
            ]
            if changed_columns or note:
                self._record_audit(
                    type_id=target_type_id,
                    item_id=item_id,
                    reason=reason,
                    note=note,
                    changed_fields=changed_columns or None,
                    snapshot_before=before,
                    snapshot_after=after,
                )
            return bool(changed_columns)

        table = self._type_manager.ensure_table(current_type_id)

        sets: List[str] = []
        params: List[Any] = []
        for column, value in fields.items():
            if column == "type_id":
                continue
            sets.append(f"{column} = ?")
            params.append(value)

        if sets:
            params.append(item_id)
            with self._conn:
                cur = self._conn.execute(
                    f"UPDATE {table} SET {', '.join(sets)} WHERE id = ?",
                    params,
                )
                if cur.rowcount == 0:
                    return False
                self._sync_global_row(current_type_id, item_id)

        after = self.get(item_id)
        if sets:
            changed_columns = [
                column
                for column in fields
                if column != "type_id"
                and before.get(column) != (after or {}).get(column)
            ]

        if changed_columns or note:
            self._record_audit(
                type_id=current_type_id,
                item_id=item_id,
                reason=reason,
                note=note,
                changed_fields=changed_columns or None,
                snapshot_before=before,
                snapshot_after=after,
            )
        return bool(changed_columns)

    def delete(self, item_id: int, *, note: Optional[str] = None) -> bool:
        type_id = self._type_manager.get_item_type(item_id)
        if type_id is None:
            return False

        before = self.get(item_id)
        if not before:
            return False

        table = self._type_manager.ensure_table(type_id)
        master_id = before.get("master_id")
        with self._conn:
            self._conn.execute(f"DELETE FROM {table} WHERE id = ?", (item_id,))
            self._conn.execute("DELETE FROM item_updates WHERE item_id = ?", (item_id,))
        self._type_manager.delete_item_entry(item_id)
        if master_id is not None:
            self._type_manager.delete_master_row(int(master_id))

        self._record_audit(
            type_id=type_id,
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

    def add_audit_note(self, item_id: int, note: str) -> int:
        type_id = self._type_manager.get_item_type(item_id)
        if type_id is None:
            raise ValueError(f"Item {item_id} not found")
        return self._updates.record(
            item_id=item_id,
            reason="audit",
            note=note,
            changed_fields=None,
            snapshot_before_json=None,
            snapshot_after_json=None,
        )

    def history_for_item(self, item_id: int, *, limit: int = 50) -> List[Dict[str, Any]]:
        return self._updates.list_for_item(item_id, limit=limit)

    def archive(self, item_id: int, *, note: Optional[str] = None) -> bool:
        item = self.get(item_id)
        if not item:
            raise ValueError(f"Item {item_id} not found")
        master_id = item.get("master_id")
        if master_id is None:
            raise ValueError("Item missing master reference")

        before = item
        now = datetime.now(timezone.utc).isoformat()
        with self._conn:
            self._conn.execute(
                "UPDATE master_list SET archived = 1, updated_at_utc = ? WHERE master_id = ?",
                (now, master_id),
            )
        after = self.get(item_id)
        self._record_audit(
            type_id=item["type_id"],
            item_id=item_id,
            reason="archive",
            note=note,
            changed_fields=["archived"],
            snapshot_before=before,
            snapshot_after=after,
        )
        return True

    # ---- internal helpers -------------------------------------------
    def _metadata_maps(self) -> Dict[str, Dict[int, Dict[str, Any]]]:
        types = {
            int(row["id"]): {"name": row["name"], "code": row["code"]}
            for row in self._conn.execute("SELECT id, name, code FROM hardware_types")
        }
        locations = {
            int(row["id"]): {"name": row["name"]}
            for row in self._conn.execute("SELECT id, name FROM locations")
        }
        users = {
            int(row["id"]): {"name": row["name"], "email": row["email"]}
            for row in self._conn.execute("SELECT id, name, email FROM users")
        }
        groups = {
            int(row["id"]): {"name": row["name"]}
            for row in self._conn.execute("SELECT id, name FROM groups")
        }
        return {
            "types": types,
            "locations": locations,
            "users": users,
            "groups": groups,
        }

    def _augment_item_display(
        self,
        item: Dict[str, Any],
        metadata: Dict[str, Dict[int, Dict[str, Any]]],
    ) -> None:
        type_meta = metadata["types"].get(int(item["type_id"]))
        if type_meta:
            item["type_name"] = type_meta["name"]
            item["type_code"] = type_meta["code"]
        else:
            item["type_name"] = None
            item["type_code"] = None

        location_id = item.get("location_id")
        loc_meta = metadata["locations"].get(int(location_id)) if location_id is not None else None
        item["location_name"] = loc_meta["name"] if loc_meta else None

        user_id = item.get("user_id")
        user_meta = metadata["users"].get(int(user_id)) if user_id is not None else None
        if user_meta:
            item["user_name"] = user_meta["name"]
            item["user_email"] = user_meta["email"]
        else:
            item["user_name"] = None
            item["user_email"] = None

        group_id = item.get("group_id")
        group_meta = metadata["groups"].get(int(group_id)) if group_id is not None else None
        item["group_name"] = group_meta["name"] if group_meta else None

    def _parse_order(self, order_by: str) -> Tuple[str, bool]:
        clause = (order_by or "").strip() or "updated_at_utc DESC"
        parts = clause.split()
        column = parts[0]
        if "." in column:
            column = column.split(".")[-1]
        direction = parts[1].upper() if len(parts) > 1 else "ASC"
        descending = direction == "DESC"
        return column, descending

    def _sort_value(self, row: Dict[str, Any], column: str) -> Any:
        value = row.get(column)
        if value is None:
            return ""
        if isinstance(value, str):
            return value.lower()
        return value

    def _build_filters(
        self,
        *,
        location_ids: Optional[Iterable[int]],
        user_ids: Optional[Iterable[int]],
        group_ids: Optional[Iterable[int]],
        search: Optional[str],
    ) -> Tuple[str, List[Any]]:
        where: List[str] = []
        params: List[Any] = []

        def _apply_in(column: str, values: List[int]) -> None:
            if not values:
                return
            placeholders = ", ".join("?" for _ in values)
            where.append(f"{column} IN ({placeholders})")
            params.extend(values)

        _apply_in("hi.location_id", self._normalize_ids(location_ids))
        _apply_in("hi.user_id", self._normalize_ids(user_ids))
        _apply_in("hi.group_id", self._normalize_ids(group_ids))

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

        clause = "WHERE " + " AND ".join(where) if where else ""
        return clause, params

    @staticmethod
    def _normalize_ids(ids: Optional[Iterable[int]]) -> List[int]:
        if not ids:
            return []
        normalized = {int(i) for i in ids if i is not None}
        return sorted(normalized)

    def _type_code(self, type_id: int) -> str:
        cur = self._conn.execute(
            "SELECT code FROM hardware_types WHERE id = ?",
            (type_id,),
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

    def _relocate_item(
        self,
        *,
        item_id: int,
        source_type_id: int,
        dest_type_id: int,
        merged_row: Dict[str, Any],
    ) -> None:
        source_table = self._type_manager.ensure_table(source_type_id)
        dest_table = self._type_manager.ensure_table(dest_type_id)
        placeholder_tag = f"SDMM-{self._type_code(dest_type_id)}-0000"
        master_id = merged_row.get("master_id")

        with self._conn:
            self._conn.execute(
                f"""
                INSERT INTO {dest_table}(
                    id, name, model, type_id, mac_address,
                    location_id, user_id, group_id, notes,
                    asset_tag, created_at_utc, updated_at_utc, master_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item_id,
                    merged_row.get("name"),
                    merged_row.get("model"),
                    dest_type_id,
                    merged_row.get("mac_address"),
                    merged_row.get("location_id"),
                    merged_row.get("user_id"),
                    merged_row.get("group_id"),
                    merged_row.get("notes"),
                    placeholder_tag,
                    merged_row.get("created_at_utc"),
                    merged_row.get("updated_at_utc"),
                    master_id,
                ),
            )
            self._conn.execute(
                f"DELETE FROM {source_table} WHERE id = ?",
                (item_id,),
            )
        self._type_manager.update_item_type(item_id, dest_type_id)
        row = self._type_manager.fetch_item_row(dest_type_id, item_id)
        if row:
            self._type_manager.sync_master_from_row(row)

    def _record_audit(
        self,
        *,
        type_id: int,
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

    def _sync_global_row(self, type_id: int, item_id: int) -> None:
        row = self._type_manager.fetch_item_row(type_id, item_id)
        if row:
            self._type_manager.sync_master_from_row(row)
