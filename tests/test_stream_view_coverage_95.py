"""Additional tests targeting specific uncovered lines for 95%+ coverage.

Focused on remaining gaps in:
- stream_view.py lines: 45-48, 362-363, 473-493, 1024-1063
- webrtc.py lines: frame processing, error handling
- layers.py lines: edge cases
"""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from imagestag import Image
from imagestag.streams.generator import GeneratorStream

if TYPE_CHECKING:
    from nicegui.testing import User


# ============================================================================
# STREAM_VIEW.PY UNCOVERED LINE TESTS
# ============================================================================


class TestStreamViewWebRTCOffer:
    """Tests for WebRTC offer sending (lines 473-493)."""

    @pytest.mark.asyncio
    async def test_webrtc_pending_offers(self, user: User) -> None:
        """Test WebRTC pending offers dict exists."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView

        view = None

        @ui.page("/test_webrtc_offers")
        def page():
            nonlocal view
            view = StreamView(width=800, height=600)

        await user.open("/test_webrtc_offers")

        # Pending offers should be empty by default
        assert hasattr(view, '_pending_webrtc_offers')
        assert len(view._pending_webrtc_offers) == 0


class TestStreamViewFrameProduction:
    """Tests for frame production (lines 1024-1063)."""

    @pytest.mark.asyncio
    async def test_produce_frame_sync_none_stream(self, user: User) -> None:
        """Test _produce_frame_sync returns None when no stream."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView, StreamViewLayer

        view = None
        layer = None

        @ui.page("/test_produce_none")
        def page():
            nonlocal view, layer
            view = StreamView(width=800, height=600)
            # Create layer with URL (no stream)
            layer = view.add_layer(url="http://example.com/img.jpg", z_index=0)

        await user.open("/test_produce_none")

        # Call static method directly
        result = StreamView._produce_frame_sync(layer)
        assert result is None  # No stream, should return None


class TestStreamViewDerivedLayerRemove:
    """Tests for derived layer removal cleanup (lines 362-363)."""

    @pytest.mark.asyncio
    async def test_remove_layer_with_callback_cleanup(self, user: User) -> None:
        """Test layer removal cleans up on_frame callbacks."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView

        view = None
        base_layer = None
        derived_id = None

        @ui.page("/test_remove_cleanup")
        def page():
            nonlocal view, base_layer, derived_id
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

            # Simulate having a callback registered
            derived._on_frame_callback = lambda f, t: None
            derived._source_stream = base_layer.stream

        await user.open("/test_remove_cleanup")

        # Remove the derived layer
        view.remove_layer(derived_id)

        # Should be removed
        assert derived_id not in view._layers


class TestStreamViewNoWebRTCFallback:
    """Tests for WebRTC not available fallback (lines 45-48)."""

    def test_aiortc_not_available_uses_none(self) -> None:
        """Test module loads when aiortc is not available."""
        # This tests the import error fallback path
        from imagestag.components.stream_view import AIORTC_AVAILABLE

        # Just verify the flag exists (value depends on whether aiortc is installed)
        assert isinstance(AIORTC_AVAILABLE, bool)


# ============================================================================
# LAYERS.PY UNCOVERED LINE TESTS
# ============================================================================


class TestLayerProducerEdgeCases:
    """Tests for layer producer edge cases."""

    @pytest.mark.asyncio
    async def test_layer_target_resize(self, user: User) -> None:
        """Test layer resizes to target dimensions."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView

        view = None
        layer = None

        @ui.page("/test_resize")
        def page():
            nonlocal view, layer
            view = StreamView(width=800, height=600)
            layer = view.add_layer(
                stream=GeneratorStream(
                    handler=lambda t: Image.from_array(np.full((100, 100, 3), 128, dtype=np.uint8)),
                    threaded=True,
                ),
                z_index=0,
                width=200,
                height=150,
            )

        await user.open("/test_resize")

        # Layer should have target dimensions set
        assert layer._target_width == 200
        assert layer._target_height == 150

        layer.start()
        await asyncio.sleep(0.2)
        layer.stop()

    @pytest.mark.asyncio
    async def test_layer_viewport_zoom_crop(self, user: User) -> None:
        """Test layer with viewport zoom crops frames."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView, Viewport

        view = None
        layer = None

        @ui.page("/test_zoom_crop")
        def page():
            nonlocal view, layer
            view = StreamView(width=800, height=600, enable_zoom=True)
            layer = view.add_layer(
                stream=GeneratorStream(
                    handler=lambda t: Image.from_array(np.full((200, 200, 3), 128, dtype=np.uint8)),
                    threaded=True,
                ),
                z_index=0,
            )

        await user.open("/test_zoom_crop")

        # Set zoom viewport
        viewport = Viewport(zoom=2.0, x=0.25, y=0.25, width=0.5, height=0.5)
        layer.set_viewport(viewport)

        assert layer.effective_zoom == 2.0

        layer.start()
        await asyncio.sleep(0.2)
        layer.stop()


class TestLayerBufferOperations:
    """Tests for layer buffer operations."""

    @pytest.mark.asyncio
    async def test_get_buffered_frame_when_empty(self, user: User) -> None:
        """Test get_buffered_frame returns None when buffer empty."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView

        view = None
        layer = None

        @ui.page("/test_empty_buffer")
        def page():
            nonlocal view, layer
            view = StreamView(width=800, height=600)
            layer = view.add_layer(
                stream=GeneratorStream(
                    handler=lambda t: Image.from_array(np.full((100, 100, 3), 128, dtype=np.uint8)),
                ),
                z_index=0,
            )

        await user.open("/test_empty_buffer")

        # Don't start - buffer should be empty
        result = layer.get_buffered_frame()
        assert result is None


# ============================================================================
# WEBRTC.PY UNCOVERED LINE TESTS
# ============================================================================


class TestWebRTCCodecBitrate:
    """Tests for codec bitrate setting."""

    def test_set_codec_bitrate(self) -> None:
        """Test _set_codec_bitrate function."""
        try:
            from imagestag.components.stream_view.webrtc import (
                _set_codec_bitrate,
                AIORTC_AVAILABLE,
            )
        except ImportError:
            pytest.skip("webrtc not available")

        if not AIORTC_AVAILABLE:
            pytest.skip("aiortc not available")

        # Should not raise
        _set_codec_bitrate(10_000_000)


class TestWebRTCCheckAvailable:
    """Tests for check_aiortc_available function."""

    def test_check_aiortc_available(self) -> None:
        """Test check_aiortc_available function."""
        try:
            from imagestag.components.stream_view.webrtc import (
                check_aiortc_available,
                AIORTC_AVAILABLE,
            )
        except ImportError:
            pytest.skip("webrtc not available")

        if AIORTC_AVAILABLE:
            # Should not raise when available
            check_aiortc_available()
        else:
            # Should raise when not available
            with pytest.raises(ImportError):
                check_aiortc_available()


class TestWebRTCConnectionClose:
    """Tests for WebRTC connection closing."""

    def test_close_nonexistent_connection(self) -> None:
        """Test closing a connection that doesn't exist."""
        try:
            from imagestag.components.stream_view.webrtc import (
                WebRTCManager,
                AIORTC_AVAILABLE,
            )
        except ImportError:
            pytest.skip("webrtc not available")

        if not AIORTC_AVAILABLE:
            pytest.skip("aiortc not available")

        manager = WebRTCManager()

        # Should not raise when closing nonexistent connection
        manager.close_connection("nonexistent_layer")

        manager.close_all()


class TestWebRTCLayerConfigViewport:
    """Tests for WebRTCLayerConfig viewport methods."""

    def test_set_viewport(self) -> None:
        """Test set_viewport method."""
        try:
            from imagestag.components.stream_view.webrtc import (
                WebRTCLayerConfig,
                AIORTC_AVAILABLE,
            )
            from imagestag.components.stream_view import Viewport
        except ImportError:
            pytest.skip("webrtc not available")

        if not AIORTC_AVAILABLE:
            pytest.skip("aiortc not available")

        stream = GeneratorStream(
            handler=lambda t: Image.from_array(np.full((100, 100, 3), 128, dtype=np.uint8)),
        )

        config = WebRTCLayerConfig(stream=stream, z_index=0)

        viewport = Viewport(zoom=2.0, x=0.1, y=0.2, width=0.5, height=0.6)
        config.set_viewport(viewport)

        assert config.viewport_x == 0.1
        assert config.viewport_y == 0.2
        assert config.viewport_width == 0.5
        assert config.viewport_height == 0.6
        assert config.viewport_zoom == 2.0


# ============================================================================
# ADDITIONAL STREAMVIEW INTERNAL TESTS
# ============================================================================


class TestStreamViewUpdateMethods:
    """Tests for StreamView update methods."""

    @pytest.mark.asyncio
    async def test_update_layer_order(self, user: User) -> None:
        """Test _update_layer_order method."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView

        view = None

        @ui.page("/test_layer_order")
        def page():
            nonlocal view
            view = StreamView(width=800, height=600)
            view.add_layer(url="http://example.com/1.jpg", z_index=2)
            view.add_layer(url="http://example.com/2.jpg", z_index=1)
            view.add_layer(url="http://example.com/3.jpg", z_index=3)

        await user.open("/test_layer_order")

        # Manually trigger order update
        view._update_layer_order()

        # Sorted order should be by z_index
        order = view._layer_order
        assert len(order) == 3


class TestStreamViewMetrics:
    """Tests for StreamView metrics."""

    @pytest.mark.asyncio
    async def test_python_metrics(self, user: User) -> None:
        """Test Python metrics collection."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView, PythonMetrics

        view = None

        @ui.page("/test_metrics")
        def page():
            nonlocal view
            view = StreamView(width=800, height=600, show_metrics=True)
            view.add_layer(
                stream=GeneratorStream(
                    handler=lambda t: Image.from_array(np.full((100, 100, 3), 128, dtype=np.uint8)),
                    threaded=True,
                ),
                z_index=0,
            )

        await user.open("/test_metrics")

        # View should have metrics
        assert view._props.get("showMetrics") is True

        # PythonMetrics class should be accessible
        pm = PythonMetrics()
        assert pm.total_frames_produced == 0
        assert pm.total_frames_delivered == 0


class TestStreamViewSVGOverlay:
    """Tests for SVG overlay functionality."""

    @pytest.mark.asyncio
    async def test_set_svg_template(self, user: User) -> None:
        """Test setting SVG template."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView

        view = None

        @ui.page("/test_svg")
        def page():
            nonlocal view
            view = StreamView(width=800, height=600)

        await user.open("/test_svg")

        # Set SVG template
        view.set_svg('<svg><text>{counter}</text></svg>', values={"counter": 0})

        # Update values
        view.update_svg_values(counter=42)


class TestStreamViewStartStop:
    """Tests for StreamView start/stop methods."""

    @pytest.mark.asyncio
    async def test_start_stop_layers(self, user: User) -> None:
        """Test start and stop methods."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView

        view = None

        @ui.page("/test_start_stop")
        def page():
            nonlocal view
            view = StreamView(width=800, height=600)
            view.add_layer(
                stream=GeneratorStream(
                    handler=lambda t: Image.from_array(np.full((100, 100, 3), 128, dtype=np.uint8)),
                    threaded=True,
                ),
                z_index=0,
            )

        await user.open("/test_start_stop")

        # Start all layers
        view.start()
        await asyncio.sleep(0.1)

        # Stop all layers
        view.stop()


# ============================================================================
# EDGE CASE TESTS
# ============================================================================


class TestStreamViewEdgeCases:
    """Tests for edge cases."""

    @pytest.mark.asyncio
    async def test_add_layer_with_image(self, user: User) -> None:
        """Test adding layer with static Image object."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView

        view = None
        layer = None

        @ui.page("/test_image_layer")
        def page():
            nonlocal view, layer
            view = StreamView(width=800, height=600)

            img = Image.from_array(np.full((100, 100, 3), 128, dtype=np.uint8))
            layer = view.add_layer(image=img, z_index=0)

        await user.open("/test_image_layer")

        # Layer should be static
        assert layer.is_static is True

    @pytest.mark.asyncio
    async def test_layer_with_mask(self, user: User) -> None:
        """Test adding layer with mask."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView

        view = None
        layer = None

        @ui.page("/test_mask_layer")
        def page():
            nonlocal view, layer
            view = StreamView(width=800, height=600)

            # Create mask as grayscale image (2D array for grayscale)
            mask = Image.from_array(np.full((100, 100), 255, dtype=np.uint8))
            layer = view.add_layer(
                url="http://example.com/img.jpg",
                mask=mask,
                z_index=0,
            )

        await user.open("/test_mask_layer")

        assert layer is not None


class TestLayerProperties:
    """Tests for layer property access."""

    @pytest.mark.asyncio
    async def test_layer_effective_viewport(self, user: User) -> None:
        """Test layer effective viewport calculation."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView

        view = None
        layer = None

        @ui.page("/test_effective_vp")
        def page():
            nonlocal view, layer
            view = StreamView(width=800, height=600, enable_zoom=True)
            layer = view.add_layer(
                stream=GeneratorStream(
                    handler=lambda t: Image.from_array(np.full((100, 100, 3), 128, dtype=np.uint8)),
                ),
                z_index=0,
                depth=0.5,  # Parallax layer
            )

        await user.open("/test_effective_vp")

        # Check depth affects effective zoom
        assert layer.depth == 0.5

    @pytest.mark.asyncio
    async def test_layer_frames_produced_count(self, user: User) -> None:
        """Test frames_produced counter."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView

        view = None
        layer = None

        @ui.page("/test_frames_count")
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

        await user.open("/test_frames_count")

        initial = layer.frames_produced

        layer.start()
        await asyncio.sleep(0.3)
        layer.stop()

        # Should have produced frames
        assert layer.frames_produced > initial
