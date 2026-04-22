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
    def GetState(self) -> "s":  # type: ignore[name-defined]
        # JSON-encoded {"snapshot": ..., "stale": bool}. a{sv} doesn't
        # unmarshall cleanly on PySide6's QtDBus client; keep the wire
        # format as a single string for both client implementations.
        snap = getattr(self._instance, "last_snapshot", lambda: None)()
        stale = bool(getattr(self._instance, "is_stale", lambda: False)())
        return json.dumps({"snapshot": snap, "stale": stale})

    @method()
    async def RefreshNow(self) -> None:
        fn = getattr(self._instance, "refresh", None)
        if fn is None:
            return
        import inspect as _inspect
        if _inspect.iscoroutinefunction(fn):
            await fn()
        else:
            fn()
