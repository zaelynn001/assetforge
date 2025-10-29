# Rev 1.2.0 - Distro

"""History panel showing item change timeline."""
from __future__ import annotations

from typing import Iterable, List

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QHBoxLayout,
)


class HistoryPanel(QWidget):
    auditRequested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._list = QListWidget(self)
        self._list.setSelectionMode(QAbstractItemView.NoSelection)
        self._list.setUniformItemSizes(False)
        self._list.setWordWrap(True)
        self._list.setSpacing(6)
        self._list.setContextMenuPolicy(Qt.CustomContextMenu)
        self._list.customContextMenuRequested.connect(self._show_context_menu)

        self._btn_audit = QPushButton("Add Audit Note", self)
        self._btn_audit.clicked.connect(self.auditRequested.emit)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(self._btn_audit)

        layout = QVBoxLayout(self)
        layout.addWidget(self._list)
        layout.addLayout(buttons)

    # ------------------------------------------------------------------
    def set_entries(self, entries: Iterable[dict]) -> None:
        self._list.clear()
        for entry in entries:
            item = QListWidgetItem()
            widget = _HistoryEntryWidget(entry)
            item.setSizeHint(widget.sizeHint())
            item.setData(Qt.UserRole, entry)
            self._list.addItem(item)
            self._list.setItemWidget(item, widget)

    def _show_context_menu(self, pos) -> None:
        item = self._list.itemAt(pos)
        if item is None:
            return
        entry = item.data(Qt.UserRole) or {}
        timestamp = entry.get("created_at", "")
        summary = _format_summary(entry)
        changes = entry.get("changes", "")

        menu = QMenu(self)
        if timestamp:
            action_timestamp = menu.addAction("Copy Timestamp")
        else:
            action_timestamp = None
        if summary:
            action_summary = menu.addAction("Copy Summary")
        else:
            action_summary = None
        if changes.strip():
            action_changes = menu.addAction("Copy Changes")
        else:
            action_changes = None
        menu.addSeparator()
        action_all = menu.addAction("Copy Entry")

        chosen = menu.exec(self._list.mapToGlobal(pos))
        if chosen is None:
            return

        clipboard = QApplication.clipboard()
        if chosen is action_timestamp:
            clipboard.setText(timestamp)
        elif chosen is action_summary:
            clipboard.setText(summary)
        elif chosen is action_changes:
            clipboard.setText(changes)
        elif chosen is action_all:
            parts = [timestamp]
            if summary:
                parts.append(summary)
            if changes.strip():
                parts.append(changes)
            clipboard.setText("\n".join(parts))


class _HistoryEntryWidget(QWidget):
    def __init__(self, entry: dict) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        timestamp = QLabel(entry.get("created_at", ""), self)
        timestamp.setStyleSheet("font-weight: bold;")
        timestamp.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(timestamp)

        summary_text = _format_summary(entry)
        if summary_text:
            summary = QLabel(summary_text, self)
            summary.setWordWrap(True)
            summary.setTextInteractionFlags(Qt.TextSelectableByMouse)
            layout.addWidget(summary)

        changes_text = entry.get("changes") or ""
        if changes_text.strip():
            for raw_line in changes_text.splitlines():
                line = raw_line.strip()
                if not line:
                    continue
                change_label = QLabel(f"• {line}", self)
                change_label.setWordWrap(True)
                change_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
                layout.addWidget(change_label)

        layout.addStretch(1)


def _format_summary(entry: dict) -> str:
    summary_parts: List[str] = []
    reason = (entry.get("reason") or "").strip()
    if reason:
        summary_parts.append(reason.capitalize())
    note = (entry.get("note") or "").strip()
    if note:
        summary_parts.append(note)
    return " — ".join(summary_parts)
