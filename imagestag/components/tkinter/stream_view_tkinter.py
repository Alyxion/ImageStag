"""Tkinter-based StreamView implementation.

Provides a native tkinter window for displaying StreamView layers.
"""

from __future__ import annotations

import threading
import time
import tkinter as tk
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

from ..shared import ResizeEvent
from ..shared.stream_view_base import StreamViewBase
from .events import convert_key_event, convert_mouse_event, button_num_to_button

if TYPE_CHECKING:
    from imagestag import Image


@dataclass
class StreamViewTkinter(StreamViewBase):
    """Native tkinter implementation of StreamView.

    Displays StreamView layers in a tkinter window with keyboard/mouse handling.
    No additional dependencies required (tkinter is built into Python).

    Example:
        from imagestag.components.tkinter import StreamViewTkinter
        from imagestag.streams import VideoStream

        video = VideoStream('video.mp4', loop=True)

        view = StreamViewTkinter(1280, 720, title="My Player")
        view.add_layer(stream=video, z_index=0)

        @view.on_key
        def handle_key(event):
            if event.key == 'q':
                view.stop()

        view.run()

    Attributes:
        width: Window width in pixels
        height: Window height in pixels
        title: Window title
        target_fps: Target frame rate for rendering
        compositing_mode: "python" for single-image compositing,
                         "native" for per-layer tkinter drawing
        resizable: Whether window can be resized
    """

    # Tkinter-specific attributes
    compositing_mode: Literal["python", "native"] = "python"
    resizable: bool = True

    # Tkinter-specific state
    _root: Any = field(default=None, repr=False)
    _canvas: Any = field(default=None, repr=False)
    _photo_image: Any = field(default=None, repr=False)
    _canvas_image_id: int = field(default=0, repr=False)
    _frame_interval_ms: int = field(default=16, repr=False)
    _ImageTk: Any = field(default=None, repr=False)
    _PILImage: Any = field(default=None, repr=False)

    def __post_init__(self) -> None:
        """Initialize compositor and frame interval."""
        super().__post_init__()
        self._frame_interval_ms = max(1, 1000 // self.target_fps)

    def stop(self) -> None:
        """Stop playback and close window."""
        super().stop()
        if self._root:
            self._root.destroy()

    def run(self) -> None:
        """Run the main event loop (blocking).

        This creates the tkinter window and runs the event loop
        until stop() is called or window is closed.
        """
        # Check for PIL (required for tkinter image display)
        try:
            from PIL import Image as PILImage, ImageTk
            self._ImageTk = ImageTk
            self._PILImage = PILImage
        except ImportError:
            raise ImportError(
                "Pillow is required for StreamViewTkinter. "
                "Install with: poetry add Pillow"
            )

        # Create root window
        self._root = tk.Tk()
        self._root.title(self.title)
        self._root.geometry(f"{self.width}x{self.height}")

        if self.resizable:
            self._root.resizable(True, True)
        else:
            self._root.resizable(False, False)

        # Create canvas
        self._canvas = tk.Canvas(
            self._root,
            width=self.width,
            height=self.height,
            bg='black',
            highlightthickness=0,
        )
        self._canvas.pack(fill=tk.BOTH, expand=True)

        # Create initial image on canvas
        self._canvas_image_id = self._canvas.create_image(
            0, 0, anchor=tk.NW, image=None
        )

        # Bind events
        self._root.bind('<KeyPress>', self._on_key_press)
        self._root.bind('<KeyRelease>', self._on_key_release)
        self._canvas.bind('<Motion>', self._on_mouse_motion)
        self._canvas.bind('<Button-1>', lambda e: self._on_mouse_button(e, 1, True))
        self._canvas.bind('<Button-2>', lambda e: self._on_mouse_button(e, 2, True))
        self._canvas.bind('<Button-3>', lambda e: self._on_mouse_button(e, 3, True))
        self._canvas.bind('<ButtonRelease-1>', lambda e: self._on_mouse_button(e, 1, False))
        self._canvas.bind('<ButtonRelease-2>', lambda e: self._on_mouse_button(e, 2, False))
        self._canvas.bind('<ButtonRelease-3>', lambda e: self._on_mouse_button(e, 3, False))
        self._canvas.bind('<MouseWheel>', self._on_mouse_wheel)
        self._root.bind('<Configure>', self._on_configure)
        self._root.protocol("WM_DELETE_WINDOW", self._on_close)

        # Start layers
        self.start()

        # Schedule first frame
        self._root.after(self._frame_interval_ms, self._render_loop)

        # Run mainloop
        self._root.mainloop()

    def run_async(self) -> threading.Thread:
        """Start the view in a background thread.

        Note: Tkinter has thread restrictions. This may not work
        correctly on all platforms.

        :return: Thread running the view
        """
        thread = threading.Thread(target=self.run, daemon=True)
        thread.start()
        return thread

    def _on_close(self) -> None:
        """Handle window close."""
        self.stop()

    def _on_key_press(self, event: tk.Event) -> None:
        """Handle key press event."""
        key_event = convert_key_event(event, is_press=True)
        self._dispatch_key_event(key_event)

    def _on_key_release(self, event: tk.Event) -> None:
        """Handle key release event."""
        key_event = convert_key_event(event, is_press=False)
        self._dispatch_key_event(key_event)

    def _on_mouse_motion(self, event: tk.Event) -> None:
        """Handle mouse motion event."""
        mouse_event = convert_mouse_event(event, event_type="move")
        self._dispatch_mouse_event(mouse_event)

    def _on_mouse_button(self, event: tk.Event, button_num: int, is_press: bool) -> None:
        """Handle mouse button event."""
        button = button_num_to_button(button_num)
        event_type = "press" if is_press else "release"
        mouse_event = convert_mouse_event(event, event_type=event_type, button=button)
        self._dispatch_mouse_event(mouse_event)

    def _on_mouse_wheel(self, event: tk.Event) -> None:
        """Handle mouse wheel event."""
        mouse_event = convert_mouse_event(event, event_type="scroll")
        self._dispatch_mouse_event(mouse_event)

    def _on_configure(self, event: tk.Event) -> None:
        """Handle window configure (resize) event."""
        if event.widget != self._root:
            return

        if event.width != self.width or event.height != self.height:
            self._handle_resize(event.width, event.height)

    def _render_loop(self) -> None:
        """Render loop called by tkinter after()."""
        if not self._running:
            return

        if not self._paused:
            timestamp = time.perf_counter() - self._start_time
            self._render_frame(timestamp)

        # Schedule next frame
        self._root.after(self._frame_interval_ms, self._render_loop)

    def _render_frame(self, timestamp: float) -> None:
        """Render a single frame to the canvas.

        :param timestamp: Current playback timestamp
        """
        if self.compositing_mode == "python":
            # Composite all layers to single Image, then display
            composite = self._compositor.composite_rgb(timestamp)
            self._display_image(composite)
        else:
            # Native mode: would draw each layer separately
            # For tkinter, this is the same as python mode since we use a single canvas
            composite = self._compositor.composite_rgb(timestamp)
            self._display_image(composite)

    def _display_image(self, image: "Image") -> None:
        """Display an Image on the tkinter canvas.

        :param image: Image to display
        """
        # Resize to canvas size
        canvas_w = self._canvas.winfo_width()
        canvas_h = self._canvas.winfo_height()

        if canvas_w <= 1 or canvas_h <= 1:
            # Canvas not ready yet
            return

        if image.width != canvas_w or image.height != canvas_h:
            image = image.resized((canvas_w, canvas_h))

        # Convert to PIL Image, then to PhotoImage
        pil_image = self._PILImage.fromarray(image.convert('RGB').get_pixels())
        self._photo_image = self._ImageTk.PhotoImage(pil_image)

        # Update canvas
        self._canvas.itemconfig(self._canvas_image_id, image=self._photo_image)
