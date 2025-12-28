"""PIL-based headless StreamView implementation.

Provides StreamViewPil for rendering layer compositions to PIL images
without requiring a display or GUI framework.
"""

from .stream_view_pil import StreamViewPil

__all__ = ['StreamViewPil']
