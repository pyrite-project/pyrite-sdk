from pyrite_sdk.api.ui import *
from pyrite_sdk.core.plugin import UiPlugin
from pyrite_sdk.models.consts import Package, Ui


MARKDOWN = """# Markdown Demo

Render markdown from a PyriteSDK UI plugin.

## Supported content

- headings
- paragraphs
- **bold** and _italic_ text
- inline `code`
- links surfaced through `on_tap_link`

```python
from pyrite_sdk.api.ui import MarkdownBlock
```

Open the [Pyrite project](https://example.com/pyrite) link to test events.
"""


def record_link(url: str = "", **kwargs) -> None:
    plugin.bridge.let(data.last_link, url)


def reset_link(**kwargs) -> None:
    plugin.bridge.let(data.last_link, "No link tapped yet")


def build_home_page() -> Page:
    page = Page(packages=[Package.core.widgets, Package.core.material])
    root = NewWidget(Ui.root).add_to(page)

    with Scaffold(
        app_bar=AppBar(title=Text("Markdown Plugin")),
    ).add_to(root):
        with SafeArea():
            with SingleChildScrollView(padding=EdgeInsets.all(16)):
                with Column(cross_axis_alignment=CrossAxisAlignment.start):
                    Text(
                        "markdown_widget via PyriteSDK",
                        style=TextStyle(font_size=20, font_weight=FontWeight.bold),
                    )
                    SizedBox(height=8)
                    Text(
                        "This page exercises the MarkdownBlock SDK wrapper.",
                        style=TextStyle(font_size=13, color=Colors.grey),
                    )
                    SizedBox(height=16)
                    with Card(elevation=1, margin=EdgeInsets.all(0)):
                        MarkdownBlock(
                            MARKDOWN,
                            selectable=False,
                            padding=EdgeInsets.all(16),
                            on_tap_link=Event(record_link),
                        )
                    SizedBox(height=16)
                    Text(
                        ["Last link: ", data.last_link],
                        style=TextStyle(font_size=13, color=Colors.blue),
                    )
                    SizedBox(height=8)
                    with ElevatedButton(on_pressed=Event(reset_link)):
                        Text("Reset link state")

    return page


class MarkdownPlugin(UiPlugin):
    def __init__(self):
        super().__init__()
        self.pages = {"home": build_home_page()}

    def on_start(self):
        print("Markdown plugin started")

    def on_dispose(self):
        print("Markdown plugin disposed")


plugin = MarkdownPlugin()
plugin.start()
