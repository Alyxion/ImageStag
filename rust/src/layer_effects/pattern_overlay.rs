//! Pattern overlay layer effect.
//!
//! Fills the layer with a repeating pattern while preserving the alpha channel.

use ndarray::Array3;
use numpy::{IntoPyArray, PyArray3, PyReadonlyArray3};
use pyo3::prelude::*;

/// Sample a pixel from a pattern with tiling (modulo wrapping).
#[inline]
fn sample_pattern_tiled(
    pattern: &Array3<f32>,
    x: isize,
    y: isize,
    pattern_w: usize,
    pattern_h: usize,
) -> (f32, f32, f32, f32) {
    // Modulo wrap for tiling
    let px = ((x % pattern_w as isize) + pattern_w as isize) as usize % pattern_w;
    let py = ((y % pattern_h as isize) + pattern_h as isize) as usize % pattern_h;

    let r = pattern[[py, px, 0]];
    let g = pattern[[py, px, 1]];
    let b = pattern[[py, px, 2]];
    let a = if pattern.shape()[2] > 3 { pattern[[py, px, 3]] } else { 1.0 };

    (r, g, b, a)
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
/// # Arguments
/// * `image` - Source RGBA image
/// * `pattern` - Pattern RGBA image to tile
/// * `scale` - Pattern scale factor (1.0 = 100%)
/// * `offset_x` - Horizontal offset for pattern origin
/// * `offset_y` - Vertical offset for pattern origin
/// * `opacity` - Effect opacity (0.0-1.0)
#[pyfunction]
#[pyo3(signature = (image, pattern, scale=1.0, offset_x=0, offset_y=0, opacity=1.0))]
pub fn pattern_overlay_rgba<'py>(
    py: Python<'py>,
    image: PyReadonlyArray3<'py, u8>,
    pattern: PyReadonlyArray3<'py, u8>,
    scale: f32,
    offset_x: i32,
    offset_y: i32,
    opacity: f32,
) -> Bound<'py, PyArray3<u8>> {
    let input = image.as_array();
    let pat = pattern.as_array();
    let (height, width, _) = (input.shape()[0], input.shape()[1], input.shape()[2]);
    let (pattern_h, pattern_w, pattern_c) = (pat.shape()[0], pat.shape()[1], pat.shape()[2]);

    // Convert pattern to f32
    let mut pattern_f32 = Array3::<f32>::zeros((pattern_h, pattern_w, pattern_c));
    for y in 0..pattern_h {
        for x in 0..pattern_w {
            for c in 0..pattern_c {
                pattern_f32[[y, x, c]] = pat[[y, x, c]] as f32 / 255.0;
            }
        }
    }

    let mut result = Array3::<u8>::zeros((height, width, 4));

    // Effective scale (clamped to valid range)
    let effective_scale = scale.clamp(0.01, 100.0);

    for y in 0..height {
        for x in 0..width {
            let orig_a = input[[y, x, 3]];
            if orig_a == 0 {
                continue;
            }

            // Calculate pattern coordinates with scale and offset
            let px = (x as f32 / effective_scale) + offset_x as f32;
            let py = (y as f32 / effective_scale) + offset_y as f32;

            // Sample pattern (with bilinear interpolation for smooth scaling)
            let (pat_r, pat_g, pat_b, pat_a) = if effective_scale == 1.0 {
                sample_pattern_tiled(&pattern_f32, px.round() as isize, py.round() as isize, pattern_w, pattern_h)
            } else {
                sample_pattern_bilinear(&pattern_f32, px, py, pattern_w, pattern_h)
            };

            // Blend with original based on opacity and pattern alpha
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
            result[[y, x, 3]] = orig_a; // Preserve alpha
        }
    }

    result.into_pyarray(py)
}

/// Apply pattern overlay to RGBA f32 image.
///
/// Same as pattern_overlay_rgba but for f32 images (0.0-1.0 range).
#[pyfunction]
#[pyo3(signature = (image, pattern, scale=1.0, offset_x=0, offset_y=0, opacity=1.0))]
pub fn pattern_overlay_rgba_f32<'py>(
    py: Python<'py>,
    image: PyReadonlyArray3<'py, f32>,
    pattern: PyReadonlyArray3<'py, f32>,
    scale: f32,
    offset_x: i32,
    offset_y: i32,
    opacity: f32,
) -> Bound<'py, PyArray3<f32>> {
    let input = image.as_array();
    let pat = pattern.as_array();
    let (height, width, _) = (input.shape()[0], input.shape()[1], input.shape()[2]);
    let (pattern_h, pattern_w, pattern_c) = (pat.shape()[0], pat.shape()[1], pat.shape()[2]);

    // Copy pattern to owned array for sampling
    let mut pattern_f32 = Array3::<f32>::zeros((pattern_h, pattern_w, pattern_c));
    for y in 0..pattern_h {
        for x in 0..pattern_w {
            for c in 0..pattern_c {
                pattern_f32[[y, x, c]] = pat[[y, x, c]];
            }
        }
    }

    let mut result = Array3::<f32>::zeros((height, width, 4));

    let effective_scale = scale.clamp(0.01, 100.0);

    for y in 0..height {
        for x in 0..width {
            let orig_a = input[[y, x, 3]];
            if orig_a <= 0.0 {
                continue;
            }

            // Calculate pattern coordinates with scale and offset
            let px = (x as f32 / effective_scale) + offset_x as f32;
            let py = (y as f32 / effective_scale) + offset_y as f32;

            // Sample pattern
            let (pat_r, pat_g, pat_b, pat_a) = if effective_scale == 1.0 {
                sample_pattern_tiled(&pattern_f32, px.round() as isize, py.round() as isize, pattern_w, pattern_h)
            } else {
                sample_pattern_bilinear(&pattern_f32, px, py, pattern_w, pattern_h)
            };

            // Blend with original based on opacity and pattern alpha
            let blend_a = opacity * pat_a;

            let final_r = input[[y, x, 0]] * (1.0 - blend_a) + pat_r * blend_a;
            let final_g = input[[y, x, 1]] * (1.0 - blend_a) + pat_g * blend_a;
            let final_b = input[[y, x, 2]] * (1.0 - blend_a) + pat_b * blend_a;

            result[[y, x, 0]] = final_r;
            result[[y, x, 1]] = final_g;
            result[[y, x, 2]] = final_b;
            result[[y, x, 3]] = orig_a; // Preserve alpha
        }
    }

    result.into_pyarray(py)
}
