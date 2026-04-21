"""Plugin manifest loading and validation."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # type: ignore[import-not-found]

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
