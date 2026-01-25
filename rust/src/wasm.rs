//! WebAssembly exports for ImageStag filters.
//!
//! These functions are exposed to JavaScript via wasm-bindgen.
//!
//! ## Bit Depth Support
//!
//! All filters have two versions:
//! - **u8**: 8-bit per channel (0-255), standard for web/display
//! - **f32**: Float per channel (0.0-1.0), for HDR/linear workflows
//!
//! Both versions use identical Rust implementations.

use wasm_bindgen::prelude::*;
use ndarray::Array3;

use crate::filters::grayscale::{
    grayscale_rgba_u8, grayscale_rgba_f32,
    u8_to_f32, f32_to_u8, f32_to_u16_12bit, u16_12bit_to_f32,
};

// ============================================================================
// Grayscale Filter - u8 (8-bit)
// ============================================================================

/// Convert RGBA u8 image to grayscale using BT.709 luminosity.
///
/// # Arguments
/// * `data` - Flat array of RGBA bytes (length = width * height * 4)
/// * `width` - Image width in pixels
/// * `height` - Image height in pixels
///
/// # Returns
/// Flat array of RGBA bytes with grayscale values
#[wasm_bindgen]
pub fn grayscale_rgba_wasm(
    data: &[u8],
    width: usize,
    height: usize,
) -> Vec<u8> {
    let input = Array3::from_shape_vec(
        (height, width, 4),
        data.to_vec()
    ).expect("Invalid dimensions");

    let result = grayscale_rgba_u8(input.view());
    result.into_raw_vec_and_offset().0
}

// ============================================================================
// Grayscale Filter - f32 (float)
// ============================================================================

/// Convert RGBA f32 image to grayscale using BT.709 luminosity.
///
/// # Arguments
/// * `data` - Flat array of RGBA floats (length = width * height * 4), values 0.0-1.0
/// * `width` - Image width in pixels
/// * `height` - Image height in pixels
///
/// # Returns
/// Flat array of RGBA floats with grayscale values
#[wasm_bindgen]
pub fn grayscale_rgba_f32_wasm(
    data: &[f32],
    width: usize,
    height: usize,
) -> Vec<f32> {
    let input = Array3::from_shape_vec(
        (height, width, 4),
        data.to_vec()
    ).expect("Invalid dimensions");

    let result = grayscale_rgba_f32(input.view());
    result.into_raw_vec_and_offset().0
}

// ============================================================================
// Conversion Utilities
// ============================================================================

/// Convert u8 image (0-255) to f32 (0.0-1.0)
#[wasm_bindgen]
pub fn convert_u8_to_f32_wasm(
    data: &[u8],
    width: usize,
    height: usize,
) -> Vec<f32> {
    let input = Array3::from_shape_vec(
        (height, width, 4),
        data.to_vec()
    ).expect("Invalid dimensions");

    let result = u8_to_f32(input.view());
    result.into_raw_vec_and_offset().0
}

/// Convert f32 image (0.0-1.0) to u8 (0-255)
#[wasm_bindgen]
pub fn convert_f32_to_u8_wasm(
    data: &[f32],
    width: usize,
    height: usize,
) -> Vec<u8> {
    let input = Array3::from_shape_vec(
        (height, width, 4),
        data.to_vec()
    ).expect("Invalid dimensions");

    let result = f32_to_u8(input.view());
    result.into_raw_vec_and_offset().0
}

/// Convert f32 image (0.0-1.0) to u16 12-bit (0-4095)
#[wasm_bindgen]
pub fn convert_f32_to_12bit_wasm(
    data: &[f32],
    width: usize,
    height: usize,
) -> Vec<u16> {
    let input = Array3::from_shape_vec(
        (height, width, 4),
        data.to_vec()
    ).expect("Invalid dimensions");

    let result = f32_to_u16_12bit(input.view());
    result.into_raw_vec_and_offset().0
}

/// Convert u16 12-bit (0-4095) to f32 (0.0-1.0)
#[wasm_bindgen]
pub fn convert_12bit_to_f32_wasm(
    data: &[u16],
    width: usize,
    height: usize,
) -> Vec<f32> {
    let input = Array3::from_shape_vec(
        (height, width, 4),
        data.to_vec()
    ).expect("Invalid dimensions");

    let result = u16_12bit_to_f32(input.view());
    result.into_raw_vec_and_offset().0
}
