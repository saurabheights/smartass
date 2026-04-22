"""Thin typed client for Open-Meteo (forecast) + its geocoding service."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import zip_longest
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
    apparent_temperature: float
    weather_code: int
    humidity: int
    wind_speed: float
    wind_direction: int
    precipitation: float
    cloud_cover: int
    is_day: int


@dataclass(frozen=True)
class DailyEntry:
    date: str
    temp_max: float
    temp_min: float
    weather_code: int
    sunrise: str
    sunset: str
    precipitation_sum: float
    precipitation_probability_max: int
    uv_index_max: float
    wind_speed_max: float


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
            "current": (
                "temperature_2m,apparent_temperature,weather_code,"
                "relative_humidity_2m,wind_speed_10m,wind_direction_10m,"
                "precipitation,cloud_cover,is_day"
            ),
            "daily": (
                "temperature_2m_max,temperature_2m_min,weather_code,"
                "sunrise,sunset,precipitation_sum,precipitation_probability_max,"
                "uv_index_max,wind_speed_10m_max"
            ),
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
                time=str(cur.get("time", "")),
                temperature=float(cur.get("temperature_2m", 0.0)),
                apparent_temperature=float(cur.get("apparent_temperature", cur.get("temperature_2m", 0.0))),
                weather_code=int(cur.get("weather_code", 0)),
                humidity=int(cur.get("relative_humidity_2m", 0)),
                wind_speed=float(cur.get("wind_speed_10m", 0.0)),
                wind_direction=int(cur.get("wind_direction_10m", 0)),
                precipitation=float(cur.get("precipitation", 0.0)),
                cloud_cover=int(cur.get("cloud_cover", 0)),
                is_day=int(cur.get("is_day", 1)),
            )
            days = list(
                zip_longest(
                    daily.get("time", []),
                    daily.get("temperature_2m_max", []),
                    daily.get("temperature_2m_min", []),
                    daily.get("weather_code", []),
                    daily.get("sunrise", []),
                    daily.get("sunset", []),
                    daily.get("precipitation_sum", []),
                    daily.get("precipitation_probability_max", []),
                    daily.get("uv_index_max", []),
                    daily.get("wind_speed_10m_max", []),
                    fillvalue=None,
                )
            )
            daily_entries = [
                DailyEntry(
                    date=str(d) if d is not None else "",
                    temp_max=float(mx) if mx is not None else 0.0,
                    temp_min=float(mn) if mn is not None else 0.0,
                    weather_code=int(wc) if wc is not None else 0,
                    sunrise=str(sr) if sr is not None else "",
                    sunset=str(ss) if ss is not None else "",
                    precipitation_sum=float(psum) if psum is not None else 0.0,
                    precipitation_probability_max=int(pprob) if pprob is not None else 0,
                    uv_index_max=float(uv) if uv is not None else 0.0,
                    wind_speed_max=float(wmax) if wmax is not None else 0.0,
                )
                for (d, mx, mn, wc, sr, ss, psum, pprob, uv, wmax) in days
            ]
        except (KeyError, TypeError, ValueError) as e:
            raise WeatherError(f"malformed forecast payload: {e}") from e
        return WeatherSnapshot(current=current, daily=daily_entries, units=units)
