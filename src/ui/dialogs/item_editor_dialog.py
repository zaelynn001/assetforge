# Rev 1.0.0

"""Modal dialog for creating or editing an inventory item."""
from __future__ import annotations

from typing import Iterable, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QTextEdit,
    QVBoxLayout,
)


class ItemEditorDialog(QDialog):
    def __init__(
        self,
        *,
        types: Iterable[dict],
        locations: Iterable[dict],
        users: Iterable[dict],
        groups: Iterable[dict],
        parent=None,
        item: Optional[dict] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("New Item" if item is None else "Edit Item")
        self.setModal(True)

        self._types = list(types)
        self._locations = list(locations)
        self._users = list(users)
        self._groups = list(groups)

        self._name = QLineEdit()
        self._model = QLineEdit()
        self._type_combo = QComboBox()
        self._mac = QLineEdit()
        self._location_combo = QComboBox()
        self._user_combo = QComboBox()
        self._group_combo = QComboBox()
        self._notes = QTextEdit()
        self._notes.setPlaceholderText("Optional notes…")
        self._notes.setFixedHeight(80)

        self._populate_combo(self._type_combo, self._types, required=True)
        self._populate_combo(self._location_combo, self._locations)
        self._populate_combo(self._user_combo, self._users)
        self._populate_combo(self._group_combo, self._groups)

        form = QFormLayout()
        form.addRow("Name", self._name)
        form.addRow("Model", self._model)
        form.addRow("Type", self._type_combo)
        form.addRow("MAC", self._mac)
        form.addRow("Location", self._location_combo)
        form.addRow("User", self._user_combo)
        form.addRow("Group", self._group_combo)
        form.addRow("Notes", self._notes)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

        if item:
            self._apply_item(item)
        self._apply_relative_size()

    # ------------------------------------------------------------------
    def _populate_combo(self, combo: QComboBox, rows: Iterable[dict], *, required: bool = False) -> None:
        combo.clear()
        if not required:
            combo.addItem("—", None)
        for row in rows:
            combo.addItem(row.get("name", "Unnamed"), row.get("id"))

    def _apply_item(self, item: dict) -> None:
        self._name.setText(item.get("name", ""))
        self._model.setText(item.get("model", ""))
        self._mac.setText(item.get("mac_address", ""))
        self._notes.setPlainText(item.get("notes", "") or "")
        self._set_combo_value(self._type_combo, item.get("type_id"))
        self._set_combo_value(self._location_combo, item.get("location_id"))
        self._set_combo_value(self._user_combo, item.get("user_id"))
        self._set_combo_value(self._group_combo, item.get("group_id"))

    def _set_combo_value(self, combo: QComboBox, value) -> None:
        if value is None:
            combo.setCurrentIndex(0)
            return
        idx = combo.findData(value)
        if idx >= 0:
            combo.setCurrentIndex(idx)

    # ------------------------------------------------------------------
    def _on_accept(self) -> None:
        if not self._name.text().strip():
            QMessageBox.warning(self, "Missing name", "Please provide a name for the item.")
            return
        if self._type_combo.currentData() is None:
            QMessageBox.warning(self, "Missing type", "Please select a hardware type.")
            return
        self.accept()

    def values(self) -> dict:
        def data(combo: QComboBox):
            value = combo.currentData()
            return int(value) if value is not None else None

        notes_text = self._notes.toPlainText().strip()

        return {
            "name": self._name.text().strip(),
            "model": self._model.text().strip() or None,
            "type_id": int(self._type_combo.currentData()),
            "mac_address": self._mac.text().strip() or None,
            "location_id": data(self._location_combo),
            "user_id": data(self._user_combo),
            "group_id": data(self._group_combo),
            "notes": notes_text or None,
        }

    def _apply_relative_size(self) -> None:
        parent = self.parentWidget()
        window = parent.window() if parent else None
        if window is None:
            from PySide6.QtWidgets import QApplication
            window = QApplication.activeWindow()
        if window is None:
            return
        self.resize(int(window.width() * 0.5), int(window.height() * 0.6))
