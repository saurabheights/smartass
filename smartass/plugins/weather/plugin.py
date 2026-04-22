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

    # --- public API ---

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
                "apparent_temperature": snap.current.apparent_temperature,
                "weather_code": snap.current.weather_code,
                "humidity": snap.current.humidity,
                "wind_speed": snap.current.wind_speed,
                "wind_direction": snap.current.wind_direction,
                "precipitation": snap.current.precipitation,
                "cloud_cover": snap.current.cloud_cover,
                "is_day": snap.current.is_day,
            },
            "daily": [
                {
                    "date": d.date,
                    "temp_max": d.temp_max,
                    "temp_min": d.temp_min,
                    "weather_code": d.weather_code,
                    "sunrise": d.sunrise,
                    "sunset": d.sunset,
                    "precipitation_sum": d.precipitation_sum,
                    "precipitation_probability_max": d.precipitation_probability_max,
                    "uv_index_max": d.uv_index_max,
                    "wind_speed_max": d.wind_speed_max,
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
