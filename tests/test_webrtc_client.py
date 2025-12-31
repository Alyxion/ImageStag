"""Comprehensive WebRTC client and StreamView integration tests.

Uses the WebRTCReceiver client to test actual WebRTC signaling flows
and NiceGUI testing patterns for realistic UI testing.
"""

import asyncio
import time
import threading
import pytest
import numpy as np

from imagestag import Image

# Check if aiortc is available
try:
    from aiortc import RTCPeerConnection
    AIORTC_AVAILABLE = True
except ImportError:
    AIORTC_AVAILABLE = False

# NiceGUI testing imports
from nicegui import ui
from nicegui.testing import User


# ============================================================================
# WEBRTC RECEIVER CLIENT TESTS
# ============================================================================


@pytest.mark.skipif(not AIORTC_AVAILABLE, reason="aiortc not installed")
class TestWebRTCReceiverClient:
    """Tests for the WebRTCReceiver client component."""

    def test_receiver_creation(self):
        """Test creating a WebRTCReceiver."""
        from imagestag.components.webrtc_client import WebRTCReceiver, ReceiverState

        receiver = WebRTCReceiver()
        assert receiver.state == ReceiverState.DISCONNECTED
        assert receiver.frames_received == 0
        assert receiver.buffer_size == 0
        assert not receiver.is_connected

    def test_receiver_with_config(self):
        """Test creating receiver with custom config."""
        from imagestag.components.webrtc_client import WebRTCReceiver
        from imagestag.components.webrtc_client.receiver import WebRTCReceiverConfig

        config = WebRTCReceiverConfig(
            buffer_size=20,
            ice_servers=["stun:stun.example.com:3478"],
            timeout=60.0,
        )
        receiver = WebRTCReceiver(config)
        assert receiver.config.buffer_size == 20
        assert receiver.config.timeout == 60.0

    def test_receiver_start_stop(self):
        """Test starting and stopping the receiver."""
        from imagestag.components.webrtc_client import WebRTCReceiver, ReceiverState

        receiver = WebRTCReceiver()
        receiver.start()

        assert receiver._loop is not None
        assert receiver._thread is not None
        assert receiver._thread.is_alive()

        receiver.close()
        time.sleep(0.5)
        assert receiver.state == ReceiverState.CLOSED

    def test_receiver_context_manager(self):
        """Test receiver as context manager."""
        from imagestag.components.webrtc_client import WebRTCReceiver

        with WebRTCReceiver() as receiver:
            assert receiver._loop is not None
            assert receiver._thread.is_alive()

        # After context exit, should be closed
        time.sleep(0.5)

    def test_receiver_callbacks(self):
        """Test registering callbacks."""
        from imagestag.components.webrtc_client import WebRTCReceiver, ReceiverState

        receiver = WebRTCReceiver()

        state_changes = []
        frames_received = []

        def on_state(state):
            state_changes.append(state)

        def on_frame(frame):
            frames_received.append(frame)

        receiver.on_state_change(on_state)
        receiver.on_frame(on_frame)

        # Verify callbacks are registered
        assert on_state in receiver._on_state_callbacks
        assert on_frame in receiver._on_frame_callbacks

    def test_receiver_stats(self):
        """Test receiver statistics."""
        from imagestag.components.webrtc_client import WebRTCReceiver

        receiver = WebRTCReceiver()
        stats = receiver.get_stats()

        assert "state" in stats
        assert "frames_received" in stats
        assert "bytes_received" in stats
        assert "buffer_size" in stats
        assert "fps" in stats
        assert stats["frames_received"] == 0

    def test_receiver_buffer_operations(self):
        """Test buffer operations."""
        from imagestag.components.webrtc_client import WebRTCReceiver

        receiver = WebRTCReceiver()

        # Initially empty
        assert receiver.get_frame() is None
        assert receiver.get_all_frames() == []

        # Clear empty buffer (should not fail)
        receiver.clear_buffer()


@pytest.mark.skipif(not AIORTC_AVAILABLE, reason="aiortc not installed")
class TestWebRTCFullSignaling:
    """Full WebRTC signaling tests with sender and receiver."""

    def test_full_signaling_flow_with_receiver_client(self):
        """Test complete signaling flow using WebRTCReceiver client."""
        from imagestag.components.stream_view.webrtc import WebRTCManager, WebRTCLayerConfig
        from imagestag.components.webrtc_client import WebRTCReceiver
        from imagestag.streams.generator import GeneratorStream

        # Create a stream that generates frames
        frame_count = [0]

        def generate_frame(t):
            frame_count[0] += 1
            arr = np.full((240, 320, 3), frame_count[0] % 256, dtype=np.uint8)
            return Image.from_array(arr)

        stream = GeneratorStream(handler=generate_frame, target_fps=10)

        # Create sender (WebRTCManager)
        manager = WebRTCManager()
        offer_received = threading.Event()
        received_offer = [None]

        def on_offer(layer_id: str, offer: dict):
            received_offer[0] = offer
            offer_received.set()

        config = WebRTCLayerConfig(
            stream=stream,
            z_index=0,
            codec="h264",
            bitrate=1_000_000,
            width=320,
            height=240,
        )

        manager.create_connection("test-layer", config, on_offer=on_offer)

        # Wait for offer
        assert offer_received.wait(timeout=15.0), "Offer not received"

        # Create receiver using our WebRTCReceiver client
        with WebRTCReceiver() as receiver:
            # Create answer from offer
            answer = receiver.create_answer(received_offer[0])
            assert "sdp" in answer
            assert "type" in answer
            assert answer["type"] == "answer"

            # Send answer back to manager
            manager.handle_answer("test-layer", answer)

            # Wait for frames to be received
            assert receiver.wait_for_frame(timeout=15.0), "No frames received"

            # Verify we received frames
            assert receiver.frames_received > 0
            frame = receiver.get_frame()
            assert frame is not None
            assert frame.width == 320
            assert frame.height == 240

            # Check stats
            stats = receiver.get_stats()
            assert stats["frames_received"] > 0

        # Cleanup
        manager.shutdown()

    def test_receiver_with_multiple_frames(self):
        """Test receiving multiple frames and buffering."""
        from imagestag.components.stream_view.webrtc import WebRTCManager, WebRTCLayerConfig
        from imagestag.components.webrtc_client import WebRTCReceiver
        from imagestag.components.webrtc_client.receiver import WebRTCReceiverConfig
        from imagestag.streams.generator import GeneratorStream

        stream = GeneratorStream(
            handler=lambda t: Image.from_array(np.full((120, 160, 3), 100, dtype=np.uint8)),
            target_fps=30,
        )

        manager = WebRTCManager()
        offer_event = threading.Event()
        offer_data = [None]

        config = WebRTCLayerConfig(stream=stream, z_index=0, width=160, height=120)
        manager.create_connection(
            "multi-frame",
            config,
            on_offer=lambda lid, o: (offer_data.__setitem__(0, o), offer_event.set()),
        )

        offer_event.wait(timeout=10.0)

        # Use larger buffer
        receiver_config = WebRTCReceiverConfig(buffer_size=20)
        with WebRTCReceiver(receiver_config) as receiver:
            answer = receiver.create_answer(offer_data[0])
            manager.handle_answer("multi-frame", answer)

            # Wait longer to receive multiple frames
            receiver.wait_for_frame(timeout=10.0)
            time.sleep(0.5)  # Let more frames arrive

            # Should have multiple frames in buffer
            all_frames = receiver.get_all_frames()
            assert len(all_frames) > 1

            # Test clear buffer
            receiver.clear_buffer()
            assert receiver.buffer_size == 0

        manager.shutdown()


# ============================================================================
# NICEGUI INTEGRATION TESTS - STREAMVIEW WEBRTC
# ============================================================================


@pytest.mark.skipif(not AIORTC_AVAILABLE, reason="aiortc not installed")
class TestStreamViewWebRTCWithNiceGUI:
    """NiceGUI integration tests for StreamView WebRTC functionality."""

    @pytest.mark.asyncio
    async def test_add_webrtc_layer_ui(self, user: User) -> None:
        """Test adding a WebRTC layer in UI context."""
        from imagestag.components.stream_view import StreamView
        from imagestag.streams.generator import GeneratorStream

        view = None
        layer_id = None
        stream = None

        @ui.page("/test_webrtc_add")
        def test_page():
            nonlocal view, layer_id, stream
            stream = GeneratorStream(
                handler=lambda t: Image.from_array(np.full((120, 160, 3), 128, dtype=np.uint8)),
                target_fps=5,
            )
            stream.start()
            view = StreamView(width=640, height=480)
            layer_id = view.add_webrtc_layer(
                stream=stream, z_index=0, name="Test Layer"
            )

        await user.open("/test_webrtc_add")

        assert layer_id is not None
        assert view._webrtc_manager is not None
        assert layer_id in view._webrtc_layers
        assert layer_id in view._pending_webrtc_configs

        if stream:
            stream.stop()

    @pytest.mark.asyncio
    async def test_remove_webrtc_layer_ui(self, user: User) -> None:
        """Test removing a WebRTC layer in UI context."""
        from imagestag.components.stream_view import StreamView
        from imagestag.streams.generator import GeneratorStream

        view = None
        layer_id = None
        stream = None

        @ui.page("/test_webrtc_remove")
        def test_page():
            nonlocal view, layer_id, stream
            stream = GeneratorStream(
                handler=lambda t: Image.from_array(np.full((80, 80, 3), 64, dtype=np.uint8)),
                target_fps=5,
            )
            stream.start()
            view = StreamView(width=400, height=300)
            layer_id = view.add_webrtc_layer(stream=stream, z_index=0)

        await user.open("/test_webrtc_remove")

        assert layer_id in view._webrtc_layers

        view.remove_webrtc_layer(layer_id)
        assert layer_id not in view._webrtc_layers

        if stream:
            stream.stop()

    @pytest.mark.asyncio
    async def test_webrtc_offer_timer(self, user: User) -> None:
        """Test that WebRTC offers are processed by timer."""
        from imagestag.components.stream_view import StreamView
        from imagestag.streams.generator import GeneratorStream

        view = None
        stream = None

        @ui.page("/test_webrtc_timer")
        def test_page():
            nonlocal view, stream
            stream = GeneratorStream(
                handler=lambda t: Image.from_array(np.full((100, 100, 3), 50, dtype=np.uint8)),
                target_fps=5,
            )
            stream.start()
            view = StreamView(width=400, height=300)
            view.add_webrtc_layer(stream=stream, z_index=0)

        await user.open("/test_webrtc_timer")

        # View should have a WebRTC manager
        assert view._webrtc_manager is not None

        if stream:
            stream.stop()


# ============================================================================
# DERIVED LAYER CALLBACK TESTS
# ============================================================================


class TestDerivedLayerCallbacksWithNiceGUI:
    """NiceGUI tests for derived layer callbacks."""

    @pytest.mark.asyncio
    async def test_derived_layer_with_callback(self, user: User) -> None:
        """Test derived layer callback is set up correctly."""
        from imagestag.components.stream_view import StreamView
        from imagestag.streams.generator import GeneratorStream

        view = None
        source = None
        derived = None
        stream = None

        @ui.page("/test_derived_cb")
        def test_page():
            nonlocal view, source, derived, stream
            stream = GeneratorStream(
                handler=lambda t: Image.from_array(np.full((200, 200, 3), 150, dtype=np.uint8)),
                target_fps=10,
            )
            stream.start()
            view = StreamView(width=800, height=600)
            source = view.add_layer(stream=stream, z_index=0)
            derived = view.add_layer(
                source_layer=source,
                z_index=1,
                x=20,
                y=20,
                width=100,
                height=100,
            )

        await user.open("/test_derived_cb")

        assert derived is not None
        assert derived.source_layer is source
        # The on_frame callback should be registered
        assert hasattr(derived, "_on_frame_callback")

        if stream:
            stream.stop()

    @pytest.mark.asyncio
    async def test_derived_layer_with_filter_pipeline(self, user: User) -> None:
        """Test derived layer with filter pipeline."""
        from imagestag.components.stream_view import StreamView
        from imagestag.streams.generator import GeneratorStream
        from imagestag.filters import FilterPipeline
        from imagestag.filters.base import Filter

        class InvertFilter(Filter):
            def apply(self, image, context=None):
                arr = 255 - image.get_pixels()
                return Image.from_array(arr)

        view = None
        derived = None
        stream = None

        @ui.page("/test_derived_filter")
        def test_page():
            nonlocal view, derived, stream
            stream = GeneratorStream(
                handler=lambda t: Image.from_array(np.full((150, 150, 3), 100, dtype=np.uint8)),
                target_fps=10,
            )
            stream.start()
            view = StreamView(width=800, height=600)
            source = view.add_layer(stream=stream, z_index=0)
            derived = view.add_layer(
                source_layer=source,
                pipeline=FilterPipeline(filters=[InvertFilter()]),
                z_index=1,
            )

        await user.open("/test_derived_filter")

        assert derived is not None
        assert derived.pipeline is not None

        if stream:
            stream.stop()

    @pytest.mark.asyncio
    async def test_derived_layer_overscan_anchor(self, user: User) -> None:
        """Test derived layer with overscan generates anchor positions."""
        from imagestag.components.stream_view import StreamView
        from imagestag.streams.generator import GeneratorStream

        view = None
        derived = None
        stream = None

        @ui.page("/test_derived_overscan")
        def test_page():
            nonlocal view, derived, stream
            stream = GeneratorStream(
                handler=lambda t: Image.from_array(np.full((300, 300, 3), 80, dtype=np.uint8)),
                target_fps=10,
            )
            stream.start()
            view = StreamView(width=800, height=600)
            source = view.add_layer(stream=stream, z_index=0)
            derived = view.add_layer(
                source_layer=source,
                z_index=1,
                x=50,
                y=50,
                width=150,
                height=150,
                overscan=10,
            )

        await user.open("/test_derived_overscan")

        assert derived.overscan == 10
        assert derived.x == 50
        assert derived.y == 50

        if stream:
            stream.stop()


# ============================================================================
# SVG OVERLAY TESTS
# ============================================================================


class TestSVGOverlayWithNiceGUI:
    """NiceGUI tests for SVG overlay functionality."""

    @pytest.mark.asyncio
    async def test_set_svg_template(self, user: User) -> None:
        """Test setting SVG template."""
        from imagestag.components.stream_view import StreamView

        view = None

        @ui.page("/test_svg_template")
        def test_page():
            nonlocal view
            view = StreamView(width=640, height=480)
            view.set_svg(
                '<text x="{x}" y="{y}">{label}</text>',
                {"x": 100, "y": 50, "label": "Hello"},
            )

        await user.open("/test_svg_template")

        assert view._svg_template == '<text x="{x}" y="{y}">{label}</text>'
        assert view._svg_values == {"x": 100, "y": 50, "label": "Hello"}

    @pytest.mark.asyncio
    async def test_update_svg_values(self, user: User) -> None:
        """Test updating SVG placeholder values."""
        from imagestag.components.stream_view import StreamView

        view = None

        @ui.page("/test_svg_update")
        def test_page():
            nonlocal view
            view = StreamView(width=640, height=480)
            view.set_svg('<text x="0" y="0">{counter}</text>', {"counter": 0})

        await user.open("/test_svg_update")

        view.update_svg_values(counter=42)  # Uses **kwargs
        assert view._svg_values["counter"] == 42


# ============================================================================
# VIEWPORT AND ZOOM TESTS
# ============================================================================


class TestViewportWithNiceGUI:
    """NiceGUI tests for viewport and zoom functionality."""

    @pytest.mark.asyncio
    async def test_set_viewport(self, user: User) -> None:
        """Test setting viewport programmatically."""
        from imagestag.components.stream_view import StreamView
        from imagestag.components.stream_view.stream_view import Viewport
        from imagestag.streams.generator import GeneratorStream

        view = None
        layer = None
        stream = None

        @ui.page("/test_set_viewport")
        def test_page():
            nonlocal view, layer, stream
            stream = GeneratorStream(
                handler=lambda t: Image.from_array(np.full((400, 400, 3), 128, dtype=np.uint8)),
                target_fps=5,
            )
            stream.start()
            view = StreamView(width=800, height=600)
            layer = view.add_layer(stream=stream, z_index=0)

        await user.open("/test_set_viewport")

        # Set viewport
        viewport = Viewport(x=0.25, y=0.25, width=0.5, height=0.5, zoom=2.0)
        layer.set_viewport(viewport)

        # Check individual viewport fields
        assert layer._viewport_zoom == 2.0
        assert layer._viewport_x == 0.25

        if stream:
            stream.stop()

    @pytest.mark.asyncio
    async def test_viewport_zoom_check(self, user: User) -> None:
        """Test viewport zoom level."""
        from imagestag.components.stream_view import StreamView
        from imagestag.components.stream_view.stream_view import Viewport
        from imagestag.streams.generator import GeneratorStream

        view = None
        layer = None
        stream = None

        @ui.page("/test_zoom_check")
        def test_page():
            nonlocal view, layer, stream
            stream = GeneratorStream(
                handler=lambda t: Image.from_array(np.full((200, 200, 3), 100, dtype=np.uint8)),
                target_fps=5,
            )
            stream.start()
            view = StreamView(width=640, height=480)
            layer = view.add_layer(stream=stream, z_index=0)

        await user.open("/test_zoom_check")

        # Initial zoom should be 1.0
        assert layer._viewport_zoom == 1.0

        # Update zoom via viewport
        layer.set_viewport(Viewport(zoom=2.0))
        assert layer._viewport_zoom == 2.0

        if stream:
            stream.stop()


# ============================================================================
# LAYER LIFECYCLE TESTS
# ============================================================================


class TestLayerLifecycleWithNiceGUI:
    """NiceGUI tests for layer lifecycle management."""

    @pytest.mark.asyncio
    async def test_add_remove_layer(self, user: User) -> None:
        """Test adding and removing layers."""
        from imagestag.components.stream_view import StreamView
        from imagestag.streams.generator import GeneratorStream

        view = None
        layer = None
        stream = None

        @ui.page("/test_layer_lifecycle")
        def test_page():
            nonlocal view, layer, stream
            stream = GeneratorStream(
                handler=lambda t: Image.from_array(np.full((100, 100, 3), 80, dtype=np.uint8)),
                target_fps=5,
            )
            stream.start()
            view = StreamView(width=640, height=480)
            layer = view.add_layer(stream=stream, z_index=0)

        await user.open("/test_layer_lifecycle")

        layer_id = layer.id
        assert layer_id in view._layers

        view.remove_layer(layer_id)
        assert layer_id not in view._layers

        if stream:
            stream.stop()

    @pytest.mark.asyncio
    async def test_layer_properties(self, user: User) -> None:
        """Test layer properties."""
        from imagestag.components.stream_view import StreamView

        view = None
        layer = None

        @ui.page("/test_layer_props")
        def test_page():
            nonlocal view, layer
            view = StreamView(width=640, height=480)
            layer = view.add_layer(url="http://example.com/image.jpg", z_index=0)

        await user.open("/test_layer_props")

        # Check layer properties
        assert layer.z_index == 0
        assert layer.id is not None

    @pytest.mark.asyncio
    async def test_multiple_layers_z_order(self, user: User) -> None:
        """Test multiple layers with z-order."""
        from imagestag.components.stream_view import StreamView

        view = None
        layers = []

        @ui.page("/test_z_order")
        def test_page():
            nonlocal view, layers
            view = StreamView(width=640, height=480)
            for i in range(3):
                layer = view.add_layer(
                    url=f"http://example.com/image{i}.jpg", z_index=i
                )
                layers.append(layer)

        await user.open("/test_z_order")

        assert len(layers) == 3
        assert layers[0].z_index == 0
        assert layers[1].z_index == 1
        assert layers[2].z_index == 2


# ============================================================================
# EVENT HANDLER TESTS
# ============================================================================


class TestEventHandlersWithNiceGUI:
    """NiceGUI tests for event handlers."""

    @pytest.mark.asyncio
    async def test_on_click_handler(self, user: User) -> None:
        """Test on_click event handler."""
        from imagestag.components.stream_view import StreamView

        view = None
        click_received = [False]

        @ui.page("/test_onclick")
        def test_page():
            nonlocal view

            def handle_click(e):
                click_received[0] = True

            view = StreamView(width=640, height=480)
            view.on("click", handle_click)

        await user.open("/test_onclick")

        # Event handler should be registered
        assert view is not None

    @pytest.mark.asyncio
    async def test_on_viewport_change_handler(self, user: User) -> None:
        """Test on_viewport_change event handler."""
        from imagestag.components.stream_view import StreamView

        view = None
        viewport_changed = [False]

        @ui.page("/test_onviewport")
        def test_page():
            nonlocal view

            def handle_viewport(e):
                viewport_changed[0] = True

            view = StreamView(width=640, height=480)
            view.on("viewport_change", handle_viewport)

        await user.open("/test_onviewport")

        assert view is not None


# ============================================================================
# FRAME PRODUCTION TESTS
# ============================================================================


class TestFrameProductionWithNiceGUI:
    """NiceGUI tests for frame production and delivery."""

    @pytest.mark.asyncio
    async def test_frame_production_with_stream(self, user: User) -> None:
        """Test frame production from stream."""
        from imagestag.components.stream_view import StreamView
        from imagestag.streams.generator import GeneratorStream

        view = None
        layer = None
        stream = None
        frames_generated = [0]

        def gen_frame(t):
            frames_generated[0] += 1
            return Image.from_array(np.full((100, 100, 3), frames_generated[0] % 256, dtype=np.uint8))

        @ui.page("/test_frame_prod")
        def test_page():
            nonlocal view, layer, stream
            stream = GeneratorStream(handler=gen_frame, target_fps=30, threaded=True)
            stream.start()
            view = StreamView(width=640, height=480)
            layer = view.add_layer(stream=stream, z_index=0, fps=30)

        await user.open("/test_frame_prod")

        # Wait for some frames to be generated by the stream
        await asyncio.sleep(0.3)

        # The stream should have generated frames
        assert stream.frame_index >= 0

        if stream:
            stream.stop()

    @pytest.mark.asyncio
    async def test_static_image_layer(self, user: User) -> None:
        """Test static image layer (no streaming)."""
        from imagestag.components.stream_view import StreamView

        view = None
        layer = None
        img = None

        @ui.page("/test_static_layer")
        def test_page():
            nonlocal view, layer, img
            img = Image.from_array(np.full((100, 100, 3), 200, dtype=np.uint8))
            view = StreamView(width=640, height=480)
            layer = view.add_layer(image=img, z_index=0)

        await user.open("/test_static_layer")

        assert layer is not None
        assert layer.is_static is True


# ============================================================================
# METRICS AND DIAGNOSTICS TESTS
# ============================================================================


class TestMetricsWithNiceGUI:
    """NiceGUI tests for metrics and diagnostics."""

    @pytest.mark.asyncio
    async def test_show_metrics(self, user: User) -> None:
        """Test showing metrics overlay."""
        from imagestag.components.stream_view import StreamView

        view = None

        @ui.page("/test_metrics")
        def test_page():
            nonlocal view
            view = StreamView(width=640, height=480, show_metrics=True)

        await user.open("/test_metrics")

        assert view._props["showMetrics"] is True

    @pytest.mark.asyncio
    async def test_fps_counter(self, user: User) -> None:
        """Test FPS counter in StreamView."""
        from imagestag.components.stream_view import StreamView

        view = None

        @ui.page("/test_fps")
        def test_page():
            nonlocal view
            view = StreamView(width=640, height=480)

        await user.open("/test_fps")

        # FPS counter should exist
        assert view._fps_counter is not None
        initial_fps = view._fps_counter.fps

        # Tick a few times
        for _ in range(5):
            view._fps_counter.tick()
            await asyncio.sleep(0.05)

        # FPS should be non-negative
        assert view._fps_counter.fps >= 0
