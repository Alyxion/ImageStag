"""Tests for SKImage sample image loading utilities."""

import numpy as np
import pytest

from imagestag import Image
from imagestag.skimage import SKImage


class TestSKImageLoad:
    """Tests for SKImage.load() function."""

    def test_load_astronaut(self):
        img = SKImage.load("astronaut")
        assert img.width > 0
        assert img.height > 0

    def test_load_camera(self):
        img = SKImage.load("camera")
        assert img.width > 0

    def test_load_coffee(self):
        img = SKImage.load("coffee")
        assert img.width > 0

    def test_load_coins(self):
        img = SKImage.load("coins")
        assert img.width > 0

    def test_load_moon(self):
        img = SKImage.load("moon")
        assert img.width > 0

    def test_load_text(self):
        img = SKImage.load("text")
        assert img.width > 0

    def test_load_group(self):
        img = SKImage.load("group")
        assert img.width > 0

    def test_load_invalid_raises(self):
        with pytest.raises(ValueError):
            SKImage.load("nope")


class TestSKImageProperties:
    """Tests for SKImage property methods."""

    def test_coffee(self):
        assert SKImage.coffee().width > 0

    def test_horse(self):
        assert SKImage.horse().width > 0

    def test_hubble_deep_field(self):
        assert SKImage.hubble_deep_field().width > 0

    def test_immunohistochemistry(self):
        assert SKImage.immunohistochemistry().width > 0

    def test_moon(self):
        assert SKImage.moon().width > 0

    def test_page(self):
        assert SKImage.page().width > 0

    def test_rocket(self):
        assert SKImage.rocket().width > 0

    def test_text(self):
        assert SKImage.text().width > 0

    def test_cat_alias(self):
        assert SKImage.cat().width > 0

    def test_face_alias(self):
        assert SKImage.face().width > 0

    def test_faces_alias(self):
        assert SKImage.faces().width > 0


class TestSKImageToImage:
    """Tests for SKImage._to_image() conversion."""

    def test_2d_array_to_grayscale(self):
        arr2 = np.zeros((5, 6), dtype=np.uint8)
        img = SKImage._to_image(arr2)
        assert img.width == 6
        assert img.height == 5

    def test_3d_float_array(self):
        arr3 = np.zeros((5, 6, 3), dtype=np.float32)
        img = SKImage._to_image(arr3)
        assert img.width == 6

    def test_4d_array_raises(self):
        with pytest.raises(ValueError):
            SKImage._to_image(np.zeros((1, 2, 3, 4), dtype=np.uint8))

    def test_rgba_array(self):
        arr4 = np.zeros((5, 6, 4), dtype=np.uint8)
        img = SKImage._to_image(arr4)
        assert img.width == 6

    def test_float_to_uint8_coercion(self):
        arr = np.array([[0.0, 0.5, 1.0]], dtype=np.float32)
        img = SKImage._to_image(arr)
        px = img.get_pixels()
        assert px[0, 0, 0] == 0
        assert px[0, 1, 0] == 127 or px[0, 1, 0] == 128
        assert px[0, 2, 0] == 255

    def test_int32_to_uint8(self):
        arr2 = np.array([[0, 128, 255]], dtype=np.int32)
        img2 = SKImage._to_image(arr2)
        assert img2.get_pixels().dtype == np.uint8
