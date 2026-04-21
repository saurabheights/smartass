"""Discovers, loads, and manages plugins' lifecycles."""

from __future__ import annotations

import importlib.util
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

from smartass.core import dbus_names
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
        http_factory: Optional[Callable[[], Any]] = None,
    ) -> None:
        self.config_store = config_store
        self.roots = list(roots)
        self._http_factory = http_factory
        self._discovered: dict[str, DiscoveredPlugin] = {}
        self._running: dict[str, _RunningPlugin] = {}
        self._bus: Any = None
        self._bus_objects: dict[str, Any] = {}

    def attach_bus(self, bus: Any) -> None:
        """Attach a live D-Bus connection for per-plugin object exports."""
        self._bus = bus

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
        logger = logging.getLogger(f"smartass.plugins.{m.id}")
        return PluginContext(
            config=None,
            data_dir=data_dir,
            log=logger,
            http=http,
            bus=None,
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
        if self.config_store is not None:
            ctx.config = PluginConfig(self.config_store, plugin_id, instance.settings_schema())
        try:
            instance.on_load()
            await instance.on_start()
        except Exception:
            log.exception("plugin %s failed to start", plugin_id)
            raise
        self._running[plugin_id] = _RunningPlugin(dp=dp, instance=instance)
        if self._bus is not None:
            from smartass.daemon.plugin_object import PluginObject
            obj = PluginObject(plugin_id, instance)
            self._bus.export(dbus_names.plugin_path(plugin_id), obj)
            self._bus_objects[plugin_id] = obj
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
        if self._bus is not None and plugin_id in self._bus_objects:
            obj = self._bus_objects.pop(plugin_id)
            self._bus.unexport(dbus_names.plugin_path(plugin_id), obj)
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
