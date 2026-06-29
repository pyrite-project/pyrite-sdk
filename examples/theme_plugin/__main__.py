from pyrite_sdk.core.plugin import Plugin


class NordPlugin(Plugin):
    def on_start(self):
        print("Nord Theme: registering theme...")
        self.theme.register("nord", {
            # No mode → supports light/dark switching
            # Light colors
            "color.primary": "#5E81AC",
            "color.onPrimary": "#ECEFF4",
            "color.primaryContainer": "#81A1C1",
            "color.onPrimaryContainer": "#2E3440",
            "color.secondary": "#88C0D0",
            "color.onSecondary": "#2E3440",
            "color.secondaryContainer": "#8FBCBB",
            "color.onSecondaryContainer": "#2E3440",
            "color.tertiary": "#B48EAD",
            "color.onTertiary": "#ECEFF4",
            "color.tertiaryContainer": "#D8DEE9",
            "color.onTertiaryContainer": "#2E3440",
            "color.error": "#BF616A",
            "color.onError": "#ECEFF4",
            "color.errorContainer": "#D08770",
            "color.onErrorContainer": "#2E3440",
            "color.surface": "#ECEFF4",
            "color.onSurface": "#2E3440",
            "color.surfaceDim": "#D8DEE9",
            "color.surfaceBright": "#ECEFF4",
            "color.surfaceContainerLowest": "#FFFFFF",
            "color.surfaceContainerLow": "#E5E9F0",
            "color.surfaceContainer": "#D8DEE9",
            "color.surfaceContainerHigh": "#C8CED8",
            "color.surfaceContainerHighest": "#B8C0CC",
            "color.onSurfaceVariant": "#4C566A",
            "color.outline": "#7B88A1",
            "color.outlineVariant": "#D8DEE9",
            "color.inverseSurface": "#2E3440",
            "color.onInverseSurface": "#ECEFF4",
            "color.inversePrimary": "#88C0D0",
            "color.scrim": "#2E3440",
            "color.shadow": "#2E3440",
            # Dark colors
            "dark.color.primary": "#88C0D0",
            "dark.color.onPrimary": "#2E3440",
            "dark.color.primaryContainer": "#5E81AC",
            "dark.color.onPrimaryContainer": "#ECEFF4",
            "dark.color.secondary": "#81A1C1",
            "dark.color.onSecondary": "#2E3440",
            "dark.color.secondaryContainer": "#4C566A",
            "dark.color.onSecondaryContainer": "#ECEFF4",
            "dark.color.tertiary": "#B48EAD",
            "dark.color.onTertiary": "#2E3440",
            "dark.color.tertiaryContainer": "#434C5E",
            "dark.color.onTertiaryContainer": "#ECEFF4",
            "dark.color.error": "#BF616A",
            "dark.color.onError": "#2E3440",
            "dark.color.errorContainer": "#D08770",
            "dark.color.onErrorContainer": "#ECEFF4",
            "dark.color.surface": "#2E3440",
            "dark.color.onSurface": "#ECEFF4",
            "dark.color.surfaceDim": "#2E3440",
            "dark.color.surfaceBright": "#3B4252",
            "dark.color.surfaceContainerLowest": "#1E2128",
            "dark.color.surfaceContainerLow": "#272C36",
            "dark.color.surfaceContainer": "#2E3440",
            "dark.color.surfaceContainerHigh": "#3B4252",
            "dark.color.surfaceContainerHighest": "#434C5E",
            "dark.color.onSurfaceVariant": "#D8DEE9",
            "dark.color.outline": "#7B88A1",
            "dark.color.outlineVariant": "#4C566A",
            "dark.color.inverseSurface": "#ECEFF4",
            "dark.color.onInverseSurface": "#2E3440",
            "dark.color.inversePrimary": "#5E81AC",
            # Corners
            "sub.defaultRadius": 6,
            "sub.cardRadius": 8,
            "sub.chipRadius": 6,
            "sub.inputDecoratorRadius": 6,
            "sub.textButtonRadius": 6,
            "sub.elevatedButtonRadius": 6,
            "sub.outlinedButtonRadius": 6,
            "sub.filledButtonRadius": 6,
            "sub.segmentedButtonRadius": 6,
            "sub.popupMenuRadius": 6,
            "sub.menuRadius": 6,
            "sub.searchBarRadius": 6,
            "sub.fabRadius": 16,
            "sub.tooltipRadius": 4,
            "sub.bottomSheetRadius": 16,
            # Layout
            "global.density": "standard",
            "global.fontFamily": "HarmonyOS Sans SC",
            # AppBar
            "appBar.elevation": 0,
            "appBar.scrolledUnderElevation": 1,
            # Divider
            "sub.useM2StyleDividerInM3": False,
            "sub.blendOnLevel": 10,
            "sub.blendOnColors": True,
        })
        print("Nord Theme: registered successfully")

    def on_dispose(self):
        print("Nord Theme: disposed")


plugin = NordPlugin()
plugin.start()
