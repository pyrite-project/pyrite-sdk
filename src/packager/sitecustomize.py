sitecustomize_py = """
# A site customization that can be used to trick pip into installing packages cross-platform.
# The folder containing this file should be on your PYTHONPATH pip is invoked.

custom_system = "{platform}"
custom_platform = "{tag}"
custom_mac_ver = "{mac_ver}"

import collections
import platform
import sysconfig

if custom_system:
    platform.system = lambda: custom_system

if custom_platform:
    sysconfig.get_platform = lambda: custom_platform

if custom_mac_ver:
  orig_mac_ver = platform.mac_ver

  def custom_mac_ver_impl():
      orig = orig_mac_ver()
      return orig[0], orig[1], custom_mac_ver

  platform.mac_ver = custom_mac_ver_impl

if custom_system == "Android":
  AndroidVer = collections.namedtuple(
      "AndroidVer",
      ["release", "api_level", "manufacturer", "model", "device", "is_emulator"]
  )

  tag_parts = custom_platform.split("-")
  try:
      api_level = int(tag_parts[1])
  except (IndexError, ValueError):
      api_level = 24

  def custom_android_ver():
      return AndroidVer("", api_level, "", "", "", False)

  platform.android_ver = custom_android_ver

orig_platform_version = platform.version
platform.version = lambda: orig_platform_version() + ";embedded"
"""
