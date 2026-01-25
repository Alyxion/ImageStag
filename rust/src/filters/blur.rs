//! Blur filters for RGBA images.
//!
//! Provides Gaussian and box blur implementations optimized
//! for RGBA images with proper alpha handling.
//!
//! ## Alpha Handling
//!
//! For RGBA images, all blur filters use **premultiplied alpha** processing:
//! 1. Convert to premultiplied: RGB *= alpha
//! 2. Apply blur to premultiplied RGB and alpha separately
//! 3. Convert back to straight alpha: RGB /= alpha
//!
//! This prevents transparent pixels (e.g., white with 0 alpha) from bleeding into
//! the blur result.

use ndarray::Array3;
use numpy::{IntoPyArray, PyArray3, PyReadonlyArray3};
use pyo3::prelude::*;

use super::core::gaussian_kernel_1d;

/// Apply Gaussian blur to RGBA image.
///
/// Uses separable 2-pass convolution for efficiency.
/// Uses premultiplied alpha to prevent transparent pixels from bleeding.
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
    let has_alpha = channels == 4;

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

    // Work in f32 for precision with premultiplied alpha for RGBA
    let mut temp = Array3::<f32>::zeros((height, width, channels));
    let mut result = Array3::<f32>::zeros((height, width, channels));

    // Horizontal pass
    for y in 0..height {
        for x in 0..width {
            if has_alpha {
                let mut sum_rgb = [0.0f32; 3];
                let mut sum_alpha = 0.0f32;

                for (ki, &kv) in kernel.iter().enumerate() {
                    let sx = (x as isize + ki as isize - half as isize)
                        .clamp(0, width as isize - 1) as usize;
                    let a = input[[y, sx, 3]] as f32 / 255.0;
                    sum_alpha += a * kv;
                    for c in 0..3 {
                        // Premultiplied: RGB * alpha
                        sum_rgb[c] += input[[y, sx, c]] as f32 * a * kv;
                    }
                }

                for c in 0..3 {
                    temp[[y, x, c]] = sum_rgb[c];
                }
                temp[[y, x, 3]] = sum_alpha;
            } else {
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
    }

    // Vertical pass
    for y in 0..height {
        for x in 0..width {
            if has_alpha {
                let mut sum_rgb = [0.0f32; 3];
                let mut sum_alpha = 0.0f32;

                for (ki, &kv) in kernel.iter().enumerate() {
                    let sy = (y as isize + ki as isize - half as isize)
                        .clamp(0, height as isize - 1) as usize;
                    sum_alpha += temp[[sy, x, 3]] * kv;
                    for c in 0..3 {
                        sum_rgb[c] += temp[[sy, x, c]] * kv;
                    }
                }

                // Unpremultiply
                let final_alpha = sum_alpha.clamp(0.0, 1.0);
                result[[y, x, 3]] = final_alpha * 255.0;

                if final_alpha > 0.001 {
                    for c in 0..3 {
                        let unpremultiplied = sum_rgb[c] / final_alpha;
                        result[[y, x, c]] = unpremultiplied.clamp(0.0, 255.0);
                    }
                } else {
                    for c in 0..3 {
                        result[[y, x, c]] = 0.0;
                    }
                }
            } else {
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
    }

    // Convert back to u8
    result.mapv(|v| v.clamp(0.0, 255.0) as u8).into_pyarray(py)
}

/// Apply box blur to RGBA image.
///
/// Faster than Gaussian blur but produces a blockier result.
/// Uses premultiplied alpha to prevent transparent pixels from bleeding.
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
    let has_alpha = channels == 4;

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

    // Box blur with premultiplied alpha for RGBA
    for y in 0..height {
        for x in 0..width {
            if has_alpha {
                let mut sum_rgb = [0.0f32; 3];
                let mut sum_alpha = 0.0f32;
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

                        let sy = sy as usize;
                        let sx = sx as usize;
                        let a = input[[sy, sx, 3]] as f32 / 255.0;
                        sum_alpha += a;
                        for c in 0..3 {
                            // Premultiplied: RGB * alpha
                            sum_rgb[c] += input[[sy, sx, c]] as f32 * a;
                        }
                        count += 1;
                    }
                }

                // Average and unpremultiply
                let final_alpha = (sum_alpha / count as f32).clamp(0.0, 1.0);
                result[[y, x, 3]] = (final_alpha * 255.0) as u8;

                if final_alpha > 0.001 {
                    for c in 0..3 {
                        let avg_premultiplied = sum_rgb[c] / count as f32;
                        let unpremultiplied = avg_premultiplied / final_alpha;
                        result[[y, x, c]] = unpremultiplied.clamp(0.0, 255.0) as u8;
                    }
                } else {
                    for c in 0..3 {
                        result[[y, x, c]] = 0;
                    }
                }
            } else {
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
    }

    result.into_pyarray(py)
}
