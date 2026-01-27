//! Inner Shadow layer effect.
//!
//! Creates a shadow inside the shape edges.
//!
//! Co-located with:
//! - inner_shadow.py (Python wrapper)
//! - inner_shadow.js (JavaScript wrapper)

use ndarray::{Array2, Array3};
use numpy::{IntoPyArray, PyArray3, PyReadonlyArray3};
use pyo3::prelude::*;

use crate::filters::core::{blur_alpha_f32, dilate_alpha};

/// Apply inner shadow effect to RGBA image.
///
/// Creates a shadow inside the shape edges by:
/// 1. Inverting the alpha (shadow is where content isn't)
/// 2. Blurring the inverted alpha
/// 3. Offsetting the shadow
/// 4. Masking with original alpha (shadow only visible inside shape)
///
/// # Arguments
/// * `image` - Source RGBA image
/// * `offset_x` - Horizontal shadow offset
/// * `offset_y` - Vertical shadow offset
/// * `blur_radius` - Shadow blur radius
/// * `choke` - How much to contract before blur (0.0-1.0)
/// * `color` - Shadow color (R, G, B)
/// * `opacity` - Shadow opacity (0.0-1.0)
#[pyfunction]
#[pyo3(signature = (image, offset_x=2.0, offset_y=2.0, blur_radius=5.0, choke=0.0, color=(0, 0, 0), opacity=0.75))]
pub fn inner_shadow_rgba<'py>(
    py: Python<'py>,
    image: PyReadonlyArray3<'py, u8>,
    offset_x: f32,
    offset_y: f32,
    blur_radius: f32,
    choke: f32,
    color: (u8, u8, u8),
    opacity: f32,
) -> Bound<'py, PyArray3<u8>> {
    let input = image.as_array();
    let (height, width, _) = (input.shape()[0], input.shape()[1], input.shape()[2]);

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

    // Invert alpha for inner shadow (shadow comes from outside)
    let mut inverted = Array2::<f32>::zeros((height, width));
    for y in 0..height {
        for x in 0..width {
            inverted[[y, x]] = 1.0 - alpha[[y, x]];
        }
    }

    // Apply choke (erode the inverted alpha, which expands the shadow)
    let choke_radius = blur_radius * choke;
    let choked = if choke_radius > 0.0 {
        dilate_alpha(&inverted, choke_radius)
    } else {
        inverted
    };

    // Blur the shadow
    let blurred = blur_alpha_f32(&choked, blur_radius);

    // Create result - start with original
    let mut result = input_f32.clone();

    let shadow_r = color.0 as f32 / 255.0;
    let shadow_g = color.1 as f32 / 255.0;
    let shadow_b = color.2 as f32 / 255.0;

    let ox = offset_x.round() as isize;
    let oy = offset_y.round() as isize;

    // Apply shadow inside the shape
    for y in 0..height {
        for x in 0..width {
            let orig_a = alpha[[y, x]];
            if orig_a <= 0.0 {
                continue;
            }

            // Sample shadow alpha from offset position
            let sx = (x as isize - ox).clamp(0, width as isize - 1) as usize;
            let sy = (y as isize - oy).clamp(0, height as isize - 1) as usize;

            // Shadow is visible where blurred inverted alpha is > 0 AND inside original shape
            let shadow_a = blurred[[sy, sx]] * opacity * orig_a;

            if shadow_a > 0.0 {
                // Blend shadow color over original
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

    result.mapv(|v| (v.clamp(0.0, 1.0) * 255.0) as u8).into_pyarray(py)
}

/// Apply inner shadow effect to f32 RGBA image.
#[pyfunction]
#[pyo3(signature = (image, offset_x=2.0, offset_y=2.0, blur_radius=5.0, choke=0.0, color=(0.0, 0.0, 0.0), opacity=0.75))]
pub fn inner_shadow_rgba_f32<'py>(
    py: Python<'py>,
    image: PyReadonlyArray3<'py, f32>,
    offset_x: f32,
    offset_y: f32,
    blur_radius: f32,
    choke: f32,
    color: (f32, f32, f32),
    opacity: f32,
) -> Bound<'py, PyArray3<f32>> {
    let input = image.as_array();
    let (height, width, _) = (input.shape()[0], input.shape()[1], input.shape()[2]);

    // Clone input
    let mut input_f32 = Array3::<f32>::zeros((height, width, 4));
    for y in 0..height {
        for x in 0..width {
            for c in 0..4 {
                input_f32[[y, x, c]] = input[[y, x, c]];
            }
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

    let ox = offset_x.round() as isize;
    let oy = offset_y.round() as isize;

    for y in 0..height {
        for x in 0..width {
            let orig_a = alpha[[y, x]];
            if orig_a <= 0.0 {
                continue;
            }

            let sx = (x as isize - ox).clamp(0, width as isize - 1) as usize;
            let sy = (y as isize - oy).clamp(0, height as isize - 1) as usize;

            let shadow_a = blurred[[sy, sx]] * opacity * orig_a;

            if shadow_a > 0.0 {
                let out_a = shadow_a + result[[y, x, 3]] * (1.0 - shadow_a);
                if out_a > 0.0 {
                    result[[y, x, 0]] = (color.0 * shadow_a + result[[y, x, 0]] * result[[y, x, 3]] * (1.0 - shadow_a)) / out_a;
                    result[[y, x, 1]] = (color.1 * shadow_a + result[[y, x, 1]] * result[[y, x, 3]] * (1.0 - shadow_a)) / out_a;
                    result[[y, x, 2]] = (color.2 * shadow_a + result[[y, x, 2]] * result[[y, x, 3]] * (1.0 - shadow_a)) / out_a;
                    result[[y, x, 3]] = out_a;
                }
            }
        }
    }

    result.into_pyarray(py)
}
