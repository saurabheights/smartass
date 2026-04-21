import logging
import textwrap
from pathlib import Path

import pytest

from smartass.core.config import ConfigStore
from smartass.daemon.plugin_manager import PluginManager


def _write_hello(root: Path, plugin_id: str = "hello", tracking_file: Path | None = None) -> None:
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
    track = str(tracking_file) if tracking_file else ""
    (d / "plugin.py").write_text(
        textwrap.dedent(
            f"""
            from smartass.core.plugin_interface import (
                PluginInterface, SettingsSchema, StringField,
            )


            class HelloPlugin(PluginInterface):
                id = "{plugin_id}"

                def build_tab(self, parent):
                    return None

                def settings_schema(self) -> SettingsSchema:
                    return SettingsSchema(
                        fields=(StringField(key="greeting", label="Greeting", default="hi"),)
                    )

                def on_load(self):
                    open({track!r}, "a").write("load,")

                async def on_start(self):
                    open({track!r}, "a").write("start,")

                async def on_stop(self):
                    open({track!r}, "a").write("stop,")

                def on_unload(self):
                    open({track!r}, "a").write("unload,")
            """
        )
    )


@pytest.mark.asyncio
async def test_enable_fires_on_load_then_on_start(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg_data"))
    root = tmp_path / "plugins"
    track = tmp_path / "track.log"
    _write_hello(root, tracking_file=track)

    store = ConfigStore(tmp_path / "cfg.toml")
    store.load()
    pm = PluginManager(config_store=store, roots=[root])
    pm.discover()
    await pm.enable("hello")
    assert track.read_text() == "load,start,"
    assert store.is_enabled("hello")


@pytest.mark.asyncio
async def test_disable_fires_on_stop_then_on_unload(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg_data"))
    root = tmp_path / "plugins"
    track = tmp_path / "track.log"
    _write_hello(root, tracking_file=track)

    store = ConfigStore(tmp_path / "cfg.toml")
    store.load()
    pm = PluginManager(config_store=store, roots=[root])
    pm.discover()
    await pm.enable("hello")
    track.write_text("")
    await pm.disable("hello")
    assert track.read_text() == "stop,unload,"
    assert not store.is_enabled("hello")


@pytest.mark.asyncio
async def test_enable_idempotent(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg_data"))
    root = tmp_path / "plugins"
    track = tmp_path / "track.log"
    _write_hello(root, tracking_file=track)
    store = ConfigStore(tmp_path / "cfg.toml")
    store.load()
    pm = PluginManager(config_store=store, roots=[root])
    pm.discover()
    await pm.enable("hello")
    await pm.enable("hello")
    # Only one load,start pair
    assert track.read_text() == "load,start,"


@pytest.mark.asyncio
async def test_disable_unknown_is_noop(tmp_path):
    store = ConfigStore(tmp_path / "cfg.toml")
    store.load()
    pm = PluginManager(config_store=store, roots=[tmp_path / "plugins"])
    pm.discover()
    await pm.disable("nope")  # should not raise


@pytest.mark.asyncio
async def test_boot_enables_all_from_config(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg_data"))
    root = tmp_path / "plugins"
    track = tmp_path / "track.log"
    _write_hello(root, tracking_file=track)

    store = ConfigStore(tmp_path / "cfg.toml")
    store.load()
    store.set_enabled("hello", True)
    pm = PluginManager(config_store=store, roots=[root])
    pm.discover()
    await pm.boot()
    assert track.read_text() == "load,start,"


@pytest.mark.asyncio
async def test_shutdown_stops_all_running(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg_data"))
    root = tmp_path / "plugins"
    track = tmp_path / "track.log"
    _write_hello(root, tracking_file=track)

    store = ConfigStore(tmp_path / "cfg.toml")
    store.load()
    pm = PluginManager(config_store=store, roots=[root])
    pm.discover()
    await pm.enable("hello")
    track.write_text("")
    await pm.shutdown()
    assert track.read_text() == "stop,unload,"
