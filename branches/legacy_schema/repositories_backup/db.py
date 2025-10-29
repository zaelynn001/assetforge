# Rev 1.2.0 - Distro

"""SQLite helper utilities for AssetForge."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from src.utils.paths import DB_PATH, MIGRATIONS_DIR, ensure_runtime_dirs


def _configure_connection(conn: sqlite3.Connection) -> None:
    """Apply consistent PRAGMA settings to any SQLite connection."""
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA busy_timeout = 5000;")


class Database:
    """SQLite wrapper that handles migrations, WAL, and per-type tables."""

    def __init__(self, path: Path | str = DB_PATH) -> None:
        ensure_runtime_dirs()
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        _configure_connection(self.conn)
        self.type_manager = TypeTableManager(self.conn)

    def close(self) -> None:
        try:
            self.conn.close()
        except Exception:
            pass

    def cursor(self) -> sqlite3.Cursor:
        return self.conn.cursor()

    # -- migrations -----------------------------------------------------
    def run_migrations(self, migrations_dir: Path | str = MIGRATIONS_DIR) -> List[str]:
        """Apply any outstanding .sql migrations. Returns filenames that ran."""
        migrations_dir = Path(migrations_dir)
        migrations_dir.mkdir(parents=True, exist_ok=True)
        self._ensure_schema_table()

        applied = self._applied_migrations()
        applied_now: List[str] = []

        for script in sorted(migrations_dir.glob("*.sql")):
            if script.name in applied:
                continue
            sql = script.read_text(encoding="utf-8")
            with self.conn:
                previous_fk = self.conn.execute("PRAGMA foreign_keys").fetchone()[0]
                try:
                    self.conn.execute("PRAGMA foreign_keys = OFF")
                    self.conn.executescript(sql)
                    self.conn.execute(
                        "INSERT INTO schema_migrations(filename, applied_at_utc) VALUES (?, ?)",
                        (script.name, datetime.now(timezone.utc).isoformat()),
                    )
                finally:
                    self.conn.execute(f"PRAGMA foreign_keys = {1 if previous_fk else 0}")
            applied_now.append(script.name)

        self.type_manager.sync()
        return applied_now

    def _ensure_schema_table(self) -> None:
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                filename TEXT PRIMARY KEY,
                applied_at_utc TEXT NOT NULL
            )
            """
        )

    def _applied_migrations(self) -> set[str]:
        rows = self.conn.execute("SELECT filename FROM schema_migrations").fetchall()
        return {row[0] for row in rows}

    # -- context manager ------------------------------------------------
    def __enter__(self) -> "Database":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


TYPE_TABLE_BASE = """
CREATE TABLE IF NOT EXISTS {table} (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  model TEXT,
  type_id INTEGER NOT NULL REFERENCES hardware_types(id)
     ON DELETE CASCADE ON UPDATE CASCADE,
  mac_address TEXT,
  ip_address TEXT,
  location_id INTEGER REFERENCES locations(id) ON DELETE SET NULL,
  user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
  group_id INTEGER REFERENCES groups(id) ON DELETE SET NULL,
  sub_type_id INTEGER REFERENCES sub_types(id) ON DELETE SET NULL,
  notes TEXT,
  created_at_utc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
  updated_at_utc TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
  asset_tag TEXT NOT NULL UNIQUE,
  master_id INTEGER REFERENCES master_list(master_id) ON DELETE CASCADE
    DEFERRABLE INITIALLY DEFERRED
);
"""

TYPE_TABLE_AUX = """
CREATE UNIQUE INDEX IF NOT EXISTS ux_{table}_mac_lower ON {table} (lower(mac_address));
CREATE INDEX IF NOT EXISTS idx_{table}_location ON {table}(location_id);
CREATE INDEX IF NOT EXISTS idx_{table}_user ON {table}(user_id);
CREATE INDEX IF NOT EXISTS idx_{table}_group ON {table}(group_id);

CREATE TRIGGER IF NOT EXISTS trg_{table}_touch_updated
AFTER UPDATE ON {table}
FOR EACH ROW
BEGIN
  UPDATE {table}
     SET updated_at_utc = strftime('%Y-%m-%dT%H:%M:%SZ','now')
   WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS trg_{table}_asset_tag_after_insert
AFTER INSERT ON {table}
FOR EACH ROW
BEGIN
  UPDATE {table}
     SET asset_tag = 'SDMM-' ||
                     (SELECT code FROM hardware_types WHERE id = NEW.type_id) ||
                     '-' || printf('%04d', NEW.id)
   WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS trg_{table}_asset_tag_after_type_change
AFTER UPDATE OF type_id ON {table}
FOR EACH ROW
BEGIN
  UPDATE {table}
     SET asset_tag = 'SDMM-' ||
                     (SELECT code FROM hardware_types WHERE id = NEW.type_id) ||
                     '-' || printf('%04d', NEW.id)
   WHERE id = NEW.id;
END;
"""

TYPE_TABLE_MAP: Dict[int, str] = {
    1: "laptops_pcs",
    2: "network_gear",
    3: "landline_phones",
    4: "printers",
    5: "payment_terminals",
    6: "lorex_cameras",
    7: "eufy_cameras",
    8: "peripheral_devices",
    9: "access_points",
    10: "misc",
}


class TypeTableManager:
    """Keeps per-type tables aligned with master_list records."""

    MASTER_COLUMNS: Tuple[str, ...] = (
        "master_id",
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

    PER_TYPE_COLUMNS: Tuple[str, ...] = (
        "id",
        "master_id",
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
    )

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    # ---- lifecycle ---------------------------------------------------
    def sync(self) -> None:
        for type_id in self.available_type_ids():
            table = self.ensure_table(type_id)
            columns = ", ".join(self.PER_TYPE_COLUMNS)
            cur = self._conn.execute(f"SELECT {columns} FROM {table}")
            for row in cur.fetchall():
                if row["master_id"] is not None:
                    self.sync_master_from_row(row)

    # ---- table discovery ---------------------------------------------
    def available_type_ids(self) -> List[int]:
        rows = self._conn.execute("SELECT id FROM hardware_types ORDER BY id").fetchall()
        return [int(row["id"]) for row in rows if int(row["id"]) in TYPE_TABLE_MAP]

    def table_name(self, type_id: int) -> str:
        try:
            return TYPE_TABLE_MAP[int(type_id)]
        except KeyError as exc:
            raise ValueError(f"Unknown hardware type id {type_id}") from exc

    def ensure_table(self, type_id: int) -> str:
        table = self.table_name(type_id)
        legacy = f"hardware_items_type_{type_id}"
        if not self._table_exists(table) and self._table_exists(legacy):
            self._conn.execute(f"ALTER TABLE {legacy} RENAME TO {table}")
        self._conn.executescript(TYPE_TABLE_BASE.format(table=table))
        self._conn.executescript(TYPE_TABLE_AUX.format(table=table))
        self._assert_master_column(table)
        return table

    def _assert_master_column(self, table: str) -> None:
        info = self._conn.execute(f"PRAGMA table_info({table})").fetchall()
        if not any(row["name"] == "master_id" for row in info):
            raise RuntimeError(
                f"{table} is missing required master_id column. Apply the schema migrations before running the app."
            )
        fk_rows = self._conn.execute(f"PRAGMA foreign_key_list({table})").fetchall()
        for fk in fk_rows:
            if fk["table"] == "master_list" and fk["to"] != "master_id":
                self._rebuild_table_with_master_fk(table)
                break

    def _table_exists(self, name: str) -> bool:
        cur = self._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
            (name,),
        )
        return cur.fetchone() is not None

    # ---- item index helpers -----------------------------------------
    def index_item(self, *, item_id: int, type_id: int) -> None:
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO item_index(id, type_id)
                VALUES (?, ?)
                ON CONFLICT(id) DO UPDATE SET type_id = excluded.type_id
                """,
                (item_id, type_id),
            )

    def delete_item_entry(self, item_id: int) -> None:
        with self._conn:
            self._conn.execute("DELETE FROM item_index WHERE id = ?", (item_id,))

    def get_item_type(self, item_id: int) -> Optional[int]:
        cur = self._conn.execute("SELECT type_id FROM item_index WHERE id = ?", (item_id,))
        row = cur.fetchone()
        return int(row["type_id"]) if row else None

    def update_item_type(self, item_id: int, new_type_id: int) -> None:
        with self._conn:
            self._conn.execute(
                "UPDATE item_index SET type_id = ? WHERE id = ?",
                (new_type_id, item_id),
            )

    # ---- data helpers ------------------------------------------------
    def fetch_item_row(self, type_id: int, per_type_id: int) -> Optional[sqlite3.Row]:
        table = self.ensure_table(type_id)
        columns = ", ".join(self.PER_TYPE_COLUMNS)
        cur = self._conn.execute(
            f"""
            SELECT {columns}
            FROM {table}
            WHERE id = ?
            """,
            (per_type_id,),
        )
        return cur.fetchone()

    def fetch_item_row_by_master(self, type_id: int, master_id: int) -> Optional[sqlite3.Row]:
        table = self.ensure_table(type_id)
        columns = ", ".join(self.PER_TYPE_COLUMNS)
        cur = self._conn.execute(
            f"""
            SELECT {columns}
            FROM {table}
            WHERE master_id = ?
            """,
            (master_id,),
        )
        return cur.fetchone()

    def insert_master_record(
        self,
        *,
        name: str,
        model: Optional[str],
        type_id: int,
        mac_address: Optional[str],
        ip_address: Optional[str],
        location_id: Optional[int],
        user_id: Optional[int],
        group_id: Optional[int],
        sub_type_id: Optional[int],
        notes: Optional[str],
        asset_tag: str,
        created_at_utc: Optional[str] = None,
        updated_at_utc: Optional[str] = None,
        archived: int = 0,
    ) -> int:
        now = datetime.now(timezone.utc).isoformat()
        created = created_at_utc or now
        updated = updated_at_utc or now
        with self._conn:
            cur = self._conn.execute(
                """
                INSERT INTO master_list(
                    name,
                    model,
                    type_id,
                    mac_address,
                    ip_address,
                    location_id,
                    user_id,
                    group_id,
                    sub_type_id,
                    notes,
                    asset_tag,
                    created_at_utc,
                    updated_at_utc,
                    archived
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    name,
                    model,
                    type_id,
                    mac_address,
                    ip_address,
                    location_id,
                    user_id,
                    group_id,
                    sub_type_id,
                    notes,
                    asset_tag,
                    created,
                    updated,
                    archived,
                ),
            )
        return int(cur.lastrowid)

    def sync_master_from_row(self, row: sqlite3.Row) -> None:
        master_id = row["master_id"]
        if master_id is None:
            return

        existing = self._conn.execute(
            "SELECT archived FROM master_list WHERE master_id = ?",
            (master_id,),
        ).fetchone()
        archived = int(existing["archived"]) if existing else 0

        values = [
            master_id,
            row["name"],
            row["model"],
            row["type_id"],
            row["mac_address"],
            row["ip_address"],
            row["location_id"],
            row["user_id"],
            row["group_id"],
            row["sub_type_id"],
            row["notes"],
            row["asset_tag"],
            row["created_at_utc"],
            row["updated_at_utc"],
            archived,
        ]
        columns = ", ".join(self.MASTER_COLUMNS)
        placeholders = ", ".join("?" for _ in self.MASTER_COLUMNS)
        update_clause = ", ".join(
            f"{col} = excluded.{col}"
            for col in self.MASTER_COLUMNS
            if col != "master_id"
        )
        self._conn.execute(
            f"""
            INSERT INTO master_list({columns})
            VALUES ({placeholders})
            ON CONFLICT(master_id) DO UPDATE SET {update_clause}
            """,
            values,
        )

    def delete_master_row(self, master_id: int) -> None:
        with self._conn:
            self._conn.execute("DELETE FROM master_list WHERE master_id = ?", (master_id,))

    def fetch_master_row(self, master_id: int) -> Optional[sqlite3.Row]:
        cur = self._conn.execute(
            "SELECT * FROM master_list WHERE master_id = ?",
            (master_id,),
        )
        return cur.fetchone()

    def _rebuild_table_with_master_fk(self, table: str) -> None:
        temp_table = f"{table}_tmp_rebuild"
        columns = (
            "id, name, model, type_id, mac_address, ip_address, "
            "location_id, user_id, group_id, sub_type_id, notes, "
            "created_at_utc, updated_at_utc, asset_tag, master_id"
        )
        self._conn.execute("PRAGMA defer_foreign_keys = ON")
        try:
            self._conn.executescript(TYPE_TABLE_BASE.format(table=temp_table))
            with self._conn:
                self._conn.execute(
                    f"INSERT INTO {temp_table}({columns}) SELECT {columns} FROM {table}"
                )
                self._conn.execute(f"DROP TABLE {table}")
                self._conn.execute(f"ALTER TABLE {temp_table} RENAME TO {table}")
            self._conn.executescript(TYPE_TABLE_AUX.format(table=table))
            rows = self._conn.execute(
                f"SELECT {columns} FROM {table}"
            ).fetchall()
            for row in rows:
                self.sync_master_from_row(row)
        finally:
            self._conn.execute("PRAGMA defer_foreign_keys = OFF")
