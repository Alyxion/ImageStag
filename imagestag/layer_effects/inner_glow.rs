//! Inner Glow layer effect.
//!
//! Creates a glow effect inside the shape edges.
//!
//! Co-located with:
//! - inner_glow.py (Python wrapper)
//! - inner_glow.js (JavaScript wrapper)

use ndarray::{Array2, Array3};
use numpy::{IntoPyArray, PyArray3, PyReadonlyArray3};
use pyo3::prelude::*;

use crate::filters::core::{blur_alpha_f32, erode_alpha};

/// Apply inner glow effect to RGBA image.
///
/// Creates a glow effect inside the shape edges.
///
/// # Arguments
/// * `image` - Source RGBA image
/// * `radius` - Glow blur radius
/// * `color` - Glow color (R, G, B)
/// * `opacity` - Glow opacity (0.0-1.0)
/// * `choke` - How much to contract the glow (0.0-1.0)
#[pyfunction]
#[pyo3(signature = (image, radius=10.0, color=(255, 255, 0), opacity=0.75, choke=0.0))]
pub fn inner_glow_rgba<'py>(
    py: Python<'py>,
    image: PyReadonlyArray3<'py, u8>,
    radius: f32,
    color: (u8, u8, u8),
    opacity: f32,
    choke: f32,
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

    // Create inner glow mask: erode alpha, blur, subtract from original
    let choke_radius = radius * choke;
    let eroded = if choke_radius > 0.0 {
        erode_alpha(&alpha, choke_radius)
    } else {
        alpha.clone()
    };

    // Blur the eroded alpha
    let blurred = blur_alpha_f32(&eroded, radius * (1.0 - choke * 0.5));

    // Inner glow = original alpha - blurred (inverted from edge)
    let mut glow_mask = Array2::<f32>::zeros((height, width));
    for y in 0..height {
        for x in 0..width {
            // Glow is strongest at edges, fading toward center
            let edge_dist = alpha[[y, x]] - blurred[[y, x]];
            glow_mask[[y, x]] = edge_dist.max(0.0) * alpha[[y, x]];
        }
    }

    // Compose result
    let mut result = Array3::<f32>::zeros((height, width, 4));

    // Copy original
    for y in 0..height {
        for x in 0..width {
            for c in 0..4 {
                result[[y, x, c]] = input_f32[[y, x, c]];
            }
        }
    }

    let glow_r = color.0 as f32 / 255.0;
    let glow_g = color.1 as f32 / 255.0;
    let glow_b = color.2 as f32 / 255.0;

    // Composite glow using "screen" blending (additive-like)
    for y in 0..height {
        for x in 0..width {
            let orig_a = input_f32[[y, x, 3]];
            if orig_a <= 0.0 {
                continue;
            }

            let glow_a = glow_mask[[y, x]] * opacity;
            if glow_a > 0.0 {
                // Screen blend: 1 - (1-a)(1-b)
                result[[y, x, 0]] = 1.0 - (1.0 - result[[y, x, 0]]) * (1.0 - glow_r * glow_a);
                result[[y, x, 1]] = 1.0 - (1.0 - result[[y, x, 1]]) * (1.0 - glow_g * glow_a);
                result[[y, x, 2]] = 1.0 - (1.0 - result[[y, x, 2]]) * (1.0 - glow_b * glow_a);
            }
        }
    }

    result.mapv(|v| (v.clamp(0.0, 1.0) * 255.0) as u8).into_pyarray(py)
}

/// Apply inner glow effect to f32 RGBA image.
#[pyfunction]
#[pyo3(signature = (image, radius=10.0, color=(1.0, 1.0, 0.0), opacity=0.75, choke=0.0))]
pub fn inner_glow_rgba_f32<'py>(
    py: Python<'py>,
    image: PyReadonlyArray3<'py, f32>,
    radius: f32,
    color: (f32, f32, f32),
    opacity: f32,
    choke: f32,
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

    let choke_radius = radius * choke;
    let eroded = if choke_radius > 0.0 {
        erode_alpha(&alpha, choke_radius)
    } else {
        alpha.clone()
    };

    let blurred = blur_alpha_f32(&eroded, radius * (1.0 - choke * 0.5));

    let mut glow_mask = Array2::<f32>::zeros((height, width));
    for y in 0..height {
        for x in 0..width {
            let edge_dist = alpha[[y, x]] - blurred[[y, x]];
            glow_mask[[y, x]] = edge_dist.max(0.0) * alpha[[y, x]];
        }
    }

    let mut result = Array3::<f32>::zeros((height, width, 4));

    for y in 0..height {
        for x in 0..width {
            for c in 0..4 {
                result[[y, x, c]] = input_f32[[y, x, c]];
            }
        }
    }

    for y in 0..height {
        for x in 0..width {
            let orig_a = input_f32[[y, x, 3]];
            if orig_a <= 0.0 {
                continue;
            }

            let glow_a = glow_mask[[y, x]] * opacity;
            if glow_a > 0.0 {
                result[[y, x, 0]] = 1.0 - (1.0 - result[[y, x, 0]]) * (1.0 - color.0 * glow_a);
                result[[y, x, 1]] = 1.0 - (1.0 - result[[y, x, 1]]) * (1.0 - color.1 * glow_a);
                result[[y, x, 2]] = 1.0 - (1.0 - result[[y, x, 2]]) * (1.0 - color.2 * glow_a);
            }
        }
    }

    result.into_pyarray(py)
}
