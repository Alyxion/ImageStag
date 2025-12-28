#!/usr/bin/env python3
"""StreamView Pygame Demo - Native desktop video player.

This sample demonstrates the StreamViewPygame component for native desktop
video playback using pygame.

Usage:
    # Install pygame first
    poetry add pygame

    # Run the demo
    python samples/stream_view_pygame_demo/main.py [video_path]

Controls:
    Space       - Play/Pause toggle
    Q / Escape  - Stop and exit
    +/-         - Zoom in/out
    R           - Reset zoom
    Arrow keys  - Pan (when zoomed)
    F           - Toggle fullscreen
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Default video path
DEFAULT_VIDEO = PROJECT_ROOT / "tmp" / "media" / "big_buck_bunny_1080p_h264.mov"


def main():
    parser = argparse.ArgumentParser(
        description="StreamView Pygame Demo - Native desktop video player",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Controls:
    Space       - Play/Pause toggle
    Q / Escape  - Stop and exit
    +/-         - Zoom in/out
    R           - Reset zoom
    Arrow keys  - Pan (when zoomed)
    F           - Toggle fullscreen

Examples:
    python main.py                          # Play default video
    python main.py video.mp4                # Play custom video
        """,
    )
    parser.add_argument(
        "video",
        nargs="?",
        default=str(DEFAULT_VIDEO),
        help="Path to video file (default: Big Buck Bunny)",
    )
    parser.add_argument(
        "--width",
        "-W",
        type=int,
        default=1280,
        help="Window width (default: 1280)",
    )
    parser.add_argument(
        "--height",
        "-H",
        type=int,
        default=720,
        help="Window height (default: 720)",
    )
    parser.add_argument(
        "--fps",
        "-f",
        type=int,
        default=60,
        help="Target FPS (default: 60)",
    )
    parser.add_argument(
        "--no-loop",
        action="store_true",
        help="Don't loop the video",
    )

    args = parser.parse_args()

    # Check video exists
    video_path = Path(args.video)
    if not video_path.exists():
        print(f"Error: Video not found: {video_path}")
        print("Run: python scripts/download_test_media.py")
        sys.exit(1)

    # Import components
    try:
        from imagestag.components.pygame import StreamViewPygame
    except ImportError as e:
        print("Error: pygame is required for this demo.")
        print("Install with: poetry add pygame")
        print(f"Details: {e}")
        sys.exit(1)

    from imagestag.components.stream_view import VideoStream

    # Create video stream
    video = VideoStream(str(video_path), loop=not args.no_loop)

    # Create view
    view = StreamViewPygame(
        width=args.width,
        height=args.height,
        title=f"StreamView - {video_path.name}",
        target_fps=args.fps,
    )

    # Add video layer
    view.add_layer(stream=video, z_index=0)

    # Current zoom level
    zoom_level = 1.0

    @view.on_key
    def handle_key(event):
        nonlocal zoom_level

        if not event.is_press:
            return

        key = event.key

        # Exit
        if key in ('q', 'escape'):
            view.stop()

        # Play/pause
        elif key == 'space':
            view.toggle_pause()

        # Zoom
        elif key in ('+', '='):
            zoom_level = min(10.0, zoom_level * 1.2)
            view.set_zoom(zoom_level)
        elif key == '-':
            zoom_level = max(1.0, zoom_level / 1.2)
            view.set_zoom(zoom_level)
        elif key == 'r':
            zoom_level = 1.0
            view.reset_zoom()

        # Pan
        elif key == 'left':
            view.viewport.pan(-0.05 / zoom_level, 0)
            view._compositor.update_viewports()
        elif key == 'right':
            view.viewport.pan(0.05 / zoom_level, 0)
            view._compositor.update_viewports()
        elif key == 'up':
            view.viewport.pan(0, -0.05 / zoom_level)
            view._compositor.update_viewports()
        elif key == 'down':
            view.viewport.pan(0, 0.05 / zoom_level)
            view._compositor.update_viewports()

    @view.on_mouse
    def handle_mouse(event):
        nonlocal zoom_level

        # Scroll to zoom
        if event.is_scroll:
            if event.delta_y > 0:
                zoom_level = min(10.0, zoom_level * 1.1)
            else:
                zoom_level = max(1.0, zoom_level / 1.1)

            # Zoom centered on mouse position
            cx = event.x / view.width
            cy = event.y / view.height
            view.set_zoom(zoom_level, cx, cy)

    print(f"Playing: {video_path.name}")
    print("Controls: Space=pause, Q=quit, +/-=zoom, R=reset, Arrows=pan")
    print()

    # Run the view (blocking)
    view.run()


if __name__ == "__main__":
    main()
