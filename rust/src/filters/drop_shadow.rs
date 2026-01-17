//! Drop shadow filter for layer effects.
//!
//! Creates a shadow effect by:
//! 1. Extracting the alpha channel
//! 2. Blurring it with Gaussian kernel
//! 3. Offsetting the shadow
//! 4. Colorizing with shadow color
//! 5. Compositing original on top
//!
//! Anti-aliasing is preserved through all operations.

use ndarray::{Array2, Array3};
use numpy::{IntoPyArray, PyArray3, PyReadonlyArray3};
use pyo3::prelude::*;

use super::core::{blur_alpha_f32, expand_canvas_f32, alpha_u8_to_f32};

/// Apply drop shadow effect to RGBA image.
///
/// # Arguments
/// * `image` - Source RGBA image (height, width, 4) as u8
/// * `offset_x` - Horizontal shadow offset (positive = right)
/// * `offset_y` - Vertical shadow offset (positive = down)
/// * `blur_radius` - Shadow blur radius (sigma for Gaussian)
/// * `color` - Shadow color as (R, G, B) tuple (0-255)
/// * `opacity` - Shadow opacity (0.0-1.0)
/// * `expand` - Extra pixels to add around image for shadow overflow
///
/// # Returns
/// RGBA image with drop shadow, potentially larger than input
#[pyfunction]
#[pyo3(signature = (image, offset_x=4.0, offset_y=4.0, blur_radius=5.0, color=(0, 0, 0), opacity=0.75, expand=0))]
pub fn drop_shadow_rgba<'py>(
    py: Python<'py>,
    image: PyReadonlyArray3<'py, u8>,
    offset_x: f32,
    offset_y: f32,
    blur_radius: f32,
    color: (u8, u8, u8),
    opacity: f32,
    expand: usize,
) -> Bound<'py, PyArray3<u8>> {
    let input = image.as_array();
    let (height, width, _) = (input.shape()[0], input.shape()[1], input.shape()[2]);

    // Convert to f32 for processing
    let mut input_f32 = Array3::<f32>::zeros((height, width, 4));
    for y in 0..height {
        for x in 0..width {
            input_f32[[y, x, 0]] = input[[y, x, 0]] as f32 / 255.0;
            input_f32[[y, x, 1]] = input[[y, x, 1]] as f32 / 255.0;
            input_f32[[y, x, 2]] = input[[y, x, 2]] as f32 / 255.0;
            input_f32[[y, x, 3]] = input[[y, x, 3]] as f32 / 255.0;
        }
    }

    // Calculate required expansion based on offset and blur
    let required_expand = if expand > 0 {
        expand
    } else {
        let blur_expand = (blur_radius * 3.0).ceil() as usize;
        let offset_expand = offset_x.abs().max(offset_y.abs()).ceil() as usize;
        blur_expand + offset_expand + 2
    };

    // Expand canvas if needed
    let expanded = if required_expand > 0 {
        expand_canvas_f32(&input_f32, required_expand)
    } else {
        input_f32.clone()
    };

    let (new_h, new_w, _) = (expanded.shape()[0], expanded.shape()[1], expanded.shape()[2]);

    // Extract alpha channel
    let mut alpha = Array2::<f32>::zeros((new_h, new_w));
    for y in 0..new_h {
        for x in 0..new_w {
            alpha[[y, x]] = expanded[[y, x, 3]];
        }
    }

    // Blur the alpha channel
    let blurred_alpha = blur_alpha_f32(&alpha, blur_radius);

    // Create result with shadow
    let mut result = Array3::<f32>::zeros((new_h, new_w, 4));

    let shadow_r = color.0 as f32 / 255.0;
    let shadow_g = color.1 as f32 / 255.0;
    let shadow_b = color.2 as f32 / 255.0;

    // Draw shadow (offset and colorized)
    let ox = offset_x.round() as isize;
    let oy = offset_y.round() as isize;

    for y in 0..new_h {
        for x in 0..new_w {
            // Sample shadow alpha from offset position
            let sx = (x as isize - ox).clamp(0, new_w as isize - 1) as usize;
            let sy = (y as isize - oy).clamp(0, new_h as isize - 1) as usize;

            let shadow_a = blurred_alpha[[sy, sx]] * opacity;

            result[[y, x, 0]] = shadow_r;
            result[[y, x, 1]] = shadow_g;
            result[[y, x, 2]] = shadow_b;
            result[[y, x, 3]] = shadow_a;
        }
    }

    // Composite original image on top using Porter-Duff "over"
    for y in 0..new_h {
        for x in 0..new_w {
            let src_a = expanded[[y, x, 3]];
            if src_a <= 0.0 {
                continue;
            }

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

    // Convert back to u8
    result.mapv(|v| (v.clamp(0.0, 1.0) * 255.0) as u8).into_pyarray(py)
}

/// Apply drop shadow effect to f32 RGBA image.
///
/// Same as drop_shadow_rgba but for f32 input/output (0.0-1.0 range).
#[pyfunction]
#[pyo3(signature = (image, offset_x=4.0, offset_y=4.0, blur_radius=5.0, color=(0.0, 0.0, 0.0), opacity=0.75, expand=0))]
pub fn drop_shadow_rgba_f32<'py>(
    py: Python<'py>,
    image: PyReadonlyArray3<'py, f32>,
    offset_x: f32,
    offset_y: f32,
    blur_radius: f32,
    color: (f32, f32, f32),
    opacity: f32,
    expand: usize,
) -> Bound<'py, PyArray3<f32>> {
    let input = image.as_array();
    let (height, width, _) = (input.shape()[0], input.shape()[1], input.shape()[2]);

    // Clone input for processing
    let mut input_f32 = Array3::<f32>::zeros((height, width, 4));
    for y in 0..height {
        for x in 0..width {
            for c in 0..4 {
                input_f32[[y, x, c]] = input[[y, x, c]];
            }
        }
    }

    // Calculate required expansion
    let required_expand = if expand > 0 {
        expand
    } else {
        let blur_expand = (blur_radius * 3.0).ceil() as usize;
        let offset_expand = offset_x.abs().max(offset_y.abs()).ceil() as usize;
        blur_expand + offset_expand + 2
    };

    // Expand canvas if needed
    let expanded = if required_expand > 0 {
        expand_canvas_f32(&input_f32, required_expand)
    } else {
        input_f32
    };

    let (new_h, new_w, _) = (expanded.shape()[0], expanded.shape()[1], expanded.shape()[2]);

    // Extract alpha channel
    let mut alpha = Array2::<f32>::zeros((new_h, new_w));
    for y in 0..new_h {
        for x in 0..new_w {
            alpha[[y, x]] = expanded[[y, x, 3]];
        }
    }

    // Blur the alpha channel
    let blurred_alpha = blur_alpha_f32(&alpha, blur_radius);

    // Create result with shadow
    let mut result = Array3::<f32>::zeros((new_h, new_w, 4));

    // Draw shadow (offset and colorized)
    let ox = offset_x.round() as isize;
    let oy = offset_y.round() as isize;

    for y in 0..new_h {
        for x in 0..new_w {
            let sx = (x as isize - ox).clamp(0, new_w as isize - 1) as usize;
            let sy = (y as isize - oy).clamp(0, new_h as isize - 1) as usize;

            let shadow_a = blurred_alpha[[sy, sx]] * opacity;

            result[[y, x, 0]] = color.0;
            result[[y, x, 1]] = color.1;
            result[[y, x, 2]] = color.2;
            result[[y, x, 3]] = shadow_a;
        }
    }

    // Composite original image on top
    for y in 0..new_h {
        for x in 0..new_w {
            let src_a = expanded[[y, x, 3]];
            if src_a <= 0.0 {
                continue;
            }

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

    result.into_pyarray(py)
}
