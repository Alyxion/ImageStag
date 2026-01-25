//! WebAssembly exports for ImageStag filters.
//!
//! These functions are exposed to JavaScript via wasm-bindgen.
//!
//! ## Channel Support
//!
//! All filters accept images with 1, 3, or 4 channels:
//! - **Grayscale**: channels=1, data length = width * height
//! - **RGB**: channels=3, data length = width * height * 3
//! - **RGBA**: channels=4, data length = width * height * 4
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
use crate::filters::color_adjust;
use crate::filters::color_science;
use crate::filters::stylize;
use crate::filters::levels_curves;
use crate::filters::sharpen;
use crate::filters::edge;
use crate::filters::noise;
use crate::filters::morphology;

// ============================================================================
// Grayscale Filter - u8 (8-bit)
// ============================================================================

/// Convert image to grayscale using BT.709 luminosity.
///
/// # Arguments
/// * `data` - Flat array of bytes (length = width * height * channels)
/// * `width` - Image width in pixels
/// * `height` - Image height in pixels
/// * `channels` - Number of channels (1, 3, or 4)
///
/// # Returns
/// Flat array with grayscale values (same channel count)
#[wasm_bindgen]
pub fn grayscale_rgba_wasm(
    data: &[u8],
    width: usize,
    height: usize,
    channels: usize,
) -> Vec<u8> {
    let input = Array3::from_shape_vec(
        (height, width, channels),
        data.to_vec()
    ).expect("Invalid dimensions");

    let result = grayscale_rgba_u8(input.view());
    result.into_raw_vec_and_offset().0
}

// ============================================================================
// Grayscale Filter - f32 (float)
// ============================================================================

/// Convert image to grayscale using BT.709 luminosity.
///
/// # Arguments
/// * `data` - Flat array of floats (length = width * height * channels), values 0.0-1.0
/// * `width` - Image width in pixels
/// * `height` - Image height in pixels
/// * `channels` - Number of channels (1, 3, or 4)
///
/// # Returns
/// Flat array with grayscale values (same channel count)
#[wasm_bindgen]
pub fn grayscale_rgba_f32_wasm(
    data: &[f32],
    width: usize,
    height: usize,
    channels: usize,
) -> Vec<f32> {
    let input = Array3::from_shape_vec(
        (height, width, channels),
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
    channels: usize,
) -> Vec<f32> {
    let input = Array3::from_shape_vec(
        (height, width, channels),
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
    channels: usize,
) -> Vec<u8> {
    let input = Array3::from_shape_vec(
        (height, width, channels),
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
    channels: usize,
) -> Vec<u16> {
    let input = Array3::from_shape_vec(
        (height, width, channels),
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
    channels: usize,
) -> Vec<f32> {
    let input = Array3::from_shape_vec(
        (height, width, channels),
        data.to_vec()
    ).expect("Invalid dimensions");

    let result = u16_12bit_to_f32(input.view());
    result.into_raw_vec_and_offset().0
}

// ============================================================================
// Color Adjustment Filters
// ============================================================================

#[wasm_bindgen]
pub fn brightness_wasm(data: &[u8], width: usize, height: usize, channels: usize, amount: f32) -> Vec<u8> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = color_adjust::brightness_u8(input.view(), amount);
    result.into_raw_vec_and_offset().0
}

#[wasm_bindgen]
pub fn brightness_f32_wasm(data: &[f32], width: usize, height: usize, channels: usize, amount: f32) -> Vec<f32> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = color_adjust::brightness_f32(input.view(), amount);
    result.into_raw_vec_and_offset().0
}

#[wasm_bindgen]
pub fn contrast_wasm(data: &[u8], width: usize, height: usize, channels: usize, amount: f32) -> Vec<u8> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = color_adjust::contrast_u8(input.view(), amount);
    result.into_raw_vec_and_offset().0
}

#[wasm_bindgen]
pub fn contrast_f32_wasm(data: &[f32], width: usize, height: usize, channels: usize, amount: f32) -> Vec<f32> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = color_adjust::contrast_f32(input.view(), amount);
    result.into_raw_vec_and_offset().0
}

#[wasm_bindgen]
pub fn saturation_wasm(data: &[u8], width: usize, height: usize, channels: usize, amount: f32) -> Vec<u8> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = color_adjust::saturation_u8(input.view(), amount);
    result.into_raw_vec_and_offset().0
}

#[wasm_bindgen]
pub fn saturation_f32_wasm(data: &[f32], width: usize, height: usize, channels: usize, amount: f32) -> Vec<f32> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = color_adjust::saturation_f32(input.view(), amount);
    result.into_raw_vec_and_offset().0
}

#[wasm_bindgen]
pub fn gamma_wasm(data: &[u8], width: usize, height: usize, channels: usize, gamma_val: f32) -> Vec<u8> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = color_adjust::gamma_u8(input.view(), gamma_val);
    result.into_raw_vec_and_offset().0
}

#[wasm_bindgen]
pub fn gamma_f32_wasm(data: &[f32], width: usize, height: usize, channels: usize, gamma_val: f32) -> Vec<f32> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = color_adjust::gamma_f32(input.view(), gamma_val);
    result.into_raw_vec_and_offset().0
}

#[wasm_bindgen]
pub fn exposure_wasm(data: &[u8], width: usize, height: usize, channels: usize, exposure_val: f32, offset: f32, gamma_val: f32) -> Vec<u8> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = color_adjust::exposure_u8(input.view(), exposure_val, offset, gamma_val);
    result.into_raw_vec_and_offset().0
}

#[wasm_bindgen]
pub fn exposure_f32_wasm(data: &[f32], width: usize, height: usize, channels: usize, exposure_val: f32, offset: f32, gamma_val: f32) -> Vec<f32> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = color_adjust::exposure_f32(input.view(), exposure_val, offset, gamma_val);
    result.into_raw_vec_and_offset().0
}

#[wasm_bindgen]
pub fn invert_wasm(data: &[u8], width: usize, height: usize, channels: usize) -> Vec<u8> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = color_adjust::invert_u8(input.view());
    result.into_raw_vec_and_offset().0
}

#[wasm_bindgen]
pub fn invert_f32_wasm(data: &[f32], width: usize, height: usize, channels: usize) -> Vec<f32> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = color_adjust::invert_f32(input.view());
    result.into_raw_vec_and_offset().0
}

// ============================================================================
// Color Science Filters
// ============================================================================

#[wasm_bindgen]
pub fn hue_shift_wasm(data: &[u8], width: usize, height: usize, channels: usize, degrees: f32) -> Vec<u8> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = color_science::hue_shift_u8(input.view(), degrees);
    result.into_raw_vec_and_offset().0
}

#[wasm_bindgen]
pub fn hue_shift_f32_wasm(data: &[f32], width: usize, height: usize, channels: usize, degrees: f32) -> Vec<f32> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = color_science::hue_shift_f32(input.view(), degrees);
    result.into_raw_vec_and_offset().0
}

#[wasm_bindgen]
pub fn vibrance_wasm(data: &[u8], width: usize, height: usize, channels: usize, amount: f32) -> Vec<u8> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = color_science::vibrance_u8(input.view(), amount);
    result.into_raw_vec_and_offset().0
}

#[wasm_bindgen]
pub fn vibrance_f32_wasm(data: &[f32], width: usize, height: usize, channels: usize, amount: f32) -> Vec<f32> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = color_science::vibrance_f32(input.view(), amount);
    result.into_raw_vec_and_offset().0
}

#[wasm_bindgen]
pub fn color_balance_wasm(
    data: &[u8], width: usize, height: usize, channels: usize,
    shadow_r: f32, shadow_g: f32, shadow_b: f32,
    mid_r: f32, mid_g: f32, mid_b: f32,
    high_r: f32, high_g: f32, high_b: f32,
) -> Vec<u8> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = color_science::color_balance_u8(
        input.view(),
        [shadow_r, shadow_g, shadow_b],
        [mid_r, mid_g, mid_b],
        [high_r, high_g, high_b],
    );
    result.into_raw_vec_and_offset().0
}

#[wasm_bindgen]
pub fn color_balance_f32_wasm(
    data: &[f32], width: usize, height: usize, channels: usize,
    shadow_r: f32, shadow_g: f32, shadow_b: f32,
    mid_r: f32, mid_g: f32, mid_b: f32,
    high_r: f32, high_g: f32, high_b: f32,
) -> Vec<f32> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = color_science::color_balance_f32(
        input.view(),
        [shadow_r, shadow_g, shadow_b],
        [mid_r, mid_g, mid_b],
        [high_r, high_g, high_b],
    );
    result.into_raw_vec_and_offset().0
}

// ============================================================================
// Stylize Filters
// ============================================================================

#[wasm_bindgen]
pub fn posterize_wasm(data: &[u8], width: usize, height: usize, channels: usize, levels: u8) -> Vec<u8> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = stylize::posterize_u8(input.view(), levels);
    result.into_raw_vec_and_offset().0
}

#[wasm_bindgen]
pub fn posterize_f32_wasm(data: &[f32], width: usize, height: usize, channels: usize, levels: u8) -> Vec<f32> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = stylize::posterize_f32(input.view(), levels);
    result.into_raw_vec_and_offset().0
}

#[wasm_bindgen]
pub fn solarize_wasm(data: &[u8], width: usize, height: usize, channels: usize, threshold: u8) -> Vec<u8> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = stylize::solarize_u8(input.view(), threshold);
    result.into_raw_vec_and_offset().0
}

#[wasm_bindgen]
pub fn solarize_f32_wasm(data: &[f32], width: usize, height: usize, channels: usize, threshold: f32) -> Vec<f32> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = stylize::solarize_f32(input.view(), threshold);
    result.into_raw_vec_and_offset().0
}

#[wasm_bindgen]
pub fn threshold_wasm(data: &[u8], width: usize, height: usize, channels: usize, threshold_val: u8) -> Vec<u8> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = stylize::threshold_u8(input.view(), threshold_val);
    result.into_raw_vec_and_offset().0
}

#[wasm_bindgen]
pub fn threshold_f32_wasm(data: &[f32], width: usize, height: usize, channels: usize, threshold_val: f32) -> Vec<f32> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = stylize::threshold_f32(input.view(), threshold_val);
    result.into_raw_vec_and_offset().0
}

#[wasm_bindgen]
pub fn emboss_wasm(data: &[u8], width: usize, height: usize, channels: usize, angle: f32, depth: f32) -> Vec<u8> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = stylize::emboss_u8(input.view(), angle, depth);
    result.into_raw_vec_and_offset().0
}

#[wasm_bindgen]
pub fn emboss_f32_wasm(data: &[f32], width: usize, height: usize, channels: usize, angle: f32, depth: f32) -> Vec<f32> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = stylize::emboss_f32(input.view(), angle, depth);
    result.into_raw_vec_and_offset().0
}

// ============================================================================
// Levels & Curves Filters
// ============================================================================

#[wasm_bindgen]
pub fn levels_wasm(
    data: &[u8], width: usize, height: usize, channels: usize,
    in_black: u8, in_white: u8, out_black: u8, out_white: u8, gamma_val: f32,
) -> Vec<u8> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = levels_curves::levels_u8(input.view(), in_black, in_white, out_black, out_white, gamma_val);
    result.into_raw_vec_and_offset().0
}

#[wasm_bindgen]
pub fn levels_f32_wasm(
    data: &[f32], width: usize, height: usize, channels: usize,
    in_black: f32, in_white: f32, out_black: f32, out_white: f32, gamma_val: f32,
) -> Vec<f32> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = levels_curves::levels_f32(input.view(), in_black, in_white, out_black, out_white, gamma_val);
    result.into_raw_vec_and_offset().0
}

#[wasm_bindgen]
pub fn curves_wasm(data: &[u8], width: usize, height: usize, channels: usize, points_flat: &[f32]) -> Vec<u8> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    // Convert flat array to Vec<(f32, f32)>
    let points: Vec<(f32, f32)> = points_flat.chunks(2).map(|c| (c[0], c[1])).collect();
    let result = levels_curves::curves_u8(input.view(), &points);
    result.into_raw_vec_and_offset().0
}

#[wasm_bindgen]
pub fn curves_f32_wasm(data: &[f32], width: usize, height: usize, channels: usize, points_flat: &[f32]) -> Vec<f32> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let points: Vec<(f32, f32)> = points_flat.chunks(2).map(|c| (c[0], c[1])).collect();
    let result = levels_curves::curves_f32(input.view(), &points);
    result.into_raw_vec_and_offset().0
}

#[wasm_bindgen]
pub fn auto_levels_wasm(data: &[u8], width: usize, height: usize, channels: usize, clip_percent: f32) -> Vec<u8> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = levels_curves::auto_levels_u8(input.view(), clip_percent);
    result.into_raw_vec_and_offset().0
}

#[wasm_bindgen]
pub fn auto_levels_f32_wasm(data: &[f32], width: usize, height: usize, channels: usize, clip_percent: f32) -> Vec<f32> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = levels_curves::auto_levels_f32(input.view(), clip_percent);
    result.into_raw_vec_and_offset().0
}

// ============================================================================
// Sharpen Filters
// ============================================================================

#[wasm_bindgen]
pub fn sharpen_wasm(data: &[u8], width: usize, height: usize, channels: usize, amount: f32) -> Vec<u8> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = sharpen::sharpen_u8(input.view(), amount);
    result.into_raw_vec_and_offset().0
}

#[wasm_bindgen]
pub fn sharpen_f32_wasm(data: &[f32], width: usize, height: usize, channels: usize, amount: f32) -> Vec<f32> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = sharpen::sharpen_f32(input.view(), amount);
    result.into_raw_vec_and_offset().0
}

#[wasm_bindgen]
pub fn unsharp_mask_wasm(data: &[u8], width: usize, height: usize, channels: usize, amount: f32, radius: f32, threshold_val: u8) -> Vec<u8> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = sharpen::unsharp_mask_u8(input.view(), amount, radius, threshold_val);
    result.into_raw_vec_and_offset().0
}

#[wasm_bindgen]
pub fn unsharp_mask_f32_wasm(data: &[f32], width: usize, height: usize, channels: usize, amount: f32, radius: f32, threshold_val: f32) -> Vec<f32> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = sharpen::unsharp_mask_f32(input.view(), amount, radius, threshold_val);
    result.into_raw_vec_and_offset().0
}

#[wasm_bindgen]
pub fn high_pass_wasm(data: &[u8], width: usize, height: usize, channels: usize, radius: f32) -> Vec<u8> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = sharpen::high_pass_u8(input.view(), radius);
    result.into_raw_vec_and_offset().0
}

#[wasm_bindgen]
pub fn high_pass_f32_wasm(data: &[f32], width: usize, height: usize, channels: usize, radius: f32) -> Vec<f32> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = sharpen::high_pass_f32(input.view(), radius);
    result.into_raw_vec_and_offset().0
}

#[wasm_bindgen]
pub fn motion_blur_wasm(data: &[u8], width: usize, height: usize, channels: usize, angle: f32, distance: f32) -> Vec<u8> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = sharpen::motion_blur_u8(input.view(), angle, distance);
    result.into_raw_vec_and_offset().0
}

#[wasm_bindgen]
pub fn motion_blur_f32_wasm(data: &[f32], width: usize, height: usize, channels: usize, angle: f32, distance: f32) -> Vec<f32> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = sharpen::motion_blur_f32(input.view(), angle, distance);
    result.into_raw_vec_and_offset().0
}

// ============================================================================
// Edge Detection Filters
// ============================================================================

#[wasm_bindgen]
pub fn sobel_wasm(data: &[u8], width: usize, height: usize, channels: usize, direction: &str) -> Vec<u8> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = edge::sobel_u8(input.view(), direction);
    result.into_raw_vec_and_offset().0
}

#[wasm_bindgen]
pub fn sobel_f32_wasm(data: &[f32], width: usize, height: usize, channels: usize, direction: &str) -> Vec<f32> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = edge::sobel_f32(input.view(), direction);
    result.into_raw_vec_and_offset().0
}

#[wasm_bindgen]
pub fn laplacian_wasm(data: &[u8], width: usize, height: usize, channels: usize, kernel_size: u8) -> Vec<u8> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = edge::laplacian_u8(input.view(), kernel_size);
    result.into_raw_vec_and_offset().0
}

#[wasm_bindgen]
pub fn laplacian_f32_wasm(data: &[f32], width: usize, height: usize, channels: usize, kernel_size: u8) -> Vec<f32> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = edge::laplacian_f32(input.view(), kernel_size);
    result.into_raw_vec_and_offset().0
}

#[wasm_bindgen]
pub fn find_edges_wasm(data: &[u8], width: usize, height: usize, channels: usize) -> Vec<u8> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = edge::find_edges_u8(input.view());
    result.into_raw_vec_and_offset().0
}

#[wasm_bindgen]
pub fn find_edges_f32_wasm(data: &[f32], width: usize, height: usize, channels: usize) -> Vec<f32> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = edge::find_edges_f32(input.view());
    result.into_raw_vec_and_offset().0
}

// ============================================================================
// Noise Filters
// ============================================================================

#[wasm_bindgen]
pub fn add_noise_wasm(data: &[u8], width: usize, height: usize, channels: usize, amount: f32, gaussian: bool, monochrome: bool, seed: u32) -> Vec<u8> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = noise::add_noise_u8(input.view(), amount, gaussian, monochrome, seed as u64);
    result.into_raw_vec_and_offset().0
}

#[wasm_bindgen]
pub fn add_noise_f32_wasm(data: &[f32], width: usize, height: usize, channels: usize, amount: f32, gaussian: bool, monochrome: bool, seed: u32) -> Vec<f32> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = noise::add_noise_f32(input.view(), amount, gaussian, monochrome, seed as u64);
    result.into_raw_vec_and_offset().0
}

#[wasm_bindgen]
pub fn median_wasm(data: &[u8], width: usize, height: usize, channels: usize, radius: u32) -> Vec<u8> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = noise::median_u8(input.view(), radius);
    result.into_raw_vec_and_offset().0
}

#[wasm_bindgen]
pub fn median_f32_wasm(data: &[f32], width: usize, height: usize, channels: usize, radius: u32) -> Vec<f32> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = noise::median_f32(input.view(), radius);
    result.into_raw_vec_and_offset().0
}

#[wasm_bindgen]
pub fn denoise_wasm(data: &[u8], width: usize, height: usize, channels: usize, strength: f32) -> Vec<u8> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = noise::denoise_u8(input.view(), strength);
    result.into_raw_vec_and_offset().0
}

#[wasm_bindgen]
pub fn denoise_f32_wasm(data: &[f32], width: usize, height: usize, channels: usize, strength: f32) -> Vec<f32> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = noise::denoise_f32(input.view(), strength);
    result.into_raw_vec_and_offset().0
}

// ============================================================================
// Morphology Filters
// ============================================================================

#[wasm_bindgen]
pub fn dilate_wasm(data: &[u8], width: usize, height: usize, channels: usize, radius: f32) -> Vec<u8> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = morphology::dilate_u8(input.view(), radius);
    result.into_raw_vec_and_offset().0
}

#[wasm_bindgen]
pub fn dilate_f32_wasm(data: &[f32], width: usize, height: usize, channels: usize, radius: f32) -> Vec<f32> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = morphology::dilate_f32(input.view(), radius);
    result.into_raw_vec_and_offset().0
}

#[wasm_bindgen]
pub fn erode_wasm(data: &[u8], width: usize, height: usize, channels: usize, radius: f32) -> Vec<u8> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = morphology::erode_u8(input.view(), radius);
    result.into_raw_vec_and_offset().0
}

#[wasm_bindgen]
pub fn erode_f32_wasm(data: &[f32], width: usize, height: usize, channels: usize, radius: f32) -> Vec<f32> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = morphology::erode_f32(input.view(), radius);
    result.into_raw_vec_and_offset().0
}
