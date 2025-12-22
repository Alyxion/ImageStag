"""
Tests for InterpolationMethod enum
"""

import PIL.Image

from imagestag import InterpolationMethod


def test_interpolation_values():
    """
    Tests basic InterpolationMethod values
    """
    assert InterpolationMethod.NEAREST.value == 0
    assert InterpolationMethod.LINEAR.value == 1
    assert InterpolationMethod.CUBIC.value == 2
    assert InterpolationMethod.LANCZOS.value == 3


def test_interpolation_to_pil():
    """
    Tests conversion to PIL resampling methods
    """
    assert InterpolationMethod.NEAREST.to_pil() == PIL.Image.Resampling.NEAREST
    assert InterpolationMethod.LINEAR.to_pil() == PIL.Image.Resampling.BILINEAR
    assert InterpolationMethod.CUBIC.to_pil() == PIL.Image.Resampling.BICUBIC
    assert InterpolationMethod.LANCZOS.to_pil() == PIL.Image.Resampling.LANCZOS


def test_interpolation_to_cv():
    """
    Tests conversion to OpenCV interpolation constants
    """
    # OpenCV constants: INTER_NEAREST_EXACT=6, INTER_LINEAR=1, INTER_CUBIC=2, INTER_LANCZOS4=4
    assert InterpolationMethod.NEAREST.to_cv() == 6
    assert InterpolationMethod.LINEAR.to_cv() == 1
    assert InterpolationMethod.CUBIC.to_cv() == 2
    assert InterpolationMethod.LANCZOS.to_cv() == 4
