"""Generate the Material icon metadata used by the native plugin API."""

from __future__ import annotations

import argparse
import hashlib
import keyword
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = (
    REPO_ROOT / "src" / "pyrite_sdk" / "api" / "material_icons.py"
)

BEGIN_MARKER = "// BEGIN GENERATED ICONS"
END_MARKER = "// END GENERATED ICONS"

DECLARATION_START_RE = re.compile(r"(?m)^\s*static const IconData\s+")
MATCH_ARGUMENT_RE = re.compile(r"\bmatchTextDirection\s*:")
DECLARATION_RE = re.compile(
    r"""
    ^\s*static\s+const\s+IconData\s+(?P<name>[A-Za-z_]\w*)\s*=\s*
    IconData\(\s*(?P<codepoint>0x[0-9A-Fa-f]+)\s*,\s*
    fontFamily\s*:\s*['\"](?P<font_family>[^'\"]+)['\"]\s*
    (?:,\s*matchTextDirection\s*:\s*(?P<match_text_direction>true|false)\s*)?
    ,?\s*\);
    """,
    re.MULTILINE | re.DOTALL | re.VERBOSE,
)


@dataclass(frozen=True)
class MaterialIcon:
    name: str
    codepoint: int
    match_text_direction: bool


def _generated_block(source: str, source_path: Path) -> str:
    if source.count(BEGIN_MARKER) != 1 or source.count(END_MARKER) != 1:
        raise ValueError(
            f"{source_path}: expected exactly one {BEGIN_MARKER!r} and {END_MARKER!r}"
        )

    before_end, separator, _ = source.partition(END_MARKER)
    before_begin, begin_separator, block = before_end.partition(BEGIN_MARKER)
    if not separator or not begin_separator or len(before_begin) >= len(before_end):
        raise ValueError(
            f"{source_path}: Material icon generation markers are out of order"
        )
    return block


def parse_material_icons(source_path: Path) -> list[MaterialIcon]:
    source = source_path.read_text(encoding="utf-8")
    block = _generated_block(source, source_path)
    matches = list(DECLARATION_RE.finditer(block))

    declaration_count = len(DECLARATION_START_RE.findall(block))
    if not declaration_count:
        raise ValueError(f"{source_path}: no static IconData declarations found")
    if len(matches) != declaration_count:
        raise ValueError(
            f"{source_path}: parsed {len(matches)} of {declaration_count} "
            "static IconData declarations"
        )

    match_argument_count = len(MATCH_ARGUMENT_RE.findall(block))
    parsed_match_argument_count = sum(
        match["match_text_direction"] is not None for match in matches
    )
    if parsed_match_argument_count != match_argument_count:
        raise ValueError(
            f"{source_path}: parsed {parsed_match_argument_count} of "
            f"{match_argument_count} matchTextDirection arguments"
        )

    font_families = {match["font_family"] for match in matches}
    if font_families != {"MaterialIcons"}:
        raise ValueError(
            f"{source_path}: unsupported Material icon font families: "
            f"{sorted(font_families)!r}"
        )

    icons = [
        MaterialIcon(
            name=match["name"],
            codepoint=int(match["codepoint"], 16),
            match_text_direction=match["match_text_direction"] == "true",
        )
        for match in matches
    ]

    names = [icon.name for icon in icons]
    duplicate_names = sorted(
        name for name, count in Counter(names).items() if count > 1
    )
    if duplicate_names:
        raise ValueError(f"{source_path}: duplicate icon names: {duplicate_names!r}")

    invalid_names = sorted(
        name for name in names if not name.isidentifier() or keyword.iskeyword(name)
    )
    if invalid_names:
        raise ValueError(
            f"{source_path}: icon names are not valid Python identifiers: "
            f"{invalid_names!r}"
        )

    return icons


def render_module(icons: list[MaterialIcon], source_sha256: str) -> str:
    lines = [
        '"""Generated Material icon metadata. Do not edit by hand.',
        "",
        "Regenerate with scripts/generate_material_icons.py using Flutter's",
        "packages/flutter/lib/src/material/icons.dart source file.",
        f"Source SHA-256: {source_sha256}",
        '"""',
        "",
        "from __future__ import annotations",
        "",
        "class _MaterialIconNamespaceHints:",
        '    """Static type hints for every generated Material icon."""',
    ]
    lines.extend(f"    {icon.name}: str" for icon in icons)

    lines.extend(
        [
            "",
            "",
            "MATERIAL_ICON_CODES: dict[str, int] = {",
        ]
    )
    lines.extend(f'    "{icon.name}": 0x{icon.codepoint:X},' for icon in icons)
    lines.append("}")

    rtl_icons = [icon for icon in icons if icon.match_text_direction]
    lines.extend(
        [
            "",
            "",
            "MATERIAL_ICON_MATCH_TEXT_DIRECTION: frozenset[str] = frozenset({",
        ]
    )
    lines.extend(f'    "{icon.name}",' for icon in rtl_icons)
    lines.extend(
        [
            "})",
            "",
            "",
            "__all__ = [",
            '    "MATERIAL_ICON_CODES",',
            '    "MATERIAL_ICON_MATCH_TEXT_DIRECTION",',
            '    "_MaterialIconNamespaceHints",',
            "]",
            "",
        ]
    )
    return "\n".join(lines)


def render_dart_module(icons: list[MaterialIcon], source_sha256: str) -> str:
    lines = [
        "// Generated Material icon metadata. Do not edit by hand.",
        "// Source SHA-256: " + source_sha256,
        "",
        "import 'package:flutter/widgets.dart';",
        "",
        "const materialIcons = <String, IconData>{",
    ]
    for icon in icons:
        entry = (
            f"  '{icon.name}': IconData(0x{icon.codepoint:X}, "
            "fontFamily: 'MaterialIcons'),"
        )
        if not icon.match_text_direction and len(entry) <= 80:
            lines.append(entry)
            continue
        lines.extend(
            [
                f"  '{icon.name}': IconData(",
                f"    0x{icon.codepoint:X},",
                "    fontFamily: 'MaterialIcons',",
            ]
        )
        if icon.match_text_direction:
            lines.append("    matchTextDirection: true,")
        lines.append("  ),")
    lines.extend(
        [
            "};",
            "",
            "final materialIconCodePoints = Map<String, int>.unmodifiable({",
            "  for (final entry in materialIcons.entries) entry.key: entry.value.codePoint,",
            "});",
            "",
            "const materialIconsMatchingTextDirection = <String>{",
        ]
    )
    lines.extend(
        f"  '{icon.name}'," for icon in icons if icon.match_text_direction
    )
    lines.extend(
        [
            "};",
            "",
            "IconData? materialIcon(String name) => materialIcons[name];",
            "",
        ]
    )
    return "\n".join(lines)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate Python metadata from Flutter's material/icons.dart"
    )
    parser.add_argument(
        "source",
        type=Path,
        help="path to packages/flutter/lib/src/material/icons.dart",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"generated module path (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit with status 1 when the generated module is not up to date",
    )
    parser.add_argument(
        "--dart-output",
        type=Path,
        help="optional generated Dart material icon catalog path",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    try:
        source = args.source.resolve()
        icons = parse_material_icons(source)
        source_sha256 = hashlib.sha256(source.read_bytes()).hexdigest()
        generated = render_module(icons, source_sha256)
    except (OSError, ValueError) as error:
        print(error, file=sys.stderr)
        return 2

    output = args.output.resolve()
    dart_output = args.dart_output.resolve() if args.dart_output else None
    if args.check:
        try:
            current = output.read_text(encoding="utf-8")
        except FileNotFoundError:
            current = None
        if current != generated:
            print(f"{output} is not up to date", file=sys.stderr)
            return 1
        if dart_output is not None:
            dart_generated = render_dart_module(icons, source_sha256)
            try:
                dart_current = dart_output.read_text(encoding="utf-8")
            except FileNotFoundError:
                dart_current = None
            if dart_current != dart_generated:
                print(f"{dart_output} is not up to date", file=sys.stderr)
                return 1
        print(f"{output} is up to date ({len(icons)} icons)")
        return 0

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(generated, encoding="utf-8", newline="\n")
    if dart_output is not None:
        dart_output.parent.mkdir(parents=True, exist_ok=True)
        dart_output.write_text(
            render_dart_module(icons, source_sha256),
            encoding="utf-8",
            newline="\n",
        )
    print(f"Generated {output} ({len(icons)} icons)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
