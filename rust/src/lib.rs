//! ImageStag Rust Extensions
//!
//! High-performance image processing functions implemented in Rust
//! with Python bindings via PyO3 and WASM bindings for JavaScript.
//!
//! ## Image Format
//! Cross-platform filters support multiple channel configurations:
//! - **Grayscale**: (height, width, 1) - single channel
//! - **RGB**: (height, width, 3) - 3 color channels
//! - **RGBA**: (height, width, 4) - 3 color channels + alpha
//!
//! Both bit depths are supported:
//! - `u8`: 8-bit per channel (0-255)
//! - `f32`: Float per channel (0.0-1.0)
//!
//! Channel count is inferred from input array dimensions. Filters process
//! only the channels present (no wasted work on unused alpha).
//!
//! ## Filter Architecture
//! Filters can produce output images with different dimensions than input,
//! useful for effects like drop shadows that extend beyond the original bounds.

pub mod filters;

#[cfg(feature = "python")]
pub mod layer_effects;

#[cfg(feature = "wasm")]
pub mod wasm;

// Python bindings (only when python feature is enabled)
#[cfg(feature = "python")]
mod python {
    use numpy::{IntoPyArray, PyArray3, PyReadonlyArray3};
    use pyo3::prelude::*;

    // Layer effects (all in layer_effects module)
    use crate::layer_effects::drop_shadow::{drop_shadow_rgba, drop_shadow_rgba_f32};
    use crate::layer_effects::stroke::{stroke_rgba, stroke_rgba_f32};
    use crate::layer_effects::lighting::{
        bevel_emboss_rgba, inner_glow_rgba, outer_glow_rgba,
        inner_shadow_rgba, inner_shadow_rgba_f32,
        color_overlay_rgba, color_overlay_rgba_f32,
    };
    use crate::layer_effects::satin::{satin_rgba, satin_rgba_f32};
    use crate::layer_effects::gradient_overlay::{gradient_overlay_rgba, gradient_overlay_rgba_f32};
    use crate::layer_effects::pattern_overlay::{pattern_overlay_rgba, pattern_overlay_rgba_f32};
    use crate::filters::blur::{gaussian_blur_rgba, box_blur_rgba};
    use crate::filters::basic::{threshold_gray, invert_rgba, premultiply_alpha, unpremultiply_alpha};
    use crate::filters::grayscale::{
        grayscale_rgba_u8, grayscale_rgba_f32 as grayscale_f32_impl,
        grayscale_weighted_u8, grayscale_weighted_f32, GrayscaleWeights,
        u8_to_f32 as u8_to_f32_impl, f32_to_u8 as f32_to_u8_impl,
        f32_to_u16_12bit as f32_to_12bit_impl, u16_12bit_to_f32 as u12bit_to_f32_impl,
    };

    // Cross-platform filters
    use crate::filters::color_adjust;
    use crate::filters::color_science;
    use crate::filters::stylize;
    use crate::filters::levels_curves;
    use crate::filters::sharpen as sharpen_mod;
    use crate::filters::edge;
    use crate::filters::noise as noise_mod;
    use crate::filters::morphology;

    // ========================================================================
    // Grayscale Filter
    // ========================================================================

    /// Convert RGBA u8 image to grayscale using BT.709 luminosity.
    ///
    /// Output is RGBA with R=G=B=luminosity, alpha preserved.
    #[pyfunction]
    pub fn grayscale_rgba<'py>(
        py: Python<'py>,
        image: PyReadonlyArray3<'py, u8>,
    ) -> Bound<'py, PyArray3<u8>> {
        let input = image.as_array();
        let result = grayscale_rgba_u8(input);
        result.into_pyarray(py)
    }

    /// Convert RGBA f32 image to grayscale using BT.709 luminosity.
    ///
    /// Input/output values are 0.0-1.0.
    #[pyfunction]
    pub fn grayscale_rgba_f32<'py>(
        py: Python<'py>,
        image: PyReadonlyArray3<'py, f32>,
    ) -> Bound<'py, PyArray3<f32>> {
        let input = image.as_array();
        let result = grayscale_f32_impl(input);
        result.into_pyarray(py)
    }

    /// Convert image to grayscale with custom RGB channel weights (u8).
    ///
    /// Weights are normalized automatically. Use this for Photoshop-style
    /// Black & White adjustments.
    ///
    /// # Arguments
    /// * `image` - Input image (1, 3, or 4 channels)
    /// * `r_weight` - Red channel weight (default: 0.2126 for BT.709)
    /// * `g_weight` - Green channel weight (default: 0.7152 for BT.709)
    /// * `b_weight` - Blue channel weight (default: 0.0722 for BT.709)
    #[pyfunction]
    #[pyo3(signature = (image, r_weight=0.2126, g_weight=0.7152, b_weight=0.0722))]
    pub fn grayscale_weighted<'py>(
        py: Python<'py>,
        image: PyReadonlyArray3<'py, u8>,
        r_weight: f32,
        g_weight: f32,
        b_weight: f32,
    ) -> Bound<'py, PyArray3<u8>> {
        let input = image.as_array();
        let weights = GrayscaleWeights::custom(r_weight, g_weight, b_weight);
        let result = grayscale_weighted_u8(input, weights);
        result.into_pyarray(py)
    }

    /// Convert image to grayscale with custom RGB channel weights (f32).
    ///
    /// Weights are normalized automatically.
    #[pyfunction]
    #[pyo3(signature = (image, r_weight=0.2126, g_weight=0.7152, b_weight=0.0722))]
    pub fn grayscale_weighted_f32_py<'py>(
        py: Python<'py>,
        image: PyReadonlyArray3<'py, f32>,
        r_weight: f32,
        g_weight: f32,
        b_weight: f32,
    ) -> Bound<'py, PyArray3<f32>> {
        let input = image.as_array();
        let weights = GrayscaleWeights::custom(r_weight, g_weight, b_weight);
        let result = grayscale_weighted_f32(input, weights);
        result.into_pyarray(py)
    }

    // ========================================================================
    // Conversion Utilities
    // ========================================================================

    /// Convert u8 image (0-255) to f32 (0.0-1.0)
    #[pyfunction]
    pub fn convert_u8_to_f32<'py>(
        py: Python<'py>,
        image: PyReadonlyArray3<'py, u8>,
    ) -> Bound<'py, PyArray3<f32>> {
        let input = image.as_array();
        let result = u8_to_f32_impl(input);
        result.into_pyarray(py)
    }

    /// Convert f32 image (0.0-1.0) to u8 (0-255)
    #[pyfunction]
    pub fn convert_f32_to_u8<'py>(
        py: Python<'py>,
        image: PyReadonlyArray3<'py, f32>,
    ) -> Bound<'py, PyArray3<u8>> {
        let input = image.as_array();
        let result = f32_to_u8_impl(input);
        result.into_pyarray(py)
    }

    /// Convert f32 image (0.0-1.0) to u16 12-bit (0-4095)
    #[pyfunction]
    pub fn convert_f32_to_12bit<'py>(
        py: Python<'py>,
        image: PyReadonlyArray3<'py, f32>,
    ) -> Bound<'py, PyArray3<u16>> {
        let input = image.as_array();
        let result = f32_to_12bit_impl(input);
        result.into_pyarray(py)
    }

    /// Convert u16 12-bit (0-4095) to f32 (0.0-1.0)
    #[pyfunction]
    pub fn convert_12bit_to_f32<'py>(
        py: Python<'py>,
        image: PyReadonlyArray3<'py, u16>,
    ) -> Bound<'py, PyArray3<f32>> {
        let input = image.as_array();
        let result = u12bit_to_f32_impl(input);
        result.into_pyarray(py)
    }

    // ========================================================================
    // Color Adjustment Filters
    // ========================================================================

    #[pyfunction]
    pub fn brightness<'py>(
        py: Python<'py>,
        image: PyReadonlyArray3<'py, u8>,
        amount: f32,
    ) -> Bound<'py, PyArray3<u8>> {
        let result = color_adjust::brightness_u8(image.as_array(), amount);
        result.into_pyarray(py)
    }

    #[pyfunction]
    pub fn brightness_f32<'py>(
        py: Python<'py>,
        image: PyReadonlyArray3<'py, f32>,
        amount: f32,
    ) -> Bound<'py, PyArray3<f32>> {
        let result = color_adjust::brightness_f32(image.as_array(), amount);
        result.into_pyarray(py)
    }

    #[pyfunction]
    pub fn contrast<'py>(
        py: Python<'py>,
        image: PyReadonlyArray3<'py, u8>,
        amount: f32,
    ) -> Bound<'py, PyArray3<u8>> {
        let result = color_adjust::contrast_u8(image.as_array(), amount);
        result.into_pyarray(py)
    }

    #[pyfunction]
    pub fn contrast_f32<'py>(
        py: Python<'py>,
        image: PyReadonlyArray3<'py, f32>,
        amount: f32,
    ) -> Bound<'py, PyArray3<f32>> {
        let result = color_adjust::contrast_f32(image.as_array(), amount);
        result.into_pyarray(py)
    }

    #[pyfunction]
    pub fn saturation<'py>(
        py: Python<'py>,
        image: PyReadonlyArray3<'py, u8>,
        amount: f32,
    ) -> Bound<'py, PyArray3<u8>> {
        let result = color_adjust::saturation_u8(image.as_array(), amount);
        result.into_pyarray(py)
    }

    #[pyfunction]
    pub fn saturation_f32<'py>(
        py: Python<'py>,
        image: PyReadonlyArray3<'py, f32>,
        amount: f32,
    ) -> Bound<'py, PyArray3<f32>> {
        let result = color_adjust::saturation_f32(image.as_array(), amount);
        result.into_pyarray(py)
    }

    #[pyfunction]
    pub fn gamma<'py>(
        py: Python<'py>,
        image: PyReadonlyArray3<'py, u8>,
        gamma_val: f32,
    ) -> Bound<'py, PyArray3<u8>> {
        let result = color_adjust::gamma_u8(image.as_array(), gamma_val);
        result.into_pyarray(py)
    }

    #[pyfunction]
    pub fn gamma_f32<'py>(
        py: Python<'py>,
        image: PyReadonlyArray3<'py, f32>,
        gamma_val: f32,
    ) -> Bound<'py, PyArray3<f32>> {
        let result = color_adjust::gamma_f32(image.as_array(), gamma_val);
        result.into_pyarray(py)
    }

    #[pyfunction]
    pub fn exposure<'py>(
        py: Python<'py>,
        image: PyReadonlyArray3<'py, u8>,
        exposure_val: f32,
        offset: f32,
        gamma_val: f32,
    ) -> Bound<'py, PyArray3<u8>> {
        let result = color_adjust::exposure_u8(image.as_array(), exposure_val, offset, gamma_val);
        result.into_pyarray(py)
    }

    #[pyfunction]
    pub fn exposure_f32<'py>(
        py: Python<'py>,
        image: PyReadonlyArray3<'py, f32>,
        exposure_val: f32,
        offset: f32,
        gamma_val: f32,
    ) -> Bound<'py, PyArray3<f32>> {
        let result = color_adjust::exposure_f32(image.as_array(), exposure_val, offset, gamma_val);
        result.into_pyarray(py)
    }

    #[pyfunction]
    pub fn invert<'py>(
        py: Python<'py>,
        image: PyReadonlyArray3<'py, u8>,
    ) -> Bound<'py, PyArray3<u8>> {
        let result = color_adjust::invert_u8(image.as_array());
        result.into_pyarray(py)
    }

    #[pyfunction]
    pub fn invert_f32<'py>(
        py: Python<'py>,
        image: PyReadonlyArray3<'py, f32>,
    ) -> Bound<'py, PyArray3<f32>> {
        let result = color_adjust::invert_f32(image.as_array());
        result.into_pyarray(py)
    }

    // ========================================================================
    // Color Science Filters
    // ========================================================================

    #[pyfunction]
    pub fn hue_shift<'py>(
        py: Python<'py>,
        image: PyReadonlyArray3<'py, u8>,
        degrees: f32,
    ) -> Bound<'py, PyArray3<u8>> {
        let result = color_science::hue_shift_u8(image.as_array(), degrees);
        result.into_pyarray(py)
    }

    #[pyfunction]
    pub fn hue_shift_f32<'py>(
        py: Python<'py>,
        image: PyReadonlyArray3<'py, f32>,
        degrees: f32,
    ) -> Bound<'py, PyArray3<f32>> {
        let result = color_science::hue_shift_f32(image.as_array(), degrees);
        result.into_pyarray(py)
    }

    #[pyfunction]
    pub fn vibrance<'py>(
        py: Python<'py>,
        image: PyReadonlyArray3<'py, u8>,
        amount: f32,
    ) -> Bound<'py, PyArray3<u8>> {
        let result = color_science::vibrance_u8(image.as_array(), amount);
        result.into_pyarray(py)
    }

    #[pyfunction]
    pub fn vibrance_f32<'py>(
        py: Python<'py>,
        image: PyReadonlyArray3<'py, f32>,
        amount: f32,
    ) -> Bound<'py, PyArray3<f32>> {
        let result = color_science::vibrance_f32(image.as_array(), amount);
        result.into_pyarray(py)
    }

    #[pyfunction]
    pub fn color_balance<'py>(
        py: Python<'py>,
        image: PyReadonlyArray3<'py, u8>,
        shadows: [f32; 3],
        midtones: [f32; 3],
        highlights: [f32; 3],
    ) -> Bound<'py, PyArray3<u8>> {
        let result = color_science::color_balance_u8(image.as_array(), shadows, midtones, highlights);
        result.into_pyarray(py)
    }

    #[pyfunction]
    pub fn color_balance_f32<'py>(
        py: Python<'py>,
        image: PyReadonlyArray3<'py, f32>,
        shadows: [f32; 3],
        midtones: [f32; 3],
        highlights: [f32; 3],
    ) -> Bound<'py, PyArray3<f32>> {
        let result = color_science::color_balance_f32(image.as_array(), shadows, midtones, highlights);
        result.into_pyarray(py)
    }

    // ========================================================================
    // Stylize Filters
    // ========================================================================

    #[pyfunction]
    pub fn posterize<'py>(
        py: Python<'py>,
        image: PyReadonlyArray3<'py, u8>,
        levels: u8,
    ) -> Bound<'py, PyArray3<u8>> {
        let result = stylize::posterize_u8(image.as_array(), levels);
        result.into_pyarray(py)
    }

    #[pyfunction]
    pub fn posterize_f32<'py>(
        py: Python<'py>,
        image: PyReadonlyArray3<'py, f32>,
        levels: u8,
    ) -> Bound<'py, PyArray3<f32>> {
        let result = stylize::posterize_f32(image.as_array(), levels);
        result.into_pyarray(py)
    }

    #[pyfunction]
    pub fn solarize<'py>(
        py: Python<'py>,
        image: PyReadonlyArray3<'py, u8>,
        threshold: u8,
    ) -> Bound<'py, PyArray3<u8>> {
        let result = stylize::solarize_u8(image.as_array(), threshold);
        result.into_pyarray(py)
    }

    #[pyfunction]
    pub fn solarize_f32<'py>(
        py: Python<'py>,
        image: PyReadonlyArray3<'py, f32>,
        threshold: f32,
    ) -> Bound<'py, PyArray3<f32>> {
        let result = stylize::solarize_f32(image.as_array(), threshold);
        result.into_pyarray(py)
    }

    #[pyfunction]
    pub fn threshold<'py>(
        py: Python<'py>,
        image: PyReadonlyArray3<'py, u8>,
        threshold_val: u8,
    ) -> Bound<'py, PyArray3<u8>> {
        let result = stylize::threshold_u8(image.as_array(), threshold_val);
        result.into_pyarray(py)
    }

    #[pyfunction]
    pub fn threshold_f32<'py>(
        py: Python<'py>,
        image: PyReadonlyArray3<'py, f32>,
        threshold_val: f32,
    ) -> Bound<'py, PyArray3<f32>> {
        let result = stylize::threshold_f32(image.as_array(), threshold_val);
        result.into_pyarray(py)
    }

    #[pyfunction]
    pub fn emboss<'py>(
        py: Python<'py>,
        image: PyReadonlyArray3<'py, u8>,
        angle: f32,
        depth: f32,
    ) -> Bound<'py, PyArray3<u8>> {
        let result = stylize::emboss_u8(image.as_array(), angle, depth);
        result.into_pyarray(py)
    }

    #[pyfunction]
    pub fn emboss_f32<'py>(
        py: Python<'py>,
        image: PyReadonlyArray3<'py, f32>,
        angle: f32,
        depth: f32,
    ) -> Bound<'py, PyArray3<f32>> {
        let result = stylize::emboss_f32(image.as_array(), angle, depth);
        result.into_pyarray(py)
    }

    // ========================================================================
    // Levels & Curves Filters
    // ========================================================================

    #[pyfunction]
    pub fn levels<'py>(
        py: Python<'py>,
        image: PyReadonlyArray3<'py, u8>,
        in_black: u8,
        in_white: u8,
        out_black: u8,
        out_white: u8,
        gamma_val: f32,
    ) -> Bound<'py, PyArray3<u8>> {
        let result = levels_curves::levels_u8(image.as_array(), in_black, in_white, out_black, out_white, gamma_val);
        result.into_pyarray(py)
    }

    #[pyfunction]
    pub fn levels_f32<'py>(
        py: Python<'py>,
        image: PyReadonlyArray3<'py, f32>,
        in_black: f32,
        in_white: f32,
        out_black: f32,
        out_white: f32,
        gamma_val: f32,
    ) -> Bound<'py, PyArray3<f32>> {
        let result = levels_curves::levels_f32(image.as_array(), in_black, in_white, out_black, out_white, gamma_val);
        result.into_pyarray(py)
    }

    #[pyfunction]
    pub fn curves<'py>(
        py: Python<'py>,
        image: PyReadonlyArray3<'py, u8>,
        points: Vec<(f32, f32)>,
    ) -> Bound<'py, PyArray3<u8>> {
        let result = levels_curves::curves_u8(image.as_array(), &points);
        result.into_pyarray(py)
    }

    #[pyfunction]
    pub fn curves_f32<'py>(
        py: Python<'py>,
        image: PyReadonlyArray3<'py, f32>,
        points: Vec<(f32, f32)>,
    ) -> Bound<'py, PyArray3<f32>> {
        let result = levels_curves::curves_f32(image.as_array(), &points);
        result.into_pyarray(py)
    }

    #[pyfunction]
    pub fn auto_levels<'py>(
        py: Python<'py>,
        image: PyReadonlyArray3<'py, u8>,
        clip_percent: f32,
    ) -> Bound<'py, PyArray3<u8>> {
        let result = levels_curves::auto_levels_u8(image.as_array(), clip_percent);
        result.into_pyarray(py)
    }

    #[pyfunction]
    pub fn auto_levels_f32<'py>(
        py: Python<'py>,
        image: PyReadonlyArray3<'py, f32>,
        clip_percent: f32,
    ) -> Bound<'py, PyArray3<f32>> {
        let result = levels_curves::auto_levels_f32(image.as_array(), clip_percent);
        result.into_pyarray(py)
    }

    // ========================================================================
    // Sharpen Filters
    // ========================================================================

    #[pyfunction]
    pub fn sharpen<'py>(
        py: Python<'py>,
        image: PyReadonlyArray3<'py, u8>,
        amount: f32,
    ) -> Bound<'py, PyArray3<u8>> {
        let result = sharpen_mod::sharpen_u8(image.as_array(), amount);
        result.into_pyarray(py)
    }

    #[pyfunction]
    pub fn sharpen_f32<'py>(
        py: Python<'py>,
        image: PyReadonlyArray3<'py, f32>,
        amount: f32,
    ) -> Bound<'py, PyArray3<f32>> {
        let result = sharpen_mod::sharpen_f32(image.as_array(), amount);
        result.into_pyarray(py)
    }

    #[pyfunction]
    pub fn unsharp_mask<'py>(
        py: Python<'py>,
        image: PyReadonlyArray3<'py, u8>,
        amount: f32,
        radius: f32,
        threshold_val: u8,
    ) -> Bound<'py, PyArray3<u8>> {
        let result = sharpen_mod::unsharp_mask_u8(image.as_array(), amount, radius, threshold_val);
        result.into_pyarray(py)
    }

    #[pyfunction]
    pub fn unsharp_mask_f32<'py>(
        py: Python<'py>,
        image: PyReadonlyArray3<'py, f32>,
        amount: f32,
        radius: f32,
        threshold_val: f32,
    ) -> Bound<'py, PyArray3<f32>> {
        let result = sharpen_mod::unsharp_mask_f32(image.as_array(), amount, radius, threshold_val);
        result.into_pyarray(py)
    }

    #[pyfunction]
    pub fn high_pass<'py>(
        py: Python<'py>,
        image: PyReadonlyArray3<'py, u8>,
        radius: f32,
    ) -> Bound<'py, PyArray3<u8>> {
        let result = sharpen_mod::high_pass_u8(image.as_array(), radius);
        result.into_pyarray(py)
    }

    #[pyfunction]
    pub fn high_pass_f32<'py>(
        py: Python<'py>,
        image: PyReadonlyArray3<'py, f32>,
        radius: f32,
    ) -> Bound<'py, PyArray3<f32>> {
        let result = sharpen_mod::high_pass_f32(image.as_array(), radius);
        result.into_pyarray(py)
    }

    #[pyfunction]
    pub fn motion_blur<'py>(
        py: Python<'py>,
        image: PyReadonlyArray3<'py, u8>,
        angle: f32,
        distance: f32,
    ) -> Bound<'py, PyArray3<u8>> {
        let result = sharpen_mod::motion_blur_u8(image.as_array(), angle, distance);
        result.into_pyarray(py)
    }

    #[pyfunction]
    pub fn motion_blur_f32<'py>(
        py: Python<'py>,
        image: PyReadonlyArray3<'py, f32>,
        angle: f32,
        distance: f32,
    ) -> Bound<'py, PyArray3<f32>> {
        let result = sharpen_mod::motion_blur_f32(image.as_array(), angle, distance);
        result.into_pyarray(py)
    }

    // ========================================================================
    // Edge Detection Filters
    // ========================================================================

    #[pyfunction]
    pub fn sobel<'py>(
        py: Python<'py>,
        image: PyReadonlyArray3<'py, u8>,
        direction: &str,
    ) -> Bound<'py, PyArray3<u8>> {
        let result = edge::sobel_u8(image.as_array(), direction);
        result.into_pyarray(py)
    }

    #[pyfunction]
    pub fn sobel_f32<'py>(
        py: Python<'py>,
        image: PyReadonlyArray3<'py, f32>,
        direction: &str,
    ) -> Bound<'py, PyArray3<f32>> {
        let result = edge::sobel_f32(image.as_array(), direction);
        result.into_pyarray(py)
    }

    #[pyfunction]
    pub fn laplacian<'py>(
        py: Python<'py>,
        image: PyReadonlyArray3<'py, u8>,
        kernel_size: u8,
    ) -> Bound<'py, PyArray3<u8>> {
        let result = edge::laplacian_u8(image.as_array(), kernel_size);
        result.into_pyarray(py)
    }

    #[pyfunction]
    pub fn laplacian_f32<'py>(
        py: Python<'py>,
        image: PyReadonlyArray3<'py, f32>,
        kernel_size: u8,
    ) -> Bound<'py, PyArray3<f32>> {
        let result = edge::laplacian_f32(image.as_array(), kernel_size);
        result.into_pyarray(py)
    }

    #[pyfunction]
    pub fn find_edges<'py>(
        py: Python<'py>,
        image: PyReadonlyArray3<'py, u8>,
    ) -> Bound<'py, PyArray3<u8>> {
        let result = edge::find_edges_u8(image.as_array());
        result.into_pyarray(py)
    }

    #[pyfunction]
    pub fn find_edges_f32<'py>(
        py: Python<'py>,
        image: PyReadonlyArray3<'py, f32>,
    ) -> Bound<'py, PyArray3<f32>> {
        let result = edge::find_edges_f32(image.as_array());
        result.into_pyarray(py)
    }

    // ========================================================================
    // Noise Filters
    // ========================================================================

    #[pyfunction]
    pub fn add_noise<'py>(
        py: Python<'py>,
        image: PyReadonlyArray3<'py, u8>,
        amount: f32,
        gaussian: bool,
        monochrome: bool,
        seed: u64,
    ) -> Bound<'py, PyArray3<u8>> {
        let result = noise_mod::add_noise_u8(image.as_array(), amount, gaussian, monochrome, seed);
        result.into_pyarray(py)
    }

    #[pyfunction]
    pub fn add_noise_f32<'py>(
        py: Python<'py>,
        image: PyReadonlyArray3<'py, f32>,
        amount: f32,
        gaussian: bool,
        monochrome: bool,
        seed: u64,
    ) -> Bound<'py, PyArray3<f32>> {
        let result = noise_mod::add_noise_f32(image.as_array(), amount, gaussian, monochrome, seed);
        result.into_pyarray(py)
    }

    #[pyfunction]
    pub fn median<'py>(
        py: Python<'py>,
        image: PyReadonlyArray3<'py, u8>,
        radius: u32,
    ) -> Bound<'py, PyArray3<u8>> {
        let result = noise_mod::median_u8(image.as_array(), radius);
        result.into_pyarray(py)
    }

    #[pyfunction]
    pub fn median_f32<'py>(
        py: Python<'py>,
        image: PyReadonlyArray3<'py, f32>,
        radius: u32,
    ) -> Bound<'py, PyArray3<f32>> {
        let result = noise_mod::median_f32(image.as_array(), radius);
        result.into_pyarray(py)
    }

    #[pyfunction]
    pub fn denoise<'py>(
        py: Python<'py>,
        image: PyReadonlyArray3<'py, u8>,
        strength: f32,
    ) -> Bound<'py, PyArray3<u8>> {
        let result = noise_mod::denoise_u8(image.as_array(), strength);
        result.into_pyarray(py)
    }

    #[pyfunction]
    pub fn denoise_f32<'py>(
        py: Python<'py>,
        image: PyReadonlyArray3<'py, f32>,
        strength: f32,
    ) -> Bound<'py, PyArray3<f32>> {
        let result = noise_mod::denoise_f32(image.as_array(), strength);
        result.into_pyarray(py)
    }

    // ========================================================================
    // Morphology Filters
    // ========================================================================

    #[pyfunction]
    pub fn dilate<'py>(
        py: Python<'py>,
        image: PyReadonlyArray3<'py, u8>,
        radius: f32,
    ) -> Bound<'py, PyArray3<u8>> {
        let result = morphology::dilate_u8(image.as_array(), radius);
        result.into_pyarray(py)
    }

    #[pyfunction]
    pub fn dilate_f32<'py>(
        py: Python<'py>,
        image: PyReadonlyArray3<'py, f32>,
        radius: f32,
    ) -> Bound<'py, PyArray3<f32>> {
        let result = morphology::dilate_f32(image.as_array(), radius);
        result.into_pyarray(py)
    }

    #[pyfunction]
    pub fn erode<'py>(
        py: Python<'py>,
        image: PyReadonlyArray3<'py, u8>,
        radius: f32,
    ) -> Bound<'py, PyArray3<u8>> {
        let result = morphology::erode_u8(image.as_array(), radius);
        result.into_pyarray(py)
    }

    #[pyfunction]
    pub fn erode_f32<'py>(
        py: Python<'py>,
        image: PyReadonlyArray3<'py, f32>,
        radius: f32,
    ) -> Bound<'py, PyArray3<f32>> {
        let result = morphology::erode_f32(image.as_array(), radius);
        result.into_pyarray(py)
    }

    /// ImageStag Rust extension module
    #[pymodule]
    pub fn imagestag_rust(m: &Bound<'_, PyModule>) -> PyResult<()> {
        // Basic operations
        m.add_function(wrap_pyfunction!(threshold_gray, m)?)?;
        m.add_function(wrap_pyfunction!(invert_rgba, m)?)?;
        m.add_function(wrap_pyfunction!(premultiply_alpha, m)?)?;
        m.add_function(wrap_pyfunction!(unpremultiply_alpha, m)?)?;

        // Grayscale filter (u8 and f32)
        m.add_function(wrap_pyfunction!(grayscale_rgba, m)?)?;
        m.add_function(wrap_pyfunction!(grayscale_rgba_f32, m)?)?;
        m.add_function(wrap_pyfunction!(grayscale_weighted, m)?)?;
        m.add_function(wrap_pyfunction!(grayscale_weighted_f32_py, m)?)?;

        // Conversion utilities
        m.add_function(wrap_pyfunction!(convert_u8_to_f32, m)?)?;
        m.add_function(wrap_pyfunction!(convert_f32_to_u8, m)?)?;
        m.add_function(wrap_pyfunction!(convert_f32_to_12bit, m)?)?;
        m.add_function(wrap_pyfunction!(convert_12bit_to_f32, m)?)?;

        // Color adjustment filters
        m.add_function(wrap_pyfunction!(brightness, m)?)?;
        m.add_function(wrap_pyfunction!(brightness_f32, m)?)?;
        m.add_function(wrap_pyfunction!(contrast, m)?)?;
        m.add_function(wrap_pyfunction!(contrast_f32, m)?)?;
        m.add_function(wrap_pyfunction!(saturation, m)?)?;
        m.add_function(wrap_pyfunction!(saturation_f32, m)?)?;
        m.add_function(wrap_pyfunction!(gamma, m)?)?;
        m.add_function(wrap_pyfunction!(gamma_f32, m)?)?;
        m.add_function(wrap_pyfunction!(exposure, m)?)?;
        m.add_function(wrap_pyfunction!(exposure_f32, m)?)?;
        m.add_function(wrap_pyfunction!(invert, m)?)?;
        m.add_function(wrap_pyfunction!(invert_f32, m)?)?;

        // Color science filters
        m.add_function(wrap_pyfunction!(hue_shift, m)?)?;
        m.add_function(wrap_pyfunction!(hue_shift_f32, m)?)?;
        m.add_function(wrap_pyfunction!(vibrance, m)?)?;
        m.add_function(wrap_pyfunction!(vibrance_f32, m)?)?;
        m.add_function(wrap_pyfunction!(color_balance, m)?)?;
        m.add_function(wrap_pyfunction!(color_balance_f32, m)?)?;

        // Stylize filters
        m.add_function(wrap_pyfunction!(posterize, m)?)?;
        m.add_function(wrap_pyfunction!(posterize_f32, m)?)?;
        m.add_function(wrap_pyfunction!(solarize, m)?)?;
        m.add_function(wrap_pyfunction!(solarize_f32, m)?)?;
        m.add_function(wrap_pyfunction!(threshold, m)?)?;
        m.add_function(wrap_pyfunction!(threshold_f32, m)?)?;
        m.add_function(wrap_pyfunction!(emboss, m)?)?;
        m.add_function(wrap_pyfunction!(emboss_f32, m)?)?;

        // Levels & curves filters
        m.add_function(wrap_pyfunction!(levels, m)?)?;
        m.add_function(wrap_pyfunction!(levels_f32, m)?)?;
        m.add_function(wrap_pyfunction!(curves, m)?)?;
        m.add_function(wrap_pyfunction!(curves_f32, m)?)?;
        m.add_function(wrap_pyfunction!(auto_levels, m)?)?;
        m.add_function(wrap_pyfunction!(auto_levels_f32, m)?)?;

        // Sharpen filters
        m.add_function(wrap_pyfunction!(sharpen, m)?)?;
        m.add_function(wrap_pyfunction!(sharpen_f32, m)?)?;
        m.add_function(wrap_pyfunction!(unsharp_mask, m)?)?;
        m.add_function(wrap_pyfunction!(unsharp_mask_f32, m)?)?;
        m.add_function(wrap_pyfunction!(high_pass, m)?)?;
        m.add_function(wrap_pyfunction!(high_pass_f32, m)?)?;
        m.add_function(wrap_pyfunction!(motion_blur, m)?)?;
        m.add_function(wrap_pyfunction!(motion_blur_f32, m)?)?;

        // Edge detection filters
        m.add_function(wrap_pyfunction!(sobel, m)?)?;
        m.add_function(wrap_pyfunction!(sobel_f32, m)?)?;
        m.add_function(wrap_pyfunction!(laplacian, m)?)?;
        m.add_function(wrap_pyfunction!(laplacian_f32, m)?)?;
        m.add_function(wrap_pyfunction!(find_edges, m)?)?;
        m.add_function(wrap_pyfunction!(find_edges_f32, m)?)?;

        // Noise filters
        m.add_function(wrap_pyfunction!(add_noise, m)?)?;
        m.add_function(wrap_pyfunction!(add_noise_f32, m)?)?;
        m.add_function(wrap_pyfunction!(median, m)?)?;
        m.add_function(wrap_pyfunction!(median_f32, m)?)?;
        m.add_function(wrap_pyfunction!(denoise, m)?)?;
        m.add_function(wrap_pyfunction!(denoise_f32, m)?)?;

        // Morphology filters
        m.add_function(wrap_pyfunction!(dilate, m)?)?;
        m.add_function(wrap_pyfunction!(dilate_f32, m)?)?;
        m.add_function(wrap_pyfunction!(erode, m)?)?;
        m.add_function(wrap_pyfunction!(erode_f32, m)?)?;

        // Blur filters
        m.add_function(wrap_pyfunction!(gaussian_blur_rgba, m)?)?;
        m.add_function(wrap_pyfunction!(box_blur_rgba, m)?)?;

        // Layer effects
        m.add_function(wrap_pyfunction!(drop_shadow_rgba, m)?)?;
        m.add_function(wrap_pyfunction!(drop_shadow_rgba_f32, m)?)?;
        m.add_function(wrap_pyfunction!(stroke_rgba, m)?)?;
        m.add_function(wrap_pyfunction!(stroke_rgba_f32, m)?)?;
        m.add_function(wrap_pyfunction!(bevel_emboss_rgba, m)?)?;
        m.add_function(wrap_pyfunction!(inner_glow_rgba, m)?)?;
        m.add_function(wrap_pyfunction!(outer_glow_rgba, m)?)?;
        m.add_function(wrap_pyfunction!(inner_shadow_rgba, m)?)?;
        m.add_function(wrap_pyfunction!(inner_shadow_rgba_f32, m)?)?;
        m.add_function(wrap_pyfunction!(color_overlay_rgba, m)?)?;
        m.add_function(wrap_pyfunction!(color_overlay_rgba_f32, m)?)?;

        // New layer effects (satin, gradient overlay, pattern overlay)
        m.add_function(wrap_pyfunction!(satin_rgba, m)?)?;
        m.add_function(wrap_pyfunction!(satin_rgba_f32, m)?)?;
        m.add_function(wrap_pyfunction!(gradient_overlay_rgba, m)?)?;
        m.add_function(wrap_pyfunction!(gradient_overlay_rgba_f32, m)?)?;
        m.add_function(wrap_pyfunction!(pattern_overlay_rgba, m)?)?;
        m.add_function(wrap_pyfunction!(pattern_overlay_rgba_f32, m)?)?;

        Ok(())
    }
}

#[cfg(feature = "python")]
pub use python::imagestag_rust;
