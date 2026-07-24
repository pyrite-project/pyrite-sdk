from pyrite_sdk.core.plugin import DataPlugin


class TemplateThemePlugin(DataPlugin):
    def on_contribute(self):
        self.theme.contribute(
            "nord",
            {
                "color.primary": "#5E81AC",
                "color.onPrimary": "#ECEFF4",
                "color.surface": "#ECEFF4",
                "color.onSurface": "#2E3440",
                "dark.color.primary": "#88C0D0",
                "dark.color.onPrimary": "#2E3440",
                "dark.color.surface": "#2E3440",
                "dark.color.onSurface": "#ECEFF4",
            },
        )


plugin = TemplateThemePlugin()

if __name__ == "__main__":
    plugin.run_once()
