"""Decoder-based stream classes.

This module defines the DecoderStream abstract base class for streams that
use external decoders (OpenCV, ffmpeg, etc.) to produce frames.
"""

from __future__ import annotations

import threading
from abc import abstractmethod
from typing import TYPE_CHECKING

from .base import ImageStream

if TYPE_CHECKING:
    from imagestag import Image


class DecoderStream(ImageStream):
    """Base class for streams using external decoders.

    Extends ImageStream with decoder-specific functionality:
    - Thread-safe decoder access via lock
    - FPS property for source frame rate
    - Duration and seekability indicators

    Subclasses should use self._lock when accessing the decoder.

    Example:
        class VideoStream(DecoderStream):
            def __init__(self, path: str):
                super().__init__()
                self._path = path
                self._cap = None

            def start(self):
                super().start()
                self._cap = cv2.VideoCapture(self._path)

            def stop(self):
                super().stop()
                with self._lock:
                    if self._cap:
                        self._cap.release()

            @property
            def fps(self) -> float:
                return self._source_fps

            def get_frame(self, timestamp: float) -> tuple[Image | None, int]:
                with self._lock:
                    ret, frame = self._cap.read()
                    if ret:
                        img = Image(frame)
                        return (img, self._store_frame(img))
                return (None, self._frame_index)
    """

    def __init__(self) -> None:
        """Initialize the decoder stream with thread safety primitives."""
        super().__init__()
        self._lock = threading.Lock()

    # -------------------------------------------------------------------------
    # Abstract Properties
    # -------------------------------------------------------------------------

    @property
    @abstractmethod
    def fps(self) -> float:
        """Source frame rate in frames per second.

        :return: Frame rate (e.g., 30.0, 60.0)
        """
        ...

    # -------------------------------------------------------------------------
    # Optional Properties (override in subclasses)
    # -------------------------------------------------------------------------

    @property
    def has_duration(self) -> bool:
        """Whether this stream has a known duration.

        Streams with duration (like video files) are seekable.
        Live streams (like cameras) have no duration.

        :return: True if duration is known
        """
        return False

    @property
    def is_seekable(self) -> bool:
        """Whether this stream supports seeking.

        Seeking is only available for streams with known duration.

        :return: True if seek_to() is supported
        """
        return False

    @property
    def duration(self) -> float:
        """Total stream duration in seconds.

        Only valid if has_duration is True.

        :return: Duration in seconds, or 0.0 if unknown
        """
        return 0.0

    @property
    def current_position(self) -> float:
        """Current playback position in seconds.

        For seekable streams, this is the position in the source.
        For live streams, this returns 0.0.

        :return: Position in seconds
        """
        return 0.0
