"""Pixel count assertion utilities for Stagforge testing.

Testing Principles:
1. ALWAYS use range-based assertions, never just "changed" checks
2. Calculate expected pixel counts from geometry:
   - Line: length x width
   - Rectangle: width x height
   - Circle: pi x r^2
   - Ellipse: pi x a x b
   - Stroke/outline: perimeter x stroke_width
3. Apply appropriate tolerance for rasterization effects:
   - Rectangles: +/-10% (minimal antialiasing)
   - Lines: +/-30% (end caps, antialiasing)
   - Circles/ellipses: +/-20% (rasterization)
   - Diagonal lines: +/-35% (more antialiasing)
4. Use exact counts (==) for:
   - Undo/redo operations (must restore exactly)
   - Operations outside layer bounds (must be 0)
   - Layer fill operations (must be exact area)
"""

import math
from typing import Tuple


def approx_line_pixels(length: float, width: float, tolerance: float = 0.30) -> Tuple[int, int]:
    """
    Calculate expected pixel range for a line/stroke.

    Formula: length x width
    Default tolerance: +/-30% (accounts for antialiasing, end caps)

    Args:
        length: Length of the stroke in pixels
        width: Width/size of the brush/stroke
        tolerance: Fractional tolerance (0.30 = +/-30%)

    Returns:
        (min_pixels, max_pixels) tuple

    Example:
        >>> min_px, max_px = approx_line_pixels(100, 4)  # 4px wide, 100px long
        >>> # Expected ~400 pixels, range 280-520
    """
    expected = length * width
    return (int(expected * (1 - tolerance)), int(expected * (1 + tolerance)))


def approx_rect_pixels(width: float, height: float, tolerance: float = 0.10) -> Tuple[int, int]:
    """
    Calculate expected pixel range for a filled rectangle.

    Formula: width x height
    Default tolerance: +/-10% (rectangles are precise)

    Args:
        width, height: Dimensions of rectangle
        tolerance: Fractional tolerance (0.10 = +/-10%)

    Returns:
        (min_pixels, max_pixels) tuple

    Example:
        >>> min_px, max_px = approx_rect_pixels(80, 60)
        >>> # Expected 4800 pixels, range 4320-5280
    """
    expected = width * height
    return (int(expected * (1 - tolerance)), int(expected * (1 + tolerance)))


def approx_rect_outline_pixels(width: float, height: float, stroke: float,
                                tolerance: float = 0.30) -> Tuple[int, int]:
    """
    Calculate expected pixel range for rectangle outline.

    Formula: 2x(width + height) x stroke_width
    Default tolerance: +/-30% (corner overlaps vary)

    Args:
        width, height: Outer dimensions of rectangle
        stroke: Stroke width
        tolerance: Fractional tolerance

    Returns:
        (min_pixels, max_pixels) tuple
    """
    perimeter = 2 * (width + height)
    expected = perimeter * stroke
    return (int(expected * (1 - tolerance)), int(expected * (1 + tolerance)))


def approx_circle_pixels(radius: float, tolerance: float = 0.20) -> Tuple[int, int]:
    """
    Calculate expected pixel range for a filled circle.

    Formula: pi x r^2
    Default tolerance: +/-20% (rasterization effects)

    Args:
        radius: Radius of the circle
        tolerance: Fractional tolerance (0.20 = +/-20%)

    Returns:
        (min_pixels, max_pixels) tuple

    Example:
        >>> min_px, max_px = approx_circle_pixels(40)
        >>> # Expected ~5027 pixels (pi x 40^2), range ~4022-6032
    """
    expected = math.pi * radius * radius
    return (int(expected * (1 - tolerance)), int(expected * (1 + tolerance)))


def approx_ellipse_pixels(semi_a: float, semi_b: float, tolerance: float = 0.20) -> Tuple[int, int]:
    """
    Calculate expected pixel range for a filled ellipse.

    Formula: pi x a x b (where a, b are semi-axes)
    Default tolerance: +/-20%

    Args:
        semi_a: Horizontal semi-axis
        semi_b: Vertical semi-axis
        tolerance: Fractional tolerance

    Returns:
        (min_pixels, max_pixels) tuple
    """
    expected = math.pi * semi_a * semi_b
    return (int(expected * (1 - tolerance)), int(expected * (1 + tolerance)))


def approx_circle_outline_pixels(radius: float, stroke: float,
                                  tolerance: float = 0.25) -> Tuple[int, int]:
    """
    Calculate expected pixel range for circle outline.

    Formula: 2*pi*r x stroke_width
    Default tolerance: +/-25%

    Args:
        radius: Circle radius (to center of stroke)
        stroke: Stroke width
        tolerance: Fractional tolerance

    Returns:
        (min_pixels, max_pixels) tuple
    """
    circumference = 2 * math.pi * radius
    expected = circumference * stroke
    return (int(expected * (1 - tolerance)), int(expected * (1 + tolerance)))


def diagonal_length(x1: float, y1: float, x2: float, y2: float) -> float:
    """
    Calculate the length of a diagonal line.

    Args:
        x1, y1: Start point
        x2, y2: End point

    Returns:
        Length in pixels
    """
    return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)


def assert_pixel_count_in_range(actual: int, min_expected: int, max_expected: int,
                                 description: str = "Pixel count") -> None:
    """
    Assert that a pixel count falls within expected range.

    Args:
        actual: Actual pixel count
        min_expected: Minimum expected
        max_expected: Maximum expected
        description: Description for error message

    Raises:
        AssertionError with detailed message if out of range
    """
    assert min_expected <= actual <= max_expected, \
        f"{description}: expected {min_expected}-{max_expected}, got {actual}"


def assert_pixel_count_exact(actual: int, expected: int, description: str = "Pixel count") -> None:
    """
    Assert that a pixel count is exactly as expected.

    Use for:
    - Undo/redo operations
    - Empty areas (should be 0)
    - Full layer fills (exact area)

    Args:
        actual: Actual pixel count
        expected: Expected exact count
        description: Description for error message
    """
    assert actual == expected, \
        f"{description}: expected exactly {expected}, got {actual}"


def assert_pixel_ratio(small: int, large: int, expected_ratio: float,
                       tolerance: float = 0.40, description: str = "Ratio") -> None:
    """
    Assert that the ratio between two pixel counts is approximately correct.

    Useful for testing scaling relationships (e.g., 2x radius = 4x area).

    Args:
        small: Smaller pixel count
        large: Larger pixel count
        expected_ratio: Expected ratio (large/small)
        tolerance: Fractional tolerance
        description: Description for error message
    """
    if small == 0:
        raise AssertionError(f"{description}: cannot compute ratio with 0 pixels")

    actual_ratio = large / small
    min_ratio = expected_ratio * (1 - tolerance)
    max_ratio = expected_ratio * (1 + tolerance)

    assert min_ratio <= actual_ratio <= max_ratio, \
        f"{description}: expected ratio {min_ratio:.2f}-{max_ratio:.2f}, got {actual_ratio:.2f} ({small} vs {large})"
