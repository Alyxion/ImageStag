"""Tests for vector layer resize simulation.

Simulates the MoveTool resize logic to verify correct behavior.
"""

import pytest
import copy
from stagforge.rendering.vector import scale_shape


def calculate_shapes_bounds(shapes, padding=0):
    """Calculate combined bounding box of shapes (mirrors JS getShapesBoundsInDocSpace)."""
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
            rx, ry = abs(shape.get("rx", 0)), abs(shape.get("ry", 0))
            min_x = min(min_x, cx - rx - stroke_padding)
            min_y = min(min_y, cy - ry - stroke_padding)
            max_x = max(max_x, cx + rx + stroke_padding)
            max_y = max(max_y, cy + ry + stroke_padding)

    if min_x == float('inf'):
        return None

    min_x -= padding
    min_y -= padding
    max_x += padding
    max_y += padding

    return {
        "x": min_x,
        "y": min_y,
        "width": max_x - min_x,
        "height": max_y - min_y
    }


def fit_to_content(shapes, padding=2):
    """Simulate VectorLayer.fitToContent() - returns layer bounds."""
    bounds = calculate_shapes_bounds(shapes, padding)
    if not bounds:
        return None
    return {
        "offsetX": int(bounds["x"]),  # floor
        "offsetY": int(bounds["y"]),
        "width": int(bounds["width"] + 0.999),  # ceil
        "height": int(bounds["height"] + 0.999),
    }


class TestVectorResizeSimulation:
    """Simulate MoveTool resize logic."""

    def test_br_handle_keeps_tl_fixed(self):
        """Dragging BR handle should keep top-left corner of shapes fixed."""
        # Initial shape: rect at (100, 100) size 50x50
        initial_shapes = [{
            "type": "rect",
            "x": 100,
            "y": 100,
            "width": 50,
            "height": 50,
        }]

        # Get initial state (as MoveTool.onMouseDown would)
        initial_shape_bounds = calculate_shapes_bounds(initial_shapes)
        layer_state = fit_to_content(initial_shapes)

        # Initial shape bounds: x=100, y=100, w=50, h=50
        # Initial layer (with padding=2): offsetX=98, offsetY=98, w=54, h=54
        assert initial_shape_bounds["x"] == 100
        assert initial_shape_bounds["y"] == 100
        assert initial_shape_bounds["width"] == 50
        assert initial_shape_bounds["height"] == 50

        # Simulate dragging BR handle to double the size
        # User drags from (148, 148) to (198, 198) - adds 50px each direction
        initial_layer_width = layer_state["width"]  # 54
        initial_layer_height = layer_state["height"]  # 54
        dx, dy = 50, 50
        new_layer_width = initial_layer_width + dx  # 104
        new_layer_height = initial_layer_height + dy  # 104

        # Calculate scale factors (as MoveTool.handleResize does)
        scale_x = new_layer_width / initial_layer_width
        scale_y = new_layer_height / initial_layer_height

        # BR handle: anchor at TL of shape bounds
        anchor_x = initial_shape_bounds["x"]  # 100
        anchor_y = initial_shape_bounds["y"]  # 100

        # Scale shapes
        scaled_shapes = [copy.deepcopy(s) for s in initial_shapes]
        for shape in scaled_shapes:
            scale_shape(shape, scale_x, scale_y, anchor_x, anchor_y)

        # After scaling, the TL corner should still be at (100, 100)
        new_bounds = calculate_shapes_bounds(scaled_shapes)

        print(f"Scale factors: {scale_x}, {scale_y}")
        print(f"Initial shape bounds: {initial_shape_bounds}")
        print(f"New shape bounds: {new_bounds}")
        print(f"Scaled rect: {scaled_shapes[0]}")

        # The top-left should stay fixed at (100, 100)
        assert new_bounds["x"] == pytest.approx(100, abs=0.1), \
            f"TL x should stay at 100, got {new_bounds['x']}"
        assert new_bounds["y"] == pytest.approx(100, abs=0.1), \
            f"TL y should stay at 100, got {new_bounds['y']}"

        # Width/height should scale proportionally
        expected_width = 50 * scale_x
        expected_height = 50 * scale_y
        assert new_bounds["width"] == pytest.approx(expected_width, abs=0.1)
        assert new_bounds["height"] == pytest.approx(expected_height, abs=0.1)

    def test_tl_handle_keeps_br_fixed(self):
        """Dragging TL handle should keep bottom-right corner of shapes fixed."""
        initial_shapes = [{
            "type": "rect",
            "x": 100,
            "y": 100,
            "width": 50,
            "height": 50,
        }]

        initial_shape_bounds = calculate_shapes_bounds(initial_shapes)
        layer_state = fit_to_content(initial_shapes)

        # BR corner of shapes is at (150, 150)
        initial_br_x = initial_shape_bounds["x"] + initial_shape_bounds["width"]
        initial_br_y = initial_shape_bounds["y"] + initial_shape_bounds["height"]

        # Simulate dragging TL handle to double the size
        # For TL: newWidth = initialWidth - dx, newOffsetX = initialOffsetX + (initialWidth - newWidth)
        initial_layer_width = layer_state["width"]
        initial_layer_height = layer_state["height"]
        dx, dy = -50, -50  # Dragging left and up
        new_layer_width = initial_layer_width - dx  # 104
        new_layer_height = initial_layer_height - dy  # 104

        scale_x = new_layer_width / initial_layer_width
        scale_y = new_layer_height / initial_layer_height

        # TL handle: anchor at BR of shape bounds
        anchor_x = initial_br_x  # 150
        anchor_y = initial_br_y  # 150

        scaled_shapes = [copy.deepcopy(s) for s in initial_shapes]
        for shape in scaled_shapes:
            scale_shape(shape, scale_x, scale_y, anchor_x, anchor_y)

        new_bounds = calculate_shapes_bounds(scaled_shapes)
        new_br_x = new_bounds["x"] + new_bounds["width"]
        new_br_y = new_bounds["y"] + new_bounds["height"]

        print(f"Scale factors: {scale_x}, {scale_y}")
        print(f"Initial BR: ({initial_br_x}, {initial_br_y})")
        print(f"New BR: ({new_br_x}, {new_br_y})")
        print(f"New bounds: {new_bounds}")

        # BR corner should stay fixed at (150, 150)
        assert new_br_x == pytest.approx(initial_br_x, abs=0.1), \
            f"BR x should stay at {initial_br_x}, got {new_br_x}"
        assert new_br_y == pytest.approx(initial_br_y, abs=0.1), \
            f"BR y should stay at {initial_br_y}, got {new_br_y}"

    def test_layer_bounds_match_after_resize(self):
        """After resize, layer bounds should correctly contain shapes."""
        initial_shapes = [{
            "type": "rect",
            "x": 100,
            "y": 100,
            "width": 50,
            "height": 50,
        }]

        initial_shape_bounds = calculate_shapes_bounds(initial_shapes)
        layer_state = fit_to_content(initial_shapes)

        # Double the size via BR handle
        scale_x, scale_y = 2.0, 2.0
        anchor_x = initial_shape_bounds["x"]
        anchor_y = initial_shape_bounds["y"]

        scaled_shapes = [copy.deepcopy(s) for s in initial_shapes]
        for shape in scaled_shapes:
            scale_shape(shape, scale_x, scale_y, anchor_x, anchor_y)

        # Simulate fitToContent after scaling
        new_layer_state = fit_to_content(scaled_shapes)
        new_shape_bounds = calculate_shapes_bounds(scaled_shapes)

        print(f"Scaled shape bounds: {new_shape_bounds}")
        print(f"New layer state: {new_layer_state}")

        # Layer should contain the shapes (with padding)
        assert new_layer_state["offsetX"] <= new_shape_bounds["x"]
        assert new_layer_state["offsetY"] <= new_shape_bounds["y"]
        assert (new_layer_state["offsetX"] + new_layer_state["width"] >=
                new_shape_bounds["x"] + new_shape_bounds["width"])
        assert (new_layer_state["offsetY"] + new_layer_state["height"] >=
                new_shape_bounds["y"] + new_shape_bounds["height"])

    def test_multiple_shapes_br_resize(self):
        """Multiple shapes should all scale correctly from TL anchor."""
        initial_shapes = [
            {
                "type": "rect",
                "x": 100,
                "y": 100,
                "width": 40,
                "height": 40,
            },
            {
                "type": "ellipse",
                "cx": 180,
                "cy": 120,
                "rx": 20,
                "ry": 20,
            }
        ]

        initial_shape_bounds = calculate_shapes_bounds(initial_shapes)
        # Bounds: x=100, y=100, width=100 (100 to 200), height=40 (100 to 140)

        print(f"Initial bounds: {initial_shape_bounds}")

        # Scale 2x from TL (BR handle drag)
        anchor_x = initial_shape_bounds["x"]  # 100
        anchor_y = initial_shape_bounds["y"]  # 100

        scaled_shapes = [copy.deepcopy(s) for s in initial_shapes]
        for shape in scaled_shapes:
            scale_shape(shape, 2.0, 2.0, anchor_x, anchor_y)

        new_bounds = calculate_shapes_bounds(scaled_shapes)

        print(f"Scaled rect: {scaled_shapes[0]}")
        print(f"Scaled ellipse: {scaled_shapes[1]}")
        print(f"New bounds: {new_bounds}")

        # TL should stay at (100, 100)
        assert new_bounds["x"] == pytest.approx(100, abs=0.1)
        assert new_bounds["y"] == pytest.approx(100, abs=0.1)

        # Dimensions should double
        assert new_bounds["width"] == pytest.approx(initial_shape_bounds["width"] * 2, abs=0.1)
        assert new_bounds["height"] == pytest.approx(initial_shape_bounds["height"] * 2, abs=0.1)

        # Individual shape checks
        # Rect should stay at (100, 100) with doubled size
        assert scaled_shapes[0]["x"] == pytest.approx(100, abs=0.1)
        assert scaled_shapes[0]["y"] == pytest.approx(100, abs=0.1)
        assert scaled_shapes[0]["width"] == pytest.approx(80, abs=0.1)
        assert scaled_shapes[0]["height"] == pytest.approx(80, abs=0.1)

        # Ellipse center should move: 100 + (180-100)*2 = 260
        assert scaled_shapes[1]["cx"] == pytest.approx(260, abs=0.1)
        assert scaled_shapes[1]["cy"] == pytest.approx(140, abs=0.1)  # 100 + (120-100)*2
        assert scaled_shapes[1]["rx"] == pytest.approx(40, abs=0.1)
        assert scaled_shapes[1]["ry"] == pytest.approx(40, abs=0.1)


class TestScaleFactorCalculation:
    """Test that scale factor calculation is correct."""

    def test_scale_factor_with_padding_mismatch(self):
        """
        The issue: layer dimensions include padding, but shape bounds don't.
        This test demonstrates the problem.
        """
        initial_shapes = [{
            "type": "rect",
            "x": 100,
            "y": 100,
            "width": 50,
            "height": 50,
        }]

        # Shape bounds (no padding): 50x50
        shape_bounds = calculate_shapes_bounds(initial_shapes)
        assert shape_bounds["width"] == 50
        assert shape_bounds["height"] == 50

        # Layer bounds (with padding=2): 54x54
        layer_state = fit_to_content(initial_shapes, padding=2)
        assert layer_state["width"] == 54
        assert layer_state["height"] == 54

        # If we want to resize to 100x100 shapes (2x scale)...
        # Using layer-based scale: newLayerWidth=108, scale=108/54=2.0 ✓
        # Using shape-based scale: newShapeWidth=100, scale=100/50=2.0 ✓
        # These match in this case, but the anchor point matters!

        # The problem is when dx/dy don't match the padding difference.
        # Let's say user drags +46 pixels (wants layer to be 100 pixels wide)
        dx = 46
        new_layer_width = layer_state["width"] + dx  # 54 + 46 = 100

        # Scale factor based on layer dimensions
        scale_layer = new_layer_width / layer_state["width"]  # 100/54 = 1.85

        # But the user probably expects the shapes to scale by the same visual amount
        # If layer goes from 54 to 100 (width), the SHAPES inside should also
        # scale proportionally. But the padding throws this off.

        print(f"dx={dx}, new_layer_width={new_layer_width}")
        print(f"Scale factor (layer-based): {scale_layer}")

        # With layer-based scaling: shape width = 50 * 1.85 = 92.6
        # New layer (with padding): would be 92.6 + 4 = 96.6, not 100!

        scaled_shapes = [copy.deepcopy(s) for s in initial_shapes]
        scale_shape(scaled_shapes[0], scale_layer, scale_layer,
                   shape_bounds["x"], shape_bounds["y"])

        new_shape_bounds = calculate_shapes_bounds(scaled_shapes)
        new_layer_state = fit_to_content(scaled_shapes, padding=2)

        print(f"Scaled shape width: {new_shape_bounds['width']}")
        print(f"New layer width: {new_layer_state['width']}")

        # This demonstrates the mismatch - the actual layer width won't be 100
        # because we scaled based on layer dimensions but padding is fixed.


class TestCorrectResizeApproach:
    """Test the correct approach: scale based on SHAPE bounds, not layer bounds."""

    def test_shape_based_scaling_br_handle(self):
        """
        Correct approach: track shape bounds, not layer bounds.
        When user drags BR handle, they want BR of SHAPES to follow cursor.
        """
        initial_shapes = [{
            "type": "rect",
            "x": 100,
            "y": 100,
            "width": 50,
            "height": 50,
        }]

        initial_shape_bounds = calculate_shapes_bounds(initial_shapes)
        # TL at (100, 100), BR at (150, 150)

        initial_tl_x = initial_shape_bounds["x"]
        initial_tl_y = initial_shape_bounds["y"]
        initial_br_x = initial_shape_bounds["x"] + initial_shape_bounds["width"]
        initial_br_y = initial_shape_bounds["y"] + initial_shape_bounds["height"]

        # User drags BR handle from (150, 150) to (200, 200)
        # They want the shapes to now span from (100, 100) to (200, 200)
        target_br_x = 200
        target_br_y = 200

        # Calculate scale to achieve this
        target_width = target_br_x - initial_tl_x  # 100
        target_height = target_br_y - initial_tl_y  # 100

        scale_x = target_width / initial_shape_bounds["width"]  # 100/50 = 2.0
        scale_y = target_height / initial_shape_bounds["height"]  # 100/50 = 2.0

        # Scale from TL anchor
        scaled_shapes = [copy.deepcopy(s) for s in initial_shapes]
        for shape in scaled_shapes:
            scale_shape(shape, scale_x, scale_y, initial_tl_x, initial_tl_y)

        new_bounds = calculate_shapes_bounds(scaled_shapes)

        # Verify TL stayed fixed and BR is at target
        assert new_bounds["x"] == pytest.approx(100, abs=0.1)
        assert new_bounds["y"] == pytest.approx(100, abs=0.1)
        assert new_bounds["x"] + new_bounds["width"] == pytest.approx(200, abs=0.1)
        assert new_bounds["y"] + new_bounds["height"] == pytest.approx(200, abs=0.1)

        print(f"✓ Shape-based scaling works correctly")
        print(f"  TL: ({new_bounds['x']}, {new_bounds['y']})")
        print(f"  BR: ({new_bounds['x'] + new_bounds['width']}, {new_bounds['y'] + new_bounds['height']})")
