"""StreamView Demo - High-performance video streaming with NiceGUI.

This demo showcases the StreamView component with:
- 1080p video playback at 60fps target
- Multi-layer compositing
- Two lenses: thermal view and magnifier with barrel distortion
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
from imagestag.components.stream_view import (
    StreamView,
    VideoStream,
    CustomStream,
    create_thermal_lens,
    create_magnifier_lens,
    AIORTC_AVAILABLE,
)

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
            width=1280,  # 720p default
            height=720,
            show_metrics=True,
            # Enable zoom/pan with navigation window
            enable_zoom=True,
            min_zoom=1.0,
            max_zoom=8.0,
            show_nav_window=True,
            nav_window_position="bottom-right",
            nav_window_size=(160, 90),
        )

        # Track current video layer and transport type
        video_state = {
            'layer_id': None,
            'webrtc_id': None,
            'transport': 'websocket',  # 'websocket' or 'webrtc'
        }

        def get_webrtc_bitrate(width: int, height: int) -> int:
            """Get appropriate WebRTC bitrate for resolution.

            Base: 5 Mbps for 360p
            720p: 7.5 Mbps (+50%)
            1080p: 10 Mbps (+100%)
            """
            pixels = width * height
            if pixels >= 1920 * 1080:  # 1080p+
                return 10_000_000
            elif pixels >= 1280 * 720:  # 720p+
                return 7_500_000
            else:  # 360p and below
                return 5_000_000

        def create_video_layer(transport: str = 'websocket'):
            """Create video layer with specified transport."""
            # Remove existing layer
            if video_state['layer_id']:
                view.remove_layer(video_state['layer_id'])
                video_state['layer_id'] = None
            if video_state['webrtc_id']:
                view.remove_webrtc_layer(video_state['webrtc_id'])
                video_state['webrtc_id'] = None

            if transport == 'webrtc' and AIORTC_AVAILABLE:
                # Use WebRTC transport (lower bandwidth)
                # target_fps defaults to source video FPS (auto-detected)
                # Bitrate scales with resolution for better quality
                bitrate = get_webrtc_bitrate(view._width, view._height)
                video_state['webrtc_id'] = view.add_webrtc_layer(
                    stream=video_stream,
                    z_index=0,
                    bitrate=bitrate,
                    name="Video (WebRTC)",
                )
                video_state['transport'] = 'webrtc'
                return None  # WebRTC layer doesn't return a layer object
            else:
                # Use WebSocket transport (default)
                layer = view.add_layer(
                    stream=video_stream,
                    name="Video",
                    fps=60,
                    z_index=0,
                    buffer_size=4,
                    jpeg_quality=85,
                )
                video_state['layer_id'] = layer.id
                video_state['transport'] = 'websocket'
                return layer

        # Add video layer (normal view, no filters) - start with WebRTC if available
        default_transport = 'webrtc' if AIORTC_AVAILABLE else 'websocket'
        video_layer = create_video_layer(default_transport)

        # Capture view dimensions
        DISPLAY_W, DISPLAY_H = view._width, view._height

        # ===========================================
        # LENS 1: Thermal view (false color ellipse)
        # ===========================================
        thermal_lens = create_thermal_lens(
            view=view,
            video_layer=video_layer,
            name="Thermal",
            colormap="hot",
            width=200,
            height=150,
            overscan=32,  # Larger buffer for smooth movement
            mask_feather=16,
            z_index=15,
            initial_x=DISPLAY_W // 2 - 100,  # Centered
            initial_y=DISPLAY_H // 2 - 75,
        )
        thermal_lens.attach(video_stream)

        # ===========================================
        # LENS 2: Magnifier with barrel distortion (circular)
        # ===========================================
        magnifier_lens = create_magnifier_lens(
            view=view,
            video_layer=video_layer,
            name="Magnifier",
            zoom_factor=2.5,
            barrel_strength=0.4,
            width=200,
            height=150,
            overscan=32,  # Larger buffer for smooth movement
            mask_feather=20,
            z_index=14,
            initial_x=DISPLAY_W // 2 - 100,  # Centered
            initial_y=DISPLAY_H // 2 - 75,
        )
        # Note: magnifier is NOT attached initially - only one lens active at a time

        # Track which lens is active
        active_lens = {'current': None}  # 'thermal', 'magnifier', or None

        def set_active_lens(lens_name: str):
            """Switch between lenses - only one can be active at a time."""
            prev = active_lens['current']
            active_lens['current'] = lens_name if lens_name != 'none' else None

            # Detach previous lens
            if prev == 'thermal' and lens_name != 'thermal':
                thermal_lens.detach()
                view.update_layer_position(thermal_lens.id, x=-500, y=-500)
            elif prev == 'magnifier' and lens_name != 'magnifier':
                magnifier_lens.detach()
                view.update_layer_position(magnifier_lens.id, x=-500, y=-500)

            # Attach new lens
            if lens_name == 'thermal' and prev != 'thermal':
                thermal_lens.attach(video_stream)
            elif lens_name == 'magnifier' and prev != 'magnifier':
                magnifier_lens.attach(video_stream)

        # Start with thermal lens active (don't attach magnifier yet)
        thermal_lens.attach(video_stream)
        active_lens['current'] = 'thermal'
        # Move magnifier off-screen initially
        view.update_layer_position(magnifier_lens.id, x=-500, y=-500)

        import numpy as np

        # Multi-output stream: simulates a detector that produces both
        # detection boxes AND a heatmap from a single processing pass
        def render_detector(timestamp: float) -> dict[str, Image]:
            """Render multiple outputs from one processing pass."""
            # Use current view dimensions (dynamic)
            w, h = view._width, view._height

            # Calculate animated position (simulating detected object)
            x_pos = int(w * 0.2 + w * 0.4 * abs(np.sin(timestamp * 0.5)))
            y_pos = int(h * 0.3 + h * 0.2 * abs(np.cos(timestamp * 0.7)))

            # Output 1: Detection boxes
            boxes = np.zeros((h, w, 4), dtype=np.uint8)
            # Draw border (2px wide) - green detection box
            boxes[y_pos:y_pos+2, x_pos:x_pos+150, :] = [0, 255, 0, 200]  # Top
            boxes[y_pos+98:y_pos+100, x_pos:x_pos+150, :] = [0, 255, 0, 200]  # Bottom
            boxes[y_pos:y_pos+100, x_pos:x_pos+2, :] = [0, 255, 0, 200]  # Left
            boxes[y_pos:y_pos+100, x_pos+148:x_pos+150, :] = [0, 255, 0, 200]  # Right
            # Label background
            boxes[max(0, y_pos-20):y_pos, x_pos:x_pos+80, :] = [0, 180, 0, 220]

            # Output 2: Heatmap (semi-transparent colored area showing "attention")
            heatmap = np.zeros((h, w, 4), dtype=np.uint8)
            # Draw a gradient-like blob at the detection center
            cx, cy = x_pos + 75, y_pos + 50
            for dy in range(-40, 41, 4):
                for dx in range(-60, 61, 4):
                    dist = np.sqrt(dx*dx + dy*dy)
                    if dist < 60:
                        intensity = int(150 * (1 - dist/60))
                        py, px = cy + dy, cx + dx
                        if 0 <= py < h and 0 <= px < w:
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
            stream_output="heatmap",
            name="Heatmap",
            fps=10,
            z_index=8,
            buffer_size=2,
            use_png=True,
            depth=0.0,
        )

        # Add boxes layer (on top of heatmap)
        view.add_layer(
            stream=detector_stream,
            stream_output="boxes",
            name="Boxes",
            fps=10,
            z_index=10,
            buffer_size=2,
            use_png=True,
            depth=0.0,
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

        # Handle mouse movement - update SVG crosshair and move active lens
        @view.on_mouse_move
        def handle_mouse(e):
            x, y = int(e.x), int(e.y)

            # Move only the active lens (if any)
            current = active_lens['current']
            if current == 'thermal':
                thermal_lens.move_to(x, y)
                if not video_stream.is_running:
                    thermal_lens.update_from_last_frame()
            elif current == 'magnifier':
                magnifier_lens.move_to(x, y)
                if not video_stream.is_running:
                    magnifier_lens.update_from_last_frame()

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

        # Resolution presets (standard 16:9 resolutions)
        RESOLUTIONS = {
            '360p': (640, 360),
            '720p': (1280, 720),
            '1080p': (1920, 1080),
        }

        def set_resolution(res_name: str):
            """Change display resolution."""
            w, h = RESOLUTIONS[res_name]
            view.set_size(w, h)
            # Recreate video layer if using WebRTC (bitrate scales with resolution)
            if video_state['transport'] == 'webrtc':
                create_video_layer('webrtc')
            # Update SVG viewBox for new dimensions
            view.set_svg(
                f'''
                <svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg">
                    <!-- Crosshair -->
                    <line x1="{{x}}" y1="0" x2="{{x}}" y2="{h}"
                          stroke="rgba(255,255,255,0.5)" stroke-width="1"/>
                    <line x1="0" y1="{{y}}" x2="{w}" y2="{{y}}"
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
                    'x': w // 2,
                    'y': h // 2,
                    'label_x': w // 2 + 10,
                    'label_y': h // 2 + 10,
                    'text_x': w // 2 + 15,
                    'text_y': h // 2 + 26,
                    'coords': f'{w // 2}, {h // 2}',
                }
            )

        # Controls row
        with ui.row().classes("gap-6 items-center"):
            # Resolution selection (display size)
            with ui.row().classes("gap-2 items-center"):
                ui.label("View:").classes("font-bold")
                ui.toggle(
                    ['360p', '720p', '1080p'],
                    value='720p',  # Matches initial 960x540
                    on_change=lambda e: set_resolution(e.value) if e.value else None
                ).classes("bg-gray-700")

            # Transport selection (WebSocket vs WebRTC)
            with ui.row().classes("gap-2 items-center"):
                ui.label("Transport:").classes("font-bold")
                transport_options = ['WebSocket', 'WebRTC'] if AIORTC_AVAILABLE else ['WebSocket']
                default_transport_label = 'WebRTC' if AIORTC_AVAILABLE else 'WebSocket'
                transport_toggle = ui.toggle(
                    transport_options,
                    value=default_transport_label,
                    on_change=lambda e: create_video_layer(e.value.lower()) if e.value else None
                ).classes("bg-gray-700")
                if not AIORTC_AVAILABLE:
                    ui.label("(WebRTC unavailable)").classes("text-gray-500 text-xs")

            # Lens selection
            with ui.row().classes("gap-2 items-center"):
                ui.label("Lens:").classes("font-bold")
                lens_toggle = ui.toggle(
                    ['Thermal', 'Magnifier', 'None'],
                    value='Thermal',
                    on_change=lambda e: set_active_lens(e.value.lower() if e.value else 'none')
                ).classes("bg-gray-700")

        # Control buttons
        with ui.row().classes("gap-2"):
            def do_start():
                video_stream.start()
                view.start()

            def do_pause():
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
        view.start()

        # Info
        with ui.card().classes("w-full max-w-2xl"):
            ui.markdown(f'''
### Controls
- **Transport toggle**: Switch between WebSocket (~40 Mbps) and WebRTC (~5 Mbps)
- **Lens toggle**: Switch between Thermal, Magnifier, or None
- **Mouse move**: Crosshair + active lens follows cursor
- **Mouse wheel**: Zoom in/out (centered on cursor)
- **Drag**: Pan when zoomed in
- **Double-click**: Reset zoom to 1x
- **Nav window**: Click to jump to position (shown when zoomed)
- **Start/Stop**: Control playback

### Video Source
`{video_file}`

### Lenses (selectable)
1. **Thermal**: FalseColor "hot" colormap visualization
2. **Magnifier**: 2.5x zoom with barrel distortion effect

### Layers (bottom to top)
1. **Video** (z=0): VideoStream at 60fps (WebSocket or WebRTC)
2. **Heatmap** (z=8): Multi-output stream at 10fps
3. **Detection Boxes** (z=10): Multi-output stream at 10fps
4. **Magnifier Lens** (z=14): Zoomed + barrel distorted view
5. **Thermal Lens** (z=15): False color thermal view
6. **SVG Overlay** (topmost): Crosshair with coordinates

### Transport Modes
- **WebSocket**: Base64 JPEG frames, ~40-50 Mbps, full features
- **WebRTC**: H.264/VP8 encoded, ~2-5 Mbps, lower latency

### Easy Lens Creation
```python
from imagestag.components.stream_view import (
    create_thermal_lens,
    create_magnifier_lens,
)

# Create a thermal lens
thermal = create_thermal_lens(
    view=view,
    video_layer=video_layer,
    colormap="hot",
)
thermal.attach(video_stream)

# Create a magnifier lens
magnifier = create_magnifier_lens(
    view=view,
    video_layer=video_layer,
    zoom_factor=2.5,
    barrel_strength=0.4,
)
magnifier.attach(video_stream)

# Move lenses on mouse move
@view.on_mouse_move
def on_mouse(e):
    thermal.move_to(e.x, e.y)
    magnifier.move_to(e.x, e.y)
```

### WebRTC Transport
```python
from imagestag.components.stream_view import (
    StreamView,
    VideoStream,
    AIORTC_AVAILABLE,
)

if AIORTC_AVAILABLE:
    # Use WebRTC for low-bandwidth video layer
    view.add_webrtc_layer(
        stream=video_stream,
        z_index=0,
        bitrate=5_000_000,  # 5 Mbps target
        name="Video (WebRTC)",
    )
else:
    # Fallback to WebSocket
    view.add_layer(stream=video_stream, fps=60)
```
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
