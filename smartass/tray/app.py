# smartass/tray/app.py
"""Wires QApplication, tray icon, and main window together."""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QCoreApplication
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QSystemTrayIcon

from smartass import __version__
from smartass.tray.daemon_client import DaemonClient
from smartass.tray.main_window import MainWindow
from smartass.tray.tray_icon import TrayIcon

log = logging.getLogger(__name__)

ICON_CANDIDATES = [
    Path("/usr/share/icons/hicolor/scalable/apps/ai.talonic.smartass.svg"),
    Path(__file__).resolve().parent.parent.parent / "assets" / "icons" / "smartass.svg",
]


def _load_icon() -> QIcon:
    # Prefer the *symbolic* themed icon — GNOME auto-recolors single-color
    # symbolic icons to match the panel foreground (dark/light theme aware).
    # Falls back to the regular themed icon and then to shipped SVGs.
    for name in ("ai.talonic.smartass-symbolic", "ai.talonic.smartass"):
        icon = QIcon.fromTheme(name)
        if not icon.isNull():
            return icon
    for p in ICON_CANDIDATES:
        if p.is_file():
            return QIcon(str(p))
    return QIcon.fromTheme("applications-accessories")


def _ensure_daemon_running() -> None:
    try:
        subprocess.run(
            ["systemctl", "--user", "start", "smartass-daemon.service"],
            timeout=5,
            check=False,
        )
    except Exception as e:
        log.warning("could not start daemon via systemd: %s", e)


def run_tray() -> int:
    QCoreApplication.setOrganizationName("Talonic")
    QCoreApplication.setApplicationName("Smartass")
    QCoreApplication.setApplicationVersion(__version__)

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    _ensure_daemon_running()

    try:
        client = DaemonClient()
    except Exception as e:
        log.error("session bus unavailable: %s", e)
        return 2

    if not QSystemTrayIcon.isSystemTrayAvailable():
        log.error("system tray not available on this desktop")
        return 3

    window = MainWindow(client)

    def toggle_window() -> None:
        if window.isVisible():
            window.hide()
        else:
            window.show()
            window.raise_()
            window.activateWindow()

    def restart_daemon() -> None:
        subprocess.run(
            ["systemctl", "--user", "restart", "smartass-daemon.service"],
            timeout=10,
            check=False,
        )

    tray = TrayIcon(
        icon=_load_icon(),
        on_toggle_window=toggle_window,
        on_quit=app.quit,
        on_restart_daemon=restart_daemon,
    )
    tray.show()

    return app.exec()
