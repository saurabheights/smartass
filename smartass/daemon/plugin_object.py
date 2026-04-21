# smartass/daemon/plugin_object.py
"""Per-plugin D-Bus object exposing ai.talonic.Smartass.Plugin."""

import json
from typing import Any

from dbus_next.service import ServiceInterface, method

from smartass.core import dbus_names


class PluginObject(ServiceInterface):
    def __init__(self, plugin_id: str, instance: Any) -> None:
        super().__init__(dbus_names.PLUGIN_IFACE)
        self._plugin_id = plugin_id
        self._instance = instance

    @method()
    def GetState(self) -> "a{sv}":  # type: ignore[name-defined]
        from dbus_next import Variant

        state: dict[str, Any] = {}
        # Convention: plugins may expose last_snapshot() and is_stale().
        # For the MVP Weather plugin, that's exactly what we need.
        snap = getattr(self._instance, "last_snapshot", lambda: None)()
        state["snapshot_json"] = Variant("s", json.dumps(snap) if snap is not None else "null")
        state["stale"] = Variant("b", bool(getattr(self._instance, "is_stale", lambda: False)()))
        return state
