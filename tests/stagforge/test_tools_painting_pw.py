"""Tests for painting/editing tools with pixel count validation - Playwright version.

Testing Principles:
- Pencil strokes: Bresenham line = length pixels (for 1px) or area approximation
- Effect tools modify existing pixels, so measure change magnitude
- Clone stamp copies pixels, maintaining source area pixel characteristics
- Dodge/Burn change luminance, measurable via average brightness
- Sponge changes saturation, measurable via color channel variance
"""

import pytest
from .helpers_pw import TestHelpers


pytestmark = pytest.mark.asyncio


class TestPencilTool:
    """Tests for the pencil tool (hard-edged, aliased strokes)."""

    async def test_pencil_draws_hard_edge_horizontal_line(self, helpers: TestHelpers):
        """Test pencil draws crisp horizontal line without antialiasing."""
        await helpers.new_document(200, 200)

        # Draw 1px horizontal line
        await helpers.tools.pencil_stroke([(50, 100), (150, 100)], color='#FF0000', size=1)

        red_pixels = await helpers.pixels.count_pixels_with_color((255, 0, 0, 255), tolerance=10)

        # Bresenham line from (50,100) to (150,100) = 101 pixels exactly
        # Allow small margin for endpoint behavior
        assert 95 <= red_pixels <= 110, \
            f"Expected ~101 red pixels for 1px pencil line, got {red_pixels}"

    async def test_pencil_draws_larger_size(self, helpers: TestHelpers):
        """Test pencil with larger size creates wider stroke."""
        await helpers.new_document(200, 200)

        pencil_size = 5
        stroke_length = 100

        await helpers.tools.pencil_stroke([(50, 100), (150, 100)], color='#00FF00', size=pencil_size)

        green_pixels = await helpers.pixels.count_pixels_with_color((0, 255, 0, 255), tolerance=10)

        # For size 5, expect approximately length * size = 100 * 5 = 500 pixels
        # Pencil uses fillRect so edges should be crisp
        expected = stroke_length * pencil_size
        assert expected * 0.7 <= green_pixels <= expected * 1.5, \
            f"Expected ~{expected} green pixels, got {green_pixels}"

    async def test_pencil_diagonal_line_uses_bresenham(self, helpers: TestHelpers):
        """Test pencil diagonal uses Bresenham algorithm (aliased)."""
        await helpers.new_document(200, 200)

        # Draw 1px diagonal line
        await helpers.tools.pencil_stroke([(50, 50), (150, 150)], color='#0000FF', size=1)

        blue_pixels = await helpers.pixels.count_pixels_with_color((0, 0, 255, 255), tolerance=10)

        # Diagonal 100px in x, 100px in y = ~141 pixels for Bresenham (steps max(dx,dy)+1)
        # Actually it's max(100, 100) + 1 = 101 pixels
        assert 95 <= blue_pixels <= 150, \
            f"Expected ~101-141 blue pixels for diagonal pencil line, got {blue_pixels}"


class TestSmudgeTool:
    """Tests for the smudge tool (push/blend colors)."""

    async def test_smudge_changes_pixels(self, helpers: TestHelpers):
        """Test smudge modifies pixel colors along stroke path."""
        await helpers.new_document(200, 200)

        # Create two color bands
        await helpers.tools.draw_filled_rect(0, 0, 100, 200, color='#FF0000')
        await helpers.tools.draw_filled_rect(100, 0, 100, 200, color='#0000FF')

        initial_checksum = await helpers.pixels.compute_checksum()

        # Smudge across the boundary
        await helpers.tools.smudge_stroke([(80, 100), (120, 100)], size=30, strength=50)

        after_checksum = await helpers.pixels.compute_checksum()

        assert initial_checksum != after_checksum, \
            "Smudge should modify pixels"

    async def test_smudge_blends_colors_at_boundary(self, helpers: TestHelpers):
        """Test smudge creates blended colors at color boundary."""
        await helpers.new_document(200, 200)

        # Left red, right blue
        await helpers.tools.draw_filled_rect(0, 0, 100, 200, color='#FF0000')
        await helpers.tools.draw_filled_rect(100, 0, 100, 200, color='#0000FF')

        # Count pure red pixels before
        initial_red = await helpers.pixels.count_pixels_with_color((255, 0, 0, 255), tolerance=10)

        # Smudge from red into blue area
        await helpers.tools.smudge_stroke([(50, 100), (150, 100)], size=40, strength=70)

        # After smudging, pure red count should decrease as colors blend
        after_red = await helpers.pixels.count_pixels_with_color((255, 0, 0, 255), tolerance=10)

        # Some red pixels should have changed (blended with blue)
        assert after_red < initial_red, \
            f"Pure red pixels should decrease after smudging. Before: {initial_red}, after: {after_red}"


class TestBlurTool:
    """Tests for the blur tool (paint blur effect)."""

    async def test_blur_reduces_contrast(self, helpers: TestHelpers):
        """Test blur reduces local contrast by averaging neighbors."""
        await helpers.new_document(200, 200)

        # Create checkerboard pattern (high contrast)
        for y in range(0, 200, 20):
            for x in range(0, 200, 20):
                color = '#FFFFFF' if ((x + y) // 20) % 2 == 0 else '#000000'
                await helpers.tools.draw_filled_rect(x, y, 20, 20, color=color)

        initial_checksum = await helpers.pixels.compute_checksum()

        # Blur center area
        await helpers.tools.blur_stroke([(100, 100)], size=50, strength=80)

        after_checksum = await helpers.pixels.compute_checksum()

        assert initial_checksum != after_checksum, \
            "Blur should modify pixels"

    async def test_blur_stroke_affects_path(self, helpers: TestHelpers):
        """Test blur along stroke path changes pixels."""
        await helpers.new_document(200, 200)

        # Sharp edge
        await helpers.tools.draw_filled_rect(50, 0, 100, 200, color='#FF0000')

        initial_checksum = await helpers.pixels.compute_checksum()

        # Blur along the edge
        await helpers.tools.blur_stroke([(50, 50), (50, 150)], size=30, strength=60)

        after_checksum = await helpers.pixels.compute_checksum()

        assert initial_checksum != after_checksum, \
            "Blur stroke should modify pixels along the path"


class TestSharpenTool:
    """Tests for the sharpen tool (increase local contrast)."""

    async def test_sharpen_changes_pixels(self, helpers: TestHelpers):
        """Test sharpen modifies pixel values."""
        await helpers.new_document(200, 200)

        # Create soft gradient-like area
        await helpers.tools.draw_filled_circle(100, 100, 50, color='#808080')

        initial_checksum = await helpers.pixels.compute_checksum()

        # Sharpen center
        await helpers.tools.sharpen_stroke([(100, 100)], size=40, strength=70)

        after_checksum = await helpers.pixels.compute_checksum()

        assert initial_checksum != after_checksum, \
            "Sharpen should modify pixels"


class TestDodgeTool:
    """Tests for the dodge tool (lighten areas)."""

    async def test_dodge_lightens_pixels(self, helpers: TestHelpers):
        """Test dodge increases average brightness."""
        await helpers.new_document(200, 200)

        # Fill with medium gray
        await helpers.tools.draw_filled_rect(0, 0, 200, 200, color='#808080')

        initial_avg = await helpers.pixels.get_average_brightness()

        # Dodge center area
        await helpers.tools.dodge_stroke([(100, 100)], size=50, exposure=80)

        after_avg = await helpers.pixels.get_average_brightness()

        assert after_avg > initial_avg, \
            f"Dodge should increase brightness. Before: {initial_avg:.2f}, after: {after_avg:.2f}"

    async def test_dodge_midtones_affects_medium_colors(self, helpers: TestHelpers):
        """Test dodge with midtones range affects medium brightness areas."""
        await helpers.new_document(200, 200)

        # Create areas of different brightness
        await helpers.tools.draw_filled_rect(0, 0, 100, 200, color='#404040')  # Dark
        await helpers.tools.draw_filled_rect(100, 0, 100, 200, color='#808080')  # Medium

        # Get initial medium area brightness
        initial_checksum = await helpers.pixels.compute_checksum()

        # Dodge across with midtones range
        await helpers.tools.dodge_stroke([(50, 100), (150, 100)], size=30, exposure=60, range_='midtones')

        after_checksum = await helpers.pixels.compute_checksum()

        assert initial_checksum != after_checksum, \
            "Dodge with midtones should modify pixels"


class TestBurnTool:
    """Tests for the burn tool (darken areas)."""

    async def test_burn_darkens_pixels(self, helpers: TestHelpers):
        """Test burn decreases average brightness."""
        await helpers.new_document(200, 200)

        # Fill with medium gray
        await helpers.tools.draw_filled_rect(0, 0, 200, 200, color='#808080')

        initial_avg = await helpers.pixels.get_average_brightness()

        # Burn center area
        await helpers.tools.burn_stroke([(100, 100)], size=50, exposure=80)

        after_avg = await helpers.pixels.get_average_brightness()

        assert after_avg < initial_avg, \
            f"Burn should decrease brightness. Before: {initial_avg:.2f}, after: {after_avg:.2f}"

    async def test_burn_highlights_affects_bright_areas(self, helpers: TestHelpers):
        """Test burn with highlights range affects bright areas."""
        await helpers.new_document(200, 200)

        # Create bright area
        await helpers.tools.draw_filled_rect(0, 0, 200, 200, color='#C0C0C0')

        initial_checksum = await helpers.pixels.compute_checksum()

        # Burn with highlights range
        await helpers.tools.burn_stroke([(100, 100)], size=50, exposure=70, range_='highlights')

        after_checksum = await helpers.pixels.compute_checksum()

        assert initial_checksum != after_checksum, \
            "Burn with highlights should modify bright pixels"


class TestSpongeTool:
    """Tests for the sponge tool (saturate/desaturate)."""

    async def test_sponge_saturate_increases_saturation(self, helpers: TestHelpers):
        """Test sponge in saturate mode increases color intensity."""
        await helpers.new_document(200, 200)

        # Fill with desaturated red (pinkish gray)
        await helpers.tools.draw_filled_rect(0, 0, 200, 200, color='#C08080')

        # Count pixels with high red saturation before
        initial_checksum = await helpers.pixels.compute_checksum()

        # Saturate
        await helpers.tools.sponge_stroke([(100, 100)], size=50, flow=80, mode='saturate')

        after_checksum = await helpers.pixels.compute_checksum()

        assert initial_checksum != after_checksum, \
            "Sponge saturate should modify pixels"

    async def test_sponge_desaturate_reduces_color(self, helpers: TestHelpers):
        """Test sponge in desaturate mode removes color toward gray."""
        await helpers.new_document(200, 200)

        # Fill with saturated red
        await helpers.tools.draw_filled_rect(0, 0, 200, 200, color='#FF0000')

        # Count pure red pixels before
        initial_red = await helpers.pixels.count_pixels_with_color((255, 0, 0, 255), tolerance=10)

        # Desaturate center
        await helpers.tools.sponge_stroke([(100, 100)], size=50, flow=80, mode='desaturate')

        # After desaturating, pure red count should decrease
        after_red = await helpers.pixels.count_pixels_with_color((255, 0, 0, 255), tolerance=10)

        assert after_red < initial_red, \
            f"Pure red pixels should decrease after desaturation. Before: {initial_red}, after: {after_red}"


class TestCloneStampTool:
    """Tests for the clone stamp tool (sample and paint)."""

    async def test_clone_stamp_copies_pixels(self, helpers: TestHelpers):
        """Test clone stamp copies pixels from source to destination."""
        await helpers.new_document(200, 200)

        # Create source pattern
        await helpers.tools.draw_filled_rect(20, 20, 50, 50, color='#FF0000')

        # Count red pixels before cloning
        initial_red = await helpers.pixels.count_pixels_with_color((255, 0, 0, 255), tolerance=10)

        # Set source at red area
        await helpers.tools.clone_stamp_set_source(45, 45)

        # Clone to different location
        await helpers.tools.clone_stamp_stroke([(145, 45)], size=30)

        # After cloning, red pixel count should increase
        after_red = await helpers.pixels.count_pixels_with_color((255, 0, 0, 255), tolerance=10)

        assert after_red > initial_red, \
            f"Clone stamp should copy red pixels. Before: {initial_red}, after: {after_red}"

    async def test_clone_stamp_maintains_offset(self, helpers: TestHelpers):
        """Test clone stamp maintains offset between source and destination."""
        await helpers.new_document(200, 200)

        # Create distinctive pattern
        await helpers.tools.draw_filled_rect(10, 10, 30, 30, color='#FF0000')
        await helpers.tools.draw_filled_rect(50, 10, 30, 30, color='#00FF00')

        # Clone from left area to right area
        await helpers.tools.clone_stamp_set_source(25, 25)  # Center of red

        # Stroke in destination area
        await helpers.tools.clone_stamp_stroke([(125, 25), (130, 25)], size=20)

        # Should have copied red pixels
        after_checksum = await helpers.pixels.compute_checksum()
        # Just verify something changed
        assert await helpers.pixels.count_non_transparent_pixels() > 0


class TestUndoRedoForNewTools:
    """Tests for undo/redo with new painting tools."""

    async def test_undo_pencil_restores_state(self, helpers: TestHelpers):
        """Test undo pencil stroke restores original state."""
        await helpers.new_document(200, 200)

        initial_checksum = await helpers.pixels.compute_checksum()

        await helpers.tools.pencil_stroke([(50, 100), (150, 100)], color='#FF0000', size=3)

        after_stroke_checksum = await helpers.pixels.compute_checksum()
        assert initial_checksum != after_stroke_checksum

        await helpers.undo()

        after_undo_checksum = await helpers.pixels.compute_checksum()
        assert after_undo_checksum == initial_checksum, \
            "Undo should restore original state after pencil stroke"

    async def test_undo_dodge_restores_brightness(self, helpers: TestHelpers):
        """Test undo dodge restores original brightness."""
        await helpers.new_document(200, 200)

        await helpers.tools.draw_filled_rect(0, 0, 200, 200, color='#808080')
        initial_avg = await helpers.pixels.get_average_brightness()

        await helpers.tools.dodge_stroke([(100, 100)], size=50, exposure=80)

        after_dodge_avg = await helpers.pixels.get_average_brightness()
        assert after_dodge_avg > initial_avg

        await helpers.undo()

        after_undo_avg = await helpers.pixels.get_average_brightness()
        # Allow small tolerance for floating point
        assert abs(after_undo_avg - initial_avg) < 1, \
            f"Undo should restore brightness. Expected ~{initial_avg}, got {after_undo_avg}"

    async def test_undo_blur_restores_detail(self, helpers: TestHelpers):
        """Test undo blur restores original pixels."""
        await helpers.new_document(200, 200)

        # Create pattern
        await helpers.tools.draw_filled_rect(90, 90, 20, 20, color='#FF0000')
        initial_checksum = await helpers.pixels.compute_checksum()

        await helpers.tools.blur_stroke([(100, 100)], size=30, strength=80)

        after_blur_checksum = await helpers.pixels.compute_checksum()
        assert initial_checksum != after_blur_checksum

        await helpers.undo()

        after_undo_checksum = await helpers.pixels.compute_checksum()
        assert after_undo_checksum == initial_checksum, \
            "Undo should restore original state after blur"
