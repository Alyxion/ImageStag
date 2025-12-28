"""Kivy-based StreamView implementation.

This module provides a native kivy window for displaying StreamView layers.
Requires kivy to be installed: poetry install -E kivy
"""

from .stream_view_kivy import StreamViewKivy

__all__ = [
    'StreamViewKivy',
]
