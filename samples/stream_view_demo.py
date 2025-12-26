"""StreamView Demo - High-performance video streaming with NiceGUI.

This demo showcases the StreamView component with:
- 1080p video playback at 60fps target
- Multi-layer compositing
- SVG overlay with mouse tracking
- Real-time performance metrics

Usage:
    python samples/stream_view_demo.py

    # Or with custom video:
    python samples/stream_view_demo.py /path/to/video.mp4

Requirements:
    - OpenCV (cv2) for video playback
    - The test video in tmp/media/ (run scripts/download_test_media.py)
"""

import sys
from pathlib import Path

from nicegui import ui

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from imagestag import Image
from imagestag.components.stream_view import StreamView, VideoStream, CustomStream
from imagestag.filters import FalseColor

# Default video path
DEFAULT_VIDEO = PROJECT_ROOT / "tmp" / "media" / "big_buck_bunny_1080p_h264.mov"


def main(video_path: str | None = None):
    """Main demo application."""
    # Determine video source
    video_file = Path(video_path) if video_path else DEFAULT_VIDEO

    if not video_file.exists():
        ui.label(f"Video not found: {video_file}").classes("text-red-500 text-xl")
        ui.label("Run: python scripts/download_test_media.py").classes("text-gray-500")
        ui.run(show=False, port=8080)
        return

    ui.dark_mode().enable()

    with ui.column().classes("w-full items-center p-4 gap-4"):
        ui.label("StreamView Demo").classes("text-2xl font-bold")

        # Create video stream
        video_stream = VideoStream(str(video_file), loop=True)

        # Create StreamView component
        view = StreamView(
            width=960,  # Half of 1920 for display
            height=540,  # Half of 1080 for display
            show_metrics=True,
            # Enable zoom/pan with navigation window
            enable_zoom=True,
            min_zoom=1.0,
            max_zoom=8.0,
            show_nav_window=True,
            nav_window_position="bottom-right",
            nav_window_size=(160, 90),
        )

        # Add video layer (normal view, no filters)
        # depth=1.0 (default) means it zooms/pans with the viewport
        video_layer = view.add_layer(
            stream=video_stream,
            fps=60,
            z_index=0,
            buffer_size=4,
            jpeg_quality=85,
            # depth=1.0 is default - content layer that follows viewport
        )

        # Thermal lens size (display pixels)
        LENS_W, LENS_H = 200, 150
        # Overscan border (extra pixels on each side to prevent stale content during movement)
        # Higher values = more tolerance for fast mouse movement, but larger images to transfer
        LENS_OVERSCAN = 16

        # Capture view dimensions for use in callbacks
        DISPLAY_W, DISPLAY_H = view._width, view._height

        # Track mouse position for dynamic cropping
        mouse_pos = {'x': DISPLAY_W // 2, 'y': DISPLAY_H // 2}  # Screen coords (start at center)

        # Create thermal lens in PIGGYBACK MODE
        # This eliminates all producer thread delay - frames are injected directly
        # from video's on_frame callback, synchronized perfectly with video frames
        import time as time_module
        import base64
        false_color = FalseColor(colormap='hot')

        # Create thermal layer FIRST with piggyback=True (no stream, no producer thread)
        # Frames will be injected directly by video's on_frame callback
        thermal_layer = view.add_layer(
            piggyback=True,  # No producer thread - frames injected directly
            fps=60,
            z_index=15,  # On top of everything except SVG
            buffer_size=1,  # Single frame buffer
            jpeg_quality=80,
            depth=0.0,  # Fixed overlay - doesn't zoom/pan with viewport
            # Position in top-right corner initially
            x=DISPLAY_W - LENS_W - 10,
            y=10,
            width=LENS_W,
            height=LENS_H,
            # Overscan: crop extra pixels to prevent stale content during lens movement
            overscan=LENS_OVERSCAN,
        )

        # Counter for debug output
        thermal_debug_counter = [0]

        def precompute_and_inject_thermal(frame: Image, capture_time: float) -> None:
            """Called synchronously by video stream when it captures a frame.
            Runs in video's producer thread, BEFORE video encodes.
            Directly injects into thermal_layer's buffer - zero delay!
            """
            try:
                _precompute_and_inject_thermal_impl(frame, capture_time)
            except Exception as ex:
                import traceback
                print(f"[THERMAL ERROR] {ex}", flush=True)
                traceback.print_exc()

        def _precompute_and_inject_thermal_impl(frame: Image, capture_time: float) -> None:
            t0 = time_module.perf_counter()

            # Calculate crop region based on mouse position, accounting for viewport
            # Read viewport from video layer (which tracks the current zoom/pan state)
            zoom = video_layer._viewport_zoom
            vp_x = video_layer._viewport_x
            vp_y = video_layer._viewport_y

            # Debug less frequently (every 300 frames = ~5 sec at 60fps)
            thermal_debug_counter[0] += 1
            if thermal_debug_counter[0] % 300 == 0:
                print(f"[THERMAL] zoom={zoom:.2f}, vp_x={vp_x:.3f}, vp_y={vp_y:.3f}", flush=True)

            # Get current lens position (for anchor tracking)
            lens_x = thermal_layer.x
            lens_y = thermal_layer.y

            # Calculate lens CENTER position (not mouse position!)
            # The lens display is clamped to stay within bounds, so we should
            # crop based on where the lens actually IS, not where the mouse is
            lens_center_x = lens_x + LENS_W // 2
            lens_center_y = lens_y + LENS_H // 2

            # Convert lens center to normalized coords (0-1)
            norm_x = lens_center_x / DISPLAY_W
            norm_y = lens_center_y / DISPLAY_H

            # Convert to source coords accounting for viewport
            # When zoomed, the visible area starts at (vp_x, vp_y) and spans 1/zoom
            source_norm_x = vp_x + norm_x / zoom
            source_norm_y = vp_y + norm_y / zoom

            # Scale to pixel coordinates in source frame
            cx = int(source_norm_x * frame.width)
            cy = int(source_norm_y * frame.height)

            # Thermal lens crop size (in source pixels)
            # When zoomed, crop a SMALLER region to match the magnification of the main view
            # At 2x zoom, the main view shows 1/2 as many source pixels per display pixel,
            # so the thermal lens should also show 1/2 as many source pixels
            # Include OVERSCAN: crop extra pixels for the border
            display_w_with_overscan = LENS_W + 2 * LENS_OVERSCAN
            display_h_with_overscan = LENS_H + 2 * LENS_OVERSCAN
            crop_w = int(display_w_with_overscan * frame.width / DISPLAY_W / zoom)
            crop_h = int(display_h_with_overscan * frame.height / DISPLAY_H / zoom)

            # Calculate ideal crop region (may extend beyond frame bounds)
            ideal_x1 = cx - crop_w // 2
            ideal_y1 = cy - crop_h // 2
            ideal_x2 = ideal_x1 + crop_w
            ideal_y2 = ideal_y1 + crop_h

            # Use numpy directly for edge-aware cropping with black padding
            import numpy as np

            # Get frame data as numpy array
            frame_data = frame.get_pixels_rgb()

            # Create black canvas of desired crop size
            canvas = np.zeros((max(1, crop_h), max(1, crop_w), 3), dtype=np.uint8)

            # Calculate source region (clamped to frame bounds)
            src_x1 = max(0, ideal_x1)
            src_y1 = max(0, ideal_y1)
            src_x2 = min(frame.width, ideal_x2)
            src_y2 = min(frame.height, ideal_y2)

            # Calculate destination region in canvas
            dst_x1 = src_x1 - ideal_x1
            dst_y1 = src_y1 - ideal_y1
            dst_x2 = dst_x1 + (src_x2 - src_x1)
            dst_y2 = dst_y1 + (src_y2 - src_y1)

            # Copy valid region if there is overlap
            if src_x2 > src_x1 and src_y2 > src_y1:
                canvas[dst_y1:dst_y2, dst_x1:dst_x2] = frame_data[src_y1:src_y2, src_x1:src_x2]

            cropped = Image(canvas, pixel_format="RGB")

            t_crop = time_module.perf_counter()

            thermal = false_color.apply(cropped)
            t_filter = time_module.perf_counter()

            # Pre-encode to JPEG (larger image with overscan)
            jpeg_bytes = thermal.to_jpeg(quality=80)
            encoded = f"data:image/jpeg;base64,{base64.b64encode(jpeg_bytes).decode('ascii')}"
            t_encode = time_module.perf_counter()

            # DIRECTLY inject into thermal layer's buffer - no thread scheduling delay!
            # Include anchor position so JS knows where this content is centered
            thermal_layer.inject_frame(
                encoded=encoded,
                birth_time=capture_time,
                step_timings={
                    'crop_ms': (t_crop - t0) * 1000,
                    'filter_ms': (t_filter - t_crop) * 1000,
                    'enc_ms': (t_encode - t_filter) * 1000,
                },
                anchor_x=lens_x,
                anchor_y=lens_y,
            )

        # Register synchronous callback - runs in video's thread, injects directly
        video_stream.on_frame(precompute_and_inject_thermal)

        import numpy as np

        # Multi-output stream: simulates a detector that produces both
        # detection boxes AND a heatmap from a single processing pass
        def render_detector(timestamp: float) -> dict[str, Image]:
            """Render multiple outputs from one processing pass."""
            # Calculate animated position (simulating detected object)
            x_pos = int(DISPLAY_W * 0.2 + DISPLAY_W * 0.4 * abs(np.sin(timestamp * 0.5)))
            y_pos = int(DISPLAY_H * 0.3 + DISPLAY_H * 0.2 * abs(np.cos(timestamp * 0.7)))

            # Output 1: Detection boxes
            boxes = np.zeros((DISPLAY_H, DISPLAY_W, 4), dtype=np.uint8)
            # Draw border (2px wide) - green detection box
            boxes[y_pos:y_pos+2, x_pos:x_pos+150, :] = [0, 255, 0, 200]  # Top
            boxes[y_pos+98:y_pos+100, x_pos:x_pos+150, :] = [0, 255, 0, 200]  # Bottom
            boxes[y_pos:y_pos+100, x_pos:x_pos+2, :] = [0, 255, 0, 200]  # Left
            boxes[y_pos:y_pos+100, x_pos+148:x_pos+150, :] = [0, 255, 0, 200]  # Right
            # Label background
            boxes[max(0, y_pos-20):y_pos, x_pos:x_pos+80, :] = [0, 180, 0, 220]

            # Output 2: Heatmap (semi-transparent colored area showing "attention")
            heatmap = np.zeros((DISPLAY_H, DISPLAY_W, 4), dtype=np.uint8)
            # Draw a gradient-like blob at the detection center
            cx, cy = x_pos + 75, y_pos + 50
            for dy in range(-40, 41, 4):
                for dx in range(-60, 61, 4):
                    dist = np.sqrt(dx*dx + dy*dy)
                    if dist < 60:
                        intensity = int(150 * (1 - dist/60))
                        py, px = cy + dy, cx + dx
                        if 0 <= py < DISPLAY_H and 0 <= px < DISPLAY_W:
                            heatmap[py:py+4, px:px+4, :] = [intensity, 50, 255-intensity, 100]

            return {
                "boxes": Image(boxes, pixel_format="RGBA"),
                "heatmap": Image(heatmap, pixel_format="RGBA"),
            }

        # Create ONE stream that produces multiple outputs
        detector_stream = CustomStream(render_detector, mode="thread")

        # Add heatmap layer (below boxes, semi-transparent)
        view.add_layer(
            stream=detector_stream,
            stream_output="heatmap",  # Use the heatmap output
            fps=10,
            z_index=8,
            buffer_size=2,
            use_png=True,
            depth=0.0,  # Fixed overlay - doesn't zoom/pan with viewport
        )

        # Add boxes layer (on top of heatmap)
        view.add_layer(
            stream=detector_stream,
            stream_output="boxes",  # Use the boxes output
            fps=10,
            z_index=10,
            buffer_size=2,
            use_png=True,
            depth=0.0,  # Fixed overlay - doesn't zoom/pan with viewport
        )

        # Set up SVG overlay with crosshair (topmost)
        view.set_svg(
            f'''
            <svg viewBox="0 0 {DISPLAY_W} {DISPLAY_H}" xmlns="http://www.w3.org/2000/svg">
                <!-- Crosshair -->
                <line x1="{{x}}" y1="0" x2="{{x}}" y2="{DISPLAY_H}"
                      stroke="rgba(255,255,255,0.5)" stroke-width="1"/>
                <line x1="0" y1="{{y}}" x2="{DISPLAY_W}" y2="{{y}}"
                      stroke="rgba(255,255,255,0.5)" stroke-width="1"/>
                <circle cx="{{x}}" cy="{{y}}" r="20"
                        fill="none" stroke="rgba(255,0,0,0.8)" stroke-width="2"/>

                <!-- Coordinates label -->
                <rect x="{{label_x}}" y="{{label_y}}" width="100" height="24"
                      fill="rgba(0,0,0,0.7)" rx="4"/>
                <text x="{{text_x}}" y="{{text_y}}"
                      fill="white" font-size="12" font-family="monospace">
                    {{coords}}
                </text>
            </svg>
            ''',
            {
                'x': DISPLAY_W // 2,
                'y': DISPLAY_H // 2,
                'label_x': DISPLAY_W // 2 + 10,
                'label_y': DISPLAY_H // 2 + 10,
                'text_x': DISPLAY_W // 2 + 15,
                'text_y': DISPLAY_H // 2 + 26,
                'coords': f'{DISPLAY_W // 2}, {DISPLAY_H // 2}',
            }
        )

        # Handle mouse movement - update SVG crosshair and thermal lens position
        @view.on_mouse_move
        def handle_mouse(e):
            x, y = int(e.x), int(e.y)

            # Update mouse position for thermal lens cropping
            mouse_pos['x'] = x
            mouse_pos['y'] = y

            # Move thermal lens to follow mouse (centered on cursor)
            lens_x = max(0, min(x - LENS_W // 2, DISPLAY_W - LENS_W))
            lens_y = max(0, min(y - LENS_H // 2, DISPLAY_H - LENS_H))
            view.update_layer_position(thermal_layer.id, x=lens_x, y=lens_y)

            # When video is paused, update thermal lens from last frame
            if not video_stream.is_running:
                last_frame = video_stream.last_frame
                if last_frame is not None:
                    # Re-crop thermal from current mouse position using last frame
                    precompute_and_inject_thermal(last_frame, time_module.perf_counter())

            # Update SVG crosshair
            label_x = min(max(x + 10, 5), 855)
            label_y = min(max(y + 10, 5), 511)
            view.update_svg_values(
                x=x,
                y=y,
                label_x=label_x,
                label_y=label_y,
                text_x=label_x + 5,
                text_y=label_y + 16,
                coords=f'{x}, {y}',
            )

        # Control buttons
        with ui.row().classes("gap-2"):
            def do_start():
                video_stream.start()
                view.start()

            def do_pause():
                # Only pause video playback - keep view running so lens can still move
                video_stream.pause()

            def do_resume():
                video_stream.resume()

            def do_stop():
                view.stop()
                video_stream.stop()

            ui.button("Start", on_click=do_start).classes("bg-green-600")
            ui.button("Pause", on_click=do_pause).classes("bg-yellow-600")
            ui.button("Resume", on_click=do_resume).classes("bg-blue-600")
            ui.button("Stop", on_click=do_stop).classes("bg-red-600")

            async def show_metrics():
                metrics = view.get_metrics()
                ui.notify(f"Python metrics: {metrics}")

            ui.button("Metrics", on_click=show_metrics).classes("bg-gray-600")

        # Start playing automatically
        # Note: thermal lens uses frame sharing from video_stream, no separate start needed
        view.start()

        # Info
        with ui.card().classes("w-full max-w-2xl"):
            ui.markdown(f'''
### Controls
- **Mouse move**: Crosshair + thermal lens follows cursor
- **Mouse wheel**: Zoom in/out (centered on cursor)
- **Drag**: Pan when zoomed in
- **Double-click**: Reset zoom to 1x
- **Nav window**: Click to jump to position (shown when zoomed)
- **Start/Stop**: Control playback
- **Metrics**: View performance data

### Video Source
`{video_file}`

### Layers (bottom to top)
1. **Video** (z=0): VideoStream at 60fps (normal colors)
2. **Watermark** (z=5): Static RGBA image with PNG transparency
3. **Heatmap** (z=8): Multi-output stream "heatmap" at 10fps
4. **Detection Boxes** (z=10): Multi-output stream "boxes" at 10fps
5. **Thermal Lens** (z=15): Positioned layer with CenterCrop + FalseColor("hot")
6. **SVG Overlay** (topmost): Crosshair with coordinates

### Architecture
- Pull-based frame delivery (JS requests, Python responds)
- Ahead-of-time buffering (4 frames for video, 2 for overlays)
- JPEG for video (fast), PNG for transparent overlays
- **Per-layer FilterPipeline**: Apply ImageStag filters to any layer
- **Positioned layers**: x/y/width/height for PIP windows
- Multi-output streams: one handler → multiple layer outputs
- Per-layer independent FPS control
- **Server-side viewport cropping**: Zoom crops on server before encoding (handles large images)
            ''')

    ui.run(
        show=False,
        title="StreamView Demo",
        port=8080,
        reload=True,
        uvicorn_reload_includes="*.py,*.js,*.css",
    )


if __name__ in {"__main__", "__mp_main__"}:
    video_arg = sys.argv[1] if len(sys.argv) > 1 else None
    main(video_arg)
