#!/usr/bin/env python3
"""
Terminal Multi-Player Demo - Dynamic multi-source video wall.

A demonstration of terminal video playback with various sources:
- Live generated patterns (always available)
- Video files (if found)
- Webcam feed (if detected)

Controls:
    L           - Cycle layouts (1x1 → 1x2 → 2x1 → 2x2 → 2x3 → 3x3)
    Space       - Play/Pause all
    +/-         - Speed control
    M           - Cycle render modes (all players)

    1-9         - Focus specific player
    0           - Control all players

    [/]         - Change source for focused player
    ←/→         - Seek backward/forward (seekable streams only)

    Q / Escape  - Quit

Usage:
    python samples/terminal_multi_demo/main.py
    python samples/terminal_multi_demo/main.py --layout 2x2
    python samples/terminal_multi_demo/main.py --no-webcam
"""

import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
from blessed import Terminal

from imagestag import Image
from imagestag.components.ascii import AsciiRenderer, RenderMode
from imagestag.streams import ImageStream, GeneratorStream, VideoStream, CameraStream

# ANSI codes
ESC = "\033"
RESET = f"{ESC}[0m"

# Try to import webcam support
try:
    import cv2
    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False


# =============================================================================
# Live Pattern Generators
# =============================================================================

def create_plasma_generator(width: int = 320, height: int = 240) -> Callable[[float], Image]:
    """Create a plasma effect generator."""
    def generate(timestamp: float) -> Image:
        t = timestamp * 2
        x = np.linspace(0, 4 * np.pi, width)
        y = np.linspace(0, 4 * np.pi, height)
        X, Y = np.meshgrid(x, y)

        v1 = np.sin(X + t)
        v2 = np.sin(Y + t * 0.5)
        v3 = np.sin((X + Y + t) * 0.5)
        v4 = np.sin(np.sqrt(X**2 + Y**2 + 1) + t)
        v = (v1 + v2 + v3 + v4) / 4

        r = ((np.sin(v * np.pi) + 1) * 127.5).astype(np.uint8)
        g = ((np.sin(v * np.pi + 2) + 1) * 127.5).astype(np.uint8)
        b = ((np.sin(v * np.pi + 4) + 1) * 127.5).astype(np.uint8)

        return Image(np.stack([r, g, b], axis=-1), pixel_format='RGB')
    return generate


def create_wave_generator(width: int = 320, height: int = 240) -> Callable[[float], Image]:
    """Create an animated wave interference pattern."""
    def generate(timestamp: float) -> Image:
        t = timestamp * 3
        x = np.linspace(-10, 10, width)
        y = np.linspace(-10, 10, height)
        X, Y = np.meshgrid(x, y)

        d1 = np.sqrt((X - 3)**2 + (Y - 3)**2)
        d2 = np.sqrt((X + 3)**2 + (Y - 3)**2)
        d3 = np.sqrt((X)**2 + (Y + 4)**2)

        wave = np.sin(d1 - t) + np.sin(d2 - t * 1.1) + np.sin(d3 - t * 0.9)
        wave = (wave + 3) / 6

        r = (wave * 255).astype(np.uint8)
        g = ((1 - wave) * 200).astype(np.uint8)
        b = (np.abs(wave - 0.5) * 2 * 255).astype(np.uint8)

        return Image(np.stack([r, g, b], axis=-1), pixel_format='RGB')
    return generate


def create_matrix_generator(width: int = 320, height: int = 240) -> Callable[[float], Image]:
    """Create a Matrix-style digital rain effect."""
    num_cols = width // 8
    drops = np.random.randint(0, height, num_cols).astype(np.float32)
    speeds = np.random.uniform(50, 150, num_cols)

    def generate(timestamp: float) -> Image:
        nonlocal drops
        pixels = np.zeros((height, width, 3), dtype=np.uint8)

        for i in range(num_cols):
            x = i * 8 + 4
            y = int(drops[i]) % height

            for j in range(20):
                yy = (y - j) % height
                intensity = max(0, 255 - j * 12)
                if x < width:
                    pixels[yy, max(0, x-2):min(width, x+3), 1] = intensity

            drops[i] = (drops[i] + speeds[i] * 0.03) % height

        return Image(pixels, pixel_format='RGB')
    return generate


def create_mandelbrot_generator(width: int = 320, height: int = 240) -> Callable[[float], Image]:
    """Create an animated Mandelbrot zoom generator."""
    cx, cy = -0.743643887037151, 0.131825904205330

    def generate(timestamp: float) -> Image:
        zoom = 0.5 * (1.5 ** (timestamp * 0.3))
        aspect = width / height

        x = np.linspace(cx - 2/zoom * aspect, cx + 2/zoom * aspect, width)
        y = np.linspace(cy - 2/zoom, cy + 2/zoom, height)
        X, Y = np.meshgrid(x, y)
        C = X + 1j * Y

        Z = np.zeros_like(C)
        M = np.zeros(C.shape, dtype=np.float32)

        for i in range(40):
            mask = np.abs(Z) <= 2
            Z[mask] = Z[mask] ** 2 + C[mask]
            M[mask] = i

        M = M / 40 * 255
        r = (np.sin(M * 0.1 + timestamp) * 127 + 128).astype(np.uint8)
        g = (np.sin(M * 0.1 + timestamp + 2) * 127 + 128).astype(np.uint8)
        b = (np.sin(M * 0.1 + timestamp + 4) * 127 + 128).astype(np.uint8)

        return Image(np.stack([r, g, b], axis=-1), pixel_format='RGB')
    return generate


def create_gradient_generator(width: int = 320, height: int = 240) -> Callable[[float], Image]:
    """Create a rotating gradient pattern."""
    def generate(timestamp: float) -> Image:
        angle = timestamp * 0.5
        x = np.linspace(-1, 1, width)
        y = np.linspace(-1, 1, height)
        X, Y = np.meshgrid(x, y)

        # Rotate coordinates
        Xr = X * np.cos(angle) - Y * np.sin(angle)
        Yr = X * np.sin(angle) + Y * np.cos(angle)

        r = ((Xr + 1) / 2 * 255).astype(np.uint8)
        g = ((Yr + 1) / 2 * 255).astype(np.uint8)
        b = (((np.sin(timestamp * 2) + 1) / 2) * 255 * np.ones((height, width))).astype(np.uint8)

        return Image(np.stack([r, g, b], axis=-1), pixel_format='RGB')
    return generate


def create_noise_generator(width: int = 320, height: int = 240) -> Callable[[float], Image]:
    """Create animated noise pattern."""
    def generate(timestamp: float) -> Image:
        # Seeded noise that changes with time
        np.random.seed(int(timestamp * 10) % 100000)
        noise = np.random.randint(0, 256, (height, width, 3), dtype=np.uint8)
        return Image(noise, pixel_format='RGB')
    return generate


# =============================================================================
# Video Source Management
# =============================================================================

@dataclass
class StreamSource:
    """A stream source configuration using ImageStream abstraction."""
    name: str
    label: str
    stream: ImageStream
    source_type: str  # 'generator', 'file', 'webcam'


def find_video_files() -> list[Path]:
    """Find video files in common locations."""
    extensions = {'.mp4', '.mov', '.avi', '.mkv', '.webm'}
    found = []

    for search_dir in [PROJECT_ROOT / "tmp" / "media", PROJECT_ROOT / "samples"]:
        if search_dir.exists():
            for f in search_dir.rglob("*"):
                if f.suffix.lower() in extensions and f.is_file():
                    found.append(f)

    return found[:4]


def check_webcam() -> int | None:
    """Check if webcam is available."""
    if not HAS_OPENCV:
        return None
    try:
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            ret, _ = cap.read()
            cap.release()
            return 0 if ret else None
    except Exception:
        pass
    return None


# =============================================================================
# Multi-Player Application
# =============================================================================

class MultiPlayerApp:
    """
    Dynamic multi-source terminal video player.

    Uses ImageStream abstraction for all sources, making them
    interchangeable with StreamView for web-based display.
    """

    LAYOUTS = ["1x1", "1x2", "2x1", "2x2", "2x3", "3x3"]

    # Pattern generators: (name, type, generator_factory, threaded)
    # threaded=True runs the generator in a background thread for smoother playback
    GENERATORS = [
        ("Plasma", "generator", create_plasma_generator, True),
        ("Waves", "generator", create_wave_generator, True),
        ("Matrix", "generator", create_matrix_generator, True),
        ("Mandelbrot", "generator", create_mandelbrot_generator, True),  # CPU intensive
        ("Gradient", "generator", create_gradient_generator, False),
        ("Noise", "generator", create_noise_generator, False),
    ]

    def __init__(self, layout: str = "2x2", use_webcam: bool = True):
        self.layout_idx = self.LAYOUTS.index(layout) if layout in self.LAYOUTS else 3
        self.mode = RenderMode.HALF_BLOCK
        self.char_aspect = 0.45

        # Build source list using ImageStream abstraction
        self.sources: list[StreamSource] = []
        self._build_sources(use_webcam)

        # Player slots - which source index each slot shows
        self.slots: list[int] = list(range(min(9, len(self.sources))))

        # State
        self._term: Terminal | None = None
        self._renderers: list[AsciiRenderer | None] = []
        self._running = False
        self._paused = False
        self._speed = 1.0
        self._focused: int = 0  # Always have a focused player (0 = first)
        self._start_time = 0.0
        self._pause_offset = 0.0
        self._needs_clear = False

    def _build_sources(self, use_webcam: bool) -> None:
        """Build list of available sources using ImageStream abstraction."""
        # Add generators using GeneratorStream
        for name, stype, gen_func, threaded in self.GENERATORS:
            stream = GeneratorStream(gen_func(), threaded=threaded, target_fps=30.0)
            self.sources.append(StreamSource(
                name=name.lower(),
                label=name,
                stream=stream,
                source_type=stype,
            ))

        # Add video files using VideoStream
        for vf in find_video_files():
            try:
                stream = VideoStream(str(vf), loop=True)
                self.sources.append(StreamSource(
                    name=vf.stem,
                    label=vf.stem[:12],
                    stream=stream,
                    source_type='file',
                ))
            except Exception:
                pass

        # Add webcam using CameraStream
        if use_webcam:
            webcam_idx = check_webcam()
            if webcam_idx is not None:
                stream = CameraStream(webcam_idx)
                self.sources.append(StreamSource(
                    name='webcam',
                    label='Webcam',
                    stream=stream,
                    source_type='webcam',
                ))

    @property
    def layout(self) -> str:
        return self.LAYOUTS[self.layout_idx]

    @property
    def grid(self) -> tuple[int, int]:
        return int(self.layout[0]), int(self.layout[2])

    def _time(self) -> float:
        """Get current playback time."""
        if self._paused:
            return self._pause_offset
        return (time.time() - self._start_time) * self._speed + self._pause_offset

    def run(self) -> None:
        """Main loop."""
        if not self.sources:
            print("No video sources!")
            return

        # Start all streams
        for source in self.sources:
            source.stream.start()

        self._term = Terminal()
        self._start_time = time.time()
        self._running = True

        with self._term.fullscreen(), self._term.cbreak(), self._term.hidden_cursor():
            try:
                while self._running:
                    t0 = time.time()
                    self._handle_input()
                    if not self._running:
                        break
                    self._render()

                    # 30 FPS limit
                    dt = time.time() - t0
                    if dt < 1/30:
                        time.sleep(1/30 - dt)
            except KeyboardInterrupt:
                pass
            finally:
                # Stop all streams
                for source in self.sources:
                    source.stream.stop()

        print("\nStopped")

    def _handle_input(self) -> None:
        """Process keyboard input."""
        key = self._term.inkey(timeout=0.001)
        if not key:
            return

        k = str(key)

        if k in ('q', 'Q') or key.name == 'KEY_ESCAPE':
            self._running = False
        elif k == ' ':
            self._toggle_pause()
        elif k in ('l', 'L'):
            self._cycle_layout()
        elif k in ('m', 'M'):
            self._cycle_mode()
        elif k in ('+', '='):
            self._speed = min(16.0, self._speed * 1.25)
        elif k in ('-', '_'):
            self._speed = max(0.25, self._speed / 1.25)
        elif k == '0':
            self._focused = 0  # Reset to first player
        elif k.isdigit() and int(k) <= len(self.slots):
            self._focused = int(k) - 1
        elif k == '[':
            self._change_source(-1)
        elif k == ']':
            self._change_source(1)
        elif key.name == 'KEY_LEFT':
            self._seek_relative(-5.0)
        elif key.name == 'KEY_RIGHT':
            self._seek_relative(5.0)

    def _toggle_pause(self) -> None:
        if self._paused:
            self._start_time = time.time()
            self._paused = False
            # Resume all streams
            for source in self.sources:
                source.stream.resume()
        else:
            self._pause_offset = self._time()
            self._paused = True
            # Pause all streams
            for source in self.sources:
                source.stream.pause()

    def _cycle_layout(self) -> None:
        self.layout_idx = (self.layout_idx + 1) % len(self.LAYOUTS)
        self._renderers = []
        self._needs_clear = True
        # Ensure focus is valid for new layout
        rows, cols = self.grid
        max_slots = rows * cols
        if self._focused >= max_slots:
            self._focused = 0

    def _cycle_mode(self) -> None:
        modes = list(RenderMode)
        self.mode = modes[(modes.index(self.mode) + 1) % len(modes)]
        self._renderers = []
        self._needs_clear = True

    def _change_source(self, delta: int) -> None:
        """Change source for focused slot."""
        if self._focused >= len(self.slots):
            return
        current = self.slots[self._focused]
        new_idx = (current + delta) % len(self.sources)
        self.slots[self._focused] = new_idx

    def _seek_relative(self, delta: float) -> None:
        """Seek the focused stream by delta seconds (if seekable)."""
        if self._focused >= len(self.slots):
            return
        src_idx = self.slots[self._focused]
        source = self.sources[src_idx]
        stream = source.stream

        # Only seek if stream is seekable
        if not stream.is_seekable:
            return

        # Use current_position (handles looping) or fall back to elapsed_time
        current = getattr(stream, 'current_position', stream.elapsed_time)
        new_pos = max(0.0, min(current + delta, stream.duration))

        # Seek using the stream's seek_to method
        if hasattr(stream, 'seek_to'):
            stream.seek_to(new_pos)

    def _render(self) -> None:
        """Render all players."""
        tw, th = os.get_terminal_size()
        rows, cols = self.grid
        cell_w = tw // cols
        cell_h = (th - 3) // rows  # Reserve 3 lines for status

        # Clear screen if layout/mode changed
        if self._needs_clear:
            sys.stdout.write(f"{ESC}[2J")
            self._needs_clear = False

        current_time = self._time()
        out = []

        # Ensure enough slots
        while len(self.slots) < rows * cols:
            self.slots.append(len(self.slots) % len(self.sources))

        # Render each cell
        for i in range(rows * cols):
            if i >= len(self.slots):
                break

            src_idx = self.slots[i]
            source = self.sources[src_idx]

            row, col = i // cols, i % cols
            x = col * cell_w + 1
            y = row * cell_h + 1

            # Get frame from stream
            try:
                frame, _ = source.stream.get_frame(current_time)
            except Exception:
                frame = None

            if frame is None:
                continue

            # Ensure renderer
            while len(self._renderers) <= i:
                self._renderers.append(None)

            rw, rh = cell_w - 2, cell_h - 2
            if self._renderers[i] is None or self._renderers[i].width != rw:
                self._renderers[i] = AsciiRenderer(
                    width=rw, max_height=rh,
                    mode=self.mode, char_aspect=self.char_aspect,
                    margin_x=0, margin_y=0,
                )

            # Render
            ascii_frame = self._renderers[i].render(frame)
            lines = ascii_frame.split("\n")

            # Label with source type color
            type_colors = {'generator': '35', 'file': '32', 'webcam': '31'}
            tc = type_colors.get(source.source_type, '37')
            focus_style = '1;36' if self._focused == i else '90'

            label = f"[{i+1}] {source.label}"[:cell_w-2]
            out.append(f"{ESC}[{y};{x}H{ESC}[{focus_style}m{ESC}[{tc}m{label}{RESET}")

            # Content
            for j, line in enumerate(lines[:cell_h-2]):
                out.append(f"{ESC}[{y+1+j};{x}H{line}")

        # Status bar (clean, single line)
        self._render_status(out, tw, th)

        sys.stdout.write("".join(out))
        sys.stdout.flush()

    def _render_status(self, out: list, tw: int, th: int) -> None:
        """Render status bar at bottom."""
        icon = "⏸" if self._paused else "▶"
        t = self._time()
        time_str = f"{int(t)//60:02d}:{int(t)%60:02d}"

        # Always have a focused player
        focus_str = f"Player {self._focused+1}"
        focused_stream = None
        if self._focused < len(self.slots):
            src = self.sources[self.slots[self._focused]]
            focus_str += f" ({src.label})"
            focused_stream = src.stream

        # Line 1: Status
        status = f" {icon} {time_str}  {self._speed:.2g}x  {self.layout}  {self.mode.name}  Focus: {focus_str}"
        out.append(f"{ESC}[{th-2};1H{ESC}[44m{ESC}[97m{status:<{tw}}{RESET}")

        # Line 2: Seekbar (in 1x1 mode with seekable stream) or Help
        rows, cols = self.grid
        is_single_view = rows == 1 and cols == 1
        is_seekable = focused_stream and focused_stream.is_seekable and focused_stream.duration > 0

        if is_single_view and is_seekable:
            # Render seekbar - use current_position which handles looping
            duration = focused_stream.duration
            position = getattr(focused_stream, 'current_position', focused_stream.elapsed_time)
            progress = min(1.0, position / duration) if duration > 0 else 0

            # Format times
            pos_str = f"{int(position)//60:02d}:{int(position)%60:02d}"
            dur_str = f"{int(duration)//60:02d}:{int(duration)%60:02d}"

            # Build progress bar
            bar_width = tw - len(pos_str) - len(dur_str) - 8  # padding
            filled = int(bar_width * progress)
            bar = "━" * filled + "●" + "─" * (bar_width - filled - 1)

            seekbar = f" {pos_str} {bar} {dur_str} "
            out.append(f"{ESC}[{th-1};1H{ESC}[46m{ESC}[97m{seekbar:<{tw}}{RESET}")
        else:
            # Help text
            help_text = " [/] Source  [←/→] Seek  [1-9] Focus  [Space] Pause  [L] Layout  [M] Mode  [Q] Quit"
            out.append(f"{ESC}[{th-1};1H{ESC}[100m{help_text:<{tw}}{RESET}")

        # Line 3: Source list or streaming indicator
        current_src = self.slots[self._focused] if self._focused < len(self.slots) else -1

        if is_single_view and focused_stream and not focused_stream.is_seekable:
            # Show streaming indicator for non-seekable (live) streams
            stream_icon = "◉" if not self._paused else "○"
            live_text = f" {stream_icon} LIVE STREAM  {self.sources[current_src].label}"
            out.append(f"{ESC}[{th};1H{ESC}[91m{live_text:<{tw}}{RESET}")
        else:
            # Source list (highlight current source for focused player)
            src_list = "Sources: " + " | ".join(
                f"{ESC}[{'1' if i == current_src else '0'}m{s.label}{RESET}"
                for i, s in enumerate(self.sources[:8])
            )
            out.append(f"{ESC}[{th};1H{ESC}[90m{src_list[:tw]}{RESET}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Terminal Multi-Player Demo")
    parser.add_argument("--layout", "-l", default="2x2", help="Initial layout")
    parser.add_argument("--no-webcam", action="store_true", help="Disable webcam")
    args = parser.parse_args()

    print("Terminal Multi-Player Demo")
    print("=" * 40)
    print(f"OpenCV: {HAS_OPENCV}")

    videos = find_video_files()
    print(f"Videos: {len(videos)}")

    if not args.no_webcam and HAS_OPENCV:
        webcam = check_webcam()
        print(f"Webcam: {'Yes' if webcam is not None else 'No'}")

    print("\nStarting... (Q to quit)")
    time.sleep(0.5)

    app = MultiPlayerApp(layout=args.layout, use_webcam=not args.no_webcam)
    app.run()


if __name__ == "__main__":
    main()
