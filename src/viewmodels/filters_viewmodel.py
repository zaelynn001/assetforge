# Rev 1.2.0 - Distro

"""Filters view-model loading reference data for the UI."""
from __future__ import annotations

from typing import Dict, List

from PySide6.QtCore import QObject, Signal

from src.repositories.sqlite_types_repo import SQLiteTypesRepository
from src.repositories.sqlite_locations_repo import SQLiteLocationsRepository
from src.repositories.sqlite_users_repo import SQLiteUsersRepository
from src.repositories.sqlite_groups_repo import SQLiteGroupsRepository


class FiltersViewModel(QObject):
    optionsChanged = Signal(dict)

    def __init__(
        self,
        *,
        types_repo: SQLiteTypesRepository,
        locations_repo: SQLiteLocationsRepository,
        users_repo: SQLiteUsersRepository,
        groups_repo: SQLiteGroupsRepository,
    ) -> None:
        super().__init__()
        self._types_repo = types_repo
        self._locations_repo = locations_repo
        self._users_repo = users_repo
        self._groups_repo = groups_repo
        self._options: Dict[str, List[dict]] = {
            "types": [],
            "locations": [],
            "users": [],
            "groups": [],
        }

    def refresh(self) -> Dict[str, List[dict]]:
        self._options = {
            "types": self._types_repo.list_types(order_by="name"),
            "locations": self._locations_repo.list_locations(order_by="name"),
            "users": self._users_repo.list_users(order_by="name"),
            "groups": self._groups_repo.list_groups(order_by="name"),
        }
        self.optionsChanged.emit(self._options)
        return self._options

    def options(self) -> Dict[str, List[dict]]:
        if not any(self._options.values()):
            self.refresh()
        return self._options
