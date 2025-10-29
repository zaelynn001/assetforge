# Rev 1.2.0 - Distro

"""Generic entity manager dialog for reference data."""
from __future__ import annotations

from typing import Callable, Dict, Iterable, List, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QMessageBox,
    QLineEdit,
    QFormLayout,
)


class EntityFormDialog(QDialog):
    def __init__(self, *, fields: List[Dict[str, object]], data: Optional[Dict[str, object]] = None, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit")
        self._fields = fields
        self._inputs: Dict[str, QLineEdit] = {}

        form = QFormLayout()
        for field in fields:
            key = field["key"]
            label = field["label"]
            line = QLineEdit(self)
            if data and key in data and data[key] is not None:
                line.setText(str(data[key]))
            form.addRow(str(label), line)
            self._inputs[key] = line

        buttons = QHBoxLayout()
        btn_ok = QPushButton("OK", self)
        btn_cancel = QPushButton("Cancel", self)
        btn_ok.clicked.connect(self._on_accept)
        btn_cancel.clicked.connect(self.reject)
        buttons.addStretch(1)
        buttons.addWidget(btn_cancel)
        buttons.addWidget(btn_ok)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(buttons)

    def _on_accept(self) -> None:
        for field in self._fields:
            if field.get("required") and not self._inputs[field["key"]].text().strip():
                QMessageBox.warning(self, "Missing value", f"Please fill out {field['label']}.")
                self._inputs[field["key"]].setFocus()
                return
        self.accept()

    def values(self) -> Dict[str, str]:
        return {
            key: self._inputs[key].text().strip()
            for key in self._inputs
        }


class EntityManagerDialog(QDialog):
    def __init__(
        self,
        *,
        title: str,
        fields: List[Dict[str, object]],
        list_func: Callable[[], Iterable[Dict[str, object]]],
        create_func: Callable[[Dict[str, object]], object],
        update_func: Callable[[int, Dict[str, object]], bool],
        delete_func: Callable[[int], bool],
        display_func: Optional[Callable[[Dict[str, object]], str]] = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(420, 360)
        self._fields = fields
        self._list_func = list_func
        self._create_func = create_func
        self._update_func = update_func
        self._delete_func = delete_func
        self._display_func = display_func or (lambda rec: rec.get("name", str(rec.get("id"))))
        self._records: List[Dict[str, object]] = []

        self._list = QListWidget(self)
        self._list.itemDoubleClicked.connect(self._on_edit)

        btn_add = QPushButton("Add", self)
        btn_edit = QPushButton("Edit", self)
        btn_delete = QPushButton("Delete", self)
        btn_close = QPushButton("Close", self)

        btn_add.clicked.connect(self._on_add)
        btn_edit.clicked.connect(self._on_edit)
        btn_delete.clicked.connect(self._on_delete)
        btn_close.clicked.connect(self.accept)

        buttons = QHBoxLayout()
        buttons.addWidget(btn_add)
        buttons.addWidget(btn_edit)
        buttons.addWidget(btn_delete)
        buttons.addStretch(1)
        buttons.addWidget(btn_close)

        layout = QVBoxLayout(self)
        layout.addWidget(self._list)
        layout.addLayout(buttons)

        self._reload()
        self._apply_relative_size()

    def _reload(self) -> None:
        self._records = list(self._list_func())
        self._list.clear()
        for record in self._records:
            item = QListWidgetItem(self._display_func(record))
            item.setData(Qt.UserRole, int(record.get("id")))
            self._list.addItem(item)

    # actions -----------------------------------------------------------
    def _on_add(self) -> None:
        dialog = EntityFormDialog(fields=self._fields, parent=self)
        if dialog.exec() != QDialog.Accepted:
            return
        payload = dialog.values()
        try:
            self._create_func(payload)
        except Exception as exc:
            QMessageBox.critical(self, "Create failed", str(exc))
            return
        self._reload()

    def _selected_record(self) -> Optional[Dict[str, object]]:
        item = self._list.currentItem()
        if not item:
            return None
        item_id = item.data(Qt.UserRole)
        for record in self._records:
            if int(record.get("id")) == item_id:
                return record
        return None

    def _on_edit(self) -> None:
        record = self._selected_record()
        if not record:
            return
        dialog = EntityFormDialog(fields=self._fields, data=record, parent=self)
        if dialog.exec() != QDialog.Accepted:
            return
        payload = dialog.values()
        try:
            success = self._update_func(int(record.get("id")), payload)
        except Exception as exc:
            QMessageBox.critical(self, "Update failed", str(exc))
            return
        if not success:
            QMessageBox.warning(self, "Update", "No changes were applied.")
            return
        self._reload()

    def _on_delete(self) -> None:
        record = self._selected_record()
        if not record:
            return
        if (
            QMessageBox.question(
                self,
                "Confirm delete",
                f"Delete '{self._display_func(record)}'?",
                QMessageBox.Yes | QMessageBox.No,
            )
            != QMessageBox.Yes
        ):
            return
        try:
            success = self._delete_func(int(record.get("id")))
        except Exception as exc:
            QMessageBox.critical(self, "Delete failed", str(exc))
            return
        if not success:
            QMessageBox.warning(self, "Delete", "Unable to delete; referenced elsewhere?")
            return
        self._reload()

    def _apply_relative_size(self) -> None:
        parent = self.parentWidget()
        window = parent.window() if parent else None
        if window is None:
            from PySide6.QtWidgets import QApplication
            window = QApplication.activeWindow()
        if window is None:
            return
        self.resize(int(window.width() * 0.5), int(window.height() * 0.6))
