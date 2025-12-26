"""StreamView - High-performance video streaming component for NiceGUI.

A custom NiceGUI component for 1080p@60fps video streaming with multi-layer
compositing, per-layer FPS control, and SVG overlays.

Example:
    from imagestag.components.stream_view import StreamView, VideoStream

    video = VideoStream('video.mp4', loop=True)

    view = StreamView(width=1920, height=1080, show_metrics=True)
    view.add_layer(stream=video, fps=60, z_index=0)
    view.start()
"""

from .layers import (
    ImageStream,
    VideoStream,
    CustomStream,
    StreamViewLayer,
)
from .stream_view import (
    StreamView,
    StreamViewMouseEventArguments,
    StreamViewViewportEventArguments,
    Viewport,
)
from .metrics import (
    PythonMetrics,
    LayerMetrics,
    FPSCounter,
    Timer,
)

# Backwards compatibility alias
MouseEvent = StreamViewMouseEventArguments

__all__ = [
    # Main component
    "StreamView",
    # Event arguments
    "StreamViewMouseEventArguments",
    "StreamViewViewportEventArguments",
    "Viewport",
    "MouseEvent",  # Alias for backwards compatibility
    # Stream classes
    "ImageStream",
    "VideoStream",
    "CustomStream",
    # Layer
    "StreamViewLayer",
    # Metrics
    "PythonMetrics",
    "LayerMetrics",
    "FPSCounter",
    "Timer",
]
