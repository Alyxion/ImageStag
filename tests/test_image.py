"""
Tests the features of the imagestag.image.Image class
"""

import io
import os
from unittest import mock

import numpy as np
import pytest

from imagestag import Image, ImsFramework, Colors, PixelFormat, Size2D


def test_load(stag_image_data):
    """
    Tests loading an image from bytes
    """
    image = Image(stag_image_data)
    assert image.get_size() == (665, 525)
    assert image.size == (665, 525)
    assert image.to_pil() is not None
    pixels = image.get_pixels()
    assert pixels.shape == (525, 665, 3)


def test_resize(stag_image_data):
    """
    Tests resizing an image
    """
    image = Image(stag_image_data)
    image.resize((100, 120))
    assert image.get_pixels().shape == (120, 100, 3)


def test_raw(stag_image_data):
    """
    Tests storing an image using numpy array storage
    """
    image_raw = Image(stag_image_data, framework=ImsFramework.RAW)
    data = image_raw.get_handle()
    assert isinstance(data, np.ndarray)


def test_image_color_conversion(stag_image_data):
    """
    Tests the color conversion functions of Image
    """
    image = Image(stag_image_data)
    pixel_data = image.get_pixels()
    rgb_pixels = image.copy().convert("RGBA")
    reread_rgb_pixels = rgb_pixels.get_pixels(desired_format="RGB")
    assert np.all(rgb_pixels.get_pixels_rgb() == reread_rgb_pixels)
    bgr_pixel_data = image.get_pixels_bgr()
    gray_pixel_data = image.get_pixels_gray()
    rgb_pixel = (144, 140, 137)
    assert tuple(pixel_data[50, 50, :]) == rgb_pixel
    assert tuple(bgr_pixel_data[50, 50, :]) == (137, 140, 144)
    assert gray_pixel_data[50, 50] == round(
        (np.array(rgb_pixel) * (0.2989, 0.5870, 0.1140)).sum()
    )
    grayscale_image = Image(gray_pixel_data)
    assert grayscale_image.pixel_format == PixelFormat.GRAY


def test_resize_ext(stag_image_data):
    """
    Tests Image.resize_ext
    """
    image = Image(stag_image_data)
    # to widescreen
    rescaled = image.resized_ext(target_aspect=16 / 9)
    rescaled_pixels = rescaled.get_pixels()
    black_bar_mean = (
        rescaled_pixels[0:, 0:100].mean() + rescaled_pixels[0:, -100:].mean()
    )
    assert black_bar_mean == 0.0
    mean_rescaled = np.mean(rescaled_pixels)
    assert mean_rescaled == pytest.approx(87.5, 0.5)

    # to portrait mode
    rescaled = image.resized_ext(target_aspect=9 / 16)
    rescaled_pixels = rescaled.get_pixels()
    black_bar_mean = (
        rescaled_pixels[0:100, 0:].mean() + rescaled_pixels[-100:, 0:].mean()
    )
    assert black_bar_mean == 0.0
    assert rescaled.width < rescaled.height

    # fill widescreen
    filled = image.resized_ext(size=(1920, 1080), fill_area=True, keep_aspect=True)
    with pytest.raises(ValueError):
        image.resized_ext(
            size=(1920, 1080), factor=(1.5, 1.5), fill_area=True, keep_aspect=True
        )
    filled_pixels = filled.get_pixels()
    mean_filled = np.mean(filled_pixels)
    assert mean_filled == pytest.approx(120.6, 0.05)
    assert filled.width == 1920

    # filled portrait
    filled = image.resized_ext(size=(1080, 1920), fill_area=True, keep_aspect=True)
    filled_pixels = filled.get_pixels()
    mean_filled = np.mean(filled_pixels)
    assert mean_filled == pytest.approx(120.6, 0.05)
    assert filled.width == 1080

    filled = image.resized_ext(size=(1080, 1920), fill_area=False, keep_aspect=True)
    filled_pixels = filled.get_pixels()
    mean_filled = np.mean(filled_pixels)
    assert mean_filled == pytest.approx(54.57, 0.05)

    just_scaled = image.resized_ext(size=(600, 600))
    just_scaled_pixels = just_scaled.get_pixels()
    just_scaled_mean = np.mean(just_scaled_pixels)
    assert just_scaled_mean == pytest.approx(120, 0.05)

    scaled_aspect = image.resized_ext(target_aspect=16 / 9, factor=2.0)
    scaled_aspect = scaled_aspect.get_pixels()
    scaled_aspect_mean = np.mean(scaled_aspect)
    assert scaled_aspect_mean == pytest.approx(87.5, 0.05)

    # test exceptions
    with pytest.raises(ValueError):
        image.resized_ext(size=(1080, 1920), fill_area=True, keep_aspect=False)
    with pytest.raises(ValueError):
        image.resized_ext(size=(1080, 1920), target_aspect=16 / 9)

    filled = image.resized_ext(max_size=(128, 128))
    max_size_pixels = filled.get_pixels()
    mean_max_size = np.mean(max_size_pixels)
    single_val = image.resized_ext(max_size=128)
    assert single_val.width == 128
    max_width = image.resized_ext(max_size=(128, None))
    assert max_width.width == 128 and max_width.height != 128
    max_height = image.resized_ext(max_size=(None, 128))
    assert max_height.height == 128 and max_width.width == 128
    with pytest.raises(ValueError):
        image.resized_ext(max_size=(None, None))
    assert mean_max_size == pytest.approx(120.6, 0.05)


def test_encoding(stag_image_data, tmp_path):
    """
    Tests encoding the image in different formats
    """
    image = Image(stag_image_data)
    jpg1_data = image.encode(filetype="jpg", quality=95)
    assert jpg1_data is not None and len(jpg1_data) > 2000
    jpg2_data = image.encode(filetype="jpg", quality=20)
    assert jpg2_data is not None and len(jpg2_data) < len(jpg1_data)
    png_data = image.encode(filetype="png")
    cv2_png_image = Image(png_data, framework=ImsFramework.CV)
    assert np.all(image.get_pixels_rgb() == cv2_png_image.get_pixels_rgb())
    assert png_data is not None and len(png_data) > 0
    assert image.to_png() == png_data
    assert len(image.to_jpeg()) < len(png_data)

    test_path = str(tmp_path.joinpath("test_output.png"))
    image.save(target=test_path)
    assert os.path.getsize(test_path) == len(png_data)

    decoded_png = Image(png_data)
    assert np.array_equal(decoded_png.get_pixels_rgb(), image.get_pixels_rgb())

    bmp_data = image.encode(filetype="bmp")
    assert bmp_data is not None and len(bmp_data) > 0
    decoded_bmp = Image(bmp_data)
    assert np.array_equal(decoded_bmp.get_pixels_rgb(), image.get_pixels_rgb())

    # Test tuple filetype
    jpg_tuple_data = image.encode(filetype=("jpg", 90))
    assert jpg_tuple_data is not None


def test_numpy_support(stag_image_data):
    """
    Tests the conversion to numpy
    """
    image = Image(stag_image_data)
    pi_repr = image.to_pil().__array_interface__
    np_repr = image.__array_interface__
    assert pi_repr["data"] == np_repr["data"]
    assert pi_repr["shape"] == np_repr["shape"]
    assert pi_repr["typestr"] == np_repr["typestr"]
    assert pi_repr["version"] == np_repr["version"]
    assert np_repr is not None


def test_hsv(stag_image_data):
    """
    Tests the HSV support of an image
    """
    image = Image(stag_image_data)
    org_image = image.copy()
    image.convert("hsv")
    bands = image.split()
    assert len(bands) == 3
    org_image_raw = org_image.convert_to_raw().copy()
    assert isinstance(org_image_raw.get_handle(), np.ndarray)


def test_creation():
    """
    Test image creation with different parameters
    """
    image = Image(size=(32, 32))
    assert image.width == 32 and image.height == 32
    assert image.pixel_format.name == "RGB"
    assert tuple(image.get_pixels()[0, 0]) == (0, 0, 0)

    image = Image(size=(32, 32), bg_color=Colors.RED)
    assert image.width == 32 and image.height == 32
    assert image.pixel_format.name == "RGB"
    assert tuple(image.get_pixels()[0, 0]) == (255, 0, 0)

    with pytest.raises(ValueError):
        Image(source=np.zeros((5, 5)), size=(5, 5))
    with pytest.raises(ValueError):
        Image(source=np.zeros((5, 5), dtype=np.uint8), framework=99)


def test_protection():
    """
    Try manipulation values
    """
    image = Image(size=(32, 32))
    with pytest.raises(ValueError):
        image.width = 3
    image.new_value = 23


def test_conversion(stag_image_data):
    """
    Tries converting the image
    """
    image = Image(size=(32, 32), bg_color=Colors.RED)
    png = image.to_png()
    repr_png = image._repr_png_()
    assert repr_png == png
    reloaded = Image(png)
    assert np.all(image.get_pixels() == reloaded.get_pixels())

    cv_image = Image(
        image.get_pixels(), pixel_format=PixelFormat.RGB, framework=ImsFramework.CV
    )
    assert np.all(image.get_pixels() == cv_image.get_pixels_rgb())
    assert np.all(image.to_cv2() == cv_image.get_pixels())

    split_channels = image.split()
    assert len(split_channels) == 3
    assert split_channels[0][0][0] == 255
    assert split_channels[2][0][0] == 0
    assert image.band_names == ["R", "G", "B"]

    gray_image = image.copy().convert(PixelFormat.GRAY)
    assert gray_image.band_names == ["G"]
    split_channels = gray_image.split()
    assert len(split_channels) == 1
    assert split_channels[0][0][0] == 76
    assert len(gray_image.get_raw_data()) == (32 * 32)

    with pytest.raises(NotImplementedError):
        gray_image.get_pixels(desired_format=PixelFormat.HSV)

    cv_image.convert(PixelFormat.RGB)
    assert cv_image.framework

    # PIL to RAW and back
    stag = Image(stag_image_data)
    raw_image = stag.copy()
    raw_image.convert_to_raw()
    raw_image.convert_to_raw()  # provoke skip
    assert raw_image.framework == ImsFramework.RAW
    assert np.all(raw_image.get_pixels() == stag.get_pixels())
    raw_image.convert_to_pil()
    raw_image.convert_to_pil()  # provoke skip
    assert np.all(raw_image.get_pixels() == stag.get_pixels())
    assert raw_image.framework == ImsFramework.PIL

    # paletted image
    stag.resize((80, 80))
    pal_data = io.BytesIO()
    stag.copy().to_pil().convert("P").save(pal_data, format="png")
    reloaded_pal = Image(pal_data.getvalue())
    assert reloaded_pal.width == stag.width


def test_bgr_support():
    """
    Tests BGR support
    """
    image = Image(source=np.zeros((5, 5, 3), dtype=np.uint8))
    # keep size
    assert image.resized((5, 5)).get_size() == (5, 5)
    # PIL resize
    assert image.resized((10, 10)).get_size() == (10, 10)
    assert not image.is_bgr()

    image = Image(
        source=np.zeros((5, 5), dtype=np.uint8),
        pixel_format=PixelFormat.BGR,
        framework=ImsFramework.CV,
    )
    assert not image.is_bgr()  # b/c it's gray

    image = Image(
        source=np.zeros((5, 5, 3), dtype=np.uint8),
        pixel_format=PixelFormat.BGR,
        framework=ImsFramework.CV,
    )
    assert image.is_bgr()
    assert image.band_names == ["B", "G", "R"]
    assert image.get_size() == (5, 5)
    assert image.get_size_as_size().width == 5

    image = Image(
        source=np.zeros((5, 5, 3), dtype=np.uint8),
        pixel_format=PixelFormat.RGB,
        framework=ImsFramework.RAW,
    )
    assert not image.is_bgr()
    assert image.band_names == ["R", "G", "B"]

    image = Image(
        source=np.zeros((5, 5, 3), dtype=np.uint8),
        pixel_format=PixelFormat.BGR,
        framework=ImsFramework.RAW,
    )
    assert image.band_names == ["R", "G", "B"]
    assert image.resized((8, 8)).get_size() == (8, 8)

    # cv2 resize
    image.resize((10, 10))
    assert image.get_size() == (10, 10)

    with mock.patch("imagestag.definitions.OpenCVHandler.available", False):
        image.resize((14, 14))
        assert image.get_size() == (14, 14)


def test_crop(stag_image_data):
    """
    Tests the crop function
    """
    stag = Image(stag_image_data)
    cropped = stag.cropped((0, 0, 10.0, 10.0))
    assert cropped.width == 10 and cropped.height == 10
    with pytest.raises(ValueError):
        _ = stag.cropped((8, 8, -4, 10.0))
    with pytest.raises(ValueError):
        _ = stag.cropped((2000, 8, 3000, 10.0))
    with pytest.raises(ValueError):
        _ = stag.cropped((-1000, 8, -4, 10.0))
    stag.convert_to_raw()
    cropped = stag.cropped((0, 0, 10.0, 10.0))
    assert cropped.width == 10 and cropped.height == 10


def test_damaged():
    """
    Tests if loading successfully fails for damaged images
    """
    with pytest.raises(ValueError):
        Image(b"12345", framework=ImsFramework.RAW)
    with pytest.raises(ValueError):
        Image(b"12345", framework=ImsFramework.CV)


def test_compare(stag_image_data):
    """
    Tests image comparison
    """
    stag = Image(stag_image_data)
    stag_two = Image(stag_image_data)
    assert stag == stag_two
    stag.convert_to_raw()
    assert stag == stag_two


def test_convert_gray():
    """
    Tests conversion functions
    """
    gray_image = Image(bg_color="#FF0000", size=(16, 16), pixel_format="RGBA")
    assert str(gray_image) == "Image (PIL 16x16 RGBA)"
    pix_sum = np.sum(gray_image.get_pixels_gray()).tolist()
    assert pix_sum == 19456
    with pytest.raises(ValueError):
        gray_image.convert_gray_to_rgba("#FF0000")


def test_compute_rescaled_size_from_max_size():
    """
    Tests the compute rescaled_size method
    """
    simple = Image(bg_color="#FF0000", size=(20, 10), pixel_format="RGBA")
    assert (
        simple.compute_rescaled_size_from_max_size(
            max_size=(40, 20), org_size=Size2D(20, 10)
        )[1]
        == 20
    )
    assert (
        simple.compute_rescaled_size_from_max_size(
            max_size=Size2D(40, 20), org_size=Size2D(20, 10)
        )[1]
        == 20
    )
    assert (
        simple.compute_rescaled_size_from_max_size(
            max_size=60, org_size=Size2D(20, 10)
        )[1]
        == 30
    )


def test_from_array():
    """
    Tests creating an image from an array
    """
    test_data = np.zeros((32, 32), dtype=np.uint8)
    black_array = Image.from_array(test_data, normalize=False)
    assert black_array.pixel_format == PixelFormat.GRAY
    assert black_array.width == 32

    # Test with normalization
    test_data_float = np.ones((32, 32)) * 0.5
    normalized = Image.from_array(test_data_float, normalize=True)
    assert normalized.pixel_format == PixelFormat.GRAY

    # Test 3-channel array
    rgb_data = np.zeros((32, 32, 3), dtype=np.uint8)
    rgb_image = Image.from_array(rgb_data, normalize=False)
    assert rgb_image.pixel_format == PixelFormat.RGB


def test_hash(stag_image_data):
    """
    Tests image hashing
    """
    stag = Image(stag_image_data)
    hash1 = stag.get_hash()
    assert len(hash1) == 32  # MD5 hex string
    stag2 = Image(stag_image_data)
    assert stag.get_hash() == stag2.get_hash()
