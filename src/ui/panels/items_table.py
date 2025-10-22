# Rev 1.0.0

"""Items table widget showing inventory rows."""
from __future__ import annotations

from typing import Dict, List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHeaderView, QTableWidget, QTableWidgetItem


class ItemsTable(QTableWidget):
    itemSelected = Signal(int)
    itemActivated = Signal(int)
    contextMenuRequested = Signal(object, object)  # item_id (or None), global QPoint

    _COLUMNS = (
        ("Asset Tag", "asset_tag"),
        ("Name", "name"),
        ("Model", "model"),
        ("Type", "type_name"),
        ("MAC", "mac_address"),
    )

    def __init__(self, parent=None) -> None:
        super().__init__(0, len(self._COLUMNS), parent)
        self.setHorizontalHeaderLabels([name for name, _key in self._COLUMNS])
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setSelectionMode(QTableWidget.SingleSelection)
        self.setEditTriggers(QTableWidget.NoEditTriggers)
        self.verticalHeader().setVisible(False)
        self.verticalHeader().setDefaultSectionSize(26)

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._on_context_menu)

        header: QHeaderView = self.horizontalHeader()
        header.setStretchLastSection(True)
        resize_columns = {0, 2, 4}
        for idx, _ in enumerate(self._COLUMNS):
            mode = QHeaderView.ResizeToContents if idx in resize_columns else QHeaderView.Stretch
            header.setSectionResizeMode(idx, mode)

        self.itemSelectionChanged.connect(self._emit_selection)
        self.itemDoubleClicked.connect(self._activate)
        self._rows: List[Dict[str, str]] = []

    # ------------------------------------------------------------------
    def set_rows(self, rows: List[Dict[str, str]]) -> None:
        previous_id = self.current_item_id()
        self._rows = list(rows)
        self.setRowCount(len(self._rows))
        for r, row in enumerate(self._rows):
            display_row = dict(row)
            for c, (_, key) in enumerate(self._COLUMNS):
                value = display_row.get(key) or ""
                item = QTableWidgetItem(str(value))
                item.setData(Qt.UserRole, row.get("id"))
                if c == 0:
                    item.setFont(item.font())
                    item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                self.setItem(r, c, item)
        self.resizeColumnsToContents()
        if previous_id is not None:
            self.select_item(previous_id)

    def current_item_id(self) -> Optional[int]:
        row = self.currentRow()
        if row < 0:
            return None
        item = self.item(row, 0)
        if not item:
            return None
        value = item.data(Qt.UserRole)
        return int(value) if value is not None else None

    def select_item(self, item_id: Optional[int]) -> None:
        if item_id is None:
            self.clearSelection()
            return
        for row in range(self.rowCount()):
            if self.item(row, 0).data(Qt.UserRole) == item_id:
                self.selectRow(row)
                self.scrollToItem(self.item(row, 0), QTableWidget.PositionAtCenter)
                break

    # ------------------------------------------------------------------
    def _emit_selection(self) -> None:
        item_id = self.current_item_id()
        if item_id is not None:
            self.itemSelected.emit(item_id)

    def _activate(self, item: QTableWidgetItem) -> None:
        item_id = item.data(Qt.UserRole)
        if item_id is not None:
            self.itemActivated.emit(int(item_id))

    def _on_context_menu(self, pos) -> None:
        item = self.itemAt(pos)
        item_id = None
        if item is not None:
            item_id = item.data(Qt.UserRole)
            if item_id is not None:
                self.selectRow(item.row())
        else:
            self.clearSelection()
        self.contextMenuRequested.emit(item_id, self.mapToGlobal(pos))
