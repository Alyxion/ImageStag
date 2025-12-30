"""Unit tests for StreamViewPil - headless PIL rendering backend.

Tests for:
- Basic rendering by timestamp
- Rendering by frame index
- Iterating all frames
- Saving frames to files
- Properties (frame_count, duration, fps)
"""

import numpy as np
import pytest
from unittest.mock import MagicMock, patch, PropertyMock

from imagestag import Image
from imagestag.components.pil import StreamViewPil
from imagestag.streams import GeneratorStream


class TestStreamViewPilBasic:
    """Test basic StreamViewPil functionality."""

    def test_creation(self):
        """Test creating a StreamViewPil instance."""
        view = StreamViewPil(1280, 720)
        assert view.width == 1280
        assert view.height == 720
        assert view.target_fps == 60

    def test_creation_with_title(self):
        """Test creating with custom title."""
        view = StreamViewPil(640, 480, title="Test View")
        assert view.title == "Test View"

    def test_add_layer(self):
        """Test adding a layer."""
        view = StreamViewPil(100, 100)
        frame = Image(np.zeros((100, 100, 3), dtype=np.uint8), pixel_format='RGB')

        layer = view.add_layer(
            stream=GeneratorStream(lambda ts: frame),
            z_index=0,
        )

        assert layer is not None
        assert layer.id in [l.id for l in view.layers]

    def test_remove_layer(self):
        """Test removing a layer."""
        view = StreamViewPil(100, 100)
        frame = Image(np.zeros((100, 100, 3), dtype=np.uint8), pixel_format='RGB')

        layer = view.add_layer(stream=GeneratorStream(lambda ts: frame))
        view.remove_layer(layer.id)

        assert layer.id not in [l.id for l in view.layers]


class TestStreamViewPilRender:
    """Test StreamViewPil rendering functionality."""

    def test_render_by_timestamp(self):
        """Test rendering at a timestamp."""
        view = StreamViewPil(100, 100)

        # Create a generator that returns different images based on timestamp
        def generator(ts):
            value = int(ts * 100) % 256
            pixels = np.full((100, 100, 3), value, dtype=np.uint8)
            return Image(pixels, pixel_format='RGB')

        view.add_layer(stream=GeneratorStream(generator))
        view.start()

        pil_img = view.render(timestamp=0.5)
        assert pil_img is not None
        assert pil_img.size == (100, 100)
        assert pil_img.mode == 'RGB'

        view.stop()

    def test_render_to_image(self):
        """Test render_to_image returns imagestag Image."""
        view = StreamViewPil(100, 100)
        frame = Image(np.ones((100, 100, 3), dtype=np.uint8) * 128, pixel_format='RGB')
        view.add_layer(stream=GeneratorStream(lambda ts: frame))
        view.start()

        img = view.render_to_image(timestamp=0.0)
        assert isinstance(img, Image)
        assert img.width == 100
        assert img.height == 100

        view.stop()

    def test_render_static_image(self):
        """Test rendering with static image layer."""
        view = StreamViewPil(100, 100)
        frame = Image(np.ones((100, 100, 3), dtype=np.uint8) * 255, pixel_format='RGB')

        view.add_layer(image=frame)
        view.start()

        pil_img = view.render(timestamp=0.0)
        assert pil_img is not None

        # Check pixel value is white
        pixel = pil_img.getpixel((50, 50))
        assert pixel == (255, 255, 255)

        view.stop()


class TestStreamViewPilWithVideo:
    """Test StreamViewPil with video-like streams."""

    def test_frame_count_from_video(self):
        """Test frame_count property with a video stream."""
        view = StreamViewPil(100, 100)

        # Mock a video stream with frame_count
        mock_stream = MagicMock()
        mock_stream.frame_count = 300
        mock_stream.fps = 30.0
        mock_stream.duration = 10.0
        mock_stream.last_frame_timestamp = 0.0
        mock_stream.is_paused = False

        layer = view.add_layer(stream=mock_stream)
        view.start()

        assert view.frame_count == 300
        assert view.fps == 30.0
        assert view.duration == 10.0

        view.stop()

    def test_frame_count_zero_for_generator(self):
        """Test frame_count is 0 for infinite streams."""
        view = StreamViewPil(100, 100)
        frame = Image(np.zeros((100, 100, 3), dtype=np.uint8), pixel_format='RGB')
        view.add_layer(stream=GeneratorStream(lambda ts: frame))
        view.start()

        assert view.frame_count == 0
        assert view.fps == 30.0  # default

        view.stop()

    def test_render_by_index(self):
        """Test render_by_index with a video-like stream."""
        view = StreamViewPil(100, 100)

        # Mock stream with get_frame_by_index
        call_log = []

        class MockVideoStream:
            def __init__(self):
                self.frame_count = 300
                self.fps = 30.0
                self.last_frame_timestamp = 0.0
                self.is_paused = False

            def get_frame_by_index(self, index):
                call_log.append(index)
                pixels = np.full((100, 100, 3), index % 256, dtype=np.uint8)
                return Image(pixels, pixel_format='RGB'), index

            def get_frame(self, ts):
                self.last_frame_timestamp = ts
                pixels = np.full((100, 100, 3), int(ts * 30) % 256, dtype=np.uint8)
                return Image(pixels, pixel_format='RGB'), int(ts * 30)

            def start(self):
                pass

            def stop(self):
                pass

        view.add_layer(stream=MockVideoStream())
        view.start()

        pil_img = view.render_by_index(150)
        assert pil_img is not None
        assert 150 in call_log

        view.stop()

    def test_render_all_frames_raises_on_infinite(self):
        """Test that render_all_frames raises for infinite streams."""
        view = StreamViewPil(100, 100)
        frame = Image(np.zeros((100, 100, 3), dtype=np.uint8), pixel_format='RGB')
        view.add_layer(stream=GeneratorStream(lambda ts: frame))
        view.start()

        with pytest.raises(ValueError, match="no video layer with known frame count"):
            list(view.render_all_frames())

        view.stop()


class TestStreamViewPilSave:
    """Test StreamViewPil save functionality."""

    def test_save_frame(self, tmp_path):
        """Test saving a frame to file."""
        view = StreamViewPil(100, 100)
        frame = Image(np.ones((100, 100, 3), dtype=np.uint8) * 128, pixel_format='RGB')
        view.add_layer(stream=GeneratorStream(lambda ts: frame))
        view.start()

        output_path = tmp_path / "test_frame.png"
        view.save_frame(str(output_path), timestamp=0.0)

        assert output_path.exists()
        assert output_path.stat().st_size > 0

        view.stop()

    def test_save_frame_jpg(self, tmp_path):
        """Test saving a frame as JPEG."""
        view = StreamViewPil(100, 100)
        frame = Image(np.ones((100, 100, 3), dtype=np.uint8) * 200, pixel_format='RGB')
        view.add_layer(stream=GeneratorStream(lambda ts: frame))
        view.start()

        output_path = tmp_path / "test_frame.jpg"
        view.save_frame(str(output_path), timestamp=0.0, quality=95)

        assert output_path.exists()

        view.stop()


class TestStreamViewPilLifecycle:
    """Test StreamViewPil lifecycle methods."""

    def test_start_stop(self):
        """Test start and stop methods."""
        view = StreamViewPil(100, 100)
        frame = Image(np.zeros((100, 100, 3), dtype=np.uint8), pixel_format='RGB')
        view.add_layer(stream=GeneratorStream(lambda ts: frame))

        assert not view.is_running

        view.start()
        assert view.is_running

        view.stop()
        assert not view.is_running

    def test_run_is_noop(self):
        """Test that run() just calls start() for headless mode."""
        view = StreamViewPil(100, 100)
        frame = Image(np.zeros((100, 100, 3), dtype=np.uint8), pixel_format='RGB')
        view.add_layer(stream=GeneratorStream(lambda ts: frame))

        view.run()
        assert view.is_running

        view.stop()

    def test_run_async_returns_thread(self):
        """Test that run_async returns a thread."""
        view = StreamViewPil(100, 100)
        frame = Image(np.zeros((100, 100, 3), dtype=np.uint8), pixel_format='RGB')
        view.add_layer(stream=GeneratorStream(lambda ts: frame))

        import threading
        thread = view.run_async()
        assert isinstance(thread, threading.Thread)
        assert view.is_running

        view.stop()


class TestStreamViewPilMultipleLayers:
    """Test StreamViewPil with multiple layers."""

    def test_multiple_layers_composition(self):
        """Test rendering with multiple layers."""
        view = StreamViewPil(100, 100)

        # Background layer (red)
        bg_frame = Image(np.zeros((100, 100, 3), dtype=np.uint8), pixel_format='RGB')
        bg_frame.get_pixels()[:, :, 0] = 255  # Red channel

        # Foreground layer (50x50 green at center)
        fg_frame = Image(np.zeros((50, 50, 3), dtype=np.uint8), pixel_format='RGB')
        fg_frame.get_pixels()[:, :, 1] = 255  # Green channel

        view.add_layer(stream=GeneratorStream(lambda ts: bg_frame), z_index=0)
        view.add_layer(
            stream=GeneratorStream(lambda ts: fg_frame),
            z_index=1,
            x=25, y=25,
            width=50, height=50,
        )

        view.start()
        pil_img = view.render(timestamp=0.0)
        assert pil_img is not None

        view.stop()


class TestStreamViewPilInheritance:
    """Test that StreamViewPil properly inherits from StreamViewBase."""

    def test_has_base_methods(self):
        """Test that base class methods are available."""
        view = StreamViewPil(100, 100)

        # Check layer management methods
        assert hasattr(view, 'add_layer')
        assert hasattr(view, 'remove_layer')
        assert hasattr(view, 'get_layer')
        assert hasattr(view, 'layers')

        # Check viewport methods
        assert hasattr(view, 'viewport')
        assert hasattr(view, 'set_zoom')
        assert hasattr(view, 'reset_zoom')

        # Check event decorators
        assert hasattr(view, 'on_key')
        assert hasattr(view, 'on_mouse')
        assert hasattr(view, 'on_resize')

        # Check lifecycle
        assert hasattr(view, 'start')
        assert hasattr(view, 'stop')
        assert hasattr(view, 'pause')
        assert hasattr(view, 'resume')
        assert hasattr(view, 'toggle_pause')
        assert hasattr(view, 'is_paused')
        assert hasattr(view, 'is_running')

    def test_viewport_control(self):
        """Test viewport control works."""
        view = StreamViewPil(100, 100)

        view.set_zoom(2.0, 0.5, 0.5)
        assert view.viewport.zoom == 2.0

        view.reset_zoom()
        assert view.viewport.zoom == 1.0
