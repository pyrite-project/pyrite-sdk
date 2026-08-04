"""Runtime environment API — platform, layout mode, and change notifications."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Optional

from ..models.schema import request

if TYPE_CHECKING:
    from pyrite_sdk.core.bridge import Bridge


class Environment:
    """Query and observe the runtime environment.

    Provides:
    - os: Operating system name (windows/macos/linux/android/ios/web)
    - is_desktop_platform: Whether running on a desktop OS
    - layout_mode: Current responsive layout (mobile/tablet/desktop)
    - width/height: Window dimensions
    - locale: UI language tag
    - theme_mode: dark or light

    Layout mode changes when the user resizes the window past breakpoints:
    - mobile: 0-599px
    - tablet: 600-839px
    - desktop: 840px+
    """

    def __init__(self, bridge: Bridge):
        self._bridge = bridge
        self._snapshot: Optional[dict] = None
        self._change_handlers: list[Callable[[dict], None]] = []

    def get(self, callback: Optional[Callable[[dict], None]] = None) -> Optional[dict]:
        """Query the current environment snapshot.

        Returns immediately when called without a callback; invokes the callback
        when called with one. The snapshot contains:
        {
            'os': str,
            'isDesktopPlatform': bool,
            'layoutMode': str,  # 'mobile' | 'tablet' | 'desktop'
            'width': int,
            'height': int,
            'locale': str,
            'themeMode': str,  # 'dark' | 'light'
        }
        """

        def _on_response(payload):
            self._snapshot = payload
            if callback:
                callback(payload)

        self._bridge.push_wait_response(
            request("sdk.env.get", payload={}),
            callback=_on_response,
        )
        return self._snapshot

    def on_change(self, handler: Callable[[dict], None]):
        """Subscribe to environment changes.

        The handler is called whenever the layout mode switches (e.g., from
        desktop to tablet as the user resizes the window). Debounced: rapid
        resize events collapse into a single notification once the window
        settles.
        """
        self._change_handlers.append(handler)

    def _handle_change(self, snapshot: dict):
        """Internal: dispatch ide.env.changed to subscribers."""
        self._snapshot = snapshot
        for handler in self._change_handlers:
            handler(snapshot)

    @property
    def os(self) -> Optional[str]:
        return self._snapshot.get("os") if self._snapshot else None

    @property
    def is_desktop_platform(self) -> Optional[bool]:
        return self._snapshot.get("isDesktopPlatform") if self._snapshot else None

    @property
    def layout_mode(self) -> Optional[str]:
        """Current layout: 'mobile' | 'tablet' | 'desktop'."""
        return self._snapshot.get("layoutMode") if self._snapshot else None

    @property
    def width(self) -> Optional[int]:
        return self._snapshot.get("width") if self._snapshot else None

    @property
    def height(self) -> Optional[int]:
        return self._snapshot.get("height") if self._snapshot else None

    @property
    def locale(self) -> Optional[str]:
        return self._snapshot.get("locale") if self._snapshot else None

    @property
    def theme_mode(self) -> Optional[str]:
        """Current theme: 'dark' | 'light'."""
        return self._snapshot.get("themeMode") if self._snapshot else None
