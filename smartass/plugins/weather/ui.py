# smartass/plugins/weather/ui.py
"""Weather tab — current conditions + 7-day forecast.

Reads data from the daemon via the per-plugin D-Bus object GetState().
"""

from __future__ import annotations

import json
from typing import Any

from PySide6.QtCore import Qt, QTimer
from PySide6.QtDBus import QDBusConnection, QDBusInterface, QDBusMessage
from PySide6.QtGui import QFont, QPalette
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from smartass.core import dbus_names

WMO_CODE_TO_LABEL = {
    0: "Clear",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Drizzle",
    55: "Heavy drizzle",
    61: "Light rain",
    63: "Rain",
    65: "Heavy rain",
    71: "Light snow",
    73: "Snow",
    75: "Heavy snow",
    80: "Rain showers",
    81: "Heavy rain showers",
    82: "Violent rain showers",
    95: "Thunderstorm",
    96: "Thunderstorm w/ hail",
    99: "Severe thunderstorm",
}

WMO_CODE_TO_EMOJI = {
    0: "☀️",
    1: "🌤️",
    2: "⛅",
    3: "☁️",
    45: "🌫️",
    48: "🌫️",
    51: "🌦️", 53: "🌦️", 55: "🌧️",
    61: "🌧️", 63: "🌧️", 65: "🌧️",
    71: "🌨️", 73: "🌨️", 75: "❄️",
    80: "🌦️", 81: "🌧️", 82: "⛈️",
    95: "⛈️", 96: "⛈️", 99: "⛈️",
}


class WeatherTab(QWidget):
    """Polls the daemon every 30s for a cached snapshot; no direct API calls."""

    def __init__(self, parent: QWidget | None, plugin: Any) -> None:
        super().__init__(parent)
        self._plugin = plugin
        self._bus = QDBusConnection.sessionBus()

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(16)

        # --- Top header ---
        header = QHBoxLayout()
        self._city_label = QLabel("—")
        hf = QFont()
        hf.setPointSize(22)
        hf.setBold(True)
        self._city_label.setFont(hf)
        header.addWidget(self._city_label)

        self._updated_label = QLabel("")
        self._updated_label.setForegroundRole(QPalette.ColorRole.PlaceholderText)
        uf = QFont()
        uf.setPointSize(10)
        self._updated_label.setFont(uf)
        header.addWidget(self._updated_label)

        self._stale_label = QLabel("")
        # setForegroundRole can't give us "warning red" from the palette
        # reliably across themes; keep a moderate red that works on both.
        self._stale_label.setStyleSheet("color: #d45a5a;")
        header.addWidget(self._stale_label)
        header.addStretch()

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._refresh_from_daemon)
        header.addWidget(refresh_btn)
        root.addLayout(header)

        # --- Hero card: today ---
        # Use Qt's default StyledPanel rendering — it follows the active
        # palette (dark on dark themes, light on light themes). Custom
        # stylesheets that hardcode palette(base) resolve at parse time
        # and won't track theme changes.
        hero = QFrame()
        hero.setFrameShape(QFrame.Shape.StyledPanel)
        hero.setFrameShadow(QFrame.Shadow.Raised)
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(20, 16, 20, 16)
        hero_layout.setSpacing(24)

        # Left: emoji + temp + condition
        self._emoji_label = QLabel("—")
        ef = QFont()
        ef.setPointSize(56)
        self._emoji_label.setFont(ef)
        self._emoji_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hero_layout.addWidget(self._emoji_label)

        temp_col = QVBoxLayout()
        temp_col.setSpacing(2)
        self._temp_label = QLabel("—")
        tf = QFont()
        tf.setPointSize(48)
        tf.setBold(True)
        self._temp_label.setFont(tf)
        temp_col.addWidget(self._temp_label)

        self._condition_label = QLabel("—")
        cf = QFont()
        cf.setPointSize(16)
        self._condition_label.setFont(cf)
        # No explicit color — inherits palette text so it follows the theme
        temp_col.addWidget(self._condition_label)

        self._feels_label = QLabel("")
        ff = QFont()
        ff.setPointSize(11)
        self._feels_label.setFont(ff)
        # Lower-emphasis via Qt's placeholder text role (theme-aware)
        self._feels_label.setForegroundRole(QPalette.ColorRole.PlaceholderText)
        temp_col.addWidget(self._feels_label)
        temp_col.addStretch()

        hero_layout.addLayout(temp_col, stretch=1)

        # Right: details grid
        self._details_grid = QGridLayout()
        self._details_grid.setHorizontalSpacing(24)
        self._details_grid.setVerticalSpacing(8)
        hero_layout.addLayout(self._details_grid, stretch=2)

        root.addWidget(hero)

        # --- 7-day forecast ---
        forecast_label = QLabel("7-day forecast")
        flf = QFont()
        flf.setPointSize(12)
        flf.setBold(True)
        forecast_label.setFont(flf)
        root.addWidget(forecast_label)

        self._forecast_container = QFrame()
        self._forecast_container.setFrameShape(QFrame.Shape.StyledPanel)
        self._forecast_container.setFrameShadow(QFrame.Shadow.Raised)
        self._forecast_grid = QGridLayout(self._forecast_container)
        self._forecast_grid.setContentsMargins(12, 12, 12, 12)
        self._forecast_grid.setHorizontalSpacing(16)
        self._forecast_grid.setVerticalSpacing(6)
        root.addWidget(self._forecast_container)

        root.addStretch()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)
        self._timer.start(30_000)
        self._refresh()

    # --- actions ---

    def _refresh_from_daemon(self) -> None:
        iface = QDBusInterface(
            dbus_names.SERVICE,
            dbus_names.plugin_path("weather"),
            dbus_names.PLUGIN_IFACE,
            self._bus,
        )
        if iface.isValid():
            iface.call("RefreshNow")
        # Give the daemon a moment to complete the fetch, then pull state.
        QTimer.singleShot(1500, self._refresh)

    def _refresh(self) -> None:
        payload = self._get_state_from_daemon()
        if payload is None:
            self._city_label.setText("—")
            self._condition_label.setText("Weather plugin not available.")
            self._temp_label.setText("—")
            self._emoji_label.setText("❓")
            self._feels_label.setText("")
            self._updated_label.setText("")
            self._stale_label.setText("")
            self._clear_details_grid()
            self._clear_forecast_grid()
            return
        self._render(payload)

    # --- rendering ---

    def _clear_details_grid(self) -> None:
        while self._details_grid.count():
            item = self._details_grid.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()

    def _clear_forecast_grid(self) -> None:
        while self._forecast_grid.count():
            item = self._forecast_grid.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()

    def _render(self, payload: dict[str, Any]) -> None:
        city = payload.get("city", "—")
        country = payload.get("country", "")
        self._city_label.setText(f"{city}, {country}" if country else city)

        units = payload.get("units", "metric")
        deg = "°C" if units == "metric" else "°F"
        wind_unit = "km/h" if units == "metric" else "mph"
        precip_unit = "mm" if units == "metric" else "in"

        cur = payload.get("current") or {}
        code = int(cur.get("weather_code", -1))
        condition = WMO_CODE_TO_LABEL.get(code, "—")
        emoji = WMO_CODE_TO_EMOJI.get(code, "❓")

        # --- hero card ---
        self._emoji_label.setText(emoji)
        temp = cur.get("temperature", "—")
        self._temp_label.setText(f"{temp}{deg}" if temp != "—" else "—")
        self._condition_label.setText(condition)
        feels = cur.get("apparent_temperature")
        if feels is not None:
            self._feels_label.setText(f"Feels like {feels}{deg}")
        else:
            self._feels_label.setText("")

        now_str = cur.get("time", "")
        self._updated_label.setText(f"Updated {now_str}" if now_str else "")

        # --- details grid ---
        self._clear_details_grid()
        details = [
            ("Humidity", f"{cur.get('humidity', '—')}%"),
            ("Wind", f"{cur.get('wind_speed', '—')} {wind_unit}"),
            ("Precipitation", f"{cur.get('precipitation', 0)} {precip_unit}"),
            ("Cloud cover", f"{cur.get('cloud_cover', '—')}%"),
        ]
        daily = payload.get("daily", []) or []
        if daily:
            today = daily[0]
            details.extend(
                [
                    ("Sunrise", _time_only(today.get("sunrise", ""))),
                    ("Sunset", _time_only(today.get("sunset", ""))),
                    ("UV index (max)", f"{today.get('uv_index_max', '—')}"),
                    (
                        "Rain chance",
                        f"{today.get('precipitation_probability_max', 0)}%",
                    ),
                ]
            )
        for row, (label, value) in enumerate(details):
            lbl_k = QLabel(label)
            lbl_k.setForegroundRole(QPalette.ColorRole.PlaceholderText)
            lbl_v = QLabel(value)
            lvf = QFont()
            lvf.setBold(True)
            lbl_v.setFont(lvf)
            col = row % 2
            rr = row // 2
            self._details_grid.addWidget(lbl_k, rr, col * 2)
            self._details_grid.addWidget(lbl_v, rr, col * 2 + 1)

        # --- 7-day forecast ---
        self._clear_forecast_grid()
        headers = ["Day", "", f"High / Low {deg}", f"Rain %", "Conditions"]
        for col, h in enumerate(headers):
            hdr = QLabel(h)
            hf2 = QFont()
            hf2.setBold(True)
            hdr.setFont(hf2)
            hdr.setForegroundRole(QPalette.ColorRole.PlaceholderText)
            self._forecast_grid.addWidget(hdr, 0, col)
        for row, d in enumerate(daily, start=1):
            day_label = QLabel(_weekday(d.get("date", "")))
            self._forecast_grid.addWidget(day_label, row, 0)

            emoji_lbl = QLabel(WMO_CODE_TO_EMOJI.get(int(d.get("weather_code", -1)), "❓"))
            emf = QFont()
            emf.setPointSize(16)
            emoji_lbl.setFont(emf)
            self._forecast_grid.addWidget(emoji_lbl, row, 1)

            hl = QLabel(f"{d.get('temp_max', '—')} / {d.get('temp_min', '—')}")
            self._forecast_grid.addWidget(
                hl, row, 2, alignment=Qt.AlignmentFlag.AlignRight
            )

            rain = QLabel(f"{d.get('precipitation_probability_max', 0)}%")
            self._forecast_grid.addWidget(rain, row, 3, alignment=Qt.AlignmentFlag.AlignRight)

            cond = QLabel(WMO_CODE_TO_LABEL.get(int(d.get("weather_code", -1)), "—"))
            cond.setForegroundRole(QPalette.ColorRole.PlaceholderText)
            self._forecast_grid.addWidget(cond, row, 4)

        if payload.get("stale"):
            self._stale_label.setText("(stale — daemon could not refresh)")
        else:
            self._stale_label.setText("")

    def _get_state_from_daemon(self) -> dict[str, Any] | None:
        iface = QDBusInterface(
            dbus_names.SERVICE,
            dbus_names.plugin_path("weather"),
            dbus_names.PLUGIN_IFACE,
            self._bus,
        )
        if not iface.isValid():
            return None
        reply = iface.call("GetState")
        if reply.type() == QDBusMessage.ErrorMessage:
            return None
        args = reply.arguments()
        if not args:
            return None
        try:
            wire = json.loads(args[0])
        except (json.JSONDecodeError, TypeError):
            return None
        snap = wire.get("snapshot")
        if snap is None:
            return None
        # Annotate stale flag onto the snapshot so _render can pick it up
        snap["stale"] = bool(wire.get("stale", False))
        return snap


def _weekday(date_str: str) -> str:
    """Return 'Mon', 'Tue', ... from a YYYY-MM-DD string; fall back to raw."""
    try:
        from datetime import date as _date
        d = _date.fromisoformat(date_str)
        return d.strftime("%a %b %-d")
    except (ValueError, TypeError):
        return date_str


def _time_only(iso_ts: str) -> str:
    """Return 'HH:MM' from an ISO datetime; fall back to raw."""
    if not iso_ts:
        return "—"
    # Open-Meteo uses local time without 'Z'/offset in practice.
    _, _, hm = iso_ts.partition("T")
    if hm:
        return hm[:5]
    return iso_ts
