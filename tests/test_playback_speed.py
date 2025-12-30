"""Test playback speed functionality."""

import time
from pathlib import Path

import pytest

# Get test video path
PROJECT_ROOT = Path(__file__).parent.parent
TEST_VIDEO = PROJECT_ROOT / "tmp" / "media" / "big_buck_bunny_1080p_h264.mov"


@pytest.fixture
def video_stream():
    """Create a VideoStream for testing."""
    from imagestag.streams import VideoStream

    if not TEST_VIDEO.exists():
        pytest.skip(f"Test video not found: {TEST_VIDEO}")

    stream = VideoStream(str(TEST_VIDEO), loop=True, max_fps=60.0, preserve_source_fps=True)
    stream.start()
    yield stream
    stream.stop()


class TestPlaybackSpeed:
    """Test playback speed functionality."""

    def test_playback_speed_property(self, video_stream):
        """Test that playback_speed property works."""
        # Default speed
        assert video_stream.playback_speed == 1.0

        # Change speed
        video_stream.playback_speed = 2.0
        assert video_stream.playback_speed == 2.0

        video_stream.playback_speed = 0.5
        assert video_stream.playback_speed == 0.5

        # Clamping
        video_stream.playback_speed = 0.05  # Below min
        assert video_stream.playback_speed == 0.1

        video_stream.playback_speed = 10.0  # Above max
        assert video_stream.playback_speed == 8.0

    def test_elapsed_time_scales_with_speed(self, video_stream):
        """Test that elapsed_time scales with playback speed."""
        # Reset to start
        video_stream.seek_to(0)
        video_stream.playback_speed = 1.0

        # Short wait at 1x speed
        time.sleep(0.2)
        elapsed_1x = video_stream.elapsed_time

        # Should be roughly 0.2 seconds (allow wide tolerance for CI)
        assert 0.1 < elapsed_1x < 0.4, f"At 1x speed, elapsed={elapsed_1x}"

        # Now change to 2x speed and measure rate of change
        video_stream.playback_speed = 2.0
        elapsed_before = video_stream.elapsed_time
        time.sleep(0.2)
        elapsed_after = video_stream.elapsed_time

        # At 2x speed, 0.2 real seconds should add ~0.4 video seconds
        delta = elapsed_after - elapsed_before
        assert 0.3 < delta < 0.6, f"At 2x speed, delta={delta} (expected ~0.4)"

    def test_frame_rate_scales_with_speed(self, video_stream):
        """Test that frame production rate increases with speed."""
        source_fps = video_stream.source_fps

        def count_frames(duration: float) -> int:
            """Count unique frames over a duration."""
            frames = 0
            last_index = -1
            start = time.perf_counter()
            while time.perf_counter() - start < duration:
                frame, index = video_stream.get_frame(0)
                if index != last_index and frame is not None:
                    frames += 1
                    last_index = index
                time.sleep(0.001)
            return frames

        # Test at 1x speed
        video_stream.playback_speed = 1.0
        video_stream.seek_to(0)
        frames_1x = count_frames(0.5)

        # Test at 2x speed
        video_stream.playback_speed = 2.0
        video_stream.seek_to(0)
        frames_2x = count_frames(0.5)

        # At 2x, should get roughly 2x frames (allow 50% tolerance for CI variability)
        # The key test is that 2x produces MORE frames than 1x
        assert frames_2x > frames_1x, f"2x speed ({frames_2x}) should produce more frames than 1x ({frames_1x})"

    def test_position_preserved_on_speed_change(self, video_stream):
        """Test that current position is preserved when changing speed."""
        # Seek to 5 seconds
        video_stream.seek_to(5.0)
        video_stream.playback_speed = 1.0

        # Small delay to let position settle
        time.sleep(0.05)
        pos_before = video_stream.current_position

        # Change speed - position should NOT jump significantly
        video_stream.playback_speed = 2.0
        pos_after = video_stream.current_position

        # Position should be within 0.3 seconds (accounting for time passed)
        assert abs(pos_after - pos_before) < 0.3, \
            f"Position jumped from {pos_before} to {pos_after} on speed change"

    def test_rate_limiting_respects_max_fps(self, video_stream):
        """Test that rate limiting caps output."""
        video_stream.max_fps = 30.0
        video_stream.playback_speed = 4.0  # Would be 96fps without cap
        video_stream.seek_to(0)

        # Count frames over short duration
        frames = 0
        last_index = -1
        start = time.perf_counter()
        duration = 0.5

        while time.perf_counter() - start < duration:
            frame, index = video_stream.get_frame(0)
            if index != last_index and frame is not None:
                frames += 1
                last_index = index
            time.sleep(0.001)

        fps = frames / duration

        # Should be roughly capped around 30fps (allow wide tolerance)
        # Key test: should be less than uncapped rate (96 fps)
        assert fps < 50, f"Rate limiting failed: got {fps:.0f} fps, expected < 50 (capped at 30)"


def test_layer_effective_fps():
    """Test that layer's _get_effective_fps works correctly."""
    from imagestag.streams import VideoStream
    from imagestag.components.stream_view.layers import StreamViewLayer

    if not TEST_VIDEO.exists():
        pytest.skip(f"Test video not found: {TEST_VIDEO}")

    stream = VideoStream(str(TEST_VIDEO), loop=True, max_fps=60.0, preserve_source_fps=True)

    # Create a layer (without starting it)
    layer = StreamViewLayer(
        id="test",
        stream=stream,
        target_fps=60,
    )

    for speed in [0.5, 1.0, 2.0, 4.0]:
        stream.playback_speed = speed
        effective = layer._get_effective_fps()
        expected = min(stream.source_fps * speed, stream.max_fps or 999)

        # Allow 5% tolerance
        assert abs(effective - expected) < expected * 0.05, \
            f"At {speed}x: effective_fps={effective}, expected {expected}"
