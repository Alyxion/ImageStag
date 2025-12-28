"""Tkinter-based StreamView implementation.

This module provides a native tkinter window for displaying StreamView layers.
No additional dependencies required (tkinter is built into Python).
"""

from .stream_view_tkinter import StreamViewTkinter

__all__ = [
    'StreamViewTkinter',
]
