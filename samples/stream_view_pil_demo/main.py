"""Demo: StreamViewPil with MultiOutputStream.

Demonstrates:
- Multi-output streams rendering to multiple layers
- Background thread rendering
- Different layer formats (jpeg for background, png for overlay)
- PIL-based drawing

Usage:
    poetry run python samples/stream_view_pil_demo/main.py
"""

from pathlib import Path

from PIL import Image as PILImage, ImageDraw, ImageFont

from imagestag import (
    Image,
    StreamViewPil,
    MultiOutputStream,
    RenderContext,
    LayerConfig,
)

# Output directory (in project's tmp folder, which is gitignored)
OUTPUT_DIR = Path(__file__).parent.parent.parent / "tmp" / "stream_view_pil_demo"


class SceneRenderer(MultiOutputStream):
    """Multi-output renderer with background and overlay layers."""

    # Define output layers with their configurations
    outputs = {
        "background": LayerConfig(format="jpeg", quality=60, z_index=0),
        "overlay": LayerConfig(format="png", z_index=1),
    }

    def __init__(self, width: int, height: int, target_fps: float = 30.0):
        super().__init__(target_fps=target_fps)
        self.width = width
        self.height = height

    def render(self, ctx: RenderContext) -> None:
        """Render scene to multiple layers."""
        t = ctx.timestamp

        # Render background (gradient) - will be jpeg compressed
        bg_image = self._render_background(t)
        ctx["background"].set_image(bg_image, format="jpeg", quality=60)

        # Render overlay (shapes with transparency) - will be png
        overlay_image = self._render_overlay(t)
        ctx["overlay"].set_image(overlay_image, format="png")

    def _render_background(self, timestamp: float) -> Image:
        """Render animated gradient background using PIL."""
        import math

        # Create PIL image
        pil_img = PILImage.new("RGB", (self.width, self.height))
        draw = ImageDraw.Draw(pil_img)

        # Animated gradient (horizontal bands that shift over time)
        num_bands = 20
        band_height = self.height // num_bands

        for i in range(num_bands):
            # Calculate color based on position and time
            phase = (i / num_bands + timestamp * 0.1) % 1.0
            r = int(128 + 127 * math.sin(phase * math.pi * 2))
            g = int(128 + 127 * math.sin(phase * math.pi * 2 + math.pi * 2 / 3))
            b = int(128 + 127 * math.sin(phase * math.pi * 2 + math.pi * 4 / 3))

            y1 = i * band_height
            y2 = (i + 1) * band_height
            draw.rectangle([0, y1, self.width, y2], fill=(r, g, b))

        return Image(pil_img)

    def _render_overlay(self, timestamp: float) -> Image:
        """Render animated overlay with transparency using PIL."""
        import math

        # Create PIL image with alpha
        pil_img = PILImage.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(pil_img)

        # Draw bouncing circle
        cx = int(self.width * 0.5 + self.width * 0.3 * math.sin(timestamp * 2))
        cy = int(self.height * 0.5 + self.height * 0.3 * math.cos(timestamp * 1.5))
        radius = 40

        # Yellow circle with slight transparency
        draw.ellipse(
            [cx - radius, cy - radius, cx + radius, cy + radius],
            fill=(255, 255, 0, 220),
            outline=(255, 200, 0, 255),
            width=3,
        )

        # Draw rotating rectangle
        rect_cx = self.width // 2
        rect_cy = self.height // 2
        angle = timestamp * 45  # degrees per second

        # Calculate rotated rectangle corners
        import math
        half_w, half_h = 60, 30
        rad = math.radians(angle)
        cos_a, sin_a = math.cos(rad), math.sin(rad)

        corners = []
        for dx, dy in [(-half_w, -half_h), (half_w, -half_h),
                       (half_w, half_h), (-half_w, half_h)]:
            rx = dx * cos_a - dy * sin_a + rect_cx
            ry = dx * sin_a + dy * cos_a + rect_cy
            corners.append((rx, ry))

        draw.polygon(corners, fill=(0, 200, 255, 180), outline=(0, 150, 255, 255))

        # Draw timestamp text
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
        except (IOError, OSError):
            font = ImageFont.load_default()

        text = f"t = {timestamp:.2f}s"
        draw.text((20, 20), text, fill=(255, 255, 255, 255), font=font)

        return Image(pil_img)


def main():
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Writing frames to: {OUTPUT_DIR}")

    # Create multi-output renderer
    renderer = SceneRenderer(640, 480, target_fps=10.0)

    # Create StreamViewPil
    view = StreamViewPil(640, 480, title="Multi-Output Demo")

    # Add layers from renderer outputs
    for name, output in renderer.layer_outputs.items():
        view.add_layer(
            stream=renderer,  # Same stream for all layers
            z_index=output.config.z_index,
            name=name,
        )

    # Note: For this demo, we'll render manually rather than using the
    # background thread, since we want to save specific frames

    view.start()

    # Render frames at different timestamps
    num_frames = 30
    fps = 10.0

    print(f"Rendering {num_frames} frames at {fps} FPS...")

    for i in range(num_frames):
        timestamp = i / fps

        # Manually trigger render
        renderer._render_ctx.timestamp = timestamp
        renderer._render_ctx.frame_index = i
        renderer.render(renderer._render_ctx)

        # Composite and save
        pil_img = view.render(timestamp=timestamp)
        frame_path = OUTPUT_DIR / f"frame_{i:04d}.png"
        pil_img.save(frame_path)

        print(f"  Saved: {frame_path.name} (t={timestamp:.2f}s)")

    view.stop()

    # Summary
    print(f"\nRendered {num_frames} frames to {OUTPUT_DIR}")
    print(f"Total size: {sum(f.stat().st_size for f in OUTPUT_DIR.glob('*.png')) / 1024:.1f} KB")

    first_frame = PILImage.open(OUTPUT_DIR / "frame_0000.png")
    print(f"Frame size: {first_frame.size[0]}x{first_frame.size[1]}")

    print("\nDone!")


if __name__ == "__main__":
    main()
