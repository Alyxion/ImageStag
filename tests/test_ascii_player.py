"""Tests for the AsciiPlayer component."""

import time
from unittest.mock import MagicMock, patch

import pytest

from imagestag.components.ascii import (
    AsciiPlayer,
    AsciiPlayerConfig,
    KeyboardHandler,
    PlaybackController,
    PlaybackState,
    ProgressBarRenderer,
    ProgressBarState,
    RenderMode,
)


class TestAsciiPlayerConfig:
    """Tests for AsciiPlayerConfig dataclass."""

    def test_default_values(self):
        """Test that config has sensible defaults."""
        config = AsciiPlayerConfig()

        # UI visibility defaults
        assert config.show_progress_bar is True
        assert config.show_time is True
        assert config.show_mode is True
        assert config.show_speed is True
        assert config.show_fps is True
        assert config.show_frame is True

        # Control enablement defaults
        assert config.enable_seek is True
        assert config.enable_speed_control is True
        assert config.enable_mode_switch is True

        # Speed options
        assert config.default_speed == 1.0
        assert 1.0 in config.speed_options
        assert 0.5 in config.speed_options
        assert 2.0 in config.speed_options

        # Seek settings
        assert config.seek_step == 5.0
        assert config.cursor_step_percent == 0.01

        # Video scale (default full screen)
        assert config.video_scale == 1.0

    def test_custom_values(self):
        """Test custom configuration values."""
        config = AsciiPlayerConfig(
            show_progress_bar=False,
            show_fps=False,
            enable_seek=False,
            default_speed=1.5,
            seek_step=10.0,
            video_scale=0.67,
        )

        assert config.show_progress_bar is False
        assert config.show_fps is False
        assert config.enable_seek is False
        assert config.default_speed == 1.5
        assert config.seek_step == 10.0
        assert config.video_scale == 0.67


class TestPlaybackState:
    """Tests for PlaybackState enum."""

    def test_all_states_exist(self):
        """Test all expected states exist."""
        assert PlaybackState.STOPPED.value == "stopped"
        assert PlaybackState.PLAYING.value == "playing"
        assert PlaybackState.PAUSED.value == "paused"
        assert PlaybackState.SEEKING.value == "seeking"

    def test_state_count(self):
        """Test that we have exactly 4 states."""
        assert len(PlaybackState) == 4


class TestKeyboardHandler:
    """Tests for KeyboardHandler class."""

    def test_bind_and_call(self):
        """Test binding and calling a handler."""
        mock_terminal = MagicMock()
        handler = KeyboardHandler(mock_terminal)

        callback_called = []

        def callback():
            callback_called.append(True)

        handler.bind("q", callback)

        # Simulate key press
        mock_key = MagicMock()
        mock_key.name = None
        mock_key.__str__ = lambda self: "q"
        mock_terminal.inkey.return_value = mock_key

        handler.process(timeout=0.01)

        assert len(callback_called) == 1

    def test_bind_named_key(self):
        """Test binding named keys like KEY_LEFT."""
        mock_terminal = MagicMock()
        handler = KeyboardHandler(mock_terminal)

        callback_called = []

        def callback():
            callback_called.append(True)

        handler.bind("KEY_LEFT", callback)

        # Simulate named key press
        mock_key = MagicMock()
        mock_key.name = "KEY_LEFT"
        mock_terminal.inkey.return_value = mock_key

        handler.process(timeout=0.01)

        assert len(callback_called) == 1

    def test_unbind(self):
        """Test unbinding a handler."""
        mock_terminal = MagicMock()
        handler = KeyboardHandler(mock_terminal)

        callback_called = []

        def callback():
            callback_called.append(True)

        handler.bind("q", callback)
        handler.unbind("q")

        # Simulate key press
        mock_key = MagicMock()
        mock_key.name = None
        mock_key.__str__ = lambda self: "q"
        mock_terminal.inkey.return_value = mock_key

        handler.process(timeout=0.01)

        # Callback should not be called after unbind
        assert len(callback_called) == 0


class TestPlaybackController:
    """Tests for PlaybackController class."""

    @pytest.fixture
    def mock_video(self):
        """Create a mock VideoStream."""
        video = MagicMock()
        video.fps = 30.0
        video.frame_count = 900  # 30 seconds at 30 FPS
        video.duration = 30.0  # 900 frames / 30 FPS = 30 seconds
        video._current_position = 0.0

        # Make current_position a property that returns the tracked position
        type(video).current_position = property(lambda self: self._current_position)

        # Mock seek_to to update the tracked position
        def mock_seek_to(position):
            video._current_position = max(0.0, min(position, video.duration))

        video.seek_to = mock_seek_to
        return video

    @pytest.fixture
    def controller(self, mock_video):
        """Create a PlaybackController with mock video."""
        config = AsciiPlayerConfig()
        return PlaybackController(mock_video, config)

    def test_initial_state(self, controller):
        """Test initial state is stopped."""
        assert controller.state == PlaybackState.STOPPED
        assert controller.speed == 1.0
        assert controller.current_time == 0.0

    def test_play_starts_playback(self, controller, mock_video):
        """Test play() starts playback."""
        controller.play()
        assert controller.state == PlaybackState.PLAYING
        mock_video.start.assert_called_once()

    def test_pause_pauses_playback(self, controller, mock_video):
        """Test pause() pauses playback."""
        controller.play()
        controller.pause()
        assert controller.state == PlaybackState.PAUSED
        mock_video.pause.assert_called_once()

    def test_toggle_toggles_state(self, controller, mock_video):
        """Test toggle() toggles between play and pause."""
        controller.toggle()
        assert controller.state == PlaybackState.PLAYING

        controller.toggle()
        assert controller.state == PlaybackState.PAUSED

        controller.toggle()
        assert controller.state == PlaybackState.PLAYING

    def test_stop_stops_playback(self, controller, mock_video):
        """Test stop() stops playback."""
        controller.play()
        controller.stop()
        assert controller.state == PlaybackState.STOPPED
        mock_video.stop.assert_called_once()

    def test_duration_calculation(self, controller):
        """Test duration is calculated correctly."""
        # 900 frames at 30 FPS = 30 seconds
        assert controller.duration == 30.0

    def test_seek_to(self, controller):
        """Test seeking to absolute position."""
        controller.play()
        controller.seek_to(10.0)

        # Position should be close to 10 seconds
        # (slight delay from perf_counter)
        assert 9.9 <= controller.current_time <= 10.1

    def test_seek_to_clamps_to_duration(self, controller):
        """Test seek_to clamps to valid range."""
        controller.play()

        # Seek beyond duration - allow small timing variance
        controller.seek_to(100.0)
        assert controller.current_time <= controller.duration + 0.1

        # Seek before start
        controller.seek_to(-10.0)
        assert controller.current_time >= 0.0

    def test_seek_relative(self, controller):
        """Test relative seeking."""
        controller.play()
        controller.seek_to(10.0)

        controller.seek_relative(5.0)
        assert 14.9 <= controller.current_time <= 15.1

        controller.seek_relative(-3.0)
        assert 11.9 <= controller.current_time <= 12.1

    def test_set_speed(self, controller):
        """Test setting playback speed."""
        controller.set_speed(2.0)
        assert controller.speed == 2.0

        controller.set_speed(0.5)
        assert controller.speed == 0.5

    def test_set_speed_clamps(self, controller):
        """Test speed is clamped to valid range."""
        controller.set_speed(100.0)
        assert controller.speed <= 8.0

        controller.set_speed(0.0)
        assert controller.speed >= 0.1

    def test_adjust_speed(self, controller):
        """Test adjusting speed steps through options."""
        # Start at 1.0
        assert controller.speed == 1.0

        controller.adjust_speed(0.25)
        assert controller.speed == 1.25

        controller.adjust_speed(-0.25)
        assert controller.speed == 1.0


class TestProgressBarRenderer:
    """Tests for ProgressBarRenderer class."""

    @pytest.fixture
    def renderer(self):
        """Create a ProgressBarRenderer."""
        config = AsciiPlayerConfig()
        return ProgressBarRenderer(terminal_width=80, config=config)

    def test_format_time_seconds(self, renderer):
        """Test time formatting for short durations."""
        assert renderer._format_time(0) == "00:00"
        assert renderer._format_time(65) == "01:05"
        assert renderer._format_time(599) == "09:59"

    def test_format_time_hours(self, renderer):
        """Test time formatting for long durations."""
        assert renderer._format_time(3600) == "1:00:00"
        assert renderer._format_time(3661) == "1:01:01"
        assert renderer._format_time(7200) == "2:00:00"

    def test_format_time_negative(self, renderer):
        """Test negative time is clamped to zero."""
        assert renderer._format_time(-10) == "00:00"

    def test_render_contains_state_icon(self, renderer):
        """Test rendered output contains state icon."""
        state = ProgressBarState(
            current_time=10.0,
            total_time=60.0,
            playback_state=PlaybackState.PLAYING,
        )
        output = renderer.render(state)

        # Should contain play icon
        assert "▶" in output

    def test_render_contains_time(self, renderer):
        """Test rendered output contains time."""
        state = ProgressBarState(
            current_time=65.0,  # 01:05
            total_time=600.0,  # 10:00
            playback_state=PlaybackState.PLAYING,
        )
        output = renderer.render(state)

        assert "01:05" in output
        assert "10:00" in output

    def test_render_contains_speed(self, renderer):
        """Test rendered output contains speed indicator."""
        state = ProgressBarState(
            current_time=10.0,
            total_time=60.0,
            playback_speed=2.0,
            playback_state=PlaybackState.PLAYING,
        )
        output = renderer.render(state)

        # Speed is formatted as "2.00x" or similar
        assert "2" in output and "x" in output

    def test_render_contains_mode(self, renderer):
        """Test rendered output contains render mode."""
        state = ProgressBarState(
            current_time=10.0,
            total_time=60.0,
            render_mode=RenderMode.HALF_BLOCK,
            playback_state=PlaybackState.PLAYING,
        )
        output = renderer.render(state)

        assert "HALF_BLOCK" in output

    def test_render_contains_fps(self, renderer):
        """Test rendered output contains FPS counter."""
        state = ProgressBarState(
            current_time=10.0,
            total_time=60.0,
            actual_fps=29.5,
            playback_state=PlaybackState.PLAYING,
        )
        output = renderer.render(state)

        assert "29.5" in output or "fps" in output.lower()

    def test_render_contains_progress_bar(self, renderer):
        """Test rendered output contains progress bar characters."""
        state = ProgressBarState(
            current_time=30.0,
            total_time=60.0,  # 50% progress
            playback_state=PlaybackState.PLAYING,
        )
        output = renderer.render(state)

        # Should contain progress bar characters
        assert "━" in output or "●" in output

    def test_render_seeking_mode(self, renderer):
        """Test rendered output in seeking mode."""
        state = ProgressBarState(
            current_time=30.0,
            total_time=60.0,
            cursor_position=0.75,  # Cursor at 75%
            is_seeking=True,
            playback_state=PlaybackState.SEEKING,
        )
        output = renderer.render(state)

        # Should contain seek cursor
        assert "●" in output

    def test_render_paused_icon(self, renderer):
        """Test pause icon is shown when paused."""
        state = ProgressBarState(
            current_time=10.0,
            total_time=60.0,
            playback_state=PlaybackState.PAUSED,
        )
        output = renderer.render(state)

        assert "⏸" in output

    def test_set_width(self, renderer):
        """Test set_width updates terminal width."""
        renderer.set_width(120)
        assert renderer.terminal_width == 120


class TestAsciiPlayer:
    """Tests for AsciiPlayer class."""

    def test_initialization(self, tmp_path):
        """Test player initialization."""
        video_path = tmp_path / "test.mp4"
        video_path.touch()  # Create empty file

        player = AsciiPlayer(video_path)

        assert player.video_path == video_path
        assert player.mode == RenderMode.HALF_BLOCK
        assert player.config is not None
        assert player.loop is True

    def test_custom_config(self, tmp_path):
        """Test player with custom config."""
        video_path = tmp_path / "test.mp4"
        video_path.touch()

        config = AsciiPlayerConfig(
            show_fps=False,
            enable_seek=False,
            default_speed=0.5,
        )

        player = AsciiPlayer(
            video_path,
            mode=RenderMode.BRAILLE,
            config=config,
            loop=False,
        )

        assert player.mode == RenderMode.BRAILLE
        assert player.config.show_fps is False
        assert player.loop is False

    def test_mode_switching(self, tmp_path):
        """Test _on_mode_switch cycles through modes."""
        video_path = tmp_path / "test.mp4"
        video_path.touch()

        player = AsciiPlayer(video_path, mode=RenderMode.BLOCK)

        # Simulate mode switch
        player._on_mode_switch()
        assert player.mode == RenderMode.HALF_BLOCK

        player._on_mode_switch()
        assert player.mode == RenderMode.ASCII

    def test_seek_mode_enter_and_confirm(self, tmp_path):
        """Test entering and confirming seek mode."""
        video_path = tmp_path / "test.mp4"
        video_path.touch()

        player = AsciiPlayer(video_path)

        # Mock controller
        mock_controller = MagicMock()
        mock_controller.current_time = 10.0
        mock_controller.duration = 100.0
        player._controller = mock_controller

        # Enter seek mode
        player._enter_seek_mode()
        assert player._seek_mode is True
        assert player._seek_cursor == 0.1  # 10/100

        # Move cursor
        player._seek_cursor = 0.5

        # Confirm seek
        player._confirm_seek()
        assert player._seek_mode is False
        mock_controller.seek_to.assert_called_with(50.0)  # 0.5 * 100

    def test_seek_mode_cancel(self, tmp_path):
        """Test canceling seek mode."""
        video_path = tmp_path / "test.mp4"
        video_path.touch()

        player = AsciiPlayer(video_path)

        # Mock controller
        mock_controller = MagicMock()
        mock_controller.current_time = 10.0
        mock_controller.duration = 100.0
        player._controller = mock_controller

        # Enter seek mode
        player._enter_seek_mode()

        # Move cursor
        player._seek_cursor = 0.9

        # Cancel seek
        player._cancel_seek()
        assert player._seek_mode is False
        # Should restore original position
        mock_controller.seek_to.assert_called_with(10.0)


class TestProgressBarStateDefaults:
    """Test ProgressBarState dataclass defaults."""

    def test_defaults(self):
        """Test ProgressBarState has correct defaults."""
        state = ProgressBarState()

        assert state.current_time == 0.0
        assert state.total_time == 0.0
        assert state.cursor_position is None
        assert state.is_seeking is False
        assert state.playback_speed == 1.0
        assert state.render_mode == RenderMode.HALF_BLOCK
        assert state.actual_fps == 0.0
        assert state.playback_state == PlaybackState.STOPPED
