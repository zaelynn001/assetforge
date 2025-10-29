# Rev 1.2.0 - Distro

"""Modal dialog for creating or editing an inventory item."""
from __future__ import annotations

from typing import Iterable, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
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
        sub_types: Iterable[dict],
        ip_addresses: Iterable[str],
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
        self._sub_types = list(sub_types)
        self._ip_addresses = [str(ip) for ip in ip_addresses]
        self._landline_type_id = self._resolve_landline_type_id()

        self._name = QLineEdit()
        self._model = QLineEdit()
        self._type_combo = QComboBox()
        self._mac = QLineEdit()
        self._ip_combo = QComboBox()
        self._location_combo = QComboBox()
        self._user_combo = QComboBox()
        self._group_combo = QComboBox()
        self._sub_type_combo = QComboBox()
        self._extension = QLineEdit()
        self._extension.setPlaceholderText("e.g. 1234")
        self._extension_label = QLabel("Extension")
        self._notes = QTextEdit()
        self._notes.setPlaceholderText("Optional notes…")
        self._notes.setFixedHeight(80)

        self._populate_combo(self._type_combo, self._types, required=True)
        self._populate_combo(self._location_combo, self._locations)
        self._populate_combo(self._user_combo, self._users)
        self._ip_combo.setEditable(False)
        self._populate_combo(self._group_combo, self._groups)
        self._populate_combo(self._sub_type_combo, self._sub_types)

        current_ip = item.get("ip_address") if item else None
        self._populate_ip_combo(current_ip)

        form = QFormLayout()
        form.addRow("Name", self._name)
        form.addRow("Model", self._model)
        form.addRow("Type", self._type_combo)
        form.addRow("MAC", self._mac)
        form.addRow("IP Address", self._ip_combo)
        form.addRow("Location", self._location_combo)
        form.addRow("User", self._user_combo)
        form.addRow("Group", self._group_combo)
        form.addRow("Sub Type", self._sub_type_combo)
        form.addRow(self._extension_label, self._extension)
        form.addRow("Notes", self._notes)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

        self._type_combo.currentIndexChanged.connect(self._on_type_changed)

        if item:
            self._apply_item(item)
        else:
            self._ip_combo.setCurrentIndex(0)
            self._update_extension_visibility()
        self._apply_relative_size()

    # ------------------------------------------------------------------
    def _populate_combo(self, combo: QComboBox, rows: Iterable[dict], *, required: bool = False) -> None:
        combo.clear()
        if not required:
            combo.addItem("Not Assigned", None)
        for row in rows:
            combo.addItem(row.get("name", "Unnamed"), row.get("id"))

    def _populate_ip_combo(self, current_ip: Optional[str]) -> None:
        self._ip_combo.clear()
        self._ip_combo.addItem("Not Assigned", None)
        unique = {ip for ip in self._ip_addresses if ip}
        if current_ip:
            unique.add(current_ip)

        def ip_key(value: str) -> tuple[int, ...]:
            try:
                return tuple(int(part) for part in value.split("."))
            except ValueError:
                return tuple(ord(ch) for ch in value)

        for ip in sorted(unique, key=ip_key):
            self._ip_combo.addItem(ip, ip)

    def _apply_item(self, item: dict) -> None:
        self._name.setText(item.get("name", ""))
        self._model.setText(item.get("model", ""))
        self._mac.setText(item.get("mac_address", ""))
        self._notes.setPlainText(item.get("notes", "") or "")
        self._set_combo_value(self._type_combo, item.get("type_id"))
        self._set_combo_value(self._location_combo, item.get("location_id"))
        self._set_combo_value(self._user_combo, item.get("user_id"))
        self._set_combo_value(self._group_combo, item.get("group_id"))
        self._set_combo_value(self._ip_combo, item.get("ip_address"))
        self._set_combo_value(self._sub_type_combo, item.get("sub_type_id"))
        self._extension.setText(item.get("extension", "") or "")
        self._update_extension_visibility()

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
        ip_value = self._ip_combo.currentData()
        if isinstance(ip_value, str):
            ip_value = ip_value.strip() or None

        selected_type_id = int(self._type_combo.currentData())
        extension_value = None
        if self._is_landline(selected_type_id):
            extension_value = self._extension.text().strip() or None

        return {
            "name": self._name.text().strip(),
            "model": self._model.text().strip() or None,
            "type_id": selected_type_id,
            "mac_address": self._mac.text().strip() or None,
            "ip_address": ip_value,
            "location_id": data(self._location_combo),
            "user_id": data(self._user_combo),
            "group_id": data(self._group_combo),
            "sub_type_id": data(self._sub_type_combo),
            "notes": notes_text or None,
            "extension": extension_value,
        }

    def _on_type_changed(self) -> None:
        self._update_extension_visibility()

    def _update_extension_visibility(self) -> None:
        type_id = self._type_combo.currentData()
        is_landline = self._is_landline(int(type_id)) if type_id is not None else False
        self._extension_label.setVisible(is_landline)
        self._extension.setVisible(is_landline)
        if not is_landline:
            self._extension.clear()

    def _is_landline(self, type_id: int) -> bool:
        landline_id = self._landline_type_id
        return landline_id is not None and type_id == landline_id

    def _resolve_landline_type_id(self) -> Optional[int]:
        for row in self._types:
            code = (row.get("code") or "").upper()
            if code == "TP":
                return int(row.get("id"))
        return None

    def _apply_relative_size(self) -> None:
        parent = self.parentWidget()
        window = parent.window() if parent else None
        if window is None:
            from PySide6.QtWidgets import QApplication
            window = QApplication.activeWindow()
        if window is None:
            return
        self.resize(int(window.width() * 0.5), int(window.height() * 0.6))
