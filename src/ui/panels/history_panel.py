# Rev 0.1.0

"""History panel showing item change timeline."""
from __future__ import annotations

from typing import Iterable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget


class HistoryPanel(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._table = QTableWidget(0, 4, self)
        self._table.setHorizontalHeaderLabels(["Timestamp", "Reason", "Note", "Changed Fields"])
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setSelectionMode(QTableWidget.NoSelection)

        layout = QVBoxLayout(self)
        layout.addWidget(self._table)

    def set_entries(self, entries: Iterable[dict]) -> None:
        data = list(entries)
        self._table.setRowCount(len(data))
        for r, row in enumerate(data):
            ts = row.get("created_at_utc", "")
            reason = row.get("reason", "")
            note = row.get("note", "") or ""
            changed = row.get("changed_fields", "") or ""
            values = (ts, reason, note, changed)
            for c, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setFlags(Qt.ItemIsEnabled)
                self._table.setItem(r, c, item)
        self._table.resizeColumnsToContents()
