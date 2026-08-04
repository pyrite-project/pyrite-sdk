import unittest

from pyrite_sdk.api.components import Icon, Image, Video
from pyrite_sdk.api.icons import Icons, MaterialIcon
from pyrite_sdk.api.resources import PluginResource, Resources


class ResourceApiTest(unittest.TestCase):
    def test_material_icons_are_typed_and_use_explicit_wire_references(self):
        icon = Icons.account_tree_outlined
        self.assertIsInstance(icon, MaterialIcon)
        self.assertEqual(icon.name, "account_tree_outlined")
        self.assertEqual(str(icon), "material:account_tree_outlined")
        self.assertEqual(
            Icon(icon).to_json(),
            {
                "type": "Icon",
                "props": {"name": "material:account_tree_outlined"},
            },
        )
        with self.assertRaises(AttributeError):
            _ = Icons.not_a_flutter_icon

    def test_plugin_resources_are_scoped_below_assets(self):
        resources = Resources()
        asset = resources.asset("assets/images/banner.webp")
        self.assertIsInstance(asset, PluginResource)
        self.assertEqual(asset.path, "assets/images/banner.webp")
        self.assertEqual(
            str(asset), "plugin-resource:///assets/images/banner.webp"
        )
        for invalid in (
            "banner.webp",
            "../banner.webp",
            "assets/../banner.webp",
            "assets\\banner.webp",
            "/assets/banner.webp",
        ):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                resources.asset(invalid)

    def test_image_and_video_serialize_plugin_resources(self):
        resources = Resources()
        image = Image(
            resources.asset("assets/images/banner.webp"),
            width=320,
            fit="cover",
        )
        video = Video(
            resources.asset("assets/videos/demo.mp4"),
            width=640,
            height=360,
            autoplay=True,
            show_controls=True,
        )
        self.assertEqual(
            image.to_json()["props"]["src"],
            "plugin-resource:///assets/images/banner.webp",
        )
        self.assertEqual(video.to_json()["type"], "Video")
        self.assertEqual(
            video.to_json()["props"]["src"],
            "plugin-resource:///assets/videos/demo.mp4",
        )
        with self.assertRaises(TypeError):
            Image("assets/images/banner.webp")


if __name__ == "__main__":
    unittest.main()
