"""D-Bus Core service (ai.talonic.Smartass.Core)."""

import json
import logging
import sys
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # type: ignore[import-not-found]

import tomli_w
from dbus_next.service import ServiceInterface, method, signal

from smartass.core import dbus_names
from smartass.core.config import ConfigStore, InvalidConfig
from smartass.daemon.plugin_manager import PluginManager

log = logging.getLogger(__name__)


class CoreService(ServiceInterface):
    """Exports ai.talonic.Smartass.Core on /ai/talonic/Smartass."""

    def __init__(self, pm: PluginManager, store: ConfigStore) -> None:
        super().__init__(dbus_names.CORE_IFACE)
        self._pm = pm
        self._store = store

    # --- Methods ---

    @method()
    def Ping(self) -> "s":  # type: ignore[name-defined]
        from smartass import __version__

        return f"pong {__version__}"

    @method()
    def ListPlugins(self) -> "s":  # type: ignore[name-defined]
        # JSON-encoded array of objects. Complex struct arrays don't
        # unmarshall cleanly through PySide6 QtDBus, so use the same
        # JSON-string strategy we already use for schemas.
        rows: list[dict[str, Any]] = []
        for dp in self._pm.discover():
            m = dp.manifest
            rows.append(
                {
                    "id": m.id,
                    "name": m.name,
                    "version": m.version,
                    "description": m.description,
                    "installed": True,
                    "enabled": self._store.is_enabled(m.id),
                }
            )
        return json.dumps(rows)

    @method()
    async def EnablePlugin(self, plugin_id: "s") -> None:  # type: ignore[name-defined]
        await self._pm.enable(plugin_id)
        self.PluginEnabled(plugin_id)

    @method()
    async def DisablePlugin(self, plugin_id: "s") -> None:  # type: ignore[name-defined]
        await self._pm.disable(plugin_id)
        self.PluginDisabled(plugin_id)

    @method()
    def GetConfig(self, plugin_id: "s") -> "s":  # type: ignore[name-defined]
        # Same JSON-string strategy — avoids QtDBus a{sv} unmarshal quirks.
        return json.dumps(self._store.get_plugin_values(plugin_id))

    @method()
    async def SetConfig(
        self,
        plugin_id: "s",  # type: ignore[name-defined]
        values_json: "s",  # type: ignore[name-defined]
    ) -> None:
        schema = _resolve_schema(self._pm, plugin_id)
        try:
            values = json.loads(values_json)
            self._store.set_plugin_values(plugin_id, values, schema)
        except InvalidConfig as e:
            raise ValueError(str(e)) from e
        self._store.save()
        new_values = self._store.get_plugin_values(plugin_id)

        # Notify the running plugin so it can react immediately.
        if self._pm.is_running(plugin_id):
            running = self._pm._running[plugin_id].instance  # noqa: SLF001
            try:
                running.on_settings_changed(new_values)
            except Exception:
                log.exception("plugin %s on_settings_changed raised", plugin_id)
            # If the plugin exposes a refresh() coroutine, trigger one immediately.
            refresh_fn = getattr(running, "refresh", None)
            if callable(refresh_fn):
                import asyncio as _asyncio
                import inspect as _inspect
                if _inspect.iscoroutinefunction(refresh_fn):
                    _asyncio.create_task(refresh_fn())

        # Signal still uses variant dict — fine; signals don't round-trip
        # through PySide6 client-side unmarshalling (we disabled that bridge).
        self.SettingsChanged(plugin_id, _to_variant_dict(new_values))

    @method()
    def GetSettingsSchema(self, plugin_id: "s") -> "s":  # type: ignore[name-defined]
        schema = _resolve_schema(self._pm, plugin_id)
        return json.dumps(schema.to_dict())

    @method()
    def ExportAll(self) -> "s":  # type: ignore[name-defined]
        from datetime import datetime, timezone

        from smartass import __version__

        blob: dict[str, Any] = {
            "meta": {
                "exported_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "smartass_version": __version__,
                "config_schema": self._store.data["smartass"]["version"],
            },
            "config": self._store.data,
            "plugin_state": {},
        }
        for pid in self._pm.running_ids():
            inst = self._pm._running[pid].instance  # noqa: SLF001
            state = inst.export_state() or {}
            if state:
                blob["plugin_state"][pid] = state
        return tomli_w.dumps(blob)

    @method()
    async def ImportAll(
        self,
        toml_blob: "s",  # type: ignore[name-defined]
        strategy: "s",  # type: ignore[name-defined]
    ) -> None:
        if strategy not in ("replace", "merge"):
            raise ValueError("strategy must be 'replace' or 'merge'")
        data = tomllib.loads(toml_blob)
        imported_config = data.get("config", {})

        if strategy == "replace":
            self._store._data = imported_config or self._store.data  # noqa: SLF001
        else:
            merged = dict(self._store.data)
            smart_new = imported_config.get("smartass", {})
            merged["smartass"].update(smart_new)
            plugins_new = imported_config.get("plugins", {})
            merged.setdefault("plugins", {})
            for k, v in plugins_new.items():
                merged["plugins"].setdefault(k, {}).update(v)
            self._store._data = merged  # noqa: SLF001
        self._store.save()

        for pid in self._pm.running_ids():
            await self._pm.disable(pid)
        for pid in self._store.data["smartass"]["enabled_plugins"]:
            await self._pm.enable(pid)

        for pid, state in (data.get("plugin_state") or {}).items():
            if self._pm.is_running(pid):
                self._pm._running[pid].instance.import_state(state)  # noqa: SLF001

    @method()
    async def ReloadDaemon(self) -> None:
        await self._pm.shutdown()
        self._pm.discover()
        await self._pm.boot()

    @method()
    def InstallPlugin(self, source_path: "s") -> "s":  # type: ignore[name-defined]
        raise NotImplementedError(
            "InstallPlugin not yet supported; drop a dir into ~/.local/share/smartass/plugins/"
        )

    @method()
    def UninstallPlugin(self, plugin_id: "s") -> None:  # type: ignore[name-defined]
        raise NotImplementedError("UninstallPlugin not yet supported")

    # --- Signals ---

    @signal()
    def PluginEnabled(self, plugin_id: "s") -> "s":  # type: ignore[name-defined]
        return plugin_id

    @signal()
    def PluginDisabled(self, plugin_id: "s") -> "s":  # type: ignore[name-defined]
        return plugin_id

    @signal()
    def PluginInstalled(self, plugin_id: "s") -> "s":  # type: ignore[name-defined]
        return plugin_id

    @signal()
    def PluginUninstalled(self, plugin_id: "s") -> "s":  # type: ignore[name-defined]
        return plugin_id

    @signal()
    def SettingsChanged(
        self, plugin_id: "s", values: "a{sv}"  # type: ignore[name-defined]
    ) -> "(sa{sv})":  # type: ignore[name-defined]
        return [plugin_id, values]

    @signal()
    def PluginStateUpdated(
        self, plugin_id: "s", payload: "a{sv}"  # type: ignore[name-defined]
    ) -> "(sa{sv})":  # type: ignore[name-defined]
        return [plugin_id, payload]


# --- helpers ---


def _resolve_schema(pm: PluginManager, plugin_id: str):
    dp = pm._discovered.get(plugin_id)  # noqa: SLF001
    if dp is None:
        raise ValueError(f"unknown plugin: {plugin_id}")
    cls = pm.load_plugin_class(dp)
    from smartass.core.plugin_interface import PluginContext

    dummy_ctx = PluginContext(
        config=None,
        data_dir=dp.manifest.root,
        log=log,
        http=None,
        bus=None,
        signals=None,
        permissions=dp.manifest.permissions,
    )
    return cls(dummy_ctx).settings_schema()


def _to_variant_dict(d: dict[str, Any]) -> dict[str, Any]:
    from dbus_next import Variant

    out: dict[str, Any] = {}
    for k, v in d.items():
        sig = _dbus_sig(v)
        out[k] = Variant(sig, v)
    return out


def _from_variant_dict(d: dict[str, Any]) -> dict[str, Any]:
    return {k: (v.value if hasattr(v, "value") else v) for k, v in d.items()}


def _dbus_sig(v: Any) -> str:
    if isinstance(v, bool):
        return "b"
    if isinstance(v, int):
        return "i"
    if isinstance(v, float):
        return "d"
    if isinstance(v, str):
        return "s"
    if isinstance(v, list):
        return "av"
    if isinstance(v, dict):
        return "a{sv}"
    raise TypeError(f"unsupported value for D-Bus serialization: {type(v)!r}")
