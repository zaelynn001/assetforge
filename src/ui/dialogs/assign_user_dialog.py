# Rev 0.1.0

"""Dialog for assigning a user and/or group to an item."""
from __future__ import annotations

from typing import Iterable, Optional

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QTextEdit,
    QVBoxLayout,
)


class AssignUserDialog(QDialog):
    def __init__(
        self,
        *,
        users: Iterable[dict],
        groups: Iterable[dict],
        parent=None,
        current_user_id: Optional[int] = None,
        current_group_id: Optional[int] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Assign User/Group")
        self.setModal(True)

        self._user_combo = QComboBox(self)
        self._group_combo = QComboBox(self)
        self._note = QTextEdit(self)
        self._note.setPlaceholderText("Optional note…")
        self._note.setFixedHeight(80)

        self._populate_combo(self._user_combo, users)
        self._populate_combo(self._group_combo, groups)

        if current_user_id is not None:
            idx = self._user_combo.findData(current_user_id)
            if idx >= 0:
                self._user_combo.setCurrentIndex(idx)
        if current_group_id is not None:
            idx = self._group_combo.findData(current_group_id)
            if idx >= 0:
                self._group_combo.setCurrentIndex(idx)

        form = QFormLayout()
        form.addRow("User", self._user_combo)
        form.addRow("Group", self._group_combo)
        form.addRow("Note", self._note)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _populate_combo(self, combo: QComboBox, rows: Iterable[dict]) -> None:
        combo.clear()
        combo.addItem("Unassigned", None)
        for row in rows:
            combo.addItem(row.get("name", "Unnamed"), row.get("id"))

    def values(self) -> dict:
        def data(combo: QComboBox) -> Optional[int]:
            value = combo.currentData()
            return int(value) if value is not None else None

        note_text = self._note.toPlainText().strip()
        return {
            "user_id": data(self._user_combo),
            "group_id": data(self._group_combo),
            "note": note_text or None,
        }
