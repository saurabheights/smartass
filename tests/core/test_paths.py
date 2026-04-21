from pathlib import Path

import pytest

from smartass.core import paths


def test_config_dir_honors_xdg_config_home(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    assert paths.config_dir() == tmp_path / "smartass"


def test_config_dir_defaults_to_home_config(monkeypatch, tmp_path):
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    assert paths.config_dir() == tmp_path / ".config" / "smartass"


def test_data_dir_honors_xdg_data_home(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    assert paths.data_dir() == tmp_path / "smartass"


def test_data_dir_defaults(monkeypatch, tmp_path):
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    assert paths.data_dir() == tmp_path / ".local" / "share" / "smartass"


def test_cache_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    assert paths.cache_dir() == tmp_path / "smartass"


def test_config_file_path(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    assert paths.config_file() == tmp_path / "smartass" / "config.toml"


def test_plugin_data_dir_per_plugin(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    assert paths.plugin_data_dir("weather") == tmp_path / "smartass" / "plugin_data" / "weather"


def test_user_plugin_roots_includes_user_and_system(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    roots = paths.plugin_roots()
    assert tmp_path / "smartass" / "plugins" in roots
    assert Path("/usr/share/smartass/plugins") in roots


def test_exports_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    assert paths.exports_dir() == tmp_path / "smartass" / "exports"


def test_ensure_dirs_creates_directories(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    paths.ensure_user_dirs()
    assert (tmp_path / "cfg" / "smartass").is_dir()
    assert (tmp_path / "data" / "smartass" / "plugins").is_dir()
    assert (tmp_path / "data" / "smartass" / "plugin_data").is_dir()
    assert (tmp_path / "data" / "smartass" / "exports").is_dir()
    assert (tmp_path / "cache" / "smartass").is_dir()


def test_raises_when_home_and_xdg_both_missing(monkeypatch):
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.delenv("HOME", raising=False)
    with pytest.raises(EnvironmentError, match="XDG_CONFIG_HOME"):
        paths.config_dir()
