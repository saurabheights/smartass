# tests/integration/test_daemon_weather.py
"""Requires dbus-run-session. Uses respx to mock Open-Meteo HTTP."""

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
async def test_enable_weather_over_dbus(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg_data"))

    # Copy the bundled weather plugin dir under a temp root so the test is hermetic.
    source = Path("smartass/plugins/weather").resolve()
    root = tmp_path / "plugins"
    (root / "weather").mkdir(parents=True)
    for fn in ("manifest.toml", "plugin.py", "api.py", "__init__.py"):
        src = source / fn
        if src.exists():
            (root / "weather" / fn).write_text(src.read_text())

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

        import json as _json
        rows = _json.loads(await core.call_list_plugins())
        assert any(r["id"] == "weather" for r in rows)

        await core.call_enable_plugin("weather")
        # Give the polling loop one tick
        await asyncio.sleep(0.2)

        rows = _json.loads(await core.call_list_plugins())
        row = next(r for r in rows if r["id"] == "weather")
        assert row["enabled"] is True

        await core.call_disable_plugin("weather")
        client_bus.disconnect()

    await pm.shutdown()
    bus.disconnect()
