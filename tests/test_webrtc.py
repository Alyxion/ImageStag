"""Tests for WebRTC components."""

import asyncio
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import numpy as np

from imagestag import Image
from imagestag.streams.generator import GeneratorStream


class TestModifySdpBitrate:
    """Tests for SDP bitrate modification."""

    def test_modify_sdp_bitrate_adds_bandwidth_line(self):
        """Test that bandwidth line is added after c= line in video section."""
        from imagestag.components.stream_view.webrtc import _modify_sdp_bitrate

        # Minimal SDP with video section
        sdp = (
            "v=0\r\n"
            "o=- 0 0 IN IP4 127.0.0.1\r\n"
            "s=-\r\n"
            "m=video 9 UDP/TLS/RTP/SAVPF 96\r\n"
            "c=IN IP4 0.0.0.0\r\n"
            "a=rtpmap:96 H264/90000\r\n"
            "a=fmtp:96 level-asymmetry-allowed=1\r\n"
        )

        result = _modify_sdp_bitrate(sdp, 5_000_000)

        # Check bandwidth lines added
        assert "b=AS:5000" in result
        assert "b=TIAS:5000000" in result

    def test_modify_sdp_bitrate_adds_google_constraints(self):
        """Test that x-google bitrate constraints are added to fmtp lines."""
        from imagestag.components.stream_view.webrtc import _modify_sdp_bitrate

        sdp = (
            "v=0\r\n"
            "m=video 9 UDP/TLS/RTP/SAVPF 96\r\n"
            "c=IN IP4 0.0.0.0\r\n"
            "a=fmtp:96 level-asymmetry-allowed=1\r\n"
        )

        result = _modify_sdp_bitrate(sdp, 2_000_000)

        assert "x-google-max-bitrate=2000" in result
        assert "x-google-min-bitrate=1000" in result
        assert "x-google-start-bitrate=2000" in result

    def test_modify_sdp_bitrate_preserves_audio_section(self):
        """Test that audio section is not modified."""
        from imagestag.components.stream_view.webrtc import _modify_sdp_bitrate

        sdp = (
            "v=0\r\n"
            "m=audio 9 UDP/TLS/RTP/SAVPF 111\r\n"
            "c=IN IP4 0.0.0.0\r\n"
            "a=fmtp:111 minptime=10\r\n"
            "m=video 9 UDP/TLS/RTP/SAVPF 96\r\n"
            "c=IN IP4 0.0.0.0\r\n"
            "a=fmtp:96 level-asymmetry-allowed=1\r\n"
        )

        result = _modify_sdp_bitrate(sdp, 3_000_000)

        # Audio fmtp should NOT have google constraints
        lines = result.split("\r\n")
        audio_fmtp = [l for l in lines if "a=fmtp:111" in l][0]
        assert "x-google" not in audio_fmtp


class TestCheckAiortcAvailable:
    """Tests for aiortc availability check."""

    def test_check_raises_when_not_available(self):
        """Test that check_aiortc_available raises ImportError when not available."""
        from imagestag.components.stream_view import webrtc

        # Save original
        original = webrtc.AIORTC_AVAILABLE

        try:
            webrtc.AIORTC_AVAILABLE = False
            with pytest.raises(ImportError) as exc_info:
                webrtc.check_aiortc_available()
            assert "aiortc is required" in str(exc_info.value)
        finally:
            webrtc.AIORTC_AVAILABLE = original

    def test_check_passes_when_available(self):
        """Test that check_aiortc_available passes when aiortc is available."""
        from imagestag.components.stream_view import webrtc

        original = webrtc.AIORTC_AVAILABLE

        try:
            webrtc.AIORTC_AVAILABLE = True
            # Should not raise
            webrtc.check_aiortc_available()
        finally:
            webrtc.AIORTC_AVAILABLE = original


class TestWebRTCLayerConfig:
    """Tests for WebRTCLayerConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        from imagestag.components.stream_view.webrtc import WebRTCLayerConfig

        mock_stream = MagicMock()
        config = WebRTCLayerConfig(stream=mock_stream)

        assert config.z_index == 0
        assert config.codec == "h264"
        assert config.bitrate == 5_000_000
        assert config.target_fps is None
        assert config.width is None
        assert config.height is None
        assert config.name == ""
        assert config.viewport_x == 0.0
        assert config.viewport_y == 0.0
        assert config.viewport_width == 1.0
        assert config.viewport_height == 1.0
        assert config.viewport_zoom == 1.0

    def test_get_effective_fps_uses_target_fps(self):
        """Test that explicit target_fps is used when set."""
        from imagestag.components.stream_view.webrtc import WebRTCLayerConfig

        mock_stream = MagicMock()
        mock_stream.fps = 60
        config = WebRTCLayerConfig(stream=mock_stream, target_fps=24)

        assert config.get_effective_fps() == 24

    def test_get_effective_fps_uses_source_fps(self):
        """Test that source fps is used when target_fps not set."""
        from imagestag.components.stream_view.webrtc import WebRTCLayerConfig

        mock_stream = MagicMock()
        mock_stream.fps = 30
        mock_stream.max_fps = None
        config = WebRTCLayerConfig(stream=mock_stream)

        assert config.get_effective_fps() == 30

    def test_get_effective_fps_respects_max_fps(self):
        """Test that max_fps caps the effective fps."""
        from imagestag.components.stream_view.webrtc import WebRTCLayerConfig

        mock_stream = MagicMock()
        mock_stream.fps = 120
        mock_stream.max_fps = 30
        config = WebRTCLayerConfig(stream=mock_stream)

        assert config.get_effective_fps() == 30

    def test_get_effective_fps_fallback(self):
        """Test fallback to 30 fps when source has no fps."""
        from imagestag.components.stream_view.webrtc import WebRTCLayerConfig

        mock_stream = MagicMock(spec=[])  # No fps attribute
        config = WebRTCLayerConfig(stream=mock_stream)

        assert config.get_effective_fps() == 30

    def test_set_viewport(self):
        """Test setting viewport from object."""
        from imagestag.components.stream_view.webrtc import WebRTCLayerConfig

        mock_stream = MagicMock()
        config = WebRTCLayerConfig(stream=mock_stream)

        viewport = MagicMock()
        viewport.x = 0.25
        viewport.y = 0.25
        viewport.width = 0.5
        viewport.height = 0.5
        viewport.zoom = 2.0

        config.set_viewport(viewport)

        assert config.viewport_x == 0.25
        assert config.viewport_y == 0.25
        assert config.viewport_width == 0.5
        assert config.viewport_height == 0.5
        assert config.viewport_zoom == 2.0

    def test_get_crop_rect(self):
        """Test getting crop rectangle from viewport."""
        from imagestag.components.stream_view.webrtc import WebRTCLayerConfig

        mock_stream = MagicMock()
        config = WebRTCLayerConfig(stream=mock_stream)
        config.viewport_x = 0.25
        config.viewport_y = 0.25
        config.viewport_width = 0.5
        config.viewport_height = 0.5

        x1, y1, x2, y2 = config.get_crop_rect(1920, 1080)

        assert x1 == 480  # 0.25 * 1920
        assert y1 == 270  # 0.25 * 1080
        assert x2 == 1440  # (0.25 + 0.5) * 1920
        assert y2 == 810  # (0.25 + 0.5) * 1080

    def test_get_crop_rect_clamps_bounds(self):
        """Test that crop rect is clamped to valid bounds."""
        from imagestag.components.stream_view.webrtc import WebRTCLayerConfig

        mock_stream = MagicMock()
        config = WebRTCLayerConfig(stream=mock_stream)
        # Set invalid viewport (extends beyond image)
        config.viewport_x = 0.9
        config.viewport_y = 0.9
        config.viewport_width = 0.5
        config.viewport_height = 0.5

        x1, y1, x2, y2 = config.get_crop_rect(100, 100)

        # Should be clamped
        assert x2 <= 100
        assert y2 <= 100
        assert x1 >= 0
        assert y1 >= 0
        assert x2 > x1
        assert y2 > y1


class TestSetCodecBitrate:
    """Tests for _set_codec_bitrate function."""

    def test_set_codec_bitrate_when_available(self):
        """Test setting codec bitrate when aiortc is available."""
        from imagestag.components.stream_view import webrtc

        if not webrtc.AIORTC_AVAILABLE:
            pytest.skip("aiortc not available")

        # Save originals
        orig_h264_default = webrtc.h264_codec.DEFAULT_BITRATE
        orig_vpx_default = webrtc.vpx_codec.DEFAULT_BITRATE

        try:
            webrtc._set_codec_bitrate(4_000_000)

            assert webrtc.h264_codec.DEFAULT_BITRATE == 4_000_000
            assert webrtc.h264_codec.MIN_BITRATE == 2_000_000
            assert webrtc.h264_codec.MAX_BITRATE == 8_000_000

            assert webrtc.vpx_codec.DEFAULT_BITRATE == 4_000_000
            assert webrtc.vpx_codec.MIN_BITRATE == 2_000_000
            assert webrtc.vpx_codec.MAX_BITRATE == 8_000_000
        finally:
            webrtc.h264_codec.DEFAULT_BITRATE = orig_h264_default
            webrtc.vpx_codec.DEFAULT_BITRATE = orig_vpx_default

    def test_set_codec_bitrate_when_not_available(self):
        """Test that _set_codec_bitrate is a no-op when aiortc not available."""
        from imagestag.components.stream_view import webrtc

        original = webrtc.AIORTC_AVAILABLE

        try:
            webrtc.AIORTC_AVAILABLE = False
            # Should not raise
            webrtc._set_codec_bitrate(5_000_000)
        finally:
            webrtc.AIORTC_AVAILABLE = original


@pytest.mark.skipif(
    not pytest.importorskip("aiortc", reason="aiortc not installed"),
    reason="aiortc not installed"
)
class TestStreamViewVideoTrack:
    """Tests for StreamViewVideoTrack (requires aiortc)."""

    @pytest.fixture
    def mock_stream(self):
        """Create a mock video stream."""
        stream = MagicMock()
        stream.is_running = True
        stream.is_paused = False
        stream.fps = 30

        # Create a test image
        test_img = Image.from_array(np.zeros((480, 640, 3), dtype=np.uint8))
        stream.get_frame.return_value = (test_img, 1)
        stream.last_frame = test_img
        return stream

    @pytest.fixture
    def config(self, mock_stream):
        """Create a WebRTCLayerConfig."""
        from imagestag.components.stream_view.webrtc import WebRTCLayerConfig
        return WebRTCLayerConfig(stream=mock_stream, target_fps=30)

    def test_track_kind(self, mock_stream, config):
        """Test that track kind is 'video'."""
        from imagestag.components.stream_view.webrtc import StreamViewVideoTrack

        track = StreamViewVideoTrack(mock_stream, config)
        assert track.kind == "video"

    def test_target_fps_property(self, mock_stream, config):
        """Test target_fps property."""
        from imagestag.components.stream_view.webrtc import StreamViewVideoTrack

        track = StreamViewVideoTrack(mock_stream, config)
        assert track.target_fps == 30

    @pytest.mark.asyncio
    async def test_recv_returns_video_frame(self, mock_stream, config):
        """Test that recv() returns a VideoFrame."""
        from imagestag.components.stream_view.webrtc import StreamViewVideoTrack
        from av import VideoFrame

        track = StreamViewVideoTrack(mock_stream, config, width=640, height=480)
        track._start_time = asyncio.get_event_loop().time()

        frame = await track.recv()

        assert isinstance(frame, VideoFrame)
        assert frame.pts is not None

    @pytest.mark.asyncio
    async def test_recv_returns_black_frame_when_no_content(self, config):
        """Test that recv() returns black frame when stream has no content."""
        from imagestag.components.stream_view.webrtc import StreamViewVideoTrack
        from av import VideoFrame

        mock_stream = MagicMock()
        mock_stream.is_running = True
        mock_stream.is_paused = False
        mock_stream.get_frame.return_value = (None, 0)
        mock_stream.last_frame = None

        track = StreamViewVideoTrack(mock_stream, config, width=320, height=240)
        track._start_time = asyncio.get_event_loop().time()

        frame = await track.recv()

        assert isinstance(frame, VideoFrame)
        assert frame.width == 320
        assert frame.height == 240


@pytest.mark.skipif(
    not pytest.importorskip("aiortc", reason="aiortc not installed"),
    reason="aiortc not installed"
)
class TestWebRTCManager:
    """Tests for WebRTCManager (requires aiortc)."""

    def test_manager_initialization(self):
        """Test that manager initializes event loop and thread."""
        from imagestag.components.stream_view.webrtc import WebRTCManager

        manager = WebRTCManager()

        try:
            assert manager._loop is not None
            assert manager._thread is not None
            assert manager._thread.is_alive()
            assert manager.connection_count == 0
        finally:
            manager.shutdown()

    def test_manager_shutdown(self):
        """Test that manager shuts down cleanly."""
        from imagestag.components.stream_view.webrtc import WebRTCManager

        manager = WebRTCManager()
        manager.shutdown()

        # Thread should stop
        import time
        time.sleep(0.5)
        assert not manager._thread.is_alive() or manager._thread is None

    def test_get_connection_returns_none_for_unknown(self):
        """Test that get_connection returns None for unknown layer."""
        from imagestag.components.stream_view.webrtc import WebRTCManager

        manager = WebRTCManager()

        try:
            assert manager.get_connection("unknown_layer") is None
        finally:
            manager.shutdown()

    def test_close_connection_handles_unknown(self):
        """Test that close_connection handles unknown layer gracefully."""
        from imagestag.components.stream_view.webrtc import WebRTCManager

        manager = WebRTCManager()

        try:
            # Should not raise
            manager.close_connection("unknown_layer")
        finally:
            manager.shutdown()


class TestWebRTCIntegration:
    """Integration tests for WebRTC with real streams."""

    @pytest.mark.skipif(
        not pytest.importorskip("aiortc", reason="aiortc not installed"),
        reason="aiortc not installed"
    )
    def test_create_webrtc_layer_with_generator_stream(self):
        """Test creating WebRTC layer with GeneratorStream."""
        from imagestag.components.stream_view.webrtc import (
            WebRTCManager,
            WebRTCLayerConfig,
        )

        def create_frame(t):
            # Simple colored frame
            arr = np.zeros((240, 320, 3), dtype=np.uint8)
            arr[:, :, 0] = int(127 + 127 * np.sin(t))  # Red varies with time
            return Image.from_array(arr)

        stream = GeneratorStream(handler=create_frame)
        stream.start()

        try:
            config = WebRTCLayerConfig(
                stream=stream,
                z_index=0,
                bitrate=1_000_000,
                target_fps=15,
                width=320,
                height=240,
            )

            manager = WebRTCManager()

            try:
                offer_received = []

                def on_offer(layer_id, offer):
                    offer_received.append((layer_id, offer))

                manager.create_connection("test_layer", config, on_offer)

                # Wait for offer
                import time
                for _ in range(50):  # 5 seconds max
                    if offer_received:
                        break
                    time.sleep(0.1)

                # Verify offer was generated
                assert len(offer_received) == 1
                layer_id, offer = offer_received[0]
                assert layer_id == "test_layer"
                assert "sdp" in offer
                assert "type" in offer
                assert offer["type"] == "offer"

            finally:
                manager.shutdown()
        finally:
            stream.stop()


class TestWebRTCReceiver:
    """Tests for WebRTC receiver functionality.

    These tests verify that we can receive WebRTC streams by creating
    a loopback connection (sender + receiver in same process).
    """

    @pytest.mark.skipif(
        not pytest.importorskip("aiortc", reason="aiortc not installed"),
        reason="aiortc not installed"
    )
    @pytest.mark.asyncio
    async def test_webrtc_loopback(self):
        """Test WebRTC loopback: sender -> receiver in same process."""
        from aiortc import RTCPeerConnection, RTCSessionDescription
        from aiortc.contrib.media import MediaBlackhole
        from imagestag.components.stream_view.webrtc import (
            WebRTCLayerConfig,
            StreamViewVideoTrack,
        )

        # Create a simple generator stream
        def create_frame(t):
            arr = np.full((240, 320, 3), 128, dtype=np.uint8)
            return Image.from_array(arr)

        stream = GeneratorStream(handler=create_frame)
        stream.start()

        try:
            config = WebRTCLayerConfig(
                stream=stream,
                target_fps=10,
                width=320,
                height=240,
            )

            # Create sender peer connection
            sender_pc = RTCPeerConnection()
            track = StreamViewVideoTrack(stream, config, width=320, height=240)
            sender_pc.addTrack(track)

            # Create receiver peer connection
            receiver_pc = RTCPeerConnection()
            received_frames = []

            @receiver_pc.on("track")
            def on_track(recv_track):
                async def receive_frames():
                    try:
                        for _ in range(3):  # Receive 3 frames
                            frame = await asyncio.wait_for(recv_track.recv(), timeout=5.0)
                            received_frames.append(frame)
                    except Exception:
                        pass

                asyncio.create_task(receive_frames())

            # Create offer from sender
            offer = await sender_pc.createOffer()
            await sender_pc.setLocalDescription(offer)

            # Set offer on receiver
            await receiver_pc.setRemoteDescription(
                RTCSessionDescription(sdp=sender_pc.localDescription.sdp, type="offer")
            )

            # Create answer from receiver
            answer = await receiver_pc.createAnswer()
            await receiver_pc.setLocalDescription(answer)

            # Set answer on sender
            await sender_pc.setRemoteDescription(
                RTCSessionDescription(sdp=receiver_pc.localDescription.sdp, type="answer")
            )

            # Wait for frames
            await asyncio.sleep(2.0)

            # Cleanup
            await sender_pc.close()
            await receiver_pc.close()

            # Verify frames were received
            assert len(received_frames) > 0, "Should have received at least one frame"

        finally:
            stream.stop()


@pytest.mark.skipif(
    not pytest.importorskip("aiortc", reason="aiortc not installed"),
    reason="aiortc not installed"
)
class TestStreamViewVideoTrackAdvanced:
    """Advanced tests for StreamViewVideoTrack edge cases."""

    @pytest.fixture
    def mock_config(self):
        """Create mock config."""
        config = MagicMock()
        config.viewport_zoom = 1.0
        config.get_effective_fps.return_value = 30
        return config

    @pytest.mark.asyncio
    async def test_recv_with_viewport_zoom(self, mock_config):
        """Test recv() applies viewport cropping when zoom > 1."""
        from imagestag.components.stream_view.webrtc import StreamViewVideoTrack
        from av import VideoFrame

        # Create stream with frame
        frame = Image.from_array(np.full((480, 640, 3), 128, dtype=np.uint8))
        mock_stream = MagicMock()
        mock_stream.is_running = True
        mock_stream.is_paused = False
        mock_stream.get_frame.return_value = (frame, 0)
        mock_stream.last_frame = frame

        # Set viewport zoom > 1
        mock_config.viewport_zoom = 2.0
        mock_config.get_crop_rect.return_value = (160, 120, 480, 360)

        track = StreamViewVideoTrack(mock_stream, mock_config, width=320, height=240)
        track._start_time = asyncio.get_event_loop().time()

        result = await track.recv()

        assert isinstance(result, VideoFrame)
        mock_config.get_crop_rect.assert_called_once()

    @pytest.mark.asyncio
    async def test_recv_with_grayscale_frame(self, mock_config):
        """Test recv() handles grayscale frames."""
        from imagestag.components.stream_view.webrtc import StreamViewVideoTrack
        from av import VideoFrame

        # Create grayscale frame (2D array)
        gray_arr = np.full((240, 320), 128, dtype=np.uint8)
        frame = MagicMock()
        frame.width = 320
        frame.height = 240
        frame.get_pixels.return_value = gray_arr

        mock_stream = MagicMock()
        mock_stream.is_running = True
        mock_stream.is_paused = False
        mock_stream.get_frame.return_value = (frame, 0)
        mock_stream.last_frame = frame

        track = StreamViewVideoTrack(mock_stream, mock_config, width=320, height=240)
        track._start_time = asyncio.get_event_loop().time()

        result = await track.recv()

        assert isinstance(result, VideoFrame)

    @pytest.mark.asyncio
    async def test_recv_with_rgba_frame(self, mock_config):
        """Test recv() handles RGBA frames (4 channels)."""
        from imagestag.components.stream_view.webrtc import StreamViewVideoTrack
        from av import VideoFrame

        # Create RGBA frame (4 channels)
        rgba_arr = np.full((240, 320, 4), 128, dtype=np.uint8)
        frame = MagicMock()
        frame.width = 320
        frame.height = 240
        frame.get_pixels.return_value = rgba_arr

        mock_stream = MagicMock()
        mock_stream.is_running = True
        mock_stream.is_paused = False
        mock_stream.get_frame.return_value = (frame, 0)
        mock_stream.last_frame = frame

        track = StreamViewVideoTrack(mock_stream, mock_config, width=320, height=240)
        track._start_time = asyncio.get_event_loop().time()

        result = await track.recv()

        assert isinstance(result, VideoFrame)

    @pytest.mark.asyncio
    async def test_recv_catches_exception_returns_black(self, mock_config):
        """Test recv() returns black frame when exception occurs."""
        from imagestag.components.stream_view.webrtc import StreamViewVideoTrack
        from av import VideoFrame

        mock_stream = MagicMock()
        mock_stream.is_running = True
        mock_stream.is_paused = False
        mock_stream.get_frame.side_effect = RuntimeError("Stream error")
        mock_stream.last_frame = None

        track = StreamViewVideoTrack(mock_stream, mock_config, width=320, height=240)
        track._start_time = asyncio.get_event_loop().time()

        result = await track.recv()

        # Should return black frame on error
        assert isinstance(result, VideoFrame)
        assert result.width == 320
        assert result.height == 240

    @pytest.mark.asyncio
    async def test_recv_with_crop_error_fallback(self, mock_config):
        """Test recv() handles crop errors gracefully."""
        from imagestag.components.stream_view.webrtc import StreamViewVideoTrack
        from av import VideoFrame

        frame = Image.from_array(np.full((240, 320, 3), 128, dtype=np.uint8))
        mock_stream = MagicMock()
        mock_stream.is_running = True
        mock_stream.is_paused = False
        mock_stream.get_frame.return_value = (frame, 0)
        mock_stream.last_frame = frame

        # Set viewport zoom > 1 but make crop fail
        mock_config.viewport_zoom = 2.0
        mock_config.get_crop_rect.side_effect = RuntimeError("Crop error")

        track = StreamViewVideoTrack(mock_stream, mock_config, width=320, height=240)
        track._start_time = asyncio.get_event_loop().time()

        # Should still return a frame (error is caught)
        result = await track.recv()
        assert isinstance(result, VideoFrame)


class TestWebRTCManagerAnswerHandling:
    """Tests for WebRTC answer handling edge cases."""

    @pytest.mark.skipif(
        not pytest.importorskip("aiortc", reason="aiortc not installed"),
        reason="aiortc not installed"
    )
    def test_handle_answer_unknown_layer(self):
        """Test handle_answer logs warning for unknown layer."""
        from imagestag.components.stream_view.webrtc import WebRTCManager

        manager = WebRTCManager()

        try:
            # Should not raise, just log warning
            manager.handle_answer("unknown_layer", {"sdp": "v=0", "type": "answer"})
        finally:
            manager.shutdown()
