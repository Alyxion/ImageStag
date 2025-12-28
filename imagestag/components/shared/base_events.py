"""Base event dataclasses for native StreamView implementations.

These events provide a unified interface across pygame, tkinter, and kivy backends.
"""

from dataclasses import dataclass
from enum import Enum, auto


class MouseButton(Enum):
    """Mouse button identifiers."""
    LEFT = auto()
    MIDDLE = auto()
    RIGHT = auto()
    SCROLL_UP = auto()
    SCROLL_DOWN = auto()


@dataclass
class KeyEvent:
    """Keyboard event data.

    Attributes:
        key: Key identifier (e.g., 'a', 'space', 'left', 'escape')
        key_code: Raw key code from backend (platform-specific)
        modifiers: Active modifier keys
        is_press: True for key down, False for key up
    """
    key: str
    key_code: int = 0
    modifiers: frozenset[str] = frozenset()
    is_press: bool = True

    @property
    def ctrl(self) -> bool:
        """Whether Ctrl/Command is held."""
        return 'ctrl' in self.modifiers or 'cmd' in self.modifiers

    @property
    def shift(self) -> bool:
        """Whether Shift is held."""
        return 'shift' in self.modifiers

    @property
    def alt(self) -> bool:
        """Whether Alt/Option is held."""
        return 'alt' in self.modifiers


@dataclass
class MouseEvent:
    """Mouse event data.

    Attributes:
        x: X coordinate in pixels (relative to view)
        y: Y coordinate in pixels (relative to view)
        button: Mouse button (for click/release events)
        event_type: Type of mouse event
        delta_x: Scroll delta X (for scroll events)
        delta_y: Scroll delta Y (for scroll events)
        modifiers: Active modifier keys during event
    """
    x: int
    y: int
    button: MouseButton | None = None
    event_type: str = "move"  # "move", "press", "release", "scroll"
    delta_x: float = 0.0
    delta_y: float = 0.0
    modifiers: frozenset[str] = frozenset()

    @property
    def is_click(self) -> bool:
        """Whether this is a button press event."""
        return self.event_type == "press"

    @property
    def is_release(self) -> bool:
        """Whether this is a button release event."""
        return self.event_type == "release"

    @property
    def is_scroll(self) -> bool:
        """Whether this is a scroll event."""
        return self.event_type == "scroll"

    @property
    def left_click(self) -> bool:
        """Whether left button was pressed."""
        return self.is_click and self.button == MouseButton.LEFT

    @property
    def right_click(self) -> bool:
        """Whether right button was pressed."""
        return self.is_click and self.button == MouseButton.RIGHT


@dataclass
class ResizeEvent:
    """Window/view resize event data.

    Attributes:
        width: New width in pixels
        height: New height in pixels
        old_width: Previous width in pixels
        old_height: Previous height in pixels
    """
    width: int
    height: int
    old_width: int = 0
    old_height: int = 0
