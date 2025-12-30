"""WebRTC support for StreamView.

Provides efficient video streaming using WebRTC with H.264/VP8 encoding,
reducing bandwidth from ~40-50 Mbit (base64 JPEG) to ~2-5 Mbit.

Usage:
    view = StreamView(width=1920, height=1080)
    view.add_webrtc_layer(stream=video_stream, bitrate=5_000_000)

Requirements:
    pip install aiortc
    # System packages: libavdevice-dev libavfilter-dev libopus-dev libvpx-dev
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from dataclasses import dataclass, field
from fractions import Fraction
from typing import TYPE_CHECKING, Callable

import numpy as np

try:
    from aiortc import RTCPeerConnection, RTCSessionDescription
    from aiortc.mediastreams import VideoStreamTrack
    from aiortc.codecs import h264 as h264_codec, vpx as vpx_codec
    from av import VideoFrame

    AIORTC_AVAILABLE = True
except ImportError:
    AIORTC_AVAILABLE = False
    RTCPeerConnection = None
    RTCSessionDescription = None
    VideoStreamTrack = object  # Placeholder for type hints
    VideoFrame = None
    h264_codec = None
    vpx_codec = None

if TYPE_CHECKING:
    from .layers import VideoStream

logger = logging.getLogger(__name__)


def _modify_sdp_bitrate(sdp: str, bitrate_bps: int) -> str:
    """Modify SDP to set video bitrate constraint.

    Adds b=AS (Application Specific) bandwidth line to video m-line.
    Also adds x-google-max-bitrate for Chrome compatibility.

    :param sdp: Original SDP string
    :param bitrate_bps: Target bitrate in bits per second
    :return: Modified SDP string
    """
    bitrate_kbps = bitrate_bps // 1000
    lines = sdp.split("\r\n")
    result = []
    in_video_section = False

    for i, line in enumerate(lines):
        result.append(line)

        # Detect video m-line
        if line.startswith("m=video"):
            in_video_section = True
        elif line.startswith("m="):
            in_video_section = False

        # Add bandwidth after c= line in video section
        if in_video_section and line.startswith("c="):
            # Add AS (Application Specific) bandwidth in kbps
            result.append(f"b=AS:{bitrate_kbps}")
            # Add TIAS (Transport Independent Application Specific) in bps
            result.append(f"b=TIAS:{bitrate_bps}")

        # Modify fmtp lines to add bitrate constraints for codecs
        if in_video_section and line.startswith("a=fmtp:"):
            # Add x-google-max-bitrate for Chrome
            if "x-google-max-bitrate" not in line:
                # Append to existing fmtp line
                result[-1] = f"{line};x-google-max-bitrate={bitrate_kbps};x-google-min-bitrate={bitrate_kbps // 2};x-google-start-bitrate={bitrate_kbps}"

    return "\r\n".join(result)


def check_aiortc_available() -> None:
    """Raise ImportError if aiortc is not installed."""
    if not AIORTC_AVAILABLE:
        raise ImportError(
            "aiortc is required for WebRTC support. "
            "Install with: pip install aiortc\n"
            "System packages needed: libavdevice-dev libavfilter-dev libopus-dev libvpx-dev"
        )


def _set_codec_bitrate(bitrate_bps: int) -> None:
    """Set aiortc codec bitrate constants.

    aiortc ignores SDP bandwidth constraints and uses module-level constants
    for encoder bitrate. This function sets those constants to achieve the
    desired bitrate.

    :param bitrate_bps: Target bitrate in bits per second
    """
    if not AIORTC_AVAILABLE:
        return

    # Set H.264 codec bitrate
    h264_codec.DEFAULT_BITRATE = bitrate_bps
    h264_codec.MIN_BITRATE = bitrate_bps // 2
    h264_codec.MAX_BITRATE = bitrate_bps * 2

    # Set VP8/VP9 codec bitrate
    vpx_codec.DEFAULT_BITRATE = bitrate_bps
    vpx_codec.MIN_BITRATE = bitrate_bps // 2
    vpx_codec.MAX_BITRATE = bitrate_bps * 2

    logger.info(f"Codec bitrate set: {bitrate_bps // 1000} kbps (range: {bitrate_bps // 2000}-{bitrate_bps * 2 // 1000} kbps)")


class StreamViewVideoTrack(VideoStreamTrack):
    """WebRTC video track that wraps a VideoStream.

    Provides frames from a VideoStream to WebRTC for efficient
    H.264/VP8 encoded streaming. Cropping is handled by the layer config,
    not by this track directly.
    """

    kind = "video"

    def __init__(
        self,
        video_stream: "VideoStream",
        config: "WebRTCLayerConfig",
        width: int | None = None,
        height: int | None = None,
    ) -> None:
        """Initialize the video track.

        :param video_stream: Source VideoStream to get frames from
        :param config: Layer configuration (holds viewport for cropping, FPS)
        :param width: Target width (None = use source resolution)
        :param height: Target height (None = use source resolution)
        """
        super().__init__()
        self.video_stream = video_stream
        self.config = config  # Layer config holds viewport and FPS
        self.target_width = width
        self.target_height = height
        self._frame_count = 0
        self._start_time: float | None = None

    @property
    def target_fps(self) -> int:
        """Get target FPS dynamically from config/stream."""
        return self.config.get_effective_fps()

    async def recv(self) -> "VideoFrame":
        """Get the next video frame for WebRTC.

        :return: av.VideoFrame for encoding
        """
        try:
            # Calculate timestamp
            pts, time_base = await self.next_timestamp()

            # Auto-start stream only if never started (not if paused)
            # This respects user's pause/resume control
            if not self.video_stream.is_running and not self.video_stream.is_paused:
                logger.info("WebRTC: Starting video stream (first time)")
                self.video_stream.start()

            # Get frame from VideoStream by calling get_frame() directly
            # This ensures the stream produces frames even without a WebSocket layer
            timestamp = time.perf_counter()
            frame, _ = self.video_stream.get_frame(timestamp)

            # If get_frame returns None (e.g., same frame), try last_frame
            if frame is None:
                frame = self.video_stream.last_frame

            # Debug logging (every 300 frames, ~10 seconds at 30fps)
            if self._frame_count % 300 == 0 and self._frame_count > 0:
                logger.debug(f"WebRTC frame {self._frame_count}: stream_running={self.video_stream.is_running}")

            if frame is None:
                # Return black frame if no content yet
                width = self.target_width or 1920
                height = self.target_height or 1080
                black = np.zeros((height, width, 3), dtype=np.uint8)
                video_frame = VideoFrame.from_ndarray(black, format="bgr24")
            else:
                # Apply viewport cropping from the layer config
                # The config (layer) is responsible for cropping, not this track
                if self.config.viewport_zoom > 1.0:
                    try:
                        x1, y1, x2, y2 = self.config.get_crop_rect(frame.width, frame.height)
                        frame = frame.cropped((x1, y1, x2, y2))
                    except Exception as e:
                        logger.debug(f"WebRTC crop failed: {e}")

                # Convert Image to numpy array (RGB format)
                arr = frame.get_pixels("RGB")

                # Resize to target dimensions
                if self.target_width and self.target_height:
                    if arr.shape[1] != self.target_width or arr.shape[0] != self.target_height:
                        # Use cv2 for efficient resizing if available
                        try:
                            import cv2

                            arr = cv2.resize(
                                arr,
                                (self.target_width, self.target_height),
                                interpolation=cv2.INTER_LINEAR,
                            )
                        except ImportError:
                            # Fallback to PIL
                            from PIL import Image as PILImage

                            pil_img = PILImage.fromarray(arr)
                            pil_img = pil_img.resize(
                                (self.target_width, self.target_height),
                                PILImage.Resampling.BILINEAR,
                            )
                            arr = np.array(pil_img)

                # Ensure RGB format for av (VideoStream returns RGB)
                if len(arr.shape) == 2:
                    # Grayscale to RGB
                    arr = np.stack([arr, arr, arr], axis=-1)
                elif arr.shape[2] == 4:
                    # RGBA to RGB
                    arr = arr[:, :, :3]

                video_frame = VideoFrame.from_ndarray(arr, format="rgb24")

            video_frame.pts = pts
            video_frame.time_base = time_base
            self._frame_count += 1

            return video_frame

        except Exception as e:
            logger.error(f"WebRTC Track error in recv(): {e}")
            # Return black frame on error
            width = self.target_width or 1920
            height = self.target_height or 1080
            black = np.zeros((height, width, 3), dtype=np.uint8)
            video_frame = VideoFrame.from_ndarray(black, format="bgr24")
            video_frame.pts = 0
            video_frame.time_base = Fraction(1, 90000)
            return video_frame

    async def next_timestamp(self) -> tuple[int, Fraction]:
        """Calculate the next frame timestamp.

        :return: Tuple of (pts, time_base)
        """
        if self._start_time is None:
            self._start_time = asyncio.get_event_loop().time()

        # Calculate timing
        time_base = Fraction(1, 90000)  # Standard video time base
        elapsed = asyncio.get_event_loop().time() - self._start_time
        pts = int(elapsed * 90000)

        # Throttle to target FPS
        frame_duration = 1.0 / self.target_fps
        target_time = self._frame_count * frame_duration
        if elapsed < target_time:
            await asyncio.sleep(target_time - elapsed)

        return pts, time_base


@dataclass
class WebRTCLayerConfig:
    """Configuration for a WebRTC layer.

    This is the "layer" for WebRTC - it handles viewport/cropping configuration.
    The track reads viewport values from here to apply server-side cropping.
    """

    stream: "VideoStream"
    z_index: int = 0
    codec: str = "h264"  # h264, vp8, vp9
    bitrate: int = 5_000_000  # 5 Mbps default
    target_fps: int | None = None  # None = use source fps
    width: int | None = None  # None = use source
    height: int | None = None
    name: str = ""

    def get_effective_fps(self) -> int:
        """Get the effective output FPS for WebRTC encoding.

        For WebRTC, we maintain a constant output frame rate regardless of
        playback speed. The video stream handles slow-mo/fast-forward internally
        by advancing through video content at the appropriate rate. WebRTC just
        needs to encode frames at a steady rate for smooth streaming.

        Scaling FPS by speed causes timing issues when speed changes mid-stream.
        """
        if self.target_fps is not None:
            return self.target_fps
        # Use source FPS as output rate (don't scale by playback speed)
        if hasattr(self.stream, 'fps'):
            base_fps = self.stream.fps
            if base_fps > 0:
                # Cap by stream's max_fps if set
                max_fps = getattr(self.stream, 'max_fps', None)
                if max_fps is not None:
                    return min(int(base_fps), int(max_fps))
                return max(1, int(base_fps))
        return 30  # Fallback default
    # Viewport state for server-side cropping (updated by StreamView._handle_viewport_change)
    viewport_x: float = 0.0
    viewport_y: float = 0.0
    viewport_width: float = 1.0
    viewport_height: float = 1.0
    viewport_zoom: float = 1.0

    def set_viewport(self, viewport) -> None:
        """Update viewport from StreamView viewport object.

        :param viewport: Viewport object with x, y, width, height, zoom
        """
        self.viewport_x = viewport.x
        self.viewport_y = viewport.y
        self.viewport_width = viewport.width
        self.viewport_height = viewport.height
        self.viewport_zoom = viewport.zoom

    def get_crop_rect(self, source_width: int, source_height: int) -> tuple[int, int, int, int]:
        """Get crop rectangle for current viewport in source image pixels.

        :param source_width: Width of source image in pixels
        :param source_height: Height of source image in pixels
        :return: Tuple of (x1, y1, x2, y2) crop coordinates
        """
        x1 = int(self.viewport_x * source_width)
        y1 = int(self.viewport_y * source_height)
        x2 = int((self.viewport_x + self.viewport_width) * source_width)
        y2 = int((self.viewport_y + self.viewport_height) * source_height)
        # Clamp to valid bounds
        x1 = max(0, min(x1, source_width - 1))
        y1 = max(0, min(y1, source_height - 1))
        x2 = max(x1 + 1, min(x2, source_width))
        y2 = max(y1 + 1, min(y2, source_height))
        return (x1, y1, x2, y2)


@dataclass
class WebRTCConnection:
    """State for a single WebRTC peer connection."""

    pc: "RTCPeerConnection"
    track: StreamViewVideoTrack
    config: WebRTCLayerConfig
    layer_id: str


class WebRTCManager:
    """Manages WebRTC peer connections for StreamView.

    Runs aiortc in a dedicated thread with its own event loop,
    providing a synchronous API for the rest of the application.
    """

    def __init__(self) -> None:
        """Initialize the WebRTC manager."""
        check_aiortc_available()
        self._connections: dict[str, WebRTCConnection] = {}
        self._lock = threading.Lock()

        # Create dedicated event loop and thread for WebRTC
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._started = threading.Event()
        self._start_thread()

    def _start_thread(self) -> None:
        """Start the WebRTC event loop thread."""
        def run_loop():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._started.set()
            self._loop.run_forever()

        self._thread = threading.Thread(target=run_loop, daemon=True, name="WebRTC-EventLoop")
        self._thread.start()
        self._started.wait(timeout=5.0)

    def _run_async(self, coro):
        """Run an async coroutine in the WebRTC thread and wait for result."""
        if self._loop is None:
            raise RuntimeError("WebRTC event loop not started")
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout=30.0)

    def create_connection(
        self,
        layer_id: str,
        config: WebRTCLayerConfig,
        on_offer: Callable[[str, dict], None] | None = None,
    ) -> None:
        """Create a new WebRTC peer connection.

        :param layer_id: Unique identifier for the layer
        :param config: Layer configuration
        :param on_offer: Callback called with (layer_id, offer_dict) when offer is ready
        """
        def do_create():
            # Set codec bitrate BEFORE creating encoder
            # aiortc uses module-level constants, ignoring SDP constraints
            _set_codec_bitrate(config.bitrate)

            async def create_async():
                try:
                    logger.debug(f"Creating WebRTC connection for layer {layer_id}")

                    # Create peer connection
                    pc = RTCPeerConnection()

                    # Create video track (pass config so track can read viewport for cropping)
                    # FPS is read dynamically from config.get_effective_fps()
                    track = StreamViewVideoTrack(
                        video_stream=config.stream,
                        config=config,
                        width=config.width,
                        height=config.height,
                    )

                    # Add track to peer connection
                    pc.addTrack(track)

                    # Store connection state
                    with self._lock:
                        self._connections[layer_id] = WebRTCConnection(
                            pc=pc,
                            track=track,
                            config=config,
                            layer_id=layer_id,
                        )

                    # Handle connection state changes
                    @pc.on("connectionstatechange")
                    async def on_connectionstatechange() -> None:
                        logger.debug(f"WebRTC connection state: {pc.connectionState}")
                        if pc.connectionState == "failed":
                            logger.warning(f"WebRTC connection failed for layer {layer_id}")
                            self.close_connection(layer_id)
                        elif pc.connectionState == "connected":
                            logger.info(f"WebRTC connected for layer {layer_id}")

                    # Handle ICE connection state changes
                    @pc.on("iceconnectionstatechange")
                    async def on_iceconnectionstatechange() -> None:
                        logger.debug(f"WebRTC ICE state: {pc.iceConnectionState}")

                    # Create offer
                    try:
                        offer = await asyncio.wait_for(pc.createOffer(), timeout=5.0)
                        await pc.setLocalDescription(offer)
                    except asyncio.TimeoutError:
                        logger.error(f"WebRTC createOffer timed out for layer {layer_id}")
                        return

                    # Wait for ICE gathering to complete (candidates included in SDP)
                    while pc.iceGatheringState != "complete":
                        await asyncio.sleep(0.1)

                    # Modify SDP to apply bitrate constraint
                    modified_sdp = _modify_sdp_bitrate(
                        pc.localDescription.sdp,
                        config.bitrate
                    )
                    logger.info(f"WebRTC layer {layer_id}: bitrate set to {config.bitrate // 1000} kbps")

                    offer_dict = {
                        "sdp": modified_sdp,
                        "type": pc.localDescription.type,
                    }

                    # Call the callback with the offer
                    if on_offer:
                        on_offer(layer_id, offer_dict)

                except Exception as e:
                    logger.error(f"Error creating WebRTC connection for {layer_id}: {e}")

            asyncio.run_coroutine_threadsafe(create_async(), self._loop)

        # Run in a thread to not block
        threading.Thread(target=do_create, daemon=True).start()

    def handle_answer(self, layer_id: str, answer: dict) -> None:
        """Process the browser's SDP answer.

        :param layer_id: Layer identifier
        :param answer: SDP answer dict with 'sdp' and 'type' keys
        """
        with self._lock:
            if layer_id not in self._connections:
                logger.warning(f"WebRTC answer for unknown layer: {layer_id}")
                return
            conn = self._connections[layer_id]

        async def handle_async():
            await conn.pc.setRemoteDescription(
                RTCSessionDescription(sdp=answer["sdp"], type=answer["type"])
            )
            logger.info(f"WebRTC connection established for layer {layer_id}")

        if self._loop:
            asyncio.run_coroutine_threadsafe(handle_async(), self._loop)

    def close_connection(self, layer_id: str) -> None:
        """Close a peer connection.

        :param layer_id: Layer identifier
        """
        with self._lock:
            if layer_id not in self._connections:
                return
            conn = self._connections.pop(layer_id)

        async def close_async():
            await conn.pc.close()
            logger.debug(f"WebRTC connection closed for layer {layer_id}")

        if self._loop:
            asyncio.run_coroutine_threadsafe(close_async(), self._loop)

    def close_all(self) -> None:
        """Close all peer connections."""
        with self._lock:
            layer_ids = list(self._connections.keys())
        for layer_id in layer_ids:
            self.close_connection(layer_id)

    def shutdown(self) -> None:
        """Shutdown the WebRTC manager and its event loop."""
        self.close_all()
        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread:
            self._thread.join(timeout=2.0)

    def get_connection(self, layer_id: str) -> WebRTCConnection | None:
        """Get connection state for a layer.

        :param layer_id: Layer identifier
        :return: Connection state or None
        """
        with self._lock:
            return self._connections.get(layer_id)

    @property
    def connection_count(self) -> int:
        """Number of active connections."""
        with self._lock:
            return len(self._connections)
