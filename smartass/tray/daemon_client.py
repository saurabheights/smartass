# smartass/tray/daemon_client.py
"""QtDBus-based proxy wrapper around ai.talonic.Smartass.Core.

Exposes Qt signals for tabs to bind to. Methods are synchronous wrappers
around blocking QDBus calls (acceptable — tray is GUI-event driven, calls
are fast).
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from PySide6.QtCore import QObject, Signal
from PySide6.QtDBus import QDBusConnection, QDBusInterface, QDBusMessage

from smartass.core import dbus_names

log = logging.getLogger(__name__)


class DaemonClient(QObject):
    plugin_enabled = Signal(str)
    plugin_disabled = Signal(str)
    settings_changed = Signal(str, dict)
    plugin_state_updated = Signal(str, dict)
    daemon_online = Signal()
    daemon_offline = Signal()

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._bus = QDBusConnection.sessionBus()
        if not self._bus.isConnected():
            raise RuntimeError("not connected to session bus")
        self._iface: Optional[QDBusInterface] = None
        self._connect_signals()
        self._connect_iface()

    def _connect_iface(self) -> None:
        self._iface = QDBusInterface(
            dbus_names.SERVICE,
            dbus_names.CORE_PATH,
            dbus_names.CORE_IFACE,
            self._bus,
        )
        if not self._iface.isValid():
            self._iface = None
            self.daemon_offline.emit()
        else:
            self.daemon_online.emit()

    def _connect_signals(self) -> None:
        # PySide6 QDBusConnection.connect requires 6 args (service, path,
        # interface, name, receiver, slot) with a Qt-style SLOT. Bridging
        # generic Python callables is non-trivial, and MVP tabs already
        # refresh explicitly on user action + periodic polling. Skip the
        # bridge for now; daemon-side events won't auto-propagate to the
        # tray, but user-driven changes (Enable/Disable button, Save on
        # form) always trigger an explicit refresh downstream.
        pass

    # --- sync RPC wrappers ---

    def _call(self, method: str, *args: Any) -> Any:
        if self._iface is None:
            self._connect_iface()
        if self._iface is None:
            raise RuntimeError("daemon not reachable on session bus")
        reply = self._iface.call(method, *args)
        if reply.type() == QDBusMessage.ErrorMessage:
            raise RuntimeError(reply.errorMessage())
        return reply.arguments()

    def ping(self) -> str:
        return self._call("Ping")[0]

    def list_plugins(self) -> list[tuple[str, str, str, str, bool, bool]]:
        return [tuple(r) for r in self._call("ListPlugins")[0]]

    def enable_plugin(self, plugin_id: str) -> None:
        self._call("EnablePlugin", plugin_id)

    def disable_plugin(self, plugin_id: str) -> None:
        self._call("DisablePlugin", plugin_id)

    def get_config(self, plugin_id: str) -> dict[str, Any]:
        return dict(self._call("GetConfig", plugin_id)[0])

    def set_config(self, plugin_id: str, values: dict[str, Any]) -> None:
        self._call("SetConfig", plugin_id, values)

    def get_settings_schema(self, plugin_id: str) -> dict[str, Any]:
        raw = self._call("GetSettingsSchema", plugin_id)[0]
        return json.loads(raw)

    def export_all(self) -> str:
        return self._call("ExportAll")[0]

    def import_all(self, blob: str, strategy: str = "merge") -> None:
        self._call("ImportAll", blob, strategy)
