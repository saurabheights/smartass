"""Typed TOML config store with atomic writes and migration hooks."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # type: ignore[import-not-found]

import tomli_w

from smartass.core.plugin_interface import SchemaError, SettingsSchema

CURRENT_VERSION = 1


class InvalidConfig(ValueError):
    """Raised on schema or type errors when mutating config."""


def _default_config() -> dict[str, Any]:
    return {
        "smartass": {
            "version": CURRENT_VERSION,
            "enabled_plugins": [],
            "window_start_hidden": True,
            "theme": "system",
        },
        "plugins": {},
    }


def _migrate(data: dict[str, Any]) -> dict[str, Any]:
    """Bring a loaded config dict up to CURRENT_VERSION."""
    if "smartass" not in data or "version" not in data.get("smartass", {}):
        # v0 → v1: synthesize the smartass table; preserve any plugins table
        data = {
            "smartass": {
                "version": 1,
                "enabled_plugins": [],
                "window_start_hidden": True,
                "theme": "system",
            },
            "plugins": data.get("plugins", {}),
        }
    return data


class ConfigStore:
    """Manages `config.toml` on disk.

    All mutations go through explicit methods; the daemon is the sole writer.
    `save()` is atomic (tmpfile + rename with fsync of the directory).
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self._data: dict[str, Any] = _default_config()

    @property
    def data(self) -> dict[str, Any]:
        return self._data

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._data = _default_config()
            return self._data
        raw = tomllib.loads(self.path.read_text(encoding="utf-8"))
        self._data = _migrate(raw)
        return self._data

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        blob = tomli_w.dumps(self._data).encode("utf-8")
        fd, tmp_name = tempfile.mkstemp(
            prefix=".config.", suffix=".toml.tmp", dir=self.path.parent
        )
        tmp_path = Path(tmp_name)
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(blob)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, self.path)
            dir_fd = os.open(self.path.parent, os.O_DIRECTORY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        except Exception:
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)
            raise

    # --- mutators ---

    def set_plugin_values(
        self, plugin_id: str, values: dict[str, Any], schema: SettingsSchema
    ) -> dict[str, Any]:
        try:
            cleaned = schema.validate(values)
        except SchemaError as e:
            raise InvalidConfig(str(e)) from e
        self._data.setdefault("plugins", {})[plugin_id] = cleaned
        return cleaned

    def get_plugin_values(self, plugin_id: str) -> dict[str, Any]:
        return dict(self._data.get("plugins", {}).get(plugin_id, {}))

    def set_enabled(self, plugin_id: str, enabled: bool) -> None:
        smartass = self._data.setdefault("smartass", {})
        current = set(smartass.setdefault("enabled_plugins", []))
        if enabled:
            current.add(plugin_id)
        else:
            current.discard(plugin_id)
        smartass["enabled_plugins"] = sorted(current)

    def is_enabled(self, plugin_id: str) -> bool:
        return plugin_id in self._data.get("smartass", {}).get("enabled_plugins", [])


class PluginConfig:
    """Typed wrapper handed to plugins via PluginContext."""

    def __init__(self, store: ConfigStore, plugin_id: str, schema: SettingsSchema) -> None:
        self._store = store
        self._id = plugin_id
        self._schema = schema
        self._ensure_defaults()

    def _ensure_defaults(self) -> None:
        raw = self._store.get_plugin_values(self._id)
        cleaned = self._schema.validate(raw)
        self._store.set_plugin_values(self._id, cleaned, self._schema)

    def get(self, key: str) -> Any:
        return self._store.get_plugin_values(self._id).get(key)

    def all(self) -> dict[str, Any]:
        return self._store.get_plugin_values(self._id)

    def set(self, values: dict[str, Any]) -> dict[str, Any]:
        merged = {**self.all(), **values}
        return self._store.set_plugin_values(self._id, merged, self._schema)
