"""Pygame-based StreamView implementation.

This module provides a native pygame window for displaying StreamView layers.
Requires pygame to be installed: poetry install -E pygame
"""

from .stream_view_pygame import StreamViewPygame

__all__ = [
    'StreamViewPygame',
]
