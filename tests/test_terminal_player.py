"""Tests for terminal player and ASCII components."""

import pytest
from unittest.mock import MagicMock, patch
import numpy as np
from pathlib import Path

from imagestag import Image


class TestAsciiRendererModes:
    """Tests for AsciiRenderer render modes."""

    @pytest.fixture
    def test_image(self):
        """Create a test image."""
        arr = np.zeros((100, 100, 3), dtype=np.uint8)
        for y in range(100):
            for x in range(100):
                arr[y, x, 0] = int(255 * x / 100)
                arr[y, x, 1] = int(255 * y / 100)
                arr[y, x, 2] = 128
        return Image.from_array(arr)

    def test_block_mode(self, test_image):
        """Test BLOCK render mode."""
        from imagestag.components.ascii.renderer import AsciiRenderer, RenderMode

        renderer = AsciiRenderer(width=20, mode=RenderMode.BLOCK)
        output = renderer.render(test_image)

        assert output is not None
        assert len(output) > 0
        assert "\033[" in output

    def test_half_block_mode(self, test_image):
        """Test HALF_BLOCK render mode."""
        from imagestag.components.ascii.renderer import AsciiRenderer, RenderMode

        renderer = AsciiRenderer(width=20, mode=RenderMode.HALF_BLOCK)
        output = renderer.render(test_image)

        assert output is not None
        assert "▀" in output or "▄" in output

    def test_ascii_mode(self, test_image):
        """Test ASCII render mode."""
        from imagestag.components.ascii.renderer import AsciiRenderer, RenderMode

        renderer = AsciiRenderer(width=20, mode=RenderMode.ASCII)
        output = renderer.render(test_image)

        assert output is not None

    def test_ascii_color_mode(self, test_image):
        """Test ASCII_COLOR render mode."""
        from imagestag.components.ascii.renderer import AsciiRenderer, RenderMode

        renderer = AsciiRenderer(width=20, mode=RenderMode.ASCII_COLOR)
        output = renderer.render(test_image)

        assert output is not None
        assert "\033[" in output

    def test_braille_mode(self, test_image):
        """Test BRAILLE render mode."""
        from imagestag.components.ascii.renderer import AsciiRenderer, RenderMode

        renderer = AsciiRenderer(width=20, mode=RenderMode.BRAILLE)
        output = renderer.render(test_image)

        assert output is not None

    def test_ascii_edge_mode(self, test_image):
        """Test ASCII_EDGE render mode."""
        from imagestag.components.ascii.renderer import AsciiRenderer, RenderMode

        renderer = AsciiRenderer(width=40, mode=RenderMode.ASCII_EDGE)
        output = renderer.render(test_image)

        assert output is not None
        assert any(c in output for c in "|-/\\=")

    def test_grayscale_image(self):
        """Test rendering grayscale image."""
        from imagestag.components.ascii.renderer import AsciiRenderer, RenderMode

        arr = np.linspace(0, 255, 100 * 100, dtype=np.uint8).reshape(100, 100)
        img = Image.from_array(arr)

        renderer = AsciiRenderer(width=20, mode=RenderMode.HALF_BLOCK)
        output = renderer.render(img)

        assert output is not None

    def test_rgba_image(self):
        """Test rendering RGBA image."""
        from imagestag.components.ascii.renderer import AsciiRenderer, RenderMode

        arr = np.zeros((100, 100, 4), dtype=np.uint8)
        arr[:, :, 0] = 255
        arr[:, :, 3] = 200
        img = Image.from_array(arr)

        renderer = AsciiRenderer(width=20, mode=RenderMode.HALF_BLOCK)
        output = renderer.render(img)

        assert output is not None


class TestRenderFrameToTerminal:
    """Tests for render_frame_to_terminal function."""

    def test_render_frame_to_terminal(self):
        """Test rendering frame to terminal."""
        from imagestag.components.ascii.renderer import render_frame_to_terminal, RenderMode

        arr = np.zeros((100, 100, 3), dtype=np.uint8)
        arr[:, :, 1] = 128
        img = Image.from_array(arr)

        with patch("sys.stdout") as mock_stdout:
            render_frame_to_terminal(img, width=20, mode=RenderMode.BLOCK, clear=False)
            mock_stdout.write.assert_called()


class TestTerminalPlayerClasses:
    """Tests for TerminalPlayer classes."""

    def test_playback_state_enum(self):
        """Test PlaybackState enum."""
        from imagestag.components.ascii.terminal_player import PlaybackState

        assert PlaybackState.STOPPED.value == "stopped"
        assert PlaybackState.PLAYING.value == "playing"
        assert PlaybackState.PAUSED.value == "paused"
        assert PlaybackState.SEEKING.value == "seeking"

    def test_terminal_player_config(self):
        """Test TerminalPlayerConfig defaults."""
        from imagestag.components.ascii.terminal_player import TerminalPlayerConfig

        config = TerminalPlayerConfig()

        assert config.show_progress_bar is True
        assert config.show_time is True
        assert config.show_fps is True
        assert config.enable_seek is True
        assert config.default_speed == 1.0
        assert config.seek_step == 5.0

    def test_terminal_player_config_custom(self):
        """Test TerminalPlayerConfig with custom values."""
        from imagestag.components.ascii.terminal_player import TerminalPlayerConfig

        config = TerminalPlayerConfig(
            show_fps=False,
            enable_seek=False,
            default_speed=1.5,
            seek_step=10.0,
        )

        assert config.show_fps is False
        assert config.enable_seek is False
        assert config.default_speed == 1.5
        assert config.seek_step == 10.0

    def test_progress_bar_state(self):
        """Test ProgressBarState creation."""
        from imagestag.components.ascii.terminal_player import ProgressBarState, PlaybackState

        state = ProgressBarState(
            current_time=30.0,
            total_time=60.0,
            playback_state=PlaybackState.PLAYING,
        )

        assert state.current_time == 30.0
        assert state.total_time == 60.0
        assert state.playback_state == PlaybackState.PLAYING

    def test_keyboard_handler_creation(self):
        """Test KeyboardHandler creation."""
        from imagestag.components.ascii.terminal_player import KeyboardHandler

        mock_terminal = MagicMock()
        handler = KeyboardHandler(mock_terminal)

        assert handler is not None


class TestProgressBarRenderer:
    """Tests for ProgressBarRenderer."""

    def test_format_time(self):
        """Test time formatting."""
        from imagestag.components.ascii.terminal_player import ProgressBarRenderer, TerminalPlayerConfig

        config = TerminalPlayerConfig()
        renderer = ProgressBarRenderer(terminal_width=80, config=config)

        assert renderer._format_time(0) == "00:00"
        assert renderer._format_time(65) == "01:05"
        assert renderer._format_time(3600) == "1:00:00"
        assert renderer._format_time(-5) == "00:00"

    def test_render_progress_bar(self):
        """Test rendering progress bar."""
        from imagestag.components.ascii.terminal_player import (
            ProgressBarRenderer,
            ProgressBarState,
            PlaybackState,
            TerminalPlayerConfig,
        )

        config = TerminalPlayerConfig()
        renderer = ProgressBarRenderer(terminal_width=80, config=config)

        state = ProgressBarState(
            current_time=30.0,
            total_time=60.0,
            playback_state=PlaybackState.PLAYING,
        )

        output = renderer.render(state)

        assert output is not None
        assert "00:30" in output
        assert "01:00" in output


class TestTerminalPlayer:
    """Tests for TerminalPlayer class."""

    @pytest.fixture
    def mock_video_file(self, tmp_path):
        """Create a mock video file path."""
        video_path = tmp_path / "test_video.mp4"
        video_path.touch()
        return video_path

    def test_terminal_player_initialization_with_path(self, mock_video_file):
        """Test TerminalPlayer initialization with path."""
        from imagestag.components.ascii.terminal_player import TerminalPlayer
        from imagestag.components.ascii.renderer import RenderMode

        player = TerminalPlayer(mock_video_file, mode=RenderMode.HALF_BLOCK)

        assert player.video_path == mock_video_file
        assert player.mode == RenderMode.HALF_BLOCK

    def test_terminal_player_initialization_with_stream(self):
        """Test TerminalPlayer initialization with ImageStream."""
        from imagestag.components.ascii.terminal_player import TerminalPlayer
        from imagestag.components.ascii.renderer import RenderMode
        from imagestag.streams.generator import GeneratorStream

        def create_frame(t):
            return Image.from_array(np.zeros((100, 100, 3), dtype=np.uint8))

        stream = GeneratorStream(handler=create_frame)
        player = TerminalPlayer(stream, mode=RenderMode.BLOCK, title="Test Stream")

        assert player._stream is stream

    def test_terminal_player_mode_switching(self, mock_video_file):
        """Test mode switching in TerminalPlayer."""
        from imagestag.components.ascii.terminal_player import TerminalPlayer
        from imagestag.components.ascii.renderer import RenderMode

        player = TerminalPlayer(mock_video_file, mode=RenderMode.BLOCK)

        assert player.mode == RenderMode.BLOCK

        player._on_mode_switch()
        assert player.mode == RenderMode.HALF_BLOCK

        player._on_mode_switch()
        assert player.mode == RenderMode.ASCII
