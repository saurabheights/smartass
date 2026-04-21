import textwrap
from pathlib import Path

import pytest

from smartass.core.manifest import ManifestError
from smartass.daemon.plugin_manager import DiscoveredPlugin, PluginManager


def _make_hello_plugin_dir(root: Path, plugin_id: str = "hello") -> Path:
    d = root / plugin_id
    d.mkdir(parents=True)
    (d / "manifest.toml").write_text(
        textwrap.dedent(
            f"""
            [plugin]
            id = "{plugin_id}"
            name = "Hello"
            version = "0.1.0"
            api_version = 1
            description = "Hello"
            author = "Test"
            entry = "plugin:HelloPlugin"
            icon = "x"
            permissions = []
            """
        )
    )
    (d / "plugin.py").write_text(
        textwrap.dedent(
            """
            from smartass.core.plugin_interface import (
                PluginInterface, SettingsSchema, StringField,
            )

            class HelloPlugin(PluginInterface):
                id = "hello"

                def build_tab(self, parent):
                    return None

                def settings_schema(self) -> SettingsSchema:
                    return SettingsSchema(
                        fields=(StringField(key="greeting", label="Greeting", default="hi"),)
                    )
            """
        )
    )
    return d


def test_discover_returns_plugins_from_user_and_system_roots(tmp_path):
    user_root = tmp_path / "user"
    system_root = tmp_path / "system"
    user_root.mkdir()
    system_root.mkdir()
    _make_hello_plugin_dir(user_root, "hello")
    _make_hello_plugin_dir(system_root, "hello2")

    pm = PluginManager(config_store=None, roots=[user_root, system_root])
    found = pm.discover()
    ids = sorted(p.manifest.id for p in found)
    assert ids == ["hello", "hello2"]
    assert all(isinstance(p, DiscoveredPlugin) for p in found)


def test_user_root_shadows_system_root_for_same_id(tmp_path):
    user_root = tmp_path / "user"
    system_root = tmp_path / "system"
    user_root.mkdir()
    system_root.mkdir()
    _make_hello_plugin_dir(user_root, "hello")
    _make_hello_plugin_dir(system_root, "hello")

    pm = PluginManager(config_store=None, roots=[user_root, system_root])
    found = pm.discover()
    assert len(found) == 1
    assert found[0].manifest.root == user_root / "hello"


def test_discover_skips_invalid_plugin_but_keeps_valid(tmp_path, caplog):
    root = tmp_path / "r"
    root.mkdir()
    # valid
    _make_hello_plugin_dir(root, "hello")
    # invalid — manifest.toml with id mismatch
    bad = root / "oops"
    bad.mkdir()
    (bad / "manifest.toml").write_text("[plugin]\nid = \"other\"\n")

    pm = PluginManager(config_store=None, roots=[root])
    found = pm.discover()
    assert [p.manifest.id for p in found] == ["hello"]


def test_load_plugin_class_imports_entry(tmp_path):
    root = tmp_path / "r"
    root.mkdir()
    _make_hello_plugin_dir(root, "hello")
    pm = PluginManager(config_store=None, roots=[root])
    found = pm.discover()
    cls = pm.load_plugin_class(found[0])
    assert cls.__name__ == "HelloPlugin"
