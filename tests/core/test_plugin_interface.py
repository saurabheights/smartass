import logging
from pathlib import Path
from types import SimpleNamespace

import pytest

from smartass.core.plugin_interface import (
    PluginContext,
    PluginInterface,
    SettingsSchema,
    StringField,
)


class DummyPlugin(PluginInterface):
    id = "dummy"

    def build_tab(self, parent):  # pragma: no cover - tray-side, not exercised here
        raise NotImplementedError

    def settings_schema(self) -> SettingsSchema:
        return SettingsSchema(fields=(StringField(key="x", label="X", default=""),))


def test_context_redacts_http_when_permission_missing(tmp_path):
    ctx = PluginContext(
        config=SimpleNamespace(),
        data_dir=tmp_path,
        log=logging.getLogger("test"),
        http=None,
        bus=None,
        signals=SimpleNamespace(),
        permissions=frozenset(),
    )
    assert ctx.http is None
    with pytest.raises(PermissionError, match="net.http"):
        ctx.require("net.http")


def test_context_require_passes_when_granted(tmp_path):
    ctx = PluginContext(
        config=SimpleNamespace(),
        data_dir=tmp_path,
        log=logging.getLogger("test"),
        http=SimpleNamespace(),
        bus=None,
        signals=SimpleNamespace(),
        permissions=frozenset({"net.http"}),
    )
    ctx.require("net.http")  # should not raise


def test_plugin_default_hooks_are_noops(tmp_path):
    ctx = PluginContext(
        config=SimpleNamespace(),
        data_dir=tmp_path,
        log=logging.getLogger("test"),
        http=None,
        bus=None,
        signals=SimpleNamespace(),
        permissions=frozenset(),
    )
    p = DummyPlugin(ctx)
    # All no-op defaults should not raise
    p.on_load()
    p.on_unload()
    assert p.export_state() == {}
    p.import_state({})
    assert p.dbus_interface() is None


def test_plugin_cannot_be_instantiated_without_build_tab_and_schema():
    with pytest.raises(TypeError):
        PluginInterface(ctx=None)  # abstract
