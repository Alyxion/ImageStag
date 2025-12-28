#!/usr/bin/env python3
"""Video Player - Tkinter Backend.

Full-featured video player with seeking, speed control, and progress bar.
Uses the shared PlaybackController for all backends.

Usage:
    poetry run python samples/video_player_tkinter/main.py [video_path]

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
import time
from pathlib import Path
import tkinter as tk
from tkinter import ttk

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Default video path
DEFAULT_VIDEO = PROJECT_ROOT / "tmp" / "media" / "big_buck_bunny_1080p_h264.mov"

# Help text
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


class VideoPlayerApp:
    """Tkinter video player application."""

    def __init__(self, root: tk.Tk, video_path: Path, loop: bool = True):
        self.root = root
        self.video_path = video_path

        # Import components
        from imagestag.streams import VideoStream
        from imagestag.components.shared import (
            PlaybackController,
            PlaybackConfig,
            PlaybackState,
            format_time,
        )
        from PIL import Image as PILImage, ImageTk

        self.PlaybackState = PlaybackState
        self.format_time = format_time
        self.PILImage = PILImage
        self.ImageTk = ImageTk

        # Create video and controller
        self.video = VideoStream(str(video_path), loop=loop)
        self.config = PlaybackConfig(seek_step=5.0, fine_seek_step=1.0)
        self.controller = PlaybackController(self.video, self.config)

        # UI state
        self.show_help = False
        self.fullscreen = False
        self.running = True
        self._photo = None  # Keep reference to prevent garbage collection

        # Setup window
        self.root.title(f"Video Player - {video_path.name}")
        self.root.geometry("1280x720")
        self.root.configure(bg="#141419")

        # Create main frame
        self.main_frame = tk.Frame(root, bg="#141419")
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Video canvas
        self.canvas = tk.Canvas(
            self.main_frame,
            bg="#141419",
            highlightthickness=0,
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Progress bar frame
        self.bar_frame = tk.Frame(self.main_frame, bg="#282830", height=50)
        self.bar_frame.pack(fill=tk.X, side=tk.BOTTOM)
        self.bar_frame.pack_propagate(False)

        # Progress bar widgets
        self._setup_progress_bar()

        # Bind events
        self._bind_events()

        # Start playback
        self.controller.play()

        # Start update loop
        self._update()

    def _setup_progress_bar(self):
        """Setup progress bar widgets."""
        # Left label (icon + time)
        self.left_label = tk.Label(
            self.bar_frame,
            text="\u25B6  00:00",
            bg="#282830",
            fg="#dcdce0",
            font=("Helvetica", 12),
        )
        self.left_label.pack(side=tk.LEFT, padx=15)

        # Right label (speed + fps + duration)
        self.right_label = tk.Label(
            self.bar_frame,
            text="00:00",
            bg="#282830",
            fg="#8c8c90",
            font=("Helvetica", 12),
        )
        self.right_label.pack(side=tk.RIGHT, padx=15)

        # Progress bar (using ttk.Scale for simplicity)
        style = ttk.Style()
        style.configure("Custom.Horizontal.TScale", background="#282830")

        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Scale(
            self.bar_frame,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            variable=self.progress_var,
            command=self._on_progress_change,
            style="Custom.Horizontal.TScale",
        )
        self.progress_bar.pack(fill=tk.X, expand=True, padx=10, pady=15)

        # Track if user is dragging
        self._dragging = False
        self.progress_bar.bind("<ButtonPress-1>", lambda e: setattr(self, '_dragging', True))
        self.progress_bar.bind("<ButtonRelease-1>", self._on_progress_release)

    def _on_progress_change(self, value):
        """Handle progress bar value change."""
        pass  # Will seek on release

    def _on_progress_release(self, event):
        """Handle progress bar release."""
        self._dragging = False
        progress = self.progress_var.get() / 100
        self.controller.seek_to(progress * self.controller.duration)

    def _bind_events(self):
        """Bind keyboard and window events."""
        self.root.bind("<KeyPress>", self._on_key)
        self.root.bind("<Configure>", self._on_resize)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_key(self, event):
        """Handle key press."""
        if self.show_help:
            self.show_help = False
            self._hide_help()
            return

        key = event.keysym.lower()
        shift = event.state & 0x1

        if key in ("q", "escape"):
            self._on_close()

        elif key == "space":
            self.controller.toggle()

        elif key == "left":
            if shift:
                self.controller.seek_relative(-self.config.fine_seek_step)
            else:
                self.controller.seek_backward()

        elif key == "right":
            if shift:
                self.controller.seek_relative(self.config.fine_seek_step)
            else:
                self.controller.seek_forward()

        elif key == "home":
            self.controller.seek_to_start()

        elif key == "end":
            self.controller.seek_to_end()

        elif key in ("plus", "equal"):
            self.controller.speed_up()

        elif key == "minus":
            self.controller.speed_down()

        elif key == "h" or key == "question":
            self.show_help = not self.show_help
            if self.show_help:
                self._show_help()
            else:
                self._hide_help()

        elif key == "f":
            self.fullscreen = not self.fullscreen
            self.root.attributes("-fullscreen", self.fullscreen)

    def _on_resize(self, event):
        """Handle window resize."""
        pass

    def _on_close(self):
        """Handle window close."""
        self.running = False
        self.controller.stop()
        self.root.quit()

    def _show_help(self):
        """Show help overlay."""
        self.help_frame = tk.Frame(self.root, bg="#1e1e28")
        self.help_frame.place(relx=0, rely=0, relwidth=1, relheight=1)

        help_label = tk.Label(
            self.help_frame,
            text=HELP_TEXT,
            bg="#1e1e28",
            fg="#dcdce0",
            font=("Courier", 12),
            justify=tk.LEFT,
        )
        help_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

    def _hide_help(self):
        """Hide help overlay."""
        if hasattr(self, "help_frame"):
            self.help_frame.destroy()

    def _update(self):
        """Update loop."""
        if not self.running:
            return

        # Get frame
        frame, _ = self.controller.get_frame()

        if frame is not None:
            self.controller.update_fps()

            # Get canvas size
            canvas_w = self.canvas.winfo_width()
            canvas_h = self.canvas.winfo_height()

            if canvas_w > 1 and canvas_h > 1:
                # Scale frame to fit
                scale_w = canvas_w / frame.width
                scale_h = canvas_h / frame.height
                scale = min(scale_w, scale_h)

                new_w = int(frame.width * scale)
                new_h = int(frame.height * scale)

                # Convert to PIL Image
                pil_image = frame.to_pil()
                pil_image = pil_image.resize((new_w, new_h), self.PILImage.LANCZOS)

                # Convert to PhotoImage
                self._photo = self.ImageTk.PhotoImage(pil_image)

                # Draw on canvas
                x = canvas_w // 2
                y = canvas_h // 2
                self.canvas.delete("all")
                self.canvas.create_image(x, y, image=self._photo, anchor=tk.CENTER)

        # Update progress bar
        state = self.controller.get_progress_state()

        # Left label
        icons = {
            self.PlaybackState.PLAYING: "\u25B6",
            self.PlaybackState.PAUSED: "\u23F8",
            self.PlaybackState.STOPPED: "\u23F9",
        }
        icon = icons.get(state.playback_state, "?")
        self.left_label.config(text=f"{icon}  {self.format_time(state.current_time)}")

        # Right label
        parts = []
        if state.playback_speed != 1.0:
            parts.append(f"{state.playback_speed:.1f}x")
        if state.actual_fps > 0:
            parts.append(f"{state.actual_fps:.0f}fps")
        parts.append(self.format_time(state.total_time))
        self.right_label.config(text="  |  ".join(parts))

        # Progress bar (only update if not dragging)
        if not self._dragging and state.total_time > 0:
            progress = (state.current_time / state.total_time) * 100
            self.progress_var.set(progress)

        # Schedule next update
        self.root.after(16, self._update)  # ~60 fps


def main():
    parser = argparse.ArgumentParser(description="Video Player - Tkinter Backend")
    parser.add_argument(
        "video",
        nargs="?",
        default=str(DEFAULT_VIDEO),
        help="Path to video file",
    )
    parser.add_argument("--no-loop", action="store_true", help="Don't loop video")

    args = parser.parse_args()

    # Check video exists
    video_path = Path(args.video)
    if not video_path.exists():
        print(f"Error: Video not found: {video_path}")
        print("Run: python scripts/download_test_media.py")
        sys.exit(1)

    # Check PIL
    try:
        from PIL import Image, ImageTk
    except ImportError:
        print("Error: Pillow is required. Install with: poetry add pillow")
        sys.exit(1)

    # Create and run app
    root = tk.Tk()
    app = VideoPlayerApp(root, video_path, loop=not args.no_loop)
    root.mainloop()


if __name__ == "__main__":
    main()
