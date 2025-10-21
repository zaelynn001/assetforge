# Rev 0.1.0

"""Interactive tab for managing item attributes."""
from __future__ import annotations

from typing import Iterable, List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.ui.dialogs.attribute_editor_dialog import AttributeEditorDialog


class AttributesPanel(QWidget):
    attributeAdded = Signal(str, object)
    attributeEdited = Signal(str, str, object)  # old_key, new_key, value
    attributeDeleted = Signal(str)
    importRequested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._table = QTableWidget(0, 2, self)
        self._table.setHorizontalHeaderLabels(["Key", "Value"])
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setSelectionMode(QTableWidget.SingleSelection)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.itemDoubleClicked.connect(self._on_edit_clicked)

        self._btn_add = QPushButton("Add Attribute", self)
        self._btn_edit = QPushButton("Edit", self)
        self._btn_delete = QPushButton("Delete", self)
        self._btn_import = QPushButton("Import CSV…", self)
        self._btn_edit.setEnabled(False)
        self._btn_delete.setEnabled(False)

        self._btn_add.clicked.connect(self._on_add_clicked)
        self._btn_edit.clicked.connect(self._on_edit_clicked)
        self._btn_delete.clicked.connect(self._on_delete_clicked)
        self._btn_import.clicked.connect(self.importRequested.emit)
        self._table.itemSelectionChanged.connect(self._update_button_state)

        buttons = QHBoxLayout()
        buttons.addWidget(self._btn_add)
        buttons.addWidget(self._btn_edit)
        buttons.addWidget(self._btn_delete)
        buttons.addWidget(self._btn_import)
        buttons.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addWidget(self._table)
        layout.addLayout(buttons)

        self._rows: List[dict] = []

    def set_attributes(self, rows: Iterable[dict]) -> None:
        self._rows = list(rows)
        self._table.setRowCount(len(self._rows))
        for r, row in enumerate(self._rows):
            key_item = QTableWidgetItem(row.get("attr_key", ""))
            val_item = QTableWidgetItem(row.get("attr_value", ""))
            key_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            val_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self._table.setItem(r, 0, key_item)
            self._table.setItem(r, 1, val_item)
        self._table.resizeColumnsToContents()
        self._update_button_state()

    # ------------------------------------------------------------------
    def _selected_row_index(self) -> Optional[int]:
        indexes = self._table.selectionModel().selectedRows()
        if not indexes:
            return None
        return indexes[0].row()

    def _selected_key(self) -> Optional[str]:
        idx = self._selected_row_index()
        if idx is None:
            return None
        return self._rows[idx].get("attr_key")

    def _update_button_state(self) -> None:
        has_selection = self._selected_row_index() is not None
        self._btn_edit.setEnabled(has_selection)
        self._btn_delete.setEnabled(has_selection)

    def _on_add_clicked(self) -> None:
        dialog = AttributeEditorDialog(parent=self)
        if dialog.exec() == QDialog.Accepted:
            key, value = dialog.values()
            if self._key_exists(key):
                QMessageBox.warning(self, "Duplicate", f"Attribute '{key}' already exists.")
                return
            self.attributeAdded.emit(key, value)

    def _on_edit_clicked(self) -> None:
        idx = self._selected_row_index()
        if idx is None:
            return
        current = self._rows[idx]
        dialog = AttributeEditorDialog(
            key=current.get("attr_key", ""),
            value=current.get("attr_value", "") or "",
            parent=self,
        )
        if dialog.exec() == QDialog.Accepted:
            new_key, value = dialog.values()
            old_key = current.get("attr_key", "")
            if new_key != old_key and self._key_exists(new_key):
                QMessageBox.warning(self, "Duplicate", f"Attribute '{new_key}' already exists.")
                return
            self.attributeEdited.emit(old_key, new_key, value)

    def _on_delete_clicked(self) -> None:
        key = self._selected_key()
        if not key:
            return
        self.attributeDeleted.emit(key)

    def _key_exists(self, key: str) -> bool:
        key_lower = key.lower()
        return any((row.get("attr_key") or "").lower() == key_lower for row in self._rows)
