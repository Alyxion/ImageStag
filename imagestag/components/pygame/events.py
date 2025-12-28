"""Pygame event conversion utilities.

Converts pygame events to unified event dataclasses.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..shared.base_events import KeyEvent, MouseEvent, MouseButton

if TYPE_CHECKING:
    import pygame


# Pygame key name mapping
_KEY_NAME_MAP: dict[int, str] = {}


def _init_key_map() -> None:
    """Initialize key mapping from pygame constants."""
    global _KEY_NAME_MAP
    if _KEY_NAME_MAP:
        return

    try:
        import pygame
    except ImportError:
        return

    # Common key mappings
    _KEY_NAME_MAP = {
        pygame.K_ESCAPE: 'escape',
        pygame.K_RETURN: 'enter',
        pygame.K_SPACE: 'space',
        pygame.K_TAB: 'tab',
        pygame.K_BACKSPACE: 'backspace',
        pygame.K_DELETE: 'delete',
        pygame.K_INSERT: 'insert',
        pygame.K_HOME: 'home',
        pygame.K_END: 'end',
        pygame.K_PAGEUP: 'pageup',
        pygame.K_PAGEDOWN: 'pagedown',
        pygame.K_UP: 'up',
        pygame.K_DOWN: 'down',
        pygame.K_LEFT: 'left',
        pygame.K_RIGHT: 'right',
        pygame.K_F1: 'f1',
        pygame.K_F2: 'f2',
        pygame.K_F3: 'f3',
        pygame.K_F4: 'f4',
        pygame.K_F5: 'f5',
        pygame.K_F6: 'f6',
        pygame.K_F7: 'f7',
        pygame.K_F8: 'f8',
        pygame.K_F9: 'f9',
        pygame.K_F10: 'f10',
        pygame.K_F11: 'f11',
        pygame.K_F12: 'f12',
        pygame.K_PLUS: '+',
        pygame.K_MINUS: '-',
        pygame.K_EQUALS: '=',
        pygame.K_LSHIFT: 'shift',
        pygame.K_RSHIFT: 'shift',
        pygame.K_LCTRL: 'ctrl',
        pygame.K_RCTRL: 'ctrl',
        pygame.K_LALT: 'alt',
        pygame.K_RALT: 'alt',
        pygame.K_LGUI: 'cmd',
        pygame.K_RGUI: 'cmd',
    }


def get_modifiers() -> frozenset[str]:
    """Get currently active modifier keys.

    :return: Frozenset of modifier names ('shift', 'ctrl', 'alt', 'cmd')
    """
    try:
        import pygame
    except ImportError:
        return frozenset()

    try:
        mods = pygame.key.get_mods()
    except pygame.error:
        # Video system not initialized
        return frozenset()

    result = set()

    if mods & pygame.KMOD_SHIFT:
        result.add('shift')
    if mods & pygame.KMOD_CTRL:
        result.add('ctrl')
    if mods & pygame.KMOD_ALT:
        result.add('alt')
    if mods & (pygame.KMOD_GUI | pygame.KMOD_META):
        result.add('cmd')

    return frozenset(result)


def convert_key_event(event: "pygame.event.Event") -> KeyEvent | None:
    """Convert a pygame key event to KeyEvent.

    :param event: pygame KEYDOWN or KEYUP event
    :return: KeyEvent or None if not a key event
    """
    try:
        import pygame
    except ImportError:
        return None

    _init_key_map()

    if event.type not in (pygame.KEYDOWN, pygame.KEYUP):
        return None

    is_press = event.type == pygame.KEYDOWN

    # Get key name
    key_code = event.key
    if key_code in _KEY_NAME_MAP:
        key_name = _KEY_NAME_MAP[key_code]
    elif 32 <= key_code <= 126:
        # Printable ASCII
        key_name = chr(key_code).lower()
    else:
        key_name = pygame.key.name(key_code)

    return KeyEvent(
        key=key_name,
        key_code=key_code,
        modifiers=get_modifiers(),
        is_press=is_press,
    )


def convert_mouse_event(event: "pygame.event.Event") -> MouseEvent | None:
    """Convert a pygame mouse event to MouseEvent.

    :param event: pygame MOUSEMOTION, MOUSEBUTTONDOWN, MOUSEBUTTONUP, or MOUSEWHEEL
    :return: MouseEvent or None if not a mouse event
    """
    try:
        import pygame
    except ImportError:
        return None

    if event.type == pygame.MOUSEMOTION:
        return MouseEvent(
            x=event.pos[0],
            y=event.pos[1],
            event_type="move",
            modifiers=get_modifiers(),
        )

    elif event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
        # Map pygame button numbers
        button_map = {
            1: MouseButton.LEFT,
            2: MouseButton.MIDDLE,
            3: MouseButton.RIGHT,
            4: MouseButton.SCROLL_UP,
            5: MouseButton.SCROLL_DOWN,
        }
        button = button_map.get(event.button)

        event_type = "press" if event.type == pygame.MOUSEBUTTONDOWN else "release"

        return MouseEvent(
            x=event.pos[0],
            y=event.pos[1],
            button=button,
            event_type=event_type,
            modifiers=get_modifiers(),
        )

    elif event.type == pygame.MOUSEWHEEL:
        # Get current mouse position for scroll events
        pos = pygame.mouse.get_pos()
        return MouseEvent(
            x=pos[0],
            y=pos[1],
            event_type="scroll",
            delta_x=event.x,
            delta_y=event.y,
            modifiers=get_modifiers(),
        )

    return None
