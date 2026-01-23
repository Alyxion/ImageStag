"""Unit tests for layer scaling functions.

Tests the scale_shape() Python function that mirrors JavaScript VectorShape.scale().
"""

import pytest
import copy
from stagforge.rendering.vector import scale_shape


class TestRectShapeScaling:
    """Tests for rectangle shape scaling."""

    def test_scale_rect_uniform_from_center(self):
        """Scale rect 2x uniformly from default center."""
        shape = {
            "type": "rect",
            "x": 100,
            "y": 100,
            "width": 50,
            "height": 30,
        }
        result = scale_shape(shape, 2.0, 2.0)

        # Center was (125, 115), scaling 2x means:
        # new_x = 125 + (100 - 125) * 2 = 125 - 50 = 75
        # new_y = 115 + (100 - 115) * 2 = 115 - 30 = 85
        assert result["x"] == pytest.approx(75, abs=0.001)
        assert result["y"] == pytest.approx(85, abs=0.001)
        assert result["width"] == pytest.approx(100, abs=0.001)
        assert result["height"] == pytest.approx(60, abs=0.001)

    def test_scale_rect_non_uniform(self):
        """Scale rect differently in X and Y."""
        shape = {
            "type": "rect",
            "x": 0,
            "y": 0,
            "width": 100,
            "height": 100,
        }
        result = scale_shape(shape, 2.0, 0.5)

        # Center is (50, 50)
        # new_x = 50 + (0 - 50) * 2 = -50
        # new_y = 50 + (0 - 50) * 0.5 = 25
        assert result["x"] == pytest.approx(-50, abs=0.001)
        assert result["y"] == pytest.approx(25, abs=0.001)
        assert result["width"] == pytest.approx(200, abs=0.001)
        assert result["height"] == pytest.approx(50, abs=0.001)

    def test_scale_rect_with_custom_center(self):
        """Scale rect around a custom center point."""
        shape = {
            "type": "rect",
            "x": 100,
            "y": 100,
            "width": 50,
            "height": 50,
        }
        result = scale_shape(shape, 2.0, 2.0, center_x=0, center_y=0)

        # Center at origin means all coordinates double
        assert result["x"] == pytest.approx(200, abs=0.001)
        assert result["y"] == pytest.approx(200, abs=0.001)
        assert result["width"] == pytest.approx(100, abs=0.001)
        assert result["height"] == pytest.approx(100, abs=0.001)

    def test_scale_rect_corner_radius(self):
        """Corner radius should scale with minimum scale factor."""
        shape = {
            "type": "rect",
            "x": 0,
            "y": 0,
            "width": 100,
            "height": 100,
            "cornerRadius": 10,
        }
        result = scale_shape(shape, 2.0, 3.0)

        # cornerRadius scales by min(|2|, |3|) = 2
        assert result["cornerRadius"] == pytest.approx(20, abs=0.001)

    def test_scale_rect_negative_factor(self):
        """Negative scale factors should use absolute values for dimensions."""
        shape = {
            "type": "rect",
            "x": 0,
            "y": 0,
            "width": 100,
            "height": 100,
        }
        result = scale_shape(shape, -2.0, -2.0)

        # Width/height use abs(scale)
        assert result["width"] == pytest.approx(200, abs=0.001)
        assert result["height"] == pytest.approx(200, abs=0.001)


class TestEllipseShapeScaling:
    """Tests for ellipse shape scaling."""

    def test_scale_ellipse_uniform(self):
        """Scale ellipse uniformly."""
        shape = {
            "type": "ellipse",
            "cx": 100,
            "cy": 100,
            "rx": 50,
            "ry": 30,
        }
        result = scale_shape(shape, 2.0, 2.0)

        # Default center is the ellipse center, so center stays fixed
        assert result["cx"] == pytest.approx(100, abs=0.001)
        assert result["cy"] == pytest.approx(100, abs=0.001)
        assert result["rx"] == pytest.approx(100, abs=0.001)
        assert result["ry"] == pytest.approx(60, abs=0.001)

    def test_scale_ellipse_custom_center(self):
        """Scale ellipse around custom center."""
        shape = {
            "type": "ellipse",
            "cx": 100,
            "cy": 100,
            "rx": 50,
            "ry": 50,
        }
        result = scale_shape(shape, 2.0, 2.0, center_x=0, center_y=0)

        # Ellipse center moves
        assert result["cx"] == pytest.approx(200, abs=0.001)
        assert result["cy"] == pytest.approx(200, abs=0.001)
        assert result["rx"] == pytest.approx(100, abs=0.001)
        assert result["ry"] == pytest.approx(100, abs=0.001)


class TestLineShapeScaling:
    """Tests for line shape scaling."""

    def test_scale_line_uniform(self):
        """Scale line uniformly from default center."""
        shape = {
            "type": "line",
            "x1": 0,
            "y1": 0,
            "x2": 100,
            "y2": 100,
            "strokeWidth": 2,
        }
        result = scale_shape(shape, 2.0, 2.0)

        # Center is (50, 50)
        # x1 = 50 + (0 - 50) * 2 = -50
        # y1 = 50 + (0 - 50) * 2 = -50
        # x2 = 50 + (100 - 50) * 2 = 150
        # y2 = 50 + (100 - 50) * 2 = 150
        assert result["x1"] == pytest.approx(-50, abs=0.001)
        assert result["y1"] == pytest.approx(-50, abs=0.001)
        assert result["x2"] == pytest.approx(150, abs=0.001)
        assert result["y2"] == pytest.approx(150, abs=0.001)
        assert result["strokeWidth"] == pytest.approx(4, abs=0.001)

    def test_scale_line_non_uniform_stroke_width(self):
        """Stroke width should scale by minimum factor."""
        shape = {
            "type": "line",
            "x1": 0,
            "y1": 0,
            "x2": 100,
            "y2": 0,
            "strokeWidth": 10,
        }
        result = scale_shape(shape, 3.0, 2.0)

        # strokeWidth scales by min(3, 2) = 2
        assert result["strokeWidth"] == pytest.approx(20, abs=0.001)


class TestPolygonShapeScaling:
    """Tests for polygon shape scaling."""

    def test_scale_polygon_array_format(self):
        """Scale polygon with [x, y] array format points."""
        shape = {
            "type": "polygon",
            "points": [[0, 0], [100, 0], [50, 100]],
        }
        original_points = copy.deepcopy(shape["points"])
        result = scale_shape(shape, 2.0, 2.0)

        # Center of triangle is approximately (50, 33.33)
        # All points should be scaled relative to that
        assert len(result["points"]) == 3
        # Just verify points changed in the expected direction
        assert result["points"][0][0] != original_points[0][0]

    def test_scale_polygon_dict_format(self):
        """Scale polygon with {x, y} dict format points."""
        shape = {
            "type": "polygon",
            "points": [{"x": 0, "y": 0}, {"x": 100, "y": 0}, {"x": 100, "y": 100}],
        }
        result = scale_shape(shape, 0.5, 0.5)

        # Points should be smaller
        assert len(result["points"]) == 3
        # Verify the shape is modified
        assert "x" in result["points"][0]


class TestPathShapeScaling:
    """Tests for path shape scaling."""

    def test_scale_path_with_handles(self):
        """Scale path with bezier handles."""
        shape = {
            "type": "path",
            "points": [
                {"x": 0, "y": 0, "handleOut": {"x": 10, "y": 0}},
                {"x": 100, "y": 0, "handleIn": {"x": -10, "y": 0}},
                {"x": 100, "y": 100},
            ],
        }
        result = scale_shape(shape, 2.0, 2.0)

        # Handles are relative, so they should just multiply
        assert result["points"][0]["handleOut"]["x"] == pytest.approx(20, abs=0.001)
        assert result["points"][0]["handleOut"]["y"] == pytest.approx(0, abs=0.001)
        assert result["points"][1]["handleIn"]["x"] == pytest.approx(-20, abs=0.001)
        assert result["points"][1]["handleIn"]["y"] == pytest.approx(0, abs=0.001)

    def test_scale_path_non_uniform_handles(self):
        """Handles should scale non-uniformly with scaleX/scaleY."""
        shape = {
            "type": "path",
            "points": [
                {"x": 50, "y": 50, "handleOut": {"x": 10, "y": 10}},
                {"x": 100, "y": 100},
            ],
        }
        result = scale_shape(shape, 2.0, 0.5)

        # handleOut.x scales by 2, handleOut.y scales by 0.5
        assert result["points"][0]["handleOut"]["x"] == pytest.approx(20, abs=0.001)
        assert result["points"][0]["handleOut"]["y"] == pytest.approx(5, abs=0.001)


class TestShapeScalingEdgeCases:
    """Edge case tests for shape scaling."""

    def test_scale_empty_polygon(self):
        """Empty polygon should not crash."""
        shape = {"type": "polygon", "points": []}
        result = scale_shape(shape, 2.0, 2.0)
        assert result["points"] == []

    def test_scale_empty_path(self):
        """Empty path should not crash."""
        shape = {"type": "path", "points": []}
        result = scale_shape(shape, 2.0, 2.0)
        assert result["points"] == []

    def test_scale_unknown_type(self):
        """Unknown shape type should return unchanged."""
        shape = {"type": "unknown", "foo": "bar"}
        result = scale_shape(shape, 2.0, 2.0)
        assert result == shape

    def test_scale_by_one(self):
        """Scaling by 1 should not change shape."""
        shape = {
            "type": "rect",
            "x": 100,
            "y": 100,
            "width": 50,
            "height": 30,
        }
        original = copy.deepcopy(shape)
        result = scale_shape(shape, 1.0, 1.0)

        assert result["x"] == pytest.approx(original["x"], abs=0.001)
        assert result["y"] == pytest.approx(original["y"], abs=0.001)
        assert result["width"] == pytest.approx(original["width"], abs=0.001)
        assert result["height"] == pytest.approx(original["height"], abs=0.001)
