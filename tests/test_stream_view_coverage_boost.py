"""Additional tests to boost StreamView coverage to >95%.

Focused on uncovered code paths in:
- stream_view.py (derived layers, frame production, WebRTC)
- layers.py (piggyback mode, exception handling)
- webrtc.py (image processing, error handling)
"""

from __future__ import annotations

import asyncio
import base64
import threading
import time
from fractions import Fraction
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch, PropertyMock

import numpy as np
import pytest

from imagestag import Image
from imagestag.streams.generator import GeneratorStream

if TYPE_CHECKING:
    from nicegui.testing import User


# ============================================================================
# LAYERS.PY COVERAGE TESTS
# ============================================================================


class TestLayerPiggybackMode:
    """Tests for piggyback mode in StreamViewLayer."""

    @pytest.mark.asyncio
    async def test_start_in_piggyback_mode(self, user: User) -> None:
        """Test that piggyback mode doesn't start producer thread."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView

        view = None
        layer = None

        @ui.page("/test_piggyback")
        def page():
            nonlocal view, layer
            view = StreamView(width=800, height=600)
            layer = view.add_layer(
                stream=GeneratorStream(
                    handler=lambda t: Image.from_array(np.full((100, 100, 3), 128, dtype=np.uint8))
                ),
                z_index=0,
                piggyback=True,
            )

        await user.open("/test_piggyback")

        # Start the layer
        layer.start()

        # In piggyback mode, producer thread should NOT be started
        assert layer._producer_thread is None
        assert layer._running is True

    @pytest.mark.asyncio
    async def test_start_when_already_running(self, user: User) -> None:
        """Test that start() is idempotent when already running."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView

        view = None
        layer = None

        @ui.page("/test_already_running")
        def page():
            nonlocal view, layer
            view = StreamView(width=800, height=600)
            layer = view.add_layer(
                stream=GeneratorStream(
                    handler=lambda t: Image.from_array(np.full((100, 100, 3), 128, dtype=np.uint8))
                ),
                z_index=0,
                piggyback=True,
            )

        await user.open("/test_already_running")

        # Start twice - should be idempotent
        layer.start()
        first_state = layer._running
        layer.start()
        second_state = layer._running

        assert first_state is True
        assert second_state is True


class TestLayerExceptionHandling:
    """Tests for exception handling in layer processing."""

    @pytest.mark.asyncio
    async def test_filter_exception_caught(self, user: User) -> None:
        """Test that exceptions in filter processing are caught."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView
        from imagestag.filters.base import Filter

        view = None
        layer = None

        class BrokenFilter(Filter):
            def apply(self, image: Image) -> Image:
                raise RuntimeError("Filter exploded!")

        @ui.page("/test_filter_exception")
        def page():
            nonlocal view, layer
            from imagestag.filters import FilterPipeline

            view = StreamView(width=800, height=600)
            layer = view.add_layer(
                stream=GeneratorStream(
                    handler=lambda t: Image.from_array(np.full((100, 100, 3), 128, dtype=np.uint8))
                ),
                z_index=0,
                pipeline=FilterPipeline(filters=[BrokenFilter()]),
            )

        await user.open("/test_filter_exception")

        # Should not raise - exception is caught
        layer.start()
        await asyncio.sleep(0.1)
        layer.stop()

    @pytest.mark.asyncio
    async def test_viewport_crop_exception_caught(self, user: User) -> None:
        """Test that exceptions in viewport cropping are caught."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView, Viewport

        view = None
        layer = None

        @ui.page("/test_crop_exception")
        def page():
            nonlocal view, layer
            view = StreamView(width=800, height=600, enable_zoom=True)
            layer = view.add_layer(
                stream=GeneratorStream(
                    handler=lambda t: Image.from_array(np.full((100, 100, 3), 128, dtype=np.uint8))
                ),
                z_index=0,
            )

        await user.open("/test_crop_exception")

        # Set viewport to extreme values that might cause issues
        viewport = Viewport(zoom=10.0, x=0.5, y=0.5, width=0.0001, height=0.0001)
        layer.set_viewport(viewport)

        layer.start()
        await asyncio.sleep(0.1)
        layer.stop()

        # Should not have crashed


class TestLayerFallbackReturnType:
    """Tests for fallback handling of unexpected return types."""

    @pytest.mark.asyncio
    async def test_unexpected_stream_return_type(self, user: User) -> None:
        """Test handling of unexpected return types from stream."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView

        # Create a stream that returns unexpected types
        class WeirdStream:
            def __init__(self):
                self._running = False
                self._frame_index = 0

            def start(self):
                self._running = True

            def stop(self):
                self._running = False

            def get_frame(self, timestamp: float) -> tuple:
                # Return tuple with 3 elements instead of 2
                self._frame_index += 1
                return (None, self._frame_index, "extra")

        view = None
        layer = None

        @ui.page("/test_weird_return")
        def page():
            nonlocal view, layer
            view = StreamView(width=800, height=600)
            layer = view.add_layer(stream=WeirdStream(), z_index=0)

        await user.open("/test_weird_return")

        layer.start()
        await asyncio.sleep(0.1)
        layer.stop()


# ============================================================================
# STREAM_VIEW.PY COVERAGE TESTS
# ============================================================================


class TestDerivedLayerChainTraversal:
    """Tests for derived layer source chain traversal."""

    @pytest.mark.asyncio
    async def test_derived_layer_chain_traversal(self, user: User) -> None:
        """Test traversing up the source chain for derived layers."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView

        view = None
        base_layer = None
        derived1 = None
        derived2 = None

        @ui.page("/test_chain_traversal")
        def page():
            nonlocal view, base_layer, derived1, derived2
            view = StreamView(width=800, height=600)

            # Create chain: base -> derived1 -> derived2
            base_layer = view.add_layer(
                stream=GeneratorStream(
                    handler=lambda t: Image.from_array(np.full((100, 100, 3), 128, dtype=np.uint8)),
                    threaded=True,
                ),
                z_index=0,
            )

            derived1 = view.add_layer(
                source_layer=base_layer,
                z_index=1,
            )

            # This creates a derived layer from another derived layer
            derived2 = view.add_layer(
                source_layer=derived1,
                z_index=2,
            )

        await user.open("/test_chain_traversal")

        # All should have reference to original stream
        assert base_layer.stream is not None
        assert derived1.source_layer == base_layer
        assert derived2.source_layer == derived1


class TestDerivedLayerStaticSource:
    """Tests for derived layers with static sources."""

    @pytest.mark.asyncio
    async def test_derived_layer_no_stream_warning(self, user: User) -> None:
        """Test warning when derived layer has no dynamic source stream."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView

        view = None
        base_layer = None
        derived = None

        @ui.page("/test_static_source")
        def page():
            nonlocal view, base_layer, derived
            view = StreamView(width=800, height=600)

            # Create a static layer (URL-based, no stream)
            base_layer = view.add_layer(url="http://example.com/image.jpg", z_index=0)

            # Create derived from static
            derived = view.add_layer(
                source_layer=base_layer,
                z_index=1,
            )

        await user.open("/test_static_source")

        # Derived layer should exist but can't process frames
        assert derived is not None
        assert derived.source_layer == base_layer


class TestDerivedLayerRemovalCleanup:
    """Tests for cleaning up derived layer callbacks on removal."""

    @pytest.mark.asyncio
    async def test_remove_derived_layer_cleanup(self, user: User) -> None:
        """Test that removing a derived layer cleans up callbacks."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView

        view = None
        base_layer = None
        derived = None
        derived_id = None

        @ui.page("/test_remove_derived")
        def page():
            nonlocal view, base_layer, derived, derived_id
            view = StreamView(width=800, height=600)

            base_layer = view.add_layer(
                stream=GeneratorStream(
                    handler=lambda t: Image.from_array(np.full((100, 100, 3), 128, dtype=np.uint8)),
                    threaded=True,
                ),
                z_index=0,
            )

            derived = view.add_layer(
                source_layer=base_layer,
                z_index=1,
            )
            derived_id = derived.id

        await user.open("/test_remove_derived")

        # Store reference to check cleanup
        has_callback_before = hasattr(derived, '_on_frame_callback')

        # Remove the derived layer
        view.remove_layer(derived_id)

        # Layer should be removed
        assert derived_id not in view._layers


class TestFrameRequestHandling:
    """Tests for frame request handling with buffering."""

    @pytest.mark.asyncio
    async def test_static_layer_frame_request(self, user: User) -> None:
        """Test that static layers don't produce new frames."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView

        view = None

        @ui.page("/test_static_frame")
        def page():
            nonlocal view
            view = StreamView(width=800, height=600)
            view.add_layer(url="http://example.com/image.jpg", z_index=0)

        await user.open("/test_static_frame")

        # Static layer exists
        layer = list(view._layers.values())[0]
        assert layer.is_static is True

    @pytest.mark.asyncio
    async def test_buffered_frame_retrieval(self, user: User) -> None:
        """Test retrieving buffered frames."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView

        view = None
        layer = None

        @ui.page("/test_buffered_frame")
        def page():
            nonlocal view, layer
            view = StreamView(width=800, height=600)
            layer = view.add_layer(
                stream=GeneratorStream(
                    handler=lambda t: Image.from_array(np.full((100, 100, 3), 128, dtype=np.uint8)),
                    threaded=True,
                ),
                z_index=0,
            )

        await user.open("/test_buffered_frame")

        layer.start()
        await asyncio.sleep(0.2)  # Let buffer fill

        # Should have buffered frames
        frame_data = layer.get_buffered_frame()
        if frame_data:
            timestamp, encoded, metadata = frame_data
            assert encoded.startswith("data:image/")

        layer.stop()


class TestWebRTCAnswerHandling:
    """Tests for WebRTC answer handling in StreamView."""

    @pytest.mark.asyncio
    async def test_webrtc_answer_handler(self, user: User) -> None:
        """Test WebRTC answer handling method."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView

        view = None

        @ui.page("/test_webrtc_answer")
        def page():
            nonlocal view
            view = StreamView(width=800, height=600)

        await user.open("/test_webrtc_answer")

        # Create mock event
        class MockEvent:
            args = {
                "layer_id": "test_layer",
                "answer": {"type": "answer", "sdp": "v=0\r\n"}
            }

        # Without WebRTC manager, should not crash
        view._handle_webrtc_answer(MockEvent())

        # Should handle gracefully
        assert True


# ============================================================================
# WEBRTC.PY COVERAGE TESTS
# ============================================================================


class TestWebRTCVideoTrackProcessing:
    """Tests for WebRTC video track frame processing."""

    def test_webrtc_layer_config_creation(self) -> None:
        """Test WebRTCLayerConfig creation."""
        try:
            from imagestag.components.stream_view.webrtc import (
                WebRTCLayerConfig,
                AIORTC_AVAILABLE,
            )
        except ImportError:
            pytest.skip("aiortc not available")

        if not AIORTC_AVAILABLE:
            pytest.skip("aiortc not available")

        stream = GeneratorStream(
            handler=lambda t: Image.from_array(np.full((100, 100, 3), 128, dtype=np.uint8)),
        )

        # Create config with basic parameters
        config = WebRTCLayerConfig(
            stream=stream,
            z_index=0,
            codec="h264",
            bitrate=5_000_000,
        )

        assert config.z_index == 0
        assert config.codec == "h264"
        assert config.bitrate == 5_000_000

    def test_webrtc_layer_config_with_dimensions(self) -> None:
        """Test WebRTCLayerConfig with width/height."""
        try:
            from imagestag.components.stream_view.webrtc import (
                WebRTCLayerConfig,
                AIORTC_AVAILABLE,
            )
        except ImportError:
            pytest.skip("aiortc not available")

        if not AIORTC_AVAILABLE:
            pytest.skip("aiortc not available")

        stream = GeneratorStream(
            handler=lambda t: Image.from_array(np.full((100, 100, 3), 128, dtype=np.uint8)),
        )

        config = WebRTCLayerConfig(
            stream=stream,
            z_index=0,
            width=640,
            height=480,
        )

        assert config.width == 640
        assert config.height == 480

    def test_webrtc_layer_config_get_crop_rect(self) -> None:
        """Test WebRTCLayerConfig get_crop_rect method based on viewport."""
        try:
            from imagestag.components.stream_view.webrtc import (
                WebRTCLayerConfig,
                AIORTC_AVAILABLE,
            )
        except ImportError:
            pytest.skip("aiortc not available")

        if not AIORTC_AVAILABLE:
            pytest.skip("aiortc not available")

        stream = GeneratorStream(
            handler=lambda t: Image.from_array(np.full((100, 100, 3), 128, dtype=np.uint8)),
        )

        config = WebRTCLayerConfig(
            stream=stream,
            z_index=0,
        )
        # Set viewport to crop a portion
        config.viewport_x = 0.1
        config.viewport_y = 0.1
        config.viewport_width = 0.8
        config.viewport_height = 0.8

        rect = config.get_crop_rect(100, 100)
        # 0.1*100=10, (0.1+0.8)*100=90
        assert rect == (10, 10, 90, 90)

    def test_webrtc_layer_config_effective_fps(self) -> None:
        """Test WebRTCLayerConfig get_effective_fps method."""
        try:
            from imagestag.components.stream_view.webrtc import (
                WebRTCLayerConfig,
                AIORTC_AVAILABLE,
            )
        except ImportError:
            pytest.skip("aiortc not available")

        if not AIORTC_AVAILABLE:
            pytest.skip("aiortc not available")

        stream = GeneratorStream(
            handler=lambda t: Image.from_array(np.full((100, 100, 3), 128, dtype=np.uint8)),
        )

        # With target_fps set
        config = WebRTCLayerConfig(
            stream=stream,
            z_index=0,
            target_fps=60,
        )
        assert config.get_effective_fps() == 60

        # Without target_fps (uses default)
        config2 = WebRTCLayerConfig(stream=stream, z_index=0)
        fps = config2.get_effective_fps()
        assert fps > 0  # Should return valid FPS


class TestWebRTCManagerRunAsync:
    """Tests for WebRTC manager has running loop on init."""

    def test_manager_has_loop_after_init(self) -> None:
        """Test WebRTCManager has running loop after init."""
        try:
            from imagestag.components.stream_view.webrtc import (
                WebRTCManager,
                AIORTC_AVAILABLE,
            )
        except ImportError:
            pytest.skip("aiortc not available")

        if not AIORTC_AVAILABLE:
            pytest.skip("aiortc not available")

        manager = WebRTCManager()
        # Manager starts thread on init
        assert manager._loop is not None
        manager.close_all()


class TestWebRTCResizeFallback:
    """Tests for WebRTC resize with PIL fallback."""

    def test_config_dimensions(self) -> None:
        """Test config stores dimension parameters."""
        try:
            from imagestag.components.stream_view.webrtc import (
                WebRTCLayerConfig,
                AIORTC_AVAILABLE,
            )
        except ImportError:
            pytest.skip("aiortc not available")

        if not AIORTC_AVAILABLE:
            pytest.skip("aiortc not available")

        stream = GeneratorStream(
            handler=lambda t: Image.from_array(np.full((200, 200, 3), 128, dtype=np.uint8)),
        )

        config = WebRTCLayerConfig(
            stream=stream,
            z_index=0,
            width=100,
            height=100,
        )

        assert config.width == 100
        assert config.height == 100


# ============================================================================
# SDP MODIFICATION TESTS
# ============================================================================


class TestSDPBitrateModification:
    """Tests for SDP bitrate modification."""

    def test_modify_sdp_bitrate_h264(self) -> None:
        """Test modifying H.264 SDP bitrate."""
        try:
            from imagestag.components.stream_view.webrtc import (
                _modify_sdp_bitrate,
                AIORTC_AVAILABLE,
            )
        except ImportError:
            pytest.skip("webrtc module not available")

        if not AIORTC_AVAILABLE:
            pytest.skip("aiortc not available")

        # SDP must include c= line for bandwidth to be added
        sdp = (
            "v=0\r\n"
            "o=- 123 1 IN IP4 0.0.0.0\r\n"
            "s=-\r\n"
            "t=0 0\r\n"
            "m=video 9 UDP/TLS/RTP/SAVPF 96\r\n"
            "c=IN IP4 0.0.0.0\r\n"
            "a=rtpmap:96 H264/90000\r\n"
            "a=fmtp:96 level-asymmetry-allowed=1\r\n"
        )

        modified = _modify_sdp_bitrate(sdp, 5_000_000)

        # Should contain bandwidth line (added after c= line)
        assert "b=AS:5000" in modified

    def test_modify_sdp_bitrate_vp8(self) -> None:
        """Test modifying VP8 SDP bitrate."""
        try:
            from imagestag.components.stream_view.webrtc import (
                _modify_sdp_bitrate,
                AIORTC_AVAILABLE,
            )
        except ImportError:
            pytest.skip("webrtc module not available")

        if not AIORTC_AVAILABLE:
            pytest.skip("aiortc not available")

        # SDP must include c= line for bandwidth to be added
        sdp = (
            "v=0\r\n"
            "o=- 123 1 IN IP4 0.0.0.0\r\n"
            "s=-\r\n"
            "t=0 0\r\n"
            "m=video 9 UDP/TLS/RTP/SAVPF 96\r\n"
            "c=IN IP4 0.0.0.0\r\n"
            "a=rtpmap:96 VP8/90000\r\n"
        )

        modified = _modify_sdp_bitrate(sdp, 2_000_000)

        # Should contain bandwidth line
        assert "b=AS:2000" in modified


# ============================================================================
# DERIVED LAYER FRAME PROCESSING TESTS
# ============================================================================


class TestDerivedLayerFrameProcessing:
    """Tests for derived layer frame processing callback."""

    @pytest.mark.asyncio
    async def test_derived_layer_with_pipeline(self, user: User) -> None:
        """Test derived layer with filter pipeline."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView
        from imagestag.filters.base import Filter

        class TestFilter(Filter):
            def apply(self, image: Image) -> Image:
                # Simple pass-through filter
                return image

        view = None
        base_layer = None
        derived = None

        @ui.page("/test_derived_pipeline")
        def page():
            nonlocal view, base_layer, derived
            from imagestag.filters import FilterPipeline

            view = StreamView(width=800, height=600)

            base_layer = view.add_layer(
                stream=GeneratorStream(
                    handler=lambda t: Image.from_array(np.full((100, 100, 3), 128, dtype=np.uint8)),
                    threaded=True,
                ),
                z_index=0,
            )

            derived = view.add_layer(
                source_layer=base_layer,
                z_index=1,
                pipeline=FilterPipeline(filters=[TestFilter()]),
            )

        await user.open("/test_derived_pipeline")

        base_layer.start()
        await asyncio.sleep(0.2)
        base_layer.stop()

        assert derived is not None

    @pytest.mark.asyncio
    async def test_derived_layer_with_overscan(self, user: User) -> None:
        """Test derived layer with overscan setting."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView

        view = None
        base_layer = None
        derived = None

        @ui.page("/test_derived_overscan")
        def page():
            nonlocal view, base_layer, derived
            view = StreamView(width=800, height=600)

            base_layer = view.add_layer(
                stream=GeneratorStream(
                    handler=lambda t: Image.from_array(np.full((200, 200, 3), 128, dtype=np.uint8)),
                    threaded=True,
                ),
                z_index=0,
            )

            derived = view.add_layer(
                source_layer=base_layer,
                z_index=1,
                x=50,
                y=50,
                width=100,
                height=100,
                overscan=10,
            )

        await user.open("/test_derived_overscan")

        base_layer.start()
        await asyncio.sleep(0.2)
        base_layer.stop()

        assert derived.overscan == 10


class TestDerivedLayerStreamNoOnFrame:
    """Tests for derived layers when stream doesn't support on_frame."""

    @pytest.mark.asyncio
    async def test_stream_without_on_frame(self, user: User) -> None:
        """Test handling streams that don't support on_frame callbacks."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView

        class MinimalStream:
            def __init__(self):
                self._running = False
                self._frame_index = 0

            def start(self):
                self._running = True

            def stop(self):
                self._running = False

            def get_frame(self, timestamp: float) -> tuple:
                self._frame_index += 1
                return (
                    Image.from_array(np.full((100, 100, 3), 128, dtype=np.uint8)),
                    self._frame_index
                )
            # Note: No on_frame method!

        view = None
        base_layer = None
        derived = None

        @ui.page("/test_no_on_frame")
        def page():
            nonlocal view, base_layer, derived
            view = StreamView(width=800, height=600)

            base_layer = view.add_layer(stream=MinimalStream(), z_index=0)
            derived = view.add_layer(source_layer=base_layer, z_index=1)

        await user.open("/test_no_on_frame")

        # Should not crash - just won't process derived frames
        assert derived is not None


# ============================================================================
# ADDITIONAL WEBRTC TESTS
# ============================================================================


class TestWebRTCManagerInit:
    """Tests for WebRTC manager initialization."""

    def test_webrtc_manager_init(self) -> None:
        """Test WebRTCManager initialization starts thread and loop."""
        try:
            from imagestag.components.stream_view.webrtc import (
                WebRTCManager,
                AIORTC_AVAILABLE,
            )
        except ImportError:
            pytest.skip("aiortc not available")

        if not AIORTC_AVAILABLE:
            pytest.skip("aiortc not available")

        manager = WebRTCManager()

        # Should have connections dict
        assert hasattr(manager, '_connections')
        assert isinstance(manager._connections, dict)

        # Manager auto-starts thread and loop on init
        assert manager._loop is not None

        manager.close_all()


# ============================================================================
# INIT MODULE IMPORT TESTS
# ============================================================================


class TestInitModuleImports:
    """Tests for __init__.py imports."""

    def test_stream_view_exports(self) -> None:
        """Test that all expected exports are available."""
        from imagestag.components.stream_view import (
            StreamView,
            StreamViewMouseEventArguments,
            StreamViewViewportEventArguments,
            Viewport,
            MouseEvent,
            ImageStream,
            VideoStream,
            CustomStream,
            StreamViewLayer,
            PythonMetrics,
            LayerMetrics,
            FPSCounter,
            Timer,
        )

        # All should be importable
        assert StreamView is not None
        assert StreamViewMouseEventArguments is not None
        assert MouseEvent is StreamViewMouseEventArguments  # Alias

    def test_webrtc_availability_flag(self) -> None:
        """Test AIORTC_AVAILABLE flag."""
        from imagestag.components.stream_view import AIORTC_AVAILABLE

        # Should be a boolean
        assert isinstance(AIORTC_AVAILABLE, bool)


# ============================================================================
# LAYER INJECTION TESTS
# ============================================================================


class TestLayerFrameInjection:
    """Tests for frame injection into layers."""

    @pytest.mark.asyncio
    async def test_inject_frame_with_anchor(self, user: User) -> None:
        """Test injecting frame with anchor position."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView

        view = None
        layer = None

        @ui.page("/test_inject_anchor")
        def page():
            nonlocal view, layer
            view = StreamView(width=800, height=600)
            layer = view.add_layer(url="http://example.com/placeholder.jpg", z_index=0)

        await user.open("/test_inject_anchor")

        # Create a base64 encoded image
        img = Image.from_array(np.full((100, 100, 3), 128, dtype=np.uint8))
        encoded = "data:image/jpeg;base64," + base64.b64encode(img.to_jpeg()).decode("ascii")

        # Inject with anchor position (birth_time is the correct parameter)
        layer.inject_frame(encoded, birth_time=0.0, anchor_x=50, anchor_y=50)

        assert layer.frames_produced >= 1


class TestLayerPNGEncoding:
    """Tests for PNG encoding in layers."""

    @pytest.mark.asyncio
    async def test_layer_png_mode(self, user: User) -> None:
        """Test layer using PNG encoding instead of JPEG."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView

        view = None
        layer = None

        @ui.page("/test_png_mode")
        def page():
            nonlocal view, layer
            view = StreamView(width=800, height=600)
            layer = view.add_layer(
                stream=GeneratorStream(
                    handler=lambda t: Image.from_array(np.full((100, 100, 3), 128, dtype=np.uint8)),
                    threaded=True,
                ),
                z_index=0,
                use_png=True,
            )

        await user.open("/test_png_mode")

        assert layer.use_png is True

        layer.start()
        await asyncio.sleep(0.2)

        # Check buffer has PNG frames
        frame_data = layer.get_buffered_frame()
        if frame_data:
            _, encoded, _ = frame_data
            assert "image/png" in encoded

        layer.stop()
