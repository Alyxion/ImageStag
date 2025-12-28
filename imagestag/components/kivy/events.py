"""Kivy event conversion utilities.

Converts kivy events to unified event dataclasses.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..shared.base_events import KeyEvent, MouseEvent, MouseButton

if TYPE_CHECKING:
    from kivy.core.window import Keyboard


# Kivy key name mapping (keycode to key name)
_KEY_NAME_MAP: dict[int, str] = {
    27: 'escape',
    13: 'enter',
    32: 'space',
    9: 'tab',
    8: 'backspace',
    127: 'delete',
    277: 'insert',
    278: 'home',
    279: 'end',
    280: 'pageup',
    281: 'pagedown',
    273: 'up',
    274: 'down',
    276: 'left',
    275: 'right',
    282: 'f1',
    283: 'f2',
    284: 'f3',
    285: 'f4',
    286: 'f5',
    287: 'f6',
    288: 'f7',
    289: 'f8',
    290: 'f9',
    291: 'f10',
    292: 'f11',
    293: 'f12',
}


def convert_key_event(
    keycode: tuple[int, str],
    text: str | None = None,
    modifiers: list[str] | None = None,
    is_press: bool = True,
) -> KeyEvent:
    """Convert kivy key event data to KeyEvent.

    :param keycode: Tuple of (keycode_int, key_string) from kivy
    :param text: Text character (if printable)
    :param modifiers: List of active modifiers from kivy
    :param is_press: True for key down, False for key up
    :return: KeyEvent
    """
    code, key_str = keycode

    # Map key name
    if code in _KEY_NAME_MAP:
        key_name = _KEY_NAME_MAP[code]
    elif key_str:
        # Use kivy's key string
        key_name = key_str.lower()
    elif text and len(text) == 1:
        key_name = text.lower()
    else:
        key_name = str(code)

    # Convert kivy modifiers to our format
    mod_set = set()
    if modifiers:
        for mod in modifiers:
            if mod in ('shift', 'lshift', 'rshift'):
                mod_set.add('shift')
            elif mod in ('ctrl', 'lctrl', 'rctrl'):
                mod_set.add('ctrl')
            elif mod in ('alt', 'lalt', 'ralt'):
                mod_set.add('alt')
            elif mod in ('meta', 'lmeta', 'rmeta', 'super'):
                mod_set.add('cmd')

    return KeyEvent(
        key=key_name,
        key_code=code,
        modifiers=frozenset(mod_set),
        is_press=is_press,
    )


def convert_mouse_event(
    x: float,
    y: float,
    button: str | None = None,
    event_type: str = "move",
    scroll_delta: tuple[float, float] | None = None,
    modifiers: list[str] | None = None,
    window_height: int = 0,
) -> MouseEvent:
    """Convert kivy mouse/touch event data to MouseEvent.

    :param x: X coordinate (kivy uses bottom-left origin)
    :param y: Y coordinate (kivy uses bottom-left origin)
    :param button: Button name ('left', 'right', 'middle', 'scrollup', 'scrolldown')
    :param event_type: Event type ("move", "press", "release", "scroll")
    :param scroll_delta: Scroll delta (dx, dy) for scroll events
    :param modifiers: List of active modifiers
    :param window_height: Window height for Y-coordinate conversion
    :return: MouseEvent
    """
    # Convert Y coordinate (kivy uses bottom-left origin, we use top-left)
    if window_height > 0:
        y = window_height - y

    # Map button
    mouse_button = None
    if button:
        button_map = {
            'left': MouseButton.LEFT,
            'middle': MouseButton.MIDDLE,
            'right': MouseButton.RIGHT,
            'scrollup': MouseButton.SCROLL_UP,
            'scrolldown': MouseButton.SCROLL_DOWN,
        }
        mouse_button = button_map.get(button)

    # Convert modifiers
    mod_set = set()
    if modifiers:
        for mod in modifiers:
            if 'shift' in mod:
                mod_set.add('shift')
            elif 'ctrl' in mod:
                mod_set.add('ctrl')
            elif 'alt' in mod:
                mod_set.add('alt')
            elif 'meta' in mod or 'super' in mod:
                mod_set.add('cmd')

    delta_x = 0.0
    delta_y = 0.0
    if scroll_delta:
        delta_x, delta_y = scroll_delta

    return MouseEvent(
        x=int(x),
        y=int(y),
        button=mouse_button,
        event_type=event_type,
        delta_x=delta_x,
        delta_y=delta_y,
        modifiers=frozenset(mod_set),
    )
