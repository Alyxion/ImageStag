"""Unit tests for imagestag.streams package.

Tests for the stream class hierarchy:
- ImageStream: Base class with lifecycle and frame sharing
- DecoderStream: Base for decoder-based streams
- VideoStream: Video file playback
- CameraStream: Camera capture
- GeneratorStream: Procedural frame generation
"""

import time
import threading
from unittest.mock import Mock, MagicMock, patch
import pytest
import numpy as np

from imagestag import Image
from imagestag.streams import (
    ImageStream,
    DecoderStream,
    VideoStream,
    CameraStream,
    GeneratorStream,
    CustomStream,
)


# =============================================================================
# ImageStream Tests
# =============================================================================

class ConcreteImageStream(ImageStream):
    """Concrete implementation for testing ImageStream."""

    def __init__(self):
        super().__init__()
        self._frames = []
        self._call_count = 0

    def add_frame(self, frame: Image):
        self._frames.append(frame)

    def get_frame(self, timestamp: float):
        self._call_count += 1
        if self._frames:
            frame = self._frames[0]
            if len(self._frames) > 1:
                self._frames.pop(0)
            return (frame, self._store_frame(frame))
        return (None, self._frame_index)


class TestImageStreamLifecycle:
    """Test ImageStream lifecycle management."""

    def test_initial_state(self):
        stream = ConcreteImageStream()
        assert not stream.is_running
        assert not stream.is_paused
        assert stream.frame_index == 0
        assert stream.elapsed_time == 0.0

    def test_start_sets_running(self):
        stream = ConcreteImageStream()
        stream.start()
        assert stream.is_running
        assert not stream.is_paused

    def test_stop_clears_running(self):
        stream = ConcreteImageStream()
        stream.start()
        stream.stop()
        assert not stream.is_running

    def test_pause_sets_paused(self):
        stream = ConcreteImageStream()
        stream.start()
        stream.pause()
        assert stream.is_paused
        # Note: is_running stays True for paused state

    def test_resume_clears_paused(self):
        stream = ConcreteImageStream()
        stream.start()
        stream.pause()
        stream.resume()
        assert not stream.is_paused

    def test_toggle_pause(self):
        stream = ConcreteImageStream()
        stream.start()
        assert not stream.is_paused
        stream.toggle_pause()
        assert stream.is_paused
        stream.toggle_pause()
        assert not stream.is_paused


class TestImageStreamElapsedTime:
    """Test elapsed time tracking with pause/resume."""

    def test_elapsed_time_increases(self):
        stream = ConcreteImageStream()
        stream.start()
        time.sleep(0.05)
        elapsed = stream.elapsed_time
        assert elapsed >= 0.04

    def test_elapsed_time_paused(self):
        stream = ConcreteImageStream()
        stream.start()
        time.sleep(0.05)
        stream.pause()
        paused_time = stream.elapsed_time
        time.sleep(0.05)
        # Should still be approximately the same
        assert abs(stream.elapsed_time - paused_time) < 0.01

    def test_elapsed_time_resumes_correctly(self):
        stream = ConcreteImageStream()
        stream.start()
        time.sleep(0.05)
        stream.pause()
        paused_time = stream.elapsed_time
        time.sleep(0.05)  # Time passes while paused
        stream.resume()
        time.sleep(0.05)  # Time passes after resume
        # Should be approximately paused_time + 0.05 (not counting pause)
        assert stream.elapsed_time >= paused_time + 0.04


class TestImageStreamFrameTracking:
    """Test frame index and frame storage."""

    def test_frame_index_increments(self):
        stream = ConcreteImageStream()
        frame = Image(np.zeros((10, 10, 3), dtype=np.uint8), pixel_format='RGB')
        stream.add_frame(frame)

        stream.start()
        initial_index = stream.frame_index
        result = stream.get_frame(0.0)
        assert result[1] > initial_index

    def test_last_frame_stored(self):
        stream = ConcreteImageStream()
        frame = Image(np.zeros((10, 10, 3), dtype=np.uint8), pixel_format='RGB')
        stream.add_frame(frame)

        stream.start()
        stream.get_frame(0.0)
        assert stream.last_frame is not None
        assert stream.last_frame.width == 10

    def test_last_frame_timestamp_set(self):
        stream = ConcreteImageStream()
        frame = Image(np.zeros((10, 10, 3), dtype=np.uint8), pixel_format='RGB')
        stream.add_frame(frame)

        stream.start()
        before = time.perf_counter()
        stream.get_frame(0.0)
        after = time.perf_counter()

        ts = stream.last_frame_timestamp
        assert before <= ts <= after

    def test_get_last_frame_with_timestamp(self):
        stream = ConcreteImageStream()
        frame = Image(np.zeros((10, 10, 3), dtype=np.uint8), pixel_format='RGB')
        stream.add_frame(frame)

        stream.start()
        stream.get_frame(0.0)

        img, ts = stream.get_last_frame_with_timestamp()
        assert img is not None
        assert ts > 0


class TestImageStreamSubscribers:
    """Test subscriber notification system."""

    def test_subscribe_returns_event(self):
        stream = ConcreteImageStream()
        event = stream.subscribe()
        assert isinstance(event, threading.Event)

    def test_subscribers_notified_on_frame(self):
        stream = ConcreteImageStream()
        frame = Image(np.zeros((10, 10, 3), dtype=np.uint8), pixel_format='RGB')
        stream.add_frame(frame)

        event = stream.subscribe()
        assert not event.is_set()

        stream.start()
        stream.get_frame(0.0)
        assert event.is_set()

    def test_unsubscribe_removes_event(self):
        stream = ConcreteImageStream()
        event = stream.subscribe()
        stream.unsubscribe(event)

        # Event should not be in subscribers list anymore
        frame = Image(np.zeros((10, 10, 3), dtype=np.uint8), pixel_format='RGB')
        stream.add_frame(frame)
        stream.start()
        stream.get_frame(0.0)
        # No error should occur


class TestImageStreamCallbacks:
    """Test on_frame callback system."""

    def test_on_frame_callback_called(self):
        stream = ConcreteImageStream()
        frame = Image(np.zeros((10, 10, 3), dtype=np.uint8), pixel_format='RGB')
        stream.add_frame(frame)

        callback_called = threading.Event()
        received_frame = []

        def callback(f, ts):
            received_frame.append(f)
            callback_called.set()

        stream.on_frame(callback)
        stream.start()
        stream.get_frame(0.0)

        # Wait for callback (runs in thread pool)
        callback_called.wait(timeout=1.0)
        assert len(received_frame) == 1

    def test_remove_on_frame_callback(self):
        stream = ConcreteImageStream()
        callback = Mock()

        stream.on_frame(callback)
        stream.remove_on_frame(callback)

        frame = Image(np.zeros((10, 10, 3), dtype=np.uint8), pixel_format='RGB')
        stream.add_frame(frame)
        stream.start()
        stream.get_frame(0.0)

        time.sleep(0.1)  # Give time for callbacks to run
        callback.assert_not_called()


# =============================================================================
# GeneratorStream Tests
# =============================================================================

class TestGeneratorStream:
    """Test GeneratorStream functionality."""

    def test_basic_generation(self):
        def handler(ts):
            return Image(np.zeros((10, 10, 3), dtype=np.uint8), pixel_format='RGB')

        stream = GeneratorStream(handler)
        stream.start()
        frame, index = stream.get_frame(0.0)

        assert frame is not None
        assert index > 0

    def test_handler_receives_timestamp(self):
        received_ts = []

        def handler(ts):
            received_ts.append(ts)
            return Image(np.zeros((10, 10, 3), dtype=np.uint8), pixel_format='RGB')

        stream = GeneratorStream(handler)
        stream.start()
        stream.get_frame(1.5)
        stream.get_frame(2.5)

        assert 1.5 in received_ts
        assert 2.5 in received_ts

    def test_none_return_preserves_index(self):
        def handler(ts):
            return None

        stream = GeneratorStream(handler)
        stream.start()
        initial_index = stream.frame_index
        _, index = stream.get_frame(0.0)

        assert index == initial_index

    def test_source_dependency(self):
        """Test that GeneratorStream with source only updates on new source frames."""
        # Create source stream
        source = ConcreteImageStream()
        frame1 = Image(np.ones((10, 10, 3), dtype=np.uint8) * 100, pixel_format='RGB')
        source.add_frame(frame1)
        source.start()

        # Create generator that depends on source
        process_count = [0]

        def handler(ts):
            process_count[0] += 1
            return source.last_frame

        gen = GeneratorStream(handler, source=source)
        gen.start()

        # First call - should process
        source.get_frame(0.0)  # Populate source with a frame
        gen.get_frame(0.0)
        first_count = process_count[0]

        # Second call without source change - should use cached
        gen.get_frame(0.1)
        assert process_count[0] == first_count  # No new processing

    def test_customstream_alias(self):
        """Test that CustomStream is an alias for GeneratorStream."""
        assert CustomStream is GeneratorStream


# =============================================================================
# VideoStream Tests (with mocked OpenCV)
# =============================================================================

class TestVideoStream:
    """Test VideoStream functionality."""

    @patch('imagestag.streams.video._get_cv2')
    def test_initialization(self, mock_get_cv2):
        mock_cv2 = MagicMock()
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.get.return_value = 30.0
        mock_cv2.VideoCapture.return_value = mock_cap
        mock_get_cv2.return_value = mock_cv2

        stream = VideoStream('/path/to/video.mp4', loop=True)
        assert stream.loop is True
        assert stream._path == '/path/to/video.mp4'

    def test_properties(self):
        stream = VideoStream('/path/to/video.mp4', loop=False, target_fps=60.0)
        assert stream.loop is False
        assert stream.has_duration is True
        assert stream.is_seekable is True

    @patch('imagestag.streams.video._get_cv2')
    def test_start_opens_capture(self, mock_get_cv2):
        mock_cv2 = MagicMock()
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.get.return_value = 30.0
        mock_cv2.VideoCapture.return_value = mock_cap
        mock_get_cv2.return_value = mock_cv2

        stream = VideoStream('/path/to/video.mp4')
        stream.start()

        assert stream.is_running
        mock_cv2.VideoCapture.assert_called()

    @patch('imagestag.streams.video._get_cv2')
    def test_stop_releases_capture(self, mock_get_cv2):
        mock_cv2 = MagicMock()
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.get.return_value = 30.0
        mock_cv2.VideoCapture.return_value = mock_cap
        mock_get_cv2.return_value = mock_cv2

        stream = VideoStream('/path/to/video.mp4')
        stream.start()
        stream.stop()

        mock_cap.release.assert_called()

    @patch('imagestag.streams.video._get_cv2')
    def test_seek_to(self, mock_get_cv2):
        mock_cv2 = MagicMock()
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.get.side_effect = lambda prop: {
            mock_cv2.CAP_PROP_FPS: 30.0,
            mock_cv2.CAP_PROP_FRAME_COUNT: 300,
        }.get(prop, 0)
        mock_cv2.VideoCapture.return_value = mock_cap
        mock_get_cv2.return_value = mock_cv2

        stream = VideoStream('/path/to/video.mp4')
        stream.start()
        stream.seek_to(5.0)

        # elapsed_time should now be approximately 5.0
        assert abs(stream.current_position - 5.0) < 0.1


# =============================================================================
# CameraStream Tests (with mocked OpenCV)
# =============================================================================

class TestCameraStream:
    """Test CameraStream functionality."""

    def test_properties(self):
        stream = CameraStream(0)
        assert stream.device == 0
        assert stream.has_duration is False
        assert stream.is_seekable is False

    @patch('imagestag.streams.camera._get_cv2')
    def test_start_opens_camera(self, mock_get_cv2):
        mock_cv2 = MagicMock()
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.get.return_value = 30.0
        mock_cv2.VideoCapture.return_value = mock_cap
        mock_get_cv2.return_value = mock_cv2

        stream = CameraStream(0)
        stream.start()

        assert stream.is_running
        mock_cv2.VideoCapture.assert_called_with(0)

    @patch('imagestag.streams.camera._get_cv2')
    def test_resolution_request(self, mock_get_cv2):
        mock_cv2 = MagicMock()
        mock_cv2.CAP_PROP_FRAME_WIDTH = 3
        mock_cv2.CAP_PROP_FRAME_HEIGHT = 4
        mock_cv2.CAP_PROP_FPS = 5
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.get.return_value = 30.0
        mock_cv2.VideoCapture.return_value = mock_cap
        mock_get_cv2.return_value = mock_cv2

        stream = CameraStream(0, width=1280, height=720)
        stream.start()

        # Should have called set() with width and height
        mock_cap.set.assert_any_call(mock_cv2.CAP_PROP_FRAME_WIDTH, 1280)
        mock_cap.set.assert_any_call(mock_cv2.CAP_PROP_FRAME_HEIGHT, 720)


# =============================================================================
# Integration Tests
# =============================================================================

class TestStreamIntegration:
    """Integration tests for stream classes."""

    def test_generator_frame_index_pattern(self):
        """Test the consumer pattern using frame indices."""
        frames_generated = [0]

        def handler(ts):
            frames_generated[0] += 1
            return Image(
                np.ones((10, 10, 3), dtype=np.uint8) * frames_generated[0],
                pixel_format='RGB'
            )

        stream = GeneratorStream(handler)
        stream.start()

        # Consumer pattern
        last_index = -1
        processed = []

        for i in range(5):
            frame, index = stream.get_frame(float(i))
            if index != last_index:
                processed.append(index)
                last_index = index

        # Should have processed all unique frames
        assert len(processed) == 5
        assert processed == sorted(processed)  # Monotonically increasing

    def test_stream_mode_property(self):
        """Test that mode property works."""
        stream = GeneratorStream(lambda ts: None, mode='sync')
        assert stream.mode == 'sync'

        stream = GeneratorStream(lambda ts: None, mode='thread')
        assert stream.mode == 'thread'


# =============================================================================
# Backwards Compatibility Tests
# =============================================================================

class TestBackwardsCompatibility:
    """Test backwards compatibility with old API."""

    def test_import_from_layers(self):
        """Test that streams can still be imported from layers module."""
        from imagestag.components.stream_view.layers import (
            ImageStream,
            VideoStream,
            CustomStream,
            CameraStream,
            GeneratorStream,
        )
        assert ImageStream is not None
        assert VideoStream is not None
        assert CustomStream is GeneratorStream

    def test_import_from_main_package(self):
        """Test that streams can be imported from main package."""
        from imagestag import (
            ImageStream,
            VideoStream,
            CameraStream,
            GeneratorStream,
            CustomStream,
        )
        assert ImageStream is not None
        assert CustomStream is GeneratorStream
