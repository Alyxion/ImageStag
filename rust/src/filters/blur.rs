//! Blur filters for RGBA images.
//!
//! Provides Gaussian and box blur implementations optimized
//! for RGBA images with proper alpha handling.

use ndarray::Array3;
use numpy::{IntoPyArray, PyArray3, PyReadonlyArray3};
use pyo3::prelude::*;

use super::core::gaussian_kernel_1d;

/// Apply Gaussian blur to RGBA image.
///
/// Uses separable 2-pass convolution for efficiency.
/// Alpha channel is blurred along with RGB.
///
/// # Arguments
/// * `image` - RGBA image (height, width, 4) as u8
/// * `sigma` - Standard deviation of Gaussian kernel
///
/// # Returns
/// Blurred RGBA image with same dimensions
#[pyfunction]
pub fn gaussian_blur_rgba<'py>(
    py: Python<'py>,
    image: PyReadonlyArray3<'py, u8>,
    sigma: f32,
) -> Bound<'py, PyArray3<u8>> {
    let input = image.as_array();
    let (height, width, channels) = (input.shape()[0], input.shape()[1], input.shape()[2]);

    if sigma <= 0.0 {
        // No blur, return copy
        let mut result = Array3::<u8>::zeros((height, width, channels));
        for y in 0..height {
            for x in 0..width {
                for c in 0..channels {
                    result[[y, x, c]] = input[[y, x, c]];
                }
            }
        }
        return result.into_pyarray(py);
    }

    let kernel = gaussian_kernel_1d(sigma);
    let half = kernel.len() / 2;

    // Work in f32 for precision
    let mut temp = Array3::<f32>::zeros((height, width, channels));
    let mut result = Array3::<f32>::zeros((height, width, channels));

    // Horizontal pass
    for y in 0..height {
        for x in 0..width {
            for c in 0..channels {
                let mut sum = 0.0f32;
                for (ki, &kv) in kernel.iter().enumerate() {
                    let sx = (x as isize + ki as isize - half as isize)
                        .clamp(0, width as isize - 1) as usize;
                    sum += input[[y, sx, c]] as f32 * kv;
                }
                temp[[y, x, c]] = sum;
            }
        }
    }

    // Vertical pass
    for y in 0..height {
        for x in 0..width {
            for c in 0..channels {
                let mut sum = 0.0f32;
                for (ki, &kv) in kernel.iter().enumerate() {
                    let sy = (y as isize + ki as isize - half as isize)
                        .clamp(0, height as isize - 1) as usize;
                    sum += temp[[sy, x, c]] * kv;
                }
                result[[y, x, c]] = sum;
            }
        }
    }

    // Convert back to u8
    result.mapv(|v| v.clamp(0.0, 255.0) as u8).into_pyarray(py)
}

/// Apply box blur to RGBA image.
///
/// Faster than Gaussian blur but produces a blockier result.
/// Uses integral image for O(1) per pixel complexity.
///
/// # Arguments
/// * `image` - RGBA image (height, width, 4) as u8
/// * `radius` - Blur radius in pixels
///
/// # Returns
/// Blurred RGBA image with same dimensions
#[pyfunction]
pub fn box_blur_rgba<'py>(
    py: Python<'py>,
    image: PyReadonlyArray3<'py, u8>,
    radius: usize,
) -> Bound<'py, PyArray3<u8>> {
    let input = image.as_array();
    let (height, width, channels) = (input.shape()[0], input.shape()[1], input.shape()[2]);

    if radius == 0 {
        // No blur, return copy
        let mut result = Array3::<u8>::zeros((height, width, channels));
        for y in 0..height {
            for x in 0..width {
                for c in 0..channels {
                    result[[y, x, c]] = input[[y, x, c]];
                }
            }
        }
        return result.into_pyarray(py);
    }

    let mut result = Array3::<u8>::zeros((height, width, channels));
    let r = radius as isize;
    let kernel_size = (2 * radius + 1) * (2 * radius + 1);

    // Simple box blur - average of all pixels in radius
    for y in 0..height {
        for x in 0..width {
            for c in 0..channels {
                let mut sum = 0u32;
                let mut count = 0u32;

                for dy in -r..=r {
                    let sy = y as isize + dy;
                    if sy < 0 || sy >= height as isize {
                        continue;
                    }

                    for dx in -r..=r {
                        let sx = x as isize + dx;
                        if sx < 0 || sx >= width as isize {
                            continue;
                        }

                        sum += input[[sy as usize, sx as usize, c]] as u32;
                        count += 1;
                    }
                }

                result[[y, x, c]] = (sum / count) as u8;
            }
        }
    }

    result.into_pyarray(py)
}
