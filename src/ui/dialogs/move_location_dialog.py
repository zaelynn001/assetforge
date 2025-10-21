# Rev 0.1.0

"""Dialog for selecting a new location for an item."""
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


class MoveLocationDialog(QDialog):
    def __init__(
        self,
        *,
        locations: Iterable[dict],
        parent=None,
        current_location_id: Optional[int] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Move Location")
        self.setModal(True)

        self._location_combo = QComboBox(self)
        self._note = QTextEdit(self)
        self._note.setPlaceholderText("Optional note…")
        self._note.setFixedHeight(80)

        self._populate_combo(locations)
        if current_location_id is not None:
            idx = self._location_combo.findData(current_location_id)
            if idx >= 0:
                self._location_combo.setCurrentIndex(idx)

        form = QFormLayout()
        form.addRow("Location", self._location_combo)
        form.addRow("Note", self._note)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _populate_combo(self, locations: Iterable[dict]) -> None:
        self._location_combo.clear()
        self._location_combo.addItem("Unassigned", None)
        for row in locations:
            self._location_combo.addItem(row.get("name", "Unnamed"), row.get("id"))

    def values(self) -> dict:
        value = self._location_combo.currentData()
        note_text = self._note.toPlainText().strip()
        return {
            "location_id": int(value) if value is not None else None,
            "note": note_text or None,
        }
