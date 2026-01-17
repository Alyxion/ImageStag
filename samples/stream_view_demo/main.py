"""StreamView Demo - High-performance video streaming with NiceGUI.

This demo showcases the StreamView component with:
- 1080p video playback at 60fps target
- Multi-layer compositing (video, heatmap, detection boxes)
- SVG overlay with mouse tracking
- Real-time performance metrics
- WebSocket and WebRTC transport options

Usage:
    python samples/stream_view_demo/main.py

    # Or with custom video:
    python samples/stream_view_demo/main.py /path/to/video.mp4

Requirements:
    - OpenCV (cv2) for video playback
    - The test video in tmp/media/ (run scripts/download_test_media.py)
"""

import sys
from pathlib import Path

from nicegui import ui

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from imagestag import Image, Canvas
from imagestag.components.stream_view import (
    StreamView,
    VideoStream,
    CustomStream,
    AIORTC_AVAILABLE,
)
from imagestag.components.shared import format_time

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

        # Create StreamView component wrapped in a container for overlay controls
        # Add fullscreen styles - when fullscreen, fill the screen and center content
        with ui.element('div').classes('relative').style('''
            background: black;
        ''') as view_wrapper:
            # Add fullscreen-specific CSS
            ui.add_head_html(f'''
                <style>
                    #c{view_wrapper.id}:fullscreen {{
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        width: 100vw;
                        height: 100vh;
                        background: black;
                    }}
                    #c{view_wrapper.id}:fullscreen .stream-view-container {{
                        max-width: 100vw;
                        max-height: 100vh;
                    }}
                    /* In fullscreen, position nav window in the black bar on the right, outside the video */
                    #c{view_wrapper.id}:fullscreen .stream-view-nav {{
                        position: fixed !important;
                        right: 20px !important;
                        bottom: 80px !important;
                        top: auto !important;
                        z-index: 9999;
                        /* Scale up to 2x when there's extra horizontal space (ultrawide monitors) */
                        transform: scale(1);
                        transform-origin: bottom right;
                    }}
                    /* On ultrawide screens (21:9 and wider), make nav window larger */
                    @media (min-aspect-ratio: 2/1) {{
                        #c{view_wrapper.id}:fullscreen .stream-view-nav {{
                            transform: scale(1.5);
                        }}
                    }}
                    @media (min-aspect-ratio: 21/9) {{
                        #c{view_wrapper.id}:fullscreen .stream-view-nav {{
                            transform: scale(2);
                        }}
                    }}
                </style>
            ''')
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
            'transport': 'webrtc',  # 'websocket' or 'webrtc'
            'layer': None,  # The actual layer object (None for WebRTC)
            'bitrate_mbps': 4.0,  # Default 4 Mbit for good quality
            'quality_label': None,  # Reference to quality display label
            'quality_row': None,  # Reference to quality row in settings for visibility
        }

        # Quality presets: value in Mbps -> display label
        QUALITY_PRESETS = {
            0.5: '360p',
            1.0: '480p',
            2.0: '720p',
            4.0: '1080p',
            8.0: '1440p',
            16.0: '4K',
        }

        def get_quality_label(mbps: float) -> str:
            """Get display label for bitrate."""
            return QUALITY_PRESETS.get(mbps, f'{mbps}M')

        def get_webrtc_bitrate() -> int:
            """Get WebRTC bitrate from quality setting."""
            return int(video_state['bitrate_mbps'] * 1_000_000)

        def update_quality_visibility():
            """Show/hide quality option based on transport."""
            quality_row = video_state.get('quality_row')
            if quality_row:
                if video_state['transport'] == 'webrtc':
                    quality_row.classes(remove='hidden')
                else:
                    quality_row.classes(add='hidden')

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
                # Use WebRTC transport
                # Bitrate controlled by quality setting in nav bar
                bitrate = get_webrtc_bitrate()
                video_state['webrtc_id'] = view.add_webrtc_layer(
                    stream=video_stream,
                    z_index=0,
                    bitrate=bitrate,
                    name="Video (WebRTC)",
                )
                video_state['transport'] = 'webrtc'
                video_state['layer'] = None  # WebRTC layer doesn't return a layer object
                update_quality_visibility()
                return None
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
                video_state['layer'] = layer  # Store actual layer object for derived layers
                update_quality_visibility()
                return layer

        # Add video layer (normal view, no filters) - default to WebRTC for efficiency
        default_transport = 'webrtc' if AIORTC_AVAILABLE else 'websocket'
        video_layer = create_video_layer(default_transport)

        # Track current view dimensions (updated on resize)
        display_state = {'width': view._width, 'height': view._height}
        DISPLAY_W, DISPLAY_H = view._width, view._height

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
        # Using fullscreen_scale="screen" for sharper rendering in fullscreen
        view.add_layer(
            stream=detector_stream,
            stream_output="heatmap",
            name="Heatmap",
            fps=10,
            z_index=8,
            buffer_size=2,
            use_png=True,
            depth=0.0,
            fullscreen_scale="screen",  # Render at screen resolution for sharpness
        )

        # Add boxes layer (on top of heatmap)
        # Using fullscreen_scale="screen" for sharper lines in fullscreen
        view.add_layer(
            stream=detector_stream,
            stream_output="boxes",
            name="Boxes",
            fps=10,
            z_index=10,
            buffer_size=2,
            use_png=True,
            depth=0.0,
            fullscreen_scale="screen",  # Render at screen resolution for sharpness
        )

        # Set up SVG overlay with crosshair (topmost)
        def setup_svg_overlay(w: int, h: int):
            """Create SVG overlay with proper dimensions."""
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

        # Initial SVG setup
        setup_svg_overlay(DISPLAY_W, DISPLAY_H)

        # Handle size changes (e.g., fullscreen) - update SVG viewBox
        def handle_size_change(e):
            args = e.args
            new_w = args.get('width', display_state['width'])
            new_h = args.get('height', display_state['height'])
            if new_w != display_state['width'] or new_h != display_state['height']:
                display_state['width'] = new_w
                display_state['height'] = new_h
                # Recreate SVG with new dimensions
                setup_svg_overlay(new_w, new_h)

        view.on('size-changed', handle_size_change)

        # Handle mouse movement - update SVG crosshair
        @view.on_mouse_move
        def handle_mouse(e):
            x, y = int(e.x), int(e.y)
            w, h = display_state['width'], display_state['height']

            # Update SVG crosshair - use current dimensions for bounds
            label_x = min(max(x + 10, 5), w - 105)  # 100px width + 5px margin
            label_y = min(max(y + 10, 5), h - 29)   # 24px height + 5px margin
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
            # Recreate video layer if using WebRTC (encoder needs reinit for new resolution)
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

            # Quality selection (WebRTC bitrate in Mbit)
            with ui.row().classes("gap-2 items-center"):
                ui.label("Quality:").classes("font-bold")

                def set_quality(mbps: float, update_action_bar: bool = True):
                    """Set WebRTC bitrate and recreate layer if using WebRTC."""
                    video_state['bitrate_mbps'] = mbps
                    if video_state['transport'] == 'webrtc':
                        create_video_layer('webrtc')
                    # Update action bar quality label if it exists
                    if update_action_bar and video_state['quality_label']:
                        video_state['quality_label'].set_text(get_quality_label(mbps))

                quality_options = ['0.5', '1', '2', '4', '8', '16']
                quality_toggle = ui.toggle(
                    quality_options,
                    value='4',
                    on_change=lambda e: set_quality(float(e.value)) if e.value else None
                ).classes("bg-gray-700")
                ui.label("Mbit").classes("text-xs text-gray-400")


        # Playback state
        SPEED_OPTIONS = [0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 4.0]
        control_bar_state = {'pinned': False, 'visible': True, 'hide_timer': None}

        # Video controls overlay - positioned at bottom of video
        with view_wrapper:
            # Overlay control bar at bottom (auto-hide by default)
            controls_overlay = ui.element('div').classes(
                'absolute bottom-0 left-0 right-0 '
                'bg-black/70 backdrop-blur-sm '
                'transition-opacity duration-300 '
                'py-3 px-3 z-50'
            ).style('pointer-events: auto')

            def show_controls():
                """Show controls and reset hide timer."""
                control_bar_state['visible'] = True
                controls_overlay.classes(remove='opacity-0')
                # Reset hide timer
                if control_bar_state['hide_timer']:
                    control_bar_state['hide_timer'].cancel()
                if not control_bar_state['pinned']:
                    control_bar_state['hide_timer'] = ui.timer(
                        3.0,
                        lambda: hide_controls(),
                        once=True
                    )

            def hide_controls():
                """Hide controls if not pinned."""
                if not control_bar_state['pinned']:
                    control_bar_state['visible'] = False
                    controls_overlay.classes(add='opacity-0')

            def toggle_pin():
                """Toggle pinned state."""
                control_bar_state['pinned'] = not control_bar_state['pinned']
                if control_bar_state['pinned']:
                    # Rotate pin 45° and make it blue/bright when pinned
                    pin_btn.props("icon=push_pin color=primary")
                    pin_btn.classes(remove='opacity-50')
                    pin_btn.classes(add='opacity-100')
                    pin_btn.style('transform: rotate(45deg); transition: transform 0.2s ease;')
                    if control_bar_state['hide_timer']:
                        control_bar_state['hide_timer'].cancel()
                else:
                    # Reset rotation and make subtle when unpinned
                    pin_btn.props("icon=push_pin color=white")
                    pin_btn.classes(remove='opacity-100')
                    pin_btn.classes(add='opacity-50')
                    pin_btn.style('transform: rotate(0deg); transition: transform 0.2s ease;')
                    show_controls()  # Reset hide timer

            # Show on hover/interaction with control bar
            controls_overlay.on('mouseenter', lambda: show_controls())
            controls_overlay.on('mousemove', lambda: show_controls())

        # Show controls when interacting with the video area
        view_wrapper.on('click', lambda: show_controls())
        view_wrapper.on('mousemove', lambda: show_controls())

        with controls_overlay:
            # Single row: controls | progress bar | time | settings | fullscreen
            with ui.row().classes("w-full items-center gap-2 flex-nowrap"):
                    # Pin button (smaller, more subtle, rotates when pinned)
                    pin_btn = ui.button(icon="push_pin", on_click=toggle_pin).props("flat dense round size=xs").classes("opacity-50 hover:opacity-100").style('transition: transform 0.2s ease;')
                    pin_btn.tooltip("Pin controls")

                    # Play/Pause button
                    play_btn = ui.button(icon="play_arrow").props("flat dense color=white")

                    # Step back 10s
                    ui.button(icon="replay_10", on_click=lambda: video_stream.seek_to(max(0, video_stream.current_position - 10))).props("flat dense color=white size=sm")

                    # Step forward 10s
                    ui.button(icon="forward_10", on_click=lambda: video_stream.seek_to(min(video_stream.duration, video_stream.current_position + 10))).props("flat dense color=white size=sm")

                    # Progress slider - takes remaining space
                    def on_slider_seek(e):
                        progress = e.value / 100
                        video_stream.seek_to(progress * video_stream.duration)

                    progress_slider = ui.slider(
                        min=0, max=100, value=0,
                        on_change=on_slider_seek
                    ).classes("flex-grow").props("color=white")

                    # Time display (current / duration) - right of progress bar
                    time_label = ui.label("00:00 / 00:00").classes("font-mono text-xs text-white whitespace-nowrap")

                    # Bandwidth display (updates from JS stats)
                    bandwidth_label = ui.label("").classes("font-mono text-xs text-gray-400 whitespace-nowrap")

                    async def update_bandwidth_display():
                        """Fetch bandwidth from JS and update display."""
                        try:
                            result = await ui.run_javascript(f'''
                                (function() {{
                                    const el = getElement("{view.id}");
                                    if (el && el.$refs && el.$refs.viewEl) {{
                                        const viewEl = el.$refs.viewEl;
                                        // Get total bandwidth from layers
                                        let totalBw = 0;
                                        if (viewEl.layerLatencies) {{
                                            for (const lid in viewEl.layerLatencies) {{
                                                totalBw += viewEl.layerLatencies[lid].bandwidth || 0;
                                            }}
                                        }}
                                        // Add WebRTC bandwidth
                                        if (viewEl.webrtcStats) {{
                                            for (const lid in viewEl.webrtcStats) {{
                                                totalBw += viewEl.webrtcStats[lid].bitrate || 0;
                                            }}
                                        }}
                                        return totalBw;
                                    }}
                                    return 0;
                                }})()
                            ''', timeout=1.0)
                            if result and result > 0:
                                if result >= 1_000_000:
                                    bandwidth_label.set_text(f"{result / 1_000_000:.1f} Mbps")
                                elif result >= 1000:
                                    bandwidth_label.set_text(f"{result / 1000:.0f} kbps")
                                else:
                                    bandwidth_label.set_text(f"{result:.0f} bps")
                            else:
                                bandwidth_label.set_text("")
                        except Exception:
                            pass  # Ignore errors silently

                    # Update bandwidth periodically
                    ui.timer(1.0, update_bandwidth_display)

                    # Settings state for popup management
                    settings_state = {
                        'main_visible': False,
                        'speed_visible': False,
                        'quality_visible': False,
                        'current_speed': 1.0,
                    }

                    # Settings button (gear icon) with YouTube-style popup
                    with ui.element('div').classes('relative') as settings_container:
                        settings_btn = ui.button(icon="settings").props("flat dense color=white size=sm")
                        settings_btn.tooltip("Settings")

                        # Main settings popup
                        with ui.element('div').classes('absolute bottom-full right-0 mb-2 bg-gray-900/95 rounded-lg shadow-xl').style('display: none; min-width: 220px; z-index: 1000;') as settings_popup:

                            # Speed row - opens speed submenu
                            with ui.row().classes("w-full justify-between items-center hover:bg-gray-700 px-4 py-3 cursor-pointer rounded-t-lg") as speed_row:
                                with ui.row().classes("items-center gap-3"):
                                    ui.icon("speed").classes("text-white text-lg")
                                    ui.label("Playback speed").classes("text-white text-sm")
                                speed_value_display = ui.label("Normal").classes("text-gray-400 text-sm")

                            # Quality row - opens quality submenu (only for WebRTC)
                            with ui.row().classes("w-full justify-between items-center hover:bg-gray-700 px-4 py-3 cursor-pointer rounded-b-lg") as quality_row:
                                video_state['quality_row'] = quality_row  # Store for visibility updates
                                with ui.row().classes("items-center gap-3"):
                                    ui.icon("tune").classes("text-white text-lg")
                                    ui.label("Quality").classes("text-white text-sm")
                                quality_value_display = ui.label(get_quality_label(video_state['bitrate_mbps'])).classes("text-gray-400 text-sm")
                                video_state['quality_label'] = quality_value_display

                        # Speed submenu popup
                        speed_checkmarks = {}  # Store checkmark references
                        with ui.element('div').classes('absolute bottom-full right-0 mb-2 bg-gray-900/95 rounded-lg shadow-xl').style('display: none; min-width: 200px; z-index: 1001;') as speed_submenu:
                            # Back button
                            with ui.row().classes("w-full items-center hover:bg-gray-700 px-3 py-2 cursor-pointer border-b border-gray-700") as speed_back:
                                ui.icon("arrow_back").classes("text-white text-sm mr-2")
                                ui.label("Playback speed").classes("text-white text-sm font-semibold")

                            # Speed options (0.1x to 16x)
                            speed_presets = [0.1, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 4.0, 8.0, 16.0]
                            for preset in speed_presets:
                                label_text = "Normal" if preset == 1.0 else f"{preset}x"

                                def make_speed_handler(s, lbl, checks):
                                    def handler():
                                        video_stream.playback_speed = s
                                        settings_state['current_speed'] = s
                                        speed_value_display.set_text(lbl)
                                        # Update checkmarks
                                        for spd, chk in checks.items():
                                            if spd == s:
                                                chk.classes(remove='invisible')
                                            else:
                                                chk.classes(add='invisible')
                                        # Close submenus
                                        speed_submenu.style('display: none')
                                        settings_popup.style('display: none')
                                        settings_state['main_visible'] = False
                                        settings_state['speed_visible'] = False
                                    return handler

                                with ui.row().classes("w-full justify-between items-center hover:bg-gray-700 px-4 py-2 cursor-pointer").on('click', make_speed_handler(preset, label_text, speed_checkmarks)):
                                    ui.label(label_text).classes("text-white text-sm")
                                    # Checkmark - visible only for current speed (1.0 = default)
                                    check_icon = ui.icon("check").classes("text-blue-400 text-sm")
                                    if preset != 1.0:
                                        check_icon.classes(add='invisible')
                                    speed_checkmarks[preset] = check_icon

                        # Quality submenu popup
                        quality_checkmarks = {}  # Store checkmark references
                        with ui.element('div').classes('absolute bottom-full right-0 mb-2 bg-gray-900/95 rounded-lg shadow-xl').style('display: none; min-width: 200px; z-index: 1001;') as quality_submenu:
                            # Back button
                            with ui.row().classes("w-full items-center hover:bg-gray-700 px-3 py-2 cursor-pointer border-b border-gray-700") as quality_back:
                                ui.icon("arrow_back").classes("text-white text-sm mr-2")
                                ui.label("Quality").classes("text-white text-sm font-semibold")

                            # Quality options
                            for mbps in [16.0, 8.0, 4.0, 2.0, 1.0, 0.5]:
                                label = get_quality_label(mbps)
                                bitrate_text = f"{mbps}M" if mbps >= 1 else f"{int(mbps * 1000)}K"

                                def make_quality_handler(m, l, checks):
                                    def handler():
                                        set_quality(m)
                                        quality_value_display.set_text(l)
                                        # Update checkmarks
                                        for qual, chk in checks.items():
                                            if qual == m:
                                                chk.classes(remove='invisible')
                                            else:
                                                chk.classes(add='invisible')
                                        # Close submenus
                                        quality_submenu.style('display: none')
                                        settings_popup.style('display: none')
                                        settings_state['main_visible'] = False
                                        settings_state['quality_visible'] = False
                                        # Update nav bar toggle
                                        quality_toggle.set_value(str(m) if m >= 1 else f'{m}')
                                    return handler

                                with ui.row().classes("w-full justify-between items-center hover:bg-gray-700 px-4 py-2 cursor-pointer").on('click', make_quality_handler(mbps, label, quality_checkmarks)):
                                    with ui.row().classes("items-center gap-2"):
                                        ui.label(label).classes("text-white text-sm")
                                        ui.label(bitrate_text).classes("text-gray-400 text-xs")
                                    # Checkmark - visible only for current quality (4.0 = default)
                                    check_icon = ui.icon("check").classes("text-blue-400 text-sm")
                                    if mbps != video_state['bitrate_mbps']:
                                        check_icon.classes(add='invisible')
                                    quality_checkmarks[mbps] = check_icon

                        # Event handlers for popup navigation
                        def show_main_settings():
                            settings_popup.style('display: block')
                            speed_submenu.style('display: none')
                            quality_submenu.style('display: none')
                            settings_state['main_visible'] = True
                            settings_state['speed_visible'] = False
                            settings_state['quality_visible'] = False

                        def show_speed_submenu():
                            settings_popup.style('display: none')
                            speed_submenu.style('display: block')
                            settings_state['speed_visible'] = True

                        def show_quality_submenu():
                            settings_popup.style('display: none')
                            quality_submenu.style('display: block')
                            settings_state['quality_visible'] = True

                        def close_all_popups():
                            settings_popup.style('display: none')
                            speed_submenu.style('display: none')
                            quality_submenu.style('display: none')
                            settings_state['main_visible'] = False
                            settings_state['speed_visible'] = False
                            settings_state['quality_visible'] = False

                        # Wire up click handlers
                        settings_btn.on('click', lambda: show_main_settings() if not settings_state['main_visible'] else close_all_popups())
                        speed_row.on('click', show_speed_submenu)
                        quality_row.on('click', show_quality_submenu)
                        speed_back.on('click', show_main_settings)
                        quality_back.on('click', show_main_settings)

                        # Close popups when clicking outside
                        async def setup_settings_popup_close():
                            container_id = f'c{settings_container.id}'
                            await ui.run_javascript(f'''
                                document.addEventListener('click', (e) => {{
                                    const container = document.getElementById("{container_id}");
                                    if (container && !container.contains(e.target)) {{
                                        // Close all popups by setting display none on all child divs with position absolute
                                        container.querySelectorAll('div[style*="position"]').forEach(el => {{
                                            if (el.style.display === 'block') el.style.display = 'none';
                                        }});
                                    }}
                                }});
                            ''')
                        ui.timer(0.5, setup_settings_popup_close, once=True)

                    # Initial visibility check for quality row
                    ui.timer(0.1, update_quality_visibility, once=True)

                    # Fullscreen toggle button - targets only the StreamView wrapper
                    fullscreen_state = {
                        'active': False,
                        'original_width': 1280,
                        'original_height': 720,
                        'video_aspect': video_stream.aspect_ratio,  # Use actual video aspect ratio
                    }

                    async def toggle_fullscreen():
                        """Toggle fullscreen on just the StreamView container."""
                        wrapper_id = f'c{view_wrapper.id}'
                        if fullscreen_state['active']:
                            await ui.run_javascript('document.exitFullscreen()')
                        else:
                            # Store current size before going fullscreen
                            fullscreen_state['original_width'] = view._width
                            fullscreen_state['original_height'] = view._height
                            await ui.run_javascript(f'''
                                const el = document.getElementById("{wrapper_id}");
                                if (el) el.requestFullscreen();
                            ''')

                    fullscreen_btn = ui.button(icon="fullscreen", on_click=toggle_fullscreen).props("flat dense color=white size=sm")
                    fullscreen_btn.tooltip("Toggle fullscreen")

                    # Listen for fullscreen changes and resize view directly in JS
                    async def setup_fullscreen_listener():
                        wrapper_id = f'c{view_wrapper.id}'
                        view_id = view.id
                        aspect = fullscreen_state['video_aspect']
                        orig_w = fullscreen_state['original_width']
                        orig_h = fullscreen_state['original_height']
                        btn_id = fullscreen_btn.id
                        await ui.run_javascript(f'''
                            (function() {{
                                const aspect = {aspect};
                                const origW = {orig_w};
                                const origH = {orig_h};

                                document.addEventListener('fullscreenchange', () => {{
                                    const wrapper = document.getElementById("{wrapper_id}");
                                    const isFullscreen = document.fullscreenElement === wrapper;

                                    // Delay to allow browser to complete fullscreen transition
                                    setTimeout(() => {{
                                        const screenW = window.innerWidth;
                                        const screenH = window.innerHeight;

                                        // Get the StreamView component
                                        const viewEl = getElement("{view_id}");
                                        if (!viewEl) {{
                                            console.error('[Fullscreen] Could not find view element');
                                            return;
                                        }}

                                        if (isFullscreen) {{
                                            // Calculate size to fill screen while maintaining aspect ratio
                                            let newW, newH;
                                            if (screenW / screenH > aspect) {{
                                                // Height-constrained: fill height
                                                newH = screenH;
                                                newW = Math.round(newH * aspect);
                                            }} else {{
                                                // Width-constrained: fill width
                                                newW = screenW;
                                                newH = Math.round(newW / aspect);
                                            }}
                                            console.log('[Fullscreen] Resizing to', newW, 'x', newH, '(screen:', screenW, 'x', screenH, ')');
                                            viewEl.setSize(newW, newH);
                                        }} else {{
                                            // Restore original size
                                            console.log('[Fullscreen] Restoring to', origW, 'x', origH);
                                            viewEl.setSize(origW, origH);
                                        }}

                                        // Update button icon
                                        const btn = getElement("{btn_id}");
                                        if (btn) {{
                                            btn.$props.icon = isFullscreen ? 'fullscreen_exit' : 'fullscreen';
                                        }}
                                    }}, 100);
                                }});
                            }})();
                        ''')

                    ui.timer(0.5, setup_fullscreen_listener, once=True)

        # Start with controls visible, then hide after delay
        ui.timer(3.0, lambda: hide_controls(), once=True)

        # Play/Pause toggle
        def toggle_play():
            if video_stream.is_paused:
                video_stream.resume()
                view.start()
                play_btn.props("icon=pause")
            elif video_stream.is_running:
                video_stream.pause()
                play_btn.props("icon=play_arrow")
            else:
                video_stream.start()
                view.start()
                play_btn.props("icon=pause")

        play_btn.on_click(toggle_play)

        # Click on video area to toggle play/pause
        @view.on_mouse_click
        def handle_click(e):
            toggle_play()

        # Update progress bar periodically (without triggering on_change)
        def update_progress():
            if video_stream.duration > 0:
                current = video_stream.current_position
                total = video_stream.duration
                time_label.set_text(f"{format_time(current)} / {format_time(total)}")
                # Update slider value directly to avoid triggering on_change
                progress_slider._props['model-value'] = (current / total) * 100
                progress_slider.update()

                # Sync speed display in settings popup with actual stream speed
                actual_speed = video_stream.playback_speed
                speed_text = "Normal" if actual_speed == 1.0 else f"{actual_speed}x"
                speed_value_display.set_text(speed_text)

                # Update play button state
                if video_stream.is_running and not video_stream.is_paused:
                    play_btn.props("icon=pause")
                else:
                    play_btn.props("icon=play_arrow")

        ui.timer(0.25, update_progress)

        # Start playing automatically
        video_stream.start()
        view.start()

        # Info
        with ui.card().classes("w-full max-w-2xl"):
            ui.markdown(f'''
### Controls
- **Transport toggle**: Switch between WebSocket (~40 Mbps) and WebRTC (~5 Mbps)
- **Mouse move**: Crosshair follows cursor
- **Mouse wheel**: Zoom in/out (centered on cursor)
- **Drag**: Pan when zoomed in
- **Double-click**: Reset zoom to 1x
- **Nav window**: Click to jump to position (shown when zoomed)
- **Start/Stop**: Control playback

### Video Source
`{video_file}`

### Layers (bottom to top)
1. **Video** (z=0): VideoStream at 60fps (WebSocket or WebRTC)
2. **Heatmap** (z=8): Multi-output stream at 10fps
3. **Detection Boxes** (z=10): Multi-output stream at 10fps
4. **SVG Overlay** (topmost): Crosshair with coordinates

### Transport Modes
- **WebSocket**: Base64 JPEG frames, ~40-50 Mbps, full features
- **WebRTC**: H.264/VP8 encoded, ~2-5 Mbps, lower latency

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
