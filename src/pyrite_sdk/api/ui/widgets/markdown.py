from .base import Widget
from ....interfaces.ui import EventType
from ....utils.ui import DataParser
from typing import Any, Optional, Union


MarkdownData = Union[str, list, DataParser, Any]


class MarkdownWidget(Widget):
    def __init__(
        self,
        data: MarkdownData,
        selectable: Optional[bool] = None,
        shrink_wrap: Optional[bool] = None,
        padding: Optional[Any] = None,
        on_tap_link: Optional[EventType] = None,
        code_block_padding: Optional[Any] = None,
        code_block_margin: Optional[Any] = None,
        code_block_decoration: Optional[Any] = None,
        code_block_text_style: Optional[Any] = None,
        code_block_style_not_matched: Optional[Any] = None,
        code_block_language: Optional[str] = None,
        code_block_theme: Optional[str] = None,
        inline_code_text_style: Optional[Any] = None,
        **kwargs: Any
    ) -> None:
        super().__init__(
            "MarkdownWidget",
            data=data,
            selectable=selectable,
            shrinkWrap=shrink_wrap,
            padding=padding,
            onTapLink=on_tap_link,
            codeBlockPadding=code_block_padding,
            codeBlockMargin=code_block_margin,
            codeBlockDecoration=code_block_decoration,
            codeBlockTextStyle=code_block_text_style,
            codeBlockStyleNotMatched=code_block_style_not_matched,
            codeBlockLanguage=code_block_language,
            codeBlockTheme=code_block_theme,
            inlineCodeTextStyle=inline_code_text_style,
            **kwargs
        )


class Markdown(Widget):
    def __init__(
        self,
        data: MarkdownData,
        selectable: Optional[bool] = None,
        shrink_wrap: Optional[bool] = None,
        padding: Optional[Any] = None,
        on_tap_link: Optional[EventType] = None,
        code_block_padding: Optional[Any] = None,
        code_block_margin: Optional[Any] = None,
        code_block_decoration: Optional[Any] = None,
        code_block_text_style: Optional[Any] = None,
        code_block_style_not_matched: Optional[Any] = None,
        code_block_language: Optional[str] = None,
        code_block_theme: Optional[str] = None,
        inline_code_text_style: Optional[Any] = None,
        **kwargs: Any
    ) -> None:
        super().__init__(
            "Markdown",
            data=data,
            selectable=selectable,
            shrinkWrap=shrink_wrap,
            padding=padding,
            onTapLink=on_tap_link,
            codeBlockPadding=code_block_padding,
            codeBlockMargin=code_block_margin,
            codeBlockDecoration=code_block_decoration,
            codeBlockTextStyle=code_block_text_style,
            codeBlockStyleNotMatched=code_block_style_not_matched,
            codeBlockLanguage=code_block_language,
            codeBlockTheme=code_block_theme,
            inlineCodeTextStyle=inline_code_text_style,
            **kwargs
        )


class MarkdownBlock(Widget):
    def __init__(
        self,
        data: MarkdownData,
        selectable: Optional[bool] = None,
        padding: Optional[Any] = None,
        on_tap_link: Optional[EventType] = None,
        code_block_padding: Optional[Any] = None,
        code_block_margin: Optional[Any] = None,
        code_block_decoration: Optional[Any] = None,
        code_block_text_style: Optional[Any] = None,
        code_block_style_not_matched: Optional[Any] = None,
        code_block_language: Optional[str] = None,
        code_block_theme: Optional[str] = None,
        inline_code_text_style: Optional[Any] = None,
        **kwargs: Any
    ) -> None:
        super().__init__(
            "MarkdownBlock",
            data=data,
            selectable=selectable,
            padding=padding,
            onTapLink=on_tap_link,
            codeBlockPadding=code_block_padding,
            codeBlockMargin=code_block_margin,
            codeBlockDecoration=code_block_decoration,
            codeBlockTextStyle=code_block_text_style,
            codeBlockStyleNotMatched=code_block_style_not_matched,
            codeBlockLanguage=code_block_language,
            codeBlockTheme=code_block_theme,
            inlineCodeTextStyle=inline_code_text_style,
            **kwargs
        )
