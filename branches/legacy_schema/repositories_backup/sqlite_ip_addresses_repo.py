# Rev 1.2.0 - Distro

"""SQLite repository for tracking unique IP address records."""
from __future__ import annotations

from typing import Dict, Optional

from .db import Database


class SQLiteIPAddressesRepository:
    def __init__(self, database: Database) -> None:
        if not isinstance(database, Database):
            raise RuntimeError("SQLiteIPAddressesRepository expects a Database instance.")
        self._db = database
        self._conn = database.conn

    def list_addresses(self, order_by: str = "ip_address") -> list[Dict[str, str]]:
        cur = self._conn.execute(
            f"SELECT id, ip_address FROM ip_addresses ORDER BY {order_by}"
        )
        return [dict(row) for row in cur.fetchall()]

    def list_available(self, *, include: Optional[str] = None) -> list[str]:
        rows = self._conn.execute("SELECT ip_address FROM ip_addresses").fetchall()
        all_ips = [row["ip_address"] for row in rows if row["ip_address"]]
        used = {
            row["ip_address"]
            for row in self._conn.execute(
                "SELECT ip_address FROM master_list WHERE ip_address IS NOT NULL AND archived = 0"
            )
        }
        if include:
            used.discard(include)
        available = [ip for ip in all_ips if ip not in used]
        if include and include not in available and include:
            available.append(include)

        def ip_key(value: str) -> tuple[int, ...]:
            try:
                return tuple(int(part) for part in value.split("."))
            except ValueError:
                return (value,)

        available.sort(key=ip_key)
        return available

    def find(self, ip_address: str) -> Optional[Dict[str, str]]:
        cur = self._conn.execute(
            "SELECT id, ip_address FROM ip_addresses WHERE ip_address = ?",
            (ip_address.strip(),),
        )
        row = cur.fetchone()
        return dict(row) if row else None

    def get(self, ip_id: int) -> Optional[Dict[str, str]]:
        cur = self._conn.execute(
            "SELECT id, ip_address FROM ip_addresses WHERE id = ?",
            (ip_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None

    def create(self, ip_address: str) -> Dict[str, str]:
        normalized = ip_address.strip()
        with self._conn:
            cur = self._conn.execute(
                "INSERT INTO ip_addresses(ip_address) VALUES (?)",
                (normalized,),
            )
        return {"id": int(cur.lastrowid), "ip_address": normalized}

    def update(self, ip_id: int, *, ip_address: str) -> Dict[str, str]:
        normalized = ip_address.strip()
        with self._conn:
            self._conn.execute(
                "UPDATE ip_addresses SET ip_address = ? WHERE id = ?",
                (normalized, ip_id),
            )
        record = self.get(ip_id)
        if record is None:
            raise ValueError(f"IP address {ip_id} not found")
        return record

    def delete(self, ip_id: int) -> bool:
        with self._conn:
            cur = self._conn.execute(
                "DELETE FROM ip_addresses WHERE id = ?",
                (ip_id,),
            )
        return cur.rowcount > 0

    def ensure(self, ip_address: str) -> Dict[str, str]:
        existing = self.find(ip_address)
        if existing:
            return existing
        return self.create(ip_address)
