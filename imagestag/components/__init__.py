"""Reusable NiceGUI components for ImageStag."""

from .filter_designer import FilterDesigner, get_filter_list, get_category_list
from .stream_view import (
    StreamView,
    MouseEvent,
    ImageStream,
    VideoStream,
    CustomStream,
    StreamViewLayer,
)
from .ascii import (
    AsciiRenderer,
    AsciiPlayer,
    AsciiPlayerConfig,
    RenderMode,
    PlaybackState,
)
from .shared import (
    LayerCompositor,
    Viewport,
    KeyEvent,
    MouseButton,
    ResizeEvent,
    StreamViewBase,
)
from .pil import StreamViewPil

__all__ = [
    # FilterDesigner
    'FilterDesigner',
    'get_filter_list',
    'get_category_list',
    # StreamView (NiceGUI-based)
    'StreamView',
    'MouseEvent',
    'ImageStream',
    'VideoStream',
    'CustomStream',
    'StreamViewLayer',
    # ASCII
    'AsciiRenderer',
    'AsciiPlayer',
    'AsciiPlayerConfig',
    'RenderMode',
    'PlaybackState',
    # Shared utilities
    'LayerCompositor',
    'Viewport',
    'KeyEvent',
    'MouseButton',
    'ResizeEvent',
    'StreamViewBase',
    # PIL backend (headless)
    'StreamViewPil',
]

# Optional tkinter backend (built-in but may not be configured)
try:
    from .tkinter import StreamViewTkinter
    __all__.append('StreamViewTkinter')
except ImportError:
    pass

# Optional pygame backend
try:
    from .pygame import StreamViewPygame
    __all__.append('StreamViewPygame')
except ImportError:
    pass

# Optional kivy backend
try:
    from .kivy import StreamViewKivy
    __all__.append('StreamViewKivy')
except ImportError:
    pass
