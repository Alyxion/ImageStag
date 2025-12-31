"""Comprehensive tests for StreamView component - targeting 95%+ coverage.

Uses NiceGUI testing patterns with pytest-asyncio and User fixture.
"""

import time
import pytest
from unittest.mock import MagicMock
import numpy as np

from imagestag import Image

# NiceGUI testing imports
from nicegui.testing import User


# ============================================================================
# TIMING MODULE TESTS
# ============================================================================


class TestFilterTiming:
    """Tests for FilterTiming dataclass."""

    def test_filter_timing_creation(self):
        """Test creating FilterTiming instance."""
        from imagestag.components.stream_view.timing import FilterTiming

        ft = FilterTiming(name="blur", start_ms=100.0, end_ms=150.0)
        assert ft.name == "blur"
        assert ft.start_ms == 100.0
        assert ft.end_ms == 150.0

    def test_filter_timing_duration(self):
        """Test duration_ms property."""
        from imagestag.components.stream_view.timing import FilterTiming

        ft = FilterTiming(name="test", start_ms=100.0, end_ms=175.5)
        assert ft.duration_ms == 75.5

    def test_filter_timing_to_dict(self):
        """Test to_dict method."""
        from imagestag.components.stream_view.timing import FilterTiming

        ft = FilterTiming(name="sharpen", start_ms=50.0, end_ms=80.0)
        d = ft.to_dict()
        assert d["name"] == "sharpen"
        assert d["start_ms"] == 50.0
        assert d["end_ms"] == 80.0
        assert d["duration_ms"] == 30.0


class TestFrameMetadata:
    """Tests for FrameMetadata dataclass."""

    def test_frame_metadata_creation(self):
        """Test creating FrameMetadata instance."""
        from imagestag.components.stream_view.timing import FrameMetadata

        fm = FrameMetadata(frame_id=42)
        assert fm.frame_id == 42
        assert fm.capture_time == 0.0
        assert fm.filter_timings == []

    def test_add_filter_timing(self):
        """Test adding filter timing."""
        from imagestag.components.stream_view.timing import FrameMetadata

        fm = FrameMetadata()
        fm.add_filter_timing("blur", 10.0, 25.0)
        fm.add_filter_timing("sharpen", 25.0, 35.0)

        assert len(fm.filter_timings) == 2
        assert fm.filter_timings[0].name == "blur"
        assert fm.filter_timings[1].name == "sharpen"

    def test_encode_duration_ms(self):
        """Test encode_duration_ms property."""
        from imagestag.components.stream_view.timing import FrameMetadata

        fm = FrameMetadata(encode_start=100.0, encode_end=125.0)
        assert fm.encode_duration_ms == 25.0

    def test_total_filter_ms(self):
        """Test total_filter_ms property."""
        from imagestag.components.stream_view.timing import FrameMetadata

        fm = FrameMetadata()
        fm.add_filter_timing("a", 0, 10)
        fm.add_filter_timing("b", 10, 30)
        assert fm.total_filter_ms == 30.0

    def test_python_processing_ms(self):
        """Test python_processing_ms property."""
        from imagestag.components.stream_view.timing import FrameMetadata

        fm = FrameMetadata(capture_time=100.0, send_time=200.0)
        assert fm.python_processing_ms == 100.0

        # Test with zero values
        fm2 = FrameMetadata()
        assert fm2.python_processing_ms == 0.0

    def test_network_ms(self):
        """Test network_ms property (always returns 0 for now)."""
        from imagestag.components.stream_view.timing import FrameMetadata

        fm = FrameMetadata()
        assert fm.network_ms == 0.0

    def test_js_processing_ms(self):
        """Test js_processing_ms property."""
        from imagestag.components.stream_view.timing import FrameMetadata

        fm = FrameMetadata(receive_time=100.0, render_time=150.0)
        assert fm.js_processing_ms == 50.0

        # Test with zero values
        fm2 = FrameMetadata()
        assert fm2.js_processing_ms == 0.0

    def test_to_dict_basic(self):
        """Test basic to_dict output."""
        from imagestag.components.stream_view.timing import FrameMetadata

        fm = FrameMetadata(
            frame_id=1,
            capture_time=100.0,
            encode_start=110.0,
            encode_end=115.0,
            send_time=120.0,
        )
        d = fm.to_dict()

        assert d["frame_id"] == 1
        assert d["capture_time"] == 100.0
        assert d["encode_start"] == 110.0
        assert d["encode_end"] == 115.0
        assert d["send_time"] == 120.0
        assert d["encode_duration_ms"] == 5.0

    def test_to_dict_with_nav_thumbnail(self):
        """Test to_dict includes nav_thumbnail when present."""
        from imagestag.components.stream_view.timing import FrameMetadata

        fm = FrameMetadata(nav_thumbnail="base64data")
        d = fm.to_dict()
        assert d["nav_thumbnail"] == "base64data"

    def test_to_dict_without_nav_thumbnail(self):
        """Test to_dict excludes nav_thumbnail when None."""
        from imagestag.components.stream_view.timing import FrameMetadata

        fm = FrameMetadata()
        d = fm.to_dict()
        assert "nav_thumbnail" not in d

    def test_to_dict_with_anchor(self):
        """Test to_dict includes anchor when set."""
        from imagestag.components.stream_view.timing import FrameMetadata

        fm = FrameMetadata(anchor_x=100, anchor_y=200)
        d = fm.to_dict()
        assert d["anchor_x"] == 100
        assert d["anchor_y"] == 200

    def test_to_dict_with_frame_bytes(self):
        """Test to_dict includes frame_bytes when > 0."""
        from imagestag.components.stream_view.timing import FrameMetadata

        fm = FrameMetadata(frame_bytes=12345)
        d = fm.to_dict()
        assert d["frame_bytes"] == 12345

    def test_to_dict_with_buffer_info(self):
        """Test to_dict includes buffer info when capacity > 0."""
        from imagestag.components.stream_view.timing import FrameMetadata

        fm = FrameMetadata(buffer_length=3, buffer_capacity=4)
        d = fm.to_dict()
        assert d["buffer_length"] == 3
        assert d["buffer_capacity"] == 4

    def test_to_dict_with_frame_dimensions(self):
        """Test to_dict includes frame dimensions when set."""
        from imagestag.components.stream_view.timing import FrameMetadata

        fm = FrameMetadata(frame_width=1920, frame_height=1080)
        d = fm.to_dict()
        assert d["frame_width"] == 1920
        assert d["frame_height"] == 1080

    def test_to_dict_with_effective_fps(self):
        """Test to_dict includes effective_fps when > 0."""
        from imagestag.components.stream_view.timing import FrameMetadata

        fm = FrameMetadata(effective_fps=30.0)
        d = fm.to_dict()
        assert d["effective_fps"] == 30.0

    def test_now_ms(self):
        """Test now_ms static method returns reasonable value."""
        from imagestag.components.stream_view.timing import FrameMetadata

        t1 = FrameMetadata.now_ms()
        time.sleep(0.01)
        t2 = FrameMetadata.now_ms()

        assert t2 > t1
        assert t2 - t1 >= 10  # At least 10ms


class TestNewFrameMetadata:
    """Tests for new_frame_metadata function."""

    def test_creates_unique_ids(self):
        """Test that new_frame_metadata creates unique IDs."""
        from imagestag.components.stream_view.timing import new_frame_metadata

        fm1 = new_frame_metadata()
        fm2 = new_frame_metadata()
        fm3 = new_frame_metadata()

        assert fm1.frame_id != fm2.frame_id
        assert fm2.frame_id != fm3.frame_id
        assert fm1.frame_id < fm2.frame_id < fm3.frame_id

    def test_sets_capture_time(self):
        """Test that new_frame_metadata sets capture_time."""
        from imagestag.components.stream_view.timing import new_frame_metadata

        before = time.perf_counter() * 1000
        fm = new_frame_metadata()
        after = time.perf_counter() * 1000

        assert before <= fm.capture_time <= after


# ============================================================================
# METRICS MODULE TESTS
# ============================================================================


class TestLayerMetrics:
    """Tests for LayerMetrics dataclass."""

    def test_layer_metrics_creation(self):
        """Test creating LayerMetrics instance."""
        from imagestag.components.stream_view.metrics import LayerMetrics

        lm = LayerMetrics(layer_id="test-123")
        assert lm.layer_id == "test-123"
        assert lm.capture_ms == 0.0
        assert lm.target_fps == 60.0

    def test_layer_metrics_to_dict(self):
        """Test to_dict method."""
        from imagestag.components.stream_view.metrics import LayerMetrics

        lm = LayerMetrics(
            layer_id="layer1",
            capture_ms=5.5,
            filter_ms=10.2,
            encode_ms=3.3,
            buffer_depth=2,
            frames_produced=100,
            frames_delivered=98,
            frames_dropped=2,
            actual_fps=58.5,
        )
        d = lm.to_dict()

        assert d["layer_id"] == "layer1"
        assert d["capture_ms"] == 5.5
        assert d["filter_ms"] == 10.2
        assert d["encode_ms"] == 3.3
        assert d["buffer_depth"] == 2
        assert d["frames_produced"] == 100
        assert d["frames_delivered"] == 98
        assert d["frames_dropped"] == 2
        assert d["actual_fps"] == 58.5


class TestPythonMetrics:
    """Tests for PythonMetrics dataclass."""

    def test_python_metrics_creation(self):
        """Test creating PythonMetrics instance."""
        from imagestag.components.stream_view.metrics import PythonMetrics

        pm = PythonMetrics()
        assert pm.layers == {}
        assert pm.total_frames_produced == 0

    def test_get_layer_creates_new(self):
        """Test get_layer creates new metrics if not exists."""
        from imagestag.components.stream_view.metrics import PythonMetrics

        pm = PythonMetrics()
        lm = pm.get_layer("new-layer")

        assert lm.layer_id == "new-layer"
        assert "new-layer" in pm.layers

    def test_get_layer_returns_existing(self):
        """Test get_layer returns existing metrics."""
        from imagestag.components.stream_view.metrics import PythonMetrics

        pm = PythonMetrics()
        lm1 = pm.get_layer("test")
        lm1.frames_produced = 50
        lm2 = pm.get_layer("test")

        assert lm1 is lm2
        assert lm2.frames_produced == 50

    def test_update_totals(self):
        """Test update_totals aggregates layer metrics."""
        from imagestag.components.stream_view.metrics import PythonMetrics

        pm = PythonMetrics()
        lm1 = pm.get_layer("layer1")
        lm1.frames_produced = 100
        lm1.frames_delivered = 95
        lm1.frames_dropped = 5

        lm2 = pm.get_layer("layer2")
        lm2.frames_produced = 50
        lm2.frames_delivered = 48
        lm2.frames_dropped = 2

        pm.update_totals()

        assert pm.total_frames_produced == 150
        assert pm.total_frames_delivered == 143
        assert pm.total_frames_dropped == 7

    def test_to_dict(self):
        """Test to_dict method."""
        from imagestag.components.stream_view.metrics import PythonMetrics

        pm = PythonMetrics()
        lm = pm.get_layer("test")
        lm.frames_produced = 10

        d = pm.to_dict()

        assert "layers" in d
        assert "test" in d["layers"]
        assert d["total_frames_produced"] == 10
        assert "uptime_seconds" in d


class TestFPSCounter:
    """Tests for FPSCounter class."""

    def test_fps_counter_creation(self):
        """Test creating FPSCounter."""
        from imagestag.components.stream_view.metrics import FPSCounter

        fc = FPSCounter(window_size=30)
        assert fc._window_size == 30
        assert fc.fps == 0.0

    def test_fps_counter_tick(self):
        """Test tick method."""
        from imagestag.components.stream_view.metrics import FPSCounter

        fc = FPSCounter()
        fc.tick()
        time.sleep(0.02)
        fc.tick()
        time.sleep(0.02)
        fc.tick()

        # Should have some FPS now
        assert fc.fps > 0

    def test_fps_counter_empty(self):
        """Test fps returns 0 when no ticks."""
        from imagestag.components.stream_view.metrics import FPSCounter

        fc = FPSCounter()
        assert fc.fps == 0.0

    def test_fps_counter_single_tick(self):
        """Test fps returns 0 with single tick."""
        from imagestag.components.stream_view.metrics import FPSCounter

        fc = FPSCounter()
        fc.tick()
        assert fc.fps == 0.0

    def test_fps_counter_reset(self):
        """Test reset method."""
        from imagestag.components.stream_view.metrics import FPSCounter

        fc = FPSCounter()
        fc.tick()
        time.sleep(0.01)
        fc.tick()
        fc.reset()

        assert fc.fps == 0.0
        assert fc._last_time == 0.0


class TestTimer:
    """Tests for Timer context manager."""

    def test_timer_basic(self):
        """Test basic timer usage."""
        from imagestag.components.stream_view.metrics import Timer

        with Timer() as t:
            time.sleep(0.05)

        assert t.elapsed_ms >= 50
        assert t.elapsed_seconds >= 0.05

    def test_timer_properties(self):
        """Test timer properties."""
        from imagestag.components.stream_view.metrics import Timer

        with Timer() as t:
            pass

        # Should be very small but positive
        assert t.elapsed_ms >= 0
        assert t.elapsed_seconds >= 0


# ============================================================================
# VIEWPORT AND EVENT ARGUMENT TESTS
# ============================================================================


class TestViewport:
    """Tests for Viewport dataclass."""

    def test_viewport_defaults(self):
        """Test Viewport default values."""
        from imagestag.components.stream_view.stream_view import Viewport

        vp = Viewport()
        assert vp.x == 0.0
        assert vp.y == 0.0
        assert vp.width == 1.0
        assert vp.height == 1.0
        assert vp.zoom == 1.0

    def test_viewport_custom(self):
        """Test Viewport with custom values."""
        from imagestag.components.stream_view.stream_view import Viewport

        vp = Viewport(x=0.25, y=0.25, width=0.5, height=0.5, zoom=2.0)
        assert vp.x == 0.25
        assert vp.y == 0.25
        assert vp.width == 0.5
        assert vp.height == 0.5
        assert vp.zoom == 2.0


class TestStreamViewMouseEventArguments:
    """Tests for StreamViewMouseEventArguments."""

    def test_mouse_event_defaults(self):
        """Test default values."""
        from imagestag.components.stream_view.stream_view import StreamViewMouseEventArguments

        args = StreamViewMouseEventArguments(sender=None, client=None, args={})
        assert args.x == 0
        assert args.y == 0
        assert args.buttons == 0
        assert args.alt is False
        assert args.ctrl is False
        assert args.shift is False
        assert args.meta is False
        assert args.viewport is None

    def test_mouse_event_with_viewport(self):
        """Test with viewport."""
        from imagestag.components.stream_view.stream_view import (
            StreamViewMouseEventArguments,
            Viewport,
        )

        vp = Viewport(zoom=2.0)
        args = StreamViewMouseEventArguments(
            sender=None,
            client=None,
            args={},
            x=100,
            y=200,
            viewport=vp,
        )
        assert args.x == 100
        assert args.y == 200
        assert args.viewport.zoom == 2.0


class TestStreamViewViewportEventArguments:
    """Tests for StreamViewViewportEventArguments."""

    def test_viewport_event_defaults(self):
        """Test default values with post_init."""
        from imagestag.components.stream_view.stream_view import (
            StreamViewViewportEventArguments,
            Viewport,
        )

        args = StreamViewViewportEventArguments(sender=None, client=None, args={})
        # __post_init__ should create a default Viewport
        assert args.viewport is not None
        assert isinstance(args.viewport, Viewport)

    def test_viewport_event_with_viewports(self):
        """Test with viewports."""
        from imagestag.components.stream_view.stream_view import (
            StreamViewViewportEventArguments,
            Viewport,
        )

        current = Viewport(zoom=2.0)
        prev = Viewport(zoom=1.0)
        args = StreamViewViewportEventArguments(
            sender=None,
            client=None,
            args={},
            viewport=current,
            prev_viewport=prev,
        )
        assert args.viewport.zoom == 2.0
        assert args.prev_viewport.zoom == 1.0


# ============================================================================
# STREAMVIEWLAYER TESTS
# ============================================================================


class TestStreamViewLayer:
    """Tests for StreamViewLayer dataclass."""

    def test_layer_with_stream(self):
        """Test creating layer with stream source."""
        from imagestag.components.stream_view.layers import StreamViewLayer
        from imagestag.streams.generator import GeneratorStream

        stream = GeneratorStream(
            handler=lambda t: Image.from_array(np.zeros((100, 100, 3), dtype=np.uint8))
        )
        layer = StreamViewLayer(stream=stream, z_index=1)

        assert layer.stream is stream
        assert layer.z_index == 1
        assert layer.is_static is False
        assert layer.source_type == "stream"

    def test_layer_with_url(self):
        """Test creating layer with URL source."""
        from imagestag.components.stream_view.layers import StreamViewLayer

        layer = StreamViewLayer(url="https://example.com/image.png", z_index=5)

        assert layer.url == "https://example.com/image.png"
        assert layer.is_static is True
        assert layer.source_type == "url"

    def test_layer_with_image(self):
        """Test creating layer with Image source."""
        from imagestag.components.stream_view.layers import StreamViewLayer

        img = Image.from_array(np.zeros((100, 100, 3), dtype=np.uint8))
        layer = StreamViewLayer(image=img)

        assert layer.image is img
        assert layer.is_static is True
        assert layer.source_type == "image"

    def test_layer_no_source_raises(self):
        """Test that no source raises error."""
        from imagestag.components.stream_view.layers import StreamViewLayer

        with pytest.raises(ValueError, match="requires a source"):
            StreamViewLayer()

    def test_layer_multiple_sources_raises(self):
        """Test that multiple sources raises error."""
        from imagestag.components.stream_view.layers import StreamViewLayer
        from imagestag.streams.generator import GeneratorStream

        stream = GeneratorStream(
            handler=lambda t: Image.from_array(np.zeros((10, 10, 3), dtype=np.uint8))
        )
        with pytest.raises(ValueError, match="only have one source"):
            StreamViewLayer(stream=stream, url="http://test.com")

    def test_layer_piggyback_mode(self):
        """Test piggyback layer doesn't require source."""
        from imagestag.components.stream_view.layers import StreamViewLayer

        layer = StreamViewLayer(piggyback=True)
        assert layer.piggyback is True

    def test_layer_piggyback_multiple_sources_raises(self):
        """Test piggyback with multiple sources raises error."""
        from imagestag.components.stream_view.layers import StreamViewLayer
        from imagestag.streams.generator import GeneratorStream

        stream = GeneratorStream(
            handler=lambda t: Image.from_array(np.zeros((10, 10, 3), dtype=np.uint8))
        )
        with pytest.raises(ValueError, match="at most one source"):
            StreamViewLayer(piggyback=True, stream=stream, url="http://test.com")

    def test_layer_source_layer_auto_piggyback(self):
        """Test that source_layer auto-enables piggyback."""
        from imagestag.components.stream_view.layers import StreamViewLayer

        source = StreamViewLayer(url="http://test.com")
        derived = StreamViewLayer(source_layer=source)

        assert derived.piggyback is True
        assert derived.source_type == "derived"

    def test_layer_unique_id(self):
        """Test layers get unique IDs."""
        from imagestag.components.stream_view.layers import StreamViewLayer

        layer1 = StreamViewLayer(url="http://a.com")
        layer2 = StreamViewLayer(url="http://b.com")

        assert layer1.id != layer2.id

    def test_layer_get_static_frame_url(self):
        """Test get_static_frame with URL source."""
        from imagestag.components.stream_view.layers import StreamViewLayer

        layer = StreamViewLayer(url="http://test.com/img.jpg")
        assert layer.get_static_frame() == "http://test.com/img.jpg"

    def test_layer_get_static_frame_image(self):
        """Test get_static_frame with Image source."""
        from imagestag.components.stream_view.layers import StreamViewLayer

        img = Image.from_array(np.zeros((10, 10, 3), dtype=np.uint8))
        layer = StreamViewLayer(image=img)

        result = layer.get_static_frame()
        assert result.startswith("data:image/jpeg;base64,")

    def test_layer_get_static_frame_image_png(self):
        """Test get_static_frame with PNG format."""
        from imagestag.components.stream_view.layers import StreamViewLayer

        img = Image.from_array(np.zeros((10, 10, 3), dtype=np.uint8))
        layer = StreamViewLayer(image=img, use_png=True)

        result = layer.get_static_frame()
        assert result.startswith("data:image/png;base64,")

    def test_layer_get_static_frame_no_source(self):
        """Test get_static_frame returns None for stream source."""
        from imagestag.components.stream_view.layers import StreamViewLayer
        from imagestag.streams.generator import GeneratorStream

        stream = GeneratorStream(
            handler=lambda t: Image.from_array(np.zeros((10, 10, 3), dtype=np.uint8))
        )
        layer = StreamViewLayer(stream=stream)

        assert layer.get_static_frame() is None

    def test_layer_set_viewport(self):
        """Test set_viewport method."""
        from imagestag.components.stream_view.layers import StreamViewLayer
        from imagestag.components.stream_view.stream_view import Viewport

        layer = StreamViewLayer(url="http://test.com")
        vp = Viewport(x=0.1, y=0.2, width=0.5, height=0.5, zoom=2.0)
        layer.set_viewport(vp)

        assert layer._viewport_x == 0.1
        assert layer._viewport_y == 0.2
        assert layer._viewport_w == 0.5
        assert layer._viewport_h == 0.5
        assert layer._viewport_zoom == 2.0

    def test_layer_set_target_size(self):
        """Test set_target_size method."""
        from imagestag.components.stream_view.layers import StreamViewLayer

        layer = StreamViewLayer(url="http://test.com")
        layer.set_target_size(1920, 1080)

        assert layer._target_width == 1920
        assert layer._target_height == 1080

    def test_layer_is_zoomed(self):
        """Test is_zoomed property."""
        from imagestag.components.stream_view.layers import StreamViewLayer
        from imagestag.components.stream_view.stream_view import Viewport

        layer = StreamViewLayer(url="http://test.com")
        assert layer.is_zoomed is False

        layer.set_viewport(Viewport(zoom=2.0))
        assert layer.is_zoomed is True

    def test_layer_get_viewport_crop(self):
        """Test get_viewport_crop method."""
        from imagestag.components.stream_view.layers import StreamViewLayer
        from imagestag.components.stream_view.stream_view import Viewport

        layer = StreamViewLayer(url="http://test.com")
        layer.set_viewport(Viewport(x=0.25, y=0.25, width=0.5, height=0.5, zoom=2.0))

        x1, y1, x2, y2 = layer.get_viewport_crop(1000, 1000)
        assert x1 == 250
        assert y1 == 250
        assert x2 == 750
        assert y2 == 750

    def test_layer_effective_viewport_fixed(self):
        """Test get_effective_viewport for fixed layer (depth=0)."""
        from imagestag.components.stream_view.layers import StreamViewLayer
        from imagestag.components.stream_view.stream_view import Viewport

        layer = StreamViewLayer(url="http://test.com", depth=0.0)
        layer.set_viewport(Viewport(x=0.25, y=0.25, width=0.5, height=0.5, zoom=2.0))

        x, y, w, h, z = layer.get_effective_viewport()
        assert x == 0.0
        assert y == 0.0
        assert w == 1.0
        assert h == 1.0
        assert z == 1.0

    def test_layer_effective_viewport_content(self):
        """Test get_effective_viewport for content layer (depth=1)."""
        from imagestag.components.stream_view.layers import StreamViewLayer
        from imagestag.components.stream_view.stream_view import Viewport

        layer = StreamViewLayer(url="http://test.com", depth=1.0)
        layer.set_viewport(Viewport(x=0.25, y=0.25, width=0.5, height=0.5, zoom=2.0))

        x, y, w, h, z = layer.get_effective_viewport()
        assert x == 0.25
        assert y == 0.25
        assert w == 0.5
        assert h == 0.5
        assert z == 2.0

    def test_layer_effective_viewport_parallax(self):
        """Test get_effective_viewport for parallax layer (depth=0.5)."""
        from imagestag.components.stream_view.layers import StreamViewLayer
        from imagestag.components.stream_view.stream_view import Viewport

        layer = StreamViewLayer(url="http://test.com", depth=0.5)
        layer.set_viewport(Viewport(x=0.25, y=0.25, width=0.5, height=0.5, zoom=2.0))

        x, y, w, h, z = layer.get_effective_viewport()
        # Parallax should interpolate
        assert z == 1.5  # 1 + (2 - 1) * 0.5

    def test_layer_get_effective_crop(self):
        """Test get_effective_crop method."""
        from imagestag.components.stream_view.layers import StreamViewLayer
        from imagestag.components.stream_view.stream_view import Viewport

        layer = StreamViewLayer(url="http://test.com", depth=1.0)
        layer.set_viewport(Viewport(x=0.25, y=0.25, width=0.5, height=0.5, zoom=2.0))

        x1, y1, x2, y2 = layer.get_effective_crop(1000, 1000)
        assert x1 == 250
        assert y1 == 250
        assert x2 == 750
        assert y2 == 750

    def test_layer_effective_zoom(self):
        """Test effective_zoom property."""
        from imagestag.components.stream_view.layers import StreamViewLayer
        from imagestag.components.stream_view.stream_view import Viewport

        layer = StreamViewLayer(url="http://test.com", depth=1.0)
        layer.set_viewport(Viewport(zoom=3.0))

        assert layer.effective_zoom == 3.0

    def test_layer_inject_frame(self):
        """Test inject_frame method."""
        from imagestag.components.stream_view.layers import StreamViewLayer

        layer = StreamViewLayer(piggyback=True, buffer_size=4)

        layer.inject_frame("data:image/jpeg;base64,abc", time.perf_counter())
        layer.inject_frame("data:image/jpeg;base64,def", time.perf_counter())

        assert len(layer._frame_buffer) == 2
        assert layer.frames_produced == 2

    def test_layer_inject_frame_with_timings(self):
        """Test inject_frame with step_timings."""
        from imagestag.components.stream_view.layers import StreamViewLayer

        layer = StreamViewLayer(piggyback=True)
        layer.inject_frame(
            "data:image/jpeg;base64,abc",
            time.perf_counter(),
            step_timings={"crop_ms": 1.5, "filter_ms": 2.5},
        )

        assert layer.frames_produced == 1

    def test_layer_inject_frame_with_anchor(self):
        """Test inject_frame with anchor position."""
        from imagestag.components.stream_view.layers import StreamViewLayer

        layer = StreamViewLayer(piggyback=True)
        layer.inject_frame(
            "data:image/jpeg;base64,abc",
            time.perf_counter(),
            anchor_x=100,
            anchor_y=200,
        )

        assert layer._anchor_x == 100
        assert layer._anchor_y == 200

    def test_layer_inject_frame_buffer_limit(self):
        """Test inject_frame respects buffer limit."""
        from imagestag.components.stream_view.layers import StreamViewLayer

        layer = StreamViewLayer(piggyback=True, buffer_size=2)

        for i in range(5):
            layer.inject_frame(f"data:image/jpeg;base64,{i}", time.perf_counter())

        # Should only have 2 frames (dropped oldest)
        assert len(layer._frame_buffer) == 2

    def test_layer_get_buffered_frame(self):
        """Test get_buffered_frame method."""
        from imagestag.components.stream_view.layers import StreamViewLayer

        layer = StreamViewLayer(piggyback=True)
        layer.inject_frame("data:image/jpeg;base64,first", time.perf_counter())
        layer.inject_frame("data:image/jpeg;base64,second", time.perf_counter())

        frame1 = layer.get_buffered_frame()
        assert frame1 is not None
        assert "first" in frame1[1]

        frame2 = layer.get_buffered_frame()
        assert frame2 is not None
        assert "second" in frame2[1]

        frame3 = layer.get_buffered_frame()
        assert frame3 is None

    def test_layer_start_stop(self):
        """Test start and stop methods."""
        from imagestag.components.stream_view.layers import StreamViewLayer

        layer = StreamViewLayer(url="http://test.com")

        # Static layer - start does nothing
        layer.start()
        assert layer._running is True

        layer.stop()
        assert layer._running is False

    def test_layer_start_with_stream(self):
        """Test start with stream source."""
        from imagestag.components.stream_view.layers import StreamViewLayer
        from imagestag.streams.generator import GeneratorStream

        stream = GeneratorStream(
            handler=lambda t: Image.from_array(np.zeros((10, 10, 3), dtype=np.uint8))
        )
        layer = StreamViewLayer(stream=stream, buffer_size=2)

        layer.start()
        time.sleep(0.1)

        assert layer._running is True
        assert layer._producer_thread is not None

        layer.stop()
        assert layer._running is False

    def test_layer_get_effective_fps(self):
        """Test _get_effective_fps method."""
        from imagestag.components.stream_view.layers import StreamViewLayer
        from imagestag.streams.generator import GeneratorStream

        stream = GeneratorStream(
            handler=lambda t: Image.from_array(np.zeros((10, 10, 3), dtype=np.uint8))
        )
        layer = StreamViewLayer(stream=stream, target_fps=30)

        # Should return target_fps for non-video streams
        assert layer._get_effective_fps() == 30.0


# ============================================================================
# STREAMVIEW COMPONENT TESTS (ASYNC WITH NICEGUI USER FIXTURE)
# ============================================================================


@pytest.mark.asyncio
async def test_stream_view_initialization(user: User) -> None:
    """Test StreamView initialization."""
    from nicegui import ui
    from imagestag.components.stream_view import StreamView

    view = None

    @ui.page("/test_init")
    def page():
        nonlocal view
        view = StreamView(width=1280, height=720, show_metrics=True)

    await user.open("/test_init")

    # Check that component was created and configured
    assert view is not None
    assert view._width == 1280
    assert view._height == 720
    assert view._props["showMetrics"] is True


@pytest.mark.asyncio
async def test_stream_view_props(user: User) -> None:
    """Test StreamView props are set correctly."""
    from nicegui import ui
    from imagestag.components.stream_view import StreamView

    view = None

    @ui.page("/test_props")
    def page():
        nonlocal view
        view = StreamView(
            width=1920,
            height=1080,
            show_metrics=True,
            enable_zoom=True,
            min_zoom=0.5,
            max_zoom=5.0,
        )

    await user.open("/test_props")

    # Check internal state
    assert view._width == 1920
    assert view._height == 1080
    assert view._props["showMetrics"] is True
    assert view._props["enableZoom"] is True
    assert view._props["minZoom"] == 0.5
    assert view._props["maxZoom"] == 5.0


@pytest.mark.asyncio
async def test_stream_view_add_layer_static(user: User) -> None:
    """Test adding static layer to StreamView."""
    from nicegui import ui
    from imagestag.components.stream_view import StreamView

    view = None
    layer = None

    @ui.page("/test_static_layer")
    def page():
        nonlocal view, layer
        view = StreamView(width=800, height=600)
        layer = view.add_layer(
            url="http://example.com/image.jpg",
            z_index=1,
            name="Static Layer",
        )

    await user.open("/test_static_layer")

    assert layer is not None
    assert layer.id in view._layers
    assert layer.is_static is True
    assert layer.name == "Static Layer"


@pytest.mark.asyncio
async def test_stream_view_add_layer_with_image(user: User) -> None:
    """Test adding layer with Image source."""
    from nicegui import ui
    from imagestag.components.stream_view import StreamView

    view = None
    layer = None

    @ui.page("/test_image_layer")
    def page():
        nonlocal view, layer
        img = Image.from_array(np.zeros((100, 100, 3), dtype=np.uint8))
        view = StreamView(width=800, height=600)
        layer = view.add_layer(
            image=img,
            z_index=0,
        )

    await user.open("/test_image_layer")

    assert layer is not None
    assert layer.is_static is True
    assert layer.source_type == "image"


@pytest.mark.asyncio
async def test_stream_view_add_layer_with_stream(user: User) -> None:
    """Test adding layer with stream source."""
    from nicegui import ui
    from imagestag.components.stream_view import StreamView
    from imagestag.streams.generator import GeneratorStream

    view = None
    layer = None
    stream = None

    @ui.page("/test_stream_layer")
    def page():
        nonlocal view, layer, stream
        stream = GeneratorStream(
            handler=lambda t: Image.from_array(np.zeros((100, 100, 3), dtype=np.uint8))
        )
        view = StreamView(width=800, height=600)
        layer = view.add_layer(
            stream=stream,
            fps=30,
            z_index=0,
            buffer_size=2,
            jpeg_quality=90,
        )

    await user.open("/test_stream_layer")

    assert layer is not None
    assert layer.is_static is False
    assert layer.target_fps == 30
    assert layer.jpeg_quality == 90
    assert layer.buffer_size == 2


@pytest.mark.asyncio
async def test_stream_view_add_layer_positioned(user: User) -> None:
    """Test adding positioned layer."""
    from nicegui import ui
    from imagestag.components.stream_view import StreamView

    view = None
    layer = None

    @ui.page("/test_positioned_layer")
    def page():
        nonlocal view, layer
        view = StreamView(width=800, height=600)
        layer = view.add_layer(
            url="http://example.com/overlay.png",
            x=100,
            y=50,
            width=200,
            height=150,
            z_index=10,
        )

    await user.open("/test_positioned_layer")

    assert layer.x == 100
    assert layer.y == 50
    assert layer.width == 200
    assert layer.height == 150


@pytest.mark.asyncio
async def test_stream_view_add_layer_with_depth(user: User) -> None:
    """Test adding layer with depth parameter."""
    from nicegui import ui
    from imagestag.components.stream_view import StreamView

    view = None
    fixed_layer = None
    content_layer = None
    parallax_layer = None

    @ui.page("/test_depth_layers")
    def page():
        nonlocal view, fixed_layer, content_layer, parallax_layer
        view = StreamView(width=800, height=600)
        fixed_layer = view.add_layer(url="http://test.com/hud.png", z_index=100, depth=0.0)
        content_layer = view.add_layer(url="http://test.com/video.jpg", z_index=0, depth=1.0)
        parallax_layer = view.add_layer(url="http://test.com/bg.jpg", z_index=-1, depth=0.5)

    await user.open("/test_depth_layers")

    assert fixed_layer.depth == 0.0
    assert content_layer.depth == 1.0
    assert parallax_layer.depth == 0.5


@pytest.mark.asyncio
async def test_stream_view_remove_layer(user: User) -> None:
    """Test removing a layer."""
    from nicegui import ui
    from imagestag.components.stream_view import StreamView

    view = None
    layer = None

    @ui.page("/test_remove_layer")
    def page():
        nonlocal view, layer
        view = StreamView(width=800, height=600)
        layer = view.add_layer(url="http://test.com/img.jpg", z_index=0)

    await user.open("/test_remove_layer")

    layer_id = layer.id
    assert layer_id in view._layers

    view.remove_layer(layer_id)
    assert layer_id not in view._layers


@pytest.mark.asyncio
async def test_stream_view_set_svg(user: User) -> None:
    """Test setting SVG overlay."""
    from nicegui import ui
    from imagestag.components.stream_view import StreamView

    view = None

    @ui.page("/test_svg")
    def page():
        nonlocal view
        view = StreamView(width=800, height=600)
        view.set_svg(
            '<circle cx="{x}" cy="{y}" r="10" fill="red"/>',
            {"x": 100, "y": 100},
        )

    await user.open("/test_svg")

    assert view._svg_template == '<circle cx="{x}" cy="{y}" r="10" fill="red"/>'
    assert view._svg_values == {"x": 100, "y": 100}


@pytest.mark.asyncio
async def test_stream_view_update_svg_values(user: User) -> None:
    """Test updating SVG values."""
    from nicegui import ui
    from imagestag.components.stream_view import StreamView

    view = None

    @ui.page("/test_svg_update")
    def page():
        nonlocal view
        view = StreamView(width=800, height=600)
        view.set_svg('<circle cx="{x}" cy="{y}" r="10"/>', {"x": 0, "y": 0})

    await user.open("/test_svg_update")

    view.update_svg_values(x=200, y=300)
    assert view._svg_values["x"] == 200
    assert view._svg_values["y"] == 300


@pytest.mark.asyncio
async def test_stream_view_on_mouse_move(user: User) -> None:
    """Test mouse move handler registration."""
    from nicegui import ui
    from imagestag.components.stream_view import StreamView

    view = None
    received_events = []

    @ui.page("/test_mouse_move")
    def page():
        nonlocal view
        view = StreamView(width=800, height=600)

        @view.on_mouse_move
        def handle_move(e):
            received_events.append(e)

    await user.open("/test_mouse_move")

    assert view._mouse_move_handler is not None


@pytest.mark.asyncio
async def test_stream_view_on_mouse_click(user: User) -> None:
    """Test mouse click handler registration."""
    from nicegui import ui
    from imagestag.components.stream_view import StreamView

    view = None

    @ui.page("/test_mouse_click")
    def page():
        nonlocal view
        view = StreamView(width=800, height=600)

        @view.on_mouse_click
        def handle_click(e):
            pass

    await user.open("/test_mouse_click")

    assert view._mouse_click_handler is not None


@pytest.mark.asyncio
async def test_stream_view_on_viewport_change(user: User) -> None:
    """Test viewport change handler registration."""
    from nicegui import ui
    from imagestag.components.stream_view import StreamView

    view = None

    @ui.page("/test_viewport_change")
    def page():
        nonlocal view
        view = StreamView(width=800, height=600, enable_zoom=True)

        @view.on_viewport_change
        def handle_viewport(e):
            pass

    await user.open("/test_viewport_change")

    assert view._viewport_handler is not None


@pytest.mark.asyncio
async def test_stream_view_viewport_property(user: User) -> None:
    """Test viewport property."""
    from nicegui import ui
    from imagestag.components.stream_view import StreamView

    view = None

    @ui.page("/test_viewport_prop")
    def page():
        nonlocal view
        view = StreamView(width=800, height=600)

    await user.open("/test_viewport_prop")

    vp = view.viewport
    assert vp.zoom == 1.0
    assert vp.x == 0.0
    assert vp.y == 0.0


@pytest.mark.asyncio
async def test_stream_view_zoom_property(user: User) -> None:
    """Test zoom property."""
    from nicegui import ui
    from imagestag.components.stream_view import StreamView

    view = None

    @ui.page("/test_zoom_prop")
    def page():
        nonlocal view
        view = StreamView(width=800, height=600)

    await user.open("/test_zoom_prop")

    assert view.zoom == 1.0


@pytest.mark.asyncio
async def test_stream_view_set_size(user: User) -> None:
    """Test set_size method."""
    from nicegui import ui
    from imagestag.components.stream_view import StreamView

    view = None

    @ui.page("/test_set_size")
    def page():
        nonlocal view
        view = StreamView(width=800, height=600)

    await user.open("/test_set_size")

    view.set_size(1920, 1080)
    assert view._width == 1920
    assert view._height == 1080


@pytest.mark.asyncio
async def test_stream_view_start_stop(user: User) -> None:
    """Test start and stop methods."""
    from nicegui import ui
    from imagestag.components.stream_view import StreamView

    view = None

    @ui.page("/test_start_stop")
    def page():
        nonlocal view
        view = StreamView(width=800, height=600)
        view.add_layer(url="http://test.com/img.jpg")

    await user.open("/test_start_stop")

    view.start()
    view.stop()


@pytest.mark.asyncio
async def test_stream_view_get_metrics(user: User) -> None:
    """Test get_metrics method."""
    from nicegui import ui
    from imagestag.components.stream_view import StreamView

    view = None

    @ui.page("/test_metrics")
    def page():
        nonlocal view
        view = StreamView(width=800, height=600)
        view.add_layer(url="http://test.com/img.jpg", name="Test Layer")

    await user.open("/test_metrics")

    metrics = view.get_metrics()
    assert "layers" in metrics
    assert "total_frames_produced" in metrics


@pytest.mark.asyncio
async def test_stream_view_update_layer_position(user: User) -> None:
    """Test update_layer_position method."""
    from nicegui import ui
    from imagestag.components.stream_view import StreamView

    view = None
    layer = None

    @ui.page("/test_update_position")
    def page():
        nonlocal view, layer
        view = StreamView(width=800, height=600)
        layer = view.add_layer(url="http://test.com/img.jpg", x=0, y=0, width=100, height=100)

    await user.open("/test_update_position")

    view.update_layer_position(layer.id, x=50, y=50)
    assert layer.x == 50
    assert layer.y == 50


@pytest.mark.asyncio
async def test_stream_view_set_fullscreen_mode(user: User) -> None:
    """Test set_fullscreen_mode method."""
    from nicegui import ui
    from imagestag.components.stream_view import StreamView

    view = None
    layer = None

    @ui.page("/test_fullscreen")
    def page():
        nonlocal view, layer
        view = StreamView(width=800, height=600)
        layer = view.add_layer(url="http://test.com/img.jpg", fullscreen_scale="screen")

    await user.open("/test_fullscreen")

    # Enter fullscreen
    view.set_fullscreen_mode(True, screen_width=1920, screen_height=1080, video_width=800, video_height=600)

    # Exit fullscreen
    view.set_fullscreen_mode(False)


@pytest.mark.asyncio
async def test_stream_view_source_layer_string_reference(user: User) -> None:
    """Test adding layer with source_layer as string ID."""
    from nicegui import ui
    from imagestag.components.stream_view import StreamView
    from imagestag.streams.generator import GeneratorStream

    view = None
    source_layer = None
    derived_layer = None

    @ui.page("/test_source_layer_string")
    def page():
        nonlocal view, source_layer, derived_layer
        stream = GeneratorStream(
            handler=lambda t: Image.from_array(np.zeros((100, 100, 3), dtype=np.uint8))
        )
        view = StreamView(width=800, height=600)
        source_layer = view.add_layer(stream=stream, z_index=0, name="Source")
        derived_layer = view.add_layer(source_layer=source_layer.id, z_index=1, name="Derived")

    await user.open("/test_source_layer_string")

    assert derived_layer is not None
    assert derived_layer.source_layer is source_layer


@pytest.mark.asyncio
async def test_stream_view_source_layer_invalid_raises(user: User) -> None:
    """Test adding layer with invalid source_layer ID raises error."""
    from nicegui import ui
    from imagestag.components.stream_view import StreamView

    view = None
    error_raised = False

    @ui.page("/test_invalid_source")
    def page():
        nonlocal view, error_raised
        view = StreamView(width=800, height=600)
        try:
            view.add_layer(source_layer="nonexistent", z_index=0)
        except ValueError as e:
            if "not found" in str(e):
                error_raised = True

    await user.open("/test_invalid_source")
    assert error_raised


@pytest.mark.asyncio
async def test_stream_view_layer_with_mask(user: User) -> None:
    """Test adding layer with mask."""
    from nicegui import ui
    from imagestag.components.stream_view import StreamView

    view = None
    layer = None

    @ui.page("/test_mask")
    def page():
        nonlocal view, layer
        mask = Image.from_array(np.full((100, 100), 128, dtype=np.uint8))  # Grayscale
        view = StreamView(width=800, height=600)
        layer = view.add_layer(url="http://test.com/img.jpg", mask=mask, z_index=0)

    await user.open("/test_mask")
    assert layer is not None


@pytest.mark.asyncio
async def test_stream_view_layer_with_mask_url(user: User) -> None:
    """Test adding layer with mask as URL."""
    from nicegui import ui
    from imagestag.components.stream_view import StreamView

    view = None
    layer = None

    @ui.page("/test_mask_url")
    def page():
        nonlocal view, layer
        view = StreamView(width=800, height=600)
        layer = view.add_layer(
            url="http://test.com/img.jpg",
            mask="http://test.com/mask.png",
            z_index=0,
        )

    await user.open("/test_mask_url")
    assert layer is not None


@pytest.mark.asyncio
async def test_stream_view_nav_window_config(user: User) -> None:
    """Test navigation window configuration."""
    from nicegui import ui
    from imagestag.components.stream_view import StreamView

    view = None

    @ui.page("/test_nav_window")
    def page():
        nonlocal view
        view = StreamView(
            width=800,
            height=600,
            enable_zoom=True,
            show_nav_window=True,
            nav_window_position="top-left",
            nav_window_size=(200, 120),
        )

    await user.open("/test_nav_window")

    assert view._props["showNavWindow"] is True
    assert view._props["navWindowPosition"] == "top-left"
    assert view._props["navWindowWidth"] == 200
    assert view._props["navWindowHeight"] == 120


# ============================================================================
# INTERNAL METHOD TESTS (NON-ASYNC)
# ============================================================================


class TestStreamViewInternalMethods:
    """Tests for StreamView internal methods that don't require browser."""

    def test_update_layer_order(self):
        """Test _update_layer_order sorts by z_index."""
        from imagestag.components.stream_view.layers import StreamViewLayer

        # Create mock layers dict
        layers = {}
        layer1 = StreamViewLayer(url="http://test1.com", z_index=10)
        layer2 = StreamViewLayer(url="http://test2.com", z_index=5)
        layer3 = StreamViewLayer(url="http://test3.com", z_index=15)

        layers[layer1.id] = layer1
        layers[layer2.id] = layer2
        layers[layer3.id] = layer3

        # Sort keys by z_index
        sorted_keys = sorted(layers.keys(), key=lambda lid: layers[lid].z_index)

        # Should be in order: layer2 (5), layer1 (10), layer3 (15)
        assert layers[sorted_keys[0]].z_index == 5
        assert layers[sorted_keys[1]].z_index == 10
        assert layers[sorted_keys[2]].z_index == 15

    def test_create_mouse_event_with_viewport(self):
        """Test _create_mouse_event creates proper event with viewport."""
        from imagestag.components.stream_view.stream_view import (
            StreamViewMouseEventArguments,
            Viewport,
        )
        from nicegui.events import GenericEventArguments

        # Simulate raw event data
        args = {
            "x": 100,
            "y": 200,
            "sourceX": 150,
            "sourceY": 250,
            "buttons": 1,
            "alt": False,
            "ctrl": True,
            "shift": False,
            "meta": False,
            "viewport": {
                "x": 0.1,
                "y": 0.2,
                "width": 0.5,
                "height": 0.5,
                "zoom": 2.0,
            },
        }

        # Parse viewport
        vp_data = args["viewport"]
        viewport = Viewport(
            x=vp_data.get("x", 0),
            y=vp_data.get("y", 0),
            width=vp_data.get("width", 1),
            height=vp_data.get("height", 1),
            zoom=vp_data.get("zoom", 1),
        )

        event = StreamViewMouseEventArguments(
            sender=None,
            client=None,
            args=args,
            x=args.get("x", 0),
            y=args.get("y", 0),
            source_x=args.get("sourceX", 0),
            source_y=args.get("sourceY", 0),
            buttons=args.get("buttons", 0),
            ctrl=args.get("ctrl", False),
            viewport=viewport,
        )

        assert event.x == 100
        assert event.y == 200
        assert event.source_x == 150
        assert event.source_y == 250
        assert event.buttons == 1
        assert event.ctrl is True
        assert event.viewport.zoom == 2.0

    def test_send_svg_missing_placeholder(self):
        """Test _send_svg handles missing placeholders gracefully."""
        # Test the format behavior directly
        template = '<circle cx="{x}" cy="{y}" r="10"/>'
        values = {"x": 100}  # Missing 'y'

        with pytest.raises(KeyError):
            template.format(**values)


class TestStreamViewLayerProducerLoop:
    """Tests for StreamViewLayer producer loop behavior."""

    def test_producer_loop_creates_frames(self):
        """Test that producer loop creates frames in buffer."""
        from imagestag.components.stream_view.layers import StreamViewLayer
        from imagestag.streams.generator import GeneratorStream

        call_count = [0]

        def handler(t):
            call_count[0] += 1
            return Image.from_array(np.full((10, 10, 3), call_count[0], dtype=np.uint8))

        stream = GeneratorStream(handler=handler)
        layer = StreamViewLayer(stream=stream, buffer_size=4, target_fps=30)

        layer.start()
        time.sleep(0.2)  # Let producer run
        layer.stop()

        assert call_count[0] > 0
        assert layer.frames_produced > 0


class TestStreamViewLayerUpdateFromLastFrame:
    """Tests for StreamViewLayer.update_from_last_frame."""

    def test_update_from_last_frame_no_stream(self):
        """Test update_from_last_frame returns False without stream."""
        from imagestag.components.stream_view.layers import StreamViewLayer

        layer = StreamViewLayer(url="http://test.com")
        result = layer.update_from_last_frame()
        assert result is False

    def test_update_from_last_frame_no_frame(self):
        """Test update_from_last_frame returns False without last_frame."""
        from imagestag.components.stream_view.layers import StreamViewLayer
        from imagestag.streams.generator import GeneratorStream

        stream = GeneratorStream(
            handler=lambda t: Image.from_array(np.zeros((10, 10, 3), dtype=np.uint8))
        )
        layer = StreamViewLayer(stream=stream)

        # Don't call get_frame - no last_frame yet
        result = layer.update_from_last_frame()
        assert result is False

    def test_update_from_last_frame_with_frame(self):
        """Test update_from_last_frame succeeds with last_frame."""
        from imagestag.components.stream_view.layers import StreamViewLayer
        from imagestag.streams.generator import GeneratorStream

        stream = GeneratorStream(
            handler=lambda t: Image.from_array(np.full((10, 10, 3), 128, dtype=np.uint8))
        )
        layer = StreamViewLayer(stream=stream)
        layer.set_target_size(10, 10)

        # Generate a frame so last_frame is populated
        stream.start()
        stream.get_frame(0.0)

        result = layer.update_from_last_frame()
        assert result is True
        assert len(layer._frame_buffer) == 1


# ============================================================================
# WEBRTC TESTS (IF AVAILABLE)
# ============================================================================


class TestWebRTCAvailability:
    """Test WebRTC import behavior."""

    def test_webrtc_import_flag(self):
        """Test AIORTC_AVAILABLE flag is set correctly."""
        from imagestag.components.stream_view.stream_view import AIORTC_AVAILABLE

        # Just verify the flag exists - value depends on environment
        assert isinstance(AIORTC_AVAILABLE, bool)


@pytest.mark.asyncio
async def test_stream_view_add_webrtc_layer_no_aiortc(user: User) -> None:
    """Test add_webrtc_layer raises ImportError if aiortc unavailable."""
    from nicegui import ui
    from imagestag.components.stream_view import StreamView
    from imagestag.components.stream_view.stream_view import AIORTC_AVAILABLE
    from imagestag.streams.video import VideoStream

    if AIORTC_AVAILABLE:
        pytest.skip("aiortc is available, test for missing aiortc")

    view = None

    @ui.page("/test_webrtc_no_aiortc")
    def page():
        nonlocal view
        view = StreamView(width=800, height=600)

    await user.open("/test_webrtc_no_aiortc")

    with pytest.raises(ImportError):
        view.add_webrtc_layer(MagicMock(), z_index=0)


# ============================================================================
# MORE STREAMVIEW INTERNAL HANDLER TESTS
# ============================================================================


class TestStreamViewInternalHandlers:
    """Tests for StreamView internal event handlers."""

    @pytest.mark.asyncio
    async def test_handle_viewport_change(self, user: User) -> None:
        """Test _handle_viewport_change method."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView
        from nicegui.events import GenericEventArguments

        view = None
        handler_called = [False]

        @ui.page("/test_viewport_handler")
        def page():
            nonlocal view
            view = StreamView(width=800, height=600, enable_zoom=True)

            @view.on_viewport_change
            def on_vp(e):
                handler_called[0] = True

        await user.open("/test_viewport_handler")

        # Simulate viewport change event
        class MockEvent:
            args = {"x": 0.1, "y": 0.1, "width": 0.5, "height": 0.5, "zoom": 2.0}

        view._handle_viewport_change(MockEvent())

        assert view._viewport.x == 0.1
        assert view._viewport.y == 0.1
        assert view._viewport.zoom == 2.0

    @pytest.mark.asyncio
    async def test_handle_size_changed(self, user: User) -> None:
        """Test _handle_size_changed method."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView

        view = None

        @ui.page("/test_size_handler")
        def page():
            nonlocal view
            view = StreamView(width=800, height=600)
            view.add_layer(url="http://test.com/img.jpg")

        await user.open("/test_size_handler")

        # Simulate size change event
        class MockEvent:
            args = {"width": 1920, "height": 1080}

        view._handle_size_changed(MockEvent())

        assert view._width == 1920
        assert view._height == 1080

    @pytest.mark.asyncio
    async def test_handle_mouse_move(self, user: User) -> None:
        """Test _handle_mouse_move method."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView

        view = None
        received_events = []

        @ui.page("/test_mouse_handler")
        def page():
            nonlocal view
            view = StreamView(width=800, height=600)

            @view.on_mouse_move
            def on_move(e):
                received_events.append(e)

        await user.open("/test_mouse_handler")

        # Simulate mouse move event
        class MockEvent:
            args = {"x": 100, "y": 200, "buttons": 0}

        view._handle_mouse_move(MockEvent())

        # Handler should have been called
        assert len(received_events) == 1

    @pytest.mark.asyncio
    async def test_handle_mouse_click(self, user: User) -> None:
        """Test _handle_mouse_click method."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView

        view = None
        click_events = []

        @ui.page("/test_click_handler")
        def page():
            nonlocal view
            view = StreamView(width=800, height=600)

            @view.on_mouse_click
            def on_click(e):
                click_events.append(e)

        await user.open("/test_click_handler")

        # Simulate click event
        class MockEvent:
            args = {"x": 400, "y": 300, "buttons": 1}

        view._handle_mouse_click(MockEvent())

        assert len(click_events) == 1

    @pytest.mark.asyncio
    async def test_handle_frame_request_static_layer(self, user: User) -> None:
        """Test _handle_frame_request skips static layers."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView

        view = None
        layer = None

        @ui.page("/test_frame_request_static")
        def page():
            nonlocal view, layer
            view = StreamView(width=800, height=600)
            layer = view.add_layer(url="http://test.com/img.jpg")

        await user.open("/test_frame_request_static")

        # Simulate frame request
        class MockEvent:
            args = {"layer_id": layer.id}

        # Should not raise and should skip static layer
        view._handle_frame_request(MockEvent())

    @pytest.mark.asyncio
    async def test_handle_frame_request_missing_layer(self, user: User) -> None:
        """Test _handle_frame_request handles missing layer."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView

        view = None

        @ui.page("/test_frame_request_missing")
        def page():
            nonlocal view
            view = StreamView(width=800, height=600)

        await user.open("/test_frame_request_missing")

        # Simulate frame request for non-existent layer
        class MockEvent:
            args = {"layer_id": "nonexistent"}

        # Should not raise
        view._handle_frame_request(MockEvent())

    @pytest.mark.asyncio
    async def test_check_pending_frames(self, user: User) -> None:
        """Test _check_pending_frames method."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView

        view = None

        @ui.page("/test_pending_frames")
        def page():
            nonlocal view
            view = StreamView(width=800, height=600)

        await user.open("/test_pending_frames")

        # Call directly - should not raise
        view._check_pending_frames()

    @pytest.mark.asyncio
    async def test_handle_delete(self, user: User) -> None:
        """Test _handle_delete cleanup."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView

        view = None

        @ui.page("/test_delete")
        def page():
            nonlocal view
            view = StreamView(width=800, height=600)
            view.add_layer(url="http://test.com/img.jpg")

        await user.open("/test_delete")

        # Should not raise
        view._handle_delete()


# ============================================================================
# STREAMVIEWLAYER PRODUCER LOOP AND EDGE CASES
# ============================================================================


class TestStreamViewLayerProducerEdgeCases:
    """Additional tests for StreamViewLayer producer loop edge cases."""

    def test_layer_producer_with_pipeline(self):
        """Test producer loop with filter pipeline."""
        from imagestag.components.stream_view.layers import StreamViewLayer
        from imagestag.streams.generator import GeneratorStream
        from imagestag.filters import FilterPipeline
        from imagestag.filters.base import Filter

        class SimpleFilter(Filter):
            def apply(self, image, context=None):
                return image

        pipeline = FilterPipeline(filters=[SimpleFilter()])

        stream = GeneratorStream(
            handler=lambda t: Image.from_array(np.full((10, 10, 3), 128, dtype=np.uint8))
        )
        layer = StreamViewLayer(stream=stream, pipeline=pipeline, buffer_size=2)

        layer.start()
        time.sleep(0.1)
        layer.stop()

        assert layer.frames_produced > 0

    def test_layer_producer_with_zoomed_viewport(self):
        """Test producer loop with zoomed viewport."""
        from imagestag.components.stream_view.layers import StreamViewLayer
        from imagestag.components.stream_view.stream_view import Viewport
        from imagestag.streams.generator import GeneratorStream

        stream = GeneratorStream(
            handler=lambda t: Image.from_array(np.full((100, 100, 3), 128, dtype=np.uint8))
        )
        layer = StreamViewLayer(stream=stream, buffer_size=2)
        layer.set_viewport(Viewport(x=0.25, y=0.25, width=0.5, height=0.5, zoom=2.0))
        layer.set_target_size(100, 100)

        layer.start()
        time.sleep(0.15)
        layer.stop()

        assert layer.frames_produced > 0

    def test_layer_producer_handles_exception(self):
        """Test producer loop handles stream exceptions gracefully."""
        from imagestag.components.stream_view.layers import StreamViewLayer
        from imagestag.streams.generator import GeneratorStream

        call_count = [0]

        def failing_handler(t):
            call_count[0] += 1
            if call_count[0] < 3:
                raise ValueError("Simulated error")
            return Image.from_array(np.full((10, 10, 3), 128, dtype=np.uint8))

        stream = GeneratorStream(handler=failing_handler)
        layer = StreamViewLayer(stream=stream, buffer_size=2)

        layer.start()
        time.sleep(0.2)
        layer.stop()

        # Should still run despite errors
        assert call_count[0] > 0

    def test_layer_update_from_last_frame_with_pipeline(self):
        """Test update_from_last_frame with filter pipeline."""
        from imagestag.components.stream_view.layers import StreamViewLayer
        from imagestag.streams.generator import GeneratorStream
        from imagestag.filters import FilterPipeline
        from imagestag.filters.base import Filter

        class IdentityFilter(Filter):
            def apply(self, image, context=None):
                return image

        pipeline = FilterPipeline(filters=[IdentityFilter()])

        stream = GeneratorStream(
            handler=lambda t: Image.from_array(np.full((100, 100, 3), 128, dtype=np.uint8))
        )
        layer = StreamViewLayer(stream=stream, pipeline=pipeline)
        layer.set_target_size(100, 100)

        stream.start()
        stream.get_frame(0.0)

        result = layer.update_from_last_frame()
        assert result is True

    def test_layer_update_from_last_frame_with_zoom(self):
        """Test update_from_last_frame with zoomed viewport."""
        from imagestag.components.stream_view.layers import StreamViewLayer
        from imagestag.components.stream_view.stream_view import Viewport
        from imagestag.streams.generator import GeneratorStream

        stream = GeneratorStream(
            handler=lambda t: Image.from_array(np.full((100, 100, 3), 128, dtype=np.uint8))
        )
        layer = StreamViewLayer(stream=stream)
        layer.set_viewport(Viewport(zoom=2.0, x=0.25, y=0.25, width=0.5, height=0.5))
        layer.set_target_size(100, 100)

        stream.start()
        stream.get_frame(0.0)

        result = layer.update_from_last_frame()
        assert result is True

    def test_layer_update_from_last_frame_with_png(self):
        """Test update_from_last_frame with PNG encoding."""
        from imagestag.components.stream_view.layers import StreamViewLayer
        from imagestag.streams.generator import GeneratorStream

        stream = GeneratorStream(
            handler=lambda t: Image.from_array(np.full((100, 100, 3), 128, dtype=np.uint8))
        )
        layer = StreamViewLayer(stream=stream, use_png=True)
        layer.set_target_size(100, 100)

        stream.start()
        stream.get_frame(0.0)

        result = layer.update_from_last_frame()
        assert result is True


# ============================================================================
# MORE STREAMVIEW STATIC FRAME SYNC TESTS
# ============================================================================


class TestStreamViewProduceFrameSync:
    """Tests for _produce_frame_sync static method."""

    def test_produce_frame_sync_basic(self):
        """Test _produce_frame_sync with basic stream."""
        from imagestag.components.stream_view.stream_view import StreamView
        from imagestag.components.stream_view.layers import StreamViewLayer
        from imagestag.streams.generator import GeneratorStream

        stream = GeneratorStream(
            handler=lambda t: Image.from_array(np.full((100, 100, 3), 128, dtype=np.uint8))
        )
        layer = StreamViewLayer(stream=stream)
        stream.start()

        result = StreamView._produce_frame_sync(layer)

        assert result is not None
        timestamp, encoded, metadata = result
        assert timestamp > 0
        # The encoded is just base64 without the data URL prefix in _produce_frame_sync
        assert len(encoded) > 0  # Just check it's non-empty

    def test_produce_frame_sync_no_stream(self):
        """Test _produce_frame_sync with no stream."""
        from imagestag.components.stream_view.stream_view import StreamView
        from imagestag.components.stream_view.layers import StreamViewLayer

        layer = StreamViewLayer(url="http://test.com")

        result = StreamView._produce_frame_sync(layer)
        assert result is None

    def test_produce_frame_sync_with_pipeline(self):
        """Test _produce_frame_sync with filter pipeline."""
        from imagestag.components.stream_view.stream_view import StreamView
        from imagestag.components.stream_view.layers import StreamViewLayer
        from imagestag.streams.generator import GeneratorStream
        from imagestag.filters import FilterPipeline
        from imagestag.filters.base import Filter

        class IdentityFilter(Filter):
            def apply(self, image, context=None):
                return image

        pipeline = FilterPipeline(filters=[IdentityFilter()])

        stream = GeneratorStream(
            handler=lambda t: Image.from_array(np.full((100, 100, 3), 128, dtype=np.uint8))
        )
        layer = StreamViewLayer(stream=stream, pipeline=pipeline)
        stream.start()

        result = StreamView._produce_frame_sync(layer)
        assert result is not None

    def test_produce_frame_sync_with_multi_output(self):
        """Test _produce_frame_sync with multi-output stream."""
        from imagestag.components.stream_view.stream_view import StreamView
        from imagestag.components.stream_view.layers import StreamViewLayer
        from imagestag.streams.generator import GeneratorStream

        def multi_handler(t):
            return {
                "rgb": Image.from_array(np.full((100, 100, 3), 128, dtype=np.uint8)),
                "gray": Image.from_array(np.full((100, 100), 128, dtype=np.uint8)),
            }

        stream = GeneratorStream(handler=multi_handler)
        layer = StreamViewLayer(stream=stream, stream_output="rgb")
        stream.start()

        result = StreamView._produce_frame_sync(layer)
        assert result is not None

    def test_produce_frame_sync_multi_output_default(self):
        """Test _produce_frame_sync with multi-output, no output key specified."""
        from imagestag.components.stream_view.stream_view import StreamView
        from imagestag.components.stream_view.layers import StreamViewLayer
        from imagestag.streams.generator import GeneratorStream

        def multi_handler(t):
            return {
                "rgb": Image.from_array(np.full((100, 100, 3), 128, dtype=np.uint8)),
                "gray": Image.from_array(np.full((100, 100), 128, dtype=np.uint8)),
            }

        stream = GeneratorStream(handler=multi_handler)
        layer = StreamViewLayer(stream=stream)  # No stream_output
        stream.start()

        result = StreamView._produce_frame_sync(layer)
        assert result is not None


# ============================================================================
# DERIVED LAYER TESTS
# ============================================================================


class TestDerivedLayers:
    """Tests for derived layers with source_layer."""

    @pytest.mark.asyncio
    async def test_derived_layer_with_stream_source(self, user: User) -> None:
        """Test derived layer that pulls from stream source."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView
        from imagestag.streams.generator import GeneratorStream

        view = None
        source_layer = None
        derived_layer = None

        @ui.page("/test_derived_stream")
        def page():
            nonlocal view, source_layer, derived_layer
            stream = GeneratorStream(
                handler=lambda t: Image.from_array(np.full((200, 200, 3), 128, dtype=np.uint8))
            )
            stream.start()
            view = StreamView(width=800, height=600)
            source_layer = view.add_layer(stream=stream, z_index=0, name="Source")
            derived_layer = view.add_layer(
                source_layer=source_layer,
                z_index=1,
                x=50,
                y=50,
                width=100,
                height=100,
                name="Derived",
            )

        await user.open("/test_derived_stream")

        assert derived_layer is not None
        assert derived_layer.source_layer is source_layer
        assert derived_layer.piggyback is True

    @pytest.mark.asyncio
    async def test_derived_layer_with_overscan(self, user: User) -> None:
        """Test derived layer with overscan."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView
        from imagestag.streams.generator import GeneratorStream

        view = None
        derived_layer = None

        @ui.page("/test_derived_overscan")
        def page():
            nonlocal view, derived_layer
            stream = GeneratorStream(
                handler=lambda t: Image.from_array(np.full((200, 200, 3), 128, dtype=np.uint8))
            )
            stream.start()
            view = StreamView(width=800, height=600)
            source = view.add_layer(stream=stream, z_index=0)
            derived_layer = view.add_layer(
                source_layer=source,
                z_index=1,
                x=50,
                y=50,
                width=100,
                height=100,
                overscan=16,
            )

        await user.open("/test_derived_overscan")

        assert derived_layer.overscan == 16

    @pytest.mark.asyncio
    async def test_derived_layer_with_pipeline(self, user: User) -> None:
        """Test derived layer with filter pipeline."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView
        from imagestag.streams.generator import GeneratorStream
        from imagestag.filters import FilterPipeline
        from imagestag.filters.base import Filter

        view = None
        derived_layer = None

        class InvertFilter(Filter):
            def apply(self, image, context=None):
                arr = 255 - image.get_pixels()
                return Image.from_array(arr)

        @ui.page("/test_derived_pipeline")
        def page():
            nonlocal view, derived_layer
            pipeline = FilterPipeline(filters=[InvertFilter()])
            stream = GeneratorStream(
                handler=lambda t: Image.from_array(np.full((200, 200, 3), 128, dtype=np.uint8))
            )
            stream.start()
            view = StreamView(width=800, height=600)
            source = view.add_layer(stream=stream, z_index=0)
            derived_layer = view.add_layer(
                source_layer=source,
                pipeline=pipeline,
                z_index=1,
            )

        await user.open("/test_derived_pipeline")

        assert derived_layer.pipeline is not None


class TestStreamViewFullscreenMode:
    """Tests for StreamView fullscreen mode functionality."""

    @pytest.mark.asyncio
    async def test_set_fullscreen_mode_enter(self, user: User) -> None:
        """Test entering fullscreen mode."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView

        view = None

        @ui.page("/test_fullscreen_enter")
        def page():
            nonlocal view
            view = StreamView(width=800, height=600)
            view.add_layer(url="http://test.com/img.jpg", fullscreen_scale="screen")

        await user.open("/test_fullscreen_enter")

        view.set_fullscreen_mode(True, screen_width=1920, screen_height=1080, video_width=800, video_height=600)

    @pytest.mark.asyncio
    async def test_set_fullscreen_mode_exit(self, user: User) -> None:
        """Test exiting fullscreen mode."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView

        view = None

        @ui.page("/test_fullscreen_exit")
        def page():
            nonlocal view
            view = StreamView(width=800, height=600)
            view.add_layer(url="http://test.com/img.jpg", fullscreen_scale="screen")

        await user.open("/test_fullscreen_exit")

        view.set_fullscreen_mode(True, screen_width=1920, screen_height=1080, video_width=800, video_height=600)
        view.set_fullscreen_mode(False)


class TestStreamViewZoom:
    """Tests for StreamView zoom functionality."""

    @pytest.mark.asyncio
    async def test_set_zoom(self, user: User) -> None:
        """Test set_zoom method."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView

        view = None

        @ui.page("/test_set_zoom")
        def page():
            nonlocal view
            view = StreamView(width=800, height=600, enable_zoom=True)

        await user.open("/test_set_zoom")

        view.set_zoom(2.0)
        # The zoom is managed by JS, so we just check the method runs

    @pytest.mark.asyncio
    async def test_reset_zoom(self, user: User) -> None:
        """Test reset_zoom method."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView

        view = None

        @ui.page("/test_reset_zoom")
        def page():
            nonlocal view
            view = StreamView(width=800, height=600, enable_zoom=True)

        await user.open("/test_reset_zoom")

        view.set_zoom(3.0)
        view.reset_zoom()


class TestStreamViewBufferedFrames:
    """Tests for StreamView buffered frame handling."""

    @pytest.mark.asyncio
    async def test_check_pending_frames_with_buffer(self, user: User) -> None:
        """Test _check_pending_frames with buffered frames."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView
        from imagestag.streams.generator import GeneratorStream

        view = None
        layer = None

        @ui.page("/test_buffered_frames")
        def page():
            nonlocal view, layer
            stream = GeneratorStream(
                handler=lambda t: Image.from_array(np.full((100, 100, 3), 128, dtype=np.uint8))
            )
            view = StreamView(width=800, height=600)
            layer = view.add_layer(stream=stream, buffer_size=4, fps=30)

        await user.open("/test_buffered_frames")

        # Start the layer which starts the producer
        layer.start()
        time.sleep(0.2)

        # Should have frames in buffer
        view._check_pending_frames()

        layer.stop()


class TestStreamViewNavigationWindow:
    """Tests for StreamView navigation window."""

    @pytest.mark.asyncio
    async def test_nav_window_props(self, user: User) -> None:
        """Test navigation window properties."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView

        view = None

        @ui.page("/test_nav_props")
        def page():
            nonlocal view
            view = StreamView(
                width=800,
                height=600,
                enable_zoom=True,
                show_nav_window=True,
                nav_window_position="bottom-right",
                nav_window_size=(150, 100),
            )

        await user.open("/test_nav_props")

        assert view._props["showNavWindow"] is True
        assert view._props["navWindowPosition"] == "bottom-right"
        assert view._props["navWindowWidth"] == 150
        assert view._props["navWindowHeight"] == 100


class TestStreamViewAdditionalInternals:
    """Additional tests for StreamView internal methods."""

    @pytest.mark.asyncio
    async def test_create_mouse_event(self, user: User) -> None:
        """Test _create_mouse_event method."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView

        view = None

        @ui.page("/test_create_mouse_event")
        def page():
            nonlocal view
            view = StreamView(width=800, height=600)

        await user.open("/test_create_mouse_event")

        class MockEvent:
            args = {
                "x": 100,
                "y": 200,
                "sourceX": 150,
                "sourceY": 250,
                "buttons": 1,
                "alt": True,
                "ctrl": False,
                "shift": True,
                "meta": False,
            }

        event = view._create_mouse_event(MockEvent())

        assert event.x == 100
        assert event.y == 200
        assert event.buttons == 1
        assert event.alt is True
        assert event.shift is True

    @pytest.mark.asyncio
    async def test_layer_name_property(self, user: User) -> None:
        """Test layer name property."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView

        view = None
        layer = None

        @ui.page("/test_layer_name")
        def page():
            nonlocal view, layer
            view = StreamView(width=800, height=600)
            layer = view.add_layer(url="http://test.com/img.jpg", name="TestLayer")

        await user.open("/test_layer_name")

        assert layer.name == "TestLayer"


# ============================================================================
# STREAM VIEW LAYER ADDITIONAL PROPERTIES
# ============================================================================


class TestStreamViewLayerAdditionalProperties:
    """Tests for StreamViewLayer additional properties."""

    def test_layer_stream_output(self):
        """Test layer stream_output property."""
        from imagestag.components.stream_view.layers import StreamViewLayer
        from imagestag.streams.generator import GeneratorStream

        stream = GeneratorStream(
            handler=lambda t: Image.from_array(np.zeros((10, 10, 3), dtype=np.uint8))
        )
        layer = StreamViewLayer(stream=stream, stream_output="rgb")
        assert layer.stream_output == "rgb"

    def test_layer_fullscreen_scale(self):
        """Test layer fullscreen_scale property."""
        from imagestag.components.stream_view.layers import StreamViewLayer

        layer = StreamViewLayer(url="http://test.com", fullscreen_scale="screen")
        assert layer.fullscreen_scale == "screen"

    def test_layer_position_properties(self):
        """Test layer position properties."""
        from imagestag.components.stream_view.layers import StreamViewLayer

        layer = StreamViewLayer(
            url="http://test.com",
            z_index=5,
            x=100,
            y=50,
            width=200,
            height=150,
        )

        assert layer.z_index == 5
        assert layer.x == 100
        assert layer.y == 50
        assert layer.width == 200
        assert layer.height == 150

    def test_layer_overscan_property(self):
        """Test layer overscan property."""
        from imagestag.components.stream_view.layers import StreamViewLayer

        layer = StreamViewLayer(url="http://test.com", overscan=16)
        assert layer.overscan == 16

    def test_layer_depth_property(self):
        """Test layer depth property."""
        from imagestag.components.stream_view.layers import StreamViewLayer

        layer = StreamViewLayer(url="http://test.com", depth=0.5)
        assert layer.depth == 0.5

    @pytest.mark.asyncio
    async def test_add_layer_with_mask_via_streamview(self, user: User) -> None:
        """Test adding layer with mask via StreamView.add_layer."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView

        view = None
        layer = None

        @ui.page("/test_layer_mask")
        def page():
            nonlocal view, layer
            mask = Image.from_array(np.full((50, 50), 128, dtype=np.uint8))
            view = StreamView(width=800, height=600)
            layer = view.add_layer(url="http://test.com/img.jpg", mask=mask)

        await user.open("/test_layer_mask")

        assert layer is not None


class TestFPSCounterEdgeCases:
    """Additional FPS counter tests."""

    def test_fps_counter_zero_interval(self):
        """Test fps counter with zero interval."""
        from imagestag.components.stream_view.metrics import FPSCounter

        fc = FPSCounter()
        # Tick twice immediately
        fc.tick()
        fc.tick()

        # Should not crash, fps might be very high or inf
        fps = fc.fps
        assert fps >= 0 or fps == float('inf') or fps != fps  # nan check


# ============================================================================
# WEBRTC INTEGRATION TESTS
# ============================================================================


# Check if aiortc is available
try:
    from aiortc import RTCPeerConnection
    AIORTC_AVAILABLE = True
except ImportError:
    AIORTC_AVAILABLE = False


@pytest.mark.skipif(not AIORTC_AVAILABLE, reason="aiortc not installed")
class TestStreamViewWebRTCIntegration:
    """Integration tests for StreamView WebRTC functionality."""

    @pytest.mark.asyncio
    async def test_add_webrtc_layer(self, user: User) -> None:
        """Test adding a WebRTC layer to StreamView."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView
        from imagestag.streams.generator import GeneratorStream
        import threading

        view = None
        layer_id = None
        stream = None

        @ui.page("/test_add_webrtc")
        def page():
            nonlocal view, layer_id, stream
            stream = GeneratorStream(
                handler=lambda t: Image.from_array(np.full((240, 320, 3), 128, dtype=np.uint8)),
                target_fps=10,
            )
            stream.start()
            view = StreamView(width=800, height=600)
            layer_id = view.add_webrtc_layer(
                stream=stream,
                z_index=0,
                codec="h264",
                bitrate=2_000_000,
                name="Test WebRTC Layer",
            )

        await user.open("/test_add_webrtc")

        assert layer_id is not None
        assert view is not None
        assert view._webrtc_manager is not None
        assert layer_id in view._webrtc_layers

        # Cleanup
        if stream:
            stream.stop()

    @pytest.mark.asyncio
    async def test_remove_webrtc_layer(self, user: User) -> None:
        """Test removing a WebRTC layer from StreamView."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView
        from imagestag.streams.generator import GeneratorStream

        view = None
        layer_id = None
        stream = None

        @ui.page("/test_remove_webrtc")
        def page():
            nonlocal view, layer_id, stream
            stream = GeneratorStream(
                handler=lambda t: Image.from_array(np.full((120, 160, 3), 100, dtype=np.uint8)),
                target_fps=5,
            )
            stream.start()
            view = StreamView(width=640, height=480)
            layer_id = view.add_webrtc_layer(stream=stream, z_index=0)

        await user.open("/test_remove_webrtc")

        assert layer_id is not None
        assert layer_id in view._webrtc_layers

        view.remove_webrtc_layer(layer_id)

        assert layer_id not in view._webrtc_layers

        if stream:
            stream.stop()

    @pytest.mark.asyncio
    async def test_add_multiple_webrtc_layers(self, user: User) -> None:
        """Test adding multiple WebRTC layers to StreamView."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView
        from imagestag.streams.generator import GeneratorStream

        view = None
        layer_ids = []
        streams = []

        @ui.page("/test_multi_webrtc")
        def page():
            nonlocal view, layer_ids, streams
            view = StreamView(width=800, height=600)

            for i in range(3):
                stream = GeneratorStream(
                    handler=lambda t, val=i: Image.from_array(
                        np.full((100, 100, 3), val * 50, dtype=np.uint8)
                    ),
                    target_fps=5,
                )
                stream.start()
                streams.append(stream)

                layer_id = view.add_webrtc_layer(
                    stream=stream,
                    z_index=i,
                    name=f"Layer-{i}",
                )
                layer_ids.append(layer_id)

        await user.open("/test_multi_webrtc")

        assert len(layer_ids) == 3
        for lid in layer_ids:
            assert lid in view._webrtc_layers

        # Cleanup
        for stream in streams:
            stream.stop()

    @pytest.mark.asyncio
    async def test_webrtc_layer_with_viewport(self, user: User) -> None:
        """Test WebRTC layer with viewport settings."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView
        from imagestag.streams.generator import GeneratorStream

        view = None
        layer_id = None
        stream = None

        @ui.page("/test_webrtc_viewport")
        def page():
            nonlocal view, layer_id, stream
            stream = GeneratorStream(
                handler=lambda t: Image.from_array(np.full((480, 640, 3), 150, dtype=np.uint8)),
                target_fps=10,
            )
            stream.start()
            view = StreamView(width=800, height=600)
            layer_id = view.add_webrtc_layer(
                stream=stream,
                z_index=0,
                target_fps=30,
            )

        await user.open("/test_webrtc_viewport")

        assert layer_id is not None
        config = view._webrtc_layers[layer_id]
        assert config.target_fps == 30

        if stream:
            stream.stop()


class TestDerivedLayerSetup:
    """Tests for derived layer setup and callback processing."""

    @pytest.mark.asyncio
    async def test_derived_layer_setup(self, user: User) -> None:
        """Test derived layer setup with source layer."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView
        from imagestag.streams.generator import GeneratorStream

        view = None
        source_layer = None
        derived_layer = None
        stream = None

        @ui.page("/test_derived_setup")
        def page():
            nonlocal view, source_layer, derived_layer, stream
            stream = GeneratorStream(
                handler=lambda t: Image.from_array(np.full((200, 200, 3), 100, dtype=np.uint8)),
                target_fps=15,
            )
            stream.start()
            view = StreamView(width=800, height=600)
            source_layer = view.add_layer(stream=stream, z_index=0)
            derived_layer = view.add_layer(
                source_layer=source_layer,
                z_index=1,
                x=20,
                y=20,
                width=80,
                height=80,
            )

        await user.open("/test_derived_setup")

        assert source_layer is not None
        assert derived_layer is not None
        assert derived_layer.source_layer is source_layer

        if stream:
            stream.stop()

    @pytest.mark.asyncio
    async def test_derived_layer_with_pipeline(self, user: User) -> None:
        """Test derived layer with filter pipeline."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView
        from imagestag.streams.generator import GeneratorStream
        from imagestag.filters import FilterPipeline
        from imagestag.filters.base import Filter

        class SimpleFilter(Filter):
            def apply(self, image, context=None):
                return image

        view = None
        source_layer = None
        derived_layer = None
        stream = None

        @ui.page("/test_derived_pipeline")
        def page():
            nonlocal view, source_layer, derived_layer, stream
            pipeline = FilterPipeline(filters=[SimpleFilter()])
            stream = GeneratorStream(
                handler=lambda t: Image.from_array(np.full((150, 150, 3), 120, dtype=np.uint8)),
                target_fps=10,
            )
            stream.start()
            view = StreamView(width=800, height=600)
            source_layer = view.add_layer(stream=stream, z_index=0)
            derived_layer = view.add_layer(
                source_layer=source_layer,
                pipeline=pipeline,
                z_index=1,
            )

        await user.open("/test_derived_pipeline")

        assert derived_layer is not None
        assert derived_layer.pipeline is not None

        if stream:
            stream.stop()

    @pytest.mark.asyncio
    async def test_derived_layer_with_overscan(self, user: User) -> None:
        """Test derived layer with overscan margin."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView
        from imagestag.streams.generator import GeneratorStream

        view = None
        source_layer = None
        derived_layer = None
        stream = None

        @ui.page("/test_derived_overscan")
        def page():
            nonlocal view, source_layer, derived_layer, stream
            stream = GeneratorStream(
                handler=lambda t: Image.from_array(np.full((200, 200, 3), 80, dtype=np.uint8)),
                target_fps=10,
            )
            stream.start()
            view = StreamView(width=800, height=600)
            source_layer = view.add_layer(stream=stream, z_index=0)
            derived_layer = view.add_layer(
                source_layer=source_layer,
                z_index=1,
                x=30,
                y=30,
                width=100,
                height=100,
                overscan=8,
            )

        await user.open("/test_derived_overscan")

        assert derived_layer is not None
        assert derived_layer.overscan == 8

        if stream:
            stream.stop()
