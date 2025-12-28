"""ImageStag Interactive Demo - Live Preview with Non-Destructive Editing.

Run with: poetry run python samples/image_demo/main.py
"""

import base64
from dataclasses import dataclass, field

from nicegui import ui

from imagestag import Image
from imagestag.samples import stag


@dataclass
class ImageState:
    """State management with live, non-destructive filter pipeline."""

    original: Image | None = None

    # Display properties (bound to UI)
    info_text: str = 'Load an image to begin'
    image_src: str = ''

    # Filter settings (all bound to controls)
    scale: int = 100  # percentage
    pixel_format: str = 'RGB'
    channel: str = 'All'
    show_jpeg: bool = False
    jpeg_quality: int = 90
    framework: str = 'PIL'

    def load_sample(self):
        """Load the sample stag image."""
        self.original = stag()
        self.update_preview()

    async def upload(self, e):
        """Handle image upload."""
        content = await e.file.read()
        self.original = Image(content)
        self.update_preview()

    def update_preview(self):
        """Apply filter pipeline and update preview. Called on any setting change."""
        if self.original is None:
            self.info_text = 'Load an image to begin'
            self.image_src = ''
            return

        # Start from original - non-destructive!
        img = self.original.copy()

        # 1. Apply scale
        if self.scale != 100:
            factor = self.scale / 100
            img = img.resized_ext(factor=factor)

        # 2. Apply pixel format conversion
        if self.pixel_format != 'RGB':
            img.convert(self.pixel_format)

        # 3. Extract channel if selected
        if self.channel != 'All':
            channel_map = {'R': 0, 'G': 1, 'B': 2, 'H': 0, 'S': 1, 'V': 2}
            if self.channel in channel_map:
                channels = img.split()
                idx = channel_map[self.channel]
                if idx < len(channels):
                    img = Image(channels[idx])

        # 4. Convert framework
        if self.framework == 'RAW':
            img.convert_to_raw()
        else:
            img.convert_to_pil()

        # 5. Encode for display (with optional JPEG compression preview)
        if self.show_jpeg:
            # Show JPEG compression artifacts
            jpeg_data = img.to_jpeg(quality=self.jpeg_quality)
            self.image_src = f'data:image/jpeg;base64,{base64.b64encode(jpeg_data).decode()}'
            file_size = len(jpeg_data) / 1024
            compression_info = f' | JPEG: {file_size:.1f} KB (Q{self.jpeg_quality})'
        else:
            png_data = img.to_png()
            self.image_src = f'data:image/png;base64,{base64.b64encode(png_data).decode()}'
            compression_info = ''

        # Update info text
        fmt_name = ''.join(img.pixel_format.band_names)
        self.info_text = (
            f'{img.width}x{img.height} | {fmt_name} | {img.framework.name}{compression_info}'
        )


def create_toggle_row(label: str, options: list | dict, state: ImageState, attr: str):
    """Helper to create a labeled toggle row with live update binding."""
    with ui.row().classes('items-center gap-2'):
        ui.label(label).classes('w-24 font-medium')
        toggle = ui.toggle(options).bind_value(state, attr)
        toggle.on_value_change(lambda: state.update_preview())
    return toggle


def create_slider_row(label: str, min_val: int, max_val: int, state: ImageState, attr: str, suffix: str = ''):
    """Helper to create a labeled slider with live update."""
    with ui.row().classes('items-center gap-2 w-full'):
        ui.label(label).classes('w-24 font-medium')
        slider = ui.slider(min=min_val, max=max_val).bind_value(state, attr).classes('flex-1')
        value_label = ui.label().classes('w-16 text-right')
        value_label.bind_text_from(state, attr, lambda v: f'{v}{suffix}')
        slider.on_value_change(lambda: state.update_preview())
    return slider


@ui.page('/')
def index():
    """Main demo page with live preview."""
    state = ImageState()

    # Channel toggle reference for dynamic updates
    channel_toggle = None

    def update_channel_options():
        """Update channel toggle options based on pixel format."""
        nonlocal channel_toggle
        if channel_toggle is None:
            return

        if state.pixel_format == 'HSV':
            channel_toggle.options = ['H', 'S', 'V']
            if state.channel not in ['H', 'S', 'V']:
                state.channel = 'H'
        elif state.pixel_format == 'GRAY':
            channel_toggle.options = ['All']
            state.channel = 'All'
        else:  # RGB, RGBA
            channel_toggle.options = ['All', 'R', 'G', 'B']
            if state.channel not in ['All', 'R', 'G', 'B']:
                state.channel = 'All'

        channel_toggle.update()
        state.update_preview()

    with ui.header().classes('bg-primary'):
        ui.label('ImageStag Live Demo').classes('text-xl font-bold')
        ui.space()
        ui.label().bind_text(state, 'info_text').classes('text-sm opacity-90')

    with ui.row().classes('w-full max-w-7xl mx-auto p-4 gap-4'):
        # Left panel - Controls
        with ui.card().classes('w-96'):
            # Load section
            ui.label('Source Image').classes('text-lg font-semibold')
            with ui.row().classes('gap-2 w-full'):
                ui.button('Reset to Sample', on_click=state.load_sample, icon='refresh')
            ui.upload(
                on_upload=state.upload,
                auto_upload=True,
                label='Drop image here or click to upload'
            ).classes('w-full').props('accept=image/*')

            ui.separator().classes('my-4')

            # Transform section
            ui.label('Transform').classes('text-lg font-semibold')
            create_slider_row('Scale', 25, 200, state, 'scale', '%')

            ui.separator().classes('my-4')

            # Color section
            ui.label('Color').classes('text-lg font-semibold')

            # Format toggle with callback to update channel options
            with ui.row().classes('items-center gap-2'):
                ui.label('Format').classes('w-24 font-medium')
                format_toggle = ui.toggle(['RGB', 'RGBA', 'GRAY', 'HSV']).bind_value(state, 'pixel_format')
                format_toggle.on_value_change(update_channel_options)

            # Channel selector - options change based on format
            with ui.row().classes('items-center gap-2'):
                ui.label('Channel').classes('w-24 font-medium')
                channel_toggle = ui.toggle(['All', 'R', 'G', 'B']).bind_value(state, 'channel')
                channel_toggle.on_value_change(lambda: state.update_preview())

            ui.separator().classes('my-4')

            # Framework section
            ui.label('Storage').classes('text-lg font-semibold')
            create_toggle_row('Framework', ['PIL', 'RAW'], state, 'framework')

            ui.separator().classes('my-4')

            # Compression preview section
            ui.label('Compression Preview').classes('text-lg font-semibold')
            with ui.row().classes('items-center gap-2'):
                ui.label('Show JPEG').classes('w-24 font-medium')
                jpeg_switch = ui.switch().bind_value(state, 'show_jpeg')
                jpeg_switch.on_value_change(lambda: state.update_preview())

            create_slider_row('Quality', 1, 100, state, 'jpeg_quality', '')

            ui.separator().classes('my-4')

            # Download section
            ui.label('Export').classes('text-lg font-semibold')
            with ui.row().classes('gap-2'):
                ui.button(
                    'PNG',
                    icon='download',
                    on_click=lambda: ui.download(state.original.to_png(), 'image.png')
                    if state.original else None,
                )
                ui.button(
                    'JPEG',
                    icon='download',
                    on_click=lambda: ui.download(
                        state.original.to_jpeg(quality=state.jpeg_quality), 'image.jpg'
                    ) if state.original else None,
                )

        # Right panel - Live preview
        with ui.card().classes('flex-1 min-h-[600px]'):
            ui.label('Live Preview').classes('text-lg font-semibold mb-2')

            with ui.column().classes('w-full h-full items-center justify-center'):
                ui.image().bind_source(state, 'image_src').classes(
                    'max-w-full max-h-[550px] object-contain'
                ).style('image-rendering: pixelated')

    # Auto-load sample image on page load
    state.load_sample()


if __name__ in {'__main__', '__mp_main__'}:
    ui.run(title='ImageStag Live Demo', port=8080, show=False)
