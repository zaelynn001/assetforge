# Rev 0.1.0

"""Filters sidebar with combo boxes for quick narrowing."""
from __future__ import annotations

from typing import Dict, Iterable, Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class FiltersPanel(QWidget):
    filtersChanged = Signal(dict)
    clearRequested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._type_combo = QComboBox()
        self._location_combo = QComboBox()
        self._user_combo = QComboBox()
        self._group_combo = QComboBox()

        for combo in (
            self._type_combo,
            self._location_combo,
            self._user_combo,
            self._group_combo,
        ):
            combo.currentIndexChanged.connect(self._emit_filters)

        form = QFormLayout()
        form.addRow("Type", self._type_combo)
        form.addRow("Location", self._location_combo)
        form.addRow("User", self._user_combo)
        form.addRow("Group", self._group_combo)

        clear_btn = QPushButton("Clear Filters")
        clear_btn.clicked.connect(self._on_clear)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addStretch(1)
        layout.addWidget(clear_btn)

    # ------------------------------------------------------------------
    def populate(self, *, types, locations, users, groups) -> None:
        self._populate_combo(self._type_combo, types)
        self._populate_combo(self._location_combo, locations)
        self._populate_combo(self._user_combo, users)
        self._populate_combo(self._group_combo, groups)

    def _populate_combo(self, combo: QComboBox, rows: Iterable[dict]) -> None:
        combo.blockSignals(True)
        combo.clear()
        combo.addItem("All", None)
        for row in rows:
            combo.addItem(row.get("name", "Unnamed"), row.get("id"))
        combo.blockSignals(False)

    def selected_filters(self) -> Dict[str, Optional[int]]:
        return {
            "type_id": self._current_data(self._type_combo),
            "location_id": self._current_data(self._location_combo),
            "user_id": self._current_data(self._user_combo),
            "group_id": self._current_data(self._group_combo),
        }

    def _current_data(self, combo: QComboBox) -> Optional[int]:
        data = combo.currentData()
        return int(data) if data is not None else None

    def _emit_filters(self) -> None:
        self.filtersChanged.emit(self.selected_filters())

    def _on_clear(self) -> None:
        for combo in (
            self._type_combo,
            self._location_combo,
            self._user_combo,
            self._group_combo,
        ):
            combo.setCurrentIndex(0)
        self.clearRequested.emit()
