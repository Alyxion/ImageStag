//! Color Overlay layer effect.
//!
//! Replaces all colors with a solid color while preserving alpha.
//!
//! Co-located with:
//! - color_overlay.py (Python wrapper)
//! - color_overlay.js (JavaScript wrapper)

use ndarray::Array3;
use numpy::{IntoPyArray, PyArray3, PyReadonlyArray3};
use pyo3::prelude::*;

/// Apply color overlay effect to RGBA image.
///
/// Replaces all colors with a solid color while preserving alpha.
///
/// # Arguments
/// * `image` - Source RGBA image
/// * `color` - Overlay color (R, G, B)
/// * `opacity` - Overlay opacity (0.0-1.0)
#[pyfunction]
#[pyo3(signature = (image, color=(255, 0, 0), opacity=1.0))]
pub fn color_overlay_rgba<'py>(
    py: Python<'py>,
    image: PyReadonlyArray3<'py, u8>,
    color: (u8, u8, u8),
    opacity: f32,
) -> Bound<'py, PyArray3<u8>> {
    let input = image.as_array();
    let (height, width, _) = (input.shape()[0], input.shape()[1], input.shape()[2]);

    let mut result = Array3::<u8>::zeros((height, width, 4));

    for y in 0..height {
        for x in 0..width {
            let orig_a = input[[y, x, 3]] as f32 / 255.0;
            if orig_a <= 0.0 {
                continue;
            }

            // Blend overlay color with original based on opacity
            let blend_a = opacity;
            let orig_r = input[[y, x, 0]] as f32 / 255.0;
            let orig_g = input[[y, x, 1]] as f32 / 255.0;
            let orig_b = input[[y, x, 2]] as f32 / 255.0;
            let overlay_r = color.0 as f32 / 255.0;
            let overlay_g = color.1 as f32 / 255.0;
            let overlay_b = color.2 as f32 / 255.0;

            // Linear blend between original and overlay color
            let final_r = orig_r * (1.0 - blend_a) + overlay_r * blend_a;
            let final_g = orig_g * (1.0 - blend_a) + overlay_g * blend_a;
            let final_b = orig_b * (1.0 - blend_a) + overlay_b * blend_a;

            result[[y, x, 0]] = (final_r * 255.0) as u8;
            result[[y, x, 1]] = (final_g * 255.0) as u8;
            result[[y, x, 2]] = (final_b * 255.0) as u8;
            result[[y, x, 3]] = input[[y, x, 3]]; // Preserve alpha
        }
    }

    result.into_pyarray(py)
}

/// Apply color overlay effect to f32 RGBA image.
#[pyfunction]
#[pyo3(signature = (image, color=(1.0, 0.0, 0.0), opacity=1.0))]
pub fn color_overlay_rgba_f32<'py>(
    py: Python<'py>,
    image: PyReadonlyArray3<'py, f32>,
    color: (f32, f32, f32),
    opacity: f32,
) -> Bound<'py, PyArray3<f32>> {
    let input = image.as_array();
    let (height, width, _) = (input.shape()[0], input.shape()[1], input.shape()[2]);

    let mut result = Array3::<f32>::zeros((height, width, 4));

    for y in 0..height {
        for x in 0..width {
            let orig_a = input[[y, x, 3]];
            if orig_a <= 0.0 {
                continue;
            }

            let blend_a = opacity;

            result[[y, x, 0]] = input[[y, x, 0]] * (1.0 - blend_a) + color.0 * blend_a;
            result[[y, x, 1]] = input[[y, x, 1]] * (1.0 - blend_a) + color.1 * blend_a;
            result[[y, x, 2]] = input[[y, x, 2]] * (1.0 - blend_a) + color.2 * blend_a;
            result[[y, x, 3]] = orig_a;
        }
    }

    result.into_pyarray(py)
}
