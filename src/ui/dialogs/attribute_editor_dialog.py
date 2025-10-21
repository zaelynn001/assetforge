# Rev 0.1.0

"""Dialog for editing an item attribute key/value pair."""
from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QVBoxLayout,
)


class AttributeEditorDialog(QDialog):
    def __init__(self, *, key: str = "", value: str = "", parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Attribute")
        self.setModal(True)

        self._key_edit = QLineEdit(key, self)
        self._value_edit = QLineEdit(value, self)
        self._key_edit.setPlaceholderText("Key (e.g. cpu)")
        self._value_edit.setPlaceholderText("Value")

        form = QFormLayout()
        form.addRow("Key", self._key_edit)
        form.addRow("Value", self._value_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _on_accept(self) -> None:
        if not self._key_edit.text().strip():
            self._key_edit.setFocus()
            return
        self.accept()

    def values(self) -> tuple[str, Optional[str]]:
        key = self._key_edit.text().strip()
        value = self._value_edit.text().strip()
        return key, value or None
