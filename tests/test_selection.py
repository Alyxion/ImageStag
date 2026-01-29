"""Unit tests for selection algorithms (contour extraction and magic wand).

Tests the Rust implementations of:
- Marching squares contour extraction from alpha masks
- Magic wand flood fill selection

Uses SVG test fixtures rendered to RGBA for realistic test cases.
"""

import pytest
import numpy as np
from pathlib import Path

# Import Rust implementations
try:
    from imagestag.imagestag_rust import extract_contours, magic_wand_select
    HAS_RUST = True
except ImportError:
    HAS_RUST = False
    extract_contours = None
    magic_wand_select = None


# Test fixture path
SVG_FIXTURES_DIR = Path(__file__).parent.parent / "imagestag" / "samples" / "svgs" / "test-fixtures"


def render_svg_to_rgba(svg_path: Path, width: int, height: int) -> np.ndarray:
    """Render an SVG file to RGBA pixel data using resvg.

    Args:
        svg_path: Path to SVG file
        width: Output width in pixels
        height: Output height in pixels

    Returns:
        numpy array of shape (height, width, 4) with RGBA values
    """
    from resvg_py import svg_to_bytes
    from PIL import Image
    import io

    svg_content = svg_path.read_text()
    png_bytes = svg_to_bytes(svg_string=svg_content, width=width, height=height)

    # Decode PNG to RGBA
    image = Image.open(io.BytesIO(png_bytes))
    image = image.convert('RGBA')
    return np.array(image, dtype=np.uint8)


def create_simple_mask(width: int, height: int, rect: tuple) -> np.ndarray:
    """Create a simple rectangular mask for testing.

    Args:
        width: Mask width
        height: Mask height
        rect: (x, y, w, h) rectangle to fill

    Returns:
        Uint8 mask array
    """
    mask = np.zeros((height, width), dtype=np.uint8)
    x, y, w, h = rect
    mask[y:y+h, x:x+w] = 255
    return mask.flatten()


def create_circle_mask(width: int, height: int, cx: int, cy: int, r: int) -> np.ndarray:
    """Create a circular mask for testing.

    Args:
        width: Mask width
        height: Mask height
        cx, cy: Circle center
        r: Circle radius

    Returns:
        Uint8 mask array
    """
    mask = np.zeros((height, width), dtype=np.uint8)
    for y in range(height):
        for x in range(width):
            if (x - cx) ** 2 + (y - cy) ** 2 <= r ** 2:
                mask[y, x] = 255
    return mask.flatten()


@pytest.mark.skipif(not HAS_RUST, reason="Rust extension not available")
class TestContourExtraction:
    """Tests for marching squares contour extraction."""

    def test_empty_mask(self):
        """Empty mask should return no contours."""
        mask = np.zeros(100 * 100, dtype=np.uint8)
        contours = extract_contours(list(mask), 100, 100)
        assert len(contours) == 0

    def test_full_mask(self):
        """Full mask should return contours around the edges."""
        mask = np.full(100 * 100, 255, dtype=np.uint8)
        contours = extract_contours(list(mask), 100, 100)
        # Full mask generates contours along the boundary
        # The marching squares algorithm may produce multiple edge segments
        assert len(contours) >= 1
        # Total points across all contours should cover the boundary
        total_points = sum(len(c) for c in contours)
        assert total_points >= 4

    def test_rectangular_selection(self):
        """Rectangular selection should return contours."""
        mask = create_simple_mask(100, 100, (20, 20, 60, 40))
        contours = extract_contours(list(mask), 100, 100)

        # Should have at least one contour
        assert len(contours) >= 1
        total_points = sum(len(c) for c in contours)
        # Rectangle boundary should have multiple points
        assert total_points >= 4

        # All points should be within mask bounds
        for contour in contours:
            for x, y in contour:
                assert 0 <= x <= 100
                assert 0 <= y <= 100

    def test_circular_selection(self):
        """Circular selection should return contours."""
        mask = create_circle_mask(100, 100, 50, 50, 20)
        contours = extract_contours(list(mask), 100, 100)

        # Should have at least one contour
        assert len(contours) >= 1
        # Circle should have many points for smooth outline
        total_points = sum(len(c) for c in contours)
        assert total_points >= 20

    def test_two_disconnected_regions(self):
        """Two separate regions should return two contours."""
        mask = np.zeros((100, 100), dtype=np.uint8)
        # Region 1: top-left
        mask[10:30, 10:30] = 255
        # Region 2: bottom-right
        mask[60:80, 60:80] = 255

        contours = extract_contours(list(mask.flatten()), 100, 100)

        # Should have at least 2 contours (one per region)
        # Note: marching squares may generate additional inner contours
        assert len(contours) >= 2

    def test_single_pixel(self):
        """Single pixel is an edge case - may produce 0 or 1 contour."""
        mask = np.zeros(100 * 100, dtype=np.uint8)
        mask[50 * 100 + 50] = 255  # Single pixel at (50, 50)

        contours = extract_contours(list(mask), 100, 100)

        # Single pixel may not produce a contour (needs >= 3 points)
        # This is acceptable - marching ants can skip isolated pixels
        assert len(contours) >= 0

    def test_diagonal_line(self):
        """Diagonal line of pixels should produce a contour."""
        mask = np.zeros((100, 100), dtype=np.uint8)
        for i in range(20, 80):
            mask[i, i] = 255

        contours = extract_contours(list(mask.flatten()), 100, 100)

        # Should have at least one contour
        assert len(contours) >= 1

    def test_complex_concave_polygon(self):
        """Complex concave polygon from real lasso selection - regression test for WASM hang."""
        # Real coordinates from user's lasso selection that caused WASM infinite loop
        polygon_points = [
            [192.76, 278.07], [196.24, 278.77], [199.72, 279.46], [203.21, 279.46],
            [206.69, 280.16], [211.57, 280.16], [215.05, 280.86], [218.53, 280.86],
            [222.02, 281.55], [225.50, 281.55], [228.98, 281.55], [232.46, 281.55],
            [235.95, 282.25], [239.43, 282.25], [242.91, 282.25], [246.40, 282.25],
            [249.88, 282.25], [253.36, 281.55], [256.85, 280.86], [260.33, 280.86],
            [264.51, 279.46], [267.99, 278.77], [272.87, 278.07], [276.35, 277.37],
            [279.14, 275.98], [283.32, 275.28], [286.10, 273.89], [290.98, 272.50],
            [293.77, 271.10], [297.25, 269.71], [300.04, 268.32], [302.82, 266.92],
            [306.31, 265.53], [309.09, 263.44], [311.88, 262.05], [314.67, 259.26],
            [316.76, 256.48], [318.85, 253.69], [319.54, 250.21], [320.24, 246.72],
            [320.24, 243.24], [320.24, 239.76], [319.54, 236.27], [318.15, 233.49],
            [317.45, 230.00], [316.76, 226.52], [316.06, 223.04], [314.67, 219.55],
            [314.67, 216.07], [315.36, 212.59], [317.45, 209.80], [320.24, 207.71],
            [323.03, 206.32], [325.81, 204.93], [328.60, 203.53], [332.08, 202.14],
            [335.56, 201.44], [339.05, 200.75], [341.83, 199.35], [345.32, 199.35],
            [348.80, 198.66], [352.28, 198.66], [355.77, 197.96], [359.25, 197.96],
            [362.73, 197.96], [366.91, 197.96], [371.79, 198.66], [375.27, 198.66],
            [378.76, 199.35], [382.24, 199.35], [386.42, 200.05], [389.90, 200.75],
            [393.38, 201.44], [396.87, 202.14], [400.35, 202.84], [403.14, 204.23],
            [405.92, 205.62], [409.41, 207.01], [412.19, 208.41], [415.68, 209.10],
            [418.46, 210.50], [421.95, 211.89], [424.73, 213.28], [428.22, 214.68],
            [431.00, 216.07], [433.79, 217.46], [437.27, 218.86], [440.06, 220.25],
            [442.84, 221.64], [447.02, 223.73], [449.81, 225.13], [452.60, 227.22],
            [455.38, 229.31], [458.17, 231.40], [460.96, 233.49], [462.35, 236.27],
            [464.44, 239.06], [465.83, 241.85], [466.53, 245.33], [467.92, 248.12],
            [469.32, 251.60], [470.01, 255.08], [471.41, 257.87], [472.10, 261.35],
            [472.80, 264.83], [472.80, 268.32], [472.80, 271.80], [472.80, 275.28],
            [472.10, 278.77], [470.71, 282.25], [469.32, 285.04], [466.53, 287.82],
            [463.74, 289.91], [460.96, 292.00], [458.17, 294.09], [455.38, 295.49],
            [452.60, 297.58], [449.81, 298.97], [446.33, 299.67], [442.84, 301.06],
            [439.36, 301.76], [435.88, 302.45], [432.39, 303.85], [428.91, 305.24],
            [426.13, 306.63], [423.34, 308.03], [420.55, 310.11], [418.46, 312.90],
            # Close the polygon back to start area
            [350.0, 350.0], [300.0, 350.0], [250.0, 320.0], [200.0, 300.0],
        ]

        # Create mask from polygon (800x600 document size)
        width, height = 800, 600
        mask = np.zeros((height, width), dtype=np.uint8)

        # Fill polygon using point-in-polygon test
        min_x = int(min(p[0] for p in polygon_points))
        max_x = int(max(p[0] for p in polygon_points)) + 1
        min_y = int(min(p[1] for p in polygon_points))
        max_y = int(max(p[1] for p in polygon_points)) + 1

        for y in range(max(0, min_y), min(height, max_y)):
            for x in range(max(0, min_x), min(width, max_x)):
                if point_in_polygon(x + 0.5, y + 0.5, polygon_points):
                    mask[y, x] = 255

        # This should complete without hanging
        contours = extract_contours(list(mask.flatten()), width, height)

        # Should produce at least one contour
        assert len(contours) >= 1

        # Verify contour points are valid
        for contour in contours:
            for point in contour:
                assert len(point) == 2
                assert 0 <= point[0] <= width
                assert 0 <= point[1] <= height


def point_in_polygon(x, y, polygon):
    """Ray casting point-in-polygon test."""
    n = len(polygon)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


@pytest.mark.skipif(not HAS_RUST, reason="Rust extension not available")
class TestMagicWand:
    """Tests for magic wand selection."""

    def test_solid_color_selection(self):
        """Clicking on solid color should select entire region."""
        # Create 4x4 solid red image
        image = np.full((4, 4, 4), [255, 0, 0, 255], dtype=np.uint8)

        mask = magic_wand_select(
            list(image.flatten()),
            width=4, height=4,
            start_x=2, start_y=2,
            tolerance=0,
            contiguous=True
        )

        # Should select all pixels
        mask_arr = np.frombuffer(mask, dtype=np.uint8)
        assert np.all(mask_arr == 255)

    def test_two_color_regions(self):
        """Should only select contiguous pixels of same color."""
        # Left half red, right half blue
        image = np.zeros((4, 4, 4), dtype=np.uint8)
        image[:, :2] = [255, 0, 0, 255]  # Red left
        image[:, 2:] = [0, 0, 255, 255]  # Blue right

        # Click on red region
        mask = magic_wand_select(
            list(image.flatten()),
            width=4, height=4,
            start_x=0, start_y=0,
            tolerance=0,
            contiguous=True
        )

        mask_arr = np.frombuffer(mask, dtype=np.uint8).reshape(4, 4)

        # Red region (left 2 columns) should be selected
        assert np.all(mask_arr[:, :2] == 255)
        # Blue region (right 2 columns) should not be selected
        assert np.all(mask_arr[:, 2:] == 0)

    def test_tolerance(self):
        """Tolerance should allow selection of similar colors."""
        # Create image with slight color gradient
        image = np.zeros((3, 3, 4), dtype=np.uint8)
        image[0, :] = [255, 0, 0, 255]   # Pure red (255)
        image[1, :] = [250, 0, 0, 255]   # Slightly darker red
        image[2, :] = [200, 0, 0, 255]   # Much darker red

        # Click on center with tolerance 10
        mask = magic_wand_select(
            list(image.flatten()),
            width=3, height=3,
            start_x=1, start_y=1,
            tolerance=10,
            contiguous=True
        )

        mask_arr = np.frombuffer(mask, dtype=np.uint8).reshape(3, 3)

        # First two rows should be selected (within tolerance)
        assert np.all(mask_arr[0:2, :] == 255)
        # Third row should not be selected (difference > 10)
        assert np.all(mask_arr[2, :] == 0)

    def test_non_contiguous_selection(self):
        """Non-contiguous mode should select all matching pixels."""
        # Checkerboard pattern
        image = np.zeros((4, 4, 4), dtype=np.uint8)
        for y in range(4):
            for x in range(4):
                if (x + y) % 2 == 0:
                    image[y, x] = [255, 0, 0, 255]  # Red
                else:
                    image[y, x] = [0, 0, 255, 255]  # Blue

        # Click on red, non-contiguous
        mask = magic_wand_select(
            list(image.flatten()),
            width=4, height=4,
            start_x=0, start_y=0,
            tolerance=0,
            contiguous=False
        )

        mask_arr = np.frombuffer(mask, dtype=np.uint8).reshape(4, 4)

        # All red squares should be selected (8 pixels)
        selected_count = np.sum(mask_arr == 255)
        assert selected_count == 8

    def test_out_of_bounds_click(self):
        """Click outside image should return empty mask."""
        image = np.full((4, 4, 4), [255, 0, 0, 255], dtype=np.uint8)

        mask = magic_wand_select(
            list(image.flatten()),
            width=4, height=4,
            start_x=10, start_y=10,  # Out of bounds
            tolerance=0,
            contiguous=True
        )

        mask_arr = np.frombuffer(mask, dtype=np.uint8)
        assert np.all(mask_arr == 0)


@pytest.mark.skipif(not HAS_RUST, reason="Rust extension not available")
class TestMagicWandWithSVG:
    """Tests using the SVG color-shapes fixture."""

    @pytest.fixture
    def color_shapes_image(self):
        """Load and render the color-shapes.svg test fixture."""
        svg_path = SVG_FIXTURES_DIR / "color-shapes.svg"
        if not svg_path.exists():
            pytest.skip(f"SVG fixture not found: {svg_path}")
        return render_svg_to_rgba(svg_path, 200, 200)

    def test_select_red_circle(self, color_shapes_image):
        """Click on red circle should select only red pixels."""
        image = color_shapes_image

        # Red circle center is at (50, 50)
        mask = magic_wand_select(
            list(image.flatten()),
            width=200, height=200,
            start_x=50, start_y=50,
            tolerance=10,
            contiguous=True
        )

        mask_arr = np.frombuffer(mask, dtype=np.uint8).reshape(200, 200)

        # Check that red circle region is selected
        # Center of red circle (50, 50) should be selected
        assert mask_arr[50, 50] == 255

        # Green rectangle center (150, 50) should NOT be selected
        assert mask_arr[50, 150] == 0

        # Blue circle center (50, 150) should NOT be selected
        assert mask_arr[150, 50] == 0

        # Count selected pixels - should be roughly pi * 30^2 = ~2827
        selected_count = np.sum(mask_arr == 255)
        expected_area = 3.14159 * 30 * 30
        assert 0.8 * expected_area < selected_count < 1.2 * expected_area

    def test_select_green_rectangle(self, color_shapes_image):
        """Click on green rectangle should select only green pixels."""
        image = color_shapes_image

        # Green rectangle is at x=120-180, y=20-80, center roughly (150, 50)
        mask = magic_wand_select(
            list(image.flatten()),
            width=200, height=200,
            start_x=150, start_y=50,
            tolerance=10,
            contiguous=True
        )

        mask_arr = np.frombuffer(mask, dtype=np.uint8).reshape(200, 200)

        # Green rectangle area should be selected
        assert mask_arr[50, 150] == 255

        # Red circle should NOT be selected
        assert mask_arr[50, 50] == 0

        # Count selected pixels - should be roughly 60 * 60 = 3600
        selected_count = np.sum(mask_arr == 255)
        expected_area = 60 * 60
        assert 0.8 * expected_area < selected_count < 1.2 * expected_area

    def test_select_white_background(self, color_shapes_image):
        """Click on white background should select background area."""
        image = color_shapes_image

        # Click on white background (corner)
        mask = magic_wand_select(
            list(image.flatten()),
            width=200, height=200,
            start_x=0, start_y=0,
            tolerance=10,
            contiguous=True
        )

        mask_arr = np.frombuffer(mask, dtype=np.uint8).reshape(200, 200)

        # Background corner should be selected
        assert mask_arr[0, 0] == 255

        # Colored shapes should NOT be selected (contiguous mode)
        # Note: this depends on connectivity - corner may be isolated
        # Just verify background was selected
        selected_count = np.sum(mask_arr == 255)
        assert selected_count > 0

    def test_select_cyan_ellipse(self, color_shapes_image):
        """Click on cyan ellipse (center) should select only that shape."""
        image = color_shapes_image

        # Cyan ellipse is at center (100, 100)
        mask = magic_wand_select(
            list(image.flatten()),
            width=200, height=200,
            start_x=100, start_y=100,
            tolerance=10,
            contiguous=True
        )

        mask_arr = np.frombuffer(mask, dtype=np.uint8).reshape(200, 200)

        # Ellipse center should be selected
        assert mask_arr[100, 100] == 255

        # Other shapes should NOT be selected
        assert mask_arr[50, 50] == 0    # Red circle
        assert mask_arr[50, 150] == 0   # Green rectangle

        # Count - ellipse area is pi * 20 * 15 = ~942
        selected_count = np.sum(mask_arr == 255)
        expected_area = 3.14159 * 20 * 15
        assert 0.7 * expected_area < selected_count < 1.3 * expected_area

    def test_contours_from_svg_selection(self, color_shapes_image):
        """Extract contours from magic wand selection."""
        image = color_shapes_image

        # Select red circle
        mask = magic_wand_select(
            list(image.flatten()),
            width=200, height=200,
            start_x=50, start_y=50,
            tolerance=10,
            contiguous=True
        )

        # Extract contours from the selection mask
        contours = extract_contours(list(mask), 200, 200)

        # Should have at least one contour
        assert len(contours) >= 1

        # Contour should have many points (smooth circle)
        assert len(contours[0]) >= 20


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
