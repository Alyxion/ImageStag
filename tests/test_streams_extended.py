"""Extended tests for streams: multi_output, camera, video, generator."""

import time
import pytest
from unittest.mock import MagicMock, patch
import numpy as np

from imagestag import Image
from imagestag.streams.base import ImageStream
from imagestag.streams.generator import GeneratorStream


class TestImageStreamBase:
    """Extended tests for ImageStream base class."""

    def test_stream_threaded_mode(self):
        """Test threaded stream mode."""
        class SimpleStream(ImageStream):
            def __init__(self):
                super().__init__(threaded=True, target_fps=10.0)
                self._counter = 0

            def get_frame(self, timestamp: float):
                self._counter += 1
                arr = np.full((10, 10, 3), self._counter % 256, dtype=np.uint8)
                frame = Image.from_array(arr)
                return (frame, self._store_frame(frame))

        stream = SimpleStream()
        stream.start()

        try:
            assert stream.threaded is True
            assert stream.target_fps == 10.0
            assert stream._thread is not None
            assert stream._thread.is_alive()

            time.sleep(0.3)
            assert stream.frame_index > 0
        finally:
            stream.stop()

    def test_stream_target_fps_setter(self):
        """Test target_fps setter clamps values."""
        class SimpleStream(ImageStream):
            def get_frame(self, timestamp: float):
                return (None, 0)

        stream = SimpleStream()

        stream.target_fps = 200.0
        assert stream.target_fps == 120.0

        stream.target_fps = 0.1
        assert stream.target_fps == 1.0

    def test_stream_pause_resume_timing(self):
        """Test that pause/resume maintains correct elapsed_time."""
        class SimpleStream(ImageStream):
            def get_frame(self, timestamp: float):
                return (None, 0)

        stream = SimpleStream()
        stream.start()

        try:
            time.sleep(0.1)
            elapsed_before_pause = stream.elapsed_time

            stream.pause()
            time.sleep(0.2)

            assert abs(stream.elapsed_time - elapsed_before_pause) < 0.05

            stream.resume()
            time.sleep(0.1)

            elapsed_after_resume = stream.elapsed_time
            expected = elapsed_before_pause + 0.1
            assert abs(elapsed_after_resume - expected) < 0.05
        finally:
            stream.stop()

    def test_stream_toggle_pause(self):
        """Test toggle_pause method."""
        class SimpleStream(ImageStream):
            def get_frame(self, timestamp: float):
                return (None, 0)

        stream = SimpleStream()
        stream.start()

        try:
            assert stream.is_paused is False

            stream.toggle_pause()
            assert stream.is_paused is True

            stream.toggle_pause()
            assert stream.is_paused is False
        finally:
            stream.stop()

    def test_stream_frame_count_property(self):
        """Test frame_count and has_frame_count properties."""
        class SimpleStream(ImageStream):
            def get_frame(self, timestamp: float):
                return (None, 0)

        stream = SimpleStream()

        assert stream.frame_count == 0
        assert stream.has_frame_count is False

    def test_stream_duration_property(self):
        """Test duration and is_seekable properties."""
        class SimpleStream(ImageStream):
            def get_frame(self, timestamp: float):
                return (None, 0)

        stream = SimpleStream()

        assert stream.duration == 0.0
        assert stream.is_seekable is False

    def test_stream_subscribe_unsubscribe(self):
        """Test frame subscription."""
        class SimpleStream(ImageStream):
            def get_frame(self, timestamp: float):
                arr = np.zeros((10, 10, 3), dtype=np.uint8)
                frame = Image.from_array(arr)
                return (frame, self._store_frame(frame))

        stream = SimpleStream()

        event = stream.subscribe()
        assert event is not None
        assert event in stream._frame_subscribers

        stream.unsubscribe(event)
        assert event not in stream._frame_subscribers

    def test_stream_wait_for_frame(self):
        """Test wait_for_frame method."""
        class SimpleStream(ImageStream):
            def __init__(self):
                super().__init__(threaded=True, target_fps=30.0)

            def get_frame(self, timestamp: float):
                arr = np.zeros((10, 10, 3), dtype=np.uint8)
                frame = Image.from_array(arr)
                return (frame, self._store_frame(frame))

        stream = SimpleStream()
        stream.start()

        try:
            result = stream.wait_for_frame(timeout=1.0)
            assert result is True
        finally:
            stream.stop()

    def test_stream_on_frame_callback(self):
        """Test on_frame callback registration."""
        class SimpleStream(ImageStream):
            def get_frame(self, timestamp: float):
                arr = np.zeros((10, 10, 3), dtype=np.uint8)
                frame = Image.from_array(arr)
                return (frame, self._store_frame(frame))

        stream = SimpleStream()

        received_frames = []

        def callback(frame, timestamp):
            received_frames.append((frame, timestamp))

        stream.on_frame(callback)
        stream.get_frame(0.0)

        time.sleep(0.1)

        assert len(received_frames) == 1

    def test_stream_remove_on_frame_callback(self):
        """Test removing on_frame callback."""
        class SimpleStream(ImageStream):
            def get_frame(self, timestamp: float):
                arr = np.zeros((10, 10, 3), dtype=np.uint8)
                frame = Image.from_array(arr)
                return (frame, self._store_frame(frame))

        stream = SimpleStream()

        callback = MagicMock()
        stream.on_frame(callback)
        stream.remove_on_frame(callback)

        stream.get_frame(0.0)
        time.sleep(0.1)

        callback.assert_not_called()

    def test_stream_prevents_duplicate_callbacks(self):
        """Test that duplicate callbacks are not registered."""
        class SimpleStream(ImageStream):
            def get_frame(self, timestamp: float):
                return (None, 0)

        stream = SimpleStream()

        callback = MagicMock()
        stream.on_frame(callback)
        stream.on_frame(callback)

        assert len(stream._on_frame_callbacks) == 1

    def test_stream_callback_limit(self):
        """Test callback limit (100 max)."""
        class SimpleStream(ImageStream):
            def get_frame(self, timestamp: float):
                return (None, 0)

        stream = SimpleStream()

        for i in range(100):
            stream.on_frame(lambda f, t, i=i: None)

        extra_callback = MagicMock()
        stream.on_frame(extra_callback)

        assert len(stream._on_frame_callbacks) == 100


class TestGeneratorStreamExtended:
    """Extended tests for GeneratorStream."""

    def test_generator_stream_with_source_dependency(self):
        """Test GeneratorStream with source stream dependency."""
        source = GeneratorStream(
            handler=lambda t: Image.from_array(np.zeros((10, 10, 3), dtype=np.uint8))
        )

        def process_frame(t):
            frame = source.last_frame
            if frame:
                arr = 255 - frame.get_pixels()
                return Image.from_array(arr)
            return None

        dependent = GeneratorStream(handler=process_frame, source=source)

        source.get_frame(0.0)
        frame, idx = dependent.get_frame(0.0)

        assert frame is not None

    def test_generator_stream_caches_when_source_unchanged(self):
        """Test that GeneratorStream caches results when source unchanged."""
        call_count = [0]

        source = GeneratorStream(
            handler=lambda t: Image.from_array(np.zeros((10, 10, 3), dtype=np.uint8))
        )

        def process_frame(t):
            call_count[0] += 1
            return source.last_frame

        dependent = GeneratorStream(handler=process_frame, source=source)

        source.get_frame(0.0)

        dependent.get_frame(0.0)
        dependent.get_frame(0.0)
        dependent.get_frame(0.0)

        assert call_count[0] == 1

    def test_generator_stream_render_override(self):
        """Test GeneratorStream with render() override."""
        class CustomStream(GeneratorStream):
            def __init__(self):
                super().__init__()
                self.render_count = 0

            def render(self, timestamp: float):
                self.render_count += 1
                arr = np.full((10, 10, 3), self.render_count, dtype=np.uint8)
                return Image.from_array(arr)

        stream = CustomStream()
        frame1, _ = stream.get_frame(0.0)
        frame2, _ = stream.get_frame(0.1)

        assert stream.render_count == 2
        assert frame1 is not None
        assert frame2 is not None

    def test_generator_stream_multi_output(self):
        """Test GeneratorStream with multiple outputs (dict return)."""
        def multi_handler(t):
            return {
                "rgb": Image.from_array(np.zeros((10, 10, 3), dtype=np.uint8)),
                "gray": Image.from_array(np.zeros((10, 10), dtype=np.uint8)),
            }

        stream = GeneratorStream(handler=multi_handler)
        frame, idx = stream.get_frame(0.0)

        assert frame is not None

    def test_generator_stream_tuple_with_timestamp(self):
        """Test GeneratorStream with tuple return (frame, timestamp)."""
        def handler_with_timestamp(t):
            frame = Image.from_array(np.zeros((10, 10, 3), dtype=np.uint8))
            return (frame, time.perf_counter())

        stream = GeneratorStream(handler=handler_with_timestamp)
        frame, idx = stream.get_frame(0.0)

        assert frame is not None

    def test_generator_stream_tuple_with_timings(self):
        """Test GeneratorStream with tuple return (frame, timestamp, timings)."""
        def handler_with_timings(t):
            frame = Image.from_array(np.zeros((10, 10, 3), dtype=np.uint8))
            return (frame, time.perf_counter(), {"step1": 0.001})

        stream = GeneratorStream(handler=handler_with_timings)
        frame, idx = stream.get_frame(0.0)

        assert frame is not None

    def test_generator_stream_returns_none_when_paused(self):
        """Test that GeneratorStream returns None when paused."""
        stream = GeneratorStream(
            handler=lambda t: Image.from_array(np.zeros((10, 10, 3), dtype=np.uint8))
        )
        stream.start()
        stream.pause()

        frame, idx = stream.get_frame(0.0)
        assert frame is None

        stream.stop()


class TestMultiOutputStream:
    """Tests for MultiOutputStream class."""

    def test_multi_output_layer_config(self):
        """Test LayerConfig dataclass."""
        from imagestag.streams.multi_output import LayerConfig

        config = LayerConfig(
            format="jpeg",
            quality=90,
            z_index=5,
        )

        assert config.format == "jpeg"
        assert config.quality == 90
        assert config.z_index == 5

    def test_multi_output_layer_output(self):
        """Test LayerOutput dataclass."""
        from imagestag.streams.multi_output import LayerOutput, LayerConfig

        output = LayerOutput(
            name="test_layer",
            config=LayerConfig(format="png"),
        )

        assert output.name == "test_layer"
        assert output.config.format == "png"
        assert output.image is None
        assert output.dirty is False



class TestCameraStream:
    """Tests for CameraStream class."""

    def test_camera_stream_get_cv2(self):
        """Test _get_cv2 helper function."""
        from imagestag.streams.camera import _get_cv2

        cv2 = _get_cv2()
        assert cv2 is not None
