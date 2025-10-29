# Rev 1.2.0 - Distro

"""SQLite repository for inventory items using the unified items table."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

from src.models.item_record import ItemRecord

from .db import Database
from .sqlite_updates_repo import SQLiteUpdatesRepository

_UNSET = object()


class SQLiteItemsRepository:
    """CRUD operations plus audit recording for inventory items."""

    _AUDIT_FIELDS = (
        "name",
        "model",
        "type_id",
        "mac_address",
        "ip_address",
        "location_id",
        "user_id",
        "group_id",
        "sub_type_id",
        "notes",
        "extension",
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
        self._updates = updates_repo or SQLiteUpdatesRepository(database)
        self._landline_type_id_cache: Optional[int] = None

    # ---- queries -----------------------------------------------------
    def list_records(
        self,
        *,
        order_by: str = "i.updated_at_utc DESC",
        type_ids: Optional[Iterable[int]] = None,
        location_ids: Optional[Iterable[int]] = None,
        user_ids: Optional[Iterable[int]] = None,
        group_ids: Optional[Iterable[int]] = None,
        search: Optional[str] = None,
        limit: int = 500,
    ) -> List[ItemRecord]:
        type_filter = self._normalize_ids(type_ids)
        location_filter = self._normalize_ids(location_ids)
        user_filter = self._normalize_ids(user_ids)
        group_filter = self._normalize_ids(group_ids)

        where: List[str] = ["i.archived = 0"]
        params: List[Any] = []

        if type_filter:
            placeholders = ", ".join("?" for _ in type_filter)
            where.append(f"i.type_id IN ({placeholders})")
            params.extend(type_filter)
        if location_filter:
            placeholders = ", ".join("?" for _ in location_filter)
            where.append(f"i.location_id IN ({placeholders})")
            params.extend(location_filter)
        if user_filter:
            placeholders = ", ".join("?" for _ in user_filter)
            where.append(f"i.user_id IN ({placeholders})")
            params.extend(user_filter)
        if group_filter:
            placeholders = ", ".join("?" for _ in group_filter)
            where.append(f"i.group_id IN ({placeholders})")
            params.extend(group_filter)

        if search:
            like = f"%{search.lower()}%"
            where.append(
                """
                (
                    lower(i.name) LIKE ?
                    OR lower(COALESCE(i.model, '')) LIKE ?
                    OR lower(COALESCE(i.mac_address, '')) LIKE ?
                    OR lower(i.asset_tag) LIKE ?
                )
                """
            )
            params.extend([like, like, like, like])

        clause = "WHERE " + " AND ".join(where) if where else ""

        column, descending = self._parse_order(order_by)
        direction = "DESC" if descending else "ASC"

        sql = f"""
            SELECT
                i.id,
                i.type_serial,
                i.name,
                i.model,
                i.type_id,
                i.mac_address,
                i.ip_address,
                i.location_id,
                i.user_id,
                i.group_id,
                i.sub_type_id,
                i.notes,
                i.extension,
                i.asset_tag,
                i.created_at_utc,
                i.updated_at_utc,
                i.archived
            FROM items AS i
            {clause}
            ORDER BY {column} {direction}
            LIMIT ?
        """
        params.append(limit)

        metadata = self._metadata_maps()
        return [
            ItemRecord.from_row(row, metadata)
            for row in self._conn.execute(sql, params).fetchall()
        ]

    def list_items(
        self,
        *,
        order_by: str = "i.updated_at_utc DESC",
        type_ids: Optional[Iterable[int]] = None,
        location_ids: Optional[Iterable[int]] = None,
        user_ids: Optional[Iterable[int]] = None,
        group_ids: Optional[Iterable[int]] = None,
        search: Optional[str] = None,
        limit: int = 500,
    ) -> List[Dict[str, Any]]:
        return [
            record.as_dict()
            for record in self.list_records(
                order_by=order_by,
                type_ids=type_ids,
                location_ids=location_ids,
                user_ids=user_ids,
                group_ids=group_ids,
                search=search,
                limit=limit,
            )
        ]

    def get(self, item_id: int) -> Optional[Dict[str, Any]]:
        record = self._get_record(item_id)
        return record.as_dict() if record else None

    def get_details(self, item_id: int) -> Optional[Dict[str, Any]]:
        return self.get(item_id)

    # ---- mutations ---------------------------------------------------
    def create(
        self,
        *,
        name: str,
        type_id: int,
        model: Optional[str] = None,
        mac_address: Optional[str] = None,
        ip_address: object = _UNSET,
        location_id: Optional[int] = None,
        user_id: Optional[int] = None,
        group_id: Optional[int] = None,
        sub_type_id: Optional[int] = None,
        notes: Optional[str] = None,
        extension: Optional[str] = None,
        note: Optional[str] = None,
    ) -> Dict[str, Any]:
        if ip_address is _UNSET:
            ip_address = None
        mac_norm = self._normalize_mac(mac_address)
        ip_norm = self._normalize_ip(ip_address)
        self._ensure_ip_available(ip_norm)
        self._assert_ip_exists(ip_norm)

        extension_clean = self._clean_extension(type_id, extension)

        with self._conn:
            type_serial = self._next_type_serial(type_id)
            asset_tag = self._asset_tag_for(type_id=type_id, type_serial=type_serial)
            cur = self._conn.execute(
                """
                INSERT INTO items(
                    type_serial, name, model, type_id, mac_address,
                    ip_address, location_id, user_id, group_id,
                    sub_type_id, notes, extension, asset_tag
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    type_serial,
                    name,
                    model,
                    type_id,
                    mac_norm,
                    ip_norm,
                    location_id,
                    user_id,
                    group_id,
                    sub_type_id,
                    notes,
                    extension_clean,
                    asset_tag,
                ),
            )
            item_id = int(cur.lastrowid)

        record = self._get_record(item_id)
        item = record.as_dict() if record else {}
        self._record_audit(
            item_id=item_id,
            type_id=type_id,
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
        ip_address: Optional[str] = _UNSET,
        location_id: Optional[int] = None,
        user_id: Optional[int] = None,
        group_id: Optional[int] = None,
        sub_type_id: Optional[int] = None,
        notes: Optional[str] = None,
        extension: Optional[str] = _UNSET,
        note: Optional[str] = None,
        reason: str = "update",
    ) -> bool:
        before_record = self._get_record(item_id)
        if not before_record:
            raise ValueError(f"Item {item_id} not found")
        before = before_record.as_dict()

        fields: Dict[str, Any] = {}
        if name is not None:
            fields["name"] = name
        if model is not None:
            fields["model"] = model
        if type_id is not None:
            fields["type_id"] = int(type_id)
        if mac_address is not None:
            fields["mac_address"] = self._normalize_mac(mac_address)
        if ip_address is not _UNSET:
            fields["ip_address"] = self._normalize_ip(ip_address)
        if location_id is not None:
            fields["location_id"] = location_id
        if user_id is not None:
            fields["user_id"] = user_id
        if group_id is not None:
            fields["group_id"] = group_id
        if sub_type_id is not None:
            fields["sub_type_id"] = sub_type_id
        if notes is not None:
            fields["notes"] = notes

        if not fields and note is None:
            return False

        if "ip_address" in fields:
            self._ensure_ip_available(
                fields["ip_address"],
                exclude_item=item_id,
            )
            self._assert_ip_exists(fields["ip_address"])

        type_changed = "type_id" in fields and fields["type_id"] != before["type_id"]
        new_type_id = fields["type_id"] if type_changed else before["type_id"]

        if extension is not _UNSET:
            fields["extension"] = self._clean_extension(new_type_id, extension)
        elif type_changed and new_type_id != self._landline_type_id():
            fields["extension"] = None

        with self._conn:
            updates: List[str] = []
            params: List[Any] = []

            if type_changed:
                new_type_serial = self._next_type_serial(new_type_id)
                fields["type_serial"] = new_type_serial

            for column, value in fields.items():
                updates.append(f"{column} = ?")
                params.append(value)

            if updates:
                params.append(item_id)
                self._conn.execute(
                    f"UPDATE items SET {', '.join(updates)} WHERE id = ?",
                    params,
                )
                if type_changed:
                    asset_tag = self._asset_tag_for(
                        type_id=new_type_id,
                        type_serial=new_type_serial,
                    )
                    self._conn.execute(
                        "UPDATE items SET asset_tag = ? WHERE id = ?",
                        (asset_tag, item_id),
                    )

        after_record = self._get_record(item_id)
        after = after_record.as_dict() if after_record else None
        changed_columns = [
            column
            for column in self._AUDIT_FIELDS
            if before.get(column) != (after or {}).get(column)
        ]

        if changed_columns or note:
            self._record_audit(
                item_id=item_id,
                type_id=new_type_id,
                reason=reason,
                note=note,
                changed_fields=changed_columns or None,
                snapshot_before=before,
                snapshot_after=after,
            )
        return bool(changed_columns)

    def delete(self, item_id: int, *, note: Optional[str] = None) -> bool:
        before_record = self._get_record(item_id)
        if not before_record:
            return False
        before = before_record.as_dict()

        now = datetime.now(timezone.utc).isoformat()
        archive_columns = (
            "id",
            "name",
            "model",
            "type_id",
            "mac_address",
            "ip_address",
            "location_id",
            "user_id",
            "group_id",
            "sub_type_id",
            "notes",
            "asset_tag",
            "created_at_utc",
            "updated_at_utc",
            "archived",
        )
        archive_values = [
            before.get("id"),
            before.get("name"),
            before.get("model"),
            before.get("type_id"),
            before.get("mac_address"),
            before.get("ip_address"),
            before.get("location_id"),
            before.get("user_id"),
            before.get("group_id"),
            before.get("sub_type_id"),
            before.get("notes"),
            before.get("asset_tag"),
            before.get("created_at_utc"),
            now,
            1,
        ]

        placeholders = ", ".join("?" for _ in archive_columns)
        update_clause = ", ".join(
            f"{column} = excluded.{column}" for column in archive_columns if column != "asset_tag"
        )

        with self._conn:
            self._conn.execute(
                f"""
                INSERT INTO archive({', '.join(archive_columns)})
                VALUES ({placeholders})
                ON CONFLICT(asset_tag) DO UPDATE SET {update_clause}
                """,
                archive_values,
            )
            self._conn.execute("DELETE FROM items WHERE id = ?", (item_id,))

        self._record_audit(
            item_id=item_id,
            type_id=before["type_id"],
            reason="delete",
            note=note,
            changed_fields=["archived"],
            snapshot_before=before,
            snapshot_after=None,
        )
        return True

    def assign(
        self,
        item_id: int,
        *,
        user_id: Optional[int] = None,
        group_id: Optional[int] = None,
        note: Optional[str] = None,
    ) -> bool:
        before_record = self._get_record(item_id)
        if not before_record:
            raise ValueError(f"Item {item_id} not found")
        before = before_record.as_dict()

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
        before_record = self._get_record(item_id)
        if not before_record:
            raise ValueError(f"Item {item_id} not found")
        before = before_record.as_dict()

        if before.get("location_id") == location_id:
            return False

        self.update(item_id, location_id=location_id, reason="move", note=note)
        return True

    def add_audit_note(self, item_id: int, note: str) -> int:
        if self._get_record(item_id) is None:
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
        before_record = self._get_record(item_id)
        if not before_record:
            raise ValueError(f"Item {item_id} not found")
        before = before_record.as_dict()
        if before.get("archived"):
            return False

        now = datetime.now(timezone.utc).isoformat()
        with self._conn:
            self._conn.execute(
                """
                UPDATE items
                   SET archived = 1,
                       ip_address = NULL,
                       updated_at_utc = ?
                 WHERE id = ?
                """,
                (now, item_id),
            )
        after_record = self._get_record(item_id)
        after = after_record.as_dict() if after_record else None
        self._record_audit(
            item_id=item_id,
            type_id=before["type_id"],
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
        sub_types = {
            int(row["id"]): {"name": row["name"]}
            for row in self._conn.execute("SELECT id, name FROM sub_types")
        }
        return {
            "types": types,
            "locations": locations,
            "users": users,
            "groups": groups,
            "sub_types": sub_types,
        }

    def _parse_order(self, order_by: str) -> tuple[str, bool]:
        clause = (order_by or "").strip() or "updated_at_utc DESC"
        parts = clause.split()
        column = parts[0]
        if "." in column:
            column = column.split(".")[-1]
        direction = parts[1].upper() if len(parts) > 1 else "ASC"
        descending = direction == "DESC"
        return column, descending

    def _normalize_ids(self, ids: Optional[Iterable[int]]) -> List[int]:
        if not ids:
            return []
        return sorted({int(i) for i in ids if i is not None})

    @staticmethod
    def _normalize_mac(mac: Optional[str]) -> Optional[str]:
        if mac is None:
            return None
        return mac.replace("-", "").replace(":", "").upper()

    @staticmethod
    def _normalize_ip(ip: object) -> Optional[str]:
        if ip is _UNSET or ip is None:
            return None
        value = str(ip).strip()
        return value or None

    def _ensure_ip_available(self, ip: Optional[str], *, exclude_item: Optional[int] = None) -> None:
        if not ip:
            return
        query = "SELECT id, asset_tag FROM items WHERE ip_address = ?"
        params: List[Any] = [ip]
        if exclude_item is not None:
            query += " AND id != ?"
            params.append(int(exclude_item))
        row = self._conn.execute(query, params).fetchone()
        if row:
            raise ValueError(
                f"IP address {ip} is already assigned to asset {row['asset_tag']}"
            )

    def _assert_ip_exists(self, ip: Optional[str]) -> None:
        if not ip:
            return
        exists = self._conn.execute(
            "SELECT 1 FROM ip_addresses WHERE ip_address = ?",
            (ip,),
        ).fetchone()
        if exists is None:
            raise ValueError(f"IP address {ip} does not exist in ip_addresses table")

    def _asset_tag_for(self, *, type_id: int, type_serial: int) -> str:
        code = self._conn.execute(
            "SELECT code FROM hardware_types WHERE id = ?",
            (type_id,),
        ).fetchone()
        if code is None:
            raise ValueError(f"hardware_type id {type_id} not found")
        return f"SDMM-{code['code']}-{type_serial:04d}"

    def _next_type_serial(self, type_id: int) -> int:
        row = self._conn.execute(
            "SELECT next_serial FROM type_counters WHERE type_id = ?",
            (type_id,),
        ).fetchone()
        if row is None:
            next_serial = 1
            self._conn.execute(
                "INSERT INTO type_counters(type_id, next_serial) VALUES (?, ?)",
                (type_id, 2),
            )
            return next_serial

        next_serial = int(row["next_serial"])
        self._conn.execute(
            "UPDATE type_counters SET next_serial = ? WHERE type_id = ?",
            (next_serial + 1, type_id),
        )
        return next_serial

    def _landline_type_id(self) -> Optional[int]:
        if self._landline_type_id_cache is None:
            row = self._conn.execute(
                "SELECT id FROM hardware_types WHERE code = ?",
                ("TP",),
            ).fetchone()
            self._landline_type_id_cache = int(row["id"]) if row else -1
        return self._landline_type_id_cache if self._landline_type_id_cache > 0 else None

    def _clean_extension(self, type_id: int, extension: Optional[str]) -> Optional[str]:
        value = (extension or "").strip()
        if not value:
            value = None
        landline_id = self._landline_type_id()
        if landline_id is None or type_id != landline_id:
            return None
        return value

    def _record_audit(
        self,
        *,
        item_id: int,
        type_id: int,
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

    def _get_record(self, item_id: int) -> Optional[ItemRecord]:
        row = self._conn.execute(
            """
            SELECT
                i.id,
                i.type_serial,
                i.name,
                i.model,
                i.type_id,
                i.mac_address,
                i.ip_address,
                i.location_id,
                i.user_id,
                i.group_id,
                i.sub_type_id,
                i.notes,
                i.extension,
                i.asset_tag,
                i.created_at_utc,
                i.updated_at_utc,
                i.archived
            FROM items AS i
            WHERE i.id = ?
            """,
            (item_id,),
        ).fetchone()
        if row is None:
            return None
        return ItemRecord.from_row(row, self._metadata_maps())
