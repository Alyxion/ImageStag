"""WebRTC client component for receiving video streams.

This module provides a WebRTC receiver client that can connect to
WebRTC video streams from any server and expose received frames
for processing.
"""

from .receiver import WebRTCReceiver, ReceiverState

__all__ = ["WebRTCReceiver", "ReceiverState"]
