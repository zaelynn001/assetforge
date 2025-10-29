# Rev 1.2.0 - Distro

"""Panel showing summary details for the selected item."""
from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import QLabel, QFormLayout, QWidget


class DetailsPanel(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._labels = {}
        form = QFormLayout(self)
        for key, title in (
            ("asset_tag", "Asset Tag"),
            ("name", "Name"),
            ("model", "Model"),
            ("type_name", "Type"),
            ("mac_address", "MAC Address"),
            ("ip_address", "IP Address"),
            ("extension", "Extension"),
            ("sub_type_name", "Sub Type"),
            ("location_name", "Location"),
            ("user_name", "Assigned User"),
            ("group_name", "Assigned Group"),
            ("notes", "Notes"),
            ("updated_at_utc", "Updated"),
        ):
            lbl = QLabel("—")
            lbl.setObjectName(f"detail_{key}")
            lbl.setWordWrap(True)
            form.addRow(f"{title}:", lbl)
            self._labels[key] = lbl

    def set_item(self, item: Optional[dict]) -> None:
        item = item or {}
        for key, label in self._labels.items():
            value = item.get(key)
            label.setText(str(value) if value not in (None, "") else "—")
