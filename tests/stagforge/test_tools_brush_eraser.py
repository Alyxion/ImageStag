"""Tests for brush and eraser tools with different layer offsets.

Testing Principles:
- Always use range-based assertions for pixel counts
- A brush stroke of size S over distance D produces approximately S*D pixels
- Account for antialiasing (+/- 20% tolerance typical)
- For circles/round brushes: area ≈ π*r² where r = size/2
- Verify both presence AND approximate quantity of pixels


NOTE: Sync tests with async helpers - use test_tools_brush_eraser_pw.py instead.
"""
import pytest

# Skip entire module - sync/async mismatch with helpers fixture
pytest.skip(
    "Sync tests with async helpers - use test_tools_brush_eraser_pw.py instead",
    allow_module_level=True
)


import math
import pytest
from .helpers import TestHelpers


def approx_line_pixels(length: float, width: float, tolerance: float = 0.25) -> tuple:
    """
    Calculate expected pixel range for a line/stroke.

    Args:
        length: Length of the stroke in pixels
        width: Width/size of the brush
        tolerance: Fractional tolerance (0.25 = ±25%)

    Returns:
        (min_pixels, max_pixels) tuple
    """
    expected = length * width
    return (int(expected * (1 - tolerance)), int(expected * (1 + tolerance)))


def approx_circle_pixels(radius: float, tolerance: float = 0.20) -> tuple:
    """
    Calculate expected pixel range for a filled circle.

    Args:
        radius: Radius of the circle
        tolerance: Fractional tolerance (0.20 = ±20%)

    Returns:
        (min_pixels, max_pixels) tuple
    """
    expected = math.pi * radius * radius
    return (int(expected * (1 - tolerance)), int(expected * (1 + tolerance)))


def approx_rect_pixels(width: float, height: float, tolerance: float = 0.10) -> tuple:
    """
    Calculate expected pixel range for a filled rectangle.

    Args:
        width, height: Dimensions of rectangle
        tolerance: Fractional tolerance (0.10 = ±10%)

    Returns:
        (min_pixels, max_pixels) tuple
    """
    expected = width * height
    return (int(expected * (1 - tolerance)), int(expected * (1 + tolerance)))


class TestBrushTool:
    """Tests for the brush tool."""

    def test_brush_horizontal_stroke(self, helpers: TestHelpers):
        """Test horizontal brush stroke produces expected pixel count."""
        helpers.new_document(200, 200)

        brush_size = 10
        stroke_length = 100  # from x=50 to x=150

        helpers.tools.brush_stroke(
            [(50, 100), (150, 100)],  # horizontal line
            color='#FF0000',
            size=brush_size
        )

        red_pixels = helpers.pixels.count_pixels_with_color((255, 0, 0, 255), tolerance=10)

        # Expected: stroke_length * brush_size = 100 * 10 = 1000 pixels
        # With antialiasing and round brush edges, allow ±30%
        min_expected, max_expected = approx_line_pixels(stroke_length, brush_size, tolerance=0.30)

        assert min_expected <= red_pixels <= max_expected, \
            f"Horizontal stroke: expected {min_expected}-{max_expected} red pixels, got {red_pixels}"

    def test_brush_vertical_stroke(self, helpers: TestHelpers):
        """Test vertical brush stroke produces expected pixel count."""
        helpers.new_document(200, 200)

        brush_size = 8
        stroke_length = 120  # from y=40 to y=160

        helpers.tools.brush_stroke(
            [(100, 40), (100, 160)],  # vertical line
            color='#00FF00',
            size=brush_size
        )

        green_pixels = helpers.pixels.count_pixels_with_color((0, 255, 0, 255), tolerance=10)

        min_expected, max_expected = approx_line_pixels(stroke_length, brush_size, tolerance=0.30)

        assert min_expected <= green_pixels <= max_expected, \
            f"Vertical stroke: expected {min_expected}-{max_expected} green pixels, got {green_pixels}"

    def test_brush_diagonal_stroke(self, helpers: TestHelpers):
        """Test diagonal brush stroke produces expected pixel count."""
        helpers.new_document(200, 200)

        brush_size = 6
        # Diagonal from (30, 30) to (170, 170) = sqrt(140² + 140²) ≈ 198 pixels
        stroke_length = math.sqrt(140**2 + 140**2)

        helpers.tools.brush_stroke(
            [(30, 30), (170, 170)],
            color='#0000FF',
            size=brush_size
        )

        blue_pixels = helpers.pixels.count_pixels_with_color((0, 0, 255, 255), tolerance=10)

        min_expected, max_expected = approx_line_pixels(stroke_length, brush_size, tolerance=0.35)

        assert min_expected <= blue_pixels <= max_expected, \
            f"Diagonal stroke: expected {min_expected}-{max_expected} blue pixels, got {blue_pixels}"

    def test_brush_dot_produces_circle(self, helpers: TestHelpers):
        """Test single brush dot produces approximately circular area."""
        helpers.new_document(200, 200)

        brush_size = 20  # diameter, so radius = 10

        helpers.tools.brush_dot(100, 100, color='#FF0000', size=brush_size)

        red_pixels = helpers.pixels.count_pixels_with_color((255, 0, 0, 255), tolerance=10)

        # Single dot should produce a circle with radius = size/2
        radius = brush_size / 2
        min_expected, max_expected = approx_circle_pixels(radius, tolerance=0.25)

        assert min_expected <= red_pixels <= max_expected, \
            f"Brush dot: expected {min_expected}-{max_expected} red pixels (circle r={radius}), got {red_pixels}"

    def test_brush_on_offset_layer(self, helpers: TestHelpers):
        """Test brush stroke on a layer offset from origin."""
        helpers.new_document(400, 400)

        layer_id = helpers.layers.create_offset_layer(
            offset_x=200, offset_y=200,
            width=150, height=150
        )

        brush_size = 10
        # Draw within the layer bounds: from (220, 275) to (330, 275)
        # But layer ends at x=350, so actual stroke within layer is (220,275) to (330,275)
        # Length within layer ≈ 110 pixels (clamped by layer edge at 350)
        stroke_length_in_layer = 110

        helpers.tools.brush_stroke(
            [(220, 275), (330, 275)],
            color='#00FF00',
            size=brush_size
        )

        green_pixels = helpers.pixels.count_pixels_with_color(
            (0, 255, 0, 255), tolerance=10, layer_id=layer_id
        )

        min_expected, max_expected = approx_line_pixels(stroke_length_in_layer, brush_size, tolerance=0.35)

        assert min_expected <= green_pixels <= max_expected, \
            f"Offset layer stroke: expected {min_expected}-{max_expected} green pixels, got {green_pixels}"

    def test_brush_outside_offset_layer_no_pixels(self, helpers: TestHelpers):
        """Test that brush outside offset layer bounds produces zero pixels on it."""
        helpers.new_document(400, 400)

        layer_id = helpers.layers.create_offset_layer(
            offset_x=300, offset_y=300,
            width=80, height=80
        )

        # Draw far from the offset layer
        helpers.tools.brush_stroke(
            [(10, 10), (100, 100)],
            color='#0000FF',
            size=10
        )

        # Layer should have exactly 0 non-transparent pixels
        layer_pixels = helpers.pixels.count_non_transparent_pixels(layer_id=layer_id)
        assert layer_pixels == 0, \
            f"Brush outside layer bounds should produce 0 pixels on layer, got {layer_pixels}"

    def test_brush_size_scaling(self, helpers: TestHelpers):
        """Test that doubling brush size approximately quadruples dot area."""
        helpers.new_document(300, 200)

        # Small brush dot
        helpers.tools.brush_dot(75, 100, color='#FF0000', size=10)
        small_pixels = helpers.pixels.count_pixels_with_color((255, 0, 0, 255), tolerance=10)

        # Large brush dot (2x size = 4x area for circle)
        helpers.tools.brush_dot(225, 100, color='#00FF00', size=20)
        large_pixels = helpers.pixels.count_pixels_with_color((0, 255, 0, 255), tolerance=10)

        # Ratio should be approximately 4 (±50% for tolerance)
        ratio = large_pixels / small_pixels if small_pixels > 0 else 0
        assert 2.5 <= ratio <= 5.5, \
            f"2x brush size should give ~4x pixels. Got ratio {ratio:.2f} ({small_pixels} vs {large_pixels})"


class TestEraserTool:
    """Tests for the eraser tool."""

    def test_eraser_removes_expected_pixels(self, helpers: TestHelpers):
        """Test eraser removes expected number of pixels from filled layer."""
        helpers.new_document(200, 200)

        helpers.layers.fill_layer_with_color('#FF0000')
        initial_pixels = 200 * 200  # Full layer

        eraser_size = 15
        stroke_length = 100  # horizontal stroke

        helpers.tools.eraser_stroke([(50, 100), (150, 100)], size=eraser_size)

        remaining_red = helpers.pixels.count_pixels_with_color((255, 0, 0, 255), tolerance=10)
        erased_count = initial_pixels - remaining_red

        min_erased, max_erased = approx_line_pixels(stroke_length, eraser_size, tolerance=0.35)

        assert min_erased <= erased_count <= max_erased, \
            f"Eraser should remove {min_erased}-{max_erased} pixels, removed {erased_count}"

    def test_eraser_on_offset_layer(self, helpers: TestHelpers):
        """Test eraser on an offset layer removes expected pixels."""
        helpers.new_document(400, 400)

        layer_id = helpers.layers.create_filled_layer(
            '#00FF00',
            width=100, height=100,
            offset_x=150, offset_y=150
        )

        initial_pixels = 100 * 100  # 10000
        eraser_size = 20
        # Erase horizontally through middle: (150, 200) to (250, 200)
        # Length within layer = 100 pixels
        stroke_length = 100

        helpers.tools.eraser_stroke([(150, 200), (250, 200)], size=eraser_size)

        remaining = helpers.pixels.count_non_transparent_pixels(layer_id=layer_id)
        erased_count = initial_pixels - remaining

        min_erased, max_erased = approx_line_pixels(stroke_length, eraser_size, tolerance=0.35)

        assert min_erased <= erased_count <= max_erased, \
            f"Eraser on offset layer should remove {min_erased}-{max_erased}, removed {erased_count}"

    def test_eraser_outside_offset_layer_no_effect(self, helpers: TestHelpers):
        """Test eraser outside offset layer bounds has no effect."""
        helpers.new_document(400, 400)

        layer_id = helpers.layers.create_filled_layer(
            '#0000FF',
            width=80, height=80,
            offset_x=300, offset_y=300
        )

        initial_pixels = 80 * 80  # 6400

        # Erase far from the layer
        helpers.tools.eraser_stroke([(10, 10), (100, 100)], size=20)

        remaining = helpers.pixels.count_non_transparent_pixels(layer_id=layer_id)

        assert remaining == initial_pixels, \
            f"Eraser outside layer should not affect it. Expected {initial_pixels}, got {remaining}"

    def test_eraser_crossing_layer_edge(self, helpers: TestHelpers):
        """Test eraser stroke crossing into offset layer erases partial stroke."""
        helpers.new_document(400, 400)

        layer_id = helpers.layers.create_filled_layer(
            '#FF00FF',
            width=100, height=100,
            offset_x=100, offset_y=100
        )

        initial_pixels = 100 * 100
        eraser_size = 10

        # Stroke from (50, 150) to (150, 150) - crosses into layer at x=100
        # Only 50 pixels of stroke are inside the layer
        stroke_length_inside = 50

        helpers.tools.eraser_stroke([(50, 150), (150, 150)], size=eraser_size)

        remaining = helpers.pixels.count_non_transparent_pixels(layer_id=layer_id)
        erased_count = initial_pixels - remaining

        min_erased, max_erased = approx_line_pixels(stroke_length_inside, eraser_size, tolerance=0.40)

        assert min_erased <= erased_count <= max_erased, \
            f"Partial crossing should erase {min_erased}-{max_erased}, erased {erased_count}"


class TestUndoRedo:
    """Tests for undo/redo with brush and eraser."""

    def test_undo_restores_exact_pixel_count(self, helpers: TestHelpers):
        """Test that undo restores exact original pixel count."""
        helpers.new_document(200, 200)

        initial_non_transparent = helpers.pixels.count_non_transparent_pixels()
        assert initial_non_transparent == 0, "Fresh document should have 0 non-transparent pixels"

        helpers.tools.brush_stroke([(50, 50), (150, 150)], color='#FF0000', size=10)
        after_draw = helpers.pixels.count_non_transparent_pixels()
        assert after_draw > 0, "Should have pixels after drawing"

        helpers.undo()
        after_undo = helpers.pixels.count_non_transparent_pixels()

        assert after_undo == initial_non_transparent, \
            f"Undo should restore exact count. Initial: {initial_non_transparent}, after undo: {after_undo}"

    def test_redo_restores_exact_pixel_count(self, helpers: TestHelpers):
        """Test that redo restores exact pixel count after undo."""
        helpers.new_document(200, 200)

        helpers.tools.brush_stroke([(50, 50), (150, 150)], color='#FF0000', size=10)
        after_draw = helpers.pixels.count_non_transparent_pixels()

        helpers.undo()
        helpers.redo()
        after_redo = helpers.pixels.count_non_transparent_pixels()

        assert after_redo == after_draw, \
            f"Redo should restore exact count. After draw: {after_draw}, after redo: {after_redo}"

    def test_undo_eraser_restores_exact_count(self, helpers: TestHelpers):
        """Test that undo after eraser restores exact pixel count."""
        helpers.new_document(200, 200)

        helpers.layers.fill_layer_with_color('#00FF00')
        after_fill = helpers.pixels.count_non_transparent_pixels()
        assert after_fill == 200 * 200

        helpers.tools.eraser_stroke([(50, 50), (150, 150)], size=20)
        after_erase = helpers.pixels.count_non_transparent_pixels()
        assert after_erase < after_fill

        helpers.undo()
        after_undo = helpers.pixels.count_non_transparent_pixels()

        assert after_undo == after_fill, \
            f"Undo eraser should restore {after_fill} pixels, got {after_undo}"
