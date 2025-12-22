"""
Tests the Color class
"""

import numpy as np
import pytest

from imagestag import Color, Colors, PixelFormat


def test_color_basics():
    """
    Tests the color basic functions
    """
    color = Color(Colors.WHITE)
    assert color.r == 1.0 and color.g == 1.0 and color.b == 1.0 and color.a == 1.0
    assert str(color) == "Color(1.0,1.0,1.0)"
    color = Color((0.2, 0.3, 0.4, 0.5))
    assert str(color) == "Color(0.2,0.3,0.4,0.5)"
    assert color.to_rgb() == (0.2, 0.3, 0.4)
    assert color.to_rgba() == (0.2, 0.3, 0.4, 0.5)
    assert color.to_int_rgb() == (51, 76, 102)
    assert color.to_int_rgba() == (51, 76, 102, 128)
    color = Color(red=0.2, green=0.3, blue=0.4, alpha=0.5)
    assert color.to_rgba() == (0.2, 0.3, 0.4, 0.5)
    color = Color(color)
    assert color.to_rgba() == (0.2, 0.3, 0.4, 0.5)
    with pytest.raises(RuntimeError):
        color.r = 0.5
    with pytest.raises(ValueError):
        # noinspection PyTypeChecker
        Color((0.2, 0.3, 0.4, 0.5, 0.6))
    assert Color((0.0, 0.0, 1.0)) == Colors.BLUE
    assert Color("#AABBCCAB").to_rgba() == pytest.approx((0.66, 0.73, 0.8, 0.67), 0.02)
    with pytest.raises(ValueError):
        Color("whatever")
    assert Color(color) == color
    assert Color(color) != Colors.WHITE
    with pytest.raises(ValueError):
        Color(None)
    with pytest.raises(TypeError):
        # noinspection PyTypeChecker
        Color(np.zeros((5, 3)))
    assert Color((255, 255, 255, 255)) == Colors.WHITE
    assert Color((255, 255, 255)) == Colors.WHITE
    assert Color((255, 0, 255, 255)) == Colors.FUCHSIA
    # test passing colors as rgb int
    assert Color(255, 255, 255) == Color((255, 255, 255))
    assert Color(255, 255, 255, 127 / 255) == Color(255, 255, 255, 127)


def test_conversion_functions():
    """
    Test advanced conversion functions
    """
    assert Color(244, 48, 29).to_int_hsv() == (4, 225, 244)
    assert Color(40, 48, 240).to_int_hsv() == (168, 212, 240)
    assert Color(0, 0, 0).to_int_hsv() == (0, 0, 0)
    assert Color.from_hsv(168 / 255 * 360, 212 / 255, 240 / 255).to_int_rgb() == (
        40,
        49,
        240,
    )
    assert Color.from_hsv(50, 0.0, 0.5).to_int_rgb() == (128, 128, 128)
    h, s, v = Color(30, 98, 29).to_hsv()
    assert h == pytest.approx(119, 0.01)
    assert s == pytest.approx(0.7, 0.01)
    assert v == pytest.approx(0.3843, 0.01)
    gray = Color(123, 64, 59).to_gray()
    assert gray == pytest.approx(0.3179, 0.01)
    gray = Color(30, 190, 110).to_int_gray()
    assert gray == pytest.approx(133, 0.01)
    assert Color(255, 44, 38).to_int_bgr() == (38, 44, 255)
    assert Color(255, 44, 38).to_int_bgra() == (38, 44, 255, 255)
    assert Color(255, 44, 38, 33).to_int_bgra() == (38, 44, 255, 33)
    with pytest.raises(ValueError):
        Color(255, 44, 38, 33).to_format(PixelFormat.UNSUPPORTED)


def test_color_hex():
    """
    Tests hex conversion
    """
    assert Colors.RED.to_hex() == "#FF0000"
    assert Colors.WHITE.to_hex() == "#FFFFFF"
    assert Colors.BLACK.to_hex() == "#000000"
    assert Color(255, 0, 0, 128).to_hex() == "#FF000080"


def test_color_int_rgb_auto():
    """
    Tests to_int_rgb_auto method
    """
    # No alpha
    color = Color(255, 128, 64)
    assert color.to_int_rgb_auto() == (255, 128, 64)

    # With alpha
    color = Color(255, 128, 64, 200)
    assert color.to_int_rgb_auto() == (255, 128, 64, 200)


def test_color_to_format():
    """
    Tests color format conversion
    """
    color = Color(255, 128, 64)
    assert color.to_format(PixelFormat.RGB) == (255, 128, 64)
    assert color.to_format(PixelFormat.RGBA) == (255, 128, 64, 255)
    assert color.to_format(PixelFormat.BGR) == (64, 128, 255)
    # Weighted gray: 0.299*255 + 0.587*128 + 0.114*64 = 159
    assert color.to_format(PixelFormat.GRAY) == 159


def test_predefined_colors():
    """
    Tests predefined color constants
    """
    assert Colors.BLACK.to_int_rgb() == (0, 0, 0)
    assert Colors.WHITE.to_int_rgb() == (255, 255, 255)
    assert Colors.RED.to_int_rgb() == (255, 0, 0)
    assert Colors.GREEN.to_int_rgb() == (0, 255, 0)
    assert Colors.BLUE.to_int_rgb() == (0, 0, 255)
    assert Colors.YELLOW.to_int_rgb() == (255, 255, 0)
    assert Colors.CYAN.to_int_rgb() == (0, 255, 255)
    assert Colors.MAGENTA.to_int_rgb() == (255, 0, 255)
    assert Colors.TRANSPARENT.to_int_rgba() == (0, 0, 0, 0)
