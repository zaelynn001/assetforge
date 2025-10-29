# Rev 1.2.0 - Distro

"""Typed representation of inventory items used by the UI layer."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Mapping, Optional


@dataclass(frozen=True)
class ItemRecord:
    id: int
    type_serial: int
    name: str
    model: Optional[str]
    type_id: int
    type_name: Optional[str]
    type_code: Optional[str]
    mac_address: Optional[str]
    ip_address: Optional[str]
    location_id: Optional[int]
    location_name: Optional[str]
    user_id: Optional[int]
    user_name: Optional[str]
    user_email: Optional[str]
    group_id: Optional[int]
    group_name: Optional[str]
    sub_type_id: Optional[int]
    sub_type_name: Optional[str]
    notes: Optional[str]
    extension: Optional[str]
    asset_tag: Optional[str]
    created_at_utc: str
    updated_at_utc: str
    archived: bool

    @classmethod
    def from_row(cls, row: Mapping[str, Any], metadata: Mapping[str, Dict[int, Dict[str, Any]]]) -> "ItemRecord":
        type_id = int(row["type_id"])
        type_meta = metadata["types"].get(type_id, {})
        location_id = row["location_id"]
        loc_meta = metadata["locations"].get(int(location_id)) if location_id is not None else None
        user_id = row["user_id"]
        user_meta = metadata["users"].get(int(user_id)) if user_id is not None else None
        group_id = row["group_id"]
        group_meta = metadata["groups"].get(int(group_id)) if group_id is not None else None
        sub_type_id = row["sub_type_id"]
        sub_meta = metadata["sub_types"].get(int(sub_type_id)) if sub_type_id is not None else None

        return cls(
            id=int(row["id"]),
            type_serial=int(row["type_serial"]),
            name=row["name"],
            model=row["model"],
            type_id=type_id,
            type_name=type_meta.get("name"),
            type_code=type_meta.get("code"),
            mac_address=row["mac_address"],
            ip_address=row["ip_address"],
            location_id=int(location_id) if location_id is not None else None,
            location_name=loc_meta["name"] if loc_meta else None,
            user_id=int(user_id) if user_id is not None else None,
            user_name=user_meta["name"] if user_meta else None,
            user_email=user_meta["email"] if user_meta else None,
            group_id=int(group_id) if group_id is not None else None,
            group_name=group_meta["name"] if group_meta else None,
            sub_type_id=int(sub_type_id) if sub_type_id is not None else None,
            sub_type_name=sub_meta["name"] if sub_meta else None,
            notes=row["notes"],
            extension=row["extension"],
            asset_tag=row["asset_tag"],
            created_at_utc=row["created_at_utc"],
            updated_at_utc=row["updated_at_utc"],
            archived=bool(row["archived"]),
        )

    def as_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["archived"] = int(self.archived)
        return payload
