"""Tkinter event conversion utilities.

Converts tkinter events to unified event dataclasses.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..shared.base_events import KeyEvent, MouseEvent, MouseButton

if TYPE_CHECKING:
    import tkinter as tk


# Tkinter key symbol mapping
_KEY_NAME_MAP: dict[str, str] = {
    'Escape': 'escape',
    'Return': 'enter',
    'space': 'space',
    'Tab': 'tab',
    'BackSpace': 'backspace',
    'Delete': 'delete',
    'Insert': 'insert',
    'Home': 'home',
    'End': 'end',
    'Prior': 'pageup',
    'Next': 'pagedown',
    'Up': 'up',
    'Down': 'down',
    'Left': 'left',
    'Right': 'right',
    'F1': 'f1',
    'F2': 'f2',
    'F3': 'f3',
    'F4': 'f4',
    'F5': 'f5',
    'F6': 'f6',
    'F7': 'f7',
    'F8': 'f8',
    'F9': 'f9',
    'F10': 'f10',
    'F11': 'f11',
    'F12': 'f12',
    'plus': '+',
    'minus': '-',
    'equal': '=',
    'Shift_L': 'shift',
    'Shift_R': 'shift',
    'Control_L': 'ctrl',
    'Control_R': 'ctrl',
    'Alt_L': 'alt',
    'Alt_R': 'alt',
    'Meta_L': 'cmd',
    'Meta_R': 'cmd',
    'Super_L': 'cmd',
    'Super_R': 'cmd',
}


def get_modifiers(event: "tk.Event") -> frozenset[str]:
    """Get modifier keys from tkinter event state.

    :param event: Tkinter event with state attribute
    :return: Frozenset of modifier names
    """
    result = set()
    state = getattr(event, 'state', 0)

    # Tkinter modifier masks
    if state & 0x0001:  # Shift
        result.add('shift')
    if state & 0x0004:  # Control
        result.add('ctrl')
    if state & 0x0008:  # Alt (Mod1)
        result.add('alt')
    if state & 0x0080:  # Meta (Command on Mac)
        result.add('cmd')

    return frozenset(result)


def convert_key_event(event: "tk.Event", is_press: bool = True) -> KeyEvent:
    """Convert a tkinter key event to KeyEvent.

    :param event: tkinter KeyPress or KeyRelease event
    :param is_press: True for key down, False for key up
    :return: KeyEvent
    """
    keysym = event.keysym

    # Map key name
    if keysym in _KEY_NAME_MAP:
        key_name = _KEY_NAME_MAP[keysym]
    elif len(keysym) == 1:
        key_name = keysym.lower()
    else:
        key_name = keysym.lower()

    return KeyEvent(
        key=key_name,
        key_code=event.keycode,
        modifiers=get_modifiers(event),
        is_press=is_press,
    )


def convert_mouse_event(
    event: "tk.Event",
    event_type: str = "move",
    button: MouseButton | None = None,
) -> MouseEvent:
    """Convert a tkinter mouse event to MouseEvent.

    :param event: tkinter Motion, ButtonPress, ButtonRelease, or MouseWheel event
    :param event_type: Event type ("move", "press", "release", "scroll")
    :param button: Mouse button for click events
    :return: MouseEvent
    """
    delta_x = 0.0
    delta_y = 0.0

    if event_type == "scroll":
        # On macOS, delta is in event.delta
        # On Windows/Linux, it's also in event.delta but scaled differently
        if hasattr(event, 'delta'):
            delta_y = event.delta / 120.0  # Normalize to approximately 1.0 per notch

    return MouseEvent(
        x=event.x,
        y=event.y,
        button=button,
        event_type=event_type,
        delta_x=delta_x,
        delta_y=delta_y,
        modifiers=get_modifiers(event),
    )


def button_num_to_button(num: int) -> MouseButton | None:
    """Convert tkinter button number to MouseButton.

    :param num: Button number (1=left, 2=middle, 3=right, 4/5=scroll)
    :return: MouseButton or None
    """
    button_map = {
        1: MouseButton.LEFT,
        2: MouseButton.MIDDLE,
        3: MouseButton.RIGHT,
        4: MouseButton.SCROLL_UP,
        5: MouseButton.SCROLL_DOWN,
    }
    return button_map.get(num)
