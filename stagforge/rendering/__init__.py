"""Cross-platform rendering module.

This module provides Python implementations of layer rendering that
produce pixel-identical output to the JavaScript implementations.

CRITICAL: Any changes to rendering algorithms MUST be synchronized
between JS and Python, and verified by pixel diff tests.
"""

from .text import render_text_layer
from .vector import render_vector_layer
from .svg_layer import render_svg_layer
from .document import render_document, render_layer

__all__ = [
    "render_text_layer",
    "render_vector_layer",
    "render_svg_layer",
    "render_document",
    "render_layer",
]
