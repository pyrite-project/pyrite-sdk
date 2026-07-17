import unittest
from typing import get_type_hints

from pyrite_sdk.api.ui import sentence as sentence_module
from pyrite_sdk.api.ui.sentence import (
    Alignment,
    Axis,
    BoxFit,
    Clip,
    Colors,
    CrossAxisAlignment,
    FontStyle,
    FontWeight,
    Icons,
    MainAxisAlignment,
    MainAxisSize,
    TextAlign,
    TextDirection,
)


def public_annotation_names(namespace: object) -> set[str]:
    names: set[str] = set()
    for namespace_type in type(namespace).__mro__:
        names.update(
            name
            for name in getattr(namespace_type, "__annotations__", {})
            if not name.startswith("_")
        )
    return names


class UiNamespaceTest(unittest.TestCase):
    def test_material_icon_catalog_is_complete_and_preserves_metadata(self) -> None:
        self.assertEqual(len(Icons._codes), 8825)
        self.assertEqual(len(Icons._match_text_direction), 303)
        self.assertEqual(len(set(Icons._codes.values())), 8622)
        self.assertIn("trending_flat", Icons._match_text_direction)
        self.assertNotIn("trending_neutral", Icons._match_text_direction)

        self.assertEqual(
            Icons.ten_k.to_rfw(),
            '{"icon": 0xe000, "fontFamily": "MaterialIcons"}',
        )
        self.assertEqual(
            Icons.arrow_back.to_rfw(),
            '{"icon": 0xe092, "fontFamily": "MaterialIcons", "matchTextDirection": true}',
        )
        self.assertEqual(
            Icons.zoom_out_map_outlined.to_rfw(),
            '{"icon": 0xf4dd, "fontFamily": "MaterialIcons"}',
        )

    def test_material_icon_type_hints_match_every_runtime_icon(self) -> None:
        self.assertEqual(public_annotation_names(Icons), set(Icons._codes))
        resolved_hints = get_type_hints(type(Icons))
        self.assertIs(resolved_hints["zoom_out_map_outlined"], type(Icons.ten_k))

    def test_dynamic_namespaces_list_all_supported_properties(self) -> None:
        expected_properties = {
            Colors: {
                "black",
                "white",
                "red",
                "blue",
                "green",
                "grey",
                "blueGrey",
                "blue_grey",
            },
            Alignment: {
                "center",
                "center_left",
                "center_right",
                "top_left",
                "top_center",
                "top_right",
                "bottom_left",
                "bottom_center",
                "bottom_right",
            },
            FontWeight: {
                "w100",
                "w200",
                "w300",
                "w400",
                "w500",
                "w600",
                "w700",
                "w800",
                "w900",
                "normal",
                "bold",
            },
            FontStyle: {"normal", "italic"},
            MainAxisAlignment: {
                "start",
                "end",
                "center",
                "space_between",
                "space_around",
                "space_evenly",
            },
            CrossAxisAlignment: {"start", "end", "center", "stretch", "baseline"},
            MainAxisSize: {"min", "max"},
            TextAlign: {"left", "right", "center", "justify", "start", "end"},
            TextDirection: {"rtl", "ltr"},
            Axis: {"horizontal", "vertical"},
            BoxFit: {
                "fill",
                "contain",
                "cover",
                "fit_width",
                "fit_height",
                "none",
                "scale_down",
            },
            Clip: {"none", "hard_edge", "anti_alias", "anti_alias_with_save_layer"},
        }

        for namespace, expected in expected_properties.items():
            with self.subTest(namespace=type(namespace).__name__):
                self.assertEqual(public_annotation_names(namespace), expected)

    def test_all_exported_namespace_singletons_have_concrete_type_hints(self) -> None:
        expected_namespaces = {
            "Icons",
            "Colors",
            "EdgeInsets",
            "Alignment",
            "Border",
            "BorderRadius",
            "BoxDecoration",
            "Radius",
            "TextStyle",
            "FontWeight",
            "FontStyle",
            "MainAxisAlignment",
            "CrossAxisAlignment",
            "MainAxisSize",
            "TextAlign",
            "TextDirection",
            "Axis",
            "BoxFit",
            "Clip",
        }
        self.assertTrue(
            expected_namespaces.issubset(sentence_module.expression.__annotations__)
        )

    def test_getattr_fallbacks_are_preserved(self) -> None:
        self.assertEqual(MainAxisAlignment.space_between.to_rfw(), '"spaceBetween"')
        self.assertEqual(MainAxisAlignment.future_value.to_rfw(), '"futureValue"')
        with self.assertRaises(AttributeError):
            getattr(Icons, "not_a_material_icon")


if __name__ == "__main__":
    unittest.main()
