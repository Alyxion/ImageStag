"""Grayscale filter parity test registration.

This module registers parity tests for the grayscale filter and provides
the Python implementation for testing.

Test inputs:
- deer_128: Noto emoji deer at 128x128 (vector with transparency)
- astronaut_128: Skimage astronaut at 128x128 (photographic, no transparency)
"""
from ..registry import register_filter_parity, TestCase
from ..runner import register_filter_impl


def register_grayscale_parity():
    """Register grayscale filter parity tests."""

    # Register test cases - only using ground truth images
    register_filter_parity("grayscale", [
        TestCase(
            id="deer_128",
            description="Noto emoji deer - vector with transparency",
            width=128,
            height=128,
            input_generator="deer_128",
        ),
        TestCase(
            id="astronaut_128",
            description="Skimage astronaut - photographic image",
            width=128,
            height=128,
            input_generator="astronaut_128",
        ),
    ])

    # Register Python implementation
    from imagestag.filters.grayscale import grayscale
    register_filter_impl("grayscale", grayscale)


__all__ = ['register_grayscale_parity']
