"""Constants for cross-platform parity testing.

This module defines test resolution, channel configurations, and other
constants used by both Python and JavaScript parity tests.
"""

# =============================================================================
# Test Resolution
# =============================================================================

# Standard test image dimensions
TEST_WIDTH = 400
TEST_HEIGHT = 400

# =============================================================================
# Test Inputs
# =============================================================================

# Default test inputs - used for ALL filters unless overridden
# Each input has a defined channel count for consistency
TEST_INPUTS = {
    "deer": {
        "name": "deer",
        "description": "Noto emoji deer - colorful vector WITH TRANSPARENCY",
        "channels": 4,  # RGBA - has alpha holes
        "width": TEST_WIDTH,
        "height": TEST_HEIGHT,
    },
    "astronaut": {
        "name": "astronaut",
        "description": "Skimage astronaut - photographic, SOLID (no transparency)",
        "channels": 3,  # RGB - no alpha channel
        "width": TEST_WIDTH,
        "height": TEST_HEIGHT,
    },
}

# List of input names for iteration
DEFAULT_INPUT_NAMES = ["deer", "astronaut"]

# =============================================================================
# Comparison Tolerances
# =============================================================================

# Maximum allowed difference between u8 and f32 outputs (after normalization)
# This is the max absolute difference in the 0.0-1.0 range
DEFAULT_TOLERANCE = 0.001

# For filters known to have precision differences, use a higher tolerance
RELAXED_TOLERANCE = 0.01

# =============================================================================
# Bit Depths
# =============================================================================

BIT_DEPTH_U8 = "u8"
BIT_DEPTH_F32 = "f32"

__all__ = [
    "TEST_WIDTH",
    "TEST_HEIGHT",
    "TEST_INPUTS",
    "DEFAULT_INPUT_NAMES",
    "DEFAULT_TOLERANCE",
    "RELAXED_TOLERANCE",
    "BIT_DEPTH_U8",
    "BIT_DEPTH_F32",
]
