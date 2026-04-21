"""A minimal plugin used only by tests. Not bundled in the app."""

from smartass.core.plugin_interface import PluginInterface, SettingsSchema, StringField


class HelloPlugin(PluginInterface):
    id = "hello"

    def build_tab(self, parent):  # pragma: no cover
        return None

    def settings_schema(self) -> SettingsSchema:
        return SettingsSchema(fields=(StringField(key="greeting", label="Greeting", default="hi"),))
