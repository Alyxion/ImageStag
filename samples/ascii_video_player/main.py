#!/usr/bin/env python3
"""
ASCII Video Player - Watch videos in glorious colored ASCII art!

This sample demonstrates the AsciiPlayer component for terminal-based video playback.

Usage:
    python samples/ascii_video_player/main.py [video_path] [--mode MODE]

    MODE can be: block, half_block, ascii, ascii_color, braille
    Default: half_block (best quality)

Examples:
    # Play Big Buck Bunny in half-block mode
    python samples/ascii_video_player/main.py

    # Play custom video in braille mode (highest resolution)
    python samples/ascii_video_player/main.py my_video.mp4 --mode braille

    # Play with minimal UI
    python samples/ascii_video_player/main.py --minimal

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
"""

import argparse
import sys
import time
from pathlib import Path

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from imagestag import Image
from imagestag.components.ascii import AsciiRenderer, RenderMode, AsciiPlayer, AsciiPlayerConfig
from imagestag.components.stream_view import VideoStream

# Default video path
DEFAULT_VIDEO = PROJECT_ROOT / "tmp" / "media" / "big_buck_bunny_1080p_h264.mov"

# ANSI escape codes for demo mode
ESC = "\033"
CLEAR_SCREEN = f"{ESC}[2J"
RESET = f"{ESC}[0m"


def demo_modes(image_path: str | None = None):
    """Show all rendering modes side by side."""
    if image_path is None:
        # Use first frame from video
        video_path = DEFAULT_VIDEO
        if not video_path.exists():
            print("Video not found. Run: python scripts/download_test_media.py")
            return
        video = VideoStream(str(video_path))
        video.start()
        time.sleep(0.5)
        img = video.get_frame()
        video.stop()
        if img is None:
            print("Could not get frame from video")
            return
    else:
        img = Image.load(image_path)

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


def main():
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

Examples:
  python main.py                          # Play default video
  python main.py video.mp4                # Play custom video
  python main.py --mode braille           # Use braille mode
  python main.py --demo                   # Show all modes
  python main.py --minimal                # Minimal UI (no frame)
        """,
    )
    parser.add_argument(
        "video",
        nargs="?",
        default=str(DEFAULT_VIDEO),
        help="Path to video file (default: Big Buck Bunny)",
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
        "--minimal",
        action="store_true",
        help="Minimal UI (no decorative frame)",
    )
    parser.add_argument(
        "--no-loop",
        action="store_true",
        help="Don't loop the video",
    )

    args = parser.parse_args()

    # Map mode string to enum
    mode_map = {
        "block": RenderMode.BLOCK,
        "half_block": RenderMode.HALF_BLOCK,
        "ascii": RenderMode.ASCII,
        "ascii_color": RenderMode.ASCII_COLOR,
        "braille": RenderMode.BRAILLE,
    }

    if args.demo:
        demo_modes(args.video if args.video != str(DEFAULT_VIDEO) else None)
    else:
        # Configure player
        config = AsciiPlayerConfig(
            show_progress_bar=True,
            show_time=True,
            show_mode=True,
            show_speed=True,
            show_fps=True,
            show_frame=not args.minimal,
            enable_seek=True,
            enable_speed_control=True,
            enable_mode_switch=True,
        )

        # Create and run player
        player = AsciiPlayer(
            args.video,
            mode=mode_map[args.mode],
            config=config,
            char_aspect=args.aspect,
            target_fps=args.fps,
            loop=not args.no_loop,
        )
        player.play()


if __name__ == "__main__":
    main()
