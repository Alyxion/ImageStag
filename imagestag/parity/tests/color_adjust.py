"""Color adjustment filter parity test registration.

This module registers parity tests for color adjustment filters:
- Brightness, Contrast, Saturation
- Gamma, Exposure, Invert

Test inputs:
- deer_128: Noto emoji deer at 128x128 (vector with transparency)
- astronaut_128: Skimage astronaut at 128x128 (photographic, no transparency)
"""
from ..registry import register_filter_parity, TestCase
from ..runner import register_filter_impl


def register_color_adjust_parity():
    """Register color adjustment filter parity tests."""

    from imagestag.filters.color_adjust import (
        brightness, brightness_f32,
        contrast, contrast_f32,
        saturation, saturation_f32,
        gamma, gamma_f32,
        exposure, exposure_f32,
        invert, invert_f32,
    )
    from imagestag.filters.grayscale import convert_u8_to_f32, convert_f32_to_12bit

    # =========================================================================
    # Brightness
    # =========================================================================
    register_filter_parity("brightness", [
        TestCase(
            id="deer_128_bright",
            description="Noto emoji deer - brightness +0.3",
            width=128, height=128,
            input_generator="deer_128",
            bit_depth="u8",
            params={"amount": 0.3},
        ),
        TestCase(
            id="astronaut_128_dark",
            description="Skimage astronaut - brightness -0.2",
            width=128, height=128,
            input_generator="astronaut_128",
            bit_depth="u8",
            params={"amount": -0.2},
        ),
    ])
    register_filter_impl("brightness", lambda img, **p: brightness(img, p.get("amount", 0.0)))

    register_filter_parity("brightness_f32", [
        TestCase(
            id="deer_128_bright_f32",
            description="Noto emoji deer - brightness +0.3 (f32)",
            width=128, height=128,
            input_generator="deer_128",
            bit_depth="f32",
            params={"amount": 0.3},
        ),
    ])

    def brightness_f32_pipeline(image, **params):
        img_f32 = convert_u8_to_f32(image)
        result_f32 = brightness_f32(img_f32, params.get("amount", 0.0))
        return convert_f32_to_12bit(result_f32)

    register_filter_impl("brightness_f32", brightness_f32_pipeline)

    # =========================================================================
    # Contrast
    # =========================================================================
    register_filter_parity("contrast", [
        TestCase(
            id="deer_128_contrast",
            description="Noto emoji deer - contrast +0.5",
            width=128, height=128,
            input_generator="deer_128",
            bit_depth="u8",
            params={"amount": 0.5},
        ),
        TestCase(
            id="astronaut_128_contrast",
            description="Skimage astronaut - contrast -0.3",
            width=128, height=128,
            input_generator="astronaut_128",
            bit_depth="u8",
            params={"amount": -0.3},
        ),
    ])
    register_filter_impl("contrast", lambda img, **p: contrast(img, p.get("amount", 0.0)))

    register_filter_parity("contrast_f32", [
        TestCase(
            id="deer_128_contrast_f32",
            description="Noto emoji deer - contrast +0.5 (f32)",
            width=128, height=128,
            input_generator="deer_128",
            bit_depth="f32",
            params={"amount": 0.5},
        ),
    ])

    def contrast_f32_pipeline(image, **params):
        img_f32 = convert_u8_to_f32(image)
        result_f32 = contrast_f32(img_f32, params.get("amount", 0.0))
        return convert_f32_to_12bit(result_f32)

    register_filter_impl("contrast_f32", contrast_f32_pipeline)

    # =========================================================================
    # Saturation (requires RGBA)
    # =========================================================================
    register_filter_parity("saturation", [
        TestCase(
            id="deer_128_saturated",
            description="Noto emoji deer - saturation +0.5",
            width=128, height=128,
            input_generator="deer_128",
            bit_depth="u8",
            params={"amount": 0.5},
        ),
        TestCase(
            id="astronaut_128_desat",
            description="Skimage astronaut - saturation -0.5",
            width=128, height=128,
            input_generator="astronaut_128",
            bit_depth="u8",
            params={"amount": -0.5},
        ),
    ])
    register_filter_impl("saturation", lambda img, **p: saturation(img, p.get("amount", 0.0)))

    register_filter_parity("saturation_f32", [
        TestCase(
            id="deer_128_saturated_f32",
            description="Noto emoji deer - saturation +0.5 (f32)",
            width=128, height=128,
            input_generator="deer_128",
            bit_depth="f32",
            params={"amount": 0.5},
        ),
    ])

    def saturation_f32_pipeline(image, **params):
        img_f32 = convert_u8_to_f32(image)
        result_f32 = saturation_f32(img_f32, params.get("amount", 0.0))
        return convert_f32_to_12bit(result_f32)

    register_filter_impl("saturation_f32", saturation_f32_pipeline)

    # =========================================================================
    # Gamma
    # =========================================================================
    register_filter_parity("gamma", [
        TestCase(
            id="deer_128_gamma",
            description="Noto emoji deer - gamma 2.2",
            width=128, height=128,
            input_generator="deer_128",
            bit_depth="u8",
            params={"gamma_value": 2.2},
        ),
        TestCase(
            id="astronaut_128_gamma",
            description="Skimage astronaut - gamma 0.5",
            width=128, height=128,
            input_generator="astronaut_128",
            bit_depth="u8",
            params={"gamma_value": 0.5},
        ),
    ])
    register_filter_impl("gamma", lambda img, **p: gamma(img, p.get("gamma_value", 1.0)))

    register_filter_parity("gamma_f32", [
        TestCase(
            id="deer_128_gamma_f32",
            description="Noto emoji deer - gamma 2.2 (f32)",
            width=128, height=128,
            input_generator="deer_128",
            bit_depth="f32",
            params={"gamma_value": 2.2},
        ),
    ])

    def gamma_f32_pipeline(image, **params):
        img_f32 = convert_u8_to_f32(image)
        result_f32 = gamma_f32(img_f32, params.get("gamma_value", 1.0))
        return convert_f32_to_12bit(result_f32)

    register_filter_impl("gamma_f32", gamma_f32_pipeline)

    # =========================================================================
    # Exposure
    # =========================================================================
    register_filter_parity("exposure", [
        TestCase(
            id="deer_128_exposure",
            description="Noto emoji deer - exposure +1.0 stop",
            width=128, height=128,
            input_generator="deer_128",
            bit_depth="u8",
            params={"exposure_val": 1.0, "offset": 0.0, "gamma_val": 1.0},
        ),
        TestCase(
            id="astronaut_128_exposure",
            description="Skimage astronaut - exposure -0.5 stop",
            width=128, height=128,
            input_generator="astronaut_128",
            bit_depth="u8",
            params={"exposure_val": -0.5, "offset": 0.0, "gamma_val": 1.0},
        ),
    ])
    register_filter_impl("exposure", lambda img, **p: exposure(
        img, p.get("exposure_val", 0.0), p.get("offset", 0.0), p.get("gamma_val", 1.0)
    ))

    register_filter_parity("exposure_f32", [
        TestCase(
            id="deer_128_exposure_f32",
            description="Noto emoji deer - exposure +1.0 stop (f32)",
            width=128, height=128,
            input_generator="deer_128",
            bit_depth="f32",
            params={"exposure_val": 1.0, "offset": 0.0, "gamma_val": 1.0},
        ),
    ])

    def exposure_f32_pipeline(image, **params):
        img_f32 = convert_u8_to_f32(image)
        result_f32 = exposure_f32(
            img_f32,
            params.get("exposure_val", 0.0),
            params.get("offset", 0.0),
            params.get("gamma_val", 1.0),
        )
        return convert_f32_to_12bit(result_f32)

    register_filter_impl("exposure_f32", exposure_f32_pipeline)

    # =========================================================================
    # Invert
    # =========================================================================
    register_filter_parity("invert", [
        TestCase(
            id="deer_128_invert",
            description="Noto emoji deer - invert",
            width=128, height=128,
            input_generator="deer_128",
            bit_depth="u8",
        ),
        TestCase(
            id="astronaut_128_invert",
            description="Skimage astronaut - invert",
            width=128, height=128,
            input_generator="astronaut_128",
            bit_depth="u8",
        ),
    ])
    register_filter_impl("invert", lambda img, **p: invert(img))

    register_filter_parity("invert_f32", [
        TestCase(
            id="deer_128_invert_f32",
            description="Noto emoji deer - invert (f32)",
            width=128, height=128,
            input_generator="deer_128",
            bit_depth="f32",
        ),
    ])

    def invert_f32_pipeline(image, **params):
        img_f32 = convert_u8_to_f32(image)
        result_f32 = invert_f32(img_f32)
        return convert_f32_to_12bit(result_f32)

    register_filter_impl("invert_f32", invert_f32_pipeline)


__all__ = ['register_color_adjust_parity']
