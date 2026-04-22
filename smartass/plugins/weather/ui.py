# smartass/plugins/weather/ui.py
"""Weather tab — current conditions + 7-day forecast.

Reads data from the daemon via the per-plugin D-Bus object GetState().
"""

from __future__ import annotations

import json
from typing import Any

from PySide6.QtCore import Qt, QTimer
from PySide6.QtDBus import QDBusConnection, QDBusInterface, QDBusMessage
from PySide6.QtGui import QFont
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


class WeatherTab(QWidget):
    """Polls the daemon every 30s for a cached snapshot; no direct API calls."""

    def __init__(self, parent: QWidget | None, plugin: Any) -> None:
        super().__init__(parent)
        self._plugin = plugin
        self._bus = QDBusConnection.sessionBus()

        root = QVBoxLayout(self)

        header = QHBoxLayout()
        self._city_label = QLabel("—")
        f = QFont()
        f.setPointSize(18)
        f.setBold(True)
        self._city_label.setFont(f)
        header.addWidget(self._city_label)

        self._stale_label = QLabel("")
        self._stale_label.setStyleSheet("color: #c66;")
        header.addWidget(self._stale_label)
        header.addStretch()

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._refresh)
        header.addWidget(refresh_btn)
        root.addLayout(header)

        self._current = QLabel("No data yet.")
        f2 = QFont()
        f2.setPointSize(14)
        self._current.setFont(f2)
        root.addWidget(self._current)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        root.addWidget(line)

        self._forecast_grid = QGridLayout()
        root.addLayout(self._forecast_grid)
        root.addStretch()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)
        self._timer.start(30_000)
        self._refresh()

    def _refresh(self) -> None:
        payload = self._get_state_from_daemon()
        if payload is None:
            self._city_label.setText("—")
            self._current.setText("Weather plugin not available.")
            self._stale_label.setText("")
            return
        self._render(payload)

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

    def _render(self, payload: dict[str, Any]) -> None:
        city = payload.get("city", "—")
        country = payload.get("country", "")
        self._city_label.setText(f"{city}, {country}" if country else city)

        units = payload.get("units", "metric")
        deg = "°C" if units == "metric" else "°F"
        wind = "km/h" if units == "metric" else "mph"

        cur = payload.get("current") or {}
        label = WMO_CODE_TO_LABEL.get(int(cur.get("weather_code", -1)), "—")
        self._current.setText(
            f"{cur.get('temperature', '—')}{deg} — {label}  "
            f"(humidity {cur.get('humidity', '—')}%, wind {cur.get('wind_speed', '—')} {wind})"
        )

        while self._forecast_grid.count():
            item = self._forecast_grid.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()

        daily = payload.get("daily", []) or []
        headers = ["Date", f"High {deg}", f"Low {deg}", "Conditions"]
        for col, h in enumerate(headers):
            hdr = QLabel(h)
            hf = QFont()
            hf.setBold(True)
            hdr.setFont(hf)
            self._forecast_grid.addWidget(hdr, 0, col)
        for row, d in enumerate(daily, start=1):
            self._forecast_grid.addWidget(QLabel(str(d.get("date", "—"))), row, 0)
            self._forecast_grid.addWidget(
                QLabel(str(d.get("temp_max", "—"))), row, 1, alignment=Qt.AlignmentFlag.AlignRight
            )
            self._forecast_grid.addWidget(
                QLabel(str(d.get("temp_min", "—"))), row, 2, alignment=Qt.AlignmentFlag.AlignRight
            )
            self._forecast_grid.addWidget(
                QLabel(WMO_CODE_TO_LABEL.get(int(d.get("weather_code", -1)), "—")), row, 3
            )

        if payload.get("stale"):
            self._stale_label.setText("(stale — daemon could not refresh)")
        else:
            self._stale_label.setText("")
