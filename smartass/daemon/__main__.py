"""Smartass daemon entrypoint."""

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

    pm.attach_bus(bus)
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
