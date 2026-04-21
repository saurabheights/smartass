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
    plugin_class: Optional[type[PluginInterface]] = None


@dataclass
class PluginManager:
    config_store: object
    roots: list[Path] = field(default_factory=list)

    def discover(self) -> list[DiscoveredPlugin]:
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
