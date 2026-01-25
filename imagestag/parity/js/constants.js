/**
 * Constants for cross-platform parity testing.
 *
 * This module mirrors the Python constants.py and defines test resolution,
 * channel configurations, and other constants used by JavaScript parity tests.
 */

// =============================================================================
// Test Resolution
// =============================================================================

// Standard test image dimensions
export const TEST_WIDTH = 400;
export const TEST_HEIGHT = 400;

// =============================================================================
// Test Inputs
// =============================================================================

// Default test inputs - used for ALL filters unless overridden
// Each input has a defined channel count for consistency
export const TEST_INPUTS = {
    deer: {
        name: 'deer',
        description: 'Noto emoji deer - colorful vector WITH TRANSPARENCY',
        channels: 4, // RGBA - has alpha holes
        width: TEST_WIDTH,
        height: TEST_HEIGHT,
    },
    astronaut: {
        name: 'astronaut',
        description: 'Skimage astronaut - photographic, SOLID (no transparency)',
        channels: 3, // RGB - no alpha channel
        width: TEST_WIDTH,
        height: TEST_HEIGHT,
    },
};

// List of input names for iteration
export const DEFAULT_INPUT_NAMES = ['deer', 'astronaut'];

// =============================================================================
// Comparison Tolerances
// =============================================================================

// Maximum allowed difference between u8 and f32 outputs (after normalization)
// This is the max absolute difference in the 0.0-1.0 range
export const DEFAULT_TOLERANCE = 0.001;

// For filters known to have precision differences, use a higher tolerance
export const RELAXED_TOLERANCE = 0.01;

// =============================================================================
// Bit Depths
// =============================================================================

export const BIT_DEPTH_U8 = 'u8';
export const BIT_DEPTH_F32 = 'f32';
