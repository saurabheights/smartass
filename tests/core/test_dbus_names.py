from smartass.core import dbus_names


def test_constants_match_spec():
    assert dbus_names.SERVICE == "ai.talonic.Smartass"
    assert dbus_names.CORE_PATH == "/ai/talonic/Smartass"
    assert dbus_names.CORE_IFACE == "ai.talonic.Smartass.Core"
    assert dbus_names.PLUGIN_IFACE == "ai.talonic.Smartass.Plugin"


def test_plugin_path_for():
    assert dbus_names.plugin_path("weather") == "/ai/talonic/Smartass/plugins/weather"


def test_plugin_iface_for():
    assert dbus_names.plugin_iface("weather") == "ai.talonic.Smartass.Plugin.Weather"
    assert dbus_names.plugin_iface("quick_notes") == "ai.talonic.Smartass.Plugin.QuickNotes"
