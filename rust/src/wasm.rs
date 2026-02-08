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
use crate::filters::blur_wasm;
use crate::filters::rotate;
use crate::filters::core::{blur_alpha_f32, dilate_alpha, erode_alpha, expand_canvas_f32};

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
// New Color Science Filters (Sepia, Temperature, Channel Mixer)
// ============================================================================

#[wasm_bindgen]
pub fn sepia_wasm(data: &[u8], width: usize, height: usize, channels: usize, intensity: f32) -> Vec<u8> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = color_science::sepia_u8(input.view(), intensity);
    result.into_raw_vec_and_offset().0
}

#[wasm_bindgen]
pub fn sepia_f32_wasm(data: &[f32], width: usize, height: usize, channels: usize, intensity: f32) -> Vec<f32> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = color_science::sepia_f32(input.view(), intensity);
    result.into_raw_vec_and_offset().0
}

#[wasm_bindgen]
pub fn temperature_wasm(data: &[u8], width: usize, height: usize, channels: usize, amount: f32) -> Vec<u8> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = color_science::temperature_u8(input.view(), amount);
    result.into_raw_vec_and_offset().0
}

#[wasm_bindgen]
pub fn temperature_f32_wasm(data: &[f32], width: usize, height: usize, channels: usize, amount: f32) -> Vec<f32> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = color_science::temperature_f32(input.view(), amount);
    result.into_raw_vec_and_offset().0
}

#[wasm_bindgen]
pub fn channel_mixer_wasm(data: &[u8], width: usize, height: usize, channels: usize, r_src: u8, g_src: u8, b_src: u8) -> Vec<u8> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = color_science::channel_mixer_u8(input.view(), r_src, g_src, b_src);
    result.into_raw_vec_and_offset().0
}

#[wasm_bindgen]
pub fn channel_mixer_f32_wasm(data: &[f32], width: usize, height: usize, channels: usize, r_src: u8, g_src: u8, b_src: u8) -> Vec<f32> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = color_science::channel_mixer_f32(input.view(), r_src, g_src, b_src);
    result.into_raw_vec_and_offset().0
}

// ============================================================================
// Equalize Histogram
// ============================================================================

#[wasm_bindgen]
pub fn equalize_histogram_wasm(data: &[u8], width: usize, height: usize, channels: usize) -> Vec<u8> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = color_adjust::equalize_histogram_u8(input.view());
    result.into_raw_vec_and_offset().0
}

#[wasm_bindgen]
pub fn equalize_histogram_f32_wasm(data: &[f32], width: usize, height: usize, channels: usize) -> Vec<f32> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = color_adjust::equalize_histogram_f32(input.view());
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

#[wasm_bindgen]
pub fn pencil_sketch_wasm(data: &[u8], width: usize, height: usize, channels: usize, sigma_s: f32, shade_factor: f32) -> Vec<u8> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = stylize::pencil_sketch_u8(input.view(), sigma_s, shade_factor);
    result.into_raw_vec_and_offset().0
}

#[wasm_bindgen]
pub fn pencil_sketch_f32_wasm(data: &[f32], width: usize, height: usize, channels: usize, sigma_s: f32, shade_factor: f32) -> Vec<f32> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = stylize::pencil_sketch_f32(input.view(), sigma_s, shade_factor);
    result.into_raw_vec_and_offset().0
}

#[wasm_bindgen]
pub fn pixelate_wasm(data: &[u8], width: usize, height: usize, channels: usize, block_size: u32) -> Vec<u8> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = stylize::pixelate_u8(input.view(), block_size);
    result.into_raw_vec_and_offset().0
}

#[wasm_bindgen]
pub fn pixelate_f32_wasm(data: &[f32], width: usize, height: usize, channels: usize, block_size: u32) -> Vec<f32> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = stylize::pixelate_f32(input.view(), block_size);
    result.into_raw_vec_and_offset().0
}

#[wasm_bindgen]
pub fn vignette_wasm(data: &[u8], width: usize, height: usize, channels: usize, amount: f32) -> Vec<u8> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = stylize::vignette_u8(input.view(), amount);
    result.into_raw_vec_and_offset().0
}

#[wasm_bindgen]
pub fn vignette_f32_wasm(data: &[f32], width: usize, height: usize, channels: usize, amount: f32) -> Vec<f32> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = stylize::vignette_f32(input.view(), amount);
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
pub fn sobel_wasm(data: &[u8], width: usize, height: usize, channels: usize, direction: &str, kernel_size: u8) -> Vec<u8> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = edge::sobel_u8(input.view(), direction, kernel_size);
    result.into_raw_vec_and_offset().0
}

#[wasm_bindgen]
pub fn sobel_f32_wasm(data: &[f32], width: usize, height: usize, channels: usize, direction: &str, kernel_size: u8) -> Vec<f32> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = edge::sobel_f32(input.view(), direction, kernel_size);
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
pub fn find_edges_wasm(data: &[u8], width: usize, height: usize, channels: usize, sigma: f64, low_threshold: f64, high_threshold: f64) -> Vec<u8> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = edge::find_edges_u8(input.view(), sigma, low_threshold, high_threshold);
    result.into_raw_vec_and_offset().0
}

#[wasm_bindgen]
pub fn find_edges_f32_wasm(data: &[f32], width: usize, height: usize, channels: usize, sigma: f64, low_threshold: f64, high_threshold: f64) -> Vec<f32> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = edge::find_edges_f32(input.view(), sigma, low_threshold, high_threshold);
    result.into_raw_vec_and_offset().0
}

// ============================================================================
// Draw Contours
// ============================================================================

#[wasm_bindgen]
pub fn draw_contours_wasm(data: &[u8], width: usize, height: usize, channels: usize, threshold: u8, line_width: u8, color_r: u8, color_g: u8, color_b: u8) -> Vec<u8> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = edge::draw_contours_u8(input.view(), threshold, line_width, color_r, color_g, color_b);
    result.into_raw_vec_and_offset().0
}

#[wasm_bindgen]
pub fn draw_contours_f32_wasm(data: &[f32], width: usize, height: usize, channels: usize, threshold: f32, line_width: u8, color_r: f32, color_g: f32, color_b: f32) -> Vec<f32> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = edge::draw_contours_f32(input.view(), threshold, line_width, color_r, color_g, color_b);
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

#[wasm_bindgen]
pub fn morphology_open_wasm(data: &[u8], width: usize, height: usize, channels: usize, radius: f32) -> Vec<u8> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = morphology::open_u8(input.view(), radius);
    result.into_raw_vec_and_offset().0
}

#[wasm_bindgen]
pub fn morphology_open_f32_wasm(data: &[f32], width: usize, height: usize, channels: usize, radius: f32) -> Vec<f32> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = morphology::open_f32(input.view(), radius);
    result.into_raw_vec_and_offset().0
}

#[wasm_bindgen]
pub fn morphology_close_wasm(data: &[u8], width: usize, height: usize, channels: usize, radius: f32) -> Vec<u8> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = morphology::close_u8(input.view(), radius);
    result.into_raw_vec_and_offset().0
}

#[wasm_bindgen]
pub fn morphology_close_f32_wasm(data: &[f32], width: usize, height: usize, channels: usize, radius: f32) -> Vec<f32> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = morphology::close_f32(input.view(), radius);
    result.into_raw_vec_and_offset().0
}

#[wasm_bindgen]
pub fn morphology_gradient_wasm(data: &[u8], width: usize, height: usize, channels: usize, radius: f32) -> Vec<u8> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = morphology::gradient_u8(input.view(), radius);
    result.into_raw_vec_and_offset().0
}

#[wasm_bindgen]
pub fn morphology_gradient_f32_wasm(data: &[f32], width: usize, height: usize, channels: usize, radius: f32) -> Vec<f32> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = morphology::gradient_f32(input.view(), radius);
    result.into_raw_vec_and_offset().0
}

#[wasm_bindgen]
pub fn tophat_wasm(data: &[u8], width: usize, height: usize, channels: usize, radius: f32) -> Vec<u8> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = morphology::tophat_u8(input.view(), radius);
    result.into_raw_vec_and_offset().0
}

#[wasm_bindgen]
pub fn tophat_f32_wasm(data: &[f32], width: usize, height: usize, channels: usize, radius: f32) -> Vec<f32> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = morphology::tophat_f32(input.view(), radius);
    result.into_raw_vec_and_offset().0
}

#[wasm_bindgen]
pub fn blackhat_wasm(data: &[u8], width: usize, height: usize, channels: usize, radius: f32) -> Vec<u8> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = morphology::blackhat_u8(input.view(), radius);
    result.into_raw_vec_and_offset().0
}

#[wasm_bindgen]
pub fn blackhat_f32_wasm(data: &[f32], width: usize, height: usize, channels: usize, radius: f32) -> Vec<f32> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = morphology::blackhat_f32(input.view(), radius);
    result.into_raw_vec_and_offset().0
}

// ============================================================================
// WASM-compatible Blur (no rayon)
// ============================================================================

#[wasm_bindgen]
pub fn gaussian_blur_wasm(data: &[u8], width: usize, height: usize, channels: usize, sigma: f32) -> Vec<u8> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = blur_wasm::gaussian_blur_wasm_u8(input.view(), sigma);
    result.into_raw_vec_and_offset().0
}

#[wasm_bindgen]
pub fn gaussian_blur_f32_wasm(data: &[f32], width: usize, height: usize, channels: usize, sigma: f32) -> Vec<f32> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = blur_wasm::gaussian_blur_wasm_f32(input.view(), sigma);
    result.into_raw_vec_and_offset().0
}

#[wasm_bindgen]
pub fn box_blur_wasm(data: &[u8], width: usize, height: usize, channels: usize, radius: u32) -> Vec<u8> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = blur_wasm::box_blur_wasm_u8(input.view(), radius);
    result.into_raw_vec_and_offset().0
}

#[wasm_bindgen]
pub fn box_blur_f32_wasm(data: &[f32], width: usize, height: usize, channels: usize, radius: u32) -> Vec<f32> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = blur_wasm::box_blur_wasm_f32(input.view(), radius);
    result.into_raw_vec_and_offset().0
}

// ============================================================================
// Rotation and Mirroring
// ============================================================================

/// Rotate image 90 degrees clockwise (u8).
/// Returns flat array with dimensions swapped (W, H instead of H, W).
#[wasm_bindgen]
pub fn rotate_90_cw_wasm(data: &[u8], width: usize, height: usize, channels: usize) -> Vec<u8> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = rotate::rotate_90_cw_u8(input.view());
    result.into_raw_vec_and_offset().0
}

/// Rotate image 90 degrees clockwise (f32).
#[wasm_bindgen]
pub fn rotate_90_cw_f32_wasm(data: &[f32], width: usize, height: usize, channels: usize) -> Vec<f32> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = rotate::rotate_90_cw_f32(input.view());
    result.into_raw_vec_and_offset().0
}

/// Rotate image 180 degrees (u8).
#[wasm_bindgen]
pub fn rotate_180_wasm(data: &[u8], width: usize, height: usize, channels: usize) -> Vec<u8> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = rotate::rotate_180_u8(input.view());
    result.into_raw_vec_and_offset().0
}

/// Rotate image 180 degrees (f32).
#[wasm_bindgen]
pub fn rotate_180_f32_wasm(data: &[f32], width: usize, height: usize, channels: usize) -> Vec<f32> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = rotate::rotate_180_f32(input.view());
    result.into_raw_vec_and_offset().0
}

/// Rotate image 270 degrees clockwise (90 CCW) (u8).
/// Returns flat array with dimensions swapped (W, H instead of H, W).
#[wasm_bindgen]
pub fn rotate_270_cw_wasm(data: &[u8], width: usize, height: usize, channels: usize) -> Vec<u8> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = rotate::rotate_270_cw_u8(input.view());
    result.into_raw_vec_and_offset().0
}

/// Rotate image 270 degrees clockwise (90 CCW) (f32).
#[wasm_bindgen]
pub fn rotate_270_cw_f32_wasm(data: &[f32], width: usize, height: usize, channels: usize) -> Vec<f32> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = rotate::rotate_270_cw_f32(input.view());
    result.into_raw_vec_and_offset().0
}

/// Rotate image by specified degrees (90, 180, or 270) (u8).
/// For 90/270, dimensions are swapped in output.
#[wasm_bindgen]
pub fn rotate_wasm(data: &[u8], width: usize, height: usize, channels: usize, degrees: u32) -> Vec<u8> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = rotate::rotate_u8(input.view(), degrees);
    result.into_raw_vec_and_offset().0
}

/// Rotate image by specified degrees (90, 180, or 270) (f32).
#[wasm_bindgen]
pub fn rotate_f32_wasm(data: &[f32], width: usize, height: usize, channels: usize, degrees: u32) -> Vec<f32> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = rotate::rotate_f32(input.view(), degrees);
    result.into_raw_vec_and_offset().0
}

/// Flip image horizontally (mirror left-right) (u8).
#[wasm_bindgen]
pub fn flip_horizontal_wasm(data: &[u8], width: usize, height: usize, channels: usize) -> Vec<u8> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = rotate::flip_horizontal_u8(input.view());
    result.into_raw_vec_and_offset().0
}

/// Flip image horizontally (mirror left-right) (f32).
#[wasm_bindgen]
pub fn flip_horizontal_f32_wasm(data: &[f32], width: usize, height: usize, channels: usize) -> Vec<f32> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = rotate::flip_horizontal_f32(input.view());
    result.into_raw_vec_and_offset().0
}

/// Flip image vertically (mirror top-bottom) (u8).
#[wasm_bindgen]
pub fn flip_vertical_wasm(data: &[u8], width: usize, height: usize, channels: usize) -> Vec<u8> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = rotate::flip_vertical_u8(input.view());
    result.into_raw_vec_and_offset().0
}

/// Flip image vertically (mirror top-bottom) (f32).
#[wasm_bindgen]
pub fn flip_vertical_f32_wasm(data: &[f32], width: usize, height: usize, channels: usize) -> Vec<f32> {
    let input = Array3::from_shape_vec((height, width, channels), data.to_vec()).expect("Invalid dimensions");
    let result = rotate::flip_vertical_f32(input.view());
    result.into_raw_vec_and_offset().0
}

// ============================================================================
// Layer Effects: Satin
// ============================================================================

/// Apply satin effect to RGBA u8 image.
///
/// Creates silky interior shading by compositing shifted, blurred copies
/// of the alpha channel.
#[wasm_bindgen]
pub fn satin_rgba_wasm(
    data: &[u8],
    width: usize,
    height: usize,
    color_r: u8,
    color_g: u8,
    color_b: u8,
    opacity: f32,
    angle: f32,
    distance: f32,
    size: f32,
    invert: bool,
) -> Vec<u8> {
    use ndarray::Array2;

    let input = Array3::from_shape_vec((height, width, 4), data.to_vec()).expect("Invalid dimensions");

    // Convert to f32
    let mut input_f32 = Array3::<f32>::zeros((height, width, 4));
    for y in 0..height {
        for x in 0..width {
            input_f32[[y, x, 0]] = input[[y, x, 0]] as f32 / 255.0;
            input_f32[[y, x, 1]] = input[[y, x, 1]] as f32 / 255.0;
            input_f32[[y, x, 2]] = input[[y, x, 2]] as f32 / 255.0;
            input_f32[[y, x, 3]] = input[[y, x, 3]] as f32 / 255.0;
        }
    }

    // Extract alpha
    let mut alpha = Array2::<f32>::zeros((height, width));
    for y in 0..height {
        for x in 0..width {
            alpha[[y, x]] = input_f32[[y, x, 3]];
        }
    }

    // Calculate offset direction
    let angle_rad = angle.to_radians();
    let dx = (angle_rad.cos() * distance).round() as isize;
    let dy = (-angle_rad.sin() * distance).round() as isize;

    // Create offset copies
    let mut offset_a = Array2::<f32>::zeros((height, width));
    let mut offset_b = Array2::<f32>::zeros((height, width));
    for y in 0..height {
        for x in 0..width {
            let sx_a = (x as isize + dx).clamp(0, width as isize - 1) as usize;
            let sy_a = (y as isize + dy).clamp(0, height as isize - 1) as usize;
            offset_a[[y, x]] = alpha[[sy_a, sx_a]];

            let sx_b = (x as isize - dx).clamp(0, width as isize - 1) as usize;
            let sy_b = (y as isize - dy).clamp(0, height as isize - 1) as usize;
            offset_b[[y, x]] = alpha[[sy_b, sx_b]];
        }
    }

    // Blur both copies
    let blurred_a = blur_alpha_f32(&offset_a, size);
    let blurred_b = blur_alpha_f32(&offset_b, size);

    // Compute satin mask
    let mut satin_mask = Array2::<f32>::zeros((height, width));
    for y in 0..height {
        for x in 0..width {
            let diff = (blurred_a[[y, x]] - blurred_b[[y, x]]).abs();
            let mask_val = if invert { 1.0 - diff } else { diff };
            satin_mask[[y, x]] = mask_val * alpha[[y, x]];
        }
    }

    // Create result
    let mut result = input_f32.clone();
    let satin_r = color_r as f32 / 255.0;
    let satin_g = color_g as f32 / 255.0;
    let satin_b = color_b as f32 / 255.0;

    for y in 0..height {
        for x in 0..width {
            let orig_a = alpha[[y, x]];
            if orig_a <= 0.0 { continue; }

            let satin_a = satin_mask[[y, x]] * opacity;
            if satin_a > 0.0 {
                let out_a = satin_a + result[[y, x, 3]] * (1.0 - satin_a);
                if out_a > 0.0 {
                    result[[y, x, 0]] = (satin_r * satin_a + result[[y, x, 0]] * result[[y, x, 3]] * (1.0 - satin_a)) / out_a;
                    result[[y, x, 1]] = (satin_g * satin_a + result[[y, x, 1]] * result[[y, x, 3]] * (1.0 - satin_a)) / out_a;
                    result[[y, x, 2]] = (satin_b * satin_a + result[[y, x, 2]] * result[[y, x, 3]] * (1.0 - satin_a)) / out_a;
                    result[[y, x, 3]] = out_a;
                }
            }
        }
    }

    result.mapv(|v| (v.clamp(0.0, 1.0) * 255.0) as u8).into_raw_vec_and_offset().0
}

// ============================================================================
// Layer Effects: Gradient Overlay
// ============================================================================

/// Apply gradient overlay to RGBA u8 image.
///
/// Gradient stops are passed as flat array: [pos, r, g, b, pos, r, g, b, ...]
/// Style: "linear", "radial", "angle", "reflected", "diamond"
#[wasm_bindgen]
pub fn gradient_overlay_rgba_wasm(
    data: &[u8],
    width: usize,
    height: usize,
    stops: &[f32],
    style: &str,
    angle: f32,
    scale: f32,
    reverse: bool,
    opacity: f32,
) -> Vec<u8> {
    // Parse gradient stops
    struct GradientStop { position: f32, r: f32, g: f32, b: f32 }
    let mut gradient_stops: Vec<GradientStop> = stops.chunks(4)
        .filter(|c| c.len() == 4)
        .map(|c| GradientStop { position: c[0], r: c[1] / 255.0, g: c[2] / 255.0, b: c[3] / 255.0 })
        .collect();

    gradient_stops.sort_by(|a, b| a.position.partial_cmp(&b.position).unwrap_or(std::cmp::Ordering::Equal));

    if gradient_stops.is_empty() {
        gradient_stops.push(GradientStop { position: 0.0, r: 0.0, g: 0.0, b: 0.0 });
        gradient_stops.push(GradientStop { position: 1.0, r: 1.0, g: 1.0, b: 1.0 });
    }

    let input = Array3::from_shape_vec((height, width, 4), data.to_vec()).expect("Invalid dimensions");
    let mut result = Array3::<u8>::zeros((height, width, 4));

    let cx = width as f32 / 2.0;
    let cy = height as f32 / 2.0;

    for y in 0..height {
        for x in 0..width {
            let orig_a = input[[y, x, 3]];
            if orig_a == 0 { continue; }

            // Calculate gradient t based on style
            let px = x as f32;
            let py = y as f32;
            let mut t = match style {
                "linear" => {
                    let angle_rad = angle.to_radians();
                    let dx = angle_rad.cos();
                    let dy = -angle_rad.sin();
                    let rx = px - cx;
                    let ry = py - cy;
                    let proj = rx * dx + ry * dy;
                    let max_dist = (cx * cx + cy * cy).sqrt();
                    (proj / max_dist + 1.0) / 2.0
                }
                "radial" => {
                    let dx = px - cx;
                    let dy = py - cy;
                    let dist = (dx * dx + dy * dy).sqrt();
                    let max_dist = (cx * cx + cy * cy).sqrt();
                    dist / max_dist
                }
                "angle" => {
                    let dx = px - cx;
                    let dy = py - cy;
                    let mut angle_at_pixel = dy.atan2(dx);
                    angle_at_pixel -= angle.to_radians();
                    (angle_at_pixel + std::f32::consts::PI) / (2.0 * std::f32::consts::PI)
                }
                "reflected" => {
                    let angle_rad = angle.to_radians();
                    let dx = angle_rad.cos();
                    let dy = -angle_rad.sin();
                    let rx = px - cx;
                    let ry = py - cy;
                    let proj = rx * dx + ry * dy;
                    let max_dist = (cx * cx + cy * cy).sqrt();
                    let linear_t = (proj / max_dist + 1.0) / 2.0;
                    (2.0 * (linear_t - 0.5)).abs()
                }
                "diamond" => {
                    let dx = (px - cx).abs();
                    let dy = (py - cy).abs();
                    (dx + dy) / (cx + cy)
                }
                _ => {
                    let angle_rad = angle.to_radians();
                    let dx = angle_rad.cos();
                    let dy = -angle_rad.sin();
                    let rx = px - cx;
                    let ry = py - cy;
                    let proj = rx * dx + ry * dy;
                    let max_dist = (cx * cx + cy * cy).sqrt();
                    (proj / max_dist + 1.0) / 2.0
                }
            };

            if scale != 1.0 && scale > 0.0 {
                t = 0.5 + (t - 0.5) / scale;
            }
            t = t.clamp(0.0, 1.0);
            if reverse { t = 1.0 - t; }

            // Interpolate gradient color
            let (grad_r, grad_g, grad_b) = {
                let mut prev_idx = 0;
                let mut next_idx = gradient_stops.len() - 1;
                for (i, stop) in gradient_stops.iter().enumerate() {
                    if stop.position <= t { prev_idx = i; }
                    if stop.position >= t && i > prev_idx { next_idx = i; break; }
                }
                let prev = &gradient_stops[prev_idx];
                let next = &gradient_stops[next_idx];
                if (next.position - prev.position).abs() < 0.0001 {
                    (prev.r, prev.g, prev.b)
                } else {
                    let local_t = ((t - prev.position) / (next.position - prev.position)).clamp(0.0, 1.0);
                    (prev.r + (next.r - prev.r) * local_t, prev.g + (next.g - prev.g) * local_t, prev.b + (next.b - prev.b) * local_t)
                }
            };

            let orig_r = input[[y, x, 0]] as f32 / 255.0;
            let orig_g = input[[y, x, 1]] as f32 / 255.0;
            let orig_b = input[[y, x, 2]] as f32 / 255.0;

            let final_r = orig_r * (1.0 - opacity) + grad_r * opacity;
            let final_g = orig_g * (1.0 - opacity) + grad_g * opacity;
            let final_b = orig_b * (1.0 - opacity) + grad_b * opacity;

            result[[y, x, 0]] = (final_r * 255.0).clamp(0.0, 255.0) as u8;
            result[[y, x, 1]] = (final_g * 255.0).clamp(0.0, 255.0) as u8;
            result[[y, x, 2]] = (final_b * 255.0).clamp(0.0, 255.0) as u8;
            result[[y, x, 3]] = orig_a;
        }
    }

    result.into_raw_vec_and_offset().0
}

// ============================================================================
// Layer Effects: Pattern Overlay
// ============================================================================

/// Sample a pixel from a pattern with tiling (modulo wrapping).
#[inline]
fn sample_pattern_tiled(
    pattern: &Array3<f32>,
    x: isize,
    y: isize,
    pattern_w: usize,
    pattern_h: usize,
) -> (f32, f32, f32, f32) {
    let px = ((x % pattern_w as isize) + pattern_w as isize) as usize % pattern_w;
    let py = ((y % pattern_h as isize) + pattern_h as isize) as usize % pattern_h;
    (
        pattern[[py, px, 0]],
        pattern[[py, px, 1]],
        pattern[[py, px, 2]],
        pattern[[py, px, 3]],
    )
}

/// Bilinear interpolation for scaled pattern sampling.
fn sample_pattern_bilinear(
    pattern: &Array3<f32>,
    x: f32,
    y: f32,
    pattern_w: usize,
    pattern_h: usize,
) -> (f32, f32, f32, f32) {
    let x0 = x.floor() as isize;
    let y0 = y.floor() as isize;
    let x1 = x0 + 1;
    let y1 = y0 + 1;

    let fx = x - x.floor();
    let fy = y - y.floor();

    let (r00, g00, b00, a00) = sample_pattern_tiled(pattern, x0, y0, pattern_w, pattern_h);
    let (r10, g10, b10, a10) = sample_pattern_tiled(pattern, x1, y0, pattern_w, pattern_h);
    let (r01, g01, b01, a01) = sample_pattern_tiled(pattern, x0, y1, pattern_w, pattern_h);
    let (r11, g11, b11, a11) = sample_pattern_tiled(pattern, x1, y1, pattern_w, pattern_h);

    // Bilinear interpolation
    let r = r00 * (1.0 - fx) * (1.0 - fy) + r10 * fx * (1.0 - fy) + r01 * (1.0 - fx) * fy + r11 * fx * fy;
    let g = g00 * (1.0 - fx) * (1.0 - fy) + g10 * fx * (1.0 - fy) + g01 * (1.0 - fx) * fy + g11 * fx * fy;
    let b = b00 * (1.0 - fx) * (1.0 - fy) + b10 * fx * (1.0 - fy) + b01 * (1.0 - fx) * fy + b11 * fx * fy;
    let a = a00 * (1.0 - fx) * (1.0 - fy) + a10 * fx * (1.0 - fy) + a01 * (1.0 - fx) * fy + a11 * fx * fy;

    (r, g, b, a)
}

/// Apply pattern overlay to RGBA u8 image.
///
/// Pattern is tiled across the image, scaled and offset as specified.
/// Uses bilinear interpolation when scale != 1.0 for smooth scaling.
#[wasm_bindgen]
pub fn pattern_overlay_rgba_wasm(
    data: &[u8],
    width: usize,
    height: usize,
    pattern_data: &[u8],
    pattern_width: usize,
    pattern_height: usize,
    scale: f32,
    offset_x: i32,
    offset_y: i32,
    opacity: f32,
) -> Vec<u8> {
    let input = Array3::from_shape_vec((height, width, 4), data.to_vec()).expect("Invalid dimensions");
    let pattern = Array3::from_shape_vec((pattern_height, pattern_width, 4), pattern_data.to_vec()).expect("Invalid pattern dimensions");

    // Convert pattern to f32
    let mut pattern_f32 = Array3::<f32>::zeros((pattern_height, pattern_width, 4));
    for y in 0..pattern_height {
        for x in 0..pattern_width {
            for c in 0..4 {
                pattern_f32[[y, x, c]] = pattern[[y, x, c]] as f32 / 255.0;
            }
        }
    }

    let mut result = Array3::<u8>::zeros((height, width, 4));
    let effective_scale = scale.clamp(0.01, 100.0);

    for y in 0..height {
        for x in 0..width {
            let orig_a = input[[y, x, 3]];
            if orig_a == 0 { continue; }

            // Calculate pattern coordinates with scale and offset
            let px = (x as f32 / effective_scale) + offset_x as f32;
            let py = (y as f32 / effective_scale) + offset_y as f32;

            // Sample pattern (with bilinear interpolation for smooth scaling)
            let (pat_r, pat_g, pat_b, pat_a) = if effective_scale == 1.0 {
                sample_pattern_tiled(&pattern_f32, px.round() as isize, py.round() as isize, pattern_width, pattern_height)
            } else {
                sample_pattern_bilinear(&pattern_f32, px, py, pattern_width, pattern_height)
            };

            let blend_a = opacity * pat_a;
            let orig_r = input[[y, x, 0]] as f32 / 255.0;
            let orig_g = input[[y, x, 1]] as f32 / 255.0;
            let orig_b = input[[y, x, 2]] as f32 / 255.0;

            let final_r = orig_r * (1.0 - blend_a) + pat_r * blend_a;
            let final_g = orig_g * (1.0 - blend_a) + pat_g * blend_a;
            let final_b = orig_b * (1.0 - blend_a) + pat_b * blend_a;

            result[[y, x, 0]] = (final_r * 255.0).clamp(0.0, 255.0) as u8;
            result[[y, x, 1]] = (final_g * 255.0).clamp(0.0, 255.0) as u8;
            result[[y, x, 2]] = (final_b * 255.0).clamp(0.0, 255.0) as u8;
            result[[y, x, 3]] = orig_a;
        }
    }

    result.into_raw_vec_and_offset().0
}

// ============================================================================
// Layer Effects: Drop Shadow
// ============================================================================

/// Apply drop shadow effect to RGBA u8 image.
///
/// Creates a shadow cast behind the layer by blurring and offsetting the alpha.
#[wasm_bindgen]
pub fn drop_shadow_rgba_wasm(
    data: &[u8],
    width: usize,
    height: usize,
    offset_x: f32,
    offset_y: f32,
    blur_radius: f32,
    color_r: u8,
    color_g: u8,
    color_b: u8,
    opacity: f32,
) -> Vec<u8> {
    use ndarray::Array2;

    let input = Array3::from_shape_vec((height, width, 4), data.to_vec()).expect("Invalid dimensions");

    // Convert to f32
    let mut input_f32 = Array3::<f32>::zeros((height, width, 4));
    for y in 0..height {
        for x in 0..width {
            input_f32[[y, x, 0]] = input[[y, x, 0]] as f32 / 255.0;
            input_f32[[y, x, 1]] = input[[y, x, 1]] as f32 / 255.0;
            input_f32[[y, x, 2]] = input[[y, x, 2]] as f32 / 255.0;
            input_f32[[y, x, 3]] = input[[y, x, 3]] as f32 / 255.0;
        }
    }

    // Calculate expansion
    let blur_expand = (blur_radius * 3.0).ceil() as usize;
    let offset_expand = offset_x.abs().max(offset_y.abs()).ceil() as usize;
    let required_expand = blur_expand + offset_expand + 2;

    // Expand canvas
    let expanded = expand_canvas_f32(&input_f32, required_expand);
    let (new_h, new_w, _) = (expanded.shape()[0], expanded.shape()[1], expanded.shape()[2]);

    // Extract alpha
    let mut alpha = Array2::<f32>::zeros((new_h, new_w));
    for y in 0..new_h {
        for x in 0..new_w {
            alpha[[y, x]] = expanded[[y, x, 3]];
        }
    }

    // Blur alpha
    let blurred_alpha = blur_alpha_f32(&alpha, blur_radius);

    // Create result with shadow
    let mut result = Array3::<f32>::zeros((new_h, new_w, 4));
    let shadow_r = color_r as f32 / 255.0;
    let shadow_g = color_g as f32 / 255.0;
    let shadow_b = color_b as f32 / 255.0;

    let ox = offset_x.round() as isize;
    let oy = offset_y.round() as isize;

    // Draw shadow
    for y in 0..new_h {
        for x in 0..new_w {
            let sx = (x as isize - ox).clamp(0, new_w as isize - 1) as usize;
            let sy = (y as isize - oy).clamp(0, new_h as isize - 1) as usize;
            let shadow_a = blurred_alpha[[sy, sx]] * opacity;
            result[[y, x, 0]] = shadow_r;
            result[[y, x, 1]] = shadow_g;
            result[[y, x, 2]] = shadow_b;
            result[[y, x, 3]] = shadow_a;
        }
    }

    // Composite original on top
    for y in 0..new_h {
        for x in 0..new_w {
            let src_a = expanded[[y, x, 3]];
            if src_a <= 0.0 { continue; }
            let dst_a = result[[y, x, 3]];
            let out_a = src_a + dst_a * (1.0 - src_a);
            if out_a > 0.0 {
                result[[y, x, 0]] = (expanded[[y, x, 0]] * src_a + result[[y, x, 0]] * dst_a * (1.0 - src_a)) / out_a;
                result[[y, x, 1]] = (expanded[[y, x, 1]] * src_a + result[[y, x, 1]] * dst_a * (1.0 - src_a)) / out_a;
                result[[y, x, 2]] = (expanded[[y, x, 2]] * src_a + result[[y, x, 2]] * dst_a * (1.0 - src_a)) / out_a;
                result[[y, x, 3]] = out_a;
            }
        }
    }

    result.mapv(|v| (v.clamp(0.0, 1.0) * 255.0) as u8).into_raw_vec_and_offset().0
}

// ============================================================================
// Layer Effects: Inner Shadow
// ============================================================================

/// Apply inner shadow effect to RGBA u8 image.
///
/// Creates a shadow inside the shape by inverting and blurring alpha.
#[wasm_bindgen]
pub fn inner_shadow_rgba_wasm(
    data: &[u8],
    width: usize,
    height: usize,
    offset_x: f32,
    offset_y: f32,
    blur_radius: f32,
    choke: f32,
    color_r: u8,
    color_g: u8,
    color_b: u8,
    opacity: f32,
) -> Vec<u8> {
    use ndarray::Array2;

    let input = Array3::from_shape_vec((height, width, 4), data.to_vec()).expect("Invalid dimensions");

    // Convert to f32
    let mut input_f32 = Array3::<f32>::zeros((height, width, 4));
    for y in 0..height {
        for x in 0..width {
            input_f32[[y, x, 0]] = input[[y, x, 0]] as f32 / 255.0;
            input_f32[[y, x, 1]] = input[[y, x, 1]] as f32 / 255.0;
            input_f32[[y, x, 2]] = input[[y, x, 2]] as f32 / 255.0;
            input_f32[[y, x, 3]] = input[[y, x, 3]] as f32 / 255.0;
        }
    }

    // Extract alpha
    let mut alpha = Array2::<f32>::zeros((height, width));
    for y in 0..height {
        for x in 0..width {
            alpha[[y, x]] = input_f32[[y, x, 3]];
        }
    }

    // Invert alpha
    let mut inverted = Array2::<f32>::zeros((height, width));
    for y in 0..height {
        for x in 0..width {
            inverted[[y, x]] = 1.0 - alpha[[y, x]];
        }
    }

    // Apply choke
    let choke_radius = blur_radius * choke;
    let choked = if choke_radius > 0.0 {
        dilate_alpha(&inverted, choke_radius)
    } else {
        inverted
    };

    // Blur
    let blurred = blur_alpha_f32(&choked, blur_radius);

    // Create result
    let mut result = input_f32.clone();
    let shadow_r = color_r as f32 / 255.0;
    let shadow_g = color_g as f32 / 255.0;
    let shadow_b = color_b as f32 / 255.0;

    let ox = offset_x.round() as isize;
    let oy = offset_y.round() as isize;

    for y in 0..height {
        for x in 0..width {
            let orig_a = alpha[[y, x]];
            if orig_a <= 0.0 { continue; }

            let sx = (x as isize - ox).clamp(0, width as isize - 1) as usize;
            let sy = (y as isize - oy).clamp(0, height as isize - 1) as usize;
            let shadow_a = blurred[[sy, sx]] * opacity * orig_a;

            if shadow_a > 0.0 {
                let out_a = shadow_a + result[[y, x, 3]] * (1.0 - shadow_a);
                if out_a > 0.0 {
                    result[[y, x, 0]] = (shadow_r * shadow_a + result[[y, x, 0]] * result[[y, x, 3]] * (1.0 - shadow_a)) / out_a;
                    result[[y, x, 1]] = (shadow_g * shadow_a + result[[y, x, 1]] * result[[y, x, 3]] * (1.0 - shadow_a)) / out_a;
                    result[[y, x, 2]] = (shadow_b * shadow_a + result[[y, x, 2]] * result[[y, x, 3]] * (1.0 - shadow_a)) / out_a;
                    result[[y, x, 3]] = out_a;
                }
            }
        }
    }

    result.mapv(|v| (v.clamp(0.0, 1.0) * 255.0) as u8).into_raw_vec_and_offset().0
}

// ============================================================================
// Layer Effects: Outer Glow
// ============================================================================

/// Apply outer glow effect to RGBA u8 image.
///
/// Creates a glow effect outside the shape edges.
#[wasm_bindgen]
pub fn outer_glow_rgba_wasm(
    data: &[u8],
    width: usize,
    height: usize,
    radius: f32,
    color_r: u8,
    color_g: u8,
    color_b: u8,
    opacity: f32,
    spread: f32,
) -> Vec<u8> {
    use ndarray::Array2;

    let input = Array3::from_shape_vec((height, width, 4), data.to_vec()).expect("Invalid dimensions");

    // Convert to f32
    let mut input_f32 = Array3::<f32>::zeros((height, width, 4));
    for y in 0..height {
        for x in 0..width {
            input_f32[[y, x, 0]] = input[[y, x, 0]] as f32 / 255.0;
            input_f32[[y, x, 1]] = input[[y, x, 1]] as f32 / 255.0;
            input_f32[[y, x, 2]] = input[[y, x, 2]] as f32 / 255.0;
            input_f32[[y, x, 3]] = input[[y, x, 3]] as f32 / 255.0;
        }
    }

    // Expand canvas
    let required_expand = (radius * 3.0).ceil() as usize + 2;
    let expanded = expand_canvas_f32(&input_f32, required_expand);
    let (new_h, new_w, _) = (expanded.shape()[0], expanded.shape()[1], expanded.shape()[2]);

    // Extract alpha
    let mut alpha = Array2::<f32>::zeros((new_h, new_w));
    for y in 0..new_h {
        for x in 0..new_w {
            alpha[[y, x]] = expanded[[y, x, 3]];
        }
    }

    // Apply spread (dilate before blur)
    let spread_radius = radius * spread;
    let spread_alpha = if spread_radius > 0.0 {
        dilate_alpha(&alpha, spread_radius)
    } else {
        alpha.clone()
    };

    // Blur
    let blurred = blur_alpha_f32(&spread_alpha, radius);

    // Create result
    let mut result = Array3::<f32>::zeros((new_h, new_w, 4));
    let glow_r = color_r as f32 / 255.0;
    let glow_g = color_g as f32 / 255.0;
    let glow_b = color_b as f32 / 255.0;

    // Draw glow (outside only)
    for y in 0..new_h {
        for x in 0..new_w {
            let glow_a = (blurred[[y, x]] - alpha[[y, x]]).max(0.0) * opacity;
            if glow_a > 0.0 {
                result[[y, x, 0]] = glow_r;
                result[[y, x, 1]] = glow_g;
                result[[y, x, 2]] = glow_b;
                result[[y, x, 3]] = glow_a;
            }
        }
    }

    // Composite original on top
    for y in 0..new_h {
        for x in 0..new_w {
            let src_a = expanded[[y, x, 3]];
            if src_a <= 0.0 { continue; }
            let dst_a = result[[y, x, 3]];
            let out_a = src_a + dst_a * (1.0 - src_a);
            if out_a > 0.0 {
                result[[y, x, 0]] = (expanded[[y, x, 0]] * src_a + result[[y, x, 0]] * dst_a * (1.0 - src_a)) / out_a;
                result[[y, x, 1]] = (expanded[[y, x, 1]] * src_a + result[[y, x, 1]] * dst_a * (1.0 - src_a)) / out_a;
                result[[y, x, 2]] = (expanded[[y, x, 2]] * src_a + result[[y, x, 2]] * dst_a * (1.0 - src_a)) / out_a;
                result[[y, x, 3]] = out_a;
            }
        }
    }

    result.mapv(|v| (v.clamp(0.0, 1.0) * 255.0) as u8).into_raw_vec_and_offset().0
}

// ============================================================================
// Layer Effects: Inner Glow
// ============================================================================

/// Apply inner glow effect to RGBA u8 image.
///
/// Creates a glow effect inside the shape edges.
#[wasm_bindgen]
pub fn inner_glow_rgba_wasm(
    data: &[u8],
    width: usize,
    height: usize,
    radius: f32,
    color_r: u8,
    color_g: u8,
    color_b: u8,
    opacity: f32,
    choke: f32,
) -> Vec<u8> {
    use ndarray::Array2;

    let input = Array3::from_shape_vec((height, width, 4), data.to_vec()).expect("Invalid dimensions");

    // Convert to f32
    let mut input_f32 = Array3::<f32>::zeros((height, width, 4));
    for y in 0..height {
        for x in 0..width {
            input_f32[[y, x, 0]] = input[[y, x, 0]] as f32 / 255.0;
            input_f32[[y, x, 1]] = input[[y, x, 1]] as f32 / 255.0;
            input_f32[[y, x, 2]] = input[[y, x, 2]] as f32 / 255.0;
            input_f32[[y, x, 3]] = input[[y, x, 3]] as f32 / 255.0;
        }
    }

    // Extract alpha
    let mut alpha = Array2::<f32>::zeros((height, width));
    for y in 0..height {
        for x in 0..width {
            alpha[[y, x]] = input_f32[[y, x, 3]];
        }
    }

    // Erode and blur
    let choke_radius = radius * choke;
    let eroded = if choke_radius > 0.0 {
        erode_alpha(&alpha, choke_radius)
    } else {
        alpha.clone()
    };
    let blurred = blur_alpha_f32(&eroded, radius * (1.0 - choke * 0.5));

    // Glow mask
    let mut glow_mask = Array2::<f32>::zeros((height, width));
    for y in 0..height {
        for x in 0..width {
            let edge_dist = alpha[[y, x]] - blurred[[y, x]];
            glow_mask[[y, x]] = edge_dist.max(0.0) * alpha[[y, x]];
        }
    }

    // Compose result
    let mut result = input_f32.clone();
    let glow_r = color_r as f32 / 255.0;
    let glow_g = color_g as f32 / 255.0;
    let glow_b = color_b as f32 / 255.0;

    for y in 0..height {
        for x in 0..width {
            let orig_a = alpha[[y, x]];
            if orig_a <= 0.0 { continue; }
            let glow_a = glow_mask[[y, x]] * opacity;
            if glow_a > 0.0 {
                // Screen blend
                result[[y, x, 0]] = 1.0 - (1.0 - result[[y, x, 0]]) * (1.0 - glow_r * glow_a);
                result[[y, x, 1]] = 1.0 - (1.0 - result[[y, x, 1]]) * (1.0 - glow_g * glow_a);
                result[[y, x, 2]] = 1.0 - (1.0 - result[[y, x, 2]]) * (1.0 - glow_b * glow_a);
            }
        }
    }

    result.mapv(|v| (v.clamp(0.0, 1.0) * 255.0) as u8).into_raw_vec_and_offset().0
}

// ============================================================================
// Layer Effects: Bevel & Emboss
// ============================================================================

/// Apply bevel and emboss effect to RGBA u8 image.
///
/// Creates a 3D raised or sunken appearance using highlights and shadows.
#[wasm_bindgen]
pub fn bevel_emboss_rgba_wasm(
    data: &[u8],
    width: usize,
    height: usize,
    depth: f32,
    angle: f32,
    _altitude: f32,
    highlight_r: u8,
    highlight_g: u8,
    highlight_b: u8,
    highlight_opacity: f32,
    shadow_r: u8,
    shadow_g: u8,
    shadow_b: u8,
    shadow_opacity: f32,
    style: &str,
) -> Vec<u8> {
    use ndarray::Array2;

    let input = Array3::from_shape_vec((height, width, 4), data.to_vec()).expect("Invalid dimensions");

    // Convert to f32
    let mut input_f32 = Array3::<f32>::zeros((height, width, 4));
    for y in 0..height {
        for x in 0..width {
            input_f32[[y, x, 0]] = input[[y, x, 0]] as f32 / 255.0;
            input_f32[[y, x, 1]] = input[[y, x, 1]] as f32 / 255.0;
            input_f32[[y, x, 2]] = input[[y, x, 2]] as f32 / 255.0;
            input_f32[[y, x, 3]] = input[[y, x, 3]] as f32 / 255.0;
        }
    }

    // Expand for outer bevel
    let is_outer = style == "outer_bevel";
    let expand = if is_outer { (depth.ceil() as usize) + 2 } else { 0 };
    let expanded = if expand > 0 {
        expand_canvas_f32(&input_f32, expand)
    } else {
        input_f32.clone()
    };

    let (new_h, new_w, _) = (expanded.shape()[0], expanded.shape()[1], expanded.shape()[2]);

    // Extract alpha
    let mut alpha = Array2::<f32>::zeros((new_h, new_w));
    for y in 0..new_h {
        for x in 0..new_w {
            alpha[[y, x]] = expanded[[y, x, 3]];
        }
    }

    // Light direction
    let angle_rad = angle.to_radians();
    let dx = angle_rad.cos();
    let dy = -angle_rad.sin();

    // Bump map
    let mut bump_x = Array2::<f32>::zeros((new_h, new_w));
    let mut bump_y = Array2::<f32>::zeros((new_h, new_w));
    for y in 1..new_h - 1 {
        for x in 1..new_w - 1 {
            bump_x[[y, x]] = (alpha[[y, x + 1]] - alpha[[y, x - 1]]) / 2.0;
            bump_y[[y, x]] = (alpha[[y + 1, x]] - alpha[[y - 1, x]]) / 2.0;
        }
    }

    let bump_x_blur = blur_alpha_f32(&bump_x, depth * 0.5);
    let bump_y_blur = blur_alpha_f32(&bump_y, depth * 0.5);

    // Create result
    let mut result = expanded.clone();
    let hl_r = highlight_r as f32 / 255.0;
    let hl_g = highlight_g as f32 / 255.0;
    let hl_b = highlight_b as f32 / 255.0;
    let sh_r = shadow_r as f32 / 255.0;
    let sh_g = shadow_g as f32 / 255.0;
    let sh_b = shadow_b as f32 / 255.0;

    for y in 0..new_h {
        for x in 0..new_w {
            let orig_a = expanded[[y, x, 3]];
            if orig_a <= 0.0 && !is_outer { continue; }

            let bx = bump_x_blur[[y, x]] * depth;
            let by = bump_y_blur[[y, x]] * depth;
            let intensity = bx * dx + by * dy;

            if intensity > 0.0 {
                let hl_a = intensity.min(1.0) * highlight_opacity * orig_a;
                if hl_a > 0.0 {
                    let src_a = hl_a;
                    let dst_a = result[[y, x, 3]];
                    let out_a = src_a + dst_a * (1.0 - src_a);
                    if out_a > 0.0 {
                        result[[y, x, 0]] = (hl_r * src_a + result[[y, x, 0]] * dst_a * (1.0 - src_a)) / out_a;
                        result[[y, x, 1]] = (hl_g * src_a + result[[y, x, 1]] * dst_a * (1.0 - src_a)) / out_a;
                        result[[y, x, 2]] = (hl_b * src_a + result[[y, x, 2]] * dst_a * (1.0 - src_a)) / out_a;
                        result[[y, x, 3]] = out_a;
                    }
                }
            } else if intensity < 0.0 {
                let sh_a = (-intensity).min(1.0) * shadow_opacity * orig_a;
                if sh_a > 0.0 {
                    let src_a = sh_a;
                    let dst_a = result[[y, x, 3]];
                    let out_a = src_a + dst_a * (1.0 - src_a);
                    if out_a > 0.0 {
                        result[[y, x, 0]] = (sh_r * src_a + result[[y, x, 0]] * dst_a * (1.0 - src_a)) / out_a;
                        result[[y, x, 1]] = (sh_g * src_a + result[[y, x, 1]] * dst_a * (1.0 - src_a)) / out_a;
                        result[[y, x, 2]] = (sh_b * src_a + result[[y, x, 2]] * dst_a * (1.0 - src_a)) / out_a;
                        result[[y, x, 3]] = out_a;
                    }
                }
            }
        }
    }

    result.mapv(|v| (v.clamp(0.0, 1.0) * 255.0) as u8).into_raw_vec_and_offset().0
}

// ============================================================================
// Layer Effects: Stroke
// ============================================================================

/// Apply stroke/outline effect to RGBA u8 image.
///
/// Creates an outline around non-transparent areas.
#[wasm_bindgen]
pub fn stroke_rgba_wasm(
    data: &[u8],
    img_width: usize,
    height: usize,
    stroke_width: f32,
    color_r: u8,
    color_g: u8,
    color_b: u8,
    opacity: f32,
    position: &str,
) -> Vec<u8> {
    use ndarray::Array2;

    let input = Array3::from_shape_vec((height, img_width, 4), data.to_vec()).expect("Invalid dimensions");

    // Convert to f32
    let mut input_f32 = Array3::<f32>::zeros((height, img_width, 4));
    for y in 0..height {
        for x in 0..img_width {
            input_f32[[y, x, 0]] = input[[y, x, 0]] as f32 / 255.0;
            input_f32[[y, x, 1]] = input[[y, x, 1]] as f32 / 255.0;
            input_f32[[y, x, 2]] = input[[y, x, 2]] as f32 / 255.0;
            input_f32[[y, x, 3]] = input[[y, x, 3]] as f32 / 255.0;
        }
    }

    // Expand for outside stroke
    let is_inside = position == "inside";
    let required_expand = if is_inside { 0 } else { (stroke_width.ceil() as usize) + 2 };
    let expanded = if required_expand > 0 {
        expand_canvas_f32(&input_f32, required_expand)
    } else {
        input_f32.clone()
    };

    let (new_h, new_w, _) = (expanded.shape()[0], expanded.shape()[1], expanded.shape()[2]);

    // Extract alpha
    let mut alpha = Array2::<f32>::zeros((new_h, new_w));
    for y in 0..new_h {
        for x in 0..new_w {
            alpha[[y, x]] = expanded[[y, x, 3]];
        }
    }

    // Create stroke mask
    let stroke_mask = match position {
        "inside" => {
            let eroded = erode_alpha(&alpha, stroke_width);
            let mut mask = Array2::<f32>::zeros((new_h, new_w));
            for y in 0..new_h {
                for x in 0..new_w {
                    mask[[y, x]] = (alpha[[y, x]] - eroded[[y, x]]).max(0.0);
                }
            }
            mask
        }
        "center" => {
            let half = stroke_width / 2.0;
            let dilated = dilate_alpha(&alpha, half);
            let eroded = erode_alpha(&alpha, half);
            let mut mask = Array2::<f32>::zeros((new_h, new_w));
            for y in 0..new_h {
                for x in 0..new_w {
                    mask[[y, x]] = (dilated[[y, x]] - eroded[[y, x]]).max(0.0);
                }
            }
            mask
        }
        _ => { // outside
            let dilated = dilate_alpha(&alpha, stroke_width);
            let mut mask = Array2::<f32>::zeros((new_h, new_w));
            for y in 0..new_h {
                for x in 0..new_w {
                    mask[[y, x]] = (dilated[[y, x]] - alpha[[y, x]]).max(0.0);
                }
            }
            mask
        }
    };

    // Create result
    let mut result = Array3::<f32>::zeros((new_h, new_w, 4));
    let stroke_r = color_r as f32 / 255.0;
    let stroke_g = color_g as f32 / 255.0;
    let stroke_b = color_b as f32 / 255.0;

    // Draw stroke
    for y in 0..new_h {
        for x in 0..new_w {
            let stroke_a = stroke_mask[[y, x]] * opacity;
            if stroke_a > 0.0 {
                result[[y, x, 0]] = stroke_r;
                result[[y, x, 1]] = stroke_g;
                result[[y, x, 2]] = stroke_b;
                result[[y, x, 3]] = stroke_a;
            }
        }
    }

    // Composite original
    if is_inside {
        for y in 0..new_h {
            for x in 0..new_w {
                let orig_a = expanded[[y, x, 3]];
                if orig_a <= 0.0 { continue; }
                let stroke_a = result[[y, x, 3]];
                if stroke_a <= 0.0 {
                    result[[y, x, 0]] = expanded[[y, x, 0]];
                    result[[y, x, 1]] = expanded[[y, x, 1]];
                    result[[y, x, 2]] = expanded[[y, x, 2]];
                    result[[y, x, 3]] = orig_a;
                } else {
                    let out_a = stroke_a + orig_a * (1.0 - stroke_a);
                    if out_a > 0.0 {
                        result[[y, x, 0]] = (result[[y, x, 0]] * stroke_a + expanded[[y, x, 0]] * orig_a * (1.0 - stroke_a)) / out_a;
                        result[[y, x, 1]] = (result[[y, x, 1]] * stroke_a + expanded[[y, x, 1]] * orig_a * (1.0 - stroke_a)) / out_a;
                        result[[y, x, 2]] = (result[[y, x, 2]] * stroke_a + expanded[[y, x, 2]] * orig_a * (1.0 - stroke_a)) / out_a;
                        result[[y, x, 3]] = out_a;
                    }
                }
            }
        }
    } else {
        for y in 0..new_h {
            for x in 0..new_w {
                let src_a = expanded[[y, x, 3]];
                if src_a <= 0.0 { continue; }
                let dst_a = result[[y, x, 3]];
                let out_a = src_a + dst_a * (1.0 - src_a);
                if out_a > 0.0 {
                    result[[y, x, 0]] = (expanded[[y, x, 0]] * src_a + result[[y, x, 0]] * dst_a * (1.0 - src_a)) / out_a;
                    result[[y, x, 1]] = (expanded[[y, x, 1]] * src_a + result[[y, x, 1]] * dst_a * (1.0 - src_a)) / out_a;
                    result[[y, x, 2]] = (expanded[[y, x, 2]] * src_a + result[[y, x, 2]] * dst_a * (1.0 - src_a)) / out_a;
                    result[[y, x, 3]] = out_a;
                }
            }
        }
    }

    result.mapv(|v| (v.clamp(0.0, 1.0) * 255.0) as u8).into_raw_vec_and_offset().0
}

// ============================================================================
// Layer Effects: Color Overlay
// ============================================================================

/// Apply color overlay effect to RGBA u8 image.
///
/// Replaces all colors with a solid color while preserving alpha.
#[wasm_bindgen]
pub fn color_overlay_rgba_wasm(
    data: &[u8],
    width: usize,
    height: usize,
    color_r: u8,
    color_g: u8,
    color_b: u8,
    opacity: f32,
) -> Vec<u8> {
    let input = Array3::from_shape_vec((height, width, 4), data.to_vec()).expect("Invalid dimensions");
    let mut result = Array3::<u8>::zeros((height, width, 4));

    for y in 0..height {
        for x in 0..width {
            let orig_a = input[[y, x, 3]] as f32 / 255.0;
            if orig_a <= 0.0 { continue; }

            let blend_a = opacity;
            let orig_r = input[[y, x, 0]] as f32 / 255.0;
            let orig_g = input[[y, x, 1]] as f32 / 255.0;
            let orig_b = input[[y, x, 2]] as f32 / 255.0;
            let overlay_r = color_r as f32 / 255.0;
            let overlay_g = color_g as f32 / 255.0;
            let overlay_b = color_b as f32 / 255.0;

            let final_r = orig_r * (1.0 - blend_a) + overlay_r * blend_a;
            let final_g = orig_g * (1.0 - blend_a) + overlay_g * blend_a;
            let final_b = orig_b * (1.0 - blend_a) + overlay_b * blend_a;

            result[[y, x, 0]] = (final_r * 255.0) as u8;
            result[[y, x, 1]] = (final_g * 255.0) as u8;
            result[[y, x, 2]] = (final_b * 255.0) as u8;
            result[[y, x, 3]] = input[[y, x, 3]];
        }
    }

    result.into_raw_vec_and_offset().0
}

// ============================================================================
// Selection Algorithms
// ============================================================================

use crate::selection::contour::extract_contours as extract_contours_impl;
use crate::selection::magic_wand::magic_wand_select as magic_wand_impl;
use crate::selection::marching_squares::{
    extract_contours_precise as extract_contours_precise_impl,
    contours_to_flat,
    douglas_peucker as douglas_peucker_impl,
    douglas_peucker_closed as douglas_peucker_closed_impl,
    Point as MarchingPoint,
};

/// Extract contours from an alpha mask using Marching Squares.
///
/// # Arguments
/// * `mask` - Alpha mask (0 = unselected, >0 = selected)
/// * `width` - Mask width
/// * `height` - Mask height
///
/// # Returns
/// Flat array: [num_contours, len1, x1, y1, x2, y2, ..., len2, ...]
#[wasm_bindgen]
pub fn extract_contours_wasm(mask: &[u8], width: usize, height: usize) -> Vec<f32> {
    extract_contours_impl(mask, width, height)
}

/// Magic wand selection using flood fill algorithm.
///
/// # Arguments
/// * `image` - RGBA image data (4 bytes per pixel)
/// * `width` - Image width
/// * `height` - Image height
/// * `start_x` - Starting X coordinate
/// * `start_y` - Starting Y coordinate
/// * `tolerance` - Color tolerance (0-255)
/// * `contiguous` - If true, only selects connected pixels
///
/// # Returns
/// Selection mask (255 = selected, 0 = not selected)
#[wasm_bindgen]
pub fn magic_wand_select_wasm(
    image: &[u8],
    width: usize,
    height: usize,
    start_x: usize,
    start_y: usize,
    tolerance: u8,
    contiguous: bool,
) -> Vec<u8> {
    magic_wand_impl(image, width, height, start_x, start_y, tolerance, contiguous)
}

// ============================================================================
// Precise Contour Extraction (Marching Squares + Simplification + Bezier)
// ============================================================================

/// Extract precise sub-pixel contours from an alpha mask.
///
/// Uses Marching Squares algorithm for sub-pixel contour extraction,
/// Douglas-Peucker for simplification, and optional Bezier curve fitting.
///
/// # Arguments
/// * `mask` - Alpha mask (0-255), flattened row-major
/// * `width` - Mask width
/// * `height` - Mask height
/// * `threshold` - Alpha threshold (0.0-1.0)
/// * `simplify_epsilon` - Douglas-Peucker epsilon (0 = no simplification)
/// * `fit_beziers` - Whether to fit Bezier curves
/// * `bezier_smoothness` - Bezier smoothness factor (0.1-0.5)
///
/// # Returns
/// Flat array with contour data:
/// [num_contours,
///  is_closed_1, num_points_1, x1, y1, x2, y2, ...,
///  has_beziers_1, (num_beziers, p0x, p0y, p1x, p1y, p2x, p2y, p3x, p3y, ...),
///  ...]
#[wasm_bindgen]
pub fn extract_contours_precise_wasm(
    mask: &[u8],
    width: usize,
    height: usize,
    threshold: f32,
    simplify_epsilon: f32,
    fit_beziers: bool,
    bezier_smoothness: f32,
) -> Vec<f32> {
    let contours = extract_contours_precise_impl(
        mask,
        width,
        height,
        threshold,
        simplify_epsilon,
        fit_beziers,
        bezier_smoothness,
    );
    contours_to_flat(&contours)
}

/// Simplify a polyline using the Douglas-Peucker algorithm.
///
/// # Arguments
/// * `points` - Flat array of floats [x1, y1, x2, y2, ...] representing the polyline
/// * `epsilon` - Maximum distance threshold for simplification (higher = more simplification)
///
/// # Returns
/// Flat array of simplified points [x1, y1, x2, y2, ...]
#[wasm_bindgen]
pub fn douglas_peucker_wasm(
    points: &[f32],
    epsilon: f32,
) -> Vec<f32> {
    // Convert flat array to Point array
    let pts: Vec<MarchingPoint> = points
        .chunks(2)
        .map(|chunk| MarchingPoint { x: chunk[0], y: chunk[1] })
        .collect();

    let simplified = douglas_peucker_impl(&pts, epsilon);

    // Convert back to flat array
    simplified.iter().flat_map(|p| vec![p.x, p.y]).collect()
}

/// Simplify a closed polygon using the Douglas-Peucker algorithm.
///
/// This version handles closed polygons by finding the point farthest from
/// the centroid to use as the starting point, ensuring better results.
///
/// # Arguments
/// * `points` - Flat array of floats [x1, y1, x2, y2, ...] representing the closed polygon
/// * `epsilon` - Maximum distance threshold for simplification (higher = more simplification)
///
/// # Returns
/// Flat array of simplified points [x1, y1, x2, y2, ...] (closed polygon)
#[wasm_bindgen]
pub fn douglas_peucker_closed_wasm(
    points: &[f32],
    epsilon: f32,
) -> Vec<f32> {
    // Convert flat array to Point array
    let pts: Vec<MarchingPoint> = points
        .chunks(2)
        .map(|chunk| MarchingPoint { x: chunk[0], y: chunk[1] })
        .collect();

    let simplified = douglas_peucker_closed_impl(&pts, epsilon);

    // Convert back to flat array
    simplified.iter().flat_map(|p| vec![p.x, p.y]).collect()
}
