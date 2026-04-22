"""Integration tests for CoreService over a private D-Bus session."""

import asyncio
import textwrap
from pathlib import Path

import pytest
from dbus_next.aio import MessageBus

from smartass.core import dbus_names
from smartass.core.config import ConfigStore
from smartass.daemon.plugin_manager import PluginManager
from smartass.daemon.service import CoreService


def _write_hello(root: Path, plugin_id: str = "hello") -> None:
    d = root / plugin_id
    d.mkdir(parents=True)
    (d / "manifest.toml").write_text(
        f"""
[plugin]
id = "{plugin_id}"
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
        textwrap.dedent(
            f"""
            from smartass.core.plugin_interface import (
                PluginInterface, SettingsSchema, StringField,
            )

            class HelloPlugin(PluginInterface):
                id = "{plugin_id}"
                def build_tab(self, parent): return None
                def settings_schema(self):
                    return SettingsSchema(
                        fields=(StringField(key="greeting", label="Greeting", default="hi"),)
                    )
            """
        )
    )


@pytest.mark.asyncio
async def test_ping_returns_pong(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg_data"))
    store = ConfigStore(tmp_path / "cfg.toml")
    store.load()
    pm = PluginManager(config_store=store, roots=[tmp_path / "plugins"])
    pm.discover()
    bus = await MessageBus().connect()
    svc = CoreService(pm, store)
    bus.export(dbus_names.CORE_PATH, svc)
    await bus.request_name(dbus_names.SERVICE)

    client_bus = await MessageBus().connect()
    introspection = await client_bus.introspect(dbus_names.SERVICE, dbus_names.CORE_PATH)
    proxy = client_bus.get_proxy_object(dbus_names.SERVICE, dbus_names.CORE_PATH, introspection)
    iface = proxy.get_interface(dbus_names.CORE_IFACE)
    result = await iface.call_ping()
    assert result.startswith("pong")

    bus.disconnect()
    client_bus.disconnect()


@pytest.mark.asyncio
async def test_list_plugins_reports_enabled_state(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg_data"))
    root = tmp_path / "plugins"
    _write_hello(root)
    store = ConfigStore(tmp_path / "cfg.toml")
    store.load()
    pm = PluginManager(config_store=store, roots=[root])
    pm.discover()

    bus = await MessageBus().connect()
    svc = CoreService(pm, store)
    bus.export(dbus_names.CORE_PATH, svc)
    await bus.request_name(dbus_names.SERVICE)

    client_bus = await MessageBus().connect()
    introspection = await client_bus.introspect(dbus_names.SERVICE, dbus_names.CORE_PATH)
    proxy = client_bus.get_proxy_object(dbus_names.SERVICE, dbus_names.CORE_PATH, introspection)
    iface = proxy.get_interface(dbus_names.CORE_IFACE)
    import json as _json
    rows = _json.loads(await iface.call_list_plugins())
    ids = {r["id"] for r in rows}
    assert "hello" in ids
    row = next(r for r in rows if r["id"] == "hello")
    assert row["installed"] is True
    assert row["enabled"] is False

    bus.disconnect()
    client_bus.disconnect()


@pytest.mark.asyncio
async def test_enable_plugin_persists_and_reports(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg_data"))
    root = tmp_path / "plugins"
    _write_hello(root)
    store = ConfigStore(tmp_path / "cfg.toml")
    store.load()
    pm = PluginManager(config_store=store, roots=[root])
    pm.discover()

    bus = await MessageBus().connect()
    svc = CoreService(pm, store)
    bus.export(dbus_names.CORE_PATH, svc)
    await bus.request_name(dbus_names.SERVICE)

    client_bus = await MessageBus().connect()
    introspection = await client_bus.introspect(dbus_names.SERVICE, dbus_names.CORE_PATH)
    proxy = client_bus.get_proxy_object(dbus_names.SERVICE, dbus_names.CORE_PATH, introspection)
    iface = proxy.get_interface(dbus_names.CORE_IFACE)

    await iface.call_enable_plugin("hello")
    import json as _json
    rows = _json.loads(await iface.call_list_plugins())
    row = next(r for r in rows if r["id"] == "hello")
    assert row["enabled"] is True

    bus.disconnect()
    client_bus.disconnect()
