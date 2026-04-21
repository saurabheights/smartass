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
