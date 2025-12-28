"""PIL-based headless StreamView implementation.

Provides a headless StreamView for rendering layer compositions to PIL images.
No display or GUI framework required.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import TYPE_CHECKING, Iterator

from ..shared.stream_view_base import StreamViewBase

if TYPE_CHECKING:
    from PIL import Image as PILImage
    from imagestag import Image


@dataclass
class StreamViewPil(StreamViewBase):
    """Headless StreamView that renders to PIL images.

    Renders layer compositions to PIL images without requiring a display.
    Useful for batch processing, testing, server-side rendering, and CLI tools.

    Example (by timestamp):
        from imagestag.components.pil import StreamViewPil
        from imagestag.streams import VideoStream

        view = StreamViewPil(1280, 720)
        view.add_layer(stream=VideoStream('video.mp4'))
        view.start()

        # Render at 5 seconds
        pil_img = view.render(timestamp=5.0)
        pil_img.save('frame_at_5s.png')

        view.stop()

    Example (by frame index):
        from imagestag.components.pil import StreamViewPil
        from imagestag.streams import VideoStream

        view = StreamViewPil(1280, 720)
        view.add_layer(stream=VideoStream('video.mp4'))
        view.start()

        # Render frame 150
        pil_img = view.render_by_index(150)
        pil_img.save('frame_150.png')

        # Iterate all frames
        for i, frame in enumerate(view.render_all_frames()):
            frame.save(f'frame_{i:04d}.png')

        view.stop()

    Attributes:
        width: Output width in pixels
        height: Output height in pixels
        title: Not used (headless), but kept for API compatibility
        target_fps: Target FPS for layers (default: 60)
    """

    def render(self, timestamp: float = 0.0) -> "PILImage":
        """Render the composition at a given timestamp.

        :param timestamp: Playback timestamp in seconds
        :return: PIL Image of the rendered composition
        """
        composite = self._compositor.composite_rgb(timestamp)
        return composite.to_pil()

    def render_to_image(self, timestamp: float = 0.0) -> "Image":
        """Render the composition at a given timestamp as an imagestag Image.

        :param timestamp: Playback timestamp in seconds
        :return: Image of the rendered composition
        """
        return self._compositor.composite_rgb(timestamp)

    def render_by_index(self, frame_index: int) -> "PILImage":
        """Render the composition at a specific frame index.

        Seeks video layers to the specified frame index before compositing.
        For layers without frame-based seeking, uses the timestamp equivalent.

        :param frame_index: Frame number (0-based)
        :return: PIL Image of the rendered composition
        """
        # Seek video layers to the frame index
        for layer in self._layers.values():
            stream = layer.stream
            if stream is not None and hasattr(stream, 'get_frame_by_index'):
                # Get the frame by index (this updates the stream's internal state)
                stream.get_frame_by_index(frame_index)

        # Now composite - the compositor will get the current frames from layers
        # We need to compute timestamp for layers that don't support index access
        primary_layer = self._get_primary_video_layer()
        if primary_layer and primary_layer.stream:
            fps = getattr(primary_layer.stream, 'fps', 30.0)
            timestamp = frame_index / fps
        else:
            timestamp = 0.0

        composite = self._compositor.composite_rgb(timestamp)
        return composite.to_pil()

    def render_by_index_to_image(self, frame_index: int) -> "Image":
        """Render the composition at a specific frame index as an imagestag Image.

        :param frame_index: Frame number (0-based)
        :return: Image of the rendered composition
        """
        # Same logic as render_by_index but return Image
        for layer in self._layers.values():
            stream = layer.stream
            if stream is not None and hasattr(stream, 'get_frame_by_index'):
                stream.get_frame_by_index(frame_index)

        primary_layer = self._get_primary_video_layer()
        if primary_layer and primary_layer.stream:
            fps = getattr(primary_layer.stream, 'fps', 30.0)
            timestamp = frame_index / fps
        else:
            timestamp = 0.0

        return self._compositor.composite_rgb(timestamp)

    def render_all_frames(self) -> Iterator["PILImage"]:
        """Iterate all frames from video sources.

        Yields frames from index 0 to frame_count-1. Only works if
        there is a video layer with a known frame count.

        :return: Iterator of PIL Images
        :raises ValueError: If no video layer with known frame count exists
        """
        count = self.frame_count
        if count == 0:
            raise ValueError(
                "Cannot iterate frames: no video layer with known frame count. "
                "Use render(timestamp) for infinite/unknown-length streams."
            )

        for i in range(count):
            yield self.render_by_index(i)

    def save_frame(self, path: str, timestamp: float = 0.0, **kwargs) -> None:
        """Save a single frame to a file.

        :param path: Output file path (extension determines format)
        :param timestamp: Playback timestamp in seconds
        :param kwargs: Additional arguments passed to PIL Image.save()
        """
        pil_img = self.render(timestamp)
        pil_img.save(path, **kwargs)

    def save_frame_by_index(self, path: str, frame_index: int, **kwargs) -> None:
        """Save a specific frame by index to a file.

        :param path: Output file path (extension determines format)
        :param frame_index: Frame number (0-based)
        :param kwargs: Additional arguments passed to PIL Image.save()
        """
        pil_img = self.render_by_index(frame_index)
        pil_img.save(path, **kwargs)

    @property
    def frame_count(self) -> int:
        """Get the total frame count from the primary video layer.

        Returns the frame count of the first layer with a known frame count,
        or 0 if no such layer exists.
        """
        for layer in self._layers.values():
            stream = layer.stream
            if stream is not None:
                count = getattr(stream, 'frame_count', 0)
                if count > 0:
                    return count
        return 0

    @property
    def duration(self) -> float:
        """Get the duration of the primary video layer in seconds.

        Returns the duration of the first layer with a known duration,
        or 0.0 if no such layer exists.
        """
        for layer in self._layers.values():
            stream = layer.stream
            if stream is not None:
                duration = getattr(stream, 'duration', 0.0)
                if duration > 0:
                    return duration
        return 0.0

    @property
    def fps(self) -> float:
        """Get the FPS of the primary video layer.

        Returns the FPS of the first video layer, or 30.0 as default.
        """
        layer = self._get_primary_video_layer()
        if layer and layer.stream:
            return getattr(layer.stream, 'fps', 30.0)
        return 30.0

    def _get_primary_video_layer(self):
        """Get the first layer with a video stream.

        :return: StreamViewLayer or None
        """
        for layer in self._layers.values():
            stream = layer.stream
            if stream is not None and hasattr(stream, 'frame_count'):
                return layer
        return None

    # -------------------------------------------------------------------------
    # Abstract Method Implementations (required by StreamViewBase)
    # -------------------------------------------------------------------------

    def run(self) -> None:
        """No-op for headless mode.

        StreamViewPil does not have a main loop. Use render() methods
        to get individual frames, or render_all_frames() to iterate.
        """
        self.start()

    def run_async(self) -> threading.Thread:
        """No-op for headless mode.

        :return: Dummy thread (not started)
        """
        # For headless mode, just start the layers and return a dummy thread
        self.start()
        return threading.Thread()
