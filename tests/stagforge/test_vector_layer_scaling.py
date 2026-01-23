"""Tests for vector layer scaling.

Tests the scale_shape() function and verifies that scaling vector shapes
produces reasonable coordinates.
"""

import pytest
import copy
from stagforge.rendering.vector import scale_shape


class TestVectorLayerScaling:
    """Tests for scaling vector layers with multiple shapes."""

    def test_scale_rect_and_ellipse_uniform(self):
        """Scale a rectangle and ellipse uniformly by 2x."""
        # Create shapes at specific positions
        rect = {
            "type": "rect",
            "x": 100,
            "y": 100,
            "width": 50,
            "height": 30,
            "cornerRadius": 5,
            "fillColor": "#ff0000",
            "strokeColor": "#000000",
            "strokeWidth": 2,
            "fill": True,
            "stroke": True,
            "opacity": 1.0,
        }

        ellipse = {
            "type": "ellipse",
            "cx": 200,
            "cy": 150,
            "rx": 40,
            "ry": 25,
            "fillColor": "#00ff00",
            "strokeColor": "#000000",
            "strokeWidth": 2,
            "fill": True,
            "stroke": True,
            "opacity": 1.0,
        }

        # Scale both shapes 2x from origin (0, 0)
        rect_scaled = copy.deepcopy(rect)
        ellipse_scaled = copy.deepcopy(ellipse)

        scale_shape(rect_scaled, 2.0, 2.0, center_x=0, center_y=0)
        scale_shape(ellipse_scaled, 2.0, 2.0, center_x=0, center_y=0)

        # Verify rect dimensions doubled
        assert rect_scaled["width"] == pytest.approx(100, abs=0.001)
        assert rect_scaled["height"] == pytest.approx(60, abs=0.001)
        assert rect_scaled["x"] == pytest.approx(200, abs=0.001)
        assert rect_scaled["y"] == pytest.approx(200, abs=0.001)
        assert rect_scaled["cornerRadius"] == pytest.approx(10, abs=0.001)

        # Verify ellipse radii doubled
        assert ellipse_scaled["rx"] == pytest.approx(80, abs=0.001)
        assert ellipse_scaled["ry"] == pytest.approx(50, abs=0.001)
        assert ellipse_scaled["cx"] == pytest.approx(400, abs=0.001)
        assert ellipse_scaled["cy"] == pytest.approx(300, abs=0.001)

    def test_scale_shapes_from_center(self):
        """Scale shapes from their combined center."""
        # Create a rect at (100, 100) with size 50x50
        # and an ellipse at (200, 150) with rx=40, ry=25
        rect = {
            "type": "rect",
            "x": 100,
            "y": 100,
            "width": 50,
            "height": 50,
        }

        ellipse = {
            "type": "ellipse",
            "cx": 200,
            "cy": 150,
            "rx": 40,
            "ry": 25,
        }

        # Calculate bounding box center
        # Rect bounds: 100-150 x, 100-150 y
        # Ellipse bounds: 160-240 x, 125-175 y
        # Combined bounds: 100-240 x, 100-175 y
        # Center: (170, 137.5)
        center_x = 170
        center_y = 137.5

        rect_scaled = copy.deepcopy(rect)
        ellipse_scaled = copy.deepcopy(ellipse)

        scale_shape(rect_scaled, 2.0, 2.0, center_x=center_x, center_y=center_y)
        scale_shape(ellipse_scaled, 2.0, 2.0, center_x=center_x, center_y=center_y)

        # After scaling 2x from center (170, 137.5):
        # rect x: 170 + (100 - 170) * 2 = 170 - 140 = 30
        # rect y: 137.5 + (100 - 137.5) * 2 = 137.5 - 75 = 62.5
        assert rect_scaled["x"] == pytest.approx(30, abs=0.001)
        assert rect_scaled["y"] == pytest.approx(62.5, abs=0.001)
        assert rect_scaled["width"] == pytest.approx(100, abs=0.001)
        assert rect_scaled["height"] == pytest.approx(100, abs=0.001)

        # ellipse cx: 170 + (200 - 170) * 2 = 170 + 60 = 230
        # ellipse cy: 137.5 + (150 - 137.5) * 2 = 137.5 + 25 = 162.5
        assert ellipse_scaled["cx"] == pytest.approx(230, abs=0.001)
        assert ellipse_scaled["cy"] == pytest.approx(162.5, abs=0.001)
        assert ellipse_scaled["rx"] == pytest.approx(80, abs=0.001)
        assert ellipse_scaled["ry"] == pytest.approx(50, abs=0.001)

    def test_scale_shapes_non_uniform(self):
        """Scale shapes with different x and y factors."""
        rect = {
            "type": "rect",
            "x": 0,
            "y": 0,
            "width": 100,
            "height": 100,
        }

        ellipse = {
            "type": "ellipse",
            "cx": 50,
            "cy": 50,
            "rx": 30,
            "ry": 30,
        }

        rect_scaled = copy.deepcopy(rect)
        ellipse_scaled = copy.deepcopy(ellipse)

        # Scale 2x horizontally, 0.5x vertically from origin
        scale_shape(rect_scaled, 2.0, 0.5, center_x=0, center_y=0)
        scale_shape(ellipse_scaled, 2.0, 0.5, center_x=0, center_y=0)

        # Rect should be 200x50 at origin
        assert rect_scaled["x"] == pytest.approx(0, abs=0.001)
        assert rect_scaled["y"] == pytest.approx(0, abs=0.001)
        assert rect_scaled["width"] == pytest.approx(200, abs=0.001)
        assert rect_scaled["height"] == pytest.approx(50, abs=0.001)

        # Ellipse center should move and radii scale differently
        assert ellipse_scaled["cx"] == pytest.approx(100, abs=0.001)  # 50 * 2
        assert ellipse_scaled["cy"] == pytest.approx(25, abs=0.001)   # 50 * 0.5
        assert ellipse_scaled["rx"] == pytest.approx(60, abs=0.001)   # 30 * 2
        assert ellipse_scaled["ry"] == pytest.approx(15, abs=0.001)   # 30 * 0.5

    def test_scale_line_shape(self):
        """Scale a line shape."""
        line = {
            "type": "line",
            "x1": 0,
            "y1": 0,
            "x2": 100,
            "y2": 100,
            "strokeColor": "#000000",
            "strokeWidth": 2,
        }

        line_scaled = copy.deepcopy(line)
        scale_shape(line_scaled, 2.0, 2.0, center_x=0, center_y=0)

        # Line endpoints should double
        assert line_scaled["x1"] == pytest.approx(0, abs=0.001)
        assert line_scaled["y1"] == pytest.approx(0, abs=0.001)
        assert line_scaled["x2"] == pytest.approx(200, abs=0.001)
        assert line_scaled["y2"] == pytest.approx(200, abs=0.001)
        # Stroke width should scale by min(|2|, |2|) = 2
        assert line_scaled["strokeWidth"] == pytest.approx(4, abs=0.001)

    def test_scale_polygon_shape(self):
        """Scale a polygon with multiple points."""
        # Triangle
        polygon = {
            "type": "polygon",
            "points": [[0, 0], [100, 0], [50, 100]],
            "closed": True,
            "fillColor": "#ff0000",
            "fill": True,
        }

        polygon_scaled = copy.deepcopy(polygon)
        scale_shape(polygon_scaled, 2.0, 2.0, center_x=0, center_y=0)

        # All points should double
        assert polygon_scaled["points"][0][0] == pytest.approx(0, abs=0.001)
        assert polygon_scaled["points"][0][1] == pytest.approx(0, abs=0.001)
        assert polygon_scaled["points"][1][0] == pytest.approx(200, abs=0.001)
        assert polygon_scaled["points"][1][1] == pytest.approx(0, abs=0.001)
        assert polygon_scaled["points"][2][0] == pytest.approx(100, abs=0.001)
        assert polygon_scaled["points"][2][1] == pytest.approx(200, abs=0.001)

    def test_scale_down_shapes(self):
        """Scale shapes down to half size."""
        rect = {
            "type": "rect",
            "x": 100,
            "y": 100,
            "width": 200,
            "height": 200,
        }

        rect_scaled = copy.deepcopy(rect)
        # Scale 0.5x from the rect's center (200, 200)
        scale_shape(rect_scaled, 0.5, 0.5, center_x=200, center_y=200)

        # Width/height should halve
        assert rect_scaled["width"] == pytest.approx(100, abs=0.001)
        assert rect_scaled["height"] == pytest.approx(100, abs=0.001)
        # Position should adjust to keep center at (200, 200)
        # new_x = 200 + (100 - 200) * 0.5 = 200 - 50 = 150
        assert rect_scaled["x"] == pytest.approx(150, abs=0.001)
        assert rect_scaled["y"] == pytest.approx(150, abs=0.001)

    def test_scale_circle_to_ellipse(self):
        """Non-uniform scaling converts a circle to an ellipse."""
        circle = {
            "type": "ellipse",
            "cx": 100,
            "cy": 100,
            "rx": 50,  # Equal radii = circle
            "ry": 50,
        }

        circle_scaled = copy.deepcopy(circle)
        # Scale 2x horizontally only
        scale_shape(circle_scaled, 2.0, 1.0, center_x=0, center_y=0)

        # rx should double, ry should stay same
        assert circle_scaled["rx"] == pytest.approx(100, abs=0.001)
        assert circle_scaled["ry"] == pytest.approx(50, abs=0.001)
        # Center x doubles, y stays
        assert circle_scaled["cx"] == pytest.approx(200, abs=0.001)
        assert circle_scaled["cy"] == pytest.approx(100, abs=0.001)

    def test_scale_preserves_other_properties(self):
        """Scaling should preserve fill, stroke, opacity, etc."""
        rect = {
            "type": "rect",
            "x": 100,
            "y": 100,
            "width": 50,
            "height": 50,
            "fillColor": "#ff0000",
            "strokeColor": "#0000ff",
            "strokeWidth": 3,
            "fill": True,
            "stroke": True,
            "opacity": 0.5,
            "cornerRadius": 10,
        }

        rect_scaled = copy.deepcopy(rect)
        scale_shape(rect_scaled, 2.0, 2.0, center_x=0, center_y=0)

        # These properties should be preserved
        assert rect_scaled["fillColor"] == "#ff0000"
        assert rect_scaled["strokeColor"] == "#0000ff"
        assert rect_scaled["fill"] == True
        assert rect_scaled["stroke"] == True
        assert rect_scaled["opacity"] == 0.5

    def test_scale_multiple_shapes_maintains_relative_positions(self):
        """Scaling multiple shapes should maintain their relative positions."""
        # Create two shapes side by side
        rect1 = {
            "type": "rect",
            "x": 0,
            "y": 0,
            "width": 50,
            "height": 50,
        }

        rect2 = {
            "type": "rect",
            "x": 60,  # 10px gap from rect1
            "y": 0,
            "width": 50,
            "height": 50,
        }

        rect1_scaled = copy.deepcopy(rect1)
        rect2_scaled = copy.deepcopy(rect2)

        # Scale both from origin
        scale_shape(rect1_scaled, 2.0, 2.0, center_x=0, center_y=0)
        scale_shape(rect2_scaled, 2.0, 2.0, center_x=0, center_y=0)

        # Gap should also double: was 10, now should be 20
        # rect1 ends at x=100 (0 + 100), rect2 starts at x=120 (60*2)
        gap = rect2_scaled["x"] - (rect1_scaled["x"] + rect1_scaled["width"])
        assert gap == pytest.approx(20, abs=0.001)


class TestVectorScalingEdgeCases:
    """Edge case tests for vector shape scaling."""

    def test_scale_by_one_no_change(self):
        """Scaling by 1.0 should not change anything."""
        rect = {
            "type": "rect",
            "x": 100,
            "y": 100,
            "width": 50,
            "height": 30,
        }

        original = copy.deepcopy(rect)
        scale_shape(rect, 1.0, 1.0)

        assert rect["x"] == pytest.approx(original["x"], abs=0.001)
        assert rect["y"] == pytest.approx(original["y"], abs=0.001)
        assert rect["width"] == pytest.approx(original["width"], abs=0.001)
        assert rect["height"] == pytest.approx(original["height"], abs=0.001)

    def test_scale_negative_flips_position(self):
        """Negative scale factors should flip coordinates."""
        rect = {
            "type": "rect",
            "x": 100,
            "y": 100,
            "width": 50,
            "height": 50,
        }

        rect_scaled = copy.deepcopy(rect)
        scale_shape(rect_scaled, -1.0, -1.0, center_x=0, center_y=0)

        # Position flips, but dimensions use absolute value
        assert rect_scaled["x"] == pytest.approx(-100, abs=0.001)
        assert rect_scaled["y"] == pytest.approx(-100, abs=0.001)
        assert rect_scaled["width"] == pytest.approx(50, abs=0.001)
        assert rect_scaled["height"] == pytest.approx(50, abs=0.001)

    def test_scale_empty_polygon(self):
        """Empty polygon should not crash."""
        polygon = {
            "type": "polygon",
            "points": [],
        }

        # Should not raise
        scale_shape(polygon, 2.0, 2.0)
        assert polygon["points"] == []

    def test_scale_unknown_type_unchanged(self):
        """Unknown shape type should pass through unchanged."""
        unknown = {
            "type": "mystery",
            "foo": "bar",
            "x": 100,
        }

        original = copy.deepcopy(unknown)
        result = scale_shape(unknown, 2.0, 2.0)

        # Should return unchanged
        assert result == original


def calculate_shapes_bounds(shapes, padding=0):
    """Calculate combined bounding box of multiple shapes.

    This mirrors VectorLayer.getShapesBoundsInDocSpace().

    Args:
        shapes: List of shape dicts
        padding: Extra padding around bounds

    Returns:
        dict with x, y, width, height or None if no shapes
    """
    if not shapes:
        return None

    min_x = float('inf')
    min_y = float('inf')
    max_x = float('-inf')
    max_y = float('-inf')

    for shape in shapes:
        shape_type = shape.get("type", "")
        stroke_padding = (shape.get("strokeWidth", 0) / 2) if shape.get("stroke") else 0

        if shape_type == "rect":
            x, y = shape.get("x", 0), shape.get("y", 0)
            w, h = shape.get("width", 0), shape.get("height", 0)
            min_x = min(min_x, x - stroke_padding)
            min_y = min(min_y, y - stroke_padding)
            max_x = max(max_x, x + w + stroke_padding)
            max_y = max(max_y, y + h + stroke_padding)

        elif shape_type == "ellipse":
            cx, cy = shape.get("cx", 0), shape.get("cy", 0)
            rx, ry = shape.get("rx", 0), shape.get("ry", 0)
            min_x = min(min_x, cx - rx - stroke_padding)
            min_y = min(min_y, cy - ry - stroke_padding)
            max_x = max(max_x, cx + rx + stroke_padding)
            max_y = max(max_y, cy + ry + stroke_padding)

        elif shape_type == "line":
            x1, y1 = shape.get("x1", 0), shape.get("y1", 0)
            x2, y2 = shape.get("x2", 0), shape.get("y2", 0)
            stroke_w = shape.get("strokeWidth", 1) / 2
            min_x = min(min_x, min(x1, x2) - stroke_w)
            min_y = min(min_y, min(y1, y2) - stroke_w)
            max_x = max(max_x, max(x1, x2) + stroke_w)
            max_y = max(max_y, max(y1, y2) + stroke_w)

        elif shape_type == "polygon":
            points = shape.get("points", [])
            for pt in points:
                if isinstance(pt, dict):
                    px, py = pt.get("x", 0), pt.get("y", 0)
                else:
                    px, py = pt[0], pt[1]
                min_x = min(min_x, px - stroke_padding)
                min_y = min(min_y, py - stroke_padding)
                max_x = max(max_x, px + stroke_padding)
                max_y = max(max_y, py + stroke_padding)

    if min_x == float('inf'):
        return None

    # Apply padding
    min_x = min_x - padding
    min_y = min_y - padding
    max_x = max_x + padding
    max_y = max_y + padding

    return {
        "x": min_x,
        "y": min_y,
        "width": max_x - min_x,
        "height": max_y - min_y
    }


class TestBoundingBoxGrowthOnScale:
    """Tests that verify bounding box grows correctly when shapes are scaled.

    These tests address the issue where internal shape coordinates scaled
    but the outer bounding box did not grow correctly.
    """

    def test_bounding_box_doubles_on_2x_scale(self):
        """When scaling 2x from origin, bounding box dimensions should double."""
        rect = {
            "type": "rect",
            "x": 100,
            "y": 100,
            "width": 50,
            "height": 30,
        }

        ellipse = {
            "type": "ellipse",
            "cx": 200,
            "cy": 150,
            "rx": 40,
            "ry": 25,
        }

        shapes = [copy.deepcopy(rect), copy.deepcopy(ellipse)]

        # Get bounds before scaling
        bounds_before = calculate_shapes_bounds(shapes)
        # Combined bounds: x=100, y=100, width=140 (100 to 240), height=75 (100 to 175)
        assert bounds_before["x"] == pytest.approx(100, abs=0.001)
        assert bounds_before["y"] == pytest.approx(100, abs=0.001)
        assert bounds_before["width"] == pytest.approx(140, abs=0.001)
        assert bounds_before["height"] == pytest.approx(75, abs=0.001)

        # Scale both shapes 2x from origin
        for shape in shapes:
            scale_shape(shape, 2.0, 2.0, center_x=0, center_y=0)

        # Get bounds after scaling
        bounds_after = calculate_shapes_bounds(shapes)

        # Bounds should double: width 140->280, height 75->150
        # Position should also double: x 100->200, y 100->200
        assert bounds_after["width"] == pytest.approx(280, abs=0.001)
        assert bounds_after["height"] == pytest.approx(150, abs=0.001)
        assert bounds_after["x"] == pytest.approx(200, abs=0.001)
        assert bounds_after["y"] == pytest.approx(200, abs=0.001)

    def test_bounding_box_grows_from_center(self):
        """Scaling from center should grow bounds symmetrically."""
        # Two rects side by side
        rect1 = {
            "type": "rect",
            "x": 50,
            "y": 50,
            "width": 40,
            "height": 40,
        }

        rect2 = {
            "type": "rect",
            "x": 110,
            "y": 50,
            "width": 40,
            "height": 40,
        }

        shapes = [copy.deepcopy(rect1), copy.deepcopy(rect2)]

        # Get bounds before: x=50, y=50, width=100, height=40
        bounds_before = calculate_shapes_bounds(shapes)
        center_x = bounds_before["x"] + bounds_before["width"] / 2  # 100
        center_y = bounds_before["y"] + bounds_before["height"] / 2  # 70

        # Scale 2x from center
        for shape in shapes:
            scale_shape(shape, 2.0, 2.0, center_x=center_x, center_y=center_y)

        bounds_after = calculate_shapes_bounds(shapes)

        # Width and height should double
        assert bounds_after["width"] == pytest.approx(bounds_before["width"] * 2, abs=0.001)
        assert bounds_after["height"] == pytest.approx(bounds_before["height"] * 2, abs=0.001)

        # Center should remain the same
        new_center_x = bounds_after["x"] + bounds_after["width"] / 2
        new_center_y = bounds_after["y"] + bounds_after["height"] / 2
        assert new_center_x == pytest.approx(center_x, abs=0.001)
        assert new_center_y == pytest.approx(center_y, abs=0.001)

    def test_bounding_box_shrinks_on_scale_down(self):
        """Scaling down should shrink bounding box proportionally."""
        ellipse = {
            "type": "ellipse",
            "cx": 100,
            "cy": 100,
            "rx": 50,
            "ry": 50,
        }

        shapes = [copy.deepcopy(ellipse)]

        bounds_before = calculate_shapes_bounds(shapes)
        # Ellipse bounds: x=50, y=50, width=100, height=100

        # Scale 0.5x from ellipse center
        scale_shape(shapes[0], 0.5, 0.5, center_x=100, center_y=100)

        bounds_after = calculate_shapes_bounds(shapes)

        # Bounds should halve
        assert bounds_after["width"] == pytest.approx(bounds_before["width"] * 0.5, abs=0.001)
        assert bounds_after["height"] == pytest.approx(bounds_before["height"] * 0.5, abs=0.001)

    def test_bounding_box_with_stroked_shapes(self):
        """Bounding box should include stroke width."""
        rect = {
            "type": "rect",
            "x": 100,
            "y": 100,
            "width": 50,
            "height": 50,
            "stroke": True,
            "strokeWidth": 10,
        }

        shapes = [copy.deepcopy(rect)]

        bounds_before = calculate_shapes_bounds(shapes)
        # With stroke: x=95, y=95, width=60, height=60
        assert bounds_before["x"] == pytest.approx(95, abs=0.001)
        assert bounds_before["y"] == pytest.approx(95, abs=0.001)
        assert bounds_before["width"] == pytest.approx(60, abs=0.001)
        assert bounds_before["height"] == pytest.approx(60, abs=0.001)

        # Scale 2x from origin
        scale_shape(shapes[0], 2.0, 2.0, center_x=0, center_y=0)

        bounds_after = calculate_shapes_bounds(shapes)

        # Rect size scales to 100x100, but strokeWidth for rect doesn't scale
        # (only strokeWidth for lines scales). So bounds = 100 + 10 = 110
        assert bounds_after["width"] == pytest.approx(110, abs=0.001)
        assert bounds_after["height"] == pytest.approx(110, abs=0.001)

    def test_bounding_box_non_uniform_scale(self):
        """Non-uniform scaling should affect bounds correctly."""
        rect = {
            "type": "rect",
            "x": 0,
            "y": 0,
            "width": 100,
            "height": 100,
        }

        shapes = [copy.deepcopy(rect)]

        bounds_before = calculate_shapes_bounds(shapes)

        # Scale 2x horizontal, 0.5x vertical from origin
        scale_shape(shapes[0], 2.0, 0.5, center_x=0, center_y=0)

        bounds_after = calculate_shapes_bounds(shapes)

        # Width should double (200), height should halve (50)
        assert bounds_after["width"] == pytest.approx(200, abs=0.001)
        assert bounds_after["height"] == pytest.approx(50, abs=0.001)

    def test_combined_bounds_multiple_shape_types(self):
        """Test bounding box with rect, ellipse, and line all scaling together."""
        rect = {
            "type": "rect",
            "x": 0,
            "y": 0,
            "width": 50,
            "height": 50,
        }

        ellipse = {
            "type": "ellipse",
            "cx": 100,
            "cy": 25,
            "rx": 20,
            "ry": 20,
        }

        line = {
            "type": "line",
            "x1": 0,
            "y1": 60,
            "x2": 120,
            "y2": 60,
            "strokeWidth": 4,
        }

        shapes = [copy.deepcopy(rect), copy.deepcopy(ellipse), copy.deepcopy(line)]

        bounds_before = calculate_shapes_bounds(shapes)
        # x=0 (rect), y=0 (rect),
        # max_x=120 (line or ellipse at 120), max_y=62 (line at 60 + stroke/2)

        # Scale all 1.5x from origin
        for shape in shapes:
            scale_shape(shape, 1.5, 1.5, center_x=0, center_y=0)

        bounds_after = calculate_shapes_bounds(shapes)

        # All dimensions should scale 1.5x
        assert bounds_after["width"] == pytest.approx(bounds_before["width"] * 1.5, abs=1)
        assert bounds_after["height"] == pytest.approx(bounds_before["height"] * 1.5, abs=1)
