# smartass/tray/settings_tab.py
"""Settings tab: plugin list, enable/disable, per-plugin schema form, import/export."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from smartass.tray.daemon_client import DaemonClient
from smartass.tray.schema_form import SchemaForm


class SettingsTab(QWidget):
    plugin_enabled_changed = Signal(str, bool)

    def __init__(self, client: DaemonClient, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._client = client

        root = QHBoxLayout(self)

        left = QVBoxLayout()
        self._list = QListWidget()
        self._list.itemClicked.connect(self._on_pick)
        left.addWidget(self._list)

        self._enable_btn = QPushButton("Enable")
        self._enable_btn.clicked.connect(self._toggle_selected)
        left.addWidget(self._enable_btn)

        export_btn = QPushButton("Export…")
        export_btn.clicked.connect(self._do_export)
        import_btn = QPushButton("Import…")
        import_btn.clicked.connect(self._do_import)
        left.addWidget(export_btn)
        left.addWidget(import_btn)
        root.addLayout(left, stretch=1)

        self._stack = QStackedWidget()
        root.addWidget(self._stack, stretch=3)

        self.refresh()
        client.plugin_enabled.connect(lambda pid: self.refresh())
        client.plugin_disabled.connect(lambda pid: self.refresh())

    def refresh(self) -> None:
        self._list.clear()
        try:
            rows = self._client.list_plugins()
        except Exception:
            QMessageBox.warning(self, "Smartass", "Daemon not reachable.")
            return
        for (pid, name, version, description, installed, enabled) in rows:
            item = QListWidgetItem(f"{'✓ ' if enabled else '  '}{name} ({version})")
            item.setData(Qt.ItemDataRole.UserRole, pid)
            item.setToolTip(description)
            self._list.addItem(item)

    def _selected_id(self) -> Optional[str]:
        item = self._list.currentItem()
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def _on_pick(self, item: QListWidgetItem) -> None:
        pid = item.data(Qt.ItemDataRole.UserRole)
        schema = self._client.get_settings_schema(pid)
        values = self._client.get_config(pid)
        form = SchemaForm(schema, values, on_save=lambda v, p=pid: self._save(p, v))
        while self._stack.count():
            w = self._stack.widget(0)
            self._stack.removeWidget(w)
            w.deleteLater()
        self._stack.addWidget(form)
        self._stack.setCurrentWidget(form)
        self._refresh_enable_button(pid)

    def _save(self, pid: str, values: dict) -> None:
        try:
            self._client.set_config(pid, values)
            QMessageBox.information(self, "Smartass", "Settings saved.")
        except Exception as e:
            QMessageBox.warning(self, "Smartass", f"Save failed: {e}")

    def _refresh_enable_button(self, pid: str) -> None:
        rows = {r[0]: r for r in self._client.list_plugins()}
        is_enabled = rows[pid][5] if pid in rows else False
        self._enable_btn.setText("Disable" if is_enabled else "Enable")

    def _toggle_selected(self) -> None:
        pid = self._selected_id()
        if pid is None:
            return
        rows = {r[0]: r for r in self._client.list_plugins()}
        is_enabled = rows[pid][5]
        try:
            if is_enabled:
                self._client.disable_plugin(pid)
            else:
                self._client.enable_plugin(pid)
            self.plugin_enabled_changed.emit(pid, not is_enabled)
            self.refresh()
            self._refresh_enable_button(pid)
        except Exception as e:
            QMessageBox.warning(self, "Smartass", f"Toggle failed: {e}")

    def _do_export(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Export settings", "smartass-export.toml", "TOML (*.toml)"
        )
        if not path:
            return
        blob = self._client.export_all()
        Path(path).write_text(blob, encoding="utf-8")
        QMessageBox.information(self, "Smartass", f"Exported to {path}")

    def _do_import(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Import settings", "", "TOML (*.toml)"
        )
        if not path:
            return
        blob = Path(path).read_text(encoding="utf-8")
        try:
            self._client.import_all(blob, strategy="merge")
            QMessageBox.information(self, "Smartass", "Import complete.")
            self.refresh()
        except Exception as e:
            QMessageBox.warning(self, "Smartass", f"Import failed: {e}")
