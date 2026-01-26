"""Centralized layer effect catalog for parity testing.

This module defines cross-platform layer effects with their default test parameters.
Tests are automatically generated for each effect.

## Adding a New Effect

1. Add an entry to LAYER_EFFECT_CATALOG with:
   - name: Effect name (matches Python class name in snake_case)
   - params: Default parameters for testing
   - inputs: List of input names (optional, defaults to ["deer"])
   - skip_f32: Set True if no f32 variant exists

2. Register the Python implementation in register_all_effects()

## Layer Effect Catalog Schema

```python
{
    "name": "satin",              # Effect name
    "params": {"opacity": 0.5},   # Test parameters
    "inputs": ["deer"],           # Optional, default is deer only (needs alpha)
    "skip_f32": False,            # Skip f32 test (optional, defaults to False)
}
```

## Test Inputs

Layer effects typically need transparency, so we default to just "deer":
- deer: Noto emoji deer - colorful vector WITH TRANSPARENCY (4 channels RGBA)
"""
from typing import Any, Callable
import numpy as np

from .constants import TEST_WIDTH, TEST_HEIGHT, DEFAULT_TOLERANCE
from .registry import register_effect_parity, TestCase
from .runner import register_effect_impl

# Type alias for effect apply functions
EffectApplyFunc = Callable[..., np.ndarray]


# =============================================================================
# LAYER EFFECT CATALOG - Cross-platform layer effects with test parameters
#
# Layer effects work with alpha channel, so deer (with transparency) is the
# primary test input. Effects are tested through their Python wrapper classes.
# =============================================================================

LAYER_EFFECT_CATALOG: list[dict[str, Any]] = [
    # -------------------------------------------------------------------------
    # Drop Shadow
    # -------------------------------------------------------------------------
    {
        "name": "drop_shadow",
        "params": {
            "offset_x": 4.0,
            "offset_y": 4.0,
            "blur": 5.0,  # Python wrapper uses 'blur' not 'blur_radius'
            "color": (0, 0, 0),
            "opacity": 0.75,
        },
    },

    # -------------------------------------------------------------------------
    # Inner Shadow
    # -------------------------------------------------------------------------
    {
        "name": "inner_shadow",
        "params": {
            "offset_x": 2.0,
            "offset_y": 2.0,
            "blur": 5.0,  # Python wrapper uses 'blur' not 'blur_radius'
            "choke": 0.0,
            "color": (0, 0, 0),
            "opacity": 0.75,
        },
    },

    # -------------------------------------------------------------------------
    # Outer Glow
    # -------------------------------------------------------------------------
    {
        "name": "outer_glow",
        "params": {
            "radius": 10.0,
            "color": (255, 255, 0),
            "opacity": 0.75,
            "spread": 0.0,
        },
    },

    # -------------------------------------------------------------------------
    # Inner Glow
    # -------------------------------------------------------------------------
    {
        "name": "inner_glow",
        "params": {
            "radius": 10.0,
            "color": (255, 255, 0),
            "opacity": 0.75,
            "choke": 0.0,
        },
    },

    # -------------------------------------------------------------------------
    # Bevel & Emboss
    # -------------------------------------------------------------------------
    {
        "name": "bevel_emboss",
        "params": {
            "depth": 3.0,
            "angle": 120.0,
            "altitude": 30.0,
            "highlight_color": (255, 255, 255),
            "highlight_opacity": 0.75,
            "shadow_color": (0, 0, 0),
            "shadow_opacity": 0.75,
            "style": "inner_bevel",
        },
    },

    # -------------------------------------------------------------------------
    # Satin
    # -------------------------------------------------------------------------
    {
        "name": "satin",
        "params": {
            "color": (0, 0, 0),
            "opacity": 0.5,
            "angle": 19.0,
            "distance": 11.0,
            "size": 14.0,
            "invert": False,
        },
    },

    # -------------------------------------------------------------------------
    # Color Overlay
    # -------------------------------------------------------------------------
    {
        "name": "color_overlay",
        "params": {
            "color": (255, 0, 0),
            "opacity": 1.0,
        },
    },

    # -------------------------------------------------------------------------
    # Gradient Overlay
    # -------------------------------------------------------------------------
    {
        "name": "gradient_overlay",
        "params": {
            "gradient": [
                (0.0, 255, 0, 0),    # Red at start
                (0.5, 255, 255, 0),  # Yellow at middle
                (1.0, 0, 0, 255),    # Blue at end
            ],
            "style": "linear",
            "angle": 90.0,
            "scale": 1.0,
            "reverse": False,
            "opacity": 1.0,
        },
    },

    # -------------------------------------------------------------------------
    # Pattern Overlay (simple checkerboard pattern)
    # -------------------------------------------------------------------------
    {
        "name": "pattern_overlay",
        "params": {
            "pattern": None,  # Will use default checkerboard
            "scale": 4.0,
            "offset_x": 0,
            "offset_y": 0,
            "opacity": 0.8,
        },
    },

    # -------------------------------------------------------------------------
    # Stroke
    # -------------------------------------------------------------------------
    {
        "name": "stroke",
        "params": {
            "width": 3.0,
            "color": (255, 0, 0),  # Red for visibility
            "opacity": 1.0,
            "position": "outside",
        },
    },
]


def register_all_effects() -> dict[str, bool]:
    """Register all layer effects from the catalog for parity testing.

    Returns:
        Dict mapping effect names to registration success (True/False)
    """
    from imagestag.filters.grayscale import (
        convert_u8_to_f32, convert_f32_to_12bit,
    )

    results = {}

    # Import layer effects module
    try:
        from imagestag.layer_effects import (
            DropShadow,
            InnerShadow,
            OuterGlow,
            InnerGlow,
            BevelEmboss,
            Satin,
            ColorOverlay,
            GradientOverlay,
            PatternOverlay,
            Stroke,
        )
        effects_available = True
    except ImportError:
        effects_available = False
        results["import_error"] = False
        return results

    # Map effect names to their classes
    effect_classes: dict[str, type] = {
        "drop_shadow": DropShadow,
        "inner_shadow": InnerShadow,
        "outer_glow": OuterGlow,
        "inner_glow": InnerGlow,
        "bevel_emboss": BevelEmboss,
        "satin": Satin,
        "color_overlay": ColorOverlay,
        "gradient_overlay": GradientOverlay,
        "pattern_overlay": PatternOverlay,
        "stroke": Stroke,
    }

    # Register each effect from the catalog
    for entry in LAYER_EFFECT_CATALOG:
        name = entry["name"]
        params = entry.get("params", {})
        inputs = entry.get("inputs", ["deer"])  # Default to deer (needs alpha)
        skip_f32 = entry.get("skip_f32", False)

        if name not in effect_classes:
            results[name] = False
            continue

        effect_class = effect_classes[name]

        # Register u8 test cases
        u8_test_cases = [
            TestCase(
                id=input_name,
                description=f"{name} effect - {input_name}",
                width=TEST_WIDTH,
                height=TEST_HEIGHT,
                input_generator=input_name,
                bit_depth="u8",
                params=params,
            )
            for input_name in inputs
        ]
        register_effect_parity(name, u8_test_cases)

        # Create wrapper that applies effect with params
        def make_u8_impl(cls, p):
            def impl(img):
                # Create effect instance with params
                effect = cls(**p)
                result = effect.apply(img)
                return result.image
            return impl

        register_effect_impl(name, make_u8_impl(effect_class, params))
        results[name] = True

        # Register f32 test cases if not skipped
        if not skip_f32:
            f32_name = f"{name}_f32"

            f32_test_cases = [
                TestCase(
                    id=f"{input_name}_f32",
                    description=f"{name} effect - {input_name} (f32)",
                    width=TEST_WIDTH,
                    height=TEST_HEIGHT,
                    input_generator=input_name,
                    bit_depth="f32",
                    params=params,
                )
                for input_name in inputs
            ]
            register_effect_parity(f32_name, f32_test_cases)

            # f32 pipeline: u8 input -> f32 -> process -> 12-bit output
            def make_f32_impl(cls, p):
                def impl(img):
                    img_f32 = convert_u8_to_f32(img)
                    effect = cls(**p)
                    result = effect.apply(img_f32)
                    return convert_f32_to_12bit(result.image)
                return impl

            register_effect_impl(f32_name, make_f32_impl(effect_class, params))
            results[f32_name] = True

    return results


def get_catalog_summary() -> str:
    """Get a summary of the layer effect catalog for documentation."""
    lines = [
        "# Cross-Platform Layer Effect Catalog",
        "",
        f"Total effects: {len(LAYER_EFFECT_CATALOG)}",
        "",
        "| Effect | Parameters |",
        "|--------|-----------|",
    ]

    for entry in LAYER_EFFECT_CATALOG:
        name = entry["name"]
        params = entry.get("params", {})
        # Summarize params (skip pattern arrays)
        param_items = []
        for k, v in params.items():
            if k == "pattern":
                param_items.append(f"{k}=<array>")
            elif k == "gradient":
                param_items.append(f"{k}=<stops>")
            else:
                param_items.append(f"{k}={v}")
        param_str = ", ".join(param_items) or "(none)"
        lines.append(f"| {name} | {param_str} |")

    return "\n".join(lines)


__all__ = [
    "LAYER_EFFECT_CATALOG",
    "register_all_effects",
    "get_catalog_summary",
]
