"""Frame timing and metadata tracking for StreamView.

Tracks timing information through the entire pipeline:
- Capture: When frame was obtained from source
- Filters: Time spent in each filter of the pipeline
- Encode: Time to encode to JPEG/PNG
- Send: When sent to browser
- Receive: When browser received (JS timestamp)
- Decode: When browser decoded the image
- Render: When drawn to canvas
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


@dataclass
class FilterTiming:
    """Timing for a single filter in the pipeline."""

    name: str
    start_ms: float
    end_ms: float

    @property
    def duration_ms(self) -> float:
        return self.end_ms - self.start_ms

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "start_ms": self.start_ms,
            "end_ms": self.end_ms,
            "duration_ms": self.duration_ms,
        }


@dataclass
class FrameMetadata:
    """Timing metadata for a single frame through the pipeline.

    All timestamps are in milliseconds from a common reference point.
    Python uses time.perf_counter() * 1000, JS uses performance.now().
    """

    # Unique frame identifier
    frame_id: int = 0

    # Python-side timestamps (ms)
    capture_time: float = 0.0  # When frame was captured from source
    filter_timings: list[FilterTiming] = field(default_factory=list)
    encode_start: float = 0.0
    encode_end: float = 0.0
    send_time: float = 0.0  # When sent via WebSocket

    # Will be filled by JS and sent back or calculated
    # These use JS performance.now() timestamps
    receive_time: float = 0.0  # When browser received
    decode_start: float = 0.0  # When started decoding image
    decode_end: float = 0.0  # When image.onload fired
    render_time: float = 0.0  # When drawn to canvas

    # Reference timestamp for synchronization
    # Set once at start to correlate Python and JS clocks
    python_ref_time: float = 0.0
    js_ref_time: float = 0.0

    # Navigation thumbnail (base64 JPEG of full frame, used when zoomed)
    nav_thumbnail: str | None = None

    # Anchor position for overscan layers (display coordinates where content is centered)
    # Used to offset the image when display position changes before new frame arrives
    anchor_x: int | None = None
    anchor_y: int | None = None

    # Frame size in bytes (for bandwidth tracking)
    frame_bytes: int = 0

    # Buffer occupancy (for queue monitoring)
    buffer_length: int = 0  # Current number of frames in buffer when this frame was added
    buffer_capacity: int = 0  # Max buffer size

    # Frame dimensions (for resolution tracking)
    frame_width: int = 0
    frame_height: int = 0

    def add_filter_timing(self, name: str, start_ms: float, end_ms: float) -> None:
        """Add timing for a filter stage."""
        self.filter_timings.append(FilterTiming(name, start_ms, end_ms))

    @property
    def encode_duration_ms(self) -> float:
        return self.encode_end - self.encode_start

    @property
    def total_filter_ms(self) -> float:
        return sum(f.duration_ms for f in self.filter_timings)

    @property
    def python_processing_ms(self) -> float:
        """Total time in Python (capture to send)."""
        if self.send_time > 0 and self.capture_time > 0:
            return self.send_time - self.capture_time
        return 0.0

    @property
    def network_ms(self) -> float:
        """Estimated network latency (requires clock sync)."""
        # This is approximate since Python and JS clocks differ
        return 0.0  # Will be calculated with clock sync

    @property
    def js_processing_ms(self) -> float:
        """Total time in browser (receive to render)."""
        if self.render_time > 0 and self.receive_time > 0:
            return self.render_time - self.receive_time
        return 0.0

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        result = {
            "frame_id": self.frame_id,
            "capture_time": self.capture_time,
            "filter_timings": [f.to_dict() for f in self.filter_timings],
            "encode_start": self.encode_start,
            "encode_end": self.encode_end,
            "encode_duration_ms": self.encode_duration_ms,
            "send_time": self.send_time,
            "total_filter_ms": self.total_filter_ms,
            "python_processing_ms": self.python_processing_ms,
        }
        # Only include nav_thumbnail when present (saves bandwidth when not zoomed)
        if self.nav_thumbnail:
            result["nav_thumbnail"] = self.nav_thumbnail
        # Include anchor position for overscan layers
        if self.anchor_x is not None and self.anchor_y is not None:
            result["anchor_x"] = self.anchor_x
            result["anchor_y"] = self.anchor_y
        # Include frame size for bandwidth tracking
        if self.frame_bytes > 0:
            result["frame_bytes"] = self.frame_bytes
        # Include buffer occupancy for queue monitoring
        if self.buffer_capacity > 0:
            result["buffer_length"] = self.buffer_length
            result["buffer_capacity"] = self.buffer_capacity
        # Include frame dimensions for resolution tracking
        if self.frame_width > 0 and self.frame_height > 0:
            result["frame_width"] = self.frame_width
            result["frame_height"] = self.frame_height
        return result

    @staticmethod
    def now_ms() -> float:
        """Get current time in milliseconds."""
        return time.perf_counter() * 1000


# Global frame counter for unique IDs
_frame_counter = 0


def new_frame_metadata() -> FrameMetadata:
    """Create a new FrameMetadata with unique ID and capture timestamp."""
    global _frame_counter
    _frame_counter += 1
    return FrameMetadata(
        frame_id=_frame_counter,
        capture_time=FrameMetadata.now_ms(),
    )
