# Rev 1.2.0 - Distro

"""SQLite helper utilities for AssetForge."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from src.utils.paths import DB_PATH, MIGRATIONS_DIR, ensure_runtime_dirs


def _configure_connection(conn: sqlite3.Connection) -> None:
    """Apply consistent PRAGMA settings to any SQLite connection."""
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA busy_timeout = 5000;")


class Database:
    """Thin SQLite wrapper that handles migrations and connection lifecycle."""

    def __init__(self, path: Path | str = DB_PATH) -> None:
        ensure_runtime_dirs()
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        _configure_connection(self.conn)

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
