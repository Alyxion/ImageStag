#!/usr/bin/env python3
"""
ASCII Video Player CLI - Watch videos in glorious colored ASCII art!

A command-line tool for playing videos as ASCII art in the terminal.

Usage:
    python -m imagestag.tools.ascii_player_cli [video_path] [--mode MODE]

    MODE can be: block, half_block, ascii, ascii_color, braille
    Default: half_block (best quality)

Examples:
    # Play a video in half-block mode
    python -m imagestag.tools.ascii_player_cli video.mp4

    # Play in braille mode (highest resolution)
    python -m imagestag.tools.ascii_player_cli video.mp4 --mode braille

    # Play with minimal UI
    python -m imagestag.tools.ascii_player_cli video.mp4 --minimal

    # Show demo of all rendering modes
    python -m imagestag.tools.ascii_player_cli --demo

Requirements:
    - A terminal that supports true color (24-bit) ANSI codes
    - Recommended: iTerm2, Windows Terminal, Kitty, or modern Linux terminals

Controls:
    Space       - Play/Pause toggle
    Q / Escape  - Stop and exit
    Left/Right  - Enter seek mode, move cursor
    Enter       - Confirm seek position
    Home/End    - Jump to start/end
    +/-         - Speed control
    M           - Cycle through render modes
    H / ?       - Show help
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

from imagestag import Image
from imagestag.components.ascii import AsciiRenderer, AsciiPlayer, AsciiPlayerConfig, RenderMode
from imagestag.components.stream_view import VideoStream


# ANSI escape codes for demo mode
ESC = "\033"
CLEAR_SCREEN = f"{ESC}[2J"
RESET = f"{ESC}[0m"


def demo_modes(video_path: str | None = None, image_path: str | None = None):
    """Show all rendering modes side by side."""
    img = None

    if image_path:
        img = Image.load(image_path)
    elif video_path:
        # Use first frame from video
        path = Path(video_path)
        if not path.exists():
            print(f"Video not found: {video_path}")
            return
        video = VideoStream(str(path))
        video.start()
        time.sleep(0.5)
        img = video.get_frame()
        video.stop()
        if img is None:
            print("Could not get frame from video")
            return
    else:
        print("Please provide a video or image path for the demo")
        return

    print(f"\n{ESC}[1mASCII Rendering Modes Demo{RESET}\n")

    modes = [
        (RenderMode.BLOCK, "BLOCK - Full block characters"),
        (RenderMode.HALF_BLOCK, "HALF_BLOCK - 2x vertical resolution (recommended)"),
        (RenderMode.ASCII_COLOR, "ASCII_COLOR - Colored ASCII characters"),
        (RenderMode.ASCII, "ASCII - Classic monochrome ASCII"),
        (RenderMode.BRAILLE, "BRAILLE - Highest resolution (needs good font)"),
    ]

    for mode, description in modes:
        print(f"\n{ESC}[1;33m{description}{RESET}\n")
        renderer = AsciiRenderer(width=60, mode=mode)
        print(renderer.render(img))
        print()
        input("Press Enter for next mode...")
        print(CLEAR_SCREEN, end="")


def main(args: list[str] | None = None):
    """Main entry point for the ASCII video player CLI."""
    parser = argparse.ArgumentParser(
        description="ASCII Video Player - Watch videos in colored ASCII art!",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Rendering Modes:
  block       - Full block characters with color
  half_block  - Half blocks for 2x vertical resolution (default, best quality)
  ascii       - Classic ASCII characters based on brightness
  ascii_color - Colored ASCII characters
  braille     - Braille dots for highest resolution (requires compatible font)

Controls:
  Space       - Play/Pause toggle
  Q / Escape  - Stop and exit
  Left/Right  - Enter seek mode, move cursor
  Enter       - Confirm seek position
  Home/End    - Jump to start/end
  +/-         - Speed control
  M           - Cycle through render modes
  H / ?       - Show help

Examples:
  ascii-player video.mp4                # Play a video
  ascii-player video.mp4 --mode braille # Use braille mode
  ascii-player --demo video.mp4         # Show all modes
  ascii-player video.mp4 --minimal      # Minimal UI (no frame)
  ascii-player video.mp4 --scale 0.67   # Use 2/3 of terminal
        """,
    )
    parser.add_argument(
        "video",
        nargs="?",
        help="Path to video file",
    )
    parser.add_argument(
        "--mode",
        "-m",
        choices=["block", "half_block", "ascii", "ascii_color", "braille"],
        default="half_block",
        help="Rendering mode (default: half_block)",
    )
    parser.add_argument(
        "--fps",
        "-f",
        type=float,
        default=None,
        help="Target FPS (default: video's native FPS, max 30)",
    )
    parser.add_argument(
        "--demo",
        "-d",
        action="store_true",
        help="Show demo of all rendering modes",
    )
    parser.add_argument(
        "--aspect",
        "-a",
        type=float,
        default=0.45,
        help="Terminal char aspect ratio (width/height, default: 0.45)",
    )
    parser.add_argument(
        "--scale",
        "-s",
        type=float,
        default=1.0,
        help="Video scale 0.0-1.0 (default: 1.0 = full terminal)",
    )
    parser.add_argument(
        "--minimal",
        action="store_true",
        help="Minimal UI (no decorative frame)",
    )
    parser.add_argument(
        "--no-loop",
        action="store_true",
        help="Don't loop the video",
    )

    parsed_args = parser.parse_args(args)

    # Map mode string to enum
    mode_map = {
        "block": RenderMode.BLOCK,
        "half_block": RenderMode.HALF_BLOCK,
        "ascii": RenderMode.ASCII,
        "ascii_color": RenderMode.ASCII_COLOR,
        "braille": RenderMode.BRAILLE,
    }

    if parsed_args.demo:
        demo_modes(video_path=parsed_args.video)
    elif parsed_args.video:
        # Configure player
        config = AsciiPlayerConfig(
            show_progress_bar=True,
            show_time=True,
            show_mode=True,
            show_speed=True,
            show_fps=True,
            show_frame=not parsed_args.minimal,
            enable_seek=True,
            enable_speed_control=True,
            enable_mode_switch=True,
            video_scale=parsed_args.scale,
        )

        # Create and run player
        player = AsciiPlayer(
            parsed_args.video,
            mode=mode_map[parsed_args.mode],
            config=config,
            char_aspect=parsed_args.aspect,
            target_fps=parsed_args.fps,
            loop=not parsed_args.no_loop,
        )
        player.play()
    else:
        parser.print_help()
        print("\nError: Please provide a video file path")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
