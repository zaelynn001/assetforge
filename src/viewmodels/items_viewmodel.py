# Rev 1.0.0

"""Items ViewModel providing filtering and selection logic."""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Set

from PySide6.QtCore import QObject, Signal

from src.repositories.sqlite_items_repo import SQLiteItemsRepository


class ItemsViewModel(QObject):
    """Coordinates item listings between repositories and the UI."""

    itemsChanged = Signal(list)          # Emits list of item dicts with display fields
    selectedItemChanged = Signal(dict)   # Emits detailed item dict or {}

    def __init__(self, items_repo: SQLiteItemsRepository) -> None:
        super().__init__()
        self._repo = items_repo
        self._items: List[Dict[str, Any]] = []
        self._filters: Dict[str, Set[int]] = {
            "type_ids": set(),
            "location_ids": set(),
            "user_ids": set(),
            "group_ids": set(),
        }
        self._search: Optional[str] = None
        self._selected_id: Optional[int] = None

    # ---- data loading -------------------------------------------------
    def refresh(self) -> None:
        """Reload items with the current filters/search and notify listeners."""
        self._items = self._repo.list_items(
            type_ids=self._filters["type_ids"],
            location_ids=self._filters["location_ids"],
            user_ids=self._filters["user_ids"],
            group_ids=self._filters["group_ids"],
            search=self._search,
        )
        self.itemsChanged.emit(self._items)
        if self._selected_id is not None:
            self.set_selected_item(self._selected_id, emit=True)

    # ---- filters ------------------------------------------------------
    def set_filter(self, key: str, ids: Iterable[int | None]) -> None:
        bucket = self._filters.get(key)
        if bucket is None:
            return
        new_ids = {int(i) for i in ids if i is not None}
        if new_ids != bucket:
            self._filters[key] = new_ids
            self.refresh()

    def set_filters(
        self,
        *,
        type_id: Optional[int] = None,
        location_id: Optional[int] = None,
        user_id: Optional[int] = None,
        group_id: Optional[int] = None,
    ) -> None:
        mapping = {
            "type_ids": {int(type_id)} if type_id is not None else set(),
            "location_ids": {int(location_id)} if location_id is not None else set(),
            "user_ids": {int(user_id)} if user_id is not None else set(),
            "group_ids": {int(group_id)} if group_id is not None else set(),
        }
        changed = False
        for key, new_ids in mapping.items():
            if self._filters.get(key) != new_ids:
                self._filters[key] = new_ids
                changed = True
        if changed:
            self.refresh()

    def clear_filters(self) -> None:
        changed = any(self._filters[k] for k in self._filters)
        for key in self._filters:
            self._filters[key] = set()
        if changed:
            self.refresh()

    def set_search(self, query: Optional[str]) -> None:
        cleaned = (query or "").strip() or None
        if cleaned != self._search:
            self._search = cleaned
            self.refresh()

    # ---- selection ----------------------------------------------------
    def set_selected_item(self, item_id: Optional[int], *, emit: bool = True) -> None:
        self._selected_id = item_id
        if not emit:
            return
        if item_id is None:
            self.selectedItemChanged.emit({})
            return
        details = self._repo.get_details(item_id)
        if details:
            self.selectedItemChanged.emit(details)
        else:
            self.selectedItemChanged.emit({})

    # ---- accessors ----------------------------------------------------
    def items(self) -> List[Dict[str, Any]]:
        return list(self._items)

    def selected_item_id(self) -> Optional[int]:
        return self._selected_id
