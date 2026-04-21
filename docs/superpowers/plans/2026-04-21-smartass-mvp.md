# Smartass MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the MVP of Smartass: a split daemon + Qt6 tray desktop app for Ubuntu, with a `PluginInterface` contract and a Weather plugin (Open-Meteo), installable via a single `.deb`.

**Architecture:** Two processes on the user session. `smartass-daemon` (async Python, `dbus-next`) hosts plugins in-process, owns the TOML config store, and publishes `ai.talonic.Smartass` on the session D-Bus. `smartass-tray` (PySide6, `QtDBus`) shows the AppIndicator icon, a `QTabWidget` main window with an always-on Settings tab, and one tab per enabled plugin. Plugins are directories discovered from `/usr/share/smartass/plugins/` (system) and `~/.local/share/smartass/plugins/` (user).

**Tech Stack:**
- Python ≥ 3.10, Poetry, pytest + pytest-asyncio
- `PySide6` (Qt6, QtDBus)
- `dbus-next` (async D-Bus on daemon side)
- `httpx` (async HTTP), `respx` (HTTP test mocks)
- `tomli` / `tomli-w` (TOML I/O — stdlib `tomllib` read-only, so we need `tomli-w` for writes)
- `secretstorage` (GNOME Keyring)
- `dh-virtualenv`, `debhelper`, `dh-python` (Debian packaging)
- `dbus-run-session` (integration tests)

**Reference spec:** `docs/superpowers/specs/2026-04-21-smartass-design.md`

---

## Phase 0 — Project Setup

### Task 0.1: Update pyproject.toml (runtime + dev deps, Python version)

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Replace `pyproject.toml` with the target config**

Keep existing tool blocks (`ruff`, `mypy`, `pytest`) intact; add deps, raise python version, add `[project.scripts]`.

```toml
[project]
name = "smartass"
version = "0.1.0"
description = "Smartass — desktop smart-assistant app for Ubuntu (tray + plugin host)"
authors = [
    {name="Saurabh Khanduja", email="saurabh@talonic.ai"},
]
license = "MIT"
readme = "README.md"
requires-python = ">=3.10"
keywords = ["desktop", "assistant", "gnome", "ubuntu", "plugin"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Environment :: X11 Applications :: Qt",
    "Intended Audience :: End Users/Desktop",
    "License :: OSI Approved :: MIT License",
    "Operating System :: POSIX :: Linux",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: Desktop Environment :: Gnome",
]
dependencies = [
    "PySide6 (>=6.6.0, <7.0.0)",
    "dbus-next (>=0.2.3, <1.0.0)",
    "httpx (>=0.27.0, <1.0.0)",
    "tomli-w (>=1.0.0, <2.0.0)",
    "secretstorage (>=3.3.3, <4.0.0)",
]

[project.scripts]
smartass-daemon = "smartass.daemon.__main__:main"
smartass-tray = "smartass.tray.__main__:main"

[project.urls]
repository = "https://github.com/saurabheights/smartass"
"Bug Tracker" = "https://github.com/saurabheights/smartass/issues"

[dependency-groups]
dev = [
    "ruff (>=0.8.4, <1.0.0)",
    "mypy (>=1.14.1, <2.0.0)",
    "pre-commit (>=4.0.1, <5.0.0)",
    "pytest (>=8.3.4, <9.0.0)",
    "pytest-asyncio (>=0.24.0, <1.0.0)",
    "pytest-cov (>=6.0.0, <7.0.0)",
    "pyupgrade (>=3.17.0, <4.0.0)",
    "respx (>=0.21.1, <1.0.0)",
]

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"

[tool.pytest.ini_options]
addopts = [
    "--cov=smartass/",
    "-p no:cacheprovider",
]
asyncio_mode = "auto"

[tool.coverage.run]
data_file = '.cache/.coverage'

[tool.coverage.report]
skip_empty = true

[tool.mypy]
cache_dir = '.cache/.mypy_cache'

[tool.ruff]
line-length = 120
indent-width = 4
target-version = "py310"
cache-dir = '.cache/.ruff_cache'
exclude = [".cache", ".venv", "build", "dist"]

[tool.ruff.lint]
select = ["E4", "E7", "E9", "F", "I"]
ignore = []
fixable = ["ALL"]
unfixable = []
dummy-variable-rgx = "^(_+|(_+[a-zA-Z0-9_]*[a-zA-Z0-9]+?))$"

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
skip-magic-trailing-comma = false
line-ending = "auto"
```

- [ ] **Step 2: Install deps**

Run: `poetry install`
Expected: lockfile updates; all deps install successfully.

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml poetry.lock
git commit -m "chore: raise python to 3.10, add runtime + dev deps

Adds PySide6, dbus-next, httpx, tomli-w, secretstorage for runtime.
Adds pytest-asyncio, respx for tests. Wires project.scripts entry
points for smartass-daemon and smartass-tray."
```

---

### Task 0.2: Remove old scaffold, create new package layout

**Files:**
- Delete: `smartass/smartass.py`
- Delete: `tests/test_smartass.py`
- Create: `smartass/__init__.py`
- Create: `smartass/core/__init__.py`
- Create: `smartass/daemon/__init__.py`
- Create: `smartass/tray/__init__.py`
- Create: `smartass/plugins/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/core/__init__.py`
- Create: `tests/daemon/__init__.py`
- Create: `tests/plugins/__init__.py`
- Create: `tests/plugins/weather/__init__.py`

- [ ] **Step 1: Delete the existing scaffold files**

Run: `rm smartass/smartass.py tests/test_smartass.py`

- [ ] **Step 2: Create the empty package init files**

Each `__init__.py` above should contain exactly:

```python
"""Smartass package."""
```

For `smartass/__init__.py` specifically, add the version:

```python
"""Smartass — desktop smart-assistant."""

__version__ = "0.1.0"
```

- [ ] **Step 3: Verify layout**

Run: `find smartass tests -name '__init__.py' | sort`
Expected output includes every `__init__.py` listed in Files above.

- [ ] **Step 4: Commit**

```bash
git add smartass/ tests/
git commit -m "refactor: replace single-module scaffold with package layout

Creates core/, daemon/, tray/, plugins/ subpackages and mirrors
under tests/. Drops the placeholder smartass.smartass module."
```

---

## Phase 1 — Core

### Task 1.1: `smartass/core/paths.py` — XDG path helpers

**Files:**
- Create: `smartass/core/paths.py`
- Create: `tests/core/test_paths.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/core/test_paths.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `poetry run pytest tests/core/test_paths.py -v`
Expected: ImportError / FAIL — `paths` module does not exist.

- [ ] **Step 3: Implement**

```python
# smartass/core/paths.py
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `poetry run pytest tests/core/test_paths.py -v`
Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add smartass/core/paths.py tests/core/test_paths.py
git commit -m "feat(core): XDG path helpers for config/data/cache/plugins"
```

---

### Task 1.2: `smartass/core/dbus_names.py` — constants

**Files:**
- Create: `smartass/core/dbus_names.py`
- Create: `tests/core/test_dbus_names.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/core/test_dbus_names.py
from smartass.core import dbus_names


def test_constants_match_spec():
    assert dbus_names.SERVICE == "ai.talonic.Smartass"
    assert dbus_names.CORE_PATH == "/ai/talonic/Smartass"
    assert dbus_names.CORE_IFACE == "ai.talonic.Smartass.Core"
    assert dbus_names.PLUGIN_IFACE == "ai.talonic.Smartass.Plugin"


def test_plugin_path_for():
    assert dbus_names.plugin_path("weather") == "/ai/talonic/Smartass/plugins/weather"


def test_plugin_iface_for():
    assert dbus_names.plugin_iface("weather") == "ai.talonic.Smartass.Plugin.Weather"
    assert dbus_names.plugin_iface("quick_notes") == "ai.talonic.Smartass.Plugin.QuickNotes"
```

- [ ] **Step 2: Run test**

Run: `poetry run pytest tests/core/test_dbus_names.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement**

```python
# smartass/core/dbus_names.py
"""D-Bus naming constants for Smartass."""

from __future__ import annotations

SERVICE = "ai.talonic.Smartass"
CORE_PATH = "/ai/talonic/Smartass"
CORE_IFACE = "ai.talonic.Smartass.Core"
PLUGIN_IFACE = "ai.talonic.Smartass.Plugin"


def plugin_path(plugin_id: str) -> str:
    return f"{CORE_PATH}/plugins/{plugin_id}"


def _to_pascal(snake: str) -> str:
    return "".join(part.capitalize() for part in snake.split("_"))


def plugin_iface(plugin_id: str) -> str:
    return f"{PLUGIN_IFACE}.{_to_pascal(plugin_id)}"
```

- [ ] **Step 4: Run tests**

Run: `poetry run pytest tests/core/test_dbus_names.py -v`
Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add smartass/core/dbus_names.py tests/core/test_dbus_names.py
git commit -m "feat(core): D-Bus naming constants + helpers"
```

---

### Task 1.3: `smartass/core/manifest.py` — manifest parsing

**Files:**
- Create: `smartass/core/manifest.py`
- Create: `tests/core/test_manifest.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/core/test_manifest.py
import pytest

from smartass.core.manifest import Manifest, ManifestError, load_manifest


def test_load_valid_manifest(tmp_path):
    (tmp_path / "manifest.toml").write_text(
        """
[plugin]
id = "weather"
name = "Weather"
version = "0.1.0"
api_version = 1
description = "Forecast"
author = "Saurabh Khanduja"
entry = "plugin:WeatherPlugin"
icon = "weather-clear-symbolic"
permissions = ["net.http"]
"""
    )
    m = load_manifest(tmp_path)
    assert isinstance(m, Manifest)
    assert m.id == "weather"
    assert m.name == "Weather"
    assert m.version == "0.1.0"
    assert m.api_version == 1
    assert m.entry_module == "plugin"
    assert m.entry_class == "WeatherPlugin"
    assert m.permissions == frozenset({"net.http"})
    assert m.root == tmp_path


def test_missing_file_raises(tmp_path):
    with pytest.raises(ManifestError, match="manifest.toml not found"):
        load_manifest(tmp_path)


def test_missing_required_field(tmp_path):
    (tmp_path / "manifest.toml").write_text("[plugin]\nid = \"x\"\n")
    with pytest.raises(ManifestError, match="missing required field"):
        load_manifest(tmp_path)


def test_unknown_permission_rejected(tmp_path):
    (tmp_path / "manifest.toml").write_text(
        """
[plugin]
id = "x"
name = "X"
version = "0.1.0"
api_version = 1
description = "x"
author = "x"
entry = "plugin:X"
icon = "x"
permissions = ["net.evil"]
"""
    )
    with pytest.raises(ManifestError, match="unknown permission"):
        load_manifest(tmp_path)


def test_id_must_match_dir_name(tmp_path):
    plugin_dir = tmp_path / "clipboard"
    plugin_dir.mkdir()
    (plugin_dir / "manifest.toml").write_text(
        """
[plugin]
id = "weather"
name = "X"
version = "0.1.0"
api_version = 1
description = "x"
author = "x"
entry = "plugin:X"
icon = "x"
permissions = []
"""
    )
    with pytest.raises(ManifestError, match="id 'weather' does not match directory 'clipboard'"):
        load_manifest(plugin_dir)


def test_api_version_mismatch_rejected(tmp_path):
    (tmp_path / "manifest.toml").write_text(
        """
[plugin]
id = "weather"
name = "Weather"
version = "0.1.0"
api_version = 99
description = "x"
author = "x"
entry = "plugin:X"
icon = "x"
permissions = []
"""
    )
    with pytest.raises(ManifestError, match="incompatible api_version"):
        load_manifest(tmp_path)
```

- [ ] **Step 2: Run test — expect fail**

Run: `poetry run pytest tests/core/test_manifest.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement**

```python
# smartass/core/manifest.py
"""Plugin manifest loading and validation."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

CURRENT_API_VERSION = 1
ALLOWED_PERMISSIONS = frozenset({"net.http", "fs.data", "clipboard", "ipc.dbus"})
REQUIRED_FIELDS = (
    "id",
    "name",
    "version",
    "api_version",
    "description",
    "author",
    "entry",
    "icon",
)


class ManifestError(Exception):
    """Raised for any manifest-related failure."""


@dataclass(frozen=True)
class Manifest:
    root: Path
    id: str
    name: str
    version: str
    api_version: int
    description: str
    author: str
    entry_module: str
    entry_class: str
    icon: str
    permissions: frozenset[str]


def load_manifest(plugin_dir: Path) -> Manifest:
    path = plugin_dir / "manifest.toml"
    if not path.is_file():
        raise ManifestError(f"manifest.toml not found in {plugin_dir}")
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as e:
        raise ManifestError(f"invalid TOML in {path}: {e}") from e

    plugin = data.get("plugin")
    if not isinstance(plugin, dict):
        raise ManifestError(f"{path}: missing [plugin] table")

    for field in REQUIRED_FIELDS:
        if field not in plugin:
            raise ManifestError(f"{path}: missing required field '{field}'")

    api_version = int(plugin["api_version"])
    if api_version != CURRENT_API_VERSION:
        raise ManifestError(
            f"{path}: incompatible api_version {api_version} (expected {CURRENT_API_VERSION})"
        )

    # id must match parent directory name (loader enforces co-location)
    if plugin["id"] != plugin_dir.name:
        raise ManifestError(
            f"{path}: id '{plugin['id']}' does not match directory '{plugin_dir.name}'"
        )

    perms_raw = plugin.get("permissions", [])
    if not isinstance(perms_raw, list):
        raise ManifestError(f"{path}: 'permissions' must be an array")
    perms: set[str] = set()
    for p in perms_raw:
        if p not in ALLOWED_PERMISSIONS:
            raise ManifestError(f"{path}: unknown permission '{p}'")
        perms.add(p)

    entry = plugin["entry"]
    if ":" not in entry:
        raise ManifestError(f"{path}: 'entry' must be 'module:Class'")
    module, cls = entry.split(":", 1)

    return Manifest(
        root=plugin_dir,
        id=plugin["id"],
        name=plugin["name"],
        version=plugin["version"],
        api_version=api_version,
        description=plugin["description"],
        author=plugin["author"],
        entry_module=module,
        entry_class=cls,
        icon=plugin["icon"],
        permissions=frozenset(perms),
    )
```

- [ ] **Step 4: Run tests**

Run: `poetry run pytest tests/core/test_manifest.py -v`
Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add smartass/core/manifest.py tests/core/test_manifest.py
git commit -m "feat(core): plugin manifest loader with validation"
```

---

### Task 1.4: `smartass/core/plugin_interface.py` (Part A — SettingsSchema + fields)

**Files:**
- Create: `smartass/core/plugin_interface.py`
- Create: `tests/core/test_plugin_schema.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/core/test_plugin_schema.py
import pytest

from smartass.core.plugin_interface import (
    BoolField,
    IntField,
    SchemaError,
    SecretField,
    SelectField,
    SettingsSchema,
    StringField,
)


def test_string_field_validates_type():
    f = StringField(key="city", label="City", default="Berlin")
    assert f.validate("Munich") == "Munich"
    with pytest.raises(SchemaError):
        f.validate(123)


def test_string_field_required():
    f = StringField(key="city", label="City", required=True)
    with pytest.raises(SchemaError, match="required"):
        f.validate("")


def test_int_field_bounds():
    f = IntField(key="poll", label="Poll", default=15, min=1, max=60)
    assert f.validate(30) == 30
    with pytest.raises(SchemaError, match="out of range"):
        f.validate(120)
    with pytest.raises(SchemaError, match="out of range"):
        f.validate(0)


def test_bool_field():
    f = BoolField(key="x", label="X", default=False)
    assert f.validate(True) is True
    with pytest.raises(SchemaError):
        f.validate("true")


def test_select_field_restricts_options():
    f = SelectField(key="units", label="Units", default="metric", options=("metric", "imperial"))
    assert f.validate("imperial") == "imperial"
    with pytest.raises(SchemaError, match="not in options"):
        f.validate("kelvin")


def test_secret_field_is_string_with_redacted_repr():
    f = SecretField(key="api_key", label="API Key")
    assert f.validate("s3cret") == "s3cret"
    assert "s3cret" not in repr(f)


def test_schema_validate_dict_returns_cleaned_values():
    schema = SettingsSchema(
        fields=(
            StringField(key="city", label="City", default="Berlin"),
            IntField(key="poll", label="Poll", default=15, min=1, max=60),
        )
    )
    cleaned = schema.validate({"city": "Munich", "poll": 20})
    assert cleaned == {"city": "Munich", "poll": 20}


def test_schema_applies_defaults_for_missing():
    schema = SettingsSchema(
        fields=(
            StringField(key="city", label="City", default="Berlin"),
            IntField(key="poll", label="Poll", default=15, min=1, max=60),
        )
    )
    cleaned = schema.validate({})
    assert cleaned == {"city": "Berlin", "poll": 15}


def test_schema_rejects_unknown_keys():
    schema = SettingsSchema(
        fields=(StringField(key="city", label="City", default="Berlin"),)
    )
    with pytest.raises(SchemaError, match="unknown field"):
        schema.validate({"city": "Munich", "trojan": "yes"})


def test_schema_to_json_serializable():
    schema = SettingsSchema(
        fields=(
            StringField(key="city", label="City", default="Berlin", required=True),
            SelectField(key="units", label="Units", default="metric", options=("metric", "imperial")),
        )
    )
    data = schema.to_dict()
    assert data == {
        "fields": [
            {
                "type": "string",
                "key": "city",
                "label": "City",
                "default": "Berlin",
                "required": True,
                "description": "",
            },
            {
                "type": "select",
                "key": "units",
                "label": "Units",
                "default": "metric",
                "required": False,
                "description": "",
                "options": ["metric", "imperial"],
            },
        ]
    }
```

- [ ] **Step 2: Run test — expect fail**

Run: `poetry run pytest tests/core/test_plugin_schema.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement — settings schema only (no ABC yet)**

```python
# smartass/core/plugin_interface.py
"""PluginInterface ABC and supporting types (settings schema, context).

This module is imported by both the daemon and the tray. It MUST NOT import
Qt or D-Bus libraries directly; those are injected via PluginContext.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
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
```

- [ ] **Step 4: Run tests**

Run: `poetry run pytest tests/core/test_plugin_schema.py -v`
Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add smartass/core/plugin_interface.py tests/core/test_plugin_schema.py
git commit -m "feat(core): declarative SettingsSchema with typed fields"
```

---

### Task 1.5: `plugin_interface.py` (Part B — PluginContext + PluginInterface ABC)

**Files:**
- Modify: `smartass/core/plugin_interface.py` (append ABC + context)
- Create: `tests/core/test_plugin_interface.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/core/test_plugin_interface.py
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
```

- [ ] **Step 2: Run test — expect fail**

Run: `poetry run pytest tests/core/test_plugin_interface.py -v`
Expected: `PluginContext` / `PluginInterface` missing.

- [ ] **Step 3: Append implementation to `smartass/core/plugin_interface.py`**

Append at end of file:

```python
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
        """Return an optional plugin-specific D-Bus interface class.

        The concrete class type is resolved by the daemon's D-Bus backend.
        Return None for plugins that do not publish D-Bus methods.
        """
        return None
```

- [ ] **Step 4: Run tests**

Run: `poetry run pytest tests/core/test_plugin_interface.py tests/core/test_plugin_schema.py -v`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add smartass/core/plugin_interface.py tests/core/test_plugin_interface.py
git commit -m "feat(core): PluginInterface ABC + PluginContext"
```

---

### Task 1.6: `smartass/core/config.py` — ConfigStore + migrations

**Files:**
- Create: `smartass/core/config.py`
- Create: `tests/core/test_config.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/core/test_config.py
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
```

- [ ] **Step 2: Run test — expect fail**

Run: `poetry run pytest tests/core/test_config.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement**

```python
# smartass/core/config.py
"""Typed TOML config store with atomic writes and migration hooks."""

from __future__ import annotations

import os
import tempfile
import tomllib
from pathlib import Path
from typing import Any

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
    # Future migrations chain here.
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
            # fsync the directory so the rename itself is durable
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
        # ensure defaults populated on first access
        self._ensure_defaults()

    def _ensure_defaults(self) -> None:
        raw = self._store.get_plugin_values(self._id)
        cleaned = self._schema.validate(raw)  # fills defaults for missing
        self._store.set_plugin_values(self._id, cleaned, self._schema)

    def get(self, key: str) -> Any:
        return self._store.get_plugin_values(self._id).get(key)

    def all(self) -> dict[str, Any]:
        return self._store.get_plugin_values(self._id)

    def set(self, values: dict[str, Any]) -> dict[str, Any]:
        merged = {**self.all(), **values}
        return self._store.set_plugin_values(self._id, merged, self._schema)
```

- [ ] **Step 4: Run tests**

Run: `poetry run pytest tests/core/test_config.py -v`
Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add smartass/core/config.py tests/core/test_config.py
git commit -m "feat(core): ConfigStore with atomic writes, migrations, PluginConfig"
```

---

## Phase 2 — Daemon

### Task 2.1: `smartass/daemon/http.py` — shared AsyncHttpClient

**Files:**
- Create: `smartass/daemon/http.py`
- Create: `tests/daemon/test_http.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/daemon/test_http.py
import httpx
import pytest
import respx

from smartass.daemon.http import AsyncHttpClient


@pytest.mark.asyncio
async def test_get_json_returns_parsed_body():
    client = AsyncHttpClient(user_agent="smartass-test/0.1", timeout=2.0)
    try:
        with respx.mock(assert_all_called=True) as mock:
            mock.get("https://example.test/api").mock(
                return_value=httpx.Response(200, json={"ok": True, "n": 3})
            )
            data = await client.get_json("https://example.test/api")
            assert data == {"ok": True, "n": 3}
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_get_json_raises_on_5xx():
    client = AsyncHttpClient(user_agent="smartass-test/0.1", timeout=2.0)
    try:
        with respx.mock() as mock:
            mock.get("https://example.test/api").mock(
                return_value=httpx.Response(503, text="down")
            )
            with pytest.raises(httpx.HTTPStatusError):
                await client.get_json("https://example.test/api")
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_sets_user_agent_header():
    client = AsyncHttpClient(user_agent="smartass/0.1.0", timeout=2.0)
    try:
        with respx.mock() as mock:
            route = mock.get("https://example.test/").mock(
                return_value=httpx.Response(200, json={})
            )
            await client.get_json("https://example.test/")
            assert route.calls.last.request.headers["user-agent"] == "smartass/0.1.0"
    finally:
        await client.aclose()
```

- [ ] **Step 2: Run test**

Run: `poetry run pytest tests/daemon/test_http.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement**

```python
# smartass/daemon/http.py
"""Thin async HTTP client shared by plugins with the net.http permission."""

from __future__ import annotations

from typing import Any

import httpx


class AsyncHttpClient:
    def __init__(self, user_agent: str, timeout: float = 10.0) -> None:
        self._client = httpx.AsyncClient(
            timeout=timeout,
            headers={"User-Agent": user_agent},
        )

    async def get_json(self, url: str, **kwargs: Any) -> Any:
        resp = await self._client.get(url, **kwargs)
        resp.raise_for_status()
        return resp.json()

    async def aclose(self) -> None:
        await self._client.aclose()
```

- [ ] **Step 4: Run tests**

Run: `poetry run pytest tests/daemon/test_http.py -v`
Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add smartass/daemon/http.py tests/daemon/test_http.py
git commit -m "feat(daemon): async HTTP client wrapper"
```

---

### Task 2.2: `smartass/daemon/plugin_manager.py` — discovery

**Files:**
- Create: `smartass/daemon/plugin_manager.py`
- Create: `tests/daemon/test_plugin_manager_discovery.py`
- Create: `tests/_fixtures/__init__.py`
- Create: `tests/_fixtures/hello_plugin.py` (helper — a minimal in-test plugin)

- [ ] **Step 1: Write a helper plugin (fixture) for tests**

```python
# tests/_fixtures/hello_plugin.py
"""A minimal plugin used only by tests. Not bundled in the app."""

from smartass.core.plugin_interface import PluginInterface, SettingsSchema, StringField


class HelloPlugin(PluginInterface):
    id = "hello"

    def build_tab(self, parent):  # pragma: no cover
        return None

    def settings_schema(self) -> SettingsSchema:
        return SettingsSchema(fields=(StringField(key="greeting", label="Greeting", default="hi"),))
```

- [ ] **Step 2: Write the failing test**

```python
# tests/daemon/test_plugin_manager_discovery.py
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
```

- [ ] **Step 3: Run test — expect fail**

Run: `poetry run pytest tests/daemon/test_plugin_manager_discovery.py -v`
Expected: ImportError.

- [ ] **Step 4: Implement discovery (not lifecycle yet)**

```python
# smartass/daemon/plugin_manager.py
"""Discovers, loads, and manages plugins' lifecycles.

Discovery is dir-based: each plugin is a directory under one of the roots
with a manifest.toml. A plugin's Python module is loaded via importlib with
a private module name 'smartass_plugin_<id>' so names don't collide.
"""

from __future__ import annotations

import importlib.util
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from smartass.core.manifest import Manifest, ManifestError, load_manifest
from smartass.core.plugin_interface import PluginInterface

log = logging.getLogger(__name__)


@dataclass
class DiscoveredPlugin:
    manifest: Manifest
    # populated once load_plugin_class() has run:
    plugin_class: Optional[type[PluginInterface]] = None


@dataclass
class PluginManager:
    config_store: object  # ConfigStore, typed loosely to avoid import cycle
    roots: list[Path] = field(default_factory=list)

    def discover(self) -> list[DiscoveredPlugin]:
        """Scan all roots; return DiscoveredPlugin per valid manifest.

        If the same plugin id appears in multiple roots, the first root
        wins (user plugins shadow system plugins).
        """
        seen: dict[str, DiscoveredPlugin] = {}
        for root in self.roots:
            if not root.is_dir():
                continue
            for child in sorted(root.iterdir()):
                if not child.is_dir():
                    continue
                try:
                    m = load_manifest(child)
                except ManifestError as e:
                    log.warning("skipping invalid plugin %s: %s", child, e)
                    continue
                if m.id in seen:
                    log.info("plugin %s already discovered in earlier root", m.id)
                    continue
                seen[m.id] = DiscoveredPlugin(manifest=m)
        return list(seen.values())

    def load_plugin_class(self, dp: DiscoveredPlugin) -> type[PluginInterface]:
        if dp.plugin_class is not None:
            return dp.plugin_class

        m = dp.manifest
        module_name = f"smartass_plugin_{m.id}"
        module_path = m.root / f"{m.entry_module}.py"
        if not module_path.is_file():
            raise ManifestError(f"entry module not found: {module_path}")

        spec = importlib.util.spec_from_file_location(
            module_name, module_path, submodule_search_locations=[str(m.root)]
        )
        if spec is None or spec.loader is None:
            raise ManifestError(f"cannot build import spec for {module_path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        try:
            spec.loader.exec_module(module)
        except Exception as e:
            sys.modules.pop(module_name, None)
            raise ManifestError(f"failed importing {module_path}: {e}") from e

        cls = getattr(module, m.entry_class, None)
        if cls is None or not isinstance(cls, type) or not issubclass(cls, PluginInterface):
            raise ManifestError(
                f"{module_path}: {m.entry_class} is not a PluginInterface subclass"
            )
        dp.plugin_class = cls
        return cls
```

- [ ] **Step 5: Run tests**

Run: `poetry run pytest tests/daemon/test_plugin_manager_discovery.py -v`
Expected: pass.

- [ ] **Step 6: Commit**

```bash
git add smartass/daemon/plugin_manager.py tests/daemon/test_plugin_manager_discovery.py tests/_fixtures/
git commit -m "feat(daemon): plugin discovery from user + system roots"
```

---

### Task 2.3: `plugin_manager.py` — lifecycle (enable/disable/reload)

**Files:**
- Modify: `smartass/daemon/plugin_manager.py` (append)
- Create: `tests/daemon/test_plugin_manager_lifecycle.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/daemon/test_plugin_manager_lifecycle.py
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
async def test_enable_fires_on_load_then_on_start(tmp_path):
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
async def test_disable_fires_on_stop_then_on_unload(tmp_path):
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
async def test_enable_idempotent(tmp_path):
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
async def test_boot_enables_all_from_config(tmp_path):
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
async def test_shutdown_stops_all_running(tmp_path):
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
```

- [ ] **Step 2: Run test — expect fail**

Run: `poetry run pytest tests/daemon/test_plugin_manager_lifecycle.py -v`
Expected: AttributeError — methods not implemented.

- [ ] **Step 3: Append implementation**

At the bottom of `smartass/daemon/plugin_manager.py`, add:

```python
# (append to the existing file, below load_plugin_class)

import asyncio

from smartass.core.config import ConfigStore, PluginConfig
from smartass.core import paths as _paths
from smartass.core.plugin_interface import PluginContext


@dataclass
class _RunningPlugin:
    dp: DiscoveredPlugin
    instance: PluginInterface


class PluginManager(PluginManager):  # type: ignore[no-redef]
    """Extension: lifecycle methods.

    (Same class; split for readability. This block MUST be in the same file.)
    """


# NOTE — Cleaner: implement the lifecycle directly on the original class.
# Rewrite the class definition in place rather than re-declaring it.
```

Replace the entire content of `smartass/daemon/plugin_manager.py` with the consolidated version:

```python
# smartass/daemon/plugin_manager.py
"""Discovers, loads, and manages plugins' lifecycles."""

from __future__ import annotations

import asyncio
import importlib.util
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from smartass.core import paths as _paths
from smartass.core.config import ConfigStore, PluginConfig
from smartass.core.manifest import Manifest, ManifestError, load_manifest
from smartass.core.plugin_interface import PluginContext, PluginInterface

log = logging.getLogger(__name__)


@dataclass
class DiscoveredPlugin:
    manifest: Manifest
    plugin_class: Optional[type[PluginInterface]] = None


@dataclass
class _RunningPlugin:
    dp: DiscoveredPlugin
    instance: PluginInterface


class PluginManager:
    def __init__(
        self,
        config_store: Optional[ConfigStore],
        roots: list[Path],
        http_factory: Optional[callable] = None,  # type: ignore[type-arg]
    ) -> None:
        self.config_store = config_store
        self.roots = list(roots)
        self._http_factory = http_factory
        self._discovered: dict[str, DiscoveredPlugin] = {}
        self._running: dict[str, _RunningPlugin] = {}

    # ---- discovery ----

    def discover(self) -> list[DiscoveredPlugin]:
        found: dict[str, DiscoveredPlugin] = {}
        for root in self.roots:
            if not root.is_dir():
                continue
            for child in sorted(root.iterdir()):
                if not child.is_dir():
                    continue
                try:
                    m = load_manifest(child)
                except ManifestError as e:
                    log.warning("skipping invalid plugin %s: %s", child, e)
                    continue
                if m.id in found:
                    log.info("plugin %s shadowed by earlier root", m.id)
                    continue
                found[m.id] = DiscoveredPlugin(manifest=m)
        self._discovered = found
        return list(found.values())

    def load_plugin_class(self, dp: DiscoveredPlugin) -> type[PluginInterface]:
        if dp.plugin_class is not None:
            return dp.plugin_class
        m = dp.manifest
        module_name = f"smartass_plugin_{m.id}"
        module_path = m.root / f"{m.entry_module}.py"
        if not module_path.is_file():
            raise ManifestError(f"entry module not found: {module_path}")
        spec = importlib.util.spec_from_file_location(
            module_name, module_path, submodule_search_locations=[str(m.root)]
        )
        if spec is None or spec.loader is None:
            raise ManifestError(f"cannot build import spec for {module_path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        try:
            spec.loader.exec_module(module)
        except Exception as e:
            sys.modules.pop(module_name, None)
            raise ManifestError(f"failed importing {module_path}: {e}") from e
        cls = getattr(module, m.entry_class, None)
        if cls is None or not isinstance(cls, type) or not issubclass(cls, PluginInterface):
            raise ManifestError(
                f"{module_path}: {m.entry_class} is not a PluginInterface subclass"
            )
        dp.plugin_class = cls
        return cls

    # ---- lifecycle ----

    def is_running(self, plugin_id: str) -> bool:
        return plugin_id in self._running

    def running_ids(self) -> list[str]:
        return sorted(self._running.keys())

    def _make_context(self, dp: DiscoveredPlugin) -> PluginContext:
        m = dp.manifest
        data_dir = _paths.plugin_data_dir(m.id)
        data_dir.mkdir(parents=True, exist_ok=True)
        http = None
        if "net.http" in m.permissions and self._http_factory is not None:
            http = self._http_factory()
        schema = None  # filled in after instance construction if needed
        logger = logging.getLogger(f"smartass.plugins.{m.id}")
        # config is built once the plugin provides its schema (see enable())
        return PluginContext(
            config=None,
            data_dir=data_dir,
            log=logger,
            http=http,
            bus=None,  # set later by the D-Bus service when it attaches
            signals=None,
            permissions=m.permissions,
        )

    async def enable(self, plugin_id: str) -> None:
        if plugin_id in self._running:
            log.debug("enable(%s): already running", plugin_id)
            return
        dp = self._discovered.get(plugin_id)
        if dp is None:
            raise KeyError(f"unknown plugin: {plugin_id}")
        cls = self.load_plugin_class(dp)
        ctx = self._make_context(dp)
        instance = cls(ctx)
        # attach PluginConfig now that we know the schema
        if self.config_store is not None:
            ctx.config = PluginConfig(self.config_store, plugin_id, instance.settings_schema())
        try:
            instance.on_load()
            await instance.on_start()
        except Exception:
            log.exception("plugin %s failed to start", plugin_id)
            raise
        self._running[plugin_id] = _RunningPlugin(dp=dp, instance=instance)
        if self.config_store is not None:
            self.config_store.set_enabled(plugin_id, True)
            self.config_store.save()

    async def disable(self, plugin_id: str) -> None:
        rp = self._running.pop(plugin_id, None)
        if rp is None:
            log.debug("disable(%s): not running", plugin_id)
            if self.config_store is not None and self.config_store.is_enabled(plugin_id):
                self.config_store.set_enabled(plugin_id, False)
                self.config_store.save()
            return
        try:
            await rp.instance.on_stop()
        finally:
            rp.instance.on_unload()
        if self.config_store is not None:
            self.config_store.set_enabled(plugin_id, False)
            self.config_store.save()

    async def boot(self) -> None:
        """Bring up every plugin marked enabled in config."""
        if self.config_store is None:
            return
        ids = list(self.config_store.data.get("smartass", {}).get("enabled_plugins", []))
        for pid in ids:
            try:
                await self.enable(pid)
            except Exception:
                log.exception("boot: plugin %s failed to start; continuing", pid)

    async def shutdown(self) -> None:
        for pid in list(self._running):
            try:
                await self.disable(pid)
            except Exception:
                log.exception("shutdown: plugin %s failed to stop", pid)
```

- [ ] **Step 4: Run tests**

Run: `poetry run pytest tests/daemon/ -v`
Expected: all discovery + lifecycle tests pass.

- [ ] **Step 5: Commit**

```bash
git add smartass/daemon/plugin_manager.py tests/daemon/test_plugin_manager_lifecycle.py
git commit -m "feat(daemon): plugin lifecycle (enable/disable/boot/shutdown)"
```

---

### Task 2.4: `smartass/daemon/service.py` — D-Bus Core interface

**Files:**
- Create: `smartass/daemon/service.py`
- Create: `tests/daemon/test_service_core.py`

- [ ] **Step 1: Write the failing test (integration via dbus-next private bus)**

```python
# tests/daemon/test_service_core.py
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
async def test_ping_returns_pong(tmp_path):
    """Requires a private session bus — wrap test runs with dbus-run-session."""
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
async def test_list_plugins_reports_enabled_state(tmp_path):
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
    rows = await iface.call_list_plugins()
    ids = {r[0] for r in rows}
    assert "hello" in ids
    row = next(r for r in rows if r[0] == "hello")
    assert row[4] is True  # installed
    assert row[5] is False  # enabled

    bus.disconnect()
    client_bus.disconnect()


@pytest.mark.asyncio
async def test_enable_plugin_persists_and_reports(tmp_path):
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
    rows = await iface.call_list_plugins()
    row = next(r for r in rows if r[0] == "hello")
    assert row[5] is True

    bus.disconnect()
    client_bus.disconnect()
```

- [ ] **Step 2: Run test — expect fail (module missing)**

Run: `dbus-run-session -- poetry run pytest tests/daemon/test_service_core.py -v`
Expected: ImportError for `CoreService`.

- [ ] **Step 3: Implement**

```python
# smartass/daemon/service.py
"""D-Bus Core service (ai.talonic.Smartass.Core)."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Optional

import tomli_w
from dbus_next.service import ServiceInterface, dbus_property, method, signal

from smartass.core import dbus_names
from smartass.core.config import ConfigStore, InvalidConfig
from smartass.daemon.plugin_manager import PluginManager

log = logging.getLogger(__name__)


class CoreService(ServiceInterface):
    """Exports ai.talonic.Smartass.Core on /ai/talonic/Smartass."""

    def __init__(self, pm: PluginManager, store: ConfigStore) -> None:
        super().__init__(dbus_names.CORE_IFACE)
        self._pm = pm
        self._store = store

    # --- Methods ---

    @method()
    def Ping(self) -> "s":  # type: ignore[name-defined]
        from smartass import __version__
        return f"pong {__version__}"

    @method()
    def ListPlugins(self) -> "a(sssbb)":  # type: ignore[name-defined]
        """Returns a list of (id, name, version, description, installed, enabled)."""
        rows: list[list[Any]] = []
        for dp in self._pm.discover():
            m = dp.manifest
            rows.append(
                [
                    m.id,
                    m.name,
                    m.version,
                    m.description,
                    True,  # installed (it was discovered)
                    self._store.is_enabled(m.id),
                ]
            )
        return rows

    @method()
    async def EnablePlugin(self, plugin_id: "s") -> None:  # type: ignore[name-defined]
        await self._pm.enable(plugin_id)
        self.PluginEnabled(plugin_id)

    @method()
    async def DisablePlugin(self, plugin_id: "s") -> None:  # type: ignore[name-defined]
        await self._pm.disable(plugin_id)
        self.PluginDisabled(plugin_id)

    @method()
    def GetConfig(self, plugin_id: "s") -> "a{sv}":  # type: ignore[name-defined]
        return _to_variant_dict(self._store.get_plugin_values(plugin_id))

    @method()
    def SetConfig(
        self,
        plugin_id: "s",  # type: ignore[name-defined]
        values: "a{sv}",  # type: ignore[name-defined]
    ) -> None:
        # schema validation happens in PluginConfig via the running instance;
        # when plugin is not running, use its discovered class's schema.
        schema = _resolve_schema(self._pm, plugin_id)
        try:
            self._store.set_plugin_values(plugin_id, _from_variant_dict(values), schema)
        except InvalidConfig as e:
            raise ValueError(str(e)) from e
        self._store.save()
        self.SettingsChanged(plugin_id, _to_variant_dict(self._store.get_plugin_values(plugin_id)))

    @method()
    def GetSettingsSchema(self, plugin_id: "s") -> "s":  # type: ignore[name-defined]
        schema = _resolve_schema(self._pm, plugin_id)
        return json.dumps(schema.to_dict())

    @method()
    def ExportAll(self) -> "s":  # type: ignore[name-defined]
        # Only config + opt-in plugin_state for running plugins
        from datetime import datetime, timezone
        from smartass import __version__

        blob: dict[str, Any] = {
            "meta": {
                "exported_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "smartass_version": __version__,
                "config_schema": self._store.data["smartass"]["version"],
            },
            "config": self._store.data,
            "plugin_state": {},
        }
        for pid in self._pm.running_ids():
            inst = self._pm._running[pid].instance  # noqa: SLF001 — internal
            state = inst.export_state() or {}
            if state:
                blob["plugin_state"][pid] = state
        return tomli_w.dumps(blob)

    @method()
    async def ImportAll(
        self,
        toml_blob: "s",  # type: ignore[name-defined]
        strategy: "s",  # type: ignore[name-defined]
    ) -> None:
        import tomllib

        if strategy not in ("replace", "merge"):
            raise ValueError("strategy must be 'replace' or 'merge'")
        data = tomllib.loads(toml_blob)
        imported_config = data.get("config", {})

        if strategy == "replace":
            self._store._data = imported_config or self._store.data  # noqa: SLF001
        else:
            merged = dict(self._store.data)
            smart_new = imported_config.get("smartass", {})
            merged["smartass"].update(smart_new)
            plugins_new = imported_config.get("plugins", {})
            merged.setdefault("plugins", {})
            for k, v in plugins_new.items():
                merged["plugins"].setdefault(k, {}).update(v)
            self._store._data = merged  # noqa: SLF001
        self._store.save()

        # Hot-reload currently-running plugins whose state changed
        for pid in self._pm.running_ids():
            await self._pm.disable(pid)
        for pid in self._store.data["smartass"]["enabled_plugins"]:
            await self._pm.enable(pid)

        # Apply plugin_state after reloading
        for pid, state in (data.get("plugin_state") or {}).items():
            if self._pm.is_running(pid):
                self._pm._running[pid].instance.import_state(state)  # noqa: SLF001

    @method()
    async def ReloadDaemon(self) -> None:
        await self._pm.shutdown()
        self._pm.discover()
        await self._pm.boot()

    @method()
    def InstallPlugin(self, source_path: "s") -> "s":  # type: ignore[name-defined]
        raise NotImplementedError("InstallPlugin not yet supported; drop a dir into ~/.local/share/smartass/plugins/")

    @method()
    def UninstallPlugin(self, plugin_id: "s") -> None:  # type: ignore[name-defined]
        raise NotImplementedError("UninstallPlugin not yet supported")

    # --- Signals ---

    @signal()
    def PluginEnabled(self, plugin_id: "s") -> "s":  # type: ignore[name-defined]
        return plugin_id

    @signal()
    def PluginDisabled(self, plugin_id: "s") -> "s":  # type: ignore[name-defined]
        return plugin_id

    @signal()
    def PluginInstalled(self, plugin_id: "s") -> "s":  # type: ignore[name-defined]
        return plugin_id

    @signal()
    def PluginUninstalled(self, plugin_id: "s") -> "s":  # type: ignore[name-defined]
        return plugin_id

    @signal()
    def SettingsChanged(
        self, plugin_id: "s", values: "a{sv}"  # type: ignore[name-defined]
    ) -> "(sa{sv})":  # type: ignore[name-defined]
        return [plugin_id, values]

    @signal()
    def PluginStateUpdated(
        self, plugin_id: "s", payload: "a{sv}"  # type: ignore[name-defined]
    ) -> "(sa{sv})":  # type: ignore[name-defined]
        return [plugin_id, payload]


# --- helpers ---


def _resolve_schema(pm: PluginManager, plugin_id: str):
    dp = pm._discovered.get(plugin_id)  # noqa: SLF001
    if dp is None:
        raise ValueError(f"unknown plugin: {plugin_id}")
    cls = pm.load_plugin_class(dp)
    # instantiate with a null-context just to grab schema (schemas must not
    # depend on context — enforced by convention)
    from smartass.core.plugin_interface import PluginContext
    dummy_ctx = PluginContext(
        config=None, data_dir=dp.manifest.root, log=log,
        http=None, bus=None, signals=None, permissions=dp.manifest.permissions,
    )
    return cls(dummy_ctx).settings_schema()


def _to_variant_dict(d: dict[str, Any]) -> dict[str, Any]:
    """Wrap plain Python values as dbus-next 'v' Variants."""
    from dbus_next import Variant

    out: dict[str, Any] = {}
    for k, v in d.items():
        sig = _dbus_sig(v)
        out[k] = Variant(sig, v)
    return out


def _from_variant_dict(d: dict[str, Any]) -> dict[str, Any]:
    # dbus-next hands us Variant objects on inbound a{sv}
    return {k: (v.value if hasattr(v, "value") else v) for k, v in d.items()}


def _dbus_sig(v: Any) -> str:
    if isinstance(v, bool):
        return "b"
    if isinstance(v, int):
        return "i"
    if isinstance(v, float):
        return "d"
    if isinstance(v, str):
        return "s"
    if isinstance(v, list):
        return "av"
    if isinstance(v, dict):
        return "a{sv}"
    raise TypeError(f"unsupported value for D-Bus serialization: {type(v)!r}")
```

- [ ] **Step 4: Run tests under a private bus**

Run: `dbus-run-session -- poetry run pytest tests/daemon/test_service_core.py -v`
Expected: all three tests pass.

If `dbus-run-session` is not installed, install it: `sudo apt-get install -y dbus-daemon` (provides `dbus-run-session`).

- [ ] **Step 5: Commit**

```bash
git add smartass/daemon/service.py tests/daemon/test_service_core.py
git commit -m "feat(daemon): D-Bus Core service (list/enable/get-set/import-export)"
```

---

### Task 2.5: `smartass/daemon/__main__.py` — entrypoint

**Files:**
- Create: `smartass/daemon/__main__.py`

- [ ] **Step 1: Implement the entrypoint**

```python
# smartass/daemon/__main__.py
"""Smartass daemon entrypoint."""

from __future__ import annotations

import asyncio
import logging
import signal
import sys
from logging.handlers import RotatingFileHandler

from dbus_next.aio import MessageBus

from smartass import __version__
from smartass.core import dbus_names, paths
from smartass.core.config import ConfigStore
from smartass.daemon.http import AsyncHttpClient
from smartass.daemon.plugin_manager import PluginManager
from smartass.daemon.service import CoreService

log = logging.getLogger("smartass.daemon")


def _configure_logging() -> None:
    paths.ensure_user_dirs()
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    handler = RotatingFileHandler(
        paths.cache_dir() / "daemon.log", maxBytes=1_000_000, backupCount=5
    )
    handler.setFormatter(fmt)
    root.addHandler(handler)
    stderr = logging.StreamHandler(sys.stderr)
    stderr.setFormatter(fmt)
    root.addHandler(stderr)


async def _run() -> int:
    _configure_logging()
    log.info("starting smartass daemon v%s", __version__)

    store = ConfigStore(paths.config_file())
    store.load()

    def http_factory() -> AsyncHttpClient:
        return AsyncHttpClient(user_agent=f"smartass/{__version__}")

    pm = PluginManager(
        config_store=store,
        roots=paths.plugin_roots(),
        http_factory=http_factory,
    )
    pm.discover()

    bus = await MessageBus().connect()
    svc = CoreService(pm, store)
    bus.export(dbus_names.CORE_PATH, svc)
    reply = await bus.request_name(dbus_names.SERVICE)
    from dbus_next.constants import RequestNameReply

    if reply != RequestNameReply.PRIMARY_OWNER:
        log.error("could not acquire bus name %s (reply=%s)", dbus_names.SERVICE, reply)
        return 2

    await pm.boot()
    log.info("daemon ready; booted plugins: %s", pm.running_ids())

    stop_event = asyncio.Event()

    def _signal_handler() -> None:
        log.info("signal received; shutting down")
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _signal_handler)

    await stop_event.wait()
    await pm.shutdown()
    bus.disconnect()
    log.info("daemon exit")
    return 0


def main() -> None:
    sys.exit(asyncio.run(_run()))


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Smoke-run the daemon manually**

Run (in one terminal):
```bash
dbus-run-session -- poetry run python -m smartass.daemon
```

From a second shell inside the same `dbus-run-session`:
```bash
busctl --user introspect ai.talonic.Smartass /ai/talonic/Smartass
busctl --user call ai.talonic.Smartass /ai/talonic/Smartass ai.talonic.Smartass.Core Ping
```

Expected: introspect shows Core methods; Ping replies `"s" "pong 0.1.0"`. `Ctrl-C` shuts daemon down cleanly.

- [ ] **Step 3: Commit**

```bash
git add smartass/daemon/__main__.py
git commit -m "feat(daemon): __main__ entrypoint with logging + signal handling"
```

---

## Phase 3 — Weather plugin (daemon-side + manifest)

### Task 3.1: `smartass/plugins/weather/api.py` — Open-Meteo client

**Files:**
- Create: `smartass/plugins/weather/__init__.py` (empty `"""Weather plugin."""`)
- Create: `smartass/plugins/weather/api.py`
- Create: `tests/plugins/weather/__init__.py` (empty)
- Create: `tests/plugins/weather/test_api.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/plugins/weather/test_api.py
import httpx
import pytest
import respx

from smartass.daemon.http import AsyncHttpClient
from smartass.plugins.weather.api import (
    GeocodingError,
    OpenMeteoClient,
    WeatherError,
)


@pytest.mark.asyncio
async def test_geocode_returns_first_hit():
    http = AsyncHttpClient(user_agent="smartass-test")
    try:
        with respx.mock() as mock:
            mock.get("https://geocoding-api.open-meteo.com/v1/search").mock(
                return_value=httpx.Response(
                    200,
                    json={
                        "results": [
                            {
                                "name": "Berlin",
                                "latitude": 52.52,
                                "longitude": 13.41,
                                "country_code": "DE",
                                "country": "Germany",
                            }
                        ]
                    },
                )
            )
            c = OpenMeteoClient(http)
            r = await c.geocode("Berlin")
            assert r.name == "Berlin"
            assert r.country_code == "DE"
            assert round(r.latitude, 2) == 52.52
            assert round(r.longitude, 2) == 13.41
    finally:
        await http.aclose()


@pytest.mark.asyncio
async def test_geocode_raises_when_no_results():
    http = AsyncHttpClient(user_agent="smartass-test")
    try:
        with respx.mock() as mock:
            mock.get("https://geocoding-api.open-meteo.com/v1/search").mock(
                return_value=httpx.Response(200, json={})
            )
            c = OpenMeteoClient(http)
            with pytest.raises(GeocodingError, match="no results"):
                await c.geocode("nowheresville")
    finally:
        await http.aclose()


@pytest.mark.asyncio
async def test_forecast_parses_current_and_daily():
    http = AsyncHttpClient(user_agent="smartass-test")
    try:
        with respx.mock() as mock:
            mock.get("https://api.open-meteo.com/v1/forecast").mock(
                return_value=httpx.Response(
                    200,
                    json={
                        "current": {
                            "time": "2026-04-21T10:00",
                            "temperature_2m": 13.2,
                            "weather_code": 3,
                            "relative_humidity_2m": 55,
                            "wind_speed_10m": 9.5,
                        },
                        "daily": {
                            "time": [
                                "2026-04-21",
                                "2026-04-22",
                                "2026-04-23",
                                "2026-04-24",
                                "2026-04-25",
                                "2026-04-26",
                                "2026-04-27",
                            ],
                            "temperature_2m_max": [15, 16, 14, 13, 12, 14, 15],
                            "temperature_2m_min": [5, 6, 5, 4, 3, 5, 6],
                            "weather_code": [3, 1, 2, 3, 45, 61, 1],
                        },
                    },
                )
            )
            c = OpenMeteoClient(http)
            w = await c.forecast(latitude=52.52, longitude=13.41, units="metric")
            assert w.current.temperature == 13.2
            assert w.current.weather_code == 3
            assert len(w.daily) == 7
            assert w.daily[0].temp_max == 15
            assert w.daily[0].temp_min == 5
    finally:
        await http.aclose()


@pytest.mark.asyncio
async def test_forecast_wraps_http_error():
    http = AsyncHttpClient(user_agent="smartass-test")
    try:
        with respx.mock() as mock:
            mock.get("https://api.open-meteo.com/v1/forecast").mock(
                return_value=httpx.Response(500, text="boom")
            )
            c = OpenMeteoClient(http)
            with pytest.raises(WeatherError):
                await c.forecast(latitude=0.0, longitude=0.0, units="metric")
    finally:
        await http.aclose()


@pytest.mark.asyncio
async def test_units_passed_to_api():
    http = AsyncHttpClient(user_agent="smartass-test")
    try:
        with respx.mock() as mock:
            route = mock.get("https://api.open-meteo.com/v1/forecast").mock(
                return_value=httpx.Response(
                    200,
                    json={
                        "current": {"time": "t", "temperature_2m": 0, "weather_code": 0,
                                    "relative_humidity_2m": 0, "wind_speed_10m": 0},
                        "daily": {"time": [], "temperature_2m_max": [],
                                  "temperature_2m_min": [], "weather_code": []},
                    },
                )
            )
            c = OpenMeteoClient(http)
            await c.forecast(latitude=1, longitude=2, units="imperial")
            params = dict(route.calls.last.request.url.params)
            assert params["temperature_unit"] == "fahrenheit"
            assert params["wind_speed_unit"] == "mph"
    finally:
        await http.aclose()
```

- [ ] **Step 2: Run test — expect fail**

Run: `poetry run pytest tests/plugins/weather/test_api.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement**

```python
# smartass/plugins/weather/api.py
"""Thin typed client for Open-Meteo (forecast) + its geocoding service."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


class WeatherError(Exception):
    pass


class GeocodingError(WeatherError):
    pass


@dataclass(frozen=True)
class GeoResult:
    name: str
    country: str
    country_code: str
    latitude: float
    longitude: float


@dataclass(frozen=True)
class Current:
    time: str
    temperature: float
    weather_code: int
    humidity: int
    wind_speed: float


@dataclass(frozen=True)
class DailyEntry:
    date: str
    temp_max: float
    temp_min: float
    weather_code: int


@dataclass(frozen=True)
class WeatherSnapshot:
    current: Current
    daily: list[DailyEntry]
    units: str


class OpenMeteoClient:
    def __init__(self, http: Any) -> None:
        # http is an AsyncHttpClient or anything with .get_json()
        self._http = http

    async def geocode(self, query: str) -> GeoResult:
        try:
            data = await self._http.get_json(
                GEOCODING_URL, params={"name": query, "count": 1, "language": "en"}
            )
        except httpx.HTTPError as e:
            raise GeocodingError(f"geocoding request failed: {e}") from e
        results = data.get("results") or []
        if not results:
            raise GeocodingError(f"no results for '{query}'")
        r = results[0]
        return GeoResult(
            name=r.get("name", query),
            country=r.get("country", ""),
            country_code=r.get("country_code", ""),
            latitude=float(r["latitude"]),
            longitude=float(r["longitude"]),
        )

    async def forecast(
        self, latitude: float, longitude: float, units: str = "metric"
    ) -> WeatherSnapshot:
        temp_unit = "celsius" if units == "metric" else "fahrenheit"
        wind_unit = "kmh" if units == "metric" else "mph"
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,weather_code,relative_humidity_2m,wind_speed_10m",
            "daily": "temperature_2m_max,temperature_2m_min,weather_code",
            "temperature_unit": temp_unit,
            "wind_speed_unit": wind_unit,
            "timezone": "auto",
        }
        try:
            data = await self._http.get_json(FORECAST_URL, params=params)
        except httpx.HTTPError as e:
            raise WeatherError(f"forecast request failed: {e}") from e
        cur = data.get("current") or {}
        daily = data.get("daily") or {}
        try:
            current = Current(
                time=str(cur["time"]),
                temperature=float(cur["temperature_2m"]),
                weather_code=int(cur["weather_code"]),
                humidity=int(cur.get("relative_humidity_2m", 0)),
                wind_speed=float(cur.get("wind_speed_10m", 0.0)),
            )
            days = list(
                zip(
                    daily.get("time", []),
                    daily.get("temperature_2m_max", []),
                    daily.get("temperature_2m_min", []),
                    daily.get("weather_code", []),
                )
            )
            daily_entries = [
                DailyEntry(
                    date=str(d),
                    temp_max=float(mx),
                    temp_min=float(mn),
                    weather_code=int(wc),
                )
                for (d, mx, mn, wc) in days
            ]
        except (KeyError, TypeError, ValueError) as e:
            raise WeatherError(f"malformed forecast payload: {e}") from e
        return WeatherSnapshot(current=current, daily=daily_entries, units=units)
```

- [ ] **Step 4: Run tests**

Run: `poetry run pytest tests/plugins/weather/test_api.py -v`
Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add smartass/plugins/weather/__init__.py smartass/plugins/weather/api.py tests/plugins/weather/
git commit -m "feat(weather): Open-Meteo client (geocoding + forecast)"
```

---

### Task 3.2: `smartass/plugins/weather/plugin.py` — plugin class + SQLite cache

**Files:**
- Create: `smartass/plugins/weather/plugin.py`
- Create: `tests/plugins/weather/test_plugin.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/plugins/weather/test_plugin.py
import logging
from types import SimpleNamespace

import httpx
import pytest
import respx

from smartass.core.plugin_interface import PluginContext
from smartass.daemon.http import AsyncHttpClient
from smartass.plugins.weather.plugin import WeatherPlugin


def _ctx(tmp_path, http) -> PluginContext:
    return PluginContext(
        config=SimpleNamespace(all=lambda: {"city": "Berlin", "units": "metric", "poll_minutes": 1}),
        data_dir=tmp_path,
        log=logging.getLogger("weather-test"),
        http=http,
        bus=None,
        signals=SimpleNamespace(),
        permissions=frozenset({"net.http"}),
    )


def test_schema_has_expected_fields(tmp_path):
    ctx = _ctx(tmp_path, http=None)
    p = WeatherPlugin(ctx)
    keys = [f.key for f in p.settings_schema().fields]
    assert set(keys) == {"city", "units", "poll_minutes"}


@pytest.mark.asyncio
async def test_refresh_populates_sqlite_cache(tmp_path):
    http = AsyncHttpClient(user_agent="smartass-test")
    try:
        with respx.mock() as mock:
            mock.get("https://geocoding-api.open-meteo.com/v1/search").mock(
                return_value=httpx.Response(
                    200,
                    json={
                        "results": [
                            {
                                "name": "Berlin",
                                "latitude": 52.5,
                                "longitude": 13.4,
                                "country_code": "DE",
                                "country": "Germany",
                            }
                        ]
                    },
                )
            )
            mock.get("https://api.open-meteo.com/v1/forecast").mock(
                return_value=httpx.Response(
                    200,
                    json={
                        "current": {
                            "time": "2026-04-21T10:00",
                            "temperature_2m": 13.2,
                            "weather_code": 3,
                            "relative_humidity_2m": 55,
                            "wind_speed_10m": 9.5,
                        },
                        "daily": {
                            "time": ["2026-04-21"],
                            "temperature_2m_max": [15],
                            "temperature_2m_min": [5],
                            "weather_code": [3],
                        },
                    },
                )
            )
            p = WeatherPlugin(_ctx(tmp_path, http))
            p.on_load()
            await p.refresh()
            snap = p.last_snapshot()
            assert snap is not None
            assert snap["current"]["temperature"] == 13.2
            assert len(snap["daily"]) == 1
    finally:
        await http.aclose()


@pytest.mark.asyncio
async def test_refresh_falls_back_to_cache_on_error(tmp_path):
    http = AsyncHttpClient(user_agent="smartass-test")
    try:
        with respx.mock() as mock:
            mock.get("https://geocoding-api.open-meteo.com/v1/search").mock(
                return_value=httpx.Response(
                    200,
                    json={
                        "results": [
                            {
                                "name": "Berlin",
                                "latitude": 52.5,
                                "longitude": 13.4,
                                "country_code": "DE",
                                "country": "Germany",
                            }
                        ]
                    },
                )
            )
            # First call succeeds
            mock.get("https://api.open-meteo.com/v1/forecast").mock(
                side_effect=[
                    httpx.Response(
                        200,
                        json={
                            "current": {
                                "time": "t",
                                "temperature_2m": 1.0,
                                "weather_code": 0,
                                "relative_humidity_2m": 0,
                                "wind_speed_10m": 0,
                            },
                            "daily": {
                                "time": [],
                                "temperature_2m_max": [],
                                "temperature_2m_min": [],
                                "weather_code": [],
                            },
                        },
                    ),
                    httpx.Response(503, text="down"),
                ]
            )
            p = WeatherPlugin(_ctx(tmp_path, http))
            p.on_load()
            await p.refresh()
            first = p.last_snapshot()
            await p.refresh()  # second call fails; cache should remain
            second = p.last_snapshot()
            assert second == first
            assert p.is_stale() is True
    finally:
        await http.aclose()


@pytest.mark.asyncio
async def test_start_and_stop_manage_background_task(tmp_path):
    p = WeatherPlugin(_ctx(tmp_path, http=None))
    p.on_load()
    await p.on_start()
    assert p._task is not None  # noqa: SLF001
    await p.on_stop()
    assert p._task is None  # noqa: SLF001
```

- [ ] **Step 2: Run test — expect fail**

Run: `poetry run pytest tests/plugins/weather/test_plugin.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement**

```python
# smartass/plugins/weather/plugin.py
"""Weather plugin — Open-Meteo, user-typed city, 7-day forecast."""

from __future__ import annotations

import asyncio
import json
import sqlite3
from contextlib import closing
from typing import Any, Optional

from smartass.core.plugin_interface import (
    IntField,
    PluginContext,
    PluginInterface,
    SelectField,
    SettingsSchema,
    StringField,
)
from smartass.plugins.weather.api import OpenMeteoClient, WeatherError


class WeatherPlugin(PluginInterface):
    id = "weather"

    def __init__(self, ctx: PluginContext) -> None:
        super().__init__(ctx)
        self._client: Optional[OpenMeteoClient] = None
        self._snapshot: Optional[dict[str, Any]] = None
        self._stale: bool = False
        self._task: Optional[asyncio.Task[None]] = None
        self._stop_event = asyncio.Event()
        self._db_path = ctx.data_dir / "data.db"

    # --- schema ---

    def settings_schema(self) -> SettingsSchema:
        return SettingsSchema(
            fields=(
                StringField(
                    key="city",
                    label="City",
                    default="Berlin",
                    required=True,
                    description="Name of the city to fetch weather for.",
                ),
                SelectField(
                    key="units",
                    label="Units",
                    default="metric",
                    options=("metric", "imperial"),
                ),
                IntField(
                    key="poll_minutes",
                    label="Refresh every (minutes)",
                    default=15,
                    min=1,
                    max=240,
                ),
            )
        )

    # --- UI side (stub in daemon; implemented in ui.py on tray) ---

    def build_tab(self, parent: Any) -> Any:
        from smartass.plugins.weather.ui import WeatherTab  # local import — tray-only
        return WeatherTab(parent, self)

    # --- Lifecycle ---

    def on_load(self) -> None:
        self._init_db()
        self._load_cached()
        if self.ctx.http is not None:
            self._client = OpenMeteoClient(self.ctx.http)

    async def on_start(self) -> None:
        self._stop_event.clear()
        self._task = asyncio.create_task(self._poll_loop(), name="weather-poll")

    async def on_stop(self) -> None:
        self._stop_event.set()
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass
            self._task = None

    # --- public API (called via D-Bus adaptor / tab) ---

    def last_snapshot(self) -> Optional[dict[str, Any]]:
        return self._snapshot

    def is_stale(self) -> bool:
        return self._stale

    async def refresh(self) -> None:
        if self._client is None:
            self._stale = True
            return
        cfg = self.ctx.config.all() if self.ctx.config else {"city": "Berlin", "units": "metric"}
        city = cfg.get("city", "Berlin")
        units = cfg.get("units", "metric")
        try:
            geo = await self._client.geocode(city)
            snap = await self._client.forecast(
                latitude=geo.latitude, longitude=geo.longitude, units=units
            )
        except WeatherError:
            self._stale = True
            return
        payload = {
            "city": geo.name,
            "country": geo.country_code,
            "units": units,
            "current": {
                "time": snap.current.time,
                "temperature": snap.current.temperature,
                "weather_code": snap.current.weather_code,
                "humidity": snap.current.humidity,
                "wind_speed": snap.current.wind_speed,
            },
            "daily": [
                {
                    "date": d.date,
                    "temp_max": d.temp_max,
                    "temp_min": d.temp_min,
                    "weather_code": d.weather_code,
                }
                for d in snap.daily
            ],
        }
        self._snapshot = payload
        self._stale = False
        self._save_cached(payload)

    # --- persistence ---

    def _init_db(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self._db_path)) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )
            conn.commit()

    def _load_cached(self) -> None:
        if not self._db_path.exists():
            return
        with closing(sqlite3.connect(self._db_path)) as conn:
            cur = conn.execute("SELECT value FROM cache WHERE key = 'snapshot'")
            row = cur.fetchone()
            if row is not None:
                self._snapshot = json.loads(row[0])
                self._stale = True  # cache is stale until next successful refresh

    def _save_cached(self, snap: dict[str, Any]) -> None:
        with closing(sqlite3.connect(self._db_path)) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO cache (key, value) VALUES ('snapshot', ?)",
                (json.dumps(snap),),
            )
            conn.commit()

    # --- polling loop ---

    async def _poll_loop(self) -> None:
        while not self._stop_event.is_set():
            await self.refresh()
            cfg = self.ctx.config.all() if self.ctx.config else {"poll_minutes": 15}
            minutes = int(cfg.get("poll_minutes", 15))
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=minutes * 60)
            except asyncio.TimeoutError:
                continue
```

- [ ] **Step 4: Run tests**

Run: `poetry run pytest tests/plugins/weather/test_plugin.py -v`
Expected: pass. (The `test_start_and_stop_manage_background_task` test doesn't need network — `refresh` short-circuits when `http` is None.)

- [ ] **Step 5: Commit**

```bash
git add smartass/plugins/weather/plugin.py tests/plugins/weather/test_plugin.py
git commit -m "feat(weather): WeatherPlugin with SQLite cache + polling loop"
```

---

### Task 3.3: `smartass/plugins/weather/manifest.toml`

**Files:**
- Create: `smartass/plugins/weather/manifest.toml`

- [ ] **Step 1: Write the manifest**

```toml
[plugin]
id            = "weather"
name          = "Weather"
version       = "0.1.0"
api_version   = 1
description   = "Current conditions and 7-day forecast via Open-Meteo"
author        = "Saurabh Khanduja"
entry         = "plugin:WeatherPlugin"
icon          = "weather-clear-symbolic"
permissions   = ["net.http"]
```

- [ ] **Step 2: Verify manifest parses**

Run in a Python shell (inside `poetry shell`):
```python
from pathlib import Path
from smartass.core.manifest import load_manifest
print(load_manifest(Path("smartass/plugins/weather")))
```

Expected: prints a `Manifest(...)` with `id='weather'`.

- [ ] **Step 3: Commit**

```bash
git add smartass/plugins/weather/manifest.toml
git commit -m "feat(weather): plugin manifest"
```

---

### Task 3.4: Daemon integration test — end-to-end enable Weather over D-Bus

**Files:**
- Create: `tests/integration/__init__.py`
- Create: `tests/integration/test_daemon_weather.py`

- [ ] **Step 1: Write the integration test**

```python
# tests/integration/test_daemon_weather.py
"""Requires dbus-run-session and live Open-Meteo-free tests (respx-mocked)."""

import asyncio
import textwrap
from pathlib import Path

import httpx
import pytest
import respx
from dbus_next.aio import MessageBus

from smartass.core import dbus_names
from smartass.core.config import ConfigStore
from smartass.daemon.http import AsyncHttpClient
from smartass.daemon.plugin_manager import PluginManager
from smartass.daemon.service import CoreService


@pytest.mark.asyncio
async def test_enable_weather_over_dbus(tmp_path):
    # Copy the bundled weather plugin dir under a temp root so the test is hermetic.
    source = Path("smartass/plugins/weather").resolve()
    root = tmp_path / "plugins"
    (root / "weather").mkdir(parents=True)
    for fn in ("manifest.toml", "plugin.py", "api.py", "__init__.py"):
        (root / "weather" / fn).write_text((source / fn).read_text())

    store = ConfigStore(tmp_path / "cfg.toml")
    store.load()

    def http_factory() -> AsyncHttpClient:
        return AsyncHttpClient(user_agent="smartass-test")

    pm = PluginManager(config_store=store, roots=[root], http_factory=http_factory)
    pm.discover()

    bus = await MessageBus().connect()
    svc = CoreService(pm, store)
    bus.export(dbus_names.CORE_PATH, svc)
    await bus.request_name(dbus_names.SERVICE)

    with respx.mock():
        respx.get("https://geocoding-api.open-meteo.com/v1/search").mock(
            return_value=httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "name": "Berlin",
                            "latitude": 52.5,
                            "longitude": 13.4,
                            "country_code": "DE",
                            "country": "Germany",
                        }
                    ]
                },
            )
        )
        respx.get("https://api.open-meteo.com/v1/forecast").mock(
            return_value=httpx.Response(
                200,
                json={
                    "current": {
                        "time": "t",
                        "temperature_2m": 13.2,
                        "weather_code": 3,
                        "relative_humidity_2m": 55,
                        "wind_speed_10m": 9.5,
                    },
                    "daily": {
                        "time": ["2026-04-21"],
                        "temperature_2m_max": [15],
                        "temperature_2m_min": [5],
                        "weather_code": [3],
                    },
                },
            )
        )

        client_bus = await MessageBus().connect()
        introspection = await client_bus.introspect(
            dbus_names.SERVICE, dbus_names.CORE_PATH
        )
        proxy = client_bus.get_proxy_object(
            dbus_names.SERVICE, dbus_names.CORE_PATH, introspection
        )
        core = proxy.get_interface(dbus_names.CORE_IFACE)

        rows = await core.call_list_plugins()
        assert any(r[0] == "weather" for r in rows)

        await core.call_enable_plugin("weather")
        # Give the polling loop one tick
        await asyncio.sleep(0.2)

        rows = await core.call_list_plugins()
        row = next(r for r in rows if r[0] == "weather")
        assert row[5] is True

        await core.call_disable_plugin("weather")
        client_bus.disconnect()

    await pm.shutdown()
    bus.disconnect()
```

- [ ] **Step 2: Run it under a private bus**

Run: `dbus-run-session -- poetry run pytest tests/integration/test_daemon_weather.py -v`
Expected: pass.

- [ ] **Step 3: Commit**

```bash
git add tests/integration/
git commit -m "test: end-to-end enable Weather plugin over D-Bus"
```

---

## Phase 4 — Tray

(Phases 4 and 5 have limited automated tests — Qt UI widgets are out of scope for MVP automated tests per the spec. Each task still ends in a manual smoke step + commit.)

### Task 4.1: `smartass/tray/daemon_client.py` — QtDBus proxy wrapper

**Files:**
- Create: `smartass/tray/daemon_client.py`

- [ ] **Step 1: Implement**

```python
# smartass/tray/daemon_client.py
"""QtDBus-based proxy wrapper around ai.talonic.Smartass.Core.

Exposes Qt signals for tabs to bind to. Methods are synchronous wrappers
around blocking QDBus calls (acceptable — tray is GUI-event driven, calls
are fast).
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from PySide6.QtCore import QObject, Signal
from PySide6.QtDBus import QDBusConnection, QDBusInterface, QDBusMessage

from smartass.core import dbus_names

log = logging.getLogger(__name__)


class DaemonClient(QObject):
    plugin_enabled = Signal(str)
    plugin_disabled = Signal(str)
    settings_changed = Signal(str, dict)
    plugin_state_updated = Signal(str, dict)
    daemon_online = Signal()
    daemon_offline = Signal()

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._bus = QDBusConnection.sessionBus()
        if not self._bus.isConnected():
            raise RuntimeError("not connected to session bus")
        self._iface: Optional[QDBusInterface] = None
        self._connect_signals()
        self._connect_iface()

    def _connect_iface(self) -> None:
        self._iface = QDBusInterface(
            dbus_names.SERVICE,
            dbus_names.CORE_PATH,
            dbus_names.CORE_IFACE,
            self._bus,
        )
        if not self._iface.isValid():
            self._iface = None
            self.daemon_offline.emit()
        else:
            self.daemon_online.emit()

    def _connect_signals(self) -> None:
        def _forward(local_signal):
            def _handler(message: QDBusMessage):
                args = list(message.arguments())
                local_signal.emit(*args)
            return _handler

        self._bus.connect(
            dbus_names.SERVICE,
            dbus_names.CORE_PATH,
            dbus_names.CORE_IFACE,
            "PluginEnabled",
            _forward(self.plugin_enabled),
        )
        self._bus.connect(
            dbus_names.SERVICE,
            dbus_names.CORE_PATH,
            dbus_names.CORE_IFACE,
            "PluginDisabled",
            _forward(self.plugin_disabled),
        )
        self._bus.connect(
            dbus_names.SERVICE,
            dbus_names.CORE_PATH,
            dbus_names.CORE_IFACE,
            "SettingsChanged",
            _forward(self.settings_changed),
        )
        self._bus.connect(
            dbus_names.SERVICE,
            dbus_names.CORE_PATH,
            dbus_names.CORE_IFACE,
            "PluginStateUpdated",
            _forward(self.plugin_state_updated),
        )

    # --- sync RPC wrappers ---

    def _call(self, method: str, *args: Any) -> Any:
        if self._iface is None:
            self._connect_iface()
        if self._iface is None:
            raise RuntimeError("daemon not reachable on session bus")
        reply = self._iface.call(method, *args)
        if reply.type() == QDBusMessage.ErrorMessage:
            raise RuntimeError(reply.errorMessage())
        return reply.arguments()

    def ping(self) -> str:
        return self._call("Ping")[0]

    def list_plugins(self) -> list[tuple[str, str, str, str, bool, bool]]:
        return [tuple(r) for r in self._call("ListPlugins")[0]]

    def enable_plugin(self, plugin_id: str) -> None:
        self._call("EnablePlugin", plugin_id)

    def disable_plugin(self, plugin_id: str) -> None:
        self._call("DisablePlugin", plugin_id)

    def get_config(self, plugin_id: str) -> dict[str, Any]:
        return dict(self._call("GetConfig", plugin_id)[0])

    def set_config(self, plugin_id: str, values: dict[str, Any]) -> None:
        self._call("SetConfig", plugin_id, values)

    def get_settings_schema(self, plugin_id: str) -> dict[str, Any]:
        raw = self._call("GetSettingsSchema", plugin_id)[0]
        return json.loads(raw)

    def export_all(self) -> str:
        return self._call("ExportAll")[0]

    def import_all(self, blob: str, strategy: str = "merge") -> None:
        self._call("ImportAll", blob, strategy)
```

- [ ] **Step 2: Commit**

```bash
git add smartass/tray/daemon_client.py
git commit -m "feat(tray): QtDBus DaemonClient proxy"
```

---

### Task 4.2: `smartass/tray/schema_form.py` — render SettingsSchema as Qt form

**Files:**
- Create: `smartass/tray/schema_form.py`

- [ ] **Step 1: Implement**

```python
# smartass/tray/schema_form.py
"""Render a SettingsSchema dict (from daemon) as a Qt form."""

from __future__ import annotations

from typing import Any, Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class SchemaForm(QWidget):
    """Renders a schema dict emitted by SettingsSchema.to_dict()."""

    def __init__(
        self,
        schema: dict[str, Any],
        values: dict[str, Any],
        on_save: Callable[[dict[str, Any]], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._schema = schema
        self._on_save = on_save
        self._widgets: dict[str, QWidget] = {}

        root = QVBoxLayout(self)
        form = QFormLayout()
        for f in schema.get("fields", []):
            key = f["key"]
            label = f.get("label", key)
            w = self._make_widget(f, values.get(key, f.get("default")))
            self._widgets[key] = w
            form.addRow(QLabel(label), w)
            if f.get("description"):
                hint = QLabel(f["description"])
                hint.setStyleSheet("color: gray;")
                hint.setWordWrap(True)
                form.addRow(hint)
        root.addLayout(form)

        save = QPushButton("Save")
        save.clicked.connect(self._handle_save)
        root.addWidget(save, alignment=Qt.AlignmentFlag.AlignRight)

    def _make_widget(self, field: dict[str, Any], value: Any) -> QWidget:
        t = field["type"]
        if t == "string" or t == "secret":
            w = QLineEdit()
            w.setText("" if value is None else str(value))
            if t == "secret":
                w.setEchoMode(QLineEdit.EchoMode.Password)
            return w
        if t == "int":
            w = QSpinBox()
            if field.get("min") is not None:
                w.setMinimum(int(field["min"]))
            else:
                w.setMinimum(-2**31)
            if field.get("max") is not None:
                w.setMaximum(int(field["max"]))
            else:
                w.setMaximum(2**31 - 1)
            w.setValue(int(value if value is not None else field.get("default", 0)))
            return w
        if t == "bool":
            w = QCheckBox()
            w.setChecked(bool(value))
            return w
        if t == "select":
            w = QComboBox()
            for opt in field.get("options", []):
                w.addItem(opt)
            if value is not None and value in field.get("options", []):
                w.setCurrentText(str(value))
            return w
        # Unknown type → best-effort text
        w = QLineEdit()
        w.setText("" if value is None else str(value))
        return w

    def _handle_save(self) -> None:
        out: dict[str, Any] = {}
        for f in self._schema.get("fields", []):
            key = f["key"]
            w = self._widgets[key]
            t = f["type"]
            if t in ("string", "secret"):
                out[key] = w.text()
            elif t == "int":
                out[key] = int(w.value())
            elif t == "bool":
                out[key] = bool(w.isChecked())
            elif t == "select":
                out[key] = w.currentText()
            else:
                out[key] = w.text() if hasattr(w, "text") else None
        self._on_save(out)
```

- [ ] **Step 2: Commit**

```bash
git add smartass/tray/schema_form.py
git commit -m "feat(tray): SchemaForm renderer for plugin settings"
```

---

### Task 4.3: `smartass/tray/settings_tab.py` — always-on Settings tab

**Files:**
- Create: `smartass/tray/settings_tab.py`

- [ ] **Step 1: Implement**

```python
# smartass/tray/settings_tab.py
"""Settings tab: plugin list, enable/disable, per-plugin schema form, import/export."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from smartass.tray.daemon_client import DaemonClient
from smartass.tray.schema_form import SchemaForm


class SettingsTab(QWidget):
    plugin_enabled_changed = Signal(str, bool)

    def __init__(self, client: DaemonClient, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._client = client

        root = QHBoxLayout(self)

        left = QVBoxLayout()
        self._list = QListWidget()
        self._list.itemClicked.connect(self._on_pick)
        left.addWidget(self._list)

        self._enable_btn = QPushButton("Enable")
        self._enable_btn.clicked.connect(self._toggle_selected)
        left.addWidget(self._enable_btn)

        export_btn = QPushButton("Export…")
        export_btn.clicked.connect(self._do_export)
        import_btn = QPushButton("Import…")
        import_btn.clicked.connect(self._do_import)
        left.addWidget(export_btn)
        left.addWidget(import_btn)
        root.addLayout(left, stretch=1)

        self._stack = QStackedWidget()
        root.addWidget(self._stack, stretch=3)

        self.refresh()
        client.plugin_enabled.connect(lambda pid: self.refresh())
        client.plugin_disabled.connect(lambda pid: self.refresh())

    def refresh(self) -> None:
        self._list.clear()
        try:
            rows = self._client.list_plugins()
        except Exception:
            QMessageBox.warning(self, "Smartass", "Daemon not reachable.")
            return
        for (pid, name, version, description, installed, enabled) in rows:
            item = QListWidgetItem(f"{'✓ ' if enabled else '  '}{name} ({version})")
            item.setData(Qt.ItemDataRole.UserRole, pid)
            item.setToolTip(description)
            self._list.addItem(item)

    def _selected_id(self) -> Optional[str]:
        item = self._list.currentItem()
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def _on_pick(self, item: QListWidgetItem) -> None:
        pid = item.data(Qt.ItemDataRole.UserRole)
        schema = self._client.get_settings_schema(pid)
        values = self._client.get_config(pid)
        form = SchemaForm(schema, values, on_save=lambda v, p=pid: self._save(p, v))
        # Reset the stack to a single current form
        while self._stack.count():
            w = self._stack.widget(0)
            self._stack.removeWidget(w)
            w.deleteLater()
        self._stack.addWidget(form)
        self._stack.setCurrentWidget(form)
        self._refresh_enable_button(pid)

    def _save(self, pid: str, values: dict) -> None:
        try:
            self._client.set_config(pid, values)
            QMessageBox.information(self, "Smartass", "Settings saved.")
        except Exception as e:
            QMessageBox.warning(self, "Smartass", f"Save failed: {e}")

    def _refresh_enable_button(self, pid: str) -> None:
        rows = {r[0]: r for r in self._client.list_plugins()}
        is_enabled = rows[pid][5] if pid in rows else False
        self._enable_btn.setText("Disable" if is_enabled else "Enable")

    def _toggle_selected(self) -> None:
        pid = self._selected_id()
        if pid is None:
            return
        rows = {r[0]: r for r in self._client.list_plugins()}
        is_enabled = rows[pid][5]
        try:
            if is_enabled:
                self._client.disable_plugin(pid)
            else:
                self._client.enable_plugin(pid)
            self.plugin_enabled_changed.emit(pid, not is_enabled)
            self.refresh()
            self._refresh_enable_button(pid)
        except Exception as e:
            QMessageBox.warning(self, "Smartass", f"Toggle failed: {e}")

    def _do_export(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Export settings", "smartass-export.toml", "TOML (*.toml)"
        )
        if not path:
            return
        blob = self._client.export_all()
        Path(path).write_text(blob, encoding="utf-8")
        QMessageBox.information(self, "Smartass", f"Exported to {path}")

    def _do_import(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Import settings", "", "TOML (*.toml)"
        )
        if not path:
            return
        blob = Path(path).read_text(encoding="utf-8")
        try:
            self._client.import_all(blob, strategy="merge")
            QMessageBox.information(self, "Smartass", "Import complete.")
            self.refresh()
        except Exception as e:
            QMessageBox.warning(self, "Smartass", f"Import failed: {e}")
```

- [ ] **Step 2: Commit**

```bash
git add smartass/tray/settings_tab.py
git commit -m "feat(tray): Settings tab with plugin list, form, import/export"
```

---

### Task 4.4: `smartass/tray/main_window.py` — tabbed window

**Files:**
- Create: `smartass/tray/main_window.py`

- [ ] **Step 1: Implement**

```python
# smartass/tray/main_window.py
"""Main window with QTabWidget — Settings tab always-on + one per enabled plugin."""

from __future__ import annotations

import importlib.util
import logging
import sys
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, Qt
from PySide6.QtWidgets import QMainWindow, QTabWidget, QWidget

from smartass.core import paths as _paths
from smartass.core.manifest import load_manifest
from smartass.core.plugin_interface import PluginContext, PluginInterface
from smartass.tray.daemon_client import DaemonClient
from smartass.tray.settings_tab import SettingsTab

log = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(self, client: DaemonClient) -> None:
        super().__init__()
        self.setWindowTitle("Smartass")
        self._client = client
        self._tabs = QTabWidget()
        self.setCentralWidget(self._tabs)
        self.resize(720, 520)

        self._settings_tab = SettingsTab(self._client, parent=self)
        self._tabs.addTab(self._settings_tab, "Settings")

        self._plugin_tabs: dict[str, QWidget] = {}
        self._rebuild_plugin_tabs()

        client.plugin_enabled.connect(self._on_plugin_enabled)
        client.plugin_disabled.connect(self._on_plugin_disabled)

    def _enabled_ids(self) -> list[str]:
        return [r[0] for r in self._client.list_plugins() if r[5]]

    def _rebuild_plugin_tabs(self) -> None:
        for pid in list(self._plugin_tabs):
            self._remove_plugin_tab(pid)
        for pid in self._enabled_ids():
            self._add_plugin_tab(pid)

    def _add_plugin_tab(self, plugin_id: str) -> None:
        if plugin_id in self._plugin_tabs:
            return
        try:
            widget = self._build_plugin_tab(plugin_id)
        except Exception:
            log.exception("failed to build tab for %s", plugin_id)
            return
        self._plugin_tabs[plugin_id] = widget
        self._tabs.addTab(widget, plugin_id.capitalize())

    def _remove_plugin_tab(self, plugin_id: str) -> None:
        widget = self._plugin_tabs.pop(plugin_id, None)
        if widget is None:
            return
        idx = self._tabs.indexOf(widget)
        if idx >= 0:
            self._tabs.removeTab(idx)
        widget.deleteLater()

    def _on_plugin_enabled(self, plugin_id: str) -> None:
        self._add_plugin_tab(plugin_id)

    def _on_plugin_disabled(self, plugin_id: str) -> None:
        self._remove_plugin_tab(plugin_id)

    def _build_plugin_tab(self, plugin_id: str) -> QWidget:
        """Load the plugin package tray-side and call its build_tab()."""
        plugin_dir = self._find_plugin_dir(plugin_id)
        if plugin_dir is None:
            raise RuntimeError(f"plugin '{plugin_id}' not installed")
        manifest = load_manifest(plugin_dir)
        module_name = f"smartass_plugin_{plugin_id}"
        module_path = plugin_dir / f"{manifest.entry_module}.py"
        spec = importlib.util.spec_from_file_location(
            module_name, module_path, submodule_search_locations=[str(plugin_dir)]
        )
        if spec is None or spec.loader is None:
            raise RuntimeError(f"cannot import plugin {plugin_id}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        cls = getattr(module, manifest.entry_class)
        if not issubclass(cls, PluginInterface):
            raise RuntimeError(f"plugin {plugin_id} is not a PluginInterface")

        # Tray-side context: no http, no persistence. Plugin's UI is read-only
        # against the daemon, which is the data owner.
        ctx = PluginContext(
            config=None,
            data_dir=plugin_dir,  # not written to from tray
            log=logging.getLogger(f"smartass.plugins.{plugin_id}"),
            http=None,
            bus=None,
            signals=None,
            permissions=manifest.permissions,
        )
        instance = cls(ctx)
        return instance.build_tab(self)

    def _find_plugin_dir(self, plugin_id: str) -> Optional[Path]:
        for root in _paths.plugin_roots():
            candidate = root / plugin_id
            if (candidate / "manifest.toml").is_file():
                return candidate
        # Fallback: in development, the bundled plugin lives in-tree
        dev = Path(__file__).resolve().parent.parent / "plugins" / plugin_id
        if (dev / "manifest.toml").is_file():
            return dev
        return None
```

- [ ] **Step 2: Commit**

```bash
git add smartass/tray/main_window.py
git commit -m "feat(tray): MainWindow with tabs; auto mount/unmount on plugin signals"
```

---

### Task 4.5: `smartass/tray/tray_icon.py` + `app.py` + `__main__.py`

**Files:**
- Create: `smartass/tray/tray_icon.py`
- Create: `smartass/tray/app.py`
- Create: `smartass/tray/__main__.py`

- [ ] **Step 1: tray_icon.py**

```python
# smartass/tray/tray_icon.py
"""System tray icon wrapper."""

from __future__ import annotations

from typing import Callable

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenu, QSystemTrayIcon


class TrayIcon(QSystemTrayIcon):
    def __init__(
        self,
        icon: QIcon,
        on_toggle_window: Callable[[], None],
        on_quit: Callable[[], None],
        on_restart_daemon: Callable[[], None],
    ) -> None:
        super().__init__(icon)
        self.setToolTip("Smartass")

        menu = QMenu()
        show_action = QAction("Show / Hide", menu)
        show_action.triggered.connect(on_toggle_window)
        menu.addAction(show_action)

        restart_action = QAction("Restart daemon", menu)
        restart_action.triggered.connect(on_restart_daemon)
        menu.addAction(restart_action)

        menu.addSeparator()
        quit_action = QAction("Quit tray", menu)
        quit_action.triggered.connect(on_quit)
        menu.addAction(quit_action)

        self.setContextMenu(menu)
        self.activated.connect(self._on_activated)
        self._on_toggle = on_toggle_window

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._on_toggle()
```

- [ ] **Step 2: app.py**

```python
# smartass/tray/app.py
"""Wires QApplication, tray icon, and main window together."""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QCoreApplication
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QSystemTrayIcon

from smartass import __version__
from smartass.tray.daemon_client import DaemonClient
from smartass.tray.main_window import MainWindow
from smartass.tray.tray_icon import TrayIcon

log = logging.getLogger(__name__)

ICON_CANDIDATES = [
    Path("/usr/share/icons/hicolor/scalable/apps/ai.talonic.smartass.svg"),
    Path(__file__).resolve().parent.parent.parent / "assets" / "icons" / "smartass.svg",
]


def _load_icon() -> QIcon:
    for p in ICON_CANDIDATES:
        if p.is_file():
            return QIcon(str(p))
    # Fall back to a themed icon
    return QIcon.fromTheme("applications-accessories")


def _ensure_daemon_running() -> None:
    try:
        subprocess.run(
            ["systemctl", "--user", "start", "smartass-daemon.service"],
            timeout=5,
            check=False,
        )
    except Exception as e:
        log.warning("could not start daemon via systemd: %s", e)


def run_tray() -> int:
    QCoreApplication.setOrganizationName("Talonic")
    QCoreApplication.setApplicationName("Smartass")
    QCoreApplication.setApplicationVersion(__version__)

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # closing window keeps tray alive

    _ensure_daemon_running()

    try:
        client = DaemonClient()
    except Exception as e:
        log.error("session bus unavailable: %s", e)
        return 2

    if not QSystemTrayIcon.isSystemTrayAvailable():
        log.error("system tray not available on this desktop")
        return 3

    window = MainWindow(client)

    def toggle_window() -> None:
        if window.isVisible():
            window.hide()
        else:
            window.show()
            window.raise_()
            window.activateWindow()

    def restart_daemon() -> None:
        subprocess.run(
            ["systemctl", "--user", "restart", "smartass-daemon.service"],
            timeout=10,
            check=False,
        )

    tray = TrayIcon(
        icon=_load_icon(),
        on_toggle_window=toggle_window,
        on_quit=app.quit,
        on_restart_daemon=restart_daemon,
    )
    tray.show()

    return app.exec()
```

- [ ] **Step 3: __main__.py**

```python
# smartass/tray/__main__.py
"""Smartass tray entrypoint."""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler

from smartass.core import paths
from smartass.tray.app import run_tray


def _configure_logging() -> None:
    paths.ensure_user_dirs()
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    handler = RotatingFileHandler(
        paths.cache_dir() / "tray.log", maxBytes=1_000_000, backupCount=5
    )
    handler.setFormatter(fmt)
    root.addHandler(handler)
    stderr = logging.StreamHandler(sys.stderr)
    stderr.setFormatter(fmt)
    root.addHandler(stderr)


def main() -> None:
    _configure_logging()
    sys.exit(run_tray())


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Bundle a minimal icon**

Create `assets/icons/smartass.svg` with a simple line-art robot face:

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
  <rect x="4" y="7" width="16" height="12" rx="2"/>
  <circle cx="9" cy="13" r="1.2" fill="currentColor"/>
  <circle cx="15" cy="13" r="1.2" fill="currentColor"/>
  <path d="M9 17h6"/>
  <path d="M12 7V4"/>
  <circle cx="12" cy="3" r="1" fill="currentColor"/>
  <path d="M2 12h2M20 12h2"/>
</svg>
```

- [ ] **Step 5: Manual smoke test (dev mode)**

In one terminal:
```bash
dbus-run-session -- poetry run python -m smartass.daemon
```
In another (inside the same dbus-run-session — use `export DBUS_SESSION_BUS_ADDRESS=...` printed by the first, or combine):
```bash
DBUS_SESSION_BUS_ADDRESS="$DBUS_SESSION_BUS_ADDRESS" poetry run python -m smartass.tray
```

Alternatively:
```bash
dbus-run-session -- bash -c 'poetry run python -m smartass.daemon & sleep 1 && poetry run python -m smartass.tray'
```

Expected: robot icon appears in tray. Click → window opens → Settings tab lists "Weather". Enable Weather → Weather tab appears (content will be blank until Task 5.1 implements the tab).

- [ ] **Step 6: Commit**

```bash
git add smartass/tray/tray_icon.py smartass/tray/app.py smartass/tray/__main__.py assets/icons/smartass.svg
git commit -m "feat(tray): QApplication + tray icon + entrypoint; bundle robot icon"
```

---

## Phase 5 — Weather Tab UI

### Task 5.1: `smartass/plugins/weather/ui.py` — WeatherTab

**Files:**
- Create: `smartass/plugins/weather/ui.py`

- [ ] **Step 1: Implement**

```python
# smartass/plugins/weather/ui.py
"""Weather tab — current conditions + 7-day forecast.

Reads data from the daemon via the Core D-Bus surface rather than from the
plugin instance directly (the tray-side plugin instance has no data).
"""

from __future__ import annotations

import json
from typing import Any

from PySide6.QtCore import Qt, QTimer
from PySide6.QtDBus import QDBusConnection, QDBusInterface, QDBusMessage
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from smartass.core import dbus_names

WMO_CODE_TO_LABEL = {
    0: "Clear",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Drizzle",
    55: "Heavy drizzle",
    61: "Light rain",
    63: "Rain",
    65: "Heavy rain",
    71: "Light snow",
    73: "Snow",
    75: "Heavy snow",
    80: "Rain showers",
    81: "Heavy rain showers",
    82: "Violent rain showers",
    95: "Thunderstorm",
    96: "Thunderstorm w/ hail",
    99: "Severe thunderstorm",
}


class WeatherTab(QWidget):
    """Polls the daemon every 30s for a cached snapshot; no direct API calls."""

    def __init__(self, parent: QWidget | None, plugin: Any) -> None:
        super().__init__(parent)
        self._plugin = plugin  # unused at tray side, kept for API parity
        self._bus = QDBusConnection.sessionBus()

        root = QVBoxLayout(self)

        header = QHBoxLayout()
        self._city_label = QLabel("—")
        f = QFont()
        f.setPointSize(18)
        f.setBold(True)
        self._city_label.setFont(f)
        header.addWidget(self._city_label)

        self._stale_label = QLabel("")
        self._stale_label.setStyleSheet("color: #c66;")
        header.addWidget(self._stale_label)
        header.addStretch()

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._refresh)
        header.addWidget(refresh_btn)
        root.addLayout(header)

        self._current = QLabel("No data yet.")
        f2 = QFont()
        f2.setPointSize(14)
        self._current.setFont(f2)
        root.addWidget(self._current)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        root.addWidget(line)

        self._forecast_grid = QGridLayout()
        root.addLayout(self._forecast_grid)
        root.addStretch()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)
        self._timer.start(30_000)
        self._refresh()

    # --- data fetch ---

    def _refresh(self) -> None:
        payload = self._get_state_from_daemon()
        if payload is None:
            self._city_label.setText("—")
            self._current.setText("Weather plugin not available.")
            self._stale_label.setText("")
            return
        self._render(payload)

    def _get_state_from_daemon(self) -> dict[str, Any] | None:
        iface = QDBusInterface(
            dbus_names.SERVICE,
            dbus_names.plugin_path("weather"),
            dbus_names.PLUGIN_IFACE,
            self._bus,
        )
        if not iface.isValid():
            return None
        reply = iface.call("GetState")
        if reply.type() == QDBusMessage.ErrorMessage:
            return None
        args = reply.arguments()
        if not args:
            return None
        state = args[0]
        # `state` may arrive as a dict of variants — normalize
        snap = state.get("snapshot_json") if isinstance(state, dict) else None
        if snap is None:
            return None
        try:
            return json.loads(snap)
        except json.JSONDecodeError:
            return None

    # --- render ---

    def _render(self, payload: dict[str, Any]) -> None:
        city = payload.get("city", "—")
        country = payload.get("country", "")
        self._city_label.setText(f"{city}, {country}" if country else city)

        units = payload.get("units", "metric")
        deg = "°C" if units == "metric" else "°F"
        wind = "km/h" if units == "metric" else "mph"

        cur = payload.get("current") or {}
        label = WMO_CODE_TO_LABEL.get(int(cur.get("weather_code", -1)), "—")
        self._current.setText(
            f"{cur.get('temperature', '—')}{deg} — {label}  "
            f"(humidity {cur.get('humidity', '—')}%, wind {cur.get('wind_speed', '—')} {wind})"
        )

        # reset grid
        while self._forecast_grid.count():
            item = self._forecast_grid.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()

        daily = payload.get("daily", []) or []
        headers = ["Date", f"High {deg}", f"Low {deg}", "Conditions"]
        for col, h in enumerate(headers):
            hdr = QLabel(h)
            hf = QFont()
            hf.setBold(True)
            hdr.setFont(hf)
            self._forecast_grid.addWidget(hdr, 0, col)
        for row, d in enumerate(daily, start=1):
            self._forecast_grid.addWidget(QLabel(str(d.get("date", "—"))), row, 0)
            self._forecast_grid.addWidget(
                QLabel(str(d.get("temp_max", "—"))), row, 1, alignment=Qt.AlignmentFlag.AlignRight
            )
            self._forecast_grid.addWidget(
                QLabel(str(d.get("temp_min", "—"))), row, 2, alignment=Qt.AlignmentFlag.AlignRight
            )
            self._forecast_grid.addWidget(
                QLabel(WMO_CODE_TO_LABEL.get(int(d.get("weather_code", -1)), "—")), row, 3
            )

        if payload.get("stale"):
            self._stale_label.setText("(stale — daemon could not refresh)")
        else:
            self._stale_label.setText("")
```

- [ ] **Step 2: Add `GetState` to the common plugin interface on daemon side**

Modify `smartass/daemon/service.py` — register per-plugin object exporting the common `ai.talonic.Smartass.Plugin` interface with a `GetState` method. Append a new `PluginObject` class and wire it in from `PluginManager`.

Create `smartass/daemon/plugin_object.py`:

```python
# smartass/daemon/plugin_object.py
"""Per-plugin D-Bus object exposing ai.talonic.Smartass.Plugin."""

from __future__ import annotations

import json
from typing import Any

from dbus_next.service import ServiceInterface, method

from smartass.core import dbus_names


class PluginObject(ServiceInterface):
    def __init__(self, plugin_id: str, instance: Any) -> None:
        super().__init__(dbus_names.PLUGIN_IFACE)
        self._plugin_id = plugin_id
        self._instance = instance

    @method()
    def GetState(self) -> "a{sv}":  # type: ignore[name-defined]
        from dbus_next import Variant

        state: dict[str, Any] = {}
        # Plugins MAY expose a `public_state()` callable that returns a dict;
        # we serialize complex values to a JSON string under `snapshot_json`.
        raw = getattr(self._instance, "public_state", None)
        if callable(raw):
            payload = raw() or {}
        else:
            # Fallback for Weather: expose last_snapshot() directly
            snap = getattr(self._instance, "last_snapshot", lambda: None)()
            payload = {"snapshot": snap} if snap else {}
        state["snapshot_json"] = Variant("s", json.dumps(payload.get("snapshot", payload)))
        state["stale"] = Variant("b", bool(getattr(self._instance, "is_stale", lambda: False)()))
        return state
```

- [ ] **Step 3: Wire PluginObject into `PluginManager.enable` (export on bus)**

Extend `PluginManager.__init__` to accept a `bus` reference, and in `enable()` export a `PluginObject` per plugin at `dbus_names.plugin_path(id)`. Update `smartass/daemon/plugin_manager.py`: add `bus: Any = None` param, and, in `enable` after successful `on_start`:

```python
# (inside PluginManager.enable, after self._running[plugin_id] = _RunningPlugin(...))
if self._bus is not None:
    from smartass.daemon.plugin_object import PluginObject
    obj = PluginObject(plugin_id, instance)
    self._bus.export(_paths_from_id(plugin_id), obj)
    self._bus_objects[plugin_id] = obj
```

And in `disable`:

```python
if self._bus is not None and plugin_id in self._bus_objects:
    self._bus.unexport(_paths_from_id(plugin_id), self._bus_objects.pop(plugin_id))
```

Add a small import helper within `plugin_manager.py`:

```python
from smartass.core import dbus_names as _dbus_names


def _paths_from_id(plugin_id: str) -> str:
    return _dbus_names.plugin_path(plugin_id)
```

And in `__init__`:

```python
self._bus = bus
self._bus_objects: dict[str, Any] = {}
```

- [ ] **Step 4: Update `smartass/daemon/__main__.py` to pass the bus**

Replace the `pm = PluginManager(...)` line with:
```python
pm = PluginManager(
    config_store=store,
    roots=paths.plugin_roots(),
    http_factory=http_factory,
)
```
…already matches; change it to:
```python
pm = PluginManager(
    config_store=store,
    roots=paths.plugin_roots(),
    http_factory=http_factory,
)
# Must attach bus AFTER connection:
pm._bus = bus  # noqa: SLF001 — wire-through for plugin objects
pm._bus_objects = {}
```

(Better: add a proper setter on the manager; for MVP, the attribute write is acceptable. If you prefer, add `pm.attach_bus(bus)` method — a one-liner setting both fields.)

Preferred: add to `PluginManager`:

```python
def attach_bus(self, bus: Any) -> None:
    self._bus = bus
    self._bus_objects = {}
```

And call `pm.attach_bus(bus)` in `__main__`.

- [ ] **Step 5: Manual smoke test**

Re-run the daemon + tray pair (dev mode as in Task 4.5 step 5). Enable Weather from Settings tab. Wait up to 60s. Expected: Weather tab shows "Berlin, DE", current temperature/conditions, 7-day forecast table.

- [ ] **Step 6: Commit**

```bash
git add smartass/plugins/weather/ui.py smartass/daemon/plugin_object.py smartass/daemon/plugin_manager.py smartass/daemon/__main__.py
git commit -m "feat(weather): WeatherTab + per-plugin D-Bus object (GetState)"
```

---

## Phase 6 — Debian Packaging

### Task 6.1: `debian/control`, `debian/compat`, `debian/changelog`

**Files:**
- Create: `debian/control`
- Create: `debian/compat`
- Create: `debian/changelog`
- Create: `debian/copyright`

- [ ] **Step 1: debian/control**

```
Source: smartass
Section: utils
Priority: optional
Maintainer: Saurabh Khanduja <saurabh@talonic.ai>
Build-Depends: debhelper-compat (= 13),
               dh-virtualenv,
               python3-all (>= 3.10),
               python3-venv,
               python3-pip,
               python3-dev,
               libgl1,
               libxcb-cursor0
Standards-Version: 4.6.2
Homepage: https://github.com/saurabheights/smartass

Package: smartass
Architecture: amd64
Depends: ${misc:Depends},
         ${shlibs:Depends},
         python3 (>= 3.10),
         libqt6core6,
         libqt6dbus6,
         libqt6widgets6,
         libqt6gui6,
         dbus-user-session,
         adwaita-icon-theme,
         gnome-shell-extension-appindicator | gnome-shell-extension-ubuntu-appindicators
Description: Smart assistant tray app with a plugin system
 Smartass is a desktop assistant that lives in the top bar via an
 AppIndicator icon. A tabbed window hosts a Settings tab and one tab
 per enabled plugin. Ships with a Weather plugin (Open-Meteo).
```

- [ ] **Step 2: debian/compat**

```
13
```

- [ ] **Step 3: debian/changelog**

Run: `dch --create --package smartass --newversion 0.1.0-1 "Initial release"`

If `dch` (from `devscripts`) is not installed, create `debian/changelog` manually:

```
smartass (0.1.0-1) unstable; urgency=medium

  * Initial release: MVP daemon + tray + Weather plugin.

 -- Saurabh Khanduja <saurabh@talonic.ai>  Tue, 21 Apr 2026 15:08:00 +0000
```

- [ ] **Step 4: debian/copyright**

```
Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Upstream-Name: smartass
Upstream-Contact: Saurabh Khanduja <saurabh@talonic.ai>
Source: https://github.com/saurabheights/smartass

Files: *
Copyright: 2026 Saurabh Khanduja
License: MIT
 Permission is hereby granted, free of charge, to any person obtaining a
 copy of this software and associated documentation files (the "Software"),
 to deal in the Software without restriction, including without limitation
 the rights to use, copy, modify, merge, publish, distribute, sublicense,
 and/or sell copies of the Software, and to permit persons to whom the
 Software is furnished to do so, subject to the following conditions:
 .
 The above copyright notice and this permission notice shall be included
 in all copies or substantial portions of the Software.
 .
 THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.
```

- [ ] **Step 5: Commit**

```bash
git add debian/control debian/compat debian/changelog debian/copyright
git commit -m "build: debian control/compat/changelog/copyright"
```

---

### Task 6.2: `debian/rules` + `debian/source/format`

**Files:**
- Create: `debian/rules`
- Create: `debian/source/format`

- [ ] **Step 1: debian/rules**

```
#!/usr/bin/make -f

export PYBUILD_NAME=smartass
export DH_VIRTUALENV_INSTALL_ROOT=/opt

%:
	dh $@ --with python-virtualenv

override_dh_virtualenv:
	dh_virtualenv \
		--python /usr/bin/python3 \
		--install-suffix smartass \
		--builtin-venv \
		--preinstall "wheel" \
		--preinstall "setuptools>=68"
```

Make it executable: `chmod +x debian/rules`

- [ ] **Step 2: debian/source/format**

```
3.0 (native)
```

- [ ] **Step 3: Commit**

```bash
git add debian/rules debian/source/format
chmod +x debian/rules
git add --chmod=+x debian/rules
git commit -m "build: debian/rules using dh-virtualenv; native source format"
```

---

### Task 6.3: Service units, autostart, app launcher, icon install

**Files:**
- Create: `debian/smartass-daemon.service`
- Create: `debian/smartass-tray.desktop`
- Create: `debian/ai.talonic.smartass.desktop`
- Create: `debian/smartass.install`
- Create: `debian/smartass.dirs`
- Create: `debian/smartass.postinst`
- Create: `debian/smartass.prerm`

- [ ] **Step 1: smartass-daemon.service**

```ini
[Unit]
Description=Smartass daemon (plugin host + D-Bus service)
After=graphical-session.target

[Service]
Type=dbus
BusName=ai.talonic.Smartass
ExecStart=/opt/smartass/venv/bin/python -m smartass.daemon
Restart=on-failure
RestartSec=3
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=default.target
```

- [ ] **Step 2: smartass-tray.desktop**

```ini
[Desktop Entry]
Type=Application
Name=Smartass
Exec=/opt/smartass/venv/bin/python -m smartass.tray
Icon=ai.talonic.smartass
X-GNOME-Autostart-enabled=true
OnlyShowIn=GNOME;Unity;
NoDisplay=true
```

- [ ] **Step 3: ai.talonic.smartass.desktop**

```ini
[Desktop Entry]
Type=Application
Name=Smartass
Comment=Smart assistant tray app
Exec=/opt/smartass/venv/bin/python -m smartass.tray
Icon=ai.talonic.smartass
Terminal=false
Categories=Utility;
StartupNotify=false
```

- [ ] **Step 4: smartass.install**

```
debian/smartass-daemon.service  usr/lib/systemd/user/
debian/smartass-tray.desktop    etc/xdg/autostart/
debian/ai.talonic.smartass.desktop  usr/share/applications/
assets/icons/smartass.svg       usr/share/icons/hicolor/scalable/apps/
smartass/plugins/weather        usr/share/smartass/plugins/
```

Also create `assets/icons/ai.talonic.smartass.svg` as a symlink (or copy) for the correctly-named installed icon. For simplicity, instead rename the install line to copy-and-rename:

Adjust `smartass.install` so the icon lands with the expected name:

```
debian/smartass-daemon.service  usr/lib/systemd/user/
debian/smartass-tray.desktop    etc/xdg/autostart/
debian/ai.talonic.smartass.desktop  usr/share/applications/
smartass/plugins/weather        usr/share/smartass/plugins/
```

And use a separate rule to install the icon under the correct name by adding this to `debian/rules`:

```make
override_dh_install:
	dh_install
	install -D -m 0644 assets/icons/smartass.svg \
	  debian/smartass/usr/share/icons/hicolor/scalable/apps/ai.talonic.smartass.svg
```

- [ ] **Step 5: smartass.dirs**

```
usr/lib/systemd/user
etc/xdg/autostart
usr/share/applications
usr/share/icons/hicolor/scalable/apps
usr/share/smartass/plugins
```

- [ ] **Step 6: smartass.postinst**

```bash
#!/bin/sh
set -e

case "$1" in
    configure)
        systemctl --global enable smartass-daemon.service 2>/dev/null || true
        if command -v update-desktop-database >/dev/null 2>&1; then
            update-desktop-database -q /usr/share/applications || true
        fi
        if command -v gtk-update-icon-cache >/dev/null 2>&1; then
            gtk-update-icon-cache -q /usr/share/icons/hicolor || true
        fi
        # Gentle warning for GNOME users missing the AppIndicator extension
        if ! dpkg -l gnome-shell-extension-appindicator 2>/dev/null | grep -q '^ii' \
           && ! dpkg -l gnome-shell-extension-ubuntu-appindicators 2>/dev/null | grep -q '^ii'; then
            echo "WARNING: the AppIndicator GNOME Shell extension is not installed."
            echo "         The Smartass tray icon will not appear on vanilla GNOME Shell."
            echo "         Install 'gnome-shell-extension-appindicator' and enable it."
        fi
        ;;
esac

#DEBHELPER#

exit 0
```

- [ ] **Step 7: smartass.prerm**

```bash
#!/bin/sh
set -e

case "$1" in
    remove|upgrade|deconfigure)
        # Best-effort stop across live user sessions
        for uid in $(who | awk '{print $1}' | xargs -I{} id -u {} 2>/dev/null | sort -u); do
            sudo -u "#$uid" XDG_RUNTIME_DIR="/run/user/$uid" \
                systemctl --user stop smartass-daemon.service 2>/dev/null || true
        done
        ;;
esac

#DEBHELPER#

exit 0
```

Make postinst + prerm executable: `chmod +x debian/smartass.postinst debian/smartass.prerm`.

- [ ] **Step 8: Commit**

```bash
git add debian/smartass-daemon.service debian/smartass-tray.desktop \
       debian/ai.talonic.smartass.desktop debian/smartass.install \
       debian/smartass.dirs debian/smartass.postinst debian/smartass.prerm
git update-index --chmod=+x debian/smartass.postinst debian/smartass.prerm
git commit -m "build: systemd user unit, autostart, launcher, icon install, postinst"
```

---

### Task 6.4: Build the `.deb`

**Files:** none (build artifact)

- [ ] **Step 1: Install build tools (system-wide)**

```bash
sudo apt-get install -y debhelper dh-virtualenv devscripts build-essential python3-dev
```

- [ ] **Step 2: Build**

```bash
debuild -us -uc -b
```

Expected: produces `../smartass_0.1.0-1_amd64.deb` alongside `.changes`, `.buildinfo`.

If `debuild` fails on missing Build-Depends, run `sudo apt-get build-dep -y .` first.

- [ ] **Step 3: Inspect the .deb**

```bash
dpkg-deb -c ../smartass_0.1.0-1_amd64.deb | head -40
```

Expected output includes `/opt/smartass/venv/...`, `/usr/lib/systemd/user/smartass-daemon.service`, `/etc/xdg/autostart/smartass-tray.desktop`, `/usr/share/icons/hicolor/scalable/apps/ai.talonic.smartass.svg`, `/usr/share/smartass/plugins/weather/...`.

- [ ] **Step 4: Commit any build-fix tweaks (if needed)**

If the build needed changes to `debian/rules` or deps, commit them with a descriptive message.

---

## Phase 7 — Smoke Test the Installed App

### Task 7.1: End-to-end install + verify

**Files:** none

- [ ] **Step 1: Install**

```bash
sudo apt-get install -y ./smartass_0.1.0-1_amd64.deb
```

Expected: no errors; postinst enables the user unit globally.

- [ ] **Step 2: Confirm unit is installed**

```bash
systemctl --user cat smartass-daemon.service
```

Expected: prints the unit file.

- [ ] **Step 3: Log out and log back in**

(Required for `systemctl --global enable` + `default.target.wants` symlinks to take effect for your user.)

- [ ] **Step 4: Verify daemon is running**

```bash
systemctl --user status smartass-daemon.service
busctl --user call ai.talonic.Smartass /ai/talonic/Smartass ai.talonic.Smartass.Core Ping
```

Expected: `active (running)`; Ping returns `"pong 0.1.0"`.

- [ ] **Step 5: Tray icon visible in the GNOME top bar**

Expected: a small robot icon in the top panel. (If not: confirm the AppIndicator extension is enabled — `gnome-extensions list --enabled`.)

- [ ] **Step 6: Click the tray icon → main window opens**

Expected:
- A window titled "Smartass" with **Settings** tab visible.
- Plugin list shows `Weather (0.1.0)`.

- [ ] **Step 7: Enable Weather**

- Click `Weather`, then click `Enable`.
- A **Weather** tab appears.

- [ ] **Step 8: Configure Weather for Berlin (default)**

- With `Weather` selected in the list, Save the default settings (`city = Berlin`, `units = metric`, `poll_minutes = 15`).
- Switch to the Weather tab.
- Within ~60s you should see current conditions and a 7-day forecast.

- [ ] **Step 9: Import / Export**

- In Settings tab, `Export…` → save to `~/Desktop/smartass-export.toml`.
- Open the file; confirm `[config]` contains `enabled_plugins = ["weather"]` and `[plugins.weather]` has your city.
- Flip units to imperial via the Weather form, save, then `Import…` the original export and confirm units revert.

- [ ] **Step 10: Record results in `docs/manual_qa.md`**

Create `docs/manual_qa.md`:

```markdown
# Manual QA Checklist — Smartass MVP

- [ ] `.deb` installs without error on Ubuntu 22.04 and 24.04
- [ ] `systemctl --user status smartass-daemon.service` → active
- [ ] `busctl --user call ai.talonic.Smartass /ai/talonic/Smartass ai.talonic.Smartass.Core Ping` → pong
- [ ] Tray icon visible in the GNOME top bar
- [ ] Left-click tray opens the main window
- [ ] Settings tab always visible
- [ ] Weather plugin listed; enabling adds a tab; disabling removes it
- [ ] Weather tab shows current + 7-day forecast for Berlin
- [ ] Changing `city` → Weather tab updates within one poll interval
- [ ] Export → Import roundtrip preserves settings
- [ ] Uninstall removes the unit and binaries; tray disappears on logout
```

- [ ] **Step 11: Final commit**

```bash
git add docs/manual_qa.md
git commit -m "docs: manual QA checklist for MVP smoke test"
```

---

## Self-Review (done by the author of this plan)

- **Spec coverage:**
  - §2 Architecture (split daemon + tray, lifecycle, icon) → Tasks 0.2, 2.5, 4.5, 6.3 ✓
  - §3 PluginInterface → Tasks 1.3, 1.4, 1.5 ✓
  - §4 D-Bus surface (Core + per-plugin) → Tasks 2.4, 5.1 (PluginObject) ✓
  - §5 Config + data layout → Tasks 1.1, 1.6 ✓
  - §5.4 Import/export → Task 2.4 (methods) + Task 4.3 (UI) ✓
  - §6 Packaging → Tasks 6.1–6.4 ✓
  - §7 Testing + errors → tests in every core/daemon/plugin task; manual QA in Task 7.1 ✓
  - §8 MVP milestones (1..7) → Phases 1..7 mirror them ✓

- **Placeholder scan:** No `TODO` / `TBD` / `implement later` / vague "add error handling". Every task has either full code or exact commands.

- **Type / name consistency:**
  - `dbus_names.plugin_path` used in service, manager, and tab — signature consistent.
  - `PluginContext` fields used by WeatherPlugin match those defined in Task 1.5.
  - `SettingsSchema.to_dict()` output shape assumed by `SchemaForm` matches the implementation in Task 1.4.
  - `PluginManager.attach_bus` added in Task 5.1 — used only in `__main__` post-creation. Consistent.
  - `AsyncHttpClient.get_json` — signature `(url, **kwargs)` accepting `params=...`, matches the Open-Meteo client.

No issues found beyond what's already documented in-plan.
