//! Outer Glow layer effect.
//!
//! Creates a glow effect outside the shape edges.
//!
//! Co-located with:
//! - outer_glow.py (Python wrapper)
//! - outer_glow.js (JavaScript wrapper)

use ndarray::{Array2, Array3};
use numpy::{IntoPyArray, PyArray3, PyReadonlyArray3};
use pyo3::prelude::*;

use crate::filters::core::{blur_alpha_f32, dilate_alpha, expand_canvas_f32};

/// Apply outer glow effect to RGBA image.
///
/// Creates a glow effect outside the shape edges.
///
/// # Arguments
/// * `image` - Source RGBA image
/// * `radius` - Glow blur radius
/// * `color` - Glow color (R, G, B)
/// * `opacity` - Glow opacity (0.0-1.0)
/// * `spread` - How much to expand the glow before blur (0.0-1.0)
/// * `expand` - Extra pixels to add around image
#[pyfunction]
#[pyo3(signature = (image, radius=10.0, color=(255, 255, 0), opacity=0.75, spread=0.0, expand=0))]
pub fn outer_glow_rgba<'py>(
    py: Python<'py>,
    image: PyReadonlyArray3<'py, u8>,
    radius: f32,
    color: (u8, u8, u8),
    opacity: f32,
    spread: f32,
    expand: usize,
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

    // Calculate expansion
    let required_expand = if expand > 0 {
        expand
    } else {
        (radius * 3.0).ceil() as usize + 2
    };

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

    // Blur the alpha
    let blurred = blur_alpha_f32(&spread_alpha, radius);

    // Create result with glow
    let mut result = Array3::<f32>::zeros((new_h, new_w, 4));

    let glow_r = color.0 as f32 / 255.0;
    let glow_g = color.1 as f32 / 255.0;
    let glow_b = color.2 as f32 / 255.0;

    // Draw glow first (outside only)
    for y in 0..new_h {
        for x in 0..new_w {
            // Glow is the blurred alpha minus original (outside only)
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

    result.mapv(|v| (v.clamp(0.0, 1.0) * 255.0) as u8).into_pyarray(py)
}

/// Apply outer glow effect to f32 RGBA image.
#[pyfunction]
#[pyo3(signature = (image, radius=10.0, color=(1.0, 1.0, 0.0), opacity=0.75, spread=0.0, expand=0))]
pub fn outer_glow_rgba_f32<'py>(
    py: Python<'py>,
    image: PyReadonlyArray3<'py, f32>,
    radius: f32,
    color: (f32, f32, f32),
    opacity: f32,
    spread: f32,
    expand: usize,
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

    let required_expand = if expand > 0 {
        expand
    } else {
        (radius * 3.0).ceil() as usize + 2
    };

    let expanded = expand_canvas_f32(&input_f32, required_expand);
    let (new_h, new_w, _) = (expanded.shape()[0], expanded.shape()[1], expanded.shape()[2]);

    let mut alpha = Array2::<f32>::zeros((new_h, new_w));
    for y in 0..new_h {
        for x in 0..new_w {
            alpha[[y, x]] = expanded[[y, x, 3]];
        }
    }

    let spread_radius = radius * spread;
    let spread_alpha = if spread_radius > 0.0 {
        dilate_alpha(&alpha, spread_radius)
    } else {
        alpha.clone()
    };

    let blurred = blur_alpha_f32(&spread_alpha, radius);

    let mut result = Array3::<f32>::zeros((new_h, new_w, 4));

    for y in 0..new_h {
        for x in 0..new_w {
            let glow_a = (blurred[[y, x]] - alpha[[y, x]]).max(0.0) * opacity;
            if glow_a > 0.0 {
                result[[y, x, 0]] = color.0;
                result[[y, x, 1]] = color.1;
                result[[y, x, 2]] = color.2;
                result[[y, x, 3]] = glow_a;
            }
        }
    }

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

/// Get glow-only layer (no compositing with original, full glow including under object).
///
/// Returns just the glow effect without the original image composited on top.
/// Unlike outer_glow_rgba which subtracts the original alpha, this returns the
/// FULL glow as if the object wasn't there, useful for baked SVG export.
///
/// # Arguments
/// Same as outer_glow_rgba
///
/// # Returns
/// RGBA image with ONLY the glow (original NOT composited on top, full glow area)
#[pyfunction]
#[pyo3(signature = (image, radius=10.0, color=(255, 255, 0), opacity=0.75, spread=0.0, expand=0))]
pub fn outer_glow_only_rgba<'py>(
    py: Python<'py>,
    image: PyReadonlyArray3<'py, u8>,
    radius: f32,
    color: (u8, u8, u8),
    opacity: f32,
    spread: f32,
    expand: usize,
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

    // Calculate expansion
    let required_expand = if expand > 0 {
        expand
    } else {
        (radius * 3.0).ceil() as usize + 2
    };

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

    // Blur the alpha - this is the FULL glow
    let blurred = blur_alpha_f32(&spread_alpha, radius);

    // Create glow-only result (no compositing with original)
    let mut result = Array3::<f32>::zeros((new_h, new_w, 4));

    let glow_r = color.0 as f32 / 255.0;
    let glow_g = color.1 as f32 / 255.0;
    let glow_b = color.2 as f32 / 255.0;

    // Draw FULL glow (not subtracting original alpha)
    for y in 0..new_h {
        for x in 0..new_w {
            let glow_a = blurred[[y, x]] * opacity;
            result[[y, x, 0]] = glow_r;
            result[[y, x, 1]] = glow_g;
            result[[y, x, 2]] = glow_b;
            result[[y, x, 3]] = glow_a;
        }
    }

    // NOTE: No compositing step - return glow layer only

    result.mapv(|v| (v.clamp(0.0, 1.0) * 255.0) as u8).into_pyarray(py)
}

/// Get glow-only layer for f32 RGBA image (no compositing with original).
#[pyfunction]
#[pyo3(signature = (image, radius=10.0, color=(1.0, 1.0, 0.0), opacity=0.75, spread=0.0, expand=0))]
pub fn outer_glow_only_rgba_f32<'py>(
    py: Python<'py>,
    image: PyReadonlyArray3<'py, f32>,
    radius: f32,
    color: (f32, f32, f32),
    opacity: f32,
    spread: f32,
    expand: usize,
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

    let required_expand = if expand > 0 {
        expand
    } else {
        (radius * 3.0).ceil() as usize + 2
    };

    let expanded = expand_canvas_f32(&input_f32, required_expand);
    let (new_h, new_w, _) = (expanded.shape()[0], expanded.shape()[1], expanded.shape()[2]);

    let mut alpha = Array2::<f32>::zeros((new_h, new_w));
    for y in 0..new_h {
        for x in 0..new_w {
            alpha[[y, x]] = expanded[[y, x, 3]];
        }
    }

    let spread_radius = radius * spread;
    let spread_alpha = if spread_radius > 0.0 {
        dilate_alpha(&alpha, spread_radius)
    } else {
        alpha.clone()
    };

    // Blur the alpha - this is the FULL glow
    let blurred = blur_alpha_f32(&spread_alpha, radius);

    // Create glow-only result (no compositing with original)
    let mut result = Array3::<f32>::zeros((new_h, new_w, 4));

    // Draw FULL glow (not subtracting original alpha)
    for y in 0..new_h {
        for x in 0..new_w {
            let glow_a = blurred[[y, x]] * opacity;
            result[[y, x, 0]] = color.0;
            result[[y, x, 1]] = color.1;
            result[[y, x, 2]] = color.2;
            result[[y, x, 3]] = glow_a;
        }
    }

    // NOTE: No compositing step - return glow layer only

    result.into_pyarray(py)
}
