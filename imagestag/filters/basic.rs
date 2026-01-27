//! Basic image processing operations.
//!
//! Simple pixel-wise operations that don't require spatial context:
//! - Threshold
//! - Invert
//! - Alpha premultiplication

use ndarray::{Array2, Array3};
use numpy::{IntoPyArray, PyArray2, PyArray3, PyReadonlyArray2, PyReadonlyArray3};
use pyo3::prelude::*;

/// Apply binary threshold to grayscale image.
///
/// # Arguments
/// * `image` - 2D grayscale image (u8)
/// * `threshold` - Threshold value (0-255)
///
/// # Returns
/// Binary image where pixels >= threshold become 255, others become 0
#[pyfunction]
pub fn threshold_gray<'py>(
    py: Python<'py>,
    image: PyReadonlyArray2<'py, u8>,
    threshold: u8,
) -> Bound<'py, PyArray2<u8>> {
    let input = image.as_array();
    let (height, width) = (input.shape()[0], input.shape()[1]);

    let mut result = Array2::<u8>::zeros((height, width));

    for y in 0..height {
        for x in 0..width {
            result[[y, x]] = if input[[y, x]] >= threshold { 255 } else { 0 };
        }
    }

    result.into_pyarray(py)
}

/// Invert colors in RGBA image.
///
/// Inverts RGB channels, preserves alpha.
#[pyfunction]
pub fn invert_rgba<'py>(
    py: Python<'py>,
    image: PyReadonlyArray3<'py, u8>,
) -> Bound<'py, PyArray3<u8>> {
    let input = image.as_array();
    let (height, width, channels) = (input.shape()[0], input.shape()[1], input.shape()[2]);

    let mut result = Array3::<u8>::zeros((height, width, channels));

    for y in 0..height {
        for x in 0..width {
            result[[y, x, 0]] = 255 - input[[y, x, 0]]; // R
            result[[y, x, 1]] = 255 - input[[y, x, 1]]; // G
            result[[y, x, 2]] = 255 - input[[y, x, 2]]; // B
            result[[y, x, 3]] = input[[y, x, 3]];       // A unchanged
        }
    }

    result.into_pyarray(py)
}

/// Premultiply alpha in RGBA image.
///
/// Converts from straight alpha to premultiplied alpha:
/// RGB_out = RGB_in * A / 255
///
/// This is useful for compositing operations.
#[pyfunction]
pub fn premultiply_alpha<'py>(
    py: Python<'py>,
    image: PyReadonlyArray3<'py, u8>,
) -> Bound<'py, PyArray3<u8>> {
    let input = image.as_array();
    let (height, width, channels) = (input.shape()[0], input.shape()[1], input.shape()[2]);

    let mut result = Array3::<u8>::zeros((height, width, channels));

    for y in 0..height {
        for x in 0..width {
            let a = input[[y, x, 3]] as u16;
            if a == 0 {
                // Fully transparent - zero everything
                result[[y, x, 0]] = 0;
                result[[y, x, 1]] = 0;
                result[[y, x, 2]] = 0;
                result[[y, x, 3]] = 0;
            } else if a == 255 {
                // Fully opaque - copy as-is
                result[[y, x, 0]] = input[[y, x, 0]];
                result[[y, x, 1]] = input[[y, x, 1]];
                result[[y, x, 2]] = input[[y, x, 2]];
                result[[y, x, 3]] = 255;
            } else {
                // Partial alpha - multiply RGB
                result[[y, x, 0]] = ((input[[y, x, 0]] as u16 * a) / 255) as u8;
                result[[y, x, 1]] = ((input[[y, x, 1]] as u16 * a) / 255) as u8;
                result[[y, x, 2]] = ((input[[y, x, 2]] as u16 * a) / 255) as u8;
                result[[y, x, 3]] = input[[y, x, 3]];
            }
        }
    }

    result.into_pyarray(py)
}

/// Unpremultiply alpha in RGBA image.
///
/// Converts from premultiplied alpha back to straight alpha:
/// RGB_out = RGB_in * 255 / A
///
/// This is needed before saving to formats that expect straight alpha.
#[pyfunction]
pub fn unpremultiply_alpha<'py>(
    py: Python<'py>,
    image: PyReadonlyArray3<'py, u8>,
) -> Bound<'py, PyArray3<u8>> {
    let input = image.as_array();
    let (height, width, channels) = (input.shape()[0], input.shape()[1], input.shape()[2]);

    let mut result = Array3::<u8>::zeros((height, width, channels));

    for y in 0..height {
        for x in 0..width {
            let a = input[[y, x, 3]] as u16;
            if a == 0 {
                // Fully transparent - zero everything
                result[[y, x, 0]] = 0;
                result[[y, x, 1]] = 0;
                result[[y, x, 2]] = 0;
                result[[y, x, 3]] = 0;
            } else if a == 255 {
                // Fully opaque - copy as-is
                result[[y, x, 0]] = input[[y, x, 0]];
                result[[y, x, 1]] = input[[y, x, 1]];
                result[[y, x, 2]] = input[[y, x, 2]];
                result[[y, x, 3]] = 255;
            } else {
                // Partial alpha - divide RGB
                result[[y, x, 0]] = ((input[[y, x, 0]] as u16 * 255) / a).min(255) as u8;
                result[[y, x, 1]] = ((input[[y, x, 1]] as u16 * 255) / a).min(255) as u8;
                result[[y, x, 2]] = ((input[[y, x, 2]] as u16 * 255) / a).min(255) as u8;
                result[[y, x, 3]] = input[[y, x, 3]];
            }
        }
    }

    result.into_pyarray(py)
}
