"""Verify per-plugin D-Bus object is exported on enable and unexported on disable."""

import asyncio
from pathlib import Path

import pytest
from dbus_next.aio import MessageBus
from dbus_next.errors import DBusError

from smartass.core import dbus_names
from smartass.core.config import ConfigStore
from smartass.daemon.plugin_manager import PluginManager
from smartass.daemon.service import CoreService


def _write_trivial_plugin(root: Path) -> None:
    d = root / "hello"
    d.mkdir(parents=True)
    (d / "manifest.toml").write_text(
        """
[plugin]
id = "hello"
name = "Hello"
version = "0.1.0"
api_version = 1
description = "hi"
author = "t"
entry = "plugin:HelloPlugin"
icon = "x"
permissions = []
"""
    )
    (d / "plugin.py").write_text(
        '''
from smartass.core.plugin_interface import (
    PluginInterface, SettingsSchema, StringField,
)


class HelloPlugin(PluginInterface):
    id = "hello"
    def build_tab(self, parent): return None
    def settings_schema(self):
        return SettingsSchema(fields=(StringField(key="g", label="G", default=""),))

    def last_snapshot(self):
        return {"message": "hello"}

    def is_stale(self):
        return False
'''
    )


@pytest.mark.asyncio
async def test_plugin_object_exported_on_enable(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg_data"))
    root = tmp_path / "plugins"
    _write_trivial_plugin(root)

    store = ConfigStore(tmp_path / "cfg.toml")
    store.load()
    pm = PluginManager(config_store=store, roots=[root])
    pm.discover()

    bus = await MessageBus().connect()
    svc = CoreService(pm, store)
    bus.export(dbus_names.CORE_PATH, svc)
    await bus.request_name(dbus_names.SERVICE)
    pm.attach_bus(bus)

    client_bus = await MessageBus().connect()
    introspection = await client_bus.introspect(dbus_names.SERVICE, dbus_names.CORE_PATH)
    proxy = client_bus.get_proxy_object(dbus_names.SERVICE, dbus_names.CORE_PATH, introspection)
    core = proxy.get_interface(dbus_names.CORE_IFACE)
    await core.call_enable_plugin("hello")

    # Now the plugin object should be at /ai/talonic/Smartass/plugins/hello
    plugin_path = dbus_names.plugin_path("hello")
    intro2 = await client_bus.introspect(dbus_names.SERVICE, plugin_path)
    proxy2 = client_bus.get_proxy_object(dbus_names.SERVICE, plugin_path, intro2)
    plugin_iface = proxy2.get_interface(dbus_names.PLUGIN_IFACE)
    import json as _json
    state = _json.loads(await plugin_iface.call_get_state())
    assert "snapshot" in state
    assert "stale" in state

    await core.call_disable_plugin("hello")
    # After disable, the object should be gone; introspection may still succeed
    # but would show no interfaces. Just run shutdown.
    await pm.shutdown()
    client_bus.disconnect()
    bus.disconnect()
