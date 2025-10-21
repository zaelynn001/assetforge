# Rev 0.1.0

"""Main window implementing the inventory workspace (Milestone M3)."""
from __future__ import annotations

import csv
from typing import Any, Optional

from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from src.repositories.sqlite_items_repo import SQLiteItemsRepository
from src.repositories.sqlite_types_repo import SQLiteTypesRepository
from src.repositories.sqlite_locations_repo import SQLiteLocationsRepository
from src.repositories.sqlite_users_repo import SQLiteUsersRepository
from src.repositories.sqlite_groups_repo import SQLiteGroupsRepository
from src.repositories.sqlite_attributes_repo import SQLiteAttributesRepository
from src.repositories.sqlite_updates_repo import SQLiteUpdatesRepository
from src.viewmodels.items_viewmodel import ItemsViewModel
from src.viewmodels.filters_viewmodel import FiltersViewModel
from src.ui.panels.filters_panel import FiltersPanel
from src.ui.panels.items_table import ItemsTable
from src.ui.panels.details_panel import DetailsPanel
from src.ui.panels.attributes_panel import AttributesPanel
from src.ui.panels.history_panel import HistoryPanel
from src.ui.dialogs.item_editor_dialog import ItemEditorDialog


class MainWindow(QMainWindow):
    def __init__(self, *, database: Any, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._db = database

        # repositories
        self._items_repo = SQLiteItemsRepository(database)
        self._types_repo = SQLiteTypesRepository(database)
        self._locations_repo = SQLiteLocationsRepository(database)
        self._users_repo = SQLiteUsersRepository(database)
        self._groups_repo = SQLiteGroupsRepository(database)
        self._attributes_repo = SQLiteAttributesRepository(database)
        self._updates_repo = SQLiteUpdatesRepository(database)

        # view-models
        self._items_vm = ItemsViewModel(self._items_repo)
        self._filters_vm = FiltersViewModel(
            types_repo=self._types_repo,
            locations_repo=self._locations_repo,
            users_repo=self._users_repo,
            groups_repo=self._groups_repo,
        )

        self._pending_select_id: Optional[int] = None

        self._build_ui()
        self._connect_signals()

        # populate filter combos and initial data
        options = self._filters_vm.options()
        self._filters_panel.populate(
            types=options["types"],
            locations=options["locations"],
            users=options["users"],
            groups=options["groups"],
        )

        self.statusBar().showMessage(f"Connected to {self._db.path}")
        self._items_vm.refresh()
        self.showMaximized()

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        self.setWindowTitle("AssetForge — Inventory Control")
        self.resize(1360, 900)

        self._filters_panel = FiltersPanel(self)
        self._items_table = ItemsTable(self)
        self._details_panel = DetailsPanel(self)
        self._attributes_panel = AttributesPanel(self)
        self._history_panel = HistoryPanel(self)

        tabs = QTabWidget(self)
        tabs.addTab(self._details_panel, "Overview")
        tabs.addTab(self._attributes_panel, "Attributes")
        tabs.addTab(self._history_panel, "History")

        splitter = QSplitter(Qt.Horizontal, self)
        splitter.addWidget(self._filters_panel)
        splitter.addWidget(self._items_table)
        splitter.addWidget(tabs)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        splitter.setStretchFactor(2, 2)

        central = QWidget(self)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addWidget(splitter)
        self.setCentralWidget(central)

        self._build_toolbar()

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("Main", self)
        toolbar.setMovable(False)
        self.addToolBar(Qt.TopToolBarArea, toolbar)

        self._act_new = QAction("New Item", self)
        self._act_new.triggered.connect(self._on_new_item)
        toolbar.addAction(self._act_new)

        self._act_edit = QAction("Edit Item", self)
        self._act_edit.setEnabled(False)
        self._act_edit.triggered.connect(self._on_edit_item)
        toolbar.addAction(self._act_edit)

        self._act_assign = QAction("Assign…", self)
        self._act_assign.setEnabled(False)
        self._act_assign.triggered.connect(self._on_assign_item)
        toolbar.addAction(self._act_assign)

        self._act_move = QAction("Move Location…", self)
        self._act_move.setEnabled(False)
        self._act_move.triggered.connect(self._on_move_item)
        toolbar.addAction(self._act_move)

        toolbar.addSeparator()

        self._search_edit = QLineEdit(self)
        self._search_edit.setPlaceholderText("Scan or search…")
        self._search_edit.setClearButtonEnabled(True)
        self._search_edit.returnPressed.connect(self._on_search_committed)
        self._search_edit.installEventFilter(self)
        toolbar.addWidget(self._search_edit)

    def _connect_signals(self) -> None:
        self._filters_panel.filtersChanged.connect(self._on_filters_changed)
        self._filters_panel.clearRequested.connect(self._on_filters_cleared)
        self._items_table.itemSelected.connect(self._items_vm.set_selected_item)
        self._items_table.itemActivated.connect(self._on_edit_item)
        self._items_vm.itemsChanged.connect(self._on_items_loaded)
        self._items_vm.selectedItemChanged.connect(self._on_item_details)
        self._filters_vm.optionsChanged.connect(self._on_filter_options)
        self._attributes_panel.attributeAdded.connect(self._on_attribute_added)
        self._attributes_panel.attributeEdited.connect(self._on_attribute_edited)
        self._attributes_panel.attributeDeleted.connect(self._on_attribute_deleted)
        self._attributes_panel.importRequested.connect(self._on_attribute_import)

    # ------------------------------------------------------------------
    def _on_filter_options(self, options: dict) -> None:
        self._filters_panel.populate(
            types=options.get("types", []),
            locations=options.get("locations", []),
            users=options.get("users", []),
            groups=options.get("groups", []),
        )

    def _on_filters_changed(self, filters: dict) -> None:
        self._items_vm.set_filters(
            type_id=filters.get("type_id"),
            location_id=filters.get("location_id"),
            user_id=filters.get("user_id"),
            group_id=filters.get("group_id"),
        )

    def _on_filters_cleared(self) -> None:
        self._items_vm.clear_filters()

    def _on_search_committed(self) -> None:
        self._items_vm.set_search(self._search_edit.text())

    def _on_items_loaded(self, items: list[dict]) -> None:
        self._items_table.set_rows(items)
        if self._pending_select_id is not None:
            self._items_table.select_item(self._pending_select_id)
            self._items_vm.set_selected_item(self._pending_select_id)
            self._pending_select_id = None
        else:
            current = self._items_vm.selected_item_id()
            if current:
                self._items_table.select_item(current)
        self._update_edit_action()

    def _on_item_details(self, item: dict) -> None:
        self._details_panel.set_item(item)
        if item:
            attrs = self._attributes_repo.list_for_item(item["id"])
            updates = self._updates_repo.list_for_item(item["id"], limit=100)
        else:
            attrs = []
            updates = []
        self._attributes_panel.set_attributes(attrs)
        self._history_panel.set_entries(updates)
        self._update_edit_action()

    def _update_edit_action(self) -> None:
        has_selection = self._items_vm.selected_item_id() is not None
        self._act_edit.setEnabled(has_selection)
        self._act_assign.setEnabled(has_selection)
        self._act_move.setEnabled(has_selection)

    # ------------------------------------------------------------------
    def _on_new_item(self) -> None:
        dialog = ItemEditorDialog(
            types=self._types_repo.list_types(order_by="name"),
            locations=self._locations_repo.list_locations(order_by="name"),
            users=self._users_repo.list_users(order_by="name"),
            groups=self._groups_repo.list_groups(order_by="name"),
            parent=self,
        )
        if dialog.exec() == QDialog.Accepted:
            payload = dialog.values()
            try:
                record = self._items_repo.create(**payload, note="created via UI")
            except Exception as exc:
                QMessageBox.critical(self, "Create failed", str(exc))
                return
            self._pending_select_id = record["id"]
            self._items_vm.refresh()
            self.statusBar().showMessage("Item created", 3000)

    def _on_edit_item(self) -> None:
        item_id = self._items_vm.selected_item_id()
        if item_id is None:
            return
        current = self._items_repo.get_details(item_id)
        if not current:
            QMessageBox.warning(self, "Missing item", "The selected item no longer exists.")
            self._items_vm.refresh()
            return

        dialog = ItemEditorDialog(
            types=self._types_repo.list_types(order_by="name"),
            locations=self._locations_repo.list_locations(order_by="name"),
            users=self._users_repo.list_users(order_by="name"),
            groups=self._groups_repo.list_groups(order_by="name"),
            parent=self,
            item=current,
        )
        if dialog.exec() == QDialog.Accepted:
            payload = dialog.values()
            try:
                self._items_repo.update(item_id, **payload, note="edited via UI")
            except Exception as exc:
                QMessageBox.critical(self, "Update failed", str(exc))
                return
            self._pending_select_id = item_id
            self._items_vm.refresh()
            self.statusBar().showMessage("Item updated", 3000)

    def _on_assign_item(self) -> None:
        item_id = self._items_vm.selected_item_id()
        if item_id is None:
            return
        current = self._items_repo.get_details(item_id)
        if not current:
            return
        dialog = AssignUserDialog(
            users=self._users_repo.list_users(order_by="name"),
            groups=self._groups_repo.list_groups(order_by="name"),
            parent=self,
            current_user_id=current.get("user_id"),
            current_group_id=current.get("group_id"),
        )
        if dialog.exec() == QDialog.Accepted:
            payload = dialog.values()
            try:
                self._items_repo.assign(item_id, **payload)
            except Exception as exc:
                QMessageBox.critical(self, "Assign failed", str(exc))
                return
            self._after_item_mutation(item_id, "Assignment updated")

    def _on_move_item(self) -> None:
        item_id = self._items_vm.selected_item_id()
        if item_id is None:
            return
        current = self._items_repo.get_details(item_id)
        if not current:
            return
        dialog = MoveLocationDialog(
            locations=self._locations_repo.list_locations(order_by="name"),
            parent=self,
            current_location_id=current.get("location_id"),
        )
        if dialog.exec() == QDialog.Accepted:
            payload = dialog.values()
            try:
                self._items_repo.move_location(item_id, **payload)
            except Exception as exc:
                QMessageBox.critical(self, "Move failed", str(exc))
                return
            self._after_item_mutation(item_id, "Location updated")

    def _after_item_mutation(self, item_id: int, message: str) -> None:
        self._pending_select_id = item_id
        self._items_vm.refresh()
        self.statusBar().showMessage(message, 3000)

    # ----- attributes -------------------------------------------------
    def _on_attribute_added(self, key: str, value) -> None:
        item_id = self._items_vm.selected_item_id()
        if item_id is None:
            return
        try:
            changed = self._attributes_repo.set_attribute(
                item_id=item_id,
                key=key,
                value=value,
                note="attribute add via UI",
            )
        except Exception as exc:
            QMessageBox.critical(self, "Add attribute failed", str(exc))
            return
        if changed:
            self._refresh_selected_item(item_id)
            self.statusBar().showMessage("Attribute added", 3000)

    def _on_attribute_edited(self, old_key: str, new_key: str, value) -> None:
        item_id = self._items_vm.selected_item_id()
        if item_id is None:
            return
        try:
            if new_key == old_key:
                changed = self._attributes_repo.set_attribute(
                    item_id=item_id,
                    key=old_key,
                    value=value,
                    note="attribute edit via UI",
                )
            else:
                self._attributes_repo.delete_attribute(
                    item_id=item_id,
                    key=old_key,
                    note="attribute renamed via UI",
                )
                changed = self._attributes_repo.set_attribute(
                    item_id=item_id,
                    key=new_key,
                    value=value,
                    note="attribute renamed via UI",
                )
        except Exception as exc:
            QMessageBox.critical(self, "Edit attribute failed", str(exc))
            return
        if changed:
            self._refresh_selected_item(item_id)
            self.statusBar().showMessage("Attribute updated", 3000)

    def _on_attribute_deleted(self, key: str) -> None:
        item_id = self._items_vm.selected_item_id()
        if item_id is None:
            return
        if (
            QMessageBox.question(
                self,
                "Delete attribute",
                f"Remove attribute '{key}'?",
                QMessageBox.Yes | QMessageBox.No,
            )
            != QMessageBox.Yes
        ):
            return
        try:
            changed = self._attributes_repo.delete_attribute(
                item_id=item_id,
                key=key,
                note="attribute removed via UI",
            )
        except Exception as exc:
            QMessageBox.critical(self, "Delete attribute failed", str(exc))
            return
        if changed:
            self._refresh_selected_item(item_id)
            self.statusBar().showMessage("Attribute removed", 3000)

    def _refresh_selected_item(self, item_id: int) -> None:
        details = self._items_repo.get_details(item_id) or {}
        self._details_panel.set_item(details)
        attrs = self._attributes_repo.list_for_item(item_id)
        updates = self._updates_repo.list_for_item(item_id, limit=100)
        self._attributes_panel.set_attributes(attrs)
        self._history_panel.set_entries(updates)

    def _on_attribute_import(self) -> None:
        item_id = self._items_vm.selected_item_id()
        if item_id is None:
            return
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import attributes from CSV",
            "",
            "CSV Files (*.csv);;All Files (*)",
        )
        if not path:
            return
        imported = 0
        try:
            with open(path, newline="", encoding="utf-8") as fh:
                reader = csv.reader(fh)
                for row in reader:
                    if not row:
                        continue
                    if len(row) < 1:
                        continue
                    key = row[0].strip()
                    if not key:
                        continue
                    value = row[1].strip() if len(row) > 1 else None
                    try:
                        changed = self._attributes_repo.set_attribute(
                            item_id=item_id,
                            key=key,
                            value=value,
                            note="attribute import via CSV",
                        )
                    except Exception as exc:
                        QMessageBox.warning(self, "Import warning", f"{key}: {exc}")
                        continue
                    if changed:
                        imported += 1
        except Exception as exc:
            QMessageBox.critical(self, "Import failed", str(exc))
            return
        if imported:
            self._refresh_selected_item(item_id)
            self.statusBar().showMessage(f"Imported {imported} attributes", 3000)

    # ------------------------------------------------------------------
    def eventFilter(self, obj, event):  # noqa: N802
        if obj is self._search_edit and event.type() == QEvent.FocusIn:
            self._search_edit.selectAll()
        return super().eventFilter(obj, event)

    def keyPressEvent(self, event):  # noqa: N802
        if (
            event.text()
            and not event.text().isspace()
            and not event.modifiers() & (Qt.ControlModifier | Qt.AltModifier | Qt.MetaModifier)
        ):
            if not self._search_edit.hasFocus():
                self._search_edit.setFocus()
                self._search_edit.selectAll()
            QApplication.sendEvent(self._search_edit, event)
            return
        super().keyPressEvent(event)
