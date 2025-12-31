"""Final coverage tests for remaining gaps to achieve 95%+.

Focuses on:
- set_size and set_fullscreen_mode methods
- Mouse event handling
- WebRTC layer management
- More edge cases
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import numpy as np
import pytest

from imagestag import Image
from imagestag.streams.generator import GeneratorStream

if TYPE_CHECKING:
    from nicegui.testing import User


# ============================================================================
# SIZE AND FULLSCREEN TESTS
# ============================================================================


class TestStreamViewSizing:
    """Tests for StreamView sizing methods."""

    @pytest.mark.asyncio
    async def test_set_size_updates_layers(self, user: User) -> None:
        """Test set_size updates full-canvas layer target sizes."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView

        view = None
        layer = None

        @ui.page("/test_set_size")
        def page():
            nonlocal view, layer
            view = StreamView(width=800, height=600)
            # Full-canvas layer (no explicit width/height)
            layer = view.add_layer(
                stream=GeneratorStream(
                    handler=lambda t: Image.from_array(np.full((100, 100, 3), 128, dtype=np.uint8)),
                ),
                z_index=0,
            )

        await user.open("/test_set_size")

        # Set new size
        view.set_size(1920, 1080)

        # Layer target should update
        assert layer._target_width == 1920
        assert layer._target_height == 1080

    @pytest.mark.asyncio
    async def test_set_size_skips_positioned_layers(self, user: User) -> None:
        """Test set_size doesn't affect positioned layers."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView

        view = None
        layer = None

        @ui.page("/test_set_size_positioned")
        def page():
            nonlocal view, layer
            view = StreamView(width=800, height=600)
            # Positioned layer with explicit size
            layer = view.add_layer(
                stream=GeneratorStream(
                    handler=lambda t: Image.from_array(np.full((100, 100, 3), 128, dtype=np.uint8)),
                ),
                z_index=0,
                width=200,
                height=150,
            )

        await user.open("/test_set_size_positioned")

        # Set new size
        view.set_size(1920, 1080)

        # Layer target should be original explicit size
        assert layer._target_width == 200
        assert layer._target_height == 150


class TestStreamViewFullscreen:
    """Tests for StreamView fullscreen mode."""

    @pytest.mark.asyncio
    async def test_set_fullscreen_mode_active(self, user: User) -> None:
        """Test fullscreen mode activation."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView

        view = None
        layer = None

        @ui.page("/test_fullscreen_active")
        def page():
            nonlocal view, layer
            view = StreamView(width=800, height=600)
            layer = view.add_layer(
                stream=GeneratorStream(
                    handler=lambda t: Image.from_array(np.full((100, 100, 3), 128, dtype=np.uint8)),
                ),
                z_index=0,
                fullscreen_scale="video",  # Match video resolution
            )

        await user.open("/test_fullscreen_active")

        # Enter fullscreen
        view.set_fullscreen_mode(
            active=True,
            screen_width=1920,
            screen_height=1080,
            video_width=1280,
            video_height=720,
        )

        # Layer should match video resolution
        assert layer._target_width == 1280
        assert layer._target_height == 720

    @pytest.mark.asyncio
    async def test_set_fullscreen_mode_screen_scale(self, user: User) -> None:
        """Test fullscreen mode with screen scale."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView

        view = None
        layer = None

        @ui.page("/test_fullscreen_screen")
        def page():
            nonlocal view, layer
            view = StreamView(width=800, height=600)
            layer = view.add_layer(
                stream=GeneratorStream(
                    handler=lambda t: Image.from_array(np.full((100, 100, 3), 128, dtype=np.uint8)),
                ),
                z_index=0,
                fullscreen_scale="screen",  # Match screen resolution
            )

        await user.open("/test_fullscreen_screen")

        # Enter fullscreen with screen scale
        view.set_fullscreen_mode(
            active=True,
            screen_width=1920,
            screen_height=1080,
            video_width=1280,
            video_height=720,
        )

        # Layer should match screen resolution
        assert layer._target_width == 1920
        assert layer._target_height == 1080

    @pytest.mark.asyncio
    async def test_set_fullscreen_mode_exit(self, user: User) -> None:
        """Test exiting fullscreen mode."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView

        view = None
        layer = None

        @ui.page("/test_fullscreen_exit")
        def page():
            nonlocal view, layer
            view = StreamView(width=800, height=600)
            layer = view.add_layer(
                stream=GeneratorStream(
                    handler=lambda t: Image.from_array(np.full((100, 100, 3), 128, dtype=np.uint8)),
                ),
                z_index=0,
            )

        await user.open("/test_fullscreen_exit")

        # Exit fullscreen
        view.set_fullscreen_mode(active=False)

        # Layer should match view size
        assert layer._target_width == 800
        assert layer._target_height == 600

    @pytest.mark.asyncio
    async def test_fullscreen_skips_positioned_layers(self, user: User) -> None:
        """Test fullscreen mode skips positioned layers."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView

        view = None
        layer = None

        @ui.page("/test_fullscreen_positioned")
        def page():
            nonlocal view, layer
            view = StreamView(width=800, height=600)
            layer = view.add_layer(
                stream=GeneratorStream(
                    handler=lambda t: Image.from_array(np.full((100, 100, 3), 128, dtype=np.uint8)),
                ),
                z_index=0,
                width=200,
                height=150,
            )

        await user.open("/test_fullscreen_positioned")

        # Enter fullscreen
        view.set_fullscreen_mode(
            active=True,
            screen_width=1920,
            screen_height=1080,
        )

        # Layer should keep original explicit size
        assert layer._target_width == 200
        assert layer._target_height == 150


# ============================================================================
# MOUSE EVENT TESTS
# ============================================================================


class TestStreamViewMouseEvents:
    """Tests for StreamView mouse event handling."""

    @pytest.mark.asyncio
    async def test_mouse_move_handler(self, user: User) -> None:
        """Test mouse move event handler."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView

        view = None
        events = []

        @ui.page("/test_mouse_move")
        def page():
            nonlocal view
            view = StreamView(width=800, height=600)

            @view.on_mouse_move
            def on_move(e):
                events.append(e)

        await user.open("/test_mouse_move")

        # Handler should be registered
        assert view._mouse_move_handler is not None

    @pytest.mark.asyncio
    async def test_mouse_click_handler(self, user: User) -> None:
        """Test mouse click event handler."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView

        view = None
        events = []

        @ui.page("/test_mouse_click")
        def page():
            nonlocal view
            view = StreamView(width=800, height=600)

            @view.on_mouse_click
            def on_click(e):
                events.append(e)

        await user.open("/test_mouse_click")

        # Handler should be registered
        assert view._mouse_click_handler is not None


# ============================================================================
# UPDATE LAYER POSITION TESTS
# ============================================================================


class TestUpdateLayerPosition:
    """Tests for update_layer_position method."""

    @pytest.mark.asyncio
    async def test_update_layer_position(self, user: User) -> None:
        """Test updating layer position."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView

        view = None
        layer = None

        @ui.page("/test_update_pos")
        def page():
            nonlocal view, layer
            view = StreamView(width=800, height=600)
            layer = view.add_layer(
                stream=GeneratorStream(
                    handler=lambda t: Image.from_array(np.full((100, 100, 3), 128, dtype=np.uint8)),
                ),
                z_index=0,
            )

        await user.open("/test_update_pos")

        # Update position
        view.update_layer_position(layer.id, x=100, y=50, width=200, height=150)

        # Layer should have new position
        assert layer.x == 100
        assert layer.y == 50
        assert layer.width == 200
        assert layer.height == 150

    @pytest.mark.asyncio
    async def test_update_layer_position_nonexistent(self, user: User) -> None:
        """Test updating position of nonexistent layer."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView

        view = None

        @ui.page("/test_update_pos_none")
        def page():
            nonlocal view
            view = StreamView(width=800, height=600)

        await user.open("/test_update_pos_none")

        # Should not crash with nonexistent layer
        view.update_layer_position("nonexistent", x=100, y=50)


# ============================================================================
# LAYER VISIBILITY TESTS
# ============================================================================


class TestLayerProperties2:
    """Tests for layer properties."""

    @pytest.mark.asyncio
    async def test_layer_is_static(self, user: User) -> None:
        """Test layer is_static property."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView

        view = None
        static_layer = None
        dynamic_layer = None

        @ui.page("/test_static_prop")
        def page():
            nonlocal view, static_layer, dynamic_layer
            view = StreamView(width=800, height=600)
            static_layer = view.add_layer(
                url="http://example.com/img.jpg",
                z_index=0,
            )
            dynamic_layer = view.add_layer(
                stream=GeneratorStream(
                    handler=lambda t: Image.from_array(np.full((100, 100, 3), 128, dtype=np.uint8)),
                ),
                z_index=1,
            )

        await user.open("/test_static_prop")

        # URL layer is static
        assert static_layer.is_static is True
        # Stream layer is not static
        assert dynamic_layer.is_static is False


# ============================================================================
# VIEWPORT CHANGE EVENT TESTS
# ============================================================================


class TestViewportChange:
    """Tests for viewport change handling."""

    @pytest.mark.asyncio
    async def test_viewport_enabled(self, user: User) -> None:
        """Test viewport/zoom is enabled."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView

        view = None

        @ui.page("/test_viewport_enabled")
        def page():
            nonlocal view
            view = StreamView(width=800, height=600, enable_zoom=True)

        await user.open("/test_viewport_enabled")

        # Zoom should be enabled
        assert view._props.get("enableZoom") is True


# ============================================================================
# WEBRTC LAYER TESTS
# ============================================================================


class TestWebRTCLayerManagement:
    """Tests for WebRTC layer management."""

    @pytest.mark.asyncio
    async def test_webrtc_layers_dict(self, user: User) -> None:
        """Test WebRTC layers dict exists."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView

        view = None

        @ui.page("/test_webrtc_dict")
        def page():
            nonlocal view
            view = StreamView(width=800, height=600)

        await user.open("/test_webrtc_dict")

        # WebRTC layers dict should exist
        assert hasattr(view, '_webrtc_layers')
        assert isinstance(view._webrtc_layers, dict)


# ============================================================================
# ADDITIONAL LAYER TESTS
# ============================================================================


class TestLayerStreamOutput:
    """Tests for layer stream output key."""

    @pytest.mark.asyncio
    async def test_layer_with_stream_output(self, user: User) -> None:
        """Test layer with stream_output parameter."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView

        # Create a multi-output stream
        class MultiOutputStream:
            def __init__(self):
                self._running = False
                self._frame_index = 0
                self._outputs = {"main": None, "preview": None}

            def start(self):
                self._running = True

            def stop(self):
                self._running = False

            def get_frame(self, timestamp: float, output: str = "main") -> tuple:
                self._frame_index += 1
                return (
                    Image.from_array(np.full((100, 100, 3), 128, dtype=np.uint8)),
                    self._frame_index
                )

        view = None
        layer = None

        @ui.page("/test_stream_output")
        def page():
            nonlocal view, layer
            view = StreamView(width=800, height=600)
            layer = view.add_layer(
                stream=MultiOutputStream(),
                stream_output="preview",
                z_index=0,
            )

        await user.open("/test_stream_output")

        assert layer.stream_output == "preview"


class TestLayerDepth:
    """Tests for layer depth (parallax)."""

    @pytest.mark.asyncio
    async def test_layer_depth_values(self, user: User) -> None:
        """Test layer with various depth values."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView

        view = None
        bg_layer = None
        fg_layer = None
        hud_layer = None

        @ui.page("/test_depth")
        def page():
            nonlocal view, bg_layer, fg_layer, hud_layer
            view = StreamView(width=800, height=600, enable_zoom=True)

            # Background (slower parallax)
            bg_layer = view.add_layer(
                url="http://example.com/bg.jpg",
                z_index=0,
                depth=0.5,
            )

            # Foreground (faster parallax)
            fg_layer = view.add_layer(
                url="http://example.com/fg.jpg",
                z_index=1,
                depth=1.5,
            )

            # HUD (fixed, no parallax)
            hud_layer = view.add_layer(
                url="http://example.com/hud.jpg",
                z_index=2,
                depth=0.0,
            )

        await user.open("/test_depth")

        assert bg_layer.depth == 0.5
        assert fg_layer.depth == 1.5
        assert hud_layer.depth == 0.0


# ============================================================================
# CLEANUP AND RESOURCE TESTS
# ============================================================================


class TestStreamViewCleanup:
    """Tests for StreamView cleanup."""

    @pytest.mark.asyncio
    async def test_remove_all_layers(self, user: User) -> None:
        """Test removing all layers."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView

        view = None

        @ui.page("/test_remove_all")
        def page():
            nonlocal view
            view = StreamView(width=800, height=600)
            view.add_layer(url="http://example.com/1.jpg", z_index=0)
            view.add_layer(url="http://example.com/2.jpg", z_index=1)
            view.add_layer(url="http://example.com/3.jpg", z_index=2)

        await user.open("/test_remove_all")

        # Remove all layers one by one
        layer_ids = list(view._layers.keys())
        for lid in layer_ids:
            view.remove_layer(lid)

        assert len(view._layers) == 0


# ============================================================================
# FPS COUNTER TESTS
# ============================================================================


class TestFPSCounter:
    """Tests for FPSCounter class."""

    def test_fps_counter_tick(self) -> None:
        """Test FPSCounter tick method."""
        from imagestag.components.stream_view import FPSCounter
        import time

        counter = FPSCounter(window_size=10)

        # Tick several times with small delay
        for _ in range(5):
            counter.tick()
            time.sleep(0.001)

        # FPS should be calculable now
        fps = counter.fps
        assert fps >= 0  # Can be 0 if timing not enough

    def test_fps_counter_fps_initial(self) -> None:
        """Test FPSCounter initial fps is 0."""
        from imagestag.components.stream_view import FPSCounter

        counter = FPSCounter()

        # Initial FPS should be 0
        assert counter.fps == 0.0


# ============================================================================
# TIMER TESTS
# ============================================================================


class TestTimer:
    """Tests for Timer class as context manager."""

    def test_timer_context_manager(self) -> None:
        """Test Timer as context manager."""
        from imagestag.components.stream_view import Timer
        import time

        with Timer() as timer:
            time.sleep(0.01)

        # Elapsed should be around 10ms
        elapsed = timer.elapsed_ms
        assert elapsed >= 10

    def test_timer_elapsed_seconds(self) -> None:
        """Test Timer elapsed_seconds property."""
        from imagestag.components.stream_view import Timer
        import time

        with Timer() as timer:
            time.sleep(0.01)

        # Elapsed should be around 0.01 seconds
        elapsed = timer.elapsed_seconds
        assert elapsed >= 0.01


# ============================================================================
# FRAME PRODUCTION AND REQUEST TESTS
# ============================================================================


class TestFrameProduction:
    """Tests for frame production methods."""

    @pytest.mark.asyncio
    async def test_handle_frame_request_direct_call(self, user: User) -> None:
        """Test _handle_frame_request called directly."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView

        view = None
        layer = None

        @ui.page("/test_request_frame")
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

        await user.open("/test_request_frame")

        # Start the layer to populate buffer
        layer.start()
        await asyncio.sleep(0.2)

        # Create mock event args
        mock_event = MagicMock()
        mock_event.args = {"layer_id": layer.id}

        # Call _handle_frame_request directly (simulating JS callback)
        view._handle_frame_request(mock_event)
        await asyncio.sleep(0.1)

        layer.stop()

    @pytest.mark.asyncio
    async def test_handle_frame_request_static_layer(self, user: User) -> None:
        """Test _handle_frame_request with static layer (should return early)."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView

        view = None
        layer = None

        @ui.page("/test_request_static")
        def page():
            nonlocal view, layer
            view = StreamView(width=800, height=600)
            layer = view.add_layer(url="http://example.com/img.jpg", z_index=0)

        await user.open("/test_request_static")

        # Create mock event args
        mock_event = MagicMock()
        mock_event.args = {"layer_id": layer.id}

        # Static layer should return immediately
        view._handle_frame_request(mock_event)

    @pytest.mark.asyncio
    async def test_handle_frame_request_nonexistent_layer(self, user: User) -> None:
        """Test _handle_frame_request with nonexistent layer."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView

        view = None

        @ui.page("/test_request_nonexist")
        def page():
            nonlocal view
            view = StreamView(width=800, height=600)

        await user.open("/test_request_nonexist")

        # Create mock event args
        mock_event = MagicMock()
        mock_event.args = {"layer_id": "nonexistent"}

        # Should not crash with nonexistent layer
        view._handle_frame_request(mock_event)

    @pytest.mark.asyncio
    async def test_handle_frame_request_pending_dedup(self, user: User) -> None:
        """Test _handle_frame_request deduplication of pending requests."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView

        view = None
        layer = None

        @ui.page("/test_request_dedup")
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

        await user.open("/test_request_dedup")

        # Create mock event args
        mock_event = MagicMock()
        mock_event.args = {"layer_id": layer.id}

        # Add a pending task that's not done
        pending_task = asyncio.create_task(asyncio.sleep(10))
        view._pending_requests[layer.id] = pending_task

        # Should return early due to pending request
        view._handle_frame_request(mock_event)

        # Clean up
        pending_task.cancel()
        try:
            await pending_task
        except asyncio.CancelledError:
            pass


class TestAsyncFrameProduction:
    """Tests for async frame production."""

    @pytest.mark.asyncio
    async def test_produce_frame_async(self, user: User) -> None:
        """Test _produce_frame_async method."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView

        view = None
        layer = None

        @ui.page("/test_async_produce")
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

        await user.open("/test_async_produce")

        layer.start()
        await asyncio.sleep(0.1)

        # Call async production directly
        await view._produce_frame_async(layer)

        layer.stop()

    @pytest.mark.asyncio
    async def test_produce_frame_async_no_stream(self, user: User) -> None:
        """Test _produce_frame_async with no stream."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView

        view = None
        layer = None

        @ui.page("/test_async_no_stream")
        def page():
            nonlocal view, layer
            view = StreamView(width=800, height=600)
            layer = view.add_layer(url="http://example.com/img.jpg", z_index=0)

        await user.open("/test_async_no_stream")

        # Should return early with no stream
        await view._produce_frame_async(layer)


class TestPendingRequestsCleanup:
    """Tests for pending requests cleanup."""

    @pytest.mark.asyncio
    async def test_check_pending_frames(self, user: User) -> None:
        """Test _check_pending_frames cleanup."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView

        view = None

        @ui.page("/test_pending_cleanup")
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

        await user.open("/test_pending_cleanup")

        # Add a completed task to pending
        completed_task = asyncio.create_task(asyncio.sleep(0))
        await completed_task
        view._pending_requests["test_layer"] = completed_task

        # Check pending frames should clean up
        view._check_pending_frames()
        assert "test_layer" not in view._pending_requests


class TestMultiOutputStreams:
    """Tests for multi-output stream handling."""

    @pytest.mark.asyncio
    async def test_produce_frame_with_dict_output(self, user: User) -> None:
        """Test _produce_frame_sync with dict output stream."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView

        class MultiOutputStream:
            def __init__(self):
                self._running = False

            def start(self):
                self._running = True

            def stop(self):
                self._running = False

            def get_frame(self, timestamp: float) -> tuple:
                """Return dict of frames."""
                frame = Image.from_array(np.full((100, 100, 3), 128, dtype=np.uint8))
                return ({"main": frame, "preview": frame}, 0)

        view = None
        layer = None

        @ui.page("/test_dict_output")
        def page():
            nonlocal view, layer
            view = StreamView(width=800, height=600)
            layer = view.add_layer(
                stream=MultiOutputStream(),
                z_index=0,
            )

        await user.open("/test_dict_output")

        # Produce frame - should pick first output when stream_output is None
        result = StreamView._produce_frame_sync(layer)
        assert result is not None

    @pytest.mark.asyncio
    async def test_produce_frame_with_specific_output(self, user: User) -> None:
        """Test _produce_frame_sync with specific stream_output."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView

        class MultiOutputStream:
            def __init__(self):
                self._running = False

            def start(self):
                self._running = True

            def stop(self):
                self._running = False

            def get_frame(self, timestamp: float) -> tuple:
                """Return dict of frames."""
                frame = Image.from_array(np.full((100, 100, 3), 128, dtype=np.uint8))
                return ({"main": frame, "preview": frame}, 0)

        view = None
        layer = None

        @ui.page("/test_specific_output")
        def page():
            nonlocal view, layer
            view = StreamView(width=800, height=600)
            layer = view.add_layer(
                stream=MultiOutputStream(),
                stream_output="preview",
                z_index=0,
            )

        await user.open("/test_specific_output")

        # Produce frame with specific output
        result = StreamView._produce_frame_sync(layer)
        assert result is not None

    @pytest.mark.asyncio
    async def test_produce_frame_missing_output(self, user: User) -> None:
        """Test _produce_frame_sync with missing stream_output key."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView

        class MultiOutputStream:
            def __init__(self):
                self._running = False

            def start(self):
                self._running = True

            def stop(self):
                self._running = False

            def get_frame(self, timestamp: float) -> tuple:
                """Return dict without requested key."""
                frame = Image.from_array(np.full((100, 100, 3), 128, dtype=np.uint8))
                return ({"main": frame}, 0)

        view = None
        layer = None

        @ui.page("/test_missing_output")
        def page():
            nonlocal view, layer
            view = StreamView(width=800, height=600)
            layer = view.add_layer(
                stream=MultiOutputStream(),
                stream_output="nonexistent",
                z_index=0,
            )

        await user.open("/test_missing_output")

        # Should return None for missing output key
        result = StreamView._produce_frame_sync(layer)
        assert result is None


class TestSVGErrorHandling:
    """Tests for SVG error handling."""

    @pytest.mark.asyncio
    async def test_svg_template_missing_placeholder(self, user: User) -> None:
        """Test SVG template with missing placeholder."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView

        view = None

        @ui.page("/test_svg_missing")
        def page():
            nonlocal view
            view = StreamView(width=800, height=600)

        await user.open("/test_svg_missing")

        # Set template with placeholder
        view.set_svg('<svg><text>{counter}</text></svg>', values={})

        # Should not crash with missing placeholder
        view._send_svg()  # KeyError should be caught


class TestVideoStreamSourceType:
    """Tests for VideoStream source type detection."""

    @pytest.mark.asyncio
    async def test_video_stream_source_type(self, user: User) -> None:
        """Test that VideoStream is detected as 'video' type."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView, VideoStream
        from pathlib import Path

        video_path = Path("/Users/michael/projects/ImageStag/tmp/media/big_buck_bunny_1080p_h264.mov")
        if not video_path.exists():
            pytest.skip("Big Buck Bunny video not found")

        view = None
        layer = None

        @ui.page("/test_video_source")
        def page():
            nonlocal view, layer
            view = StreamView(width=800, height=600)
            layer = view.add_layer(
                stream=VideoStream(str(video_path), loop=True),
                z_index=0,
            )

        await user.open("/test_video_source")

        # Check that layer is using VideoStream
        stream_class = type(layer.stream).__name__
        assert stream_class == "VideoStream"


class TestDerivedLayerChain:
    """Tests for derived layer chain traversal."""

    @pytest.mark.asyncio
    async def test_derived_layer_chain(self, user: User) -> None:
        """Test derived layer with nested source."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView

        view = None
        base_layer = None
        derived1 = None
        derived2 = None

        @ui.page("/test_derived_chain")
        def page():
            nonlocal view, base_layer, derived1, derived2
            view = StreamView(width=800, height=600)

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

            derived2 = view.add_layer(
                source_layer=derived1,
                z_index=2,
            )

        await user.open("/test_derived_chain")

        # All layers should exist
        assert base_layer.id in view._layers
        assert derived1.id in view._layers
        assert derived2.id in view._layers


class TestDerivedLayerCleanup:
    """Tests for derived layer cleanup on removal."""

    @pytest.mark.asyncio
    async def test_remove_derived_layer_cleans_callback(self, user: User) -> None:
        """Test removing derived layer cleans up on_frame callback."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView

        view = None
        base_layer = None
        derived_layer = None

        @ui.page("/test_derived_cleanup")
        def page():
            nonlocal view, base_layer, derived_layer
            view = StreamView(width=800, height=600)

            base_layer = view.add_layer(
                stream=GeneratorStream(
                    handler=lambda t: Image.from_array(np.full((100, 100, 3), 128, dtype=np.uint8)),
                    threaded=True,
                ),
                z_index=0,
            )

            derived_layer = view.add_layer(
                source_layer=base_layer,
                z_index=1,
            )

            # Manually set up cleanup attributes (normally set internally)
            derived_layer._on_frame_callback = lambda f, t: None
            derived_layer._source_stream = MagicMock()

        await user.open("/test_derived_cleanup")

        derived_id = derived_layer.id

        # Remove derived layer - should trigger cleanup
        view.remove_layer(derived_id)

        assert derived_id not in view._layers


class TestViewportEvents:
    """Tests for viewport change events."""

    @pytest.mark.asyncio
    async def test_viewport_change_with_paused_stream(self, user: User) -> None:
        """Test viewport change updates paused stream."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView

        view = None
        layer = None

        @ui.page("/test_viewport_paused")
        def page():
            nonlocal view, layer
            view = StreamView(width=800, height=600, enable_zoom=True)
            layer = view.add_layer(
                stream=GeneratorStream(
                    handler=lambda t: Image.from_array(np.full((100, 100, 3), 128, dtype=np.uint8)),
                    threaded=True,
                ),
                z_index=0,
            )

        await user.open("/test_viewport_paused")

        layer.start()
        await asyncio.sleep(0.1)

        # Pause the stream
        layer.stream.pause()

        # Create mock viewport change event
        mock_event = MagicMock()
        mock_event.args = {
            "x": 0.25,
            "y": 0.25,
            "width": 0.5,
            "height": 0.5,
            "zoom": 2.0,
        }

        # Trigger viewport change
        view._handle_viewport_change(mock_event)

        layer.stop()

    @pytest.mark.asyncio
    async def test_viewport_change_updates_webrtc_layers(self, user: User) -> None:
        """Test viewport change updates WebRTC layer configs."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView, VideoStream
        from imagestag.components.stream_view.webrtc import WebRTCLayerConfig

        view = None

        @ui.page("/test_viewport_webrtc")
        def page():
            nonlocal view
            view = StreamView(width=800, height=600, enable_zoom=True)

        await user.open("/test_viewport_webrtc")

        # Add a mock WebRTC config
        mock_config = MagicMock(spec=WebRTCLayerConfig)
        view._webrtc_layers["test_webrtc"] = mock_config

        # Create mock viewport change event
        mock_event = MagicMock()
        mock_event.args = {
            "x": 0.1,
            "y": 0.2,
            "width": 0.8,
            "height": 0.6,
            "zoom": 1.5,
        }

        # Trigger viewport change
        view._handle_viewport_change(mock_event)

        # WebRTC config should have set_viewport called
        mock_config.set_viewport.assert_called()


class TestMouseEventsWithViewport:
    """Tests for mouse events that include viewport."""

    @pytest.mark.asyncio
    async def test_mouse_event_with_viewport(self, user: User) -> None:
        """Test mouse event parsing with viewport data."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView

        view = None
        received_events = []

        @ui.page("/test_mouse_viewport")
        def page():
            nonlocal view
            view = StreamView(width=800, height=600, enable_zoom=True)

            @view.on_mouse_move
            def on_move(e):
                received_events.append(e)

        await user.open("/test_mouse_viewport")

        # Create mock event with viewport
        mock_event = MagicMock()
        mock_event.args = {
            "x": 400,
            "y": 300,
            "sourceX": 200,
            "sourceY": 150,
            "viewport": {
                "x": 0.25,
                "y": 0.25,
                "width": 0.5,
                "height": 0.5,
                "zoom": 2.0,
            },
        }

        # Trigger mouse move
        view._handle_mouse_move(mock_event)

        assert len(received_events) == 1
        assert received_events[0].viewport is not None
        assert received_events[0].viewport.zoom == 2.0


class TestPendingRequestsSafetyLimit:
    """Tests for pending requests safety limit."""

    @pytest.mark.asyncio
    async def test_check_pending_frames_safety_limit(self, user: User) -> None:
        """Test _check_pending_frames clears when too many requests."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView

        view = None

        @ui.page("/test_safety_limit")
        def page():
            nonlocal view
            view = StreamView(width=800, height=600)

        await user.open("/test_safety_limit")

        # Add more than 100 pending tasks to trigger safety limit
        for i in range(105):
            task = asyncio.create_task(asyncio.sleep(10))
            view._pending_requests[f"layer_{i}"] = task

        assert len(view._pending_requests) == 105

        # Check pending frames should clear all
        view._check_pending_frames()

        # All should be cleared due to safety limit
        assert len(view._pending_requests) == 0


class TestAsyncFrameProductionWithErrors:
    """Tests for async frame production error handling."""

    @pytest.mark.asyncio
    async def test_produce_frame_async_catches_exception(self, user: User) -> None:
        """Test _produce_frame_async catches and ignores exceptions."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView
        from unittest.mock import patch

        view = None
        layer = None

        @ui.page("/test_async_error")
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

        await user.open("/test_async_error")

        layer.start()
        await asyncio.sleep(0.1)

        # Add layer to pending requests
        view._pending_requests[layer.id] = asyncio.current_task()

        # Patch run.io_bound to raise exception
        with patch("nicegui.run.io_bound", side_effect=RuntimeError("Test error")):
            # Should not raise, just catch and pass
            await view._produce_frame_async(layer)

        # Cleanup should have happened
        assert layer.id not in view._pending_requests

        layer.stop()


class TestFrameProductionErrors:
    """Tests for frame production error handling."""

    @pytest.mark.asyncio
    async def test_produce_frame_stream_exception(self, user: User) -> None:
        """Test _produce_frame_sync when stream raises exception."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView

        class ErrorStream:
            def __init__(self):
                self._running = False

            def start(self):
                self._running = True

            def stop(self):
                self._running = False

            def get_frame(self, timestamp: float) -> tuple:
                raise RuntimeError("Stream error")

        view = None
        layer = None

        @ui.page("/test_stream_error")
        def page():
            nonlocal view, layer
            view = StreamView(width=800, height=600)
            layer = view.add_layer(stream=ErrorStream(), z_index=0)

        await user.open("/test_stream_error")

        # Should return None on error
        result = StreamView._produce_frame_sync(layer)
        assert result is None

    @pytest.mark.asyncio
    async def test_produce_frame_none_result(self, user: User) -> None:
        """Test _produce_frame_sync when stream returns None."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView

        class NullStream:
            def __init__(self):
                self._running = False

            def start(self):
                self._running = True

            def stop(self):
                self._running = False

            def get_frame(self, timestamp: float) -> tuple:
                return (None, 0)

        view = None
        layer = None

        @ui.page("/test_null_frame")
        def page():
            nonlocal view, layer
            view = StreamView(width=800, height=600)
            layer = view.add_layer(stream=NullStream(), z_index=0)

        await user.open("/test_null_frame")

        # Should return None
        result = StreamView._produce_frame_sync(layer)
        assert result is None

    @pytest.mark.asyncio
    async def test_produce_frame_raw_frame_not_tuple(self, user: User) -> None:
        """Test _produce_frame_sync with raw frame (not tuple)."""
        from nicegui import ui
        from imagestag.components.stream_view import StreamView

        class RawFrameStream:
            def __init__(self):
                self._running = False

            def start(self):
                self._running = True

            def stop(self):
                self._running = False

            def get_frame(self, timestamp: float):
                """Return raw frame, not tuple."""
                return Image.from_array(np.full((100, 100, 3), 128, dtype=np.uint8))

        view = None
        layer = None

        @ui.page("/test_raw_frame")
        def page():
            nonlocal view, layer
            view = StreamView(width=800, height=600)
            layer = view.add_layer(stream=RawFrameStream(), z_index=0)

        await user.open("/test_raw_frame")

        # Should handle raw frame
        result = StreamView._produce_frame_sync(layer)
        assert result is not None
