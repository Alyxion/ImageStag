"""WebRTC receiver client for receiving video streams.

This component can connect to WebRTC video streams from any server,
receive video frames, and expose them for processing.
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Callable

import numpy as np

# Check for aiortc availability
try:
    from aiortc import (
        RTCConfiguration,
        RTCIceServer,
        RTCPeerConnection,
        RTCSessionDescription,
        MediaStreamTrack,
    )
    from av import VideoFrame

    AIORTC_AVAILABLE = True
except ImportError:
    AIORTC_AVAILABLE = False
    RTCPeerConnection = None
    RTCSessionDescription = None
    MediaStreamTrack = None
    VideoFrame = None

if TYPE_CHECKING:
    from imagestag import Image

logger = logging.getLogger(__name__)


class ReceiverState(Enum):
    """State of the WebRTC receiver."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECEIVING = "receiving"
    ERROR = "error"
    CLOSED = "closed"


@dataclass
class ReceivedFrame:
    """A frame received from the WebRTC stream."""

    frame: "Image"
    timestamp: float
    pts: int
    width: int
    height: int


@dataclass
class WebRTCReceiverConfig:
    """Configuration for the WebRTC receiver."""

    buffer_size: int = 10
    ice_servers: list[str] = field(default_factory=lambda: ["stun:stun.l.google.com:19302"])
    timeout: float = 30.0


class WebRTCReceiver:
    """WebRTC receiver client for receiving video streams.

    This component can:
    - Connect to WebRTC streams using SDP offer/answer exchange
    - Receive video frames from the stream
    - Convert frames to ImageStag Image objects
    - Buffer frames for processing
    - Provide callbacks for new frames

    Example usage:
        receiver = WebRTCReceiver()
        receiver.start()

        # Connect using an SDP offer from a server
        answer = receiver.create_answer(offer_sdp)

        # Wait for frames
        if receiver.wait_for_frame(timeout=5.0):
            frame = receiver.get_frame()
            print(f"Received {frame.width}x{frame.height} frame")

        receiver.close()
    """

    def __init__(self, config: WebRTCReceiverConfig | None = None):
        """Initialize the WebRTC receiver.

        :param config: Receiver configuration (optional)
        """
        if not AIORTC_AVAILABLE:
            raise ImportError(
                "aiortc is required for WebRTC support. "
                "Install with: pip install aiortc"
            )

        self.config = config or WebRTCReceiverConfig()
        self._state = ReceiverState.DISCONNECTED
        self._pc: RTCPeerConnection | None = None
        self._track: MediaStreamTrack | None = None

        # Event loop for async operations
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._started = threading.Event()
        self._stop_event = threading.Event()

        # Frame buffer
        self._frame_buffer: deque[ReceivedFrame] = deque(maxlen=self.config.buffer_size)
        self._frame_lock = threading.Lock()
        self._frame_event = threading.Event()

        # Callbacks
        self._on_frame_callbacks: list[Callable[[ReceivedFrame], None]] = []
        self._on_state_callbacks: list[Callable[[ReceiverState], None]] = []

        # Stats
        self._frames_received = 0
        self._bytes_received = 0
        self._start_time: float | None = None

    @property
    def state(self) -> ReceiverState:
        """Get the current receiver state."""
        return self._state

    @property
    def is_connected(self) -> bool:
        """Check if the receiver is connected."""
        return self._state in (ReceiverState.CONNECTED, ReceiverState.RECEIVING)

    @property
    def frames_received(self) -> int:
        """Get the number of frames received."""
        return self._frames_received

    @property
    def buffer_size(self) -> int:
        """Get the current buffer size."""
        with self._frame_lock:
            return len(self._frame_buffer)

    def start(self) -> None:
        """Start the receiver's event loop thread."""
        if self._thread is not None and self._thread.is_alive():
            return

        def run_loop():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._started.set()
            self._loop.run_forever()

        self._thread = threading.Thread(
            target=run_loop, daemon=True, name="WebRTC-Receiver"
        )
        self._thread.start()
        self._started.wait(timeout=5.0)

    def _run_async(self, coro) -> any:
        """Run an async coroutine in the receiver thread and wait for result."""
        if self._loop is None:
            raise RuntimeError("Receiver event loop not started. Call start() first.")
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout=self.config.timeout)

    def _set_state(self, state: ReceiverState) -> None:
        """Set the receiver state and notify callbacks."""
        self._state = state
        for callback in self._on_state_callbacks:
            try:
                callback(state)
            except Exception as e:
                logger.debug(f"State callback error: {e}")

    async def _create_answer_async(self, offer: dict) -> dict:
        """Create an SDP answer from an offer (async)."""
        self._set_state(ReceiverState.CONNECTING)

        # Create ICE configuration
        ice_servers = [RTCIceServer(urls=url) for url in self.config.ice_servers]
        config = RTCConfiguration(iceServers=ice_servers)

        self._pc = RTCPeerConnection(configuration=config)

        @self._pc.on("track")
        async def on_track(track: MediaStreamTrack):
            if track.kind == "video":
                self._track = track
                self._set_state(ReceiverState.CONNECTED)
                # Start receiving frames
                asyncio.ensure_future(self._receive_frames())

        @self._pc.on("connectionstatechange")
        async def on_connection_state_change():
            state = self._pc.connectionState
            if state == "connected":
                self._set_state(ReceiverState.CONNECTED)
            elif state == "failed":
                self._set_state(ReceiverState.ERROR)
            elif state == "closed":
                self._set_state(ReceiverState.CLOSED)

        # Set remote description (the offer)
        await self._pc.setRemoteDescription(
            RTCSessionDescription(sdp=offer["sdp"], type=offer["type"])
        )

        # Create answer
        answer = await self._pc.createAnswer()
        await self._pc.setLocalDescription(answer)

        # Wait for ICE gathering to complete
        while self._pc.iceGatheringState != "complete":
            await asyncio.sleep(0.1)

        return {
            "sdp": self._pc.localDescription.sdp,
            "type": self._pc.localDescription.type,
        }

    def create_answer(self, offer: dict) -> dict:
        """Create an SDP answer from an offer.

        :param offer: SDP offer dict with 'sdp' and 'type' keys
        :return: SDP answer dict with 'sdp' and 'type' keys
        """
        return self._run_async(self._create_answer_async(offer))

    async def _receive_frames(self) -> None:
        """Receive frames from the video track."""
        from imagestag import Image

        self._start_time = time.perf_counter()
        self._set_state(ReceiverState.RECEIVING)

        try:
            while not self._stop_event.is_set() and self._track:
                try:
                    frame = await asyncio.wait_for(self._track.recv(), timeout=2.0)

                    # Convert av.VideoFrame to numpy array
                    img_array = frame.to_ndarray(format="rgb24")

                    # Create ImageStag Image
                    image = Image.from_array(img_array)

                    # Create received frame object
                    received = ReceivedFrame(
                        frame=image,
                        timestamp=time.perf_counter(),
                        pts=frame.pts or 0,
                        width=frame.width,
                        height=frame.height,
                    )

                    # Add to buffer
                    with self._frame_lock:
                        self._frame_buffer.append(received)
                        self._frames_received += 1
                        self._bytes_received += img_array.nbytes

                    self._frame_event.set()

                    # Notify callbacks
                    for callback in self._on_frame_callbacks:
                        try:
                            callback(received)
                        except Exception as e:
                            logger.debug(f"Frame callback error: {e}")

                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    logger.debug(f"Frame receive error: {e}")
                    break

        except Exception as e:
            logger.debug(f"Receive loop error: {e}")
            self._set_state(ReceiverState.ERROR)

    def wait_for_frame(self, timeout: float = 5.0) -> bool:
        """Wait for at least one frame to be received.

        :param timeout: Maximum time to wait in seconds
        :return: True if a frame was received, False if timeout
        """
        return self._frame_event.wait(timeout=timeout)

    def get_frame(self) -> ReceivedFrame | None:
        """Get the most recent frame from the buffer.

        :return: Most recent frame or None if buffer is empty
        """
        with self._frame_lock:
            if self._frame_buffer:
                return self._frame_buffer[-1]
            return None

    def get_all_frames(self) -> list[ReceivedFrame]:
        """Get all frames from the buffer.

        :return: List of all buffered frames
        """
        with self._frame_lock:
            return list(self._frame_buffer)

    def clear_buffer(self) -> None:
        """Clear the frame buffer."""
        with self._frame_lock:
            self._frame_buffer.clear()
        self._frame_event.clear()

    def on_frame(self, callback: Callable[[ReceivedFrame], None]) -> None:
        """Register a callback for new frames.

        :param callback: Function to call with each received frame
        """
        if callback not in self._on_frame_callbacks:
            self._on_frame_callbacks.append(callback)

    def on_state_change(self, callback: Callable[[ReceiverState], None]) -> None:
        """Register a callback for state changes.

        :param callback: Function to call when state changes
        """
        if callback not in self._on_state_callbacks:
            self._on_state_callbacks.append(callback)

    async def _close_async(self) -> None:
        """Close the peer connection (async)."""
        if self._pc:
            await self._pc.close()
            self._pc = None
        self._track = None
        self._set_state(ReceiverState.CLOSED)

    def close(self) -> None:
        """Close the receiver and release resources."""
        self._stop_event.set()

        if self._pc and self._loop:
            try:
                asyncio.run_coroutine_threadsafe(
                    self._close_async(), self._loop
                ).result(timeout=5.0)
            except Exception:
                pass

        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)

        if self._thread:
            self._thread.join(timeout=2.0)

        self._set_state(ReceiverState.CLOSED)

    def get_stats(self) -> dict:
        """Get receiver statistics.

        :return: Dict with frames_received, bytes_received, fps, etc.
        """
        elapsed = 0.0
        if self._start_time:
            elapsed = time.perf_counter() - self._start_time

        fps = 0.0
        if elapsed > 0:
            fps = self._frames_received / elapsed

        return {
            "state": self._state.value,
            "frames_received": self._frames_received,
            "bytes_received": self._bytes_received,
            "buffer_size": self.buffer_size,
            "elapsed_seconds": elapsed,
            "fps": fps,
        }

    def __enter__(self) -> "WebRTCReceiver":
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()
