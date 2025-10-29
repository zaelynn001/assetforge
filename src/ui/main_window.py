# Rev 1.2.0 - Distro

"""Main window implementing the inventory workspace (Milestone M3)."""
from __future__ import annotations

import csv
import datetime as dt
from datetime import datetime
import json
import subprocess
from pathlib import Path
from typing import Any, Optional

from PySide6.QtCore import Qt, QEvent, QTimer
from PySide6.QtGui import QAction, QGuiApplication
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QInputDialog,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from src.utils.paths import EXPORT_DIR
from src.repositories.sqlite_items_repo import SQLiteItemsRepository
from src.repositories.sqlite_types_repo import SQLiteTypesRepository
from src.repositories.sqlite_locations_repo import SQLiteLocationsRepository
from src.repositories.sqlite_users_repo import SQLiteUsersRepository
from src.repositories.sqlite_groups_repo import SQLiteGroupsRepository
from src.repositories.sqlite_sub_types_repo import SQLiteSubTypesRepository
from src.repositories.sqlite_ip_addresses_repo import SQLiteIPAddressesRepository
from src.viewmodels.items_viewmodel import ItemsViewModel
from src.models.item_record import ItemRecord
from src.viewmodels.filters_viewmodel import FiltersViewModel
from src.ui.panels.filters_panel import FiltersPanel
from src.ui.panels.items_table import ItemsTable
from src.ui.panels.details_panel import DetailsPanel
from src.ui.panels.history_panel import HistoryPanel
from src.ui.dialogs.item_editor_dialog import ItemEditorDialog
from src.ui.dialogs.assign_user_dialog import AssignUserDialog
from src.ui.dialogs.move_location_dialog import MoveLocationDialog
from src.services.export_xlsx import export_inventory
from src.services.import_inventory import import_inventory_csv, InventoryImportError
from src.services.search_service import parse_query
from src.ui.utils import barcode_input
from src.ui.dialogs.entity_manager_dialog import EntityManagerDialog


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
        self._sub_types_repo = SQLiteSubTypesRepository(database)
        self._ip_repo = SQLiteIPAddressesRepository(database)

        # view-models
        self._items_vm = ItemsViewModel(self._items_repo)
        self._filters_vm = FiltersViewModel(
            types_repo=self._types_repo,
            locations_repo=self._locations_repo,
            users_repo=self._users_repo,
            groups_repo=self._groups_repo,
        )

        self._pending_select_id: Optional[int] = None
        self._pending_select_tag: Optional[str] = None
        self._toolbar = None

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
        screen = QGuiApplication.primaryScreen()
        if screen:
            rect = screen.availableGeometry()
            target_width = int(rect.width() * 0.8)
            target_height = int(rect.height() * 0.8)
            offset_x = rect.left() + int((rect.width() - target_width) / 2)
            offset_y = rect.top() + int((rect.height() - target_height) / 2)
            self.setGeometry(offset_x, offset_y, target_width, target_height)
            self.setMinimumSize(int(rect.width() * 0.6), int(rect.height() * 0.6))
            self.setMaximumSize(rect.size())
        self.setWindowFlag(Qt.WindowMaximizeButtonHint, True)
        self.setWindowFlag(Qt.WindowMinimizeButtonHint, True)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        self.show()

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        self.setWindowTitle("AssetForge — Inventory Control")
        self.resize(1360, 900)

        self._filters_panel = FiltersPanel(self)
        self._items_table = ItemsTable(self)
        self._details_panel = DetailsPanel(self)
        self._history_panel = HistoryPanel(self)

        tabs = QTabWidget(self)
        tabs.addTab(self._details_panel, "Overview")
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
        central.setContextMenuPolicy(Qt.CustomContextMenu)
        central.customContextMenuRequested.connect(self._show_general_context_menu)

        self._build_toolbar()
        self._build_menus()

        self._splitter = splitter
        self._toolbar.setVisible(False)
        self._splitter.widget(0).setVisible(False)

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("Main", self)
        toolbar.setMovable(False)
        self.addToolBar(Qt.TopToolBarArea, toolbar)
        self._toolbar = toolbar

        self._act_new = QAction("New Item", self)
        self._act_new.setShortcut("Ctrl+N")
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

        self._act_export = QAction("Export XLSX…", self)
        self._act_export.setShortcut("Ctrl+E")
        self._act_export.triggered.connect(self._on_export_inventory)
        toolbar.addAction(self._act_export)

        self._act_import = QAction("Import CSV…", self)
        self._act_import.setShortcut("Ctrl+I")
        self._act_import.triggered.connect(self._on_import_inventory)
        toolbar.addAction(self._act_import)

        self._act_backup = QAction("Backup Now", self)
        self._act_backup.triggered.connect(self._on_backup_now)
        toolbar.addAction(self._act_backup)

        toolbar.addSeparator()

        self._search_edit = QLineEdit(self)
        self._search_edit.setPlaceholderText("Scan or search…")
        self._search_edit.setClearButtonEnabled(True)
        self._search_edit.returnPressed.connect(self._on_search_committed)
        self._search_edit.installEventFilter(self)
        toolbar.addWidget(self._search_edit)

    def _build_menus(self) -> None:
        menubar = self.menuBar()
        file_menu = menubar.addMenu("&File")
        view_menu = menubar.addMenu("&View")
        data_menu = menubar.addMenu("&Data")
        help_menu = menubar.addMenu("&Help")

        file_menu.addAction(self._act_new)
        file_menu.addAction(self._act_import)
        file_menu.addAction(self._act_export)
        file_menu.addAction(self._act_backup)
        file_menu.addSeparator()
        self._act_quit = QAction("Quit", self)
        self._act_quit.setShortcut("Ctrl+Q")
        self._act_quit.triggered.connect(QApplication.quit)
        file_menu.addAction(self._act_quit)

        self._act_toggle_filters = QAction("Show Filters", self, checkable=True, checked=False)
        self._act_toggle_filters.triggered.connect(self._on_toggle_filters)
        view_menu.addAction(self._act_toggle_filters)

        self._act_toggle_toolbar = QAction("Show Toolbar", self, checkable=True, checked=False)
        self._act_toggle_toolbar.triggered.connect(self._on_toggle_toolbar)
        view_menu.addAction(self._act_toggle_toolbar)

        act_users = QAction("Manage Users…", self)
        act_users.triggered.connect(self._on_manage_users)
        data_menu.addAction(act_users)

        act_groups = QAction("Manage Groups…", self)
        act_groups.triggered.connect(self._on_manage_groups)
        data_menu.addAction(act_groups)

        act_locations = QAction("Manage Locations…", self)
        act_locations.triggered.connect(self._on_manage_locations)
        data_menu.addAction(act_locations)

        act_types = QAction("Manage Types…", self)
        act_types.triggered.connect(self._on_manage_types)
        data_menu.addAction(act_types)

        act_sub_types = QAction("Manage Sub Types…", self)
        act_sub_types.triggered.connect(self._on_manage_sub_types)
        data_menu.addAction(act_sub_types)

        act_about = QAction("About", self)
        act_about.triggered.connect(self._on_about)
        help_menu.addAction(act_about)

    def _connect_signals(self) -> None:
        self._filters_panel.filtersChanged.connect(self._on_filters_changed)
        self._filters_panel.clearRequested.connect(self._on_filters_cleared)
        self._items_table.itemSelected.connect(self._items_vm.set_selected_item)
        self._items_table.itemActivated.connect(self._on_edit_item)
        self._items_table.contextMenuRequested.connect(self._show_items_context_menu)
        self._items_vm.itemsChanged.connect(self._on_items_loaded)
        self._items_vm.selectedItemChanged.connect(self._on_item_details)
        self._filters_vm.optionsChanged.connect(self._on_filter_options)
        self._history_panel.auditRequested.connect(self._on_audit_note)

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
        raw = self._search_edit.text()
        scan = barcode_input.analyze(raw)

        if scan.get("asset_tag"):
            tag = scan["asset_tag"].upper()
            self._filters_panel.set_selected_filters(
                type_id=None, location_id=None, user_id=None, group_id=None, emit=False
            )
            self._items_vm.set_filters()
            self._pending_select_tag = tag
            self._items_vm.set_search(tag)
            return

        text, directives = parse_query(raw)

        # incorporate scanner-detected MAC if no explicit directive provided
        if scan.get("mac_address") and not any(k in directives for k in ("mac", "mac_address")):
            directives["mac"] = scan["mac_address"]

        filters_kwargs = {
            "type_id": self._resolve_type_id(directives.get("type")) if "type" in directives else None,
            "location_id": self._resolve_location_id(
                directives.get("loc") or directives.get("location")
            )
            if any(k in directives for k in ("loc", "location"))
            else None,
            "user_id": self._resolve_user_id(directives.get("user")) if "user" in directives else None,
            "group_id": self._resolve_group_id(directives.get("group")) if "group" in directives else None,
        }

        self._filters_panel.set_selected_filters(emit=False, **filters_kwargs)
        self._items_vm.set_filters(**filters_kwargs)

        if any(k in directives for k in ("tag", "asset", "asset_tag")):
            tag = directives.get("tag") or directives.get("asset") or directives.get("asset_tag")
            if tag:
                normalized = tag.upper()
                self._pending_select_tag = normalized
                self._items_vm.set_search(normalized)
                return

        if any(k in directives for k in ("mac", "mac_address")):
            text = directives.get("mac") or directives.get("mac_address")

        self._pending_select_tag = None
        self._items_vm.set_search(text)

    def _on_items_loaded(self, items: list[ItemRecord]) -> None:
        self._items_table.set_rows(items)
        if self._pending_select_id is not None:
            self._items_table.select_item(self._pending_select_id)
            self._items_vm.set_selected_item(self._pending_select_id)
            self._pending_select_id = None
        else:
            current = self._items_vm.selected_item_id()
            if current:
                self._items_table.select_item(current)
        if self._pending_select_tag:
            tag_upper = self._pending_select_tag
            for record in items:
                if str(record.asset_tag or "").upper() == tag_upper:
                    self._items_table.select_item(record.id)
                    self._items_vm.set_selected_item(record.id)
                    break
            self._pending_select_tag = None
        self._update_edit_action()

    def _on_item_details(self, item: dict) -> None:
        self._details_panel.set_item(item)
        if item:
            updates_raw = self._items_repo.history_for_item(item["id"], limit=100)
        else:
            updates_raw = []
        self._history_panel.set_entries(self._decorate_updates(updates_raw))
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
            sub_types=self._sub_types_repo.list_sub_types(order_by="name"),
            ip_addresses=self._available_ip_addresses(),
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
            sub_types=self._sub_types_repo.list_sub_types(order_by="name"),
            ip_addresses=self._available_ip_addresses(current.get("ip_address")),
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

    def _refresh_selected_item(self, item_id: int) -> None:
        details = self._items_repo.get_details(item_id) or {}
        self._details_panel.set_item(details)
        updates_raw = self._items_repo.history_for_item(item_id, limit=100)
        self._history_panel.set_entries(self._decorate_updates(updates_raw))

    def _refresh_filter_options(self) -> None:
        selected = self._filters_panel.selected_filters()
        options = self._filters_vm.refresh()
        self._filters_panel.populate(
            types=options["types"],
            locations=options["locations"],
            users=options["users"],
            groups=options["groups"],
        )
        self._filters_panel.set_selected_filters(emit=False, **selected)
        self._items_vm.set_filters(**selected)
        self._items_vm.refresh()

    def _available_ip_addresses(self, current: Optional[str] = None) -> list[str]:
        return self._ip_repo.list_available(include=current)

    def changeEvent(self, event: QEvent) -> None:
        if event.type() == QEvent.WindowStateChange:
            if self.isMinimized():
                super().changeEvent(event)
                return
        super().changeEvent(event)

    # ------------------------------------------------------------------
    def _show_items_context_menu(self, item_id: Optional[int], global_pos) -> None:
        if item_id is None:
            self._show_general_context_menu(global_pos)
            return

        self._items_vm.set_selected_item(item_id)
        item = self._items_repo.get(item_id) or {}
        archived = bool(item.get("archived"))

        menu = QMenu(self)
        act_edit = menu.addAction("Edit Item")
        act_note = menu.addAction("Add Audit Note…")
        act_archive = menu.addAction("Archive Item")
        act_archive.setEnabled(not archived)
        act_export = menu.addAction("Export Details…")

        chosen = menu.exec(global_pos)
        if chosen is None:
            return
        if chosen is act_edit:
            self._on_edit_item()
        elif chosen is act_note:
            self._on_audit_note()
        elif chosen is act_archive and not archived:
            self._on_archive_item()
        elif chosen is act_export:
            self._on_export_item_details()

    def _show_general_context_menu(self, global_pos) -> None:
        menu = QMenu(self)
        act_new = menu.addAction("Add Item…")

        toolbar_visible = self._toolbar.isVisible() if self._toolbar else False
        act_toolbar = menu.addAction("Hide Toolbar" if toolbar_visible else "Show Toolbar")

        filters_visible = self._splitter.widget(0).isVisible()
        act_filters = menu.addAction("Hide Filters" if filters_visible else "Show Filters")

        menu.addSeparator()
        act_users = menu.addAction("Manage Users…")
        act_groups = menu.addAction("Manage Groups…")
        act_locations = menu.addAction("Manage Locations…")
        act_sub_types = menu.addAction("Manage Sub Types…")

        chosen = menu.exec(global_pos)
        if chosen is None:
            return
        if chosen is act_new:
            self._on_new_item()
            return
        if chosen is act_toolbar and self._toolbar:
            new_state = not toolbar_visible
            self._act_toggle_toolbar.blockSignals(True)
            self._act_toggle_toolbar.setChecked(new_state)
            self._act_toggle_toolbar.blockSignals(False)
            self._on_toggle_toolbar(new_state)
            return
        if chosen is act_filters:
            new_state = not filters_visible
            self._act_toggle_filters.blockSignals(True)
            self._act_toggle_filters.setChecked(new_state)
            self._act_toggle_filters.blockSignals(False)
            self._on_toggle_filters(new_state)
            return
        if chosen is act_users:
            self._on_manage_users()
        elif chosen is act_groups:
            self._on_manage_groups()
        elif chosen is act_locations:
            self._on_manage_locations()
        elif chosen is act_sub_types:
            self._on_manage_sub_types()

    def _on_toggle_filters(self, checked: bool) -> None:
        self._splitter.widget(0).setVisible(checked)
        sizes = self._splitter.sizes()
        if not checked:
            self._splitter.setSizes([0, sizes[1] + sizes[0] // 2, sizes[2]])
        else:
            if sizes[0] == 0:
                self._splitter.setSizes([200, sizes[1], sizes[2]])

    def _on_toggle_toolbar(self, checked: bool) -> None:
        if self._toolbar:
            self._toolbar.setVisible(checked)

    def _on_audit_note(self) -> None:
        item_id = self._items_vm.selected_item_id()
        if item_id is None:
            return
        text, ok = QInputDialog.getMultiLineText(
            self,
            "Audit note",
            "Enter audit note:",
        )
        if not ok or not text.strip():
            return
        try:
            self._items_repo.add_audit_note(item_id, text.strip())
        except Exception as exc:
            QMessageBox.critical(self, "Audit note failed", str(exc))
            return
        self._refresh_selected_item(item_id)
        self.statusBar().showMessage("Audit note added", 3000)

    def _on_archive_item(self) -> None:
        item_id = self._items_vm.selected_item_id()
        if item_id is None:
            return
        record = self._items_repo.get(item_id) or {}
        tag = record.get("asset_tag", f"Item {item_id}")
        confirm = QMessageBox.question(
            self,
            "Archive Item",
            f"Archive {tag}?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return
        try:
            self._items_repo.archive(item_id, note="archived via UI")
        except Exception as exc:
            QMessageBox.critical(self, "Archive failed", str(exc))
            return
        self._after_item_mutation(item_id, "Item archived")

    def _on_export_item_details(self) -> None:
        item_id = self._items_vm.selected_item_id()
        if item_id is None:
            return
        details = self._items_repo.get_details(item_id)
        if not details:
            return
        history = self._items_repo.history_for_item(item_id, limit=100)
        payload = {"item": details, "history": history}
        default_name = f"{details.get('asset_tag', 'item')}_details.json"
        default_path = (EXPORT_DIR / default_name).resolve()
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export Item Details",
            str(default_path),
            "JSON Files (*.json)",
        )
        if not filename:
            return
        try:
            output_path = Path(filename)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except Exception as exc:
            QMessageBox.critical(self, "Export failed", str(exc))
            return
        self.statusBar().showMessage(f"Exported item details to {output_path}", 5000)

    def _decorate_updates(self, updates: list[dict]) -> list[dict]:
        decorated = []
        for entry in updates:
            changes: list[str] = []
            before = {}
            after = {}
            if entry.get("snapshot_before_json"):
                try:
                    before = json.loads(entry["snapshot_before_json"]) or {}
                except json.JSONDecodeError:
                    before = {}
            if entry.get("snapshot_after_json"):
                try:
                    after = json.loads(entry["snapshot_after_json"]) or {}
                except json.JSONDecodeError:
                    after = {}
            keys = set(before) | set(after)
            exclude = {"updated_at_utc", "created_at_utc"}
            for key in sorted(keys):
                if key in exclude:
                    continue
                old = before.get(key)
                new = after.get(key)
                if old == new:
                    continue
                changes.append(f"{key}: {self._format_value(old)} → {self._format_value(new)}")
            if not changes and entry.get("changed_fields"):
                changes.append(str(entry.get("changed_fields")))
            decorated.append({
                "created_at": self._format_display_time(entry.get("created_at_utc")),
                "reason": entry.get("reason", ""),
                "note": entry.get("note", ""),
                "changes": "\n".join(changes),
            })
        return decorated

    def _format_display_time(self, value: Optional[str]) -> str:
        if not value:
            return ""
        try:
            if value.endswith('Z'):
                value = value[:-1]
            timestamp = dt.datetime.fromisoformat(value)
        except Exception:
            return value
        local = timestamp.astimezone()
        relative = self._relative_time(local)
        return f"{local.strftime('%Y-%m-%d %H:%M:%S %Z')} ({relative})"

    @staticmethod
    def _relative_time(when: dt.datetime) -> str:
        now = dt.datetime.now(when.tzinfo)
        delta = now - when
        seconds = int(delta.total_seconds())
        if seconds < 0:
            seconds = abs(seconds)
            suffix = 'from now'
        else:
            suffix = 'ago'
        if seconds < 60:
            return 'just now' if suffix == 'ago' else 'in <1m'
        if seconds < 3600:
            return f"{seconds // 60}m {suffix}"
        if seconds < 86400:
            return f"{seconds // 3600}h {suffix}"
        return f"{seconds // 86400}d {suffix}"

    @staticmethod
    def _format_value(value) -> str:
        if value in (None, ""):
            return "—"
        if isinstance(value, bool):
            return "true" if value else "false"
        return str(value)

    def _resolve_type_id(self, token: Optional[str]) -> Optional[int]:
        if not token:
            return None
        token = token.strip()
        if not token:
            return None
        rec = self._types_repo.find_by_code(token.upper())
        if not rec:
            rec = self._types_repo.find_by_name(token)
        return int(rec["id"]) if rec else None

    def _resolve_location_id(self, token: Optional[str]) -> Optional[int]:
        if not token:
            return None
        rec = self._locations_repo.find_by_name(token)
        return int(rec["id"]) if rec else None

    def _resolve_user_id(self, token: Optional[str]) -> Optional[int]:
        if not token:
            return None
        rec = self._users_repo.find_by_name(token)
        return int(rec["id"]) if rec else None

    def _resolve_group_id(self, token: Optional[str]) -> Optional[int]:
        if not token:
            return None
        rec = self._groups_repo.find_by_name(token)
        return int(rec["id"]) if rec else None

    def _on_export_inventory(self) -> None:
        default_name = f"inventory-{datetime.now().strftime('%Y%m%d-%H%M')}.xlsx"
        default_path = str((EXPORT_DIR / default_name).resolve())
        path_str, _ = QFileDialog.getSaveFileName(
            self,
            "Export inventory",
            default_path,
            "Excel Workbook (*.xlsx)",
        )
        if not path_str:
            return
        path = Path(path_str)
        try:
            items = self._items_repo.list_items(order_by="hi.asset_tag")
            export_inventory(path, items=items)
        except Exception as exc:
            QMessageBox.critical(self, "Export failed", str(exc))
            return
        self.statusBar().showMessage(f"Exported inventory to {path}", 5000)

    def _on_import_inventory(self) -> None:
        path_str, _ = QFileDialog.getOpenFileName(
            self,
            "Import inventory CSV",
            str(Path.cwd()),
            "CSV Files (*.csv);;All Files (*)",
        )
        if not path_str:
            return
        path = Path(path_str)
        try:
            created, notes = import_inventory_csv(
                path,
                types_repo=self._types_repo,
                locations_repo=self._locations_repo,
                users_repo=self._users_repo,
                groups_repo=self._groups_repo,
                ip_repo=self._ip_repo,
                sub_types_repo=self._sub_types_repo,
                items_repo=self._items_repo,
            )
        except InventoryImportError as exc:
            QMessageBox.critical(self, "Import failed", str(exc))
            return
        except Exception as exc:
            QMessageBox.critical(self, "Import failed", str(exc))
            return

        summary = f"Imported {created} items."
        if notes:
            summary += f" {len(notes)} rows skipped."
            QMessageBox.information(
                self,
                "Import summary",
                summary + "\n\n" + "\n".join(notes[:10]),
            )
        else:
            self.statusBar().showMessage(summary, 5000)
        self._refresh_filter_options()

    def _on_backup_now(self) -> None:
        script = Path(__file__).resolve().parents[2] / "scripts" / "backup.sh"
        if not script.exists():
            QMessageBox.warning(self, "Backup", "scripts/backup.sh not found.")
            return
        try:
            result = subprocess.run(
                ["bash", str(script)],
                cwd=Path(__file__).resolve().parents[2],
                capture_output=True,
                text=True,
                check=True,
            )
        except subprocess.CalledProcessError as exc:
            QMessageBox.critical(
                self,
                "Backup failed",
                exc.stderr or exc.stdout or str(exc),
            )
            return
        message = result.stdout.strip() or "Backup completed"
        self.statusBar().showMessage(message, 5000)

    # ----- reference data managers -----------------------------------
    def _on_manage_users(self) -> None:
        dialog = EntityManagerDialog(
            title="Manage Users",
            fields=[
                {"key": "name", "label": "Name", "required": True},
                {"key": "email", "label": "Email", "required": False},
            ],
            list_func=lambda: self._users_repo.list_users(order_by="name"),
            create_func=lambda data: self._users_repo.create(
                name=data["name"], email=data["email"] or None
            ),
            update_func=lambda rid, data: self._users_repo.update(
                rid,
                name=data["name"],
                email=data["email"] or None,
            ),
            delete_func=lambda rid: self._users_repo.delete(rid),
            display_func=lambda rec: f"{rec.get('name','')} {rec.get('email','') or ''}".strip(),
            parent=self,
        )
        dialog.exec()
        self._refresh_filter_options()

    def _on_about(self) -> None:
        QMessageBox.information(
            self,
            "About AssetForge",
            "AssetForge Inventory Control\nRevision 1.2.0 - Distro",
        )

    def _on_manage_groups(self) -> None:
        dialog = EntityManagerDialog(
            title="Manage Groups",
            fields=[{"key": "name", "label": "Name", "required": True}],
            list_func=lambda: self._groups_repo.list_groups(order_by="name"),
            create_func=lambda data: self._groups_repo.create(name=data["name"]),
            update_func=lambda rid, data: self._groups_repo.rename(rid, data["name"]),
            delete_func=lambda rid: self._groups_repo.delete(rid),
            display_func=lambda rec: rec.get("name", ""),
            parent=self,
        )
        dialog.exec()
        self._refresh_filter_options()

    def _on_manage_locations(self) -> None:
        dialog = EntityManagerDialog(
            title="Manage Locations",
            fields=[{"key": "name", "label": "Name", "required": True}],
            list_func=lambda: self._locations_repo.list_locations(order_by="name"),
            create_func=lambda data: self._locations_repo.create(name=data["name"]),
            update_func=lambda rid, data: self._locations_repo.rename(rid, data["name"]),
            delete_func=lambda rid: self._locations_repo.delete(rid),
            display_func=lambda rec: rec.get("name", ""),
            parent=self,
        )
        dialog.exec()
        self._refresh_filter_options()

    def _on_manage_types(self) -> None:
        dialog = EntityManagerDialog(
            title="Manage Types",
            fields=[
                {"key": "name", "label": "Name", "required": True},
                {"key": "code", "label": "Code", "required": True},
            ],
            list_func=lambda: self._types_repo.list_types(order_by="name"),
            create_func=lambda data: self._types_repo.create(
                name=data["name"], code=data["code"].upper()
            ),
            update_func=lambda rid, data: self._types_repo.update(
                rid,
                name=data["name"],
                code=data["code"].upper(),
            ),
            delete_func=lambda rid: self._types_repo.delete(rid),
            display_func=lambda rec: f"{rec.get('name','')} ({rec.get('code','')})",
            parent=self,
        )
        dialog.exec()
        self._refresh_filter_options()

    def _on_manage_sub_types(self) -> None:
        dialog = EntityManagerDialog(
            title="Manage Sub Types",
            fields=[{"key": "name", "label": "Name", "required": True}],
            list_func=lambda: self._sub_types_repo.list_sub_types(order_by="name"),
            create_func=lambda data: self._sub_types_repo.create(name=data["name"]),
            update_func=lambda rid, data: self._sub_types_repo.update(rid, name=data["name"]),
            delete_func=lambda rid: self._sub_types_repo.delete(rid),
            display_func=lambda rec: rec.get("name", ""),
            parent=self,
        )
        dialog.exec()

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
