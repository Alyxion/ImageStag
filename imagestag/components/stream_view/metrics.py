"""Benchmark metrics for StreamView component.

This module provides classes for tracking performance on both Python and
JavaScript sides of the StreamView component.
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from threading import Lock


@dataclass
class LayerMetrics:
    """Per-layer performance metrics."""

    layer_id: str = ""

    # Frame timing (in milliseconds)
    capture_ms: float = 0.0  # Time to get frame from source
    filter_ms: float = 0.0  # Time in FilterPipeline
    encode_ms: float = 0.0  # Time to encode to JPEG

    # Buffer state
    buffer_depth: int = 0  # Current frames in buffer
    buffer_size: int = 4  # Max buffer size

    # Frame counts
    frames_produced: int = 0
    frames_delivered: int = 0
    frames_dropped: int = 0

    # FPS
    target_fps: float = 60.0
    actual_fps: float = 0.0

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "layer_id": self.layer_id,
            "capture_ms": round(self.capture_ms, 2),
            "filter_ms": round(self.filter_ms, 2),
            "encode_ms": round(self.encode_ms, 2),
            "buffer_depth": self.buffer_depth,
            "buffer_size": self.buffer_size,
            "frames_produced": self.frames_produced,
            "frames_delivered": self.frames_delivered,
            "frames_dropped": self.frames_dropped,
            "target_fps": self.target_fps,
            "actual_fps": round(self.actual_fps, 1),
        }


@dataclass
class PythonMetrics:
    """Aggregate Python-side performance metrics."""

    # Per-layer metrics
    layers: dict[str, LayerMetrics] = field(default_factory=dict)

    # Overall stats
    total_frames_produced: int = 0
    total_frames_delivered: int = 0
    total_frames_dropped: int = 0

    # Timing
    start_time: float = field(default_factory=time.time)
    last_update: float = field(default_factory=time.time)

    def get_layer(self, layer_id: str) -> LayerMetrics:
        """Get or create metrics for a layer."""
        if layer_id not in self.layers:
            self.layers[layer_id] = LayerMetrics(layer_id=layer_id)
        return self.layers[layer_id]

    def update_totals(self) -> None:
        """Update aggregate totals from layer metrics."""
        self.total_frames_produced = sum(m.frames_produced for m in self.layers.values())
        self.total_frames_delivered = sum(m.frames_delivered for m in self.layers.values())
        self.total_frames_dropped = sum(m.frames_dropped for m in self.layers.values())
        self.last_update = time.time()

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        self.update_totals()
        return {
            "layers": {k: v.to_dict() for k, v in self.layers.items()},
            "total_frames_produced": self.total_frames_produced,
            "total_frames_delivered": self.total_frames_delivered,
            "total_frames_dropped": self.total_frames_dropped,
            "uptime_seconds": round(time.time() - self.start_time, 1),
        }


class FPSCounter:
    """Thread-safe FPS counter using a sliding window."""

    def __init__(self, window_size: int = 60) -> None:
        """Initialize FPS counter.

        :param window_size: Number of frame times to track
        """
        self._window_size = window_size
        self._frame_times: deque[float] = deque(maxlen=window_size)
        self._lock = Lock()
        self._last_time: float = 0.0

    def tick(self) -> None:
        """Record a frame tick."""
        current_time = time.perf_counter()
        with self._lock:
            if self._last_time > 0:
                self._frame_times.append(current_time - self._last_time)
            self._last_time = current_time

    @property
    def fps(self) -> float:
        """Calculate current FPS from sliding window."""
        with self._lock:
            if len(self._frame_times) < 2:
                return 0.0
            avg_interval = sum(self._frame_times) / len(self._frame_times)
            if avg_interval <= 0:
                return 0.0
            return 1.0 / avg_interval

    def reset(self) -> None:
        """Reset the counter."""
        with self._lock:
            self._frame_times.clear()
            self._last_time = 0.0


class Timer:
    """Simple context manager for timing code blocks."""

    def __init__(self) -> None:
        self._start: float = 0.0
        self._end: float = 0.0

    def __enter__(self) -> "Timer":
        self._start = time.perf_counter()
        return self

    def __exit__(self, *args) -> None:
        self._end = time.perf_counter()

    @property
    def elapsed_ms(self) -> float:
        """Elapsed time in milliseconds."""
        return (self._end - self._start) * 1000

    @property
    def elapsed_seconds(self) -> float:
        """Elapsed time in seconds."""
        return self._end - self._start


# JavaScript metrics structure (for reference - actual implementation in JS)
JS_METRICS_TEMPLATE = """
// JavaScript-side metrics structure
class JSMetrics {
    constructor() {
        this.decode_ms = 0;        // Time to decode base64
        this.composite_ms = 0;     // Time to composite layers
        this.render_ms = 0;        // Time to draw to canvas
        this.frame_interval_ms = 0; // Time between frames
        this.actual_fps = 0;       // Measured FPS
        this.dropped_frames = 0;   // Missed vsync targets

        // Per-layer metrics
        this.layers = new Map();   // layer_id -> {decode_ms, draw_ms, fps}
    }
}
"""
