from pyrite_sdk.core.plugin import DataPlugin


class LanguagePackPlugin(DataPlugin):
    def on_contribute(self):
        self.i18n.contribute(
            "zh-CN",
            {
                "app.name": "Pyrite IDE",
                "menu.file": "文件",
                "menu.edit": "编辑",
                "menu.view": "视图",
                "menu.settings": "设置",
            },
        )
        self.i18n.contribute(
            "en",
            {
                "app.name": "Pyrite IDE",
                "menu.file": "File",
                "menu.edit": "Edit",
                "menu.view": "View",
                "menu.settings": "Settings",
            },
        )


plugin = LanguagePackPlugin()
plugin.run_once()
