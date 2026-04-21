"""D-Bus naming constants for Smartass."""

from __future__ import annotations

SERVICE = "ai.talonic.Smartass"
CORE_PATH = "/ai/talonic/Smartass"
CORE_IFACE = "ai.talonic.Smartass.Core"
PLUGIN_IFACE = "ai.talonic.Smartass.Plugin"


def plugin_path(plugin_id: str) -> str:
    return f"{CORE_PATH}/plugins/{plugin_id}"


def _to_pascal(snake: str) -> str:
    return "".join(part.capitalize() for part in snake.split("_"))


def plugin_iface(plugin_id: str) -> str:
    return f"{PLUGIN_IFACE}.{_to_pascal(plugin_id)}"
