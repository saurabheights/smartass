"""PluginInterface ABC and supporting types (settings schema, context).

This module is imported by both the daemon and the tray. It MUST NOT import
Qt or D-Bus libraries directly; those are injected via PluginContext.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar, Optional


class SchemaError(ValueError):
    """Raised for any settings-schema validation failure."""


@dataclass(frozen=True)
class _BaseField:
    key: str
    label: str
    default: Any = None
    required: bool = False
    description: str = ""

    _type: ClassVar[str] = "base"

    def validate(self, value: Any) -> Any:  # pragma: no cover - overridden
        raise NotImplementedError

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self._type,
            "key": self.key,
            "label": self.label,
            "default": self.default,
            "required": self.required,
            "description": self.description,
        }


@dataclass(frozen=True)
class StringField(_BaseField):
    default: str = ""
    _type: ClassVar[str] = "string"

    def validate(self, value: Any) -> str:
        if not isinstance(value, str):
            raise SchemaError(f"{self.key}: expected string, got {type(value).__name__}")
        if self.required and not value:
            raise SchemaError(f"{self.key}: required, empty string not allowed")
        return value


@dataclass(frozen=True)
class IntField(_BaseField):
    default: int = 0
    min: Optional[int] = None
    max: Optional[int] = None
    _type: ClassVar[str] = "int"

    def validate(self, value: Any) -> int:
        if not isinstance(value, int) or isinstance(value, bool):
            raise SchemaError(f"{self.key}: expected int, got {type(value).__name__}")
        if self.min is not None and value < self.min:
            raise SchemaError(f"{self.key}: out of range (min={self.min})")
        if self.max is not None and value > self.max:
            raise SchemaError(f"{self.key}: out of range (max={self.max})")
        return value

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d["min"] = self.min
        d["max"] = self.max
        return d


@dataclass(frozen=True)
class BoolField(_BaseField):
    default: bool = False
    _type: ClassVar[str] = "bool"

    def validate(self, value: Any) -> bool:
        if not isinstance(value, bool):
            raise SchemaError(f"{self.key}: expected bool, got {type(value).__name__}")
        return value


@dataclass(frozen=True)
class SelectField(_BaseField):
    default: str = ""
    options: tuple[str, ...] = ()
    _type: ClassVar[str] = "select"

    def validate(self, value: Any) -> str:
        if not isinstance(value, str):
            raise SchemaError(f"{self.key}: expected string, got {type(value).__name__}")
        if value not in self.options:
            raise SchemaError(f"{self.key}: '{value}' not in options {self.options}")
        return value

    def to_dict(self) -> dict[str, Any]:
        d = super().to_dict()
        d["options"] = list(self.options)
        return d


@dataclass(frozen=True)
class SecretField(_BaseField):
    default: str = ""
    _type: ClassVar[str] = "secret"

    def validate(self, value: Any) -> str:
        if not isinstance(value, str):
            raise SchemaError(f"{self.key}: expected string, got {type(value).__name__}")
        return value

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return f"SecretField(key={self.key!r}, label={self.label!r})"


Field = _BaseField  # export alias


@dataclass(frozen=True)
class SettingsSchema:
    fields: tuple[_BaseField, ...] = ()

    def by_key(self) -> dict[str, _BaseField]:
        return {f.key: f for f in self.fields}

    def validate(self, values: dict[str, Any]) -> dict[str, Any]:
        by_key = self.by_key()
        unknown = set(values) - set(by_key)
        if unknown:
            raise SchemaError(f"unknown field(s): {sorted(unknown)}")
        cleaned: dict[str, Any] = {}
        for f in self.fields:
            if f.key in values:
                cleaned[f.key] = f.validate(values[f.key])
            else:
                cleaned[f.key] = f.default
        return cleaned

    def to_dict(self) -> dict[str, Any]:
        return {"fields": [f.to_dict() for f in self.fields]}


# ---- Context ----


@dataclass
class PluginContext:
    """Host-provided context injected into every plugin instance.

    The tray-side and daemon-side instances of a plugin each get their own
    PluginContext. Fields gated by permissions are set to None when the
    corresponding permission is absent.
    """

    config: Any
    data_dir: Path
    log: Any  # logging.Logger, typed Any to avoid extra import at type-check
    http: Any  # AsyncHttpClient | None
    bus: Any  # SessionBus | None
    signals: Any
    permissions: frozenset[str]

    def require(self, perm: str) -> None:
        if perm not in self.permissions:
            raise PermissionError(f"plugin lacks permission: {perm}")


# ---- Abstract plugin ----


class PluginInterface(ABC):
    """Base class every plugin subclasses.

    Instantiated in BOTH the daemon and the tray processes, with different
    PluginContext values injected. Daemon-side lifecycle hooks (on_*) only
    run in the daemon; build_tab() only runs in the tray.
    """

    id: str
    api_version: ClassVar[int] = 1

    def __init__(self, ctx: PluginContext) -> None:
        self.ctx = ctx

    # --- Lifecycle (daemon-side) ---
    def on_load(self) -> None:
        """Sync init before on_start; open DB, read config."""

    async def on_start(self) -> None:
        """Begin background work (polling, watchers)."""

    async def on_stop(self) -> None:
        """Stop tasks and flush pending work."""

    def on_unload(self) -> None:
        """Release resources after on_stop."""

    # --- UI (tray-side) ---
    @abstractmethod
    def build_tab(self, parent: Any) -> Any:
        """Return a QWidget for the main window's plugin tab."""

    # --- Settings ---
    @abstractmethod
    def settings_schema(self) -> SettingsSchema:
        """Return the declarative settings schema for this plugin."""

    def on_settings_changed(self, new: dict[str, Any]) -> None:
        """Called after the daemon persists new settings."""

    # --- Import/export ---
    def export_state(self) -> dict[str, Any]:
        """Return portable state for ExportAll. Default: no state."""
        return {}

    def import_state(self, data: dict[str, Any]) -> None:
        """Apply portable state from ImportAll. Default: ignore."""

    # --- D-Bus ---
    def dbus_interface(self) -> Optional[type]:
        """Return an optional plugin-specific D-Bus interface class."""
        return None
