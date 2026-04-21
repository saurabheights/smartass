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
