import unittest

from pyrite_sdk.api.ui.page import Page
from pyrite_sdk.api.ui.widgets import Column, NewWidget, Text
from pyrite_sdk.utils import RFWFormatError, format_rfw


class RFWFormatterTest(unittest.TestCase):
    def test_formats_output_generated_by_sdk_page(self) -> None:
        page = Page(["core.widgets", "core.material"])
        root = NewWidget("root").add_to(page)
        with Column().add_to(root):
            Text("Hello, {RFW}")
            Text("Second")

        expected = """import core.widgets;
import core.material;

widget root {} = Column(
  children: [
    Text(text: "Hello, {RFW}"),
    Text(text: "Second")
  ]
);
"""

        self.assertEqual(format_rfw(page.to_rfw()), expected)

    def test_formats_compact_page_and_is_idempotent(self) -> None:
        source = (
            "import core.widgets;import core.material;"
            "widget root {}=Scaffold("
            "appBar:AppBar(title:Text(text:\"Home\")),"
            "body:Column(children:[Text(text:\"Hello\"),Text(text:\"RFW\")])"
            ");"
        )
        expected = """import core.widgets;
import core.material;

widget root {} = Scaffold(
  appBar: AppBar(title: Text(text: "Home")),
  body: Column(
    children: [
      Text(text: "Hello"),
      Text(text: "RFW")
    ]
  )
);
"""

        formatted = format_rfw(source)

        self.assertEqual(formatted, expected)
        self.assertEqual(format_rfw(formatted), expected)

    def test_formats_switch_event_maps_and_custom_indentation(self) -> None:
        source = (
            'widget root {count:0,label:"Ready"}=Text('
            'text:switch state.count {0:"None",default:"Some"},'
            'onTap:event "tap" {"value":state.count}'
            ");"
        )
        expected = """widget root {
    count: 0,
    label: "Ready"
} = Text(
    text: switch state.count {
        0: "None",
        default: "Some"
    },
    onTap: event "tap" {"value": state.count}
);
"""

        self.assertEqual(format_rfw(source, indent_size=4), expected)

    def test_preserves_delimiters_inside_strings_and_comments(self) -> None:
        source = (
            'widget root {}=Text(text:"{not: [syntax]}; // still text",'
            'semanticsLabel:"say \\"hello\\"")/* keep { punctuation } */;'
        )
        expected = """widget root {} = Text(
  text: "{not: [syntax]}; // still text",
  semanticsLabel: "say \\"hello\\""
) /* keep { punctuation } */;
"""

        self.assertEqual(format_rfw(source), expected)

    def test_formats_for_entries_and_line_comments(self) -> None:
        source = (
            "widget root {}=Column(children:["
            "...for item in data.items:Text(text:item.label),// fallback\n"
            'Text(text:"Empty")]);'
        )
        expected = """widget root {} = Column(
  children: [
    ...for item in data.items:
      Text(text: item.label), // fallback
    Text(text: "Empty")
  ]
);
"""

        self.assertEqual(format_rfw(source), expected)

    def test_empty_input_and_format_options(self) -> None:
        self.assertEqual(format_rfw(" \n\t"), "")
        self.assertEqual(
            format_rfw('widget root {}=Text(text:"Hi");', max_line_length=20),
            'widget root {} = Text(\n  text: "Hi"\n);\n',
        )

        with self.assertRaisesRegex(ValueError, "indent_size"):
            format_rfw("widget root = Text();", indent_size=-1)
        with self.assertRaisesRegex(ValueError, "max_line_length"):
            format_rfw("widget root = Text();", max_line_length=0)

    def test_reports_structural_errors_with_location(self) -> None:
        with self.assertRaisesRegex(
            RFWFormatError,
            r"Expected closing delimiter '\]', found '\)' at line 3, column 1",
        ):
            format_rfw("widget root = [\n  Text()\n);")

        with self.assertRaisesRegex(
            RFWFormatError,
            "Unterminated string at line 1, column 26",
        ):
            format_rfw('widget root = Text(text: "missing);')


if __name__ == "__main__":
    unittest.main()
