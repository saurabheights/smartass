import pytest

from smartass.core.config import ConfigStore, InvalidConfig, PluginConfig
from smartass.core.plugin_interface import (
    IntField,
    SettingsSchema,
    StringField,
)


def _weather_schema() -> SettingsSchema:
    return SettingsSchema(
        fields=(
            StringField(key="city", label="City", default="Berlin", required=True),
            IntField(key="poll_minutes", label="Poll", default=15, min=1, max=240),
        )
    )


def test_load_creates_default_when_missing(tmp_path):
    store = ConfigStore(tmp_path / "cfg.toml")
    data = store.load()
    assert data["smartass"]["version"] == 1
    assert data["smartass"]["enabled_plugins"] == []
    assert "plugins" in data


def test_roundtrip_through_disk(tmp_path):
    path = tmp_path / "cfg.toml"
    store = ConfigStore(path)
    store.load()
    store.set_plugin_values("weather", {"city": "Munich", "poll_minutes": 30}, _weather_schema())
    store.set_enabled("weather", True)
    store.save()

    store2 = ConfigStore(path)
    data = store2.load()
    assert data["plugins"]["weather"] == {"city": "Munich", "poll_minutes": 30}
    assert data["smartass"]["enabled_plugins"] == ["weather"]


def test_set_plugin_values_validates_against_schema(tmp_path):
    store = ConfigStore(tmp_path / "cfg.toml")
    store.load()
    with pytest.raises(InvalidConfig):
        store.set_plugin_values("weather", {"poll_minutes": 9999}, _weather_schema())


def test_plugin_config_typed_getters(tmp_path):
    store = ConfigStore(tmp_path / "cfg.toml")
    store.load()
    store.set_plugin_values("weather", {"city": "Berlin", "poll_minutes": 15}, _weather_schema())
    pc = PluginConfig(store, "weather", _weather_schema())
    assert pc.get("city") == "Berlin"
    assert pc.get("poll_minutes") == 15
    pc.set({"city": "Paris", "poll_minutes": 60})
    assert pc.get("city") == "Paris"


def test_enabled_list_is_deduped_and_sorted(tmp_path):
    store = ConfigStore(tmp_path / "cfg.toml")
    store.load()
    store.set_enabled("weather", True)
    store.set_enabled("weather", True)  # idempotent
    store.set_enabled("quicknotes", True)
    store.save()
    assert store.data["smartass"]["enabled_plugins"] == ["quicknotes", "weather"]


def test_disable_removes_from_list(tmp_path):
    store = ConfigStore(tmp_path / "cfg.toml")
    store.load()
    store.set_enabled("weather", True)
    store.set_enabled("weather", False)
    assert "weather" not in store.data["smartass"]["enabled_plugins"]


def test_atomic_write_does_not_leave_partial_file_on_failure(tmp_path, monkeypatch):
    store = ConfigStore(tmp_path / "cfg.toml")
    store.load()
    store.set_enabled("weather", True)
    # Force rename to fail after tmpfile written
    import os
    real_replace = os.replace
    calls = {"n": 0}

    def boom(*a, **kw):
        calls["n"] += 1
        raise OSError("simulated")

    monkeypatch.setattr(os, "replace", boom)
    with pytest.raises(OSError):
        store.save()
    # Original file still absent (first save)
    assert not (tmp_path / "cfg.toml").exists()
    # tmpfile cleaned up
    assert list(tmp_path.iterdir()) == []


def test_migration_from_v0_injects_version(tmp_path):
    path = tmp_path / "cfg.toml"
    # v0 = no [smartass].version, just plugins table
    path.write_text('[plugins.weather]\ncity = "Berlin"\n')
    store = ConfigStore(path)
    data = store.load()
    assert data["smartass"]["version"] == 1
    assert data["plugins"]["weather"]["city"] == "Berlin"
