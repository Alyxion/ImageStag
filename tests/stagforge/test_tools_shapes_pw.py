"""Tests for shape tools (line, rect, circle, polygon) with different layer offsets - Playwright version.

Testing Principles:
- Line of width W and length L: expect W*L pixels (+/-30% for antialiasing)
- Rectangle of WxH: expect W*H pixels (+/-10% for stroke overlap)
- Circle of radius R: expect pi*R^2 pixels (+/-20% for rasterization)
- Outline-only shapes: perimeter * stroke_width pixels
- Always verify with range assertions, not just "changed"
"""

import math
import pytest
from .helpers_pw import (
    TestHelpers,
    approx_line_pixels,
    approx_rect_pixels,
    approx_rect_outline_pixels,
    approx_circle_pixels,
    approx_ellipse_pixels,
)


pytestmark = pytest.mark.asyncio


class TestLineTool:
    """Tests for the line tool."""

    async def test_horizontal_line(self, helpers: TestHelpers):
        """Test horizontal line produces expected pixel count."""
        await helpers.new_document(200, 200)

        line_width = 3
        line_length = 160  # from x=20 to x=180

        await helpers.tools.draw_line(20, 100, 180, 100, color='#FF0000', width=line_width)

        red_pixels = await helpers.pixels.count_pixels_with_color((255, 0, 0, 255), tolerance=10)
        min_expected, max_expected = approx_line_pixels(line_length, line_width)

        assert min_expected <= red_pixels <= max_expected, \
            f"Horizontal line: expected {min_expected}-{max_expected} pixels, got {red_pixels}"

    async def test_vertical_line(self, helpers: TestHelpers):
        """Test vertical line produces expected pixel count."""
        await helpers.new_document(200, 200)

        line_width = 4
        line_length = 140  # from y=30 to y=170

        await helpers.tools.draw_line(100, 30, 100, 170, color='#00FF00', width=line_width)

        green_pixels = await helpers.pixels.count_pixels_with_color((0, 255, 0, 255), tolerance=10)
        min_expected, max_expected = approx_line_pixels(line_length, line_width)

        assert min_expected <= green_pixels <= max_expected, \
            f"Vertical line: expected {min_expected}-{max_expected} pixels, got {green_pixels}"

    async def test_diagonal_line(self, helpers: TestHelpers):
        """Test diagonal line produces expected pixel count."""
        await helpers.new_document(200, 200)

        line_width = 2
        # Diagonal from (20, 20) to (180, 180) = sqrt(160^2 + 160^2) = 226 pixels
        line_length = math.sqrt(160**2 + 160**2)

        await helpers.tools.draw_line(20, 20, 180, 180, color='#0000FF', width=line_width)

        blue_pixels = await helpers.pixels.count_pixels_with_color((0, 0, 255, 255), tolerance=10)
        min_expected, max_expected = approx_line_pixels(line_length, line_width, tolerance=0.35)

        assert min_expected <= blue_pixels <= max_expected, \
            f"Diagonal line: expected {min_expected}-{max_expected} pixels, got {blue_pixels}"

    async def test_line_on_offset_layer(self, helpers: TestHelpers):
        """Test line on offset layer produces expected pixel count."""
        await helpers.new_document(400, 400)

        layer_id = await helpers.layers.create_offset_layer(
            offset_x=100, offset_y=100,
            width=200, height=200
        )

        line_width = 3
        # Line from (120, 200) to (280, 200) = 160 pixels, fully within layer
        line_length = 160

        await helpers.tools.draw_line(120, 200, 280, 200, color='#00FF00', width=line_width)

        green_pixels = await helpers.pixels.count_pixels_with_color(
            (0, 255, 0, 255), tolerance=10, layer_id=layer_id
        )
        min_expected, max_expected = approx_line_pixels(line_length, line_width)

        assert min_expected <= green_pixels <= max_expected, \
            f"Line on offset layer: expected {min_expected}-{max_expected}, got {green_pixels}"

    async def test_line_crossing_layer_boundary(self, helpers: TestHelpers):
        """Test line crossing layer boundary is clipped correctly."""
        await helpers.new_document(400, 400)

        layer_id = await helpers.layers.create_offset_layer(
            offset_x=150, offset_y=150,
            width=100, height=100
        )

        line_width = 4
        # Line from (100, 200) to (300, 200) - only 100 pixels inside layer (150 to 250)
        line_length_inside = 100

        await helpers.tools.draw_line(100, 200, 300, 200, color='#0000FF', width=line_width)

        blue_pixels = await helpers.pixels.count_pixels_with_color(
            (0, 0, 255, 255), tolerance=10, layer_id=layer_id
        )
        min_expected, max_expected = approx_line_pixels(line_length_inside, line_width, tolerance=0.40)

        assert min_expected <= blue_pixels <= max_expected, \
            f"Clipped line: expected {min_expected}-{max_expected}, got {blue_pixels}"


class TestRectTool:
    """Tests for the rectangle tool."""

    async def test_filled_rect(self, helpers: TestHelpers):
        """Test filled rectangle produces expected pixel count."""
        await helpers.new_document(200, 200)

        rect_width = 80
        rect_height = 60

        await helpers.tools.draw_filled_rect(50, 50, rect_width, rect_height, color='#FF0000')

        red_pixels = await helpers.pixels.count_pixels_with_color((255, 0, 0, 255), tolerance=10)
        min_expected, max_expected = approx_rect_pixels(rect_width, rect_height)

        assert min_expected <= red_pixels <= max_expected, \
            f"Filled rect: expected {min_expected}-{max_expected} pixels, got {red_pixels}"

    async def test_rect_outline(self, helpers: TestHelpers):
        """Test rectangle outline produces expected pixel count."""
        await helpers.new_document(200, 200)

        rect_width = 80
        rect_height = 60
        stroke_width = 2

        await helpers.tools.draw_rect_outline(50, 50, rect_width, rect_height,
                                              color='#00FF00', width_=stroke_width)

        green_pixels = await helpers.pixels.count_pixels_with_color((0, 255, 0, 255), tolerance=10)
        min_expected, max_expected = approx_rect_outline_pixels(rect_width, rect_height, stroke_width)

        # Outline should have significantly fewer pixels than filled
        filled_pixels = rect_width * rect_height
        assert green_pixels < filled_pixels * 0.5, \
            f"Outline should have < 50% of filled rect pixels"
        assert min_expected <= green_pixels <= max_expected, \
            f"Rect outline: expected {min_expected}-{max_expected}, got {green_pixels}"

    async def test_filled_rect_on_offset_layer(self, helpers: TestHelpers):
        """Test filled rect on offset layer."""
        await helpers.new_document(400, 400)

        layer_id = await helpers.layers.create_offset_layer(
            offset_x=100, offset_y=100,
            width=200, height=200
        )

        rect_width = 80
        rect_height = 60

        await helpers.tools.draw_filled_rect(150, 150, rect_width, rect_height, color='#0000FF')

        blue_pixels = await helpers.pixels.count_pixels_with_color(
            (0, 0, 255, 255), tolerance=10, layer_id=layer_id
        )
        min_expected, max_expected = approx_rect_pixels(rect_width, rect_height)

        assert min_expected <= blue_pixels <= max_expected, \
            f"Rect on offset layer: expected {min_expected}-{max_expected}, got {blue_pixels}"

    async def test_rect_clipped_by_layer_boundary(self, helpers: TestHelpers):
        """Test rect extending beyond layer is clipped."""
        await helpers.new_document(400, 400)

        layer_id = await helpers.layers.create_offset_layer(
            offset_x=150, offset_y=150,
            width=100, height=100
        )

        # Draw rect starting at (180, 180), size 80x80
        # Layer ends at (250, 250), so visible portion is 70x70
        visible_width = 70
        visible_height = 70

        await helpers.tools.draw_filled_rect(180, 180, 80, 80, color='#FF00FF')

        magenta_pixels = await helpers.pixels.count_pixels_with_color(
            (255, 0, 255, 255), tolerance=10, layer_id=layer_id
        )
        min_expected, max_expected = approx_rect_pixels(visible_width, visible_height, tolerance=0.15)

        assert min_expected <= magenta_pixels <= max_expected, \
            f"Clipped rect: expected {min_expected}-{max_expected}, got {magenta_pixels}"


class TestCircleTool:
    """Tests for the circle/ellipse tool."""

    async def test_filled_circle(self, helpers: TestHelpers):
        """Test filled circle produces expected pixel count."""
        await helpers.new_document(200, 200)

        radius = 40

        await helpers.tools.draw_filled_circle(100, 100, radius, color='#FF0000')

        red_pixels = await helpers.pixels.count_pixels_with_color((255, 0, 0, 255), tolerance=10)
        min_expected, max_expected = approx_circle_pixels(radius)

        assert min_expected <= red_pixels <= max_expected, \
            f"Filled circle r={radius}: expected {min_expected}-{max_expected}, got {red_pixels}"

    async def test_filled_ellipse(self, helpers: TestHelpers):
        """Test filled ellipse produces expected pixel count."""
        await helpers.new_document(200, 200)

        # Ellipse from (30, 60) to (170, 140) has semi-axes 70 and 40
        semi_a = 70  # horizontal semi-axis
        semi_b = 40  # vertical semi-axis

        await helpers.tools.draw_ellipse(30, 60, 140, 80, fill_color='#00FF00', fill=True, stroke=False)

        green_pixels = await helpers.pixels.count_pixels_with_color((0, 255, 0, 255), tolerance=10)
        min_expected, max_expected = approx_ellipse_pixels(semi_a, semi_b)

        assert min_expected <= green_pixels <= max_expected, \
            f"Ellipse: expected {min_expected}-{max_expected}, got {green_pixels}"

    async def test_circle_on_offset_layer(self, helpers: TestHelpers):
        """Test circle on offset layer produces expected pixel count."""
        await helpers.new_document(400, 400)

        layer_id = await helpers.layers.create_offset_layer(
            offset_x=100, offset_y=100,
            width=200, height=200
        )

        radius = 50

        await helpers.tools.draw_filled_circle(200, 200, radius, color='#0000FF')

        blue_pixels = await helpers.pixels.count_pixels_with_color(
            (0, 0, 255, 255), tolerance=10, layer_id=layer_id
        )
        min_expected, max_expected = approx_circle_pixels(radius)

        assert min_expected <= blue_pixels <= max_expected, \
            f"Circle on offset layer: expected {min_expected}-{max_expected}, got {blue_pixels}"

    async def test_circle_clipped_by_layer_corner(self, helpers: TestHelpers):
        """Test circle at layer corner is partially clipped (quarter visible)."""
        await helpers.new_document(400, 400)

        layer_id = await helpers.layers.create_offset_layer(
            offset_x=150, offset_y=150,
            width=100, height=100
        )

        radius = 40
        # Circle centered at layer corner (150, 150) - approximately 1/4 visible
        expected_fraction = 0.25

        await helpers.tools.draw_filled_circle(150, 150, radius, color='#FFFF00')

        yellow_pixels = await helpers.pixels.count_pixels_with_color(
            (255, 255, 0, 255), tolerance=10, layer_id=layer_id
        )

        full_circle = math.pi * radius * radius
        min_expected = int(full_circle * expected_fraction * 0.6)  # Allow 40% variance
        max_expected = int(full_circle * expected_fraction * 1.4)

        assert min_expected <= yellow_pixels <= max_expected, \
            f"Quarter circle: expected {min_expected}-{max_expected}, got {yellow_pixels}"

    async def test_circle_radius_scaling(self, helpers: TestHelpers):
        """Test that doubling radius quadruples area."""
        await helpers.new_document(400, 200)

        # Small circle
        await helpers.tools.draw_filled_circle(100, 100, 20, color='#FF0000')
        small_pixels = await helpers.pixels.count_pixels_with_color((255, 0, 0, 255), tolerance=10)

        # Large circle (2x radius = 4x area)
        await helpers.tools.draw_filled_circle(300, 100, 40, color='#00FF00')
        large_pixels = await helpers.pixels.count_pixels_with_color((0, 255, 0, 255), tolerance=10)

        ratio = large_pixels / small_pixels if small_pixels > 0 else 0
        # Expect ratio around 4 (+/-40%)
        assert 2.8 <= ratio <= 5.2, \
            f"2x radius should give ~4x area. Got ratio {ratio:.2f} ({small_pixels} vs {large_pixels})"


class TestShapeUndoRedo:
    """Tests for undo/redo with shapes - verify exact pixel restoration."""

    async def test_undo_rect_restores_exact_count(self, helpers: TestHelpers):
        """Test undo removes rectangle completely."""
        await helpers.new_document(200, 200)

        initial = await helpers.pixels.count_non_transparent_pixels()
        assert initial == 0

        await helpers.tools.draw_filled_rect(50, 50, 80, 60, color='#FF0000')
        after_draw = await helpers.pixels.count_non_transparent_pixels()

        min_expected, max_expected = approx_rect_pixels(80, 60)
        assert min_expected <= after_draw <= max_expected

        await helpers.undo()
        after_undo = await helpers.pixels.count_non_transparent_pixels()

        assert after_undo == initial, \
            f"Undo should restore to 0 pixels, got {after_undo}"

    async def test_undo_circle_restores_exact_count(self, helpers: TestHelpers):
        """Test undo removes circle completely."""
        await helpers.new_document(200, 200)

        initial = await helpers.pixels.count_non_transparent_pixels()
        assert initial == 0

        await helpers.tools.draw_filled_circle(100, 100, 40, color='#00FF00')
        after_draw = await helpers.pixels.count_non_transparent_pixels()
        assert after_draw > 0

        await helpers.undo()
        after_undo = await helpers.pixels.count_non_transparent_pixels()

        assert after_undo == initial, \
            f"Undo should restore to 0 pixels, got {after_undo}"

    async def test_redo_restores_exact_shape(self, helpers: TestHelpers):
        """Test redo restores exact pixel count."""
        await helpers.new_document(200, 200)

        await helpers.tools.draw_filled_rect(50, 50, 80, 60, color='#FF0000')
        after_draw = await helpers.pixels.count_non_transparent_pixels()

        await helpers.undo()
        await helpers.redo()
        after_redo = await helpers.pixels.count_non_transparent_pixels()

        assert after_redo == after_draw, \
            f"Redo should restore exact count. Expected {after_draw}, got {after_redo}"


class TestMultipleShapes:
    """Tests for multiple shapes on same layer."""

    async def test_two_non_overlapping_rects(self, helpers: TestHelpers):
        """Test two non-overlapping rectangles produce sum of areas."""
        await helpers.new_document(300, 200)

        rect1_area = 60 * 50
        rect2_area = 80 * 40

        await helpers.tools.draw_filled_rect(20, 50, 60, 50, color='#FF0000')
        await helpers.tools.draw_filled_rect(200, 80, 80, 40, color='#00FF00')

        red_pixels = await helpers.pixels.count_pixels_with_color((255, 0, 0, 255), tolerance=10)
        green_pixels = await helpers.pixels.count_pixels_with_color((0, 255, 0, 255), tolerance=10)

        min_red, max_red = approx_rect_pixels(60, 50)
        min_green, max_green = approx_rect_pixels(80, 40)

        assert min_red <= red_pixels <= max_red, \
            f"Red rect: expected {min_red}-{max_red}, got {red_pixels}"
        assert min_green <= green_pixels <= max_green, \
            f"Green rect: expected {min_green}-{max_green}, got {green_pixels}"

    async def test_overlapping_shapes(self, helpers: TestHelpers):
        """Test overlapping shapes - later shape overwrites earlier."""
        await helpers.new_document(200, 200)

        # Red rect covering most of canvas
        await helpers.tools.draw_filled_rect(20, 20, 160, 160, color='#FF0000')
        red_after_first = await helpers.pixels.count_pixels_with_color((255, 0, 0, 255), tolerance=10)

        # Blue circle in center overwrites some red
        await helpers.tools.draw_filled_circle(100, 100, 40, color='#0000FF')

        red_after_second = await helpers.pixels.count_pixels_with_color((255, 0, 0, 255), tolerance=10)
        blue_pixels = await helpers.pixels.count_pixels_with_color((0, 0, 255, 255), tolerance=10)

        # Blue circle should have approximately pi*40^2 = 5027 pixels
        min_blue, max_blue = approx_circle_pixels(40)
        assert min_blue <= blue_pixels <= max_blue, \
            f"Blue circle: expected {min_blue}-{max_blue}, got {blue_pixels}"

        # Red should be reduced by approximately the blue circle area
        red_lost = red_after_first - red_after_second
        assert min_blue * 0.8 <= red_lost <= max_blue * 1.2, \
            f"Red lost should match blue added. Lost {red_lost}, blue is {blue_pixels}"
