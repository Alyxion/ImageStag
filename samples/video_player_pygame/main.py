#!/usr/bin/env python3
"""Video Player - Pygame Backend.

Full-featured video player with seeking, speed control, and progress bar.
Uses the shared PlaybackController for all backends.

Usage:
    poetry run python samples/video_player_pygame/main.py [video_path]

Controls:
    Space       - Play/Pause toggle
    Q / Escape  - Stop and exit
    Left/Right  - Seek backward/forward 5 seconds
    Shift+Left/Right - Fine seek 1 second
    Home/End    - Jump to start/end
    +/-         - Speed up/down
    H           - Toggle help overlay
    F           - Toggle fullscreen
    Click       - Seek to position on progress bar
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Default video path
DEFAULT_VIDEO = PROJECT_ROOT / "tmp" / "media" / "big_buck_bunny_1080p_h264.mov"

# Help overlay text
HELP_TEXT = """
  VIDEO PLAYER CONTROLS

  PLAYBACK
    Space         Play / Pause
    Q / Escape    Stop and exit

  SEEKING
    Left / Right  Seek 5 seconds
    Shift+Arrows  Fine seek 1 second
    Home / End    Jump to start / end
    Click bar     Seek to position

  SPEED
    + / =         Speed up
    - / _         Speed down

  VIEW
    F             Toggle fullscreen
    H / ?         Toggle this help

  Press any key to close help
"""


def main():
    parser = argparse.ArgumentParser(
        description="Video Player - Pygame Backend",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "video",
        nargs="?",
        default=str(DEFAULT_VIDEO),
        help="Path to video file (default: Big Buck Bunny)",
    )
    parser.add_argument("--width", "-W", type=int, default=1280, help="Window width")
    parser.add_argument("--height", "-H", type=int, default=720, help="Window height")
    parser.add_argument("--no-loop", action="store_true", help="Don't loop video")

    args = parser.parse_args()

    # Check video exists
    video_path = Path(args.video)
    if not video_path.exists():
        print(f"Error: Video not found: {video_path}")
        print("Run: python scripts/download_test_media.py")
        sys.exit(1)

    # Import pygame
    try:
        import pygame
    except ImportError:
        print("Error: pygame is required. Install with: poetry add pygame")
        sys.exit(1)

    from imagestag.streams import VideoStream
    from imagestag.components.shared import (
        PlaybackController,
        PlaybackConfig,
        PlaybackState,
        format_time,
    )

    # Initialize pygame
    pygame.init()
    pygame.display.set_caption(f"Video Player - {video_path.name}")

    # Create window
    screen = pygame.display.set_mode((args.width, args.height), pygame.RESIZABLE)
    clock = pygame.time.Clock()

    # Create video and controller
    video = VideoStream(str(video_path), loop=not args.no_loop)
    config = PlaybackConfig(
        seek_step=5.0,
        fine_seek_step=1.0,
    )
    controller = PlaybackController(video, config)

    # UI state
    show_help = False
    show_controls = True
    controls_timer = 0.0
    controls_fade_delay = 3.0  # Hide controls after 3 seconds of no activity
    fullscreen = False
    windowed_size = (args.width, args.height)

    # Progress bar dimensions
    bar_height = 50
    bar_margin = 20

    # Fonts
    try:
        font = pygame.font.SysFont("Helvetica", 16)
        font_large = pygame.font.SysFont("Helvetica", 24)
        font_help = pygame.font.SysFont("Courier", 14)
    except Exception:
        font = pygame.font.Font(None, 20)
        font_large = pygame.font.Font(None, 32)
        font_help = pygame.font.Font(None, 18)

    # Colors
    BG_COLOR = (20, 20, 25)
    BAR_BG = (40, 40, 45)
    BAR_FILL = (80, 180, 100)
    BAR_EMPTY = (60, 60, 65)
    CURSOR_COLOR = (255, 200, 80)
    TEXT_COLOR = (220, 220, 225)
    TEXT_DIM = (140, 140, 145)
    HELP_BG = (30, 30, 40, 230)

    def render_progress_bar(surface, controller, y, width, height):
        """Render progress bar at bottom of screen."""
        state = controller.get_progress_state()

        # Background
        bar_rect = pygame.Rect(0, y, width, height)
        pygame.draw.rect(surface, BAR_BG, bar_rect)

        # Calculate layout
        margin = bar_margin
        bar_y = y + height // 2 - 3
        bar_h = 6

        # Status icon
        icons = {
            PlaybackState.PLAYING: "\u25B6",
            PlaybackState.PAUSED: "\u23F8",
            PlaybackState.STOPPED: "\u23F9",
        }
        icon = icons.get(state.playback_state, "?")

        # Left: icon + current time
        left_text = f"{icon}  {format_time(state.current_time)}"
        left_surface = font.render(left_text, True, TEXT_COLOR)
        surface.blit(left_surface, (margin, y + height // 2 - left_surface.get_height() // 2))

        # Right: speed + fps + duration
        parts = []
        if state.playback_speed != 1.0:
            parts.append(f"{state.playback_speed:.1f}x")
        if state.actual_fps > 0:
            parts.append(f"{state.actual_fps:.0f}fps")
        parts.append(format_time(state.total_time))
        right_text = "  |  ".join(parts)
        right_surface = font.render(right_text, True, TEXT_DIM)
        surface.blit(right_surface, (width - margin - right_surface.get_width(), y + height // 2 - right_surface.get_height() // 2))

        # Progress bar
        bar_left = margin + left_surface.get_width() + margin
        bar_right = width - margin - right_surface.get_width() - margin
        bar_width = bar_right - bar_left

        if bar_width > 50:
            # Empty bar
            pygame.draw.rect(surface, BAR_EMPTY, (bar_left, bar_y, bar_width, bar_h))

            # Fill
            if state.total_time > 0:
                progress = state.current_time / state.total_time
                progress = max(0.0, min(1.0, progress))
                fill_width = int(bar_width * progress)

                if fill_width > 0:
                    pygame.draw.rect(surface, BAR_FILL, (bar_left, bar_y, fill_width, bar_h))

                # Cursor
                cursor_x = bar_left + fill_width
                pygame.draw.circle(surface, CURSOR_COLOR, (cursor_x, bar_y + bar_h // 2), 8)

        return bar_left, bar_right, y, y + height

    def render_help_overlay(surface, width, height):
        """Render help overlay."""
        # Semi-transparent background
        overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        overlay.fill((20, 20, 30, 220))
        surface.blit(overlay, (0, 0))

        # Help text
        lines = HELP_TEXT.strip().split("\n")
        start_y = height // 2 - len(lines) * 10

        for i, line in enumerate(lines):
            text_surface = font_help.render(line, True, TEXT_COLOR)
            x = width // 2 - text_surface.get_width() // 2
            surface.blit(text_surface, (x, start_y + i * 20))

    def handle_bar_click(x, bar_left, bar_right):
        """Handle click on progress bar."""
        if bar_left <= x <= bar_right:
            progress = (x - bar_left) / (bar_right - bar_left)
            controller.seek_to(progress * controller.duration)

    # Start playback
    controller.play()
    running = True
    bar_bounds = (0, 0, 0, 0)  # (left, right, top, bottom)

    while running:
        dt = clock.tick(60) / 1000.0
        controls_timer += dt

        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                controls_timer = 0  # Reset controls visibility timer

                if show_help:
                    # Any key closes help
                    show_help = False
                    continue

                key = event.key
                mods = pygame.key.get_mods()
                shift = mods & pygame.KMOD_SHIFT

                if key == pygame.K_ESCAPE or key == pygame.K_q:
                    running = False

                elif key == pygame.K_SPACE:
                    controller.toggle()

                elif key == pygame.K_LEFT:
                    if shift:
                        controller.seek_relative(-config.fine_seek_step)
                    else:
                        controller.seek_backward()

                elif key == pygame.K_RIGHT:
                    if shift:
                        controller.seek_relative(config.fine_seek_step)
                    else:
                        controller.seek_forward()

                elif key == pygame.K_HOME:
                    controller.seek_to_start()

                elif key == pygame.K_END:
                    controller.seek_to_end()

                elif key in (pygame.K_PLUS, pygame.K_EQUALS):
                    controller.speed_up()

                elif key == pygame.K_MINUS:
                    controller.speed_down()

                elif key == pygame.K_h or key == pygame.K_QUESTION:
                    show_help = not show_help

                elif key == pygame.K_f:
                    fullscreen = not fullscreen
                    if fullscreen:
                        windowed_size = screen.get_size()
                        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
                    else:
                        screen = pygame.display.set_mode(windowed_size, pygame.RESIZABLE)

            elif event.type == pygame.MOUSEBUTTONDOWN:
                controls_timer = 0
                if event.button == 1:  # Left click
                    bar_left, bar_right, bar_top, bar_bottom = bar_bounds
                    if bar_top <= event.pos[1] <= bar_bottom:
                        handle_bar_click(event.pos[0], bar_left, bar_right)

            elif event.type == pygame.MOUSEMOTION:
                controls_timer = 0

            elif event.type == pygame.VIDEORESIZE:
                if not fullscreen:
                    screen = pygame.display.set_mode(event.size, pygame.RESIZABLE)

        # Get current frame
        frame, _ = controller.get_frame()
        width, height = screen.get_size()

        # Clear screen
        screen.fill(BG_COLOR)

        # Draw video frame
        if frame is not None:
            controller.update_fps()

            # Convert to pygame surface
            pixels = frame.get_pixels()
            if pixels.shape[2] == 4:
                pixels = pixels[:, :, :3]

            # Scale to fit (maintaining aspect ratio)
            video_height = height - bar_height if show_controls or controls_timer < controls_fade_delay else height
            scale_w = width / frame.width
            scale_h = video_height / frame.height
            scale = min(scale_w, scale_h)

            new_w = int(frame.width * scale)
            new_h = int(frame.height * scale)

            # Create pygame surface from numpy array
            surface = pygame.surfarray.make_surface(pixels.swapaxes(0, 1))
            surface = pygame.transform.smoothscale(surface, (new_w, new_h))

            # Center
            x = (width - new_w) // 2
            y = (video_height - new_h) // 2
            screen.blit(surface, (x, y))

        # Draw progress bar (with fade)
        if show_controls or controls_timer < controls_fade_delay:
            bar_bounds = render_progress_bar(screen, controller, height - bar_height, width, bar_height)

        # Draw help overlay
        if show_help:
            render_help_overlay(screen, width, height)

        pygame.display.flip()

    # Cleanup
    controller.stop()
    pygame.quit()


if __name__ == "__main__":
    main()
