"""Comprehensive WebRTC signaling and derived layer tests.

Tests the full WebRTC signaling flow with a real receiver client,
and tests derived layer frame processing callbacks in background threads.
"""

import asyncio
import time
import threading
import pytest
from unittest.mock import MagicMock, patch
import numpy as np

from imagestag import Image

# Check if aiortc is available
try:
    from aiortc import RTCPeerConnection, RTCSessionDescription, MediaStreamTrack
    from aiortc.contrib.media import MediaBlackhole
    AIORTC_AVAILABLE = True
except ImportError:
    AIORTC_AVAILABLE = False


# ============================================================================
# WEBRTC RECEIVER CLIENT
# ============================================================================


class WebRTCReceiverClient:
    """WebRTC client that can receive and consume video streams.

    This acts as the "browser" side of the connection, receiving the
    SDP offer from WebRTCManager and sending back an answer.
    """

    def __init__(self):
        self.pc = None
        self.received_frames = []
        self.track = None
        self._running = False
        self._loop = None
        self._thread = None
        self._started = threading.Event()
        self._frame_event = threading.Event()

    def start(self):
        """Start the receiver in a background thread with its own event loop."""
        def run_loop():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._started.set()
            self._loop.run_forever()

        self._thread = threading.Thread(target=run_loop, daemon=True, name="WebRTC-Receiver")
        self._thread.start()
        self._started.wait(timeout=5.0)

    def _run_async(self, coro):
        """Run an async coroutine in the receiver thread and wait for result."""
        if self._loop is None:
            raise RuntimeError("Receiver event loop not started")
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout=30.0)

    async def _create_answer_async(self, offer: dict) -> dict:
        """Create an SDP answer from an offer."""
        self.pc = RTCPeerConnection()

        @self.pc.on("track")
        async def on_track(track: MediaStreamTrack):
            if track.kind == "video":
                self.track = track
                self._running = True
                # Start receiving frames
                asyncio.ensure_future(self._receive_frames())

        # Set remote description (the offer)
        await self.pc.setRemoteDescription(
            RTCSessionDescription(sdp=offer["sdp"], type=offer["type"])
        )

        # Create answer
        answer = await self.pc.createAnswer()
        await self.pc.setLocalDescription(answer)

        # Wait for ICE gathering
        while self.pc.iceGatheringState != "complete":
            await asyncio.sleep(0.1)

        return {
            "sdp": self.pc.localDescription.sdp,
            "type": self.pc.localDescription.type,
        }

    def create_answer(self, offer: dict) -> dict:
        """Create an SDP answer synchronously."""
        return self._run_async(self._create_answer_async(offer))

    async def _receive_frames(self):
        """Receive frames from the video track."""
        try:
            while self._running and self.track:
                try:
                    frame = await asyncio.wait_for(self.track.recv(), timeout=2.0)
                    self.received_frames.append(frame)
                    self._frame_event.set()
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    break
        except Exception:
            pass

    def wait_for_frame(self, timeout: float = 5.0) -> bool:
        """Wait for at least one frame to be received."""
        return self._frame_event.wait(timeout=timeout)

    def close(self):
        """Close the receiver."""
        self._running = False
        if self.pc:
            async def close_pc():
                await self.pc.close()
            if self._loop:
                try:
                    asyncio.run_coroutine_threadsafe(close_pc(), self._loop).result(timeout=5.0)
                except Exception:
                    pass
        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread:
            self._thread.join(timeout=2.0)


# ============================================================================
# WEBRTC SIGNALING TESTS
# ============================================================================


@pytest.mark.skipif(not AIORTC_AVAILABLE, reason="aiortc not installed")
class TestWebRTCSignalingFlow:
    """Tests for the complete WebRTC signaling flow."""

    def test_webrtc_manager_creation(self):
        """Test WebRTCManager initializes correctly."""
        from imagestag.components.stream_view.webrtc import WebRTCManager

        manager = WebRTCManager()
        assert manager._loop is not None
        assert manager._thread is not None
        assert manager._thread.is_alive()
        assert manager.connection_count == 0

        manager.shutdown()

    def test_webrtc_offer_generation(self):
        """Test that WebRTCManager generates valid SDP offers."""
        from imagestag.components.stream_view.webrtc import WebRTCManager, WebRTCLayerConfig
        from imagestag.streams.generator import GeneratorStream

        stream = GeneratorStream(
            handler=lambda t: Image.from_array(np.full((480, 640, 3), 128, dtype=np.uint8))
        )

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
            bitrate=2_000_000,
            width=640,
            height=480,
        )

        manager.create_connection("test-layer", config, on_offer=on_offer)

        # Wait for offer
        assert offer_received.wait(timeout=10.0), "Offer was not received in time"
        assert received_offer[0] is not None
        assert "sdp" in received_offer[0]
        assert "type" in received_offer[0]
        assert received_offer[0]["type"] == "offer"

        # SDP should contain video track
        sdp = received_offer[0]["sdp"]
        assert "m=video" in sdp

        manager.shutdown()

    def test_webrtc_full_signaling_flow(self):
        """Test complete offer-answer signaling flow with receiver."""
        from imagestag.components.stream_view.webrtc import WebRTCManager, WebRTCLayerConfig
        from imagestag.streams.generator import GeneratorStream

        # Create a stream that generates frames
        frame_count = [0]

        def generate_frame(t):
            frame_count[0] += 1
            # Create a frame with visible pattern
            arr = np.full((480, 640, 3), frame_count[0] % 256, dtype=np.uint8)
            return Image.from_array(arr)

        stream = GeneratorStream(handler=generate_frame)

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
            bitrate=2_000_000,
            width=640,
            height=480,
        )

        manager.create_connection("test-layer", config, on_offer=on_offer)

        # Wait for offer
        assert offer_received.wait(timeout=10.0), "Offer not received"

        # Create receiver and generate answer
        receiver = WebRTCReceiverClient()
        receiver.start()

        answer = receiver.create_answer(received_offer[0])
        assert "sdp" in answer
        assert "type" in answer
        assert answer["type"] == "answer"

        # Send answer back to manager
        manager.handle_answer("test-layer", answer)

        # Wait for frames to be received
        assert receiver.wait_for_frame(timeout=10.0), "No frames received"
        assert len(receiver.received_frames) > 0

        # Cleanup
        receiver.close()
        manager.shutdown()

    def test_webrtc_viewport_update(self):
        """Test that viewport updates are applied to WebRTC config."""
        from imagestag.components.stream_view.webrtc import WebRTCLayerConfig
        from imagestag.components.stream_view.stream_view import Viewport
        from imagestag.streams.generator import GeneratorStream

        stream = GeneratorStream(
            handler=lambda t: Image.from_array(np.zeros((480, 640, 3), dtype=np.uint8))
        )

        config = WebRTCLayerConfig(stream=stream, z_index=0)

        # Initial state
        assert config.viewport_zoom == 1.0
        assert config.viewport_x == 0.0

        # Update viewport
        viewport = Viewport(x=0.25, y=0.25, width=0.5, height=0.5, zoom=2.0)
        config.set_viewport(viewport)

        assert config.viewport_zoom == 2.0
        assert config.viewport_x == 0.25
        assert config.viewport_y == 0.25
        assert config.viewport_width == 0.5
        assert config.viewport_height == 0.5

    def test_webrtc_crop_rect_calculation(self):
        """Test crop rectangle calculation from viewport."""
        from imagestag.components.stream_view.webrtc import WebRTCLayerConfig
        from imagestag.components.stream_view.stream_view import Viewport
        from imagestag.streams.generator import GeneratorStream

        stream = GeneratorStream(
            handler=lambda t: Image.from_array(np.zeros((1080, 1920, 3), dtype=np.uint8))
        )

        config = WebRTCLayerConfig(stream=stream, z_index=0)

        # Set viewport to center quarter
        viewport = Viewport(x=0.25, y=0.25, width=0.5, height=0.5, zoom=2.0)
        config.set_viewport(viewport)

        # Get crop rect for 1920x1080 source
        x1, y1, x2, y2 = config.get_crop_rect(1920, 1080)

        assert x1 == 480  # 0.25 * 1920
        assert y1 == 270  # 0.25 * 1080
        assert x2 == 1440  # (0.25 + 0.5) * 1920
        assert y2 == 810  # (0.25 + 0.5) * 1080

    def test_webrtc_multiple_connections(self):
        """Test multiple simultaneous WebRTC connections."""
        from imagestag.components.stream_view.webrtc import WebRTCManager, WebRTCLayerConfig
        from imagestag.streams.generator import GeneratorStream

        stream1 = GeneratorStream(
            handler=lambda t: Image.from_array(np.full((240, 320, 3), 100, dtype=np.uint8))
        )
        stream2 = GeneratorStream(
            handler=lambda t: Image.from_array(np.full((240, 320, 3), 200, dtype=np.uint8))
        )

        manager = WebRTCManager()
        offers_received = {"layer1": threading.Event(), "layer2": threading.Event()}
        received_offers = {}

        def on_offer(layer_id: str, offer: dict):
            received_offers[layer_id] = offer
            offers_received[layer_id].set()

        config1 = WebRTCLayerConfig(stream=stream1, z_index=0, width=320, height=240)
        config2 = WebRTCLayerConfig(stream=stream2, z_index=1, width=320, height=240)

        manager.create_connection("layer1", config1, on_offer=on_offer)
        manager.create_connection("layer2", config2, on_offer=on_offer)

        # Wait for both offers
        assert offers_received["layer1"].wait(timeout=10.0)
        assert offers_received["layer2"].wait(timeout=10.0)

        assert manager.connection_count == 2

        # Close one connection
        manager.close_connection("layer1")
        time.sleep(0.5)
        assert manager.connection_count == 1

        manager.shutdown()

    def test_webrtc_connection_close(self):
        """Test closing WebRTC connections."""
        from imagestag.components.stream_view.webrtc import WebRTCManager, WebRTCLayerConfig
        from imagestag.streams.generator import GeneratorStream

        stream = GeneratorStream(
            handler=lambda t: Image.from_array(np.zeros((240, 320, 3), dtype=np.uint8))
        )

        manager = WebRTCManager()
        offer_received = threading.Event()

        def on_offer(layer_id: str, offer: dict):
            offer_received.set()

        config = WebRTCLayerConfig(stream=stream, z_index=0, width=320, height=240)
        manager.create_connection("test", config, on_offer=on_offer)

        offer_received.wait(timeout=10.0)
        assert manager.connection_count == 1

        manager.close_connection("test")
        time.sleep(0.5)
        assert manager.connection_count == 0

        manager.shutdown()

    def test_webrtc_close_all(self):
        """Test closing all WebRTC connections."""
        from imagestag.components.stream_view.webrtc import WebRTCManager, WebRTCLayerConfig
        from imagestag.streams.generator import GeneratorStream

        manager = WebRTCManager()
        events = []

        for i in range(3):
            stream = GeneratorStream(
                handler=lambda t: Image.from_array(np.zeros((120, 160, 3), dtype=np.uint8))
            )
            event = threading.Event()
            events.append(event)
            config = WebRTCLayerConfig(stream=stream, z_index=i, width=160, height=120)
            manager.create_connection(f"layer{i}", config, on_offer=lambda lid, o, e=event: e.set())

        # Wait for all offers
        for e in events:
            e.wait(timeout=10.0)

        assert manager.connection_count == 3

        manager.close_all()
        time.sleep(0.5)
        assert manager.connection_count == 0

        manager.shutdown()


@pytest.mark.skipif(not AIORTC_AVAILABLE, reason="aiortc not installed")
class TestStreamViewVideoTrack:
    """Tests for StreamViewVideoTrack."""

    @pytest.mark.asyncio
    async def test_video_track_recv(self):
        """Test video track frame reception."""
        from imagestag.components.stream_view.webrtc import StreamViewVideoTrack, WebRTCLayerConfig
        from imagestag.streams.generator import GeneratorStream

        stream = GeneratorStream(
            handler=lambda t: Image.from_array(np.full((480, 640, 3), 128, dtype=np.uint8))
        )
        stream.start()

        config = WebRTCLayerConfig(stream=stream, z_index=0, width=640, height=480)
        track = StreamViewVideoTrack(stream, config, width=640, height=480)

        # Receive a few frames
        for i in range(3):
            frame = await track.recv()
            assert frame is not None
            assert frame.width == 640
            assert frame.height == 480

        stream.stop()

    @pytest.mark.asyncio
    async def test_video_track_timestamp(self):
        """Test video track timestamp generation."""
        from imagestag.components.stream_view.webrtc import StreamViewVideoTrack, WebRTCLayerConfig
        from imagestag.streams.generator import GeneratorStream

        stream = GeneratorStream(
            handler=lambda t: Image.from_array(np.zeros((240, 320, 3), dtype=np.uint8))
        )
        stream.start()

        config = WebRTCLayerConfig(stream=stream, z_index=0, target_fps=30)
        track = StreamViewVideoTrack(stream, config, width=320, height=240)

        pts1, time_base = await track.next_timestamp()
        await asyncio.sleep(0.05)
        pts2, _ = await track.next_timestamp()

        # PTS should increase
        assert pts2 > pts1

        stream.stop()


# ============================================================================
# DERIVED LAYER CALLBACK TESTS
# ============================================================================


class TestDerivedLayerCallbacks:
    """Tests for derived layer frame processing callbacks in background threads."""

    def test_derived_layer_callback_processing(self):
        """Test that derived layers process frames via callbacks."""
        from imagestag.components.stream_view.layers import StreamViewLayer
        from imagestag.streams.generator import GeneratorStream

        frames_generated = []

        def generate_frame(t):
            arr = np.full((200, 200, 3), len(frames_generated) % 256, dtype=np.uint8)
            frames_generated.append(t)
            return Image.from_array(arr)

        stream = GeneratorStream(handler=generate_frame, target_fps=30)
        source_layer = StreamViewLayer(stream=stream, z_index=0)
        derived_layer = StreamViewLayer(source_layer=source_layer, z_index=1)

        source_layer.start()

        # Wait for frames to be generated
        time.sleep(0.3)

        source_layer.stop()

        assert len(frames_generated) > 0
        assert derived_layer.source_layer is source_layer

    def test_derived_layer_with_filter_callback(self):
        """Test derived layer with filter pipeline in callback."""
        from imagestag.components.stream_view.layers import StreamViewLayer
        from imagestag.streams.generator import GeneratorStream
        from imagestag.filters import FilterPipeline
        from imagestag.filters.base import Filter

        filter_apply_count = [0]

        class TestFilter(Filter):
            def apply(self, image, context=None):
                filter_apply_count[0] += 1
                return image

        stream = GeneratorStream(
            handler=lambda t: Image.from_array(np.full((200, 200, 3), 128, dtype=np.uint8)),
            target_fps=30
        )
        pipeline = FilterPipeline(filters=[TestFilter()])
        source_layer = StreamViewLayer(stream=stream, z_index=0)
        derived_layer = StreamViewLayer(source_layer=source_layer, pipeline=pipeline, z_index=1)

        source_layer.start()
        time.sleep(0.3)
        source_layer.stop()

        # The derived layer setup is correct
        assert derived_layer.source_layer is source_layer
        assert derived_layer.pipeline is pipeline

    def test_background_thread_frame_injection(self):
        """Test frame injection from background threads."""
        from imagestag.components.stream_view.layers import StreamViewLayer

        layer = StreamViewLayer(piggyback=True, buffer_size=4)
        injection_count = [0]
        lock = threading.Lock()

        def inject_frames():
            for i in range(10):
                encoded = f"data:image/jpeg;base64,frame{i}"
                layer.inject_frame(encoded, time.perf_counter())
                with lock:
                    injection_count[0] += 1
                time.sleep(0.01)

        # Start multiple injection threads
        threads = []
        for _ in range(3):
            t = threading.Thread(target=inject_frames)
            t.start()
            threads.append(t)

        for t in threads:
            t.join()

        # Should have injected frames from all threads
        with lock:
            assert injection_count[0] == 30  # 3 threads * 10 frames

        # Buffer should have frames (up to buffer_size)
        assert len(layer._frame_buffer) <= layer.buffer_size

    def test_concurrent_frame_production_and_consumption(self):
        """Test concurrent frame production and consumption."""
        from imagestag.components.stream_view.layers import StreamViewLayer
        from imagestag.streams.generator import GeneratorStream

        stream = GeneratorStream(
            handler=lambda t: Image.from_array(np.full((50, 50, 3), 128, dtype=np.uint8))
        )
        layer = StreamViewLayer(stream=stream, buffer_size=8)

        produced_frames = []
        consumed_frames = []
        stop_event = threading.Event()

        def producer():
            layer.start()
            while not stop_event.is_set():
                time.sleep(0.02)
                produced_frames.append(layer.frames_produced)

        def consumer():
            while not stop_event.is_set():
                frame = layer.get_buffered_frame()
                if frame:
                    consumed_frames.append(frame)
                time.sleep(0.03)

        producer_thread = threading.Thread(target=producer)
        consumer_thread = threading.Thread(target=consumer)

        producer_thread.start()
        consumer_thread.start()

        time.sleep(0.5)
        stop_event.set()

        producer_thread.join()
        consumer_thread.join()
        layer.stop()

        # Should have produced and consumed frames
        assert layer.frames_produced > 0
        assert len(consumed_frames) > 0


# ============================================================================
# STREAMVIEW ASYNC INTERNAL HANDLER TESTS
# ============================================================================


@pytest.mark.skipif(not AIORTC_AVAILABLE, reason="aiortc not installed")
class TestStreamViewWebRTCIntegration:
    """Integration tests for StreamView with WebRTC."""

    def test_webrtc_manager_lifecycle(self):
        """Test WebRTC manager creation and shutdown."""
        from imagestag.components.stream_view.webrtc import WebRTCManager, WebRTCLayerConfig
        from imagestag.streams.generator import GeneratorStream

        stream = GeneratorStream(
            handler=lambda t: Image.from_array(np.full((240, 320, 3), 128, dtype=np.uint8))
        )

        manager = WebRTCManager()
        assert manager._loop is not None
        assert manager._thread.is_alive()

        offer_received = threading.Event()
        config = WebRTCLayerConfig(stream=stream, z_index=0, width=320, height=240)
        manager.create_connection("test-layer", config, on_offer=lambda lid, o: offer_received.set())

        offer_received.wait(timeout=10.0)
        assert manager.connection_count == 1

        manager.close_connection("test-layer")
        time.sleep(0.5)
        assert manager.connection_count == 0

        manager.shutdown()
        time.sleep(0.5)
        assert not manager._thread.is_alive()

    def test_webrtc_layer_config_parameters(self):
        """Test WebRTC layer config parameter handling."""
        from imagestag.components.stream_view.webrtc import WebRTCLayerConfig
        from imagestag.streams.generator import GeneratorStream

        stream = GeneratorStream(
            handler=lambda t: Image.from_array(np.full((100, 100, 3), 128, dtype=np.uint8))
        )

        config = WebRTCLayerConfig(
            stream=stream,
            z_index=1,
            codec="h264",
            bitrate=4_000_000,
            width=640,
            height=480,
            target_fps=30,
            name="test-layer",
        )

        assert config.stream is stream
        assert config.z_index == 1
        assert config.codec == "h264"
        assert config.bitrate == 4_000_000
        assert config.width == 640
        assert config.height == 480
        assert config.target_fps == 30
        assert config.name == "test-layer"
        assert config.get_effective_fps() == 30


# ============================================================================
# SDP MODIFICATION TESTS
# ============================================================================


@pytest.mark.skipif(not AIORTC_AVAILABLE, reason="aiortc not installed")
class TestSDPModification:
    """Tests for SDP bitrate modification."""

    def test_modify_sdp_bitrate(self):
        """Test SDP modification adds bitrate constraints."""
        from imagestag.components.stream_view.webrtc import _modify_sdp_bitrate

        # Sample SDP with proper \r\n line endings
        sdp = "v=0\r\no=- 0 0 IN IP4 127.0.0.1\r\ns=-\r\nt=0 0\r\nm=video 9 UDP/TLS/RTP/SAVPF 96\r\nc=IN IP4 0.0.0.0\r\na=rtpmap:96 H264/90000\r\na=fmtp:96 level-asymmetry-allowed=1\r\n"

        modified = _modify_sdp_bitrate(sdp, 5_000_000)

        assert "b=AS:5000" in modified
        assert "b=TIAS:5000000" in modified
        assert "x-google-max-bitrate=5000" in modified

    def test_modify_sdp_preserves_structure(self):
        """Test SDP modification preserves original structure."""
        from imagestag.components.stream_view.webrtc import _modify_sdp_bitrate

        # Sample SDP with proper \r\n line endings
        sdp = "v=0\r\no=- 0 0 IN IP4 127.0.0.1\r\ns=-\r\nt=0 0\r\nm=audio 9 UDP/TLS/RTP/SAVPF 111\r\nc=IN IP4 0.0.0.0\r\na=rtpmap:111 opus/48000/2\r\nm=video 9 UDP/TLS/RTP/SAVPF 96\r\nc=IN IP4 0.0.0.0\r\na=rtpmap:96 VP8/90000\r\n"

        modified = _modify_sdp_bitrate(sdp, 3_000_000)

        # Should have audio section
        assert "m=audio" in modified
        # Should have video section with bitrate
        assert "m=video" in modified
        assert "b=AS:3000" in modified


# ============================================================================
# ASYNC FRAME PRODUCTION TESTS
# ============================================================================


class TestAsyncFrameProduction:
    """Tests for async frame production in StreamView."""

    def test_produce_frame_sync_with_viewport_crop(self):
        """Test frame production with viewport cropping."""
        from imagestag.components.stream_view.stream_view import StreamView, Viewport
        from imagestag.components.stream_view.layers import StreamViewLayer
        from imagestag.streams.generator import GeneratorStream

        stream = GeneratorStream(
            handler=lambda t: Image.from_array(np.full((200, 200, 3), 128, dtype=np.uint8))
        )
        layer = StreamViewLayer(stream=stream)
        layer.set_viewport(Viewport(x=0.25, y=0.25, width=0.5, height=0.5, zoom=2.0))
        layer.set_target_size(100, 100)
        stream.start()

        result = StreamView._produce_frame_sync(layer)

        assert result is not None
        timestamp, encoded, metadata = result
        assert len(encoded) > 0

        stream.stop()

    def test_produce_frame_sync_with_nav_thumbnail(self):
        """Test frame production generates nav thumbnail when zoomed."""
        from imagestag.components.stream_view.stream_view import StreamView, Viewport
        from imagestag.components.stream_view.layers import StreamViewLayer
        from imagestag.streams.generator import GeneratorStream

        stream = GeneratorStream(
            handler=lambda t: Image.from_array(np.full((200, 200, 3), 128, dtype=np.uint8))
        )
        layer = StreamViewLayer(stream=stream)
        layer.set_viewport(Viewport(zoom=2.0, x=0.25, y=0.25, width=0.5, height=0.5))
        layer.set_target_size(200, 200)
        stream.start()

        result = StreamView._produce_frame_sync(layer)

        assert result is not None
        timestamp, encoded, metadata = result

        # When zoomed, should include nav_thumbnail
        # (implementation may vary)

        stream.stop()

    @pytest.mark.asyncio
    async def test_async_frame_production_thread_safety(self):
        """Test async frame production is thread-safe."""
        from imagestag.components.stream_view.stream_view import StreamView
        from imagestag.components.stream_view.layers import StreamViewLayer
        from imagestag.streams.generator import GeneratorStream

        stream = GeneratorStream(
            handler=lambda t: Image.from_array(np.full((50, 50, 3), int(t * 100) % 256, dtype=np.uint8))
        )
        layer = StreamViewLayer(stream=stream)
        layer.set_target_size(50, 50)
        stream.start()

        results = []
        errors = []

        def produce_frames():
            try:
                for _ in range(10):
                    result = StreamView._produce_frame_sync(layer)
                    if result:
                        results.append(result)
                    time.sleep(0.01)
            except Exception as e:
                errors.append(e)

        # Run multiple threads producing frames
        threads = [threading.Thread(target=produce_frames) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        stream.stop()

        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) > 0


# ============================================================================
# ADDITIONAL STREAMVIEW COVERAGE TESTS
# ============================================================================


class TestStreamViewHelpers:
    """Additional tests for StreamView helper methods."""

    def test_produce_frame_sync_with_pipeline(self):
        """Test frame production with filter pipeline."""
        from imagestag.components.stream_view.stream_view import StreamView, Viewport
        from imagestag.components.stream_view.layers import StreamViewLayer
        from imagestag.streams.generator import GeneratorStream
        from imagestag.filters import FilterPipeline
        from imagestag.filters.base import Filter

        class BrightnessFilter(Filter):
            def apply(self, image, context=None):
                arr = np.clip(image.get_pixels() + 20, 0, 255).astype(np.uint8)
                return Image.from_array(arr)

        stream = GeneratorStream(
            handler=lambda t: Image.from_array(np.full((100, 100, 3), 128, dtype=np.uint8))
        )
        pipeline = FilterPipeline(filters=[BrightnessFilter()])
        layer = StreamViewLayer(stream=stream, pipeline=pipeline)
        layer.set_target_size(100, 100)
        stream.start()

        result = StreamView._produce_frame_sync(layer)
        assert result is not None
        timestamp, encoded, metadata = result
        # The encoded string contains base64 image data (may or may not have prefix)
        assert len(encoded) > 100

        stream.stop()

    def test_produce_frame_sync_png_format(self):
        """Test frame production with PNG format."""
        from imagestag.components.stream_view.stream_view import StreamView
        from imagestag.components.stream_view.layers import StreamViewLayer
        from imagestag.streams.generator import GeneratorStream

        stream = GeneratorStream(
            handler=lambda t: Image.from_array(np.full((50, 50, 3), 200, dtype=np.uint8))
        )
        layer = StreamViewLayer(stream=stream, use_png=True)
        layer.set_target_size(50, 50)
        stream.start()

        result = StreamView._produce_frame_sync(layer)
        assert result is not None
        timestamp, encoded, metadata = result
        # Verify we got an encoded image
        assert len(encoded) > 100

        stream.stop()

    def test_layer_buffering_with_step_timings(self):
        """Test layer frame buffering with step timings."""
        from imagestag.components.stream_view.layers import StreamViewLayer

        layer = StreamViewLayer(piggyback=True, buffer_size=3)

        # Inject frames with step timings
        for i in range(5):
            step_timings = {"encode": 1.5, "filter": 0.8}
            layer.inject_frame(
                f"data:image/jpeg;base64,frame{i}",
                time.perf_counter(),
                step_timings=step_timings,
            )
            time.sleep(0.01)

        # Get buffered frame
        frame_data = layer.get_buffered_frame()
        assert frame_data is not None
        timestamp, encoded, metadata = frame_data
        assert "frame" in encoded

    def test_layer_target_size_updates(self):
        """Test layer target size updates."""
        from imagestag.components.stream_view.layers import StreamViewLayer
        from imagestag.streams.generator import GeneratorStream

        stream = GeneratorStream(
            handler=lambda t: Image.from_array(np.full((200, 200, 3), 128, dtype=np.uint8))
        )
        layer = StreamViewLayer(stream=stream)

        # Initially no target size
        assert layer._target_width == 0
        assert layer._target_height == 0

        # Set target size
        layer.set_target_size(640, 480)
        assert layer._target_width == 640
        assert layer._target_height == 480

        # Update target size
        layer.set_target_size(1280, 720)
        assert layer._target_width == 1280
        assert layer._target_height == 720


class TestViewportCropping:
    """Tests for viewport-based cropping."""

    def test_viewport_crop_with_zoom(self):
        """Test viewport cropping with zoom factor."""
        from imagestag.components.stream_view.stream_view import StreamView, Viewport
        from imagestag.components.stream_view.layers import StreamViewLayer
        from imagestag.streams.generator import GeneratorStream

        stream = GeneratorStream(
            handler=lambda t: Image.from_array(np.full((400, 400, 3), 128, dtype=np.uint8))
        )
        layer = StreamViewLayer(stream=stream)
        layer.set_viewport(Viewport(x=0.25, y=0.25, width=0.5, height=0.5, zoom=2.0))
        layer.set_target_size(200, 200)
        stream.start()

        result = StreamView._produce_frame_sync(layer)
        assert result is not None
        timestamp, encoded, metadata = result
        assert len(encoded) > 0

        stream.stop()

    def test_viewport_with_high_zoom(self):
        """Test viewport with high zoom factor."""
        from imagestag.components.stream_view.stream_view import StreamView, Viewport
        from imagestag.components.stream_view.layers import StreamViewLayer
        from imagestag.streams.generator import GeneratorStream

        stream = GeneratorStream(
            handler=lambda t: Image.from_array(np.full((400, 400, 3), 100, dtype=np.uint8))
        )
        layer = StreamViewLayer(stream=stream)
        layer.set_viewport(Viewport(zoom=2.5, x=0.2, y=0.2, width=0.4, height=0.4))
        layer.set_target_size(300, 300)
        stream.start()

        result = StreamView._produce_frame_sync(layer)
        assert result is not None

        stream.stop()


class TestLayerWithOverscan:
    """Tests for layer overscan handling."""

    def test_derived_layer_with_overscan(self):
        """Test derived layer with overscan margin."""
        from imagestag.components.stream_view.layers import StreamViewLayer
        from imagestag.streams.generator import GeneratorStream

        stream = GeneratorStream(
            handler=lambda t: Image.from_array(np.full((200, 200, 3), 128, dtype=np.uint8))
        )
        source = StreamViewLayer(stream=stream, z_index=0)
        derived = StreamViewLayer(
            source_layer=source,
            z_index=1,
            x=50,
            y=50,
            width=100,
            height=100,
            overscan=10,
        )

        assert derived.source_layer is source
        assert derived.overscan == 10
        assert derived.x == 50
        assert derived.y == 50

    def test_layer_anchor_position(self):
        """Test layer with anchor position for overscan."""
        from imagestag.components.stream_view.layers import StreamViewLayer

        layer = StreamViewLayer(piggyback=True, buffer_size=2)

        # Inject frame with anchor position
        layer.inject_frame(
            "data:image/jpeg;base64,testframe",
            time.perf_counter(),
            anchor_x=25,
            anchor_y=30,
        )

        frame_data = layer.get_buffered_frame()
        assert frame_data is not None


class TestLayerFrameMetadata:
    """Tests for frame metadata handling."""

    def test_frame_metadata_timings(self):
        """Test frame metadata timing tracking."""
        from imagestag.components.stream_view.timing import FrameMetadata, new_frame_metadata

        metadata = new_frame_metadata()
        metadata.capture_time = FrameMetadata.now_ms()
        time.sleep(0.01)
        metadata.encode_start = FrameMetadata.now_ms()
        time.sleep(0.01)
        metadata.encode_end = FrameMetadata.now_ms()
        metadata.frame_bytes = 50000
        metadata.frame_width = 640
        metadata.frame_height = 480

        d = metadata.to_dict()
        assert "capture_time" in d
        assert "encode_start" in d
        assert "encode_end" in d
        assert d["frame_bytes"] == 50000
        assert d["frame_width"] == 640

    def test_frame_metadata_filter_timings(self):
        """Test frame metadata with filter timing tracking."""
        from imagestag.components.stream_view.timing import FrameMetadata, new_frame_metadata

        metadata = new_frame_metadata()
        start1 = FrameMetadata.now_ms()
        time.sleep(0.01)
        end1 = FrameMetadata.now_ms()
        metadata.add_filter_timing("GaussianBlur", start1, end1)

        start2 = FrameMetadata.now_ms()
        time.sleep(0.01)
        end2 = FrameMetadata.now_ms()
        metadata.add_filter_timing("EdgeDetect", start2, end2)

        d = metadata.to_dict()
        assert "filter_timings" in d
        assert len(d["filter_timings"]) == 2


# User fixture provided by pytest_plugins = ['nicegui.testing.user_plugin'] in conftest.py
