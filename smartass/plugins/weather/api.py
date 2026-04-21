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
