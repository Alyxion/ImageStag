#!/usr/bin/env python3
"""
Terminal Video Player - Watch videos in glorious colored ASCII art!

This sample demonstrates the TerminalPlayer and TerminalMultiPlayer components
for terminal-based video playback.

Usage:
    # Single player (default)
    python samples/ascii_video_player/main.py [video_path]

    # Multi-player layouts
    python samples/ascii_video_player/main.py --layout 2x2 video1.mp4 video2.mp4 video3.mp4 video4.mp4
    python samples/ascii_video_player/main.py --layout 1x2 left.mp4 right.mp4

Examples:
    # Play Big Buck Bunny
    python samples/ascii_video_player/main.py

    # Side-by-side comparison
    python samples/ascii_video_player/main.py --layout 1x2 video1.mp4 video2.mp4

    # 2x2 grid with labels
    python samples/ascii_video_player/main.py --layout 2x2 --labels "Cam 1,Cam 2,Cam 3,Cam 4" v1.mp4 v2.mp4 v3.mp4 v4.mp4

    # Demo all rendering modes
    python samples/ascii_video_player/main.py --demo

Controls (Single Player):
    Space       - Play/Pause toggle
    Q / Escape  - Stop and exit
    Left/Right  - Enter seek mode, move cursor
    Enter       - Confirm seek position
    +/-         - Speed control
    M           - Cycle through render modes
    H / ?       - Show help

Controls (Multi-Player):
    Space       - Play/Pause all (or focused)
    Q / Escape  - Stop and exit
    +/-         - Speed control
    M           - Cycle render modes
    1-9         - Focus specific player
    0           - Control all players
"""

import argparse
import sys
import time
from pathlib import Path

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from imagestag import Image
from imagestag.components.ascii import (
    AsciiRenderer,
    RenderMode,
    TerminalPlayer,
    TerminalPlayerConfig,
    TerminalMultiPlayer,
    PlayerSlot,
)
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
        description="Terminal Video Player - Watch videos in colored ASCII art!",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Rendering Modes:
  block       - Full block characters with color
  half_block  - Half blocks for 2x vertical resolution (default, best quality)
  ascii       - Classic ASCII characters based on brightness
  ascii_color - Colored ASCII characters
  braille     - Braille dots for highest resolution (requires compatible font)

Layouts (for multi-player):
  1x1  - Single player
  1x2  - Two players side by side
  2x1  - Two players stacked vertically
  2x2  - Four players in a grid
  2x3  - Six players (2 rows, 3 cols)
  3x2  - Six players (3 rows, 2 cols)
  auto - Automatically determine from video count

Examples:
  python main.py                              # Play default video
  python main.py video.mp4                    # Play custom video
  python main.py --mode braille video.mp4     # Use braille mode
  python main.py --demo                       # Show all modes
  python main.py --layout 1x2 a.mp4 b.mp4     # Side-by-side
  python main.py --layout 2x2 a.mp4 b.mp4 c.mp4 d.mp4  # 2x2 grid
        """,
    )
    parser.add_argument(
        "videos",
        nargs="*",
        help="Path to video file(s). Multiple videos enable multi-player mode.",
    )
    parser.add_argument(
        "--mode",
        "-m",
        choices=["block", "half_block", "ascii", "ascii_color", "braille"],
        default="half_block",
        help="Rendering mode (default: half_block)",
    )
    parser.add_argument(
        "--layout",
        "-l",
        default="auto",
        help="Multi-player layout: 1x2, 2x1, 2x2, 3x2, auto (default: auto)",
    )
    parser.add_argument(
        "--labels",
        help="Comma-separated labels for multi-player (e.g., 'Cam 1,Cam 2')",
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
        help="Minimal UI (no decorative frame) - single player only",
    )
    parser.add_argument(
        "--no-loop",
        action="store_true",
        help="Don't loop the video(s)",
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
    mode = mode_map[args.mode]

    if args.demo:
        # Demo mode
        video = args.videos[0] if args.videos else None
        demo_modes(video if video and Path(video).exists() else None)

    elif len(args.videos) == 0:
        # No videos specified, use default
        if not DEFAULT_VIDEO.exists():
            print(f"Default video not found: {DEFAULT_VIDEO}")
            print("Run: python scripts/download_test_media.py")
            print("\nOr specify a video: python main.py <video_path>")
            return 1

        # Single player with default video
        config = TerminalPlayerConfig(
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
        player = TerminalPlayer(
            str(DEFAULT_VIDEO),
            mode=mode,
            config=config,
            char_aspect=args.aspect,
            target_fps=args.fps,
            loop=not args.no_loop,
        )
        player.play()

    elif len(args.videos) == 1:
        # Single player
        config = TerminalPlayerConfig(
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
        player = TerminalPlayer(
            args.videos[0],
            mode=mode,
            config=config,
            char_aspect=args.aspect,
            target_fps=args.fps,
            loop=not args.no_loop,
        )
        player.play()

    else:
        # Multi-player mode
        labels = args.labels.split(",") if args.labels else []

        # Create player slots
        slots = []
        for i, video_path in enumerate(args.videos):
            label = labels[i] if i < len(labels) else ""
            slots.append(PlayerSlot(video_path=video_path, mode=mode, label=label))

        # Create and run multi-player
        multi = TerminalMultiPlayer(
            slots,
            layout=args.layout,
            mode=mode,
            char_aspect=args.aspect,
            loop=not args.no_loop,
        )
        multi.play()

    return 0


if __name__ == "__main__":
    exit(main())
