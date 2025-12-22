"""
Tests the ImageBase class, the foundation of the Image class
"""

from unittest import mock

import numpy as np
import pytest

from imagestag import Image, PixelFormat
from imagestag.image_base import ImageBase


def test_normalize_to_gray(stag_image_data):
    """
    Tests the gray normalization
    """
    org_image = image = Image(stag_image_data)
    image_rgba = org_image.copy().convert("rgba")
    image_cv = Image(stag_image_data, framework="CV")
    bgra_copy = Image(org_image.get_pixels(PixelFormat.BGRA))
    image_raw = Image(stag_image_data, framework="RAW")

    result_org = ImageBase.normalize_to_gray(image.pixels)
    result_org = ImageBase.normalize_to_gray(result_org)
    result_rgba = ImageBase.normalize_to_gray(image_rgba.pixels)
    result_cv = ImageBase.normalize_to_gray(
        image_cv.pixels, input_format=PixelFormat.BGR
    )
    result_cva = ImageBase.normalize_to_gray(
        bgra_copy.pixels, input_format=PixelFormat.BGRA
    )
    result_raw = ImageBase.normalize_to_gray(image_raw.pixels)
    assert np.all(result_org == result_cv)
    assert np.all(result_org == result_cva)
    assert np.all(result_org == result_raw)
    assert np.all(result_org == result_rgba)

    with mock.patch("imagestag.definitions.get_opencv", lambda: None):
        result_org = ImageBase.normalize_to_gray(image.pixels)
        result_rgba = ImageBase.normalize_to_gray(image_rgba.pixels)
        result_cv = ImageBase.normalize_to_gray(
            image_cv.pixels, input_format=PixelFormat.BGR
        )
        result_cva = ImageBase.normalize_to_gray(
            bgra_copy.pixels, input_format=PixelFormat.BGRA
        )
        result_raw = ImageBase.normalize_to_gray(image_raw.pixels)
        assert np.all(result_org == result_cv)
        assert np.all(result_org == result_cva)
        assert np.all(result_org == result_raw)
        assert np.all(result_org == result_rgba)

    img_cv2 = ImageBase.from_cv2(result_rgba)
    assert img_cv2.framework.name == "PIL"
    assert np.all(img_cv2.get_pixels_gray() == result_org)


def test_normalize_to_bgr(stag_image_data):
    """
    Tests the bgr normalization
    """
    org_image = Image(stag_image_data)
    image = org_image.copy().convert("g")
    g_result = ImageBase.normalize_to_bgr(
        image.get_pixels_gray(), keep_gray=True, input_format=PixelFormat.GRAY
    )
    assert len(g_result.shape) == 2
    result = ImageBase.normalize_to_bgr(
        image.get_pixels_gray(), keep_gray=False, input_format=PixelFormat.GRAY
    )
    assert len(result.shape) == 3
    assert np.all(
        ImageBase.normalize_to_gray(result, input_format=PixelFormat.BGR) == g_result
    )


def test_normalize_to_rgb(stag_image_data):
    """
    Tests the rgb normalization
    """
    org_image = Image(stag_image_data)
    image = org_image.copy().convert("g")
    g_result = ImageBase.normalize_to_rgb(
        image.get_pixels_gray(), keep_gray=True, input_format=PixelFormat.GRAY
    )
    assert len(g_result.shape) == 2
    result = ImageBase.normalize_to_rgb(
        image.get_pixels_gray(), keep_gray=False, input_format=PixelFormat.GRAY
    )
    assert len(result.shape) == 3
    result = ImageBase.normalize_to_rgb(
        org_image.get_pixels(), input_format=PixelFormat.RGB
    )
    assert len(result.shape) == 3
    assert np.all(result == org_image.get_pixels())


def test_bgr_to_rgb(stag_image_data):
    """
    Tests RGB to BGR
    """
    org_image = Image(stag_image_data).convert("rgba")
    pixels = org_image.pixels
    bgr = ImageBase.bgr_to_rgb(pixels)
    assert np.any(pixels != bgr)
    assert np.all(ImageBase.bgr_to_rgb(bgr) == pixels)
    with pytest.raises(ValueError):
        ImageBase.bgr_to_rgb(org_image.get_pixels_gray())


def test_pixel_data_from_source(stag_image_data):
    """
    Tests loading pixel data from a specific source
    """
    org_image = Image(stag_image_data).convert("rgba")
    pixels = org_image.pixels
    assert ImageBase._pixel_data_from_source(pixels) is pixels
    assert np.all(ImageBase._pixel_data_from_source(org_image.to_pil()) == pixels)
    with pytest.raises(NotImplementedError):
        assert ImageBase._pixel_data_from_source(123.45)


def test_detect_format():
    """
    Tests format detection
    """
    # Grayscale
    gray = np.zeros((10, 10), dtype=np.uint8)
    assert ImageBase.detect_format(gray) == PixelFormat.GRAY

    # RGB
    rgb = np.zeros((10, 10, 3), dtype=np.uint8)
    assert ImageBase.detect_format(rgb) == PixelFormat.RGB

    # RGBA
    rgba = np.zeros((10, 10, 4), dtype=np.uint8)
    assert ImageBase.detect_format(rgba) == PixelFormat.RGBA

    # BGR (cv2 mode)
    assert ImageBase.detect_format(rgb, is_cv2=True) == PixelFormat.BGR

    # BGRA (cv2 mode)
    assert ImageBase.detect_format(rgba, is_cv2=True) == PixelFormat.BGRA
