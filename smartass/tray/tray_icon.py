# smartass/tray/tray_icon.py
"""System tray icon wrapper."""

from __future__ import annotations

from typing import Callable

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenu, QSystemTrayIcon


class TrayIcon(QSystemTrayIcon):
    def __init__(
        self,
        icon: QIcon,
        on_toggle_window: Callable[[], None],
        on_quit: Callable[[], None],
        on_restart_daemon: Callable[[], None],
    ) -> None:
        super().__init__(icon)
        self.setToolTip("Smartass")

        menu = QMenu()
        show_action = QAction("Show / Hide", menu)
        show_action.triggered.connect(on_toggle_window)
        menu.addAction(show_action)

        restart_action = QAction("Restart daemon", menu)
        restart_action.triggered.connect(on_restart_daemon)
        menu.addAction(restart_action)

        menu.addSeparator()
        quit_action = QAction("Quit tray", menu)
        quit_action.triggered.connect(on_quit)
        menu.addAction(quit_action)

        self.setContextMenu(menu)
        self.activated.connect(self._on_activated)
        self._on_toggle = on_toggle_window

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._on_toggle()
