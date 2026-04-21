"""XDG-compliant filesystem paths for Smartass."""

from __future__ import annotations

import os
from pathlib import Path

APP_NAME = "smartass"
SYSTEM_PLUGIN_ROOT = Path("/usr/share/smartass/plugins")


def _xdg(home_env: str, default_rel: str) -> Path:
    value = os.environ.get(home_env)
    if value:
        return Path(value)
    return Path(os.environ["HOME"]) / default_rel


def config_dir() -> Path:
    return _xdg("XDG_CONFIG_HOME", ".config") / APP_NAME


def data_dir() -> Path:
    return _xdg("XDG_DATA_HOME", ".local/share") / APP_NAME


def cache_dir() -> Path:
    return _xdg("XDG_CACHE_HOME", ".cache") / APP_NAME


def config_file() -> Path:
    return config_dir() / "config.toml"


def user_plugin_dir() -> Path:
    return data_dir() / "plugins"


def plugin_data_dir(plugin_id: str) -> Path:
    return data_dir() / "plugin_data" / plugin_id


def exports_dir() -> Path:
    return data_dir() / "exports"


def plugin_roots() -> list[Path]:
    """Return plugin search paths, user-first (overrides system)."""
    return [user_plugin_dir(), SYSTEM_PLUGIN_ROOT]


def ensure_user_dirs() -> None:
    """Create all user-writable dirs used by the app."""
    for d in (
        config_dir(),
        data_dir(),
        user_plugin_dir(),
        data_dir() / "plugin_data",
        exports_dir(),
        cache_dir(),
    ):
        d.mkdir(parents=True, exist_ok=True)
