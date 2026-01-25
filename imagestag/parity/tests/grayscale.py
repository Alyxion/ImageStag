"""Grayscale filter parity test registration.

This module registers parity tests for the grayscale filter and provides
the Python implementation for testing.

## Bit Depth Support

- **u8 (8-bit)**: Values 0-255, stored as lossless AVIF
- **f32 (float)**: Values 0.0-1.0, converted to u8 for comparison

Test inputs:
- deer_128: Noto emoji deer at 128x128 (vector with transparency)
- astronaut_128: Skimage astronaut at 128x128 (photographic, no transparency)
"""
from ..registry import register_filter_parity, TestCase
from ..runner import register_filter_impl


def register_grayscale_parity():
    """Register grayscale filter parity tests (u8 and f32)."""

    # Register u8 test cases
    register_filter_parity("grayscale", [
        TestCase(
            id="deer_128",
            description="Noto emoji deer - vector with transparency",
            width=128,
            height=128,
            input_generator="deer_128",
            bit_depth="u8",
        ),
        TestCase(
            id="astronaut_128",
            description="Skimage astronaut - photographic image",
            width=128,
            height=128,
            input_generator="astronaut_128",
            bit_depth="u8",
        ),
    ])

    # Register f32 test cases (processed via float, stored as u8)
    register_filter_parity("grayscale_f32", [
        TestCase(
            id="deer_128_f32",
            description="Noto emoji deer - float version",
            width=128,
            height=128,
            input_generator="deer_128",
            bit_depth="f32",
        ),
        TestCase(
            id="astronaut_128_f32",
            description="Skimage astronaut - float version",
            width=128,
            height=128,
            input_generator="astronaut_128",
            bit_depth="f32",
        ),
    ])

    # Register Python implementations
    from imagestag.filters.grayscale import (
        grayscale,
        grayscale_f32,
        convert_u8_to_f32,
        convert_f32_to_12bit,
    )

    # u8 implementation
    register_filter_impl("grayscale", grayscale)

    # f32 implementation (convert u8->f32, process, convert to 12-bit for storage)
    def grayscale_f32_pipeline(image):
        """Process image using f32 pipeline, return 12-bit uint16 for storage."""
        img_f32 = convert_u8_to_f32(image)
        result_f32 = grayscale_f32(img_f32)
        return convert_f32_to_12bit(result_f32)

    register_filter_impl("grayscale_f32", grayscale_f32_pipeline)


__all__ = ['register_grayscale_parity']
