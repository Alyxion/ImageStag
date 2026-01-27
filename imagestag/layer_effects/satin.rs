//! Satin layer effect.
//!
//! Creates a silky, satiny interior shading by compositing shifted and blurred
//! copies of the layer alpha channel.

use ndarray::{Array2, Array3};
use numpy::{IntoPyArray, PyArray3, PyReadonlyArray3};
use pyo3::prelude::*;

use crate::filters::core::blur_alpha_f32;

/// Apply satin effect to RGBA u8 image.
///
/// Creates silky interior shading by:
/// 1. Creating two offset copies of the alpha (at +angle and -angle)
/// 2. Blurring both copies
/// 3. Computing the absolute difference
/// 4. Optionally inverting the result
/// 5. Masking with original alpha (only inside the shape)
///
/// # Arguments
/// * `image` - Source RGBA image
/// * `color` - Satin color (R, G, B), 0-255
/// * `opacity` - Effect opacity (0.0-1.0)
/// * `angle` - Direction angle in degrees
/// * `distance` - Offset distance in pixels
/// * `size` - Blur radius
/// * `invert` - Whether to invert the effect
#[pyfunction]
#[pyo3(signature = (image, color=(0, 0, 0), opacity=0.5, angle=19.0, distance=11.0, size=14.0, invert=false))]
pub fn satin_rgba<'py>(
    py: Python<'py>,
    image: PyReadonlyArray3<'py, u8>,
    color: (u8, u8, u8),
    opacity: f32,
    angle: f32,
    distance: f32,
    size: f32,
    invert: bool,
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

    // Calculate offset direction
    let angle_rad = angle.to_radians();
    let dx = (angle_rad.cos() * distance).round() as isize;
    let dy = (-angle_rad.sin() * distance).round() as isize;

    // Create offset copy A (positive direction)
    let mut offset_a = Array2::<f32>::zeros((height, width));
    for y in 0..height {
        for x in 0..width {
            let sx = (x as isize + dx).clamp(0, width as isize - 1) as usize;
            let sy = (y as isize + dy).clamp(0, height as isize - 1) as usize;
            offset_a[[y, x]] = alpha[[sy, sx]];
        }
    }

    // Create offset copy B (negative direction)
    let mut offset_b = Array2::<f32>::zeros((height, width));
    for y in 0..height {
        for x in 0..width {
            let sx = (x as isize - dx).clamp(0, width as isize - 1) as usize;
            let sy = (y as isize - dy).clamp(0, height as isize - 1) as usize;
            offset_b[[y, x]] = alpha[[sy, sx]];
        }
    }

    // Blur both copies
    let blurred_a = blur_alpha_f32(&offset_a, size);
    let blurred_b = blur_alpha_f32(&offset_b, size);

    // Compute satin mask: absolute difference
    let mut satin_mask = Array2::<f32>::zeros((height, width));
    for y in 0..height {
        for x in 0..width {
            let diff = (blurred_a[[y, x]] - blurred_b[[y, x]]).abs();
            // Apply inversion if requested
            let mask_val = if invert { 1.0 - diff } else { diff };
            // Mask with original alpha (only inside the shape)
            satin_mask[[y, x]] = mask_val * alpha[[y, x]];
        }
    }

    // Create result - start with original
    let mut result = input_f32.clone();

    let satin_r = color.0 as f32 / 255.0;
    let satin_g = color.1 as f32 / 255.0;
    let satin_b = color.2 as f32 / 255.0;

    // Apply satin effect using multiply-like blending
    for y in 0..height {
        for x in 0..width {
            let orig_a = alpha[[y, x]];
            if orig_a <= 0.0 {
                continue;
            }

            let satin_a = satin_mask[[y, x]] * opacity;
            if satin_a > 0.0 {
                // Blend satin color over original
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

    result.mapv(|v| (v.clamp(0.0, 1.0) * 255.0) as u8).into_pyarray(py)
}

/// Apply satin effect to RGBA f32 image.
///
/// Same as satin_rgba but for f32 images (0.0-1.0 range).
#[pyfunction]
#[pyo3(signature = (image, color=(0.0, 0.0, 0.0), opacity=0.5, angle=19.0, distance=11.0, size=14.0, invert=false))]
pub fn satin_rgba_f32<'py>(
    py: Python<'py>,
    image: PyReadonlyArray3<'py, f32>,
    color: (f32, f32, f32),
    opacity: f32,
    angle: f32,
    distance: f32,
    size: f32,
    invert: bool,
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

    // Calculate offset direction
    let angle_rad = angle.to_radians();
    let dx = (angle_rad.cos() * distance).round() as isize;
    let dy = (-angle_rad.sin() * distance).round() as isize;

    // Create offset copy A (positive direction)
    let mut offset_a = Array2::<f32>::zeros((height, width));
    for y in 0..height {
        for x in 0..width {
            let sx = (x as isize + dx).clamp(0, width as isize - 1) as usize;
            let sy = (y as isize + dy).clamp(0, height as isize - 1) as usize;
            offset_a[[y, x]] = alpha[[sy, sx]];
        }
    }

    // Create offset copy B (negative direction)
    let mut offset_b = Array2::<f32>::zeros((height, width));
    for y in 0..height {
        for x in 0..width {
            let sx = (x as isize - dx).clamp(0, width as isize - 1) as usize;
            let sy = (y as isize - dy).clamp(0, height as isize - 1) as usize;
            offset_b[[y, x]] = alpha[[sy, sx]];
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

    for y in 0..height {
        for x in 0..width {
            let orig_a = alpha[[y, x]];
            if orig_a <= 0.0 {
                continue;
            }

            let satin_a = satin_mask[[y, x]] * opacity;
            if satin_a > 0.0 {
                let out_a = satin_a + result[[y, x, 3]] * (1.0 - satin_a);
                if out_a > 0.0 {
                    result[[y, x, 0]] = (color.0 * satin_a + result[[y, x, 0]] * result[[y, x, 3]] * (1.0 - satin_a)) / out_a;
                    result[[y, x, 1]] = (color.1 * satin_a + result[[y, x, 1]] * result[[y, x, 3]] * (1.0 - satin_a)) / out_a;
                    result[[y, x, 2]] = (color.2 * satin_a + result[[y, x, 2]] * result[[y, x, 3]] * (1.0 - satin_a)) / out_a;
                    result[[y, x, 3]] = out_a;
                }
            }
        }
    }

    result.into_pyarray(py)
}
