"""ImageStag streams package.

This package provides stream classes for frame sources:

- ImageStream: Abstract base class for all frame sources
- DecoderStream: Base for streams using external decoders (OpenCV)
- VideoStream: Video file playback with seeking support
- CameraStream: Live camera/webcam capture
- GeneratorStream: On-demand frame generation via callback

All streams support:
- Frame index tracking for efficient new-frame detection
- Pause/resume functionality
- Frame sharing via last_frame property
- Subscriber notifications for dependent streams
- on_frame callbacks for synchronous processing

Example:
    from imagestag.streams import VideoStream, CameraStream, GeneratorStream

    # Video playback
    video = VideoStream('movie.mp4', loop=True)
    video.start()

    # Camera capture
    camera = CameraStream(0)
    camera.start()

    # Procedural generation
    def render(t: float) -> Image:
        return generate_pattern(t)

    gen = GeneratorStream(render)
    gen.start()

    # Efficient frame consumption
    last_index = -1
    while stream.is_running:
        frame, index = stream.get_frame(stream.elapsed_time)
        if index != last_index:
            process(frame)
            last_index = index
"""

from .base import ImageStream, FrameResult
from .decoder import DecoderStream
from .video import VideoStream
from .camera import CameraStream
from .generator import GeneratorStream, CustomStream
from .multi_output import MultiOutputStream, RenderContext, LayerOutput, LayerConfig

__all__ = [
    "ImageStream",
    "DecoderStream",
    "VideoStream",
    "CameraStream",
    "GeneratorStream",
    "CustomStream",  # Backwards compatibility alias
    "FrameResult",
    # Multi-output
    "MultiOutputStream",
    "RenderContext",
    "LayerOutput",
    "LayerConfig",
]
