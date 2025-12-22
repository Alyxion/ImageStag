"""
Tests for PixelFormat enum
"""

import pytest
from numpy import uint8

from imagestag import PixelFormat


def test_pixel_format_values():
    """
    Tests basic PixelFormat values
    """
    assert PixelFormat.RGB == 0
    assert PixelFormat.RGBA == 1
    assert PixelFormat.BGR == 5
    assert PixelFormat.BGRA == 6
    assert PixelFormat.GRAY == 10
    assert PixelFormat.UNSUPPORTED == 99


def test_pixel_format_from_string():
    """
    Tests creating PixelFormat from string
    """
    assert PixelFormat("rgb") == PixelFormat.RGB
    assert PixelFormat("RGB") == PixelFormat.RGB
    assert PixelFormat("rgba") == PixelFormat.RGBA
    assert PixelFormat("RGBA") == PixelFormat.RGBA
    assert PixelFormat("bgr") == PixelFormat.BGR
    assert PixelFormat("bgra") == PixelFormat.BGRA
    assert PixelFormat("gray") == PixelFormat.GRAY
    assert PixelFormat("g") == PixelFormat.GRAY
    assert PixelFormat("hsv") == PixelFormat.HSV


def test_pixel_format_from_pil():
    """
    Tests conversion from PIL format strings
    """
    assert PixelFormat.from_pil("rgb") == PixelFormat.RGB
    assert PixelFormat.from_pil("RGB") == PixelFormat.RGB
    assert PixelFormat.from_pil("rgba") == PixelFormat.RGBA
    assert PixelFormat.from_pil("l") == PixelFormat.GRAY
    assert PixelFormat.from_pil("L") == PixelFormat.GRAY
    assert PixelFormat.from_pil("hsv") == PixelFormat.HSV
    assert PixelFormat.from_pil("unknown") == PixelFormat.UNSUPPORTED


def test_pixel_format_to_pil():
    """
    Tests conversion to PIL format strings
    """
    assert PixelFormat.RGB.to_pil() == "RGB"
    assert PixelFormat.RGBA.to_pil() == "RGBA"
    assert PixelFormat.GRAY.to_pil() == "L"
    assert PixelFormat.HSV.to_pil() == "HSV"
    assert PixelFormat.BGR.to_pil() is None  # No direct PIL equivalent
    assert PixelFormat.BGRA.to_pil() is None


def test_pixel_format_band_names():
    """
    Tests band name properties
    """
    assert PixelFormat.RGB.band_names == ["R", "G", "B"]
    assert PixelFormat.RGBA.band_names == ["R", "G", "B", "A"]
    assert PixelFormat.BGR.band_names == ["B", "G", "R"]
    assert PixelFormat.BGRA.band_names == ["B", "G", "R", "A"]
    assert PixelFormat.GRAY.band_names == ["G"]
    assert PixelFormat.HSV.band_names == ["H", "S", "V"]


def test_pixel_format_full_band_names():
    """
    Tests full band name properties
    """
    assert PixelFormat.RGB.full_band_names == ["Red", "Green", "Blue"]
    assert PixelFormat.RGBA.full_band_names == ["Red", "Green", "Blue", "Alpha"]
    assert PixelFormat.BGR.full_band_names == ["Blue", "Green", "Red"]
    assert PixelFormat.BGRA.full_band_names == ["Blue", "Green", "Red", "Alpha"]
    assert PixelFormat.GRAY.full_band_names == ["Gray"]
    assert PixelFormat.HSV.full_band_names == ["Hue", "Saturation", "Value"]


def test_pixel_format_band_count():
    """
    Tests band count property
    """
    assert PixelFormat.RGB.band_count == 3
    assert PixelFormat.RGBA.band_count == 4
    assert PixelFormat.BGR.band_count == 3
    assert PixelFormat.BGRA.band_count == 4
    assert PixelFormat.GRAY.band_count == 1


def test_pixel_format_data_type():
    """
    Tests data type property
    """
    assert PixelFormat.RGB.data_type == uint8
    assert PixelFormat.RGBA.data_type == uint8
    assert PixelFormat.BGR.data_type == uint8
    assert PixelFormat.BGRA.data_type == uint8
    assert PixelFormat.GRAY.data_type == uint8


def test_pixel_format_string_conversion():
    """
    Tests string conversion edge cases
    """
    # Test that unknown strings don't create valid PixelFormat
    import pytest
    with pytest.raises(ValueError):
        PixelFormat("unknown_format")
