"""Centralized filter catalog for parity testing.

This module defines ALL cross-platform filters with their default test parameters.
Tests are automatically generated for each filter - no individual test files needed.

## Adding a New Filter

1. Add an entry to FILTER_CATALOG with:
   - name: Filter name (matches Rust/Python/JS function name)
   - params: Default parameters for testing
   - inputs: List of input names (optional, defaults to ["deer", "astronaut"])
   - skip_f32: Set True if no f32 variant exists

2. Register the Python implementation in register_all_filters()

## Filter Catalog Schema

```python
{
    "name": "brightness",           # Filter name
    "params": {"amount": 0.3},      # Test parameters
    "inputs": ["deer", "astronaut"],  # Optional, these are the defaults
    "skip_f32": False,              # Skip f32 test (optional, defaults to False)
    "tolerance": 0.001,             # Diff tolerance (optional, defaults to 0.001)
}
```

## Test Inputs

By default, EVERY filter is tested with BOTH inputs for comprehensive coverage:
- deer: Noto emoji deer - colorful vector WITH TRANSPARENCY (4 channels RGBA)
- astronaut: Skimage astronaut - photographic, SOLID (3 channels RGB)

Custom inputs should only be used in exceptional cases (e.g., line/circle detection).
"""
from typing import Any, Callable
import numpy as np

from .constants import (
    TEST_WIDTH,
    TEST_HEIGHT,
    TEST_INPUTS,
    DEFAULT_INPUT_NAMES,
    DEFAULT_TOLERANCE,
)
from .registry import register_filter_parity, TestCase
from .runner import register_filter_impl

# Type alias for filter functions
FilterFunc = Callable[..., np.ndarray]


# =============================================================================
# FILTER CATALOG - All cross-platform filters with default test parameters
#
# Each filter is tested with BOTH deer_128 (transparency) and astronaut_128
# (solid) by default. Only specify "inputs" to override for special cases.
# =============================================================================

FILTER_CATALOG: list[dict[str, Any]] = [
    # -------------------------------------------------------------------------
    # Grayscale
    # -------------------------------------------------------------------------
    {"name": "grayscale", "params": {}},

    # -------------------------------------------------------------------------
    # Color Adjustment (color_adjust.py)
    # -------------------------------------------------------------------------
    {"name": "brightness", "params": {"amount": 0.3}},
    {"name": "contrast", "params": {"amount": 0.5}},
    {"name": "saturation", "params": {"amount": 0.5}},
    {"name": "gamma", "params": {"gamma_value": 2.2}},
    {"name": "exposure", "params": {"exposure_val": 1.0, "offset": 0.0, "gamma_val": 1.0}},
    {"name": "invert", "params": {}},

    # -------------------------------------------------------------------------
    # Color Science (color_science.py)
    # -------------------------------------------------------------------------
    {"name": "hue_shift", "params": {"degrees": 90.0}},
    {"name": "vibrance", "params": {"amount": 0.5}},
    {
        "name": "color_balance",
        "params": {
            "shadows": [0.1, 0.0, -0.1],
            "midtones": [0.0, 0.0, 0.0],
            "highlights": [-0.1, 0.0, 0.1],
        },
    },

    # -------------------------------------------------------------------------
    # Stylize (stylize.py)
    # -------------------------------------------------------------------------
    {"name": "posterize", "params": {"levels": 4}},
    {"name": "solarize", "params": {"threshold": 128}},  # u8: 128, f32: 0.5
    {"name": "threshold", "params": {"threshold_val": 128}},  # u8: 128, f32: 0.5
    {"name": "emboss", "params": {"angle": 135.0, "depth": 1.0}},

    # -------------------------------------------------------------------------
    # Levels & Curves (levels_curves.py)
    # -------------------------------------------------------------------------
    {
        "name": "levels",
        "params": {
            "in_black": 20,
            "in_white": 235,
            "out_black": 0,
            "out_white": 255,
            "gamma": 1.0,
        },
    },
    {
        "name": "curves",
        "params": {"points": [(0.0, 0.0), (0.25, 0.35), (0.75, 0.65), (1.0, 1.0)]},
    },
    {"name": "auto_levels", "params": {"clip_percent": 0.01}},

    # -------------------------------------------------------------------------
    # Sharpen & Blur (sharpen_filters.py)
    # -------------------------------------------------------------------------
    {"name": "sharpen", "params": {"amount": 1.0}},
    {"name": "unsharp_mask", "params": {"amount": 1.0, "radius": 2.0, "threshold": 0}},
    {"name": "high_pass", "params": {"radius": 3.0}},
    {"name": "motion_blur", "params": {"angle": 45.0, "distance": 10.0}},

    # -------------------------------------------------------------------------
    # Edge Detection (edge_detect.py)
    # -------------------------------------------------------------------------
    {"name": "sobel", "params": {"direction": "both"}},
    {"name": "laplacian", "params": {"kernel_size": 3}},
    {"name": "find_edges", "params": {}},

    # -------------------------------------------------------------------------
    # Noise
    # -------------------------------------------------------------------------
    {"name": "add_noise", "params": {"amount": 0.1, "gaussian": True, "monochrome": False, "seed": 42}},
    {"name": "median", "params": {"radius": 2}},
    {"name": "denoise", "params": {"strength": 0.5}},

    # -------------------------------------------------------------------------
    # Morphology
    # -------------------------------------------------------------------------
    {"name": "dilate", "params": {"radius": 2.0}},
    {"name": "erode", "params": {"radius": 2.0}},
]


def _get_f32_params(params: dict[str, Any], filter_name: str) -> dict[str, Any]:
    """Convert u8 params to f32 equivalents where needed."""
    f32_params = params.copy()

    # Threshold values need conversion from 0-255 to 0.0-1.0
    if filter_name == "solarize" and "threshold" in f32_params:
        f32_params["threshold"] = f32_params["threshold"] / 255.0
    if filter_name == "threshold" and "threshold_val" in f32_params:
        f32_params["threshold_val"] = f32_params["threshold_val"] / 255.0
    if filter_name == "unsharp_mask" and "threshold" in f32_params:
        f32_params["threshold"] = f32_params["threshold"] / 255.0

    # Levels params need conversion
    if filter_name == "levels":
        for key in ["in_black", "in_white", "out_black", "out_white"]:
            if key in f32_params:
                f32_params[key] = f32_params[key] / 255.0

    return f32_params


def register_all_filters() -> dict[str, bool]:
    """Register all filters from the catalog for parity testing.

    Returns:
        Dict mapping filter names to registration success (True/False)
    """
    from imagestag.filters.grayscale import (
        grayscale, grayscale_f32,
        convert_u8_to_f32, convert_f32_to_12bit,
    )

    results = {}

    # Import filter modules - may fail if not all are implemented
    filter_modules = {}
    try:
        from imagestag.filters import color_adjust
        filter_modules["color_adjust"] = color_adjust
    except ImportError:
        pass

    try:
        from imagestag.filters import color_science
        filter_modules["color_science"] = color_science
    except ImportError:
        pass

    try:
        from imagestag.filters import stylize
        filter_modules["stylize"] = stylize
    except ImportError:
        pass

    try:
        from imagestag.filters import levels_curves
        filter_modules["levels_curves"] = levels_curves
    except ImportError:
        pass

    try:
        from imagestag.filters import sharpen_filters
        filter_modules["sharpen_filters"] = sharpen_filters
    except ImportError:
        pass

    try:
        from imagestag.filters import edge_detect
        filter_modules["edge_detect"] = edge_detect
    except ImportError:
        pass

    try:
        from imagestag.filters import noise_filters
        filter_modules["noise_filters"] = noise_filters
    except ImportError:
        pass

    try:
        from imagestag.filters import morphology_filters
        filter_modules["morphology_filters"] = morphology_filters
    except ImportError:
        pass

    # Map filter names to their module and function
    filter_funcs: dict[str, tuple[FilterFunc, FilterFunc | None]] = {
        # (u8_func, f32_func or None)
        "grayscale": (grayscale, grayscale_f32),
    }

    # Add color_adjust filters
    if "color_adjust" in filter_modules:
        m = filter_modules["color_adjust"]
        filter_funcs.update({
            "brightness": (m.brightness, m.brightness_f32),
            "contrast": (m.contrast, m.contrast_f32),
            "saturation": (m.saturation, m.saturation_f32),
            "gamma": (m.gamma, m.gamma_f32),
            "exposure": (m.exposure, m.exposure_f32),
            "invert": (m.invert, m.invert_f32),
        })

    # Add color_science filters
    if "color_science" in filter_modules:
        m = filter_modules["color_science"]
        filter_funcs.update({
            "hue_shift": (m.hue_shift, m.hue_shift_f32),
            "vibrance": (m.vibrance, m.vibrance_f32),
            "color_balance": (m.color_balance, m.color_balance_f32),
        })

    # Add stylize filters
    if "stylize" in filter_modules:
        m = filter_modules["stylize"]
        filter_funcs.update({
            "posterize": (m.posterize, m.posterize_f32),
            "solarize": (m.solarize, m.solarize_f32),
            "threshold": (m.threshold, m.threshold_f32),
            "emboss": (m.emboss, m.emboss_f32),
        })

    # Add levels_curves filters
    if "levels_curves" in filter_modules:
        m = filter_modules["levels_curves"]
        filter_funcs.update({
            "levels": (m.levels, m.levels_f32),
            "curves": (m.curves, m.curves_f32),
            "auto_levels": (m.auto_levels, m.auto_levels_f32),
        })

    # Add sharpen filters
    if "sharpen_filters" in filter_modules:
        m = filter_modules["sharpen_filters"]
        filter_funcs.update({
            "sharpen": (m.sharpen, m.sharpen_f32),
            "unsharp_mask": (m.unsharp_mask, m.unsharp_mask_f32),
            "high_pass": (m.high_pass, m.high_pass_f32),
            "motion_blur": (m.motion_blur, m.motion_blur_f32),
        })

    # Add edge detection filters
    if "edge_detect" in filter_modules:
        m = filter_modules["edge_detect"]
        filter_funcs.update({
            "sobel": (m.sobel, m.sobel_f32),
            "laplacian": (m.laplacian, m.laplacian_f32),
            "find_edges": (m.find_edges, m.find_edges_f32),
        })

    # Add noise filters
    if "noise_filters" in filter_modules:
        m = filter_modules["noise_filters"]
        filter_funcs.update({
            "add_noise": (m.add_noise, m.add_noise_f32),
            "median": (m.median, m.median_f32),
            "denoise": (m.denoise, m.denoise_f32),
        })

    # Add morphology filters
    if "morphology_filters" in filter_modules:
        m = filter_modules["morphology_filters"]
        filter_funcs.update({
            "dilate": (m.dilate, m.dilate_f32),
            "erode": (m.erode, m.erode_f32),
        })

    # Register each filter from the catalog
    for entry in FILTER_CATALOG:
        name = entry["name"]
        params = entry.get("params", {})
        inputs = entry.get("inputs", DEFAULT_INPUT_NAMES)  # Both deer and astronaut by default
        skip_f32 = entry.get("skip_f32", False)

        if name not in filter_funcs:
            results[name] = False
            continue

        u8_func, f32_func = filter_funcs[name]

        # Register u8 test cases (one per input)
        u8_test_cases = [
            TestCase(
                id=input_name,
                description=f"{name} filter - {input_name}",
                width=TEST_WIDTH,
                height=TEST_HEIGHT,
                input_generator=input_name,
                bit_depth="u8",
                params=params,
            )
            for input_name in inputs
        ]
        register_filter_parity(name, u8_test_cases)

        # Create wrapper that applies params
        def make_u8_impl(func, p):
            return lambda img, **kw: func(img, **{**p, **kw})

        register_filter_impl(name, make_u8_impl(u8_func, params))
        results[name] = True

        # Register f32 test cases if available (one per input)
        if not skip_f32 and f32_func is not None:
            f32_name = f"{name}_f32"
            f32_params = _get_f32_params(params, name)

            f32_test_cases = [
                TestCase(
                    id=f"{input_name}_f32",
                    description=f"{name} filter - {input_name} (f32)",
                    width=TEST_WIDTH,
                    height=TEST_HEIGHT,
                    input_generator=input_name,
                    bit_depth="f32",
                    params=f32_params,
                )
                for input_name in inputs
            ]
            register_filter_parity(f32_name, f32_test_cases)

            # f32 pipeline: u8 input -> f32 -> process -> 12-bit output
            def make_f32_impl(func, p):
                def impl(img, **kw):
                    img_f32 = convert_u8_to_f32(img)
                    result = func(img_f32, **{**p, **kw})
                    return convert_f32_to_12bit(result)
                return impl

            register_filter_impl(f32_name, make_f32_impl(f32_func, f32_params))
            results[f32_name] = True

    return results


def get_catalog_summary() -> str:
    """Get a summary of the filter catalog for documentation."""
    lines = [
        "# Cross-Platform Filter Catalog",
        "",
        f"Total filters: {len(FILTER_CATALOG)}",
        "",
        "| Filter | Parameters | Input |",
        "|--------|-----------|-------|",
    ]

    for entry in FILTER_CATALOG:
        name = entry["name"]
        params = entry.get("params", {})
        input_gen = entry.get("input", "deer_128")
        param_str = ", ".join(f"{k}={v}" for k, v in params.items()) or "(none)"
        lines.append(f"| {name} | {param_str} | {input_gen} |")

    return "\n".join(lines)


__all__ = [
    "FILTER_CATALOG",
    "register_all_filters",
    "get_catalog_summary",
]
