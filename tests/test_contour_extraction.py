"""
Tests for contour extraction filter.

Tests cover:
- Basic contour extraction from simple shapes
- Simplification with Douglas-Peucker
- Bezier curve fitting
- SVG output generation
- Error handling for invalid inputs
"""

import numpy as np
import pytest
from imagestag.filters.contour import (
    extract_contours,
    contours_to_svg,
    extract_contours_to_svg,
    Point,
    BezierSegment,
    Contour,
    ContourExtractor,
    douglas_peucker,
    douglas_peucker_closed,
)


class TestExtractContours:
    """Tests for basic contour extraction."""

    def test_extract_contours_circle(self):
        """Extract contours from a circular mask."""
        # Create a 100x100 mask with a circle
        mask = np.zeros((100, 100), dtype=np.uint8)
        y, x = np.ogrid[:100, :100]
        mask[(x - 50)**2 + (y - 50)**2 < 30**2] = 255

        contours = extract_contours(mask, threshold=0.5)

        assert len(contours) == 1
        assert contours[0].is_closed is True
        assert len(contours[0].points) > 10  # Should have multiple points

    def test_extract_contours_square(self):
        """Extract contours from a square mask."""
        mask = np.zeros((100, 100), dtype=np.uint8)
        mask[20:80, 20:80] = 255

        contours = extract_contours(mask, threshold=0.5)

        assert len(contours) == 1
        assert contours[0].is_closed is True

    def test_extract_contours_empty_mask(self):
        """Empty mask should produce no contours."""
        mask = np.zeros((100, 100), dtype=np.uint8)
        contours = extract_contours(mask, threshold=0.5)
        assert len(contours) == 0

    def test_extract_contours_full_mask(self):
        """Full mask should produce no contours (no edges)."""
        mask = np.full((100, 100), 255, dtype=np.uint8)
        contours = extract_contours(mask, threshold=0.5)
        assert len(contours) == 0

    def test_extract_contours_threshold(self):
        """Test that threshold parameter works correctly."""
        mask = np.zeros((100, 100), dtype=np.uint8)
        mask[20:80, 20:80] = 128  # Half-intensity

        # With low threshold, should find contours
        contours_low = extract_contours(mask, threshold=0.3)
        assert len(contours_low) == 1

        # With high threshold, should find no contours
        contours_high = extract_contours(mask, threshold=0.7)
        assert len(contours_high) == 0


class TestSimplification:
    """Tests for Douglas-Peucker simplification."""

    def test_simplification_reduces_points(self):
        """Simplification should reduce point count."""
        mask = np.zeros((100, 100), dtype=np.uint8)
        y, x = np.ogrid[:100, :100]
        mask[(x - 50)**2 + (y - 50)**2 < 30**2] = 255

        # Raw extraction
        contours_raw = extract_contours(mask, simplify_epsilon=0.0)

        # Simplified
        contours_simplified = extract_contours(mask, simplify_epsilon=0.5)

        assert len(contours_raw) == 1
        assert len(contours_simplified) == 1
        assert len(contours_simplified[0].points) < len(contours_raw[0].points)

    def test_simplification_preserves_closure(self):
        """Simplification should preserve contour closure."""
        mask = np.zeros((100, 100), dtype=np.uint8)
        mask[20:80, 20:80] = 255

        contours = extract_contours(mask, simplify_epsilon=0.5)

        assert len(contours) == 1
        assert contours[0].is_closed is True

    def test_higher_epsilon_more_simplification(self):
        """Higher epsilon should produce fewer points."""
        mask = np.zeros((100, 100), dtype=np.uint8)
        y, x = np.ogrid[:100, :100]
        mask[(x - 50)**2 + (y - 50)**2 < 30**2] = 255

        contours_eps03 = extract_contours(mask, simplify_epsilon=0.3)
        contours_eps05 = extract_contours(mask, simplify_epsilon=0.5)

        assert len(contours_eps05[0].points) <= len(contours_eps03[0].points)


class TestBezierFitting:
    """Tests for Bezier curve fitting."""

    def test_bezier_fitting_produces_curves(self):
        """Bezier fitting should produce curve segments."""
        mask = np.zeros((100, 100), dtype=np.uint8)
        y, x = np.ogrid[:100, :100]
        mask[(x - 50)**2 + (y - 50)**2 < 30**2] = 255

        contours = extract_contours(
            mask,
            simplify_epsilon=0.5,
            fit_beziers=True,
            bezier_smoothness=0.25,
        )

        assert len(contours) == 1
        assert contours[0].beziers is not None
        assert len(contours[0].beziers) > 0

    def test_bezier_segments_are_valid(self):
        """Bezier segments should have valid control points."""
        mask = np.zeros((100, 100), dtype=np.uint8)
        mask[20:80, 20:80] = 255

        contours = extract_contours(
            mask,
            simplify_epsilon=0.5,
            fit_beziers=True,
        )

        assert len(contours) == 1
        for bez in contours[0].beziers:
            # All control points should be within image bounds (with margin)
            for pt in [bez.p0, bez.p1, bez.p2, bez.p3]:
                assert -10 <= pt.x <= 110
                assert -10 <= pt.y <= 110

    def test_bezier_segments_connect(self):
        """Bezier segments should connect end-to-end."""
        mask = np.zeros((100, 100), dtype=np.uint8)
        y, x = np.ogrid[:100, :100]
        mask[(x - 50)**2 + (y - 50)**2 < 30**2] = 255

        contours = extract_contours(
            mask,
            simplify_epsilon=0.5,
            fit_beziers=True,
        )

        assert len(contours) == 1
        beziers = contours[0].beziers
        assert beziers is not None

        # Each segment's p0 should be close to previous segment's p3
        for i in range(1, len(beziers)):
            prev_end = beziers[i - 1].p3
            curr_start = beziers[i].p0
            distance = np.sqrt(
                (prev_end.x - curr_start.x)**2 +
                (prev_end.y - curr_start.y)**2
            )
            assert distance < 0.01  # Should be essentially the same point


class TestSvgOutput:
    """Tests for SVG output generation."""

    def test_contours_to_svg_basic(self):
        """Basic SVG generation should work."""
        mask = np.zeros((100, 100), dtype=np.uint8)
        mask[20:80, 20:80] = 255

        contours = extract_contours(mask, simplify_epsilon=0.5)
        svg = contours_to_svg(contours, 100, 100)

        assert '<svg' in svg
        assert '</svg>' in svg
        assert '<path' in svg
        assert 'viewBox="0 0 100 100"' in svg

    def test_contours_to_svg_with_background(self):
        """SVG with background should include rect."""
        mask = np.zeros((100, 100), dtype=np.uint8)
        mask[20:80, 20:80] = 255

        contours = extract_contours(mask, simplify_epsilon=0.5)
        svg = contours_to_svg(
            contours, 100, 100,
            background_color="#000000"
        )

        assert '<rect' in svg
        assert 'fill="#000000"' in svg

    def test_contours_to_svg_with_stroke(self):
        """SVG with stroke should include stroke attributes."""
        mask = np.zeros((100, 100), dtype=np.uint8)
        mask[20:80, 20:80] = 255

        contours = extract_contours(mask, simplify_epsilon=0.5)
        svg = contours_to_svg(
            contours, 100, 100,
            stroke_color="#FF0000",
            stroke_width=2.0,
        )

        assert 'stroke="#FF0000"' in svg
        assert 'stroke-width="2.00"' in svg

    def test_extract_contours_to_svg_convenience(self):
        """Convenience function should work end-to-end."""
        mask = np.zeros((100, 100), dtype=np.uint8)
        mask[20:80, 20:80] = 255

        svg = extract_contours_to_svg(
            mask,
            simplify_epsilon=0.5,
            fit_beziers=True,
            fill_color="#FFFFFF",
            background_color="#000000",
        )

        assert '<svg' in svg
        assert '</svg>' in svg
        assert '<path' in svg
        assert '<rect' in svg

    def test_svg_path_data_format(self):
        """SVG path data should use correct format."""
        mask = np.zeros((100, 100), dtype=np.uint8)
        mask[20:80, 20:80] = 255

        # Polyline (no beziers)
        contours = extract_contours(mask, simplify_epsilon=0.5, fit_beziers=False)
        svg = contours_to_svg(contours, 100, 100)
        assert 'd="M' in svg  # Should have move command
        assert ' L ' in svg or 'L ' in svg  # Should have line commands
        assert ' Z"' in svg or 'Z"' in svg  # Should be closed

    def test_svg_bezier_path_data_format(self):
        """SVG Bezier path should use C commands."""
        mask = np.zeros((100, 100), dtype=np.uint8)
        y, x = np.ogrid[:100, :100]
        mask[(x - 50)**2 + (y - 50)**2 < 30**2] = 255

        contours = extract_contours(mask, simplify_epsilon=0.5, fit_beziers=True)
        svg = contours_to_svg(contours, 100, 100)

        assert 'd="M' in svg  # Should have move command
        assert ' C ' in svg or 'C ' in svg  # Should have cubic bezier commands


class TestInputValidation:
    """Tests for input validation."""

    def test_3d_rgba_input(self):
        """3D RGBA input should extract alpha channel."""
        rgba = np.zeros((100, 100, 4), dtype=np.uint8)
        rgba[20:80, 20:80, 3] = 255  # Alpha channel

        contours = extract_contours(rgba, simplify_epsilon=0.5)

        assert len(contours) == 1
        assert contours[0].is_closed is True

    def test_float32_input(self):
        """Float32 input (0.0-1.0) should work."""
        mask = np.zeros((100, 100), dtype=np.float32)
        mask[20:80, 20:80] = 1.0

        contours = extract_contours(mask, simplify_epsilon=0.5)

        assert len(contours) == 1

    def test_invalid_shape_raises_error(self):
        """Invalid shape should raise ValueError."""
        mask = np.zeros((100,), dtype=np.uint8)  # 1D array

        with pytest.raises(ValueError, match="2D or 3D"):
            extract_contours(mask)

    def test_invalid_dtype_raises_error(self):
        """Invalid dtype should raise ValueError."""
        mask = np.zeros((100, 100), dtype=np.int32)

        with pytest.raises(ValueError, match="dtype"):
            extract_contours(mask)


class TestContourDataClasses:
    """Tests for Contour data classes."""

    def test_point_to_tuple(self):
        """Point.to_tuple should return (x, y)."""
        p = Point(x=10.5, y=20.3)
        assert p.to_tuple() == (10.5, 20.3)

    def test_bezier_to_tuple(self):
        """BezierSegment.to_tuple should return nested tuples."""
        bez = BezierSegment(
            p0=Point(0, 0),
            p1=Point(1, 2),
            p2=Point(3, 2),
            p3=Point(4, 0),
        )
        expected = ((0, 0), (1, 2), (3, 2), (4, 0))
        assert bez.to_tuple() == expected

    def test_contour_to_dict(self):
        """Contour.to_dict should return dict representation."""
        contour = Contour(
            points=[Point(0, 0), Point(10, 0), Point(10, 10)],
            is_closed=True,
            beziers=None,
        )
        d = contour.to_dict()
        assert d['points'] == [(0, 0), (10, 0), (10, 10)]
        assert d['is_closed'] is True
        assert 'beziers' not in d

    def test_contour_to_svg_path(self):
        """Contour.to_svg_path should generate valid path string."""
        contour = Contour(
            points=[Point(0, 0), Point(10, 0), Point(10, 10)],
            is_closed=True,
            beziers=None,
        )
        path = contour.to_svg_path()
        assert path.startswith('M ')
        assert ' L ' in path
        assert path.endswith(' Z')


class TestRustBackend:
    """Verify contour extraction uses Rust backend."""

    def test_rust_backend_available(self):
        """Rust backend must be available."""
        from imagestag import imagestag_rust
        assert hasattr(imagestag_rust, 'extract_contours_precise')

    def test_rust_backend_returns_correct_format(self):
        """Rust backend should return list of dicts with correct keys."""
        from imagestag import imagestag_rust

        mask = np.zeros((50, 50), dtype=np.uint8)
        mask[10:40, 10:40] = 255

        result = imagestag_rust.extract_contours_precise(
            mask=mask.flatten().tolist(),
            width=50,
            height=50,
            threshold=0.5,
            simplify_epsilon=0.5,
            fit_beziers=False,
            bezier_smoothness=0.25,
        )

        assert len(result) == 1
        assert 'points' in result[0]
        assert 'is_closed' in result[0]
        assert isinstance(result[0]['points'], list)
        assert isinstance(result[0]['is_closed'], bool)


class TestSvgReconstruction:
    """Tests using actual SVG files to measure reconstruction quality."""

    # Maximum allowed pixel difference percentage for various configs
    # Note: Using 256x256 for faster tests results in higher diff than 512x512
    MAX_DIFF_RAW = 4.0  # Raw marching squares
    MAX_DIFF_SIMPLIFIED = 4.5  # Simplified polyline
    MAX_DIFF_BEZIER = 5.0  # Bezier curves

    @pytest.fixture
    def svg_test_data(self):
        """Load test SVG files and render to masks."""
        from pathlib import Path
        from PIL import Image
        from resvg_py import svg_to_bytes
        import io

        project_root = Path(__file__).parent.parent
        svg_files = {
            'deer': project_root / "imagestag/samples/svgs/noto-emoji/deer.svg",
            'male_deer': project_root / "imagestag/samples/svgs/openclipart/male-deer.svg",
        }

        test_data = {}
        size = 256  # Use smaller size for faster tests

        for name, svg_path in svg_files.items():
            if not svg_path.exists():
                continue

            # Render SVG to RGBA
            png_bytes = svg_to_bytes(
                svg_path=str(svg_path),
                width=size,
                height=size,
                background=None,
            )
            img = Image.open(io.BytesIO(png_bytes)).convert('RGBA')
            rgba = np.array(img)

            # Extract alpha mask
            mask = rgba[:, :, 3]

            # Create reference image (white silhouette on black)
            reference = np.zeros((size, size, 4), dtype=np.uint8)
            reference[:, :, 0] = mask
            reference[:, :, 1] = mask
            reference[:, :, 2] = mask
            reference[:, :, 3] = 255

            test_data[name] = {
                'mask': mask,
                'reference': reference,
                'size': size,
            }

        return test_data

    def _render_svg_string(self, svg_content: str, size: int) -> np.ndarray:
        """Render SVG string to RGBA numpy array."""
        from PIL import Image
        from resvg_py import svg_to_bytes
        import io

        png_bytes = svg_to_bytes(
            svg_string=svg_content,
            width=size,
            height=size,
            background=None,
        )
        img = Image.open(io.BytesIO(png_bytes)).convert('RGBA')
        return np.array(img)

    def _compute_diff(self, img1: np.ndarray, img2: np.ndarray) -> float:
        """Compute percentage of pixels that differ significantly."""
        if img1.shape != img2.shape:
            raise ValueError(f"Shape mismatch: {img1.shape} vs {img2.shape}")

        # Compare RGB channels
        rgb1 = img1[:, :, :3].astype(np.float32)
        rgb2 = img2[:, :, :3].astype(np.float32)
        diff = np.mean(np.abs(rgb1 - rgb2), axis=2)

        # Count pixels with significant difference (> 5 out of 255)
        diff_mask = diff > 5
        diff_count = np.sum(diff_mask)
        total_pixels = img1.shape[0] * img1.shape[1]

        return diff_count / total_pixels * 100

    def test_deer_raw_extraction(self, svg_test_data):
        """Test raw contour extraction on deer SVG."""
        if 'deer' not in svg_test_data:
            pytest.skip("deer.svg not found")

        data = svg_test_data['deer']
        contours = extract_contours(data['mask'], threshold=0.5, simplify_epsilon=0.0)

        assert len(contours) >= 1
        assert contours[0].is_closed

        # Render and compare
        svg = contours_to_svg(
            contours, data['size'], data['size'],
            fill_color="#FFFFFF",
            background_color="#000000",
        )
        rendered = self._render_svg_string(svg, data['size'])
        diff = self._compute_diff(data['reference'], rendered)

        assert diff < self.MAX_DIFF_RAW, f"Deer raw extraction diff {diff:.2f}% exceeds {self.MAX_DIFF_RAW}%"

    def test_deer_simplified_extraction(self, svg_test_data):
        """Test simplified contour extraction on deer SVG."""
        if 'deer' not in svg_test_data:
            pytest.skip("deer.svg not found")

        data = svg_test_data['deer']
        contours = extract_contours(
            data['mask'],
            threshold=0.5,
            simplify_epsilon=0.5,
        )

        assert len(contours) >= 1

        # Render and compare
        svg = contours_to_svg(
            contours, data['size'], data['size'],
            fill_color="#FFFFFF",
            background_color="#000000",
        )
        rendered = self._render_svg_string(svg, data['size'])
        diff = self._compute_diff(data['reference'], rendered)

        assert diff < self.MAX_DIFF_SIMPLIFIED, f"Deer simplified diff {diff:.2f}% exceeds {self.MAX_DIFF_SIMPLIFIED}%"

    def test_deer_bezier_extraction(self, svg_test_data):
        """Test Bezier contour extraction on deer SVG."""
        if 'deer' not in svg_test_data:
            pytest.skip("deer.svg not found")

        data = svg_test_data['deer']
        contours = extract_contours(
            data['mask'],
            threshold=0.5,
            simplify_epsilon=0.5,
            fit_beziers=True,
            bezier_smoothness=0.25,
        )

        assert len(contours) >= 1
        assert contours[0].beziers is not None

        # Render and compare
        svg = contours_to_svg(
            contours, data['size'], data['size'],
            fill_color="#FFFFFF",
            background_color="#000000",
        )
        rendered = self._render_svg_string(svg, data['size'])
        diff = self._compute_diff(data['reference'], rendered)

        assert diff < self.MAX_DIFF_BEZIER, f"Deer Bezier diff {diff:.2f}% exceeds {self.MAX_DIFF_BEZIER}%"

    def test_male_deer_raw_extraction(self, svg_test_data):
        """Test raw contour extraction on male-deer SVG."""
        if 'male_deer' not in svg_test_data:
            pytest.skip("male-deer.svg not found")

        data = svg_test_data['male_deer']
        contours = extract_contours(data['mask'], threshold=0.5, simplify_epsilon=0.0)

        assert len(contours) >= 1

        # Render and compare
        svg = contours_to_svg(
            contours, data['size'], data['size'],
            fill_color="#FFFFFF",
            background_color="#000000",
        )
        rendered = self._render_svg_string(svg, data['size'])
        diff = self._compute_diff(data['reference'], rendered)

        assert diff < self.MAX_DIFF_RAW, f"Male-deer raw extraction diff {diff:.2f}% exceeds {self.MAX_DIFF_RAW}%"

    def test_male_deer_simplified_extraction(self, svg_test_data):
        """Test simplified contour extraction on male-deer SVG."""
        if 'male_deer' not in svg_test_data:
            pytest.skip("male-deer.svg not found")

        data = svg_test_data['male_deer']
        contours = extract_contours(
            data['mask'],
            threshold=0.5,
            simplify_epsilon=0.5,
        )

        assert len(contours) >= 1

        # Render and compare
        svg = contours_to_svg(
            contours, data['size'], data['size'],
            fill_color="#FFFFFF",
            background_color="#000000",
        )
        rendered = self._render_svg_string(svg, data['size'])
        diff = self._compute_diff(data['reference'], rendered)

        assert diff < self.MAX_DIFF_SIMPLIFIED, f"Male-deer simplified diff {diff:.2f}% exceeds {self.MAX_DIFF_SIMPLIFIED}%"

    def test_male_deer_bezier_extraction(self, svg_test_data):
        """Test Bezier contour extraction on male-deer SVG."""
        if 'male_deer' not in svg_test_data:
            pytest.skip("male-deer.svg not found")

        data = svg_test_data['male_deer']
        contours = extract_contours(
            data['mask'],
            threshold=0.5,
            simplify_epsilon=0.5,
            fit_beziers=True,
            bezier_smoothness=0.25,
        )

        assert len(contours) >= 1
        assert contours[0].beziers is not None

        # Render and compare
        svg = contours_to_svg(
            contours, data['size'], data['size'],
            fill_color="#FFFFFF",
            background_color="#000000",
        )
        rendered = self._render_svg_string(svg, data['size'])
        diff = self._compute_diff(data['reference'], rendered)

        assert diff < self.MAX_DIFF_BEZIER, f"Male-deer Bezier diff {diff:.2f}% exceeds {self.MAX_DIFF_BEZIER}%"

    def test_simplification_reduces_points_deer(self, svg_test_data):
        """Verify simplification reduces point count on real SVG."""
        if 'deer' not in svg_test_data:
            pytest.skip("deer.svg not found")

        data = svg_test_data['deer']

        raw = extract_contours(data['mask'], simplify_epsilon=0.0)
        simplified = extract_contours(data['mask'], simplify_epsilon=0.5)

        raw_points = sum(len(c.points) for c in raw)
        simplified_points = sum(len(c.points) for c in simplified)

        assert simplified_points < raw_points, \
            f"Simplified ({simplified_points}) should have fewer points than raw ({raw_points})"

    def test_bezier_fitting_on_real_svg(self, svg_test_data):
        """Verify Bezier fitting produces valid curves on real SVG."""
        if 'deer' not in svg_test_data:
            pytest.skip("deer.svg not found")

        data = svg_test_data['deer']
        contours = extract_contours(
            data['mask'],
            simplify_epsilon=0.5,
            fit_beziers=True,
        )

        # Check all contours have valid Bezier segments
        for contour in contours:
            assert contour.beziers is not None
            assert len(contour.beziers) > 0

            # Verify segments connect
            for i in range(1, len(contour.beziers)):
                prev_end = contour.beziers[i - 1].p3
                curr_start = contour.beziers[i].p0
                dist = np.sqrt(
                    (prev_end.x - curr_start.x)**2 +
                    (prev_end.y - curr_start.y)**2
                )
                assert dist < 0.01, f"Bezier segments don't connect at index {i}"


class TestContourExtractorFilter:
    """Tests for the ContourExtractor filter class."""

    def test_contour_extractor_is_registered(self):
        """ContourExtractor should be registered in filter registry."""
        from imagestag.filters.base import FILTER_REGISTRY
        assert 'ContourExtractor' in FILTER_REGISTRY

    def test_contour_extractor_basic(self):
        """ContourExtractor should extract contours from image."""
        from imagestag import Image

        # Create a simple image with a circle
        rgba = np.zeros((100, 100, 4), dtype=np.uint8)
        y, x = np.ogrid[:100, :100]
        circle_mask = (x - 50)**2 + (y - 50)**2 < 30**2
        rgba[circle_mask, 0] = 255  # Red
        rgba[circle_mask, 3] = 255  # Alpha

        image = Image(rgba)
        extractor = ContourExtractor(simplify_epsilon=0.5)
        result = extractor(image)

        # Should return GeometryList
        from imagestag.geometry_list import GeometryList
        assert isinstance(result, GeometryList)
        assert len(result) >= 1

    def test_contour_extractor_returns_polygons(self):
        """ContourExtractor should return Polygon geometries."""
        from imagestag import Image
        from imagestag.geometry_list import Polygon

        # Create image with square
        rgba = np.zeros((100, 100, 4), dtype=np.uint8)
        rgba[20:80, 20:80, :3] = 255
        rgba[20:80, 20:80, 3] = 255

        image = Image(rgba)
        extractor = ContourExtractor()
        result = extractor(image)

        assert len(result) >= 1
        assert isinstance(result[0], Polygon)
        assert result[0].closed is True
        assert len(result[0].points) > 3

    def test_contour_extractor_with_beziers(self):
        """ContourExtractor with fit_beziers stores bezier data in metadata."""
        from imagestag import Image

        rgba = np.zeros((100, 100, 4), dtype=np.uint8)
        y, x = np.ogrid[:100, :100]
        circle_mask = (x - 50)**2 + (y - 50)**2 < 30**2
        rgba[circle_mask] = [255, 255, 255, 255]

        image = Image(rgba)
        extractor = ContourExtractor(
            simplify_epsilon=0.5,
            fit_beziers=True,
            bezier_smoothness=0.25,
        )
        result = extractor(image)

        assert len(result) >= 1
        # Bezier data should be in metadata extra
        assert 'beziers' in result[0].meta.extra
        assert len(result[0].meta.extra['beziers']) > 0

    def test_contour_extractor_parameters(self):
        """ContourExtractor parameters should affect output."""
        from imagestag import Image

        rgba = np.zeros((100, 100, 4), dtype=np.uint8)
        y, x = np.ogrid[:100, :100]
        circle_mask = (x - 50)**2 + (y - 50)**2 < 30**2
        rgba[circle_mask] = [255, 255, 255, 255]

        image = Image(rgba)

        # Raw extraction
        raw = ContourExtractor(simplify_epsilon=0.0)(image)
        # Simplified
        simplified = ContourExtractor(simplify_epsilon=0.5)(image)

        raw_points = sum(len(p.points) for p in raw)
        simplified_points = sum(len(p.points) for p in simplified)

        assert simplified_points < raw_points

    def test_contour_extractor_geometry_filter(self):
        """ContourExtractor should be a GeometryFilter."""
        from imagestag.filters.geometry import GeometryFilter
        assert issubclass(ContourExtractor, GeometryFilter)

    def test_contour_extractor_has_detect_method(self):
        """ContourExtractor should implement detect() method."""
        extractor = ContourExtractor()
        assert hasattr(extractor, 'detect')
        assert callable(extractor.detect)


class TestDouglasPeucker:
    """Tests for Douglas-Peucker polyline simplification."""

    def test_douglas_peucker_basic(self):
        """Basic simplification removes collinear points."""
        # Points on a line with some on the line
        points = [(0, 0), (1, 0), (2, 0), (3, 0), (4, 0)]
        result = douglas_peucker(points, epsilon=0.1)

        # Should reduce to just endpoints
        assert len(result) == 2
        assert result[0] == (0, 0)
        assert result[1] == (4, 0)

    def test_douglas_peucker_preserves_corners(self):
        """Corners should be preserved during simplification."""
        # A square shape
        points = [(0, 0), (10, 0), (10, 10), (0, 10)]
        result = douglas_peucker(points, epsilon=0.5)

        # All corners should be preserved
        assert len(result) == 4
        assert (0, 0) in result
        assert (10, 0) in result
        assert (10, 10) in result
        assert (0, 10) in result

    def test_douglas_peucker_epsilon_zero(self):
        """Epsilon=0 should preserve all points."""
        points = [(0, 0), (1, 0.1), (2, -0.1), (3, 0), (4, 0)]
        result = douglas_peucker(points, epsilon=0.0)

        assert len(result) == len(points)
        for i, pt in enumerate(result):
            assert abs(pt[0] - points[i][0]) < 0.001
            assert abs(pt[1] - points[i][1]) < 0.001

    def test_douglas_peucker_two_points(self):
        """Two points should remain two points."""
        points = [(0, 0), (10, 10)]
        result = douglas_peucker(points, epsilon=1.0)

        assert len(result) == 2
        assert result[0] == (0, 0)
        assert result[1] == (10, 10)

    def test_douglas_peucker_triangle(self):
        """Triangle with slight deviation on one edge."""
        # Triangle with extra point on one edge
        points = [(0, 0), (5, 0.05), (10, 0), (5, 10)]
        result = douglas_peucker(points, epsilon=0.1)

        # The point (5, 0.05) should be removed (deviation < epsilon)
        assert len(result) == 3
        assert (0, 0) in result
        assert (10, 0) in result
        assert (5, 10) in result

    def test_douglas_peucker_large_deviation(self):
        """Points with large deviation should be preserved."""
        points = [(0, 0), (5, 5), (10, 0)]  # V shape
        result = douglas_peucker(points, epsilon=0.5)

        # The middle point has large deviation and should be kept
        assert len(result) == 3

    def test_douglas_peucker_closed_basic(self):
        """Closed polygon simplification."""
        # Square with extra points on edges
        points = [
            (0, 0), (5, 0), (10, 0),
            (10, 5), (10, 10),
            (5, 10), (0, 10),
            (0, 5), (0, 0)  # Closed
        ]
        result = douglas_peucker_closed(points, epsilon=0.5)

        # Should simplify significantly (removing edge midpoints)
        assert len(result) < len(points)
        # Should preserve at least 4 corners + closure
        assert len(result) >= 5
        # Verify the result is closed
        assert result[0] == result[-1]

    def test_douglas_peucker_closed_preserves_corners(self):
        """Closed polygon should preserve corner points."""
        # Hexagon-ish shape
        points = [
            (5, 0), (10, 2.5), (10, 7.5),
            (5, 10), (0, 7.5), (0, 2.5), (5, 0)
        ]
        result = douglas_peucker_closed(points, epsilon=0.5)

        # Should preserve all corners since they have significant deviation
        assert len(result) >= 5

    def test_douglas_peucker_closed_circle_approximation(self):
        """Simplifying a circle should reduce points significantly."""
        # Create a rough circle with many points
        import math
        n_points = 100
        radius = 10
        points = []
        for i in range(n_points):
            angle = 2 * math.pi * i / n_points
            x = radius * math.cos(angle) + 10
            y = radius * math.sin(angle) + 10
            points.append((x, y))
        points.append(points[0])  # Close the polygon

        result = douglas_peucker_closed(points, epsilon=0.5)

        # Should significantly reduce the number of points
        assert len(result) < len(points) / 2

    def test_douglas_peucker_rust_backend(self):
        """Verify Douglas-Peucker uses Rust backend."""
        from imagestag import imagestag_rust

        assert hasattr(imagestag_rust, 'douglas_peucker')
        assert hasattr(imagestag_rust, 'douglas_peucker_closed')

        # Test direct Rust call
        points = [(0.0, 0.0), (1.0, 0.0), (2.0, 0.0)]
        result = imagestag_rust.douglas_peucker(points, 0.1)

        assert len(result) == 2
        assert result[0] == (0.0, 0.0)
        assert result[1] == (2.0, 0.0)
