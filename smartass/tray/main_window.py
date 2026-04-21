# smartass/tray/main_window.py
"""Main window with QTabWidget — Settings tab always-on + one per enabled plugin."""

from __future__ import annotations

import importlib.util
import logging
import sys
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMainWindow, QTabWidget, QWidget

from smartass.core import paths as _paths
from smartass.core.manifest import load_manifest
from smartass.core.plugin_interface import PluginContext, PluginInterface
from smartass.tray.daemon_client import DaemonClient
from smartass.tray.settings_tab import SettingsTab

log = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(self, client: DaemonClient) -> None:
        super().__init__()
        self.setWindowTitle("Smartass")
        self._client = client
        self._tabs = QTabWidget()
        self.setCentralWidget(self._tabs)
        self.resize(720, 520)

        self._settings_tab = SettingsTab(self._client, parent=self)
        self._tabs.addTab(self._settings_tab, "Settings")

        self._plugin_tabs: dict[str, QWidget] = {}
        self._rebuild_plugin_tabs()

        client.plugin_enabled.connect(self._on_plugin_enabled)
        client.plugin_disabled.connect(self._on_plugin_disabled)

    def _enabled_ids(self) -> list[str]:
        return [r[0] for r in self._client.list_plugins() if r[5]]

    def _rebuild_plugin_tabs(self) -> None:
        for pid in list(self._plugin_tabs):
            self._remove_plugin_tab(pid)
        for pid in self._enabled_ids():
            self._add_plugin_tab(pid)

    def _add_plugin_tab(self, plugin_id: str) -> None:
        if plugin_id in self._plugin_tabs:
            return
        try:
            widget = self._build_plugin_tab(plugin_id)
        except Exception:
            log.exception("failed to build tab for %s", plugin_id)
            return
        self._plugin_tabs[plugin_id] = widget
        self._tabs.addTab(widget, plugin_id.capitalize())

    def _remove_plugin_tab(self, plugin_id: str) -> None:
        widget = self._plugin_tabs.pop(plugin_id, None)
        if widget is None:
            return
        idx = self._tabs.indexOf(widget)
        if idx >= 0:
            self._tabs.removeTab(idx)
        widget.deleteLater()

    def _on_plugin_enabled(self, plugin_id: str) -> None:
        self._add_plugin_tab(plugin_id)

    def _on_plugin_disabled(self, plugin_id: str) -> None:
        self._remove_plugin_tab(plugin_id)

    def _build_plugin_tab(self, plugin_id: str) -> QWidget:
        plugin_dir = self._find_plugin_dir(plugin_id)
        if plugin_dir is None:
            raise RuntimeError(f"plugin '{plugin_id}' not installed")
        manifest = load_manifest(plugin_dir)
        module_name = f"smartass_plugin_{plugin_id}"
        module_path = plugin_dir / f"{manifest.entry_module}.py"
        spec = importlib.util.spec_from_file_location(
            module_name, module_path, submodule_search_locations=[str(plugin_dir)]
        )
        if spec is None or spec.loader is None:
            raise RuntimeError(f"cannot import plugin {plugin_id}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        cls = getattr(module, manifest.entry_class)
        if not issubclass(cls, PluginInterface):
            raise RuntimeError(f"plugin {plugin_id} is not a PluginInterface")

        ctx = PluginContext(
            config=None,
            data_dir=plugin_dir,
            log=logging.getLogger(f"smartass.plugins.{plugin_id}"),
            http=None,
            bus=None,
            signals=None,
            permissions=manifest.permissions,
        )
        instance = cls(ctx)
        return instance.build_tab(self)

    def _find_plugin_dir(self, plugin_id: str) -> Optional[Path]:
        for root in _paths.plugin_roots():
            candidate = root / plugin_id
            if (candidate / "manifest.toml").is_file():
                return candidate
        dev = Path(__file__).resolve().parent.parent / "plugins" / plugin_id
        if (dev / "manifest.toml").is_file():
            return dev
        return None
