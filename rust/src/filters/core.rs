//! Core utilities for image processing filters.
//!
//! This module provides shared functionality used by multiple filters:
//! - Gaussian kernel generation
//! - Distance field computation
//! - Color blending utilities
//! - Coordinate transformation helpers

use ndarray::{Array1, Array2, Array3, ArrayView3, Axis};
use rayon::prelude::*;

/// Generate a 1D Gaussian kernel.
///
/// # Arguments
/// * `sigma` - Standard deviation of the Gaussian
///
/// # Returns
/// Normalized 1D kernel as Vec<f32>
pub fn gaussian_kernel_1d(sigma: f32) -> Vec<f32> {
    if sigma <= 0.0 {
        return vec![1.0];
    }

    // Kernel size = 6 sigma (covers 99.7% of distribution), ensure odd
    let kernel_size = ((sigma * 6.0).ceil() as usize) | 1;
    let half = kernel_size / 2;

    let mut kernel: Vec<f32> = (0..kernel_size)
        .map(|i| {
            let x = i as f32 - half as f32;
            (-x * x / (2.0 * sigma * sigma)).exp()
        })
        .collect();

    // Normalize
    let sum: f32 = kernel.iter().sum();
    for v in kernel.iter_mut() {
        *v /= sum;
    }

    kernel
}

/// Generate a 2D Gaussian kernel.
///
/// # Arguments
/// * `sigma` - Standard deviation of the Gaussian
///
/// # Returns
/// Normalized 2D kernel as Array2<f32>
pub fn gaussian_kernel_2d(sigma: f32) -> Array2<f32> {
    let k1d = gaussian_kernel_1d(sigma);
    let size = k1d.len();

    let mut kernel = Array2::<f32>::zeros((size, size));
    for y in 0..size {
        for x in 0..size {
            kernel[[y, x]] = k1d[y] * k1d[x];
        }
    }

    kernel
}

/// Apply separable 1D Gaussian blur to alpha channel.
///
/// This is optimized for blurring just the alpha channel,
/// used extensively in shadow and glow effects.
///
/// # Arguments
/// * `alpha` - 2D array of alpha values (u8 or f32)
/// * `sigma` - Blur radius (standard deviation)
///
/// # Returns
/// Blurred alpha channel
pub fn blur_alpha_u8(alpha: &Array2<u8>, sigma: f32) -> Array2<u8> {
    let (height, width) = (alpha.shape()[0], alpha.shape()[1]);
    let kernel = gaussian_kernel_1d(sigma);
    let half = kernel.len() / 2;

    // Convert to f32 for precision during blur
    let mut temp = Array2::<f32>::zeros((height, width));
    let mut result = Array2::<f32>::zeros((height, width));

    // Horizontal pass
    for y in 0..height {
        for x in 0..width {
            let mut sum = 0.0f32;
            for (ki, &kv) in kernel.iter().enumerate() {
                let sx = (x as isize + ki as isize - half as isize)
                    .clamp(0, width as isize - 1) as usize;
                sum += alpha[[y, sx]] as f32 * kv;
            }
            temp[[y, x]] = sum;
        }
    }

    // Vertical pass
    for y in 0..height {
        for x in 0..width {
            let mut sum = 0.0f32;
            for (ki, &kv) in kernel.iter().enumerate() {
                let sy = (y as isize + ki as isize - half as isize)
                    .clamp(0, height as isize - 1) as usize;
                sum += temp[[sy, x]] * kv;
            }
            result[[y, x]] = sum;
        }
    }

    // Convert back to u8
    result.mapv(|v| v.clamp(0.0, 255.0) as u8)
}

/// Apply separable 1D Gaussian blur to f32 alpha channel.
pub fn blur_alpha_f32(alpha: &Array2<f32>, sigma: f32) -> Array2<f32> {
    let (height, width) = (alpha.shape()[0], alpha.shape()[1]);
    let kernel = gaussian_kernel_1d(sigma);
    let half = kernel.len() / 2;

    let mut temp = Array2::<f32>::zeros((height, width));
    let mut result = Array2::<f32>::zeros((height, width));

    // Horizontal pass
    for y in 0..height {
        for x in 0..width {
            let mut sum = 0.0f32;
            for (ki, &kv) in kernel.iter().enumerate() {
                let sx = (x as isize + ki as isize - half as isize)
                    .clamp(0, width as isize - 1) as usize;
                sum += alpha[[y, sx]] * kv;
            }
            temp[[y, x]] = sum;
        }
    }

    // Vertical pass
    for y in 0..height {
        for x in 0..width {
            let mut sum = 0.0f32;
            for (ki, &kv) in kernel.iter().enumerate() {
                let sy = (y as isize + ki as isize - half as isize)
                    .clamp(0, height as isize - 1) as usize;
                sum += temp[[sy, x]] * kv;
            }
            result[[y, x]] = sum;
        }
    }

    result.mapv(|v| v.clamp(0.0, 1.0))
}

/// Compute signed distance field from alpha channel.
///
/// Positive values are outside the shape, negative inside.
/// Used for stroke, bevel, and other distance-based effects.
///
/// # Arguments
/// * `alpha` - Binary or anti-aliased alpha channel
/// * `max_distance` - Maximum distance to compute
///
/// # Returns
/// Signed distance field as f32 array
pub fn compute_sdf(alpha: &Array2<f32>, max_distance: f32) -> Array2<f32> {
    let (height, width) = (alpha.shape()[0], alpha.shape()[1]);
    let max_dist_sq = max_distance * max_distance;

    // Simple brute-force SDF for small distances
    // For large distances, use jump flooding or other optimized algorithms
    let mut sdf = Array2::<f32>::zeros((height, width));

    let search_radius = (max_distance.ceil() as usize) + 1;

    for y in 0..height {
        for x in 0..width {
            let inside = alpha[[y, x]] > 0.5;
            let mut min_dist_sq = max_dist_sq;

            // Search neighborhood for edge
            for dy in -(search_radius as isize)..=(search_radius as isize) {
                let sy = y as isize + dy;
                if sy < 0 || sy >= height as isize {
                    continue;
                }

                for dx in -(search_radius as isize)..=(search_radius as isize) {
                    let sx = x as isize + dx;
                    if sx < 0 || sx >= width as isize {
                        continue;
                    }

                    let neighbor_inside = alpha[[sy as usize, sx as usize]] > 0.5;
                    if neighbor_inside != inside {
                        let dist_sq = (dx * dx + dy * dy) as f32;
                        min_dist_sq = min_dist_sq.min(dist_sq);
                    }
                }
            }

            let dist = min_dist_sq.sqrt();
            sdf[[y, x]] = if inside { -dist } else { dist };
        }
    }

    sdf
}

/// Dilate alpha channel by given radius.
///
/// Uses a circular structuring element for anti-aliased results.
pub fn dilate_alpha(alpha: &Array2<f32>, radius: f32) -> Array2<f32> {
    let (height, width) = (alpha.shape()[0], alpha.shape()[1]);
    let mut result = Array2::<f32>::zeros((height, width));

    let r_ceil = radius.ceil() as isize;
    let r_sq = radius * radius;

    for y in 0..height {
        for x in 0..width {
            let mut max_val = 0.0f32;

            for dy in -r_ceil..=r_ceil {
                let sy = y as isize + dy;
                if sy < 0 || sy >= height as isize {
                    continue;
                }

                for dx in -r_ceil..=r_ceil {
                    let sx = x as isize + dx;
                    if sx < 0 || sx >= width as isize {
                        continue;
                    }

                    let dist_sq = (dx * dx + dy * dy) as f32;
                    if dist_sq <= r_sq {
                        // Anti-aliased contribution based on distance
                        let edge_dist = radius - dist_sq.sqrt();
                        let contribution = if edge_dist >= 1.0 {
                            alpha[[sy as usize, sx as usize]]
                        } else if edge_dist > 0.0 {
                            alpha[[sy as usize, sx as usize]] * edge_dist
                        } else {
                            0.0
                        };
                        max_val = max_val.max(contribution);
                    }
                }
            }

            result[[y, x]] = max_val;
        }
    }

    result
}

/// Erode alpha channel by given radius.
pub fn erode_alpha(alpha: &Array2<f32>, radius: f32) -> Array2<f32> {
    let (height, width) = (alpha.shape()[0], alpha.shape()[1]);
    let mut result = Array2::<f32>::zeros((height, width));

    let r_ceil = radius.ceil() as isize;
    let r_sq = radius * radius;

    for y in 0..height {
        for x in 0..width {
            let mut min_val = 1.0f32;

            for dy in -r_ceil..=r_ceil {
                let sy = y as isize + dy;
                if sy < 0 || sy >= height as isize {
                    min_val = 0.0;
                    continue;
                }

                for dx in -r_ceil..=r_ceil {
                    let sx = x as isize + dx;
                    if sx < 0 || sx >= width as isize {
                        min_val = 0.0;
                        continue;
                    }

                    let dist_sq = (dx * dx + dy * dy) as f32;
                    if dist_sq <= r_sq {
                        min_val = min_val.min(alpha[[sy as usize, sx as usize]]);
                    }
                }
            }

            result[[y, x]] = min_val;
        }
    }

    result
}

/// Blend color onto existing pixel using alpha.
///
/// Uses Porter-Duff "over" compositing.
#[inline]
pub fn blend_over_u8(
    dst: &mut [u8; 4],
    src_r: u8,
    src_g: u8,
    src_b: u8,
    src_a: u8,
) {
    if src_a == 0 {
        return;
    }
    if src_a == 255 {
        dst[0] = src_r;
        dst[1] = src_g;
        dst[2] = src_b;
        dst[3] = 255;
        return;
    }

    let src_af = src_a as f32 / 255.0;
    let dst_af = dst[3] as f32 / 255.0;
    let out_a = src_af + dst_af * (1.0 - src_af);

    if out_a > 0.0 {
        dst[0] = ((src_r as f32 * src_af + dst[0] as f32 * dst_af * (1.0 - src_af)) / out_a) as u8;
        dst[1] = ((src_g as f32 * src_af + dst[1] as f32 * dst_af * (1.0 - src_af)) / out_a) as u8;
        dst[2] = ((src_b as f32 * src_af + dst[2] as f32 * dst_af * (1.0 - src_af)) / out_a) as u8;
        dst[3] = (out_a * 255.0) as u8;
    }
}

/// Blend color onto existing pixel using alpha (f32 version).
#[inline]
pub fn blend_over_f32(
    dst: &mut [f32; 4],
    src_r: f32,
    src_g: f32,
    src_b: f32,
    src_a: f32,
) {
    if src_a <= 0.0 {
        return;
    }
    if src_a >= 1.0 {
        dst[0] = src_r;
        dst[1] = src_g;
        dst[2] = src_b;
        dst[3] = 1.0;
        return;
    }

    let out_a = src_a + dst[3] * (1.0 - src_a);

    if out_a > 0.0 {
        dst[0] = (src_r * src_a + dst[0] * dst[3] * (1.0 - src_a)) / out_a;
        dst[1] = (src_g * src_a + dst[1] * dst[3] * (1.0 - src_a)) / out_a;
        dst[2] = (src_b * src_a + dst[2] * dst[3] * (1.0 - src_a)) / out_a;
        dst[3] = out_a;
    }
}

/// Extract alpha channel from RGBA image.
pub fn extract_alpha_u8(image: &Array3<u8>) -> Array2<u8> {
    let (h, w, _) = (image.shape()[0], image.shape()[1], image.shape()[2]);
    let mut alpha = Array2::<u8>::zeros((h, w));
    for y in 0..h {
        for x in 0..w {
            alpha[[y, x]] = image[[y, x, 3]];
        }
    }
    alpha
}

/// Extract alpha channel from RGBA f32 image.
pub fn extract_alpha_f32(image: &Array3<f32>) -> Array2<f32> {
    let (h, w, _) = (image.shape()[0], image.shape()[1], image.shape()[2]);
    let mut alpha = Array2::<f32>::zeros((h, w));
    for y in 0..h {
        for x in 0..w {
            alpha[[y, x]] = image[[y, x, 3]];
        }
    }
    alpha
}

/// Convert u8 alpha to f32 (0-255 -> 0.0-1.0).
pub fn alpha_u8_to_f32(alpha: &Array2<u8>) -> Array2<f32> {
    alpha.mapv(|v| v as f32 / 255.0)
}

/// Convert f32 alpha to u8 (0.0-1.0 -> 0-255).
pub fn alpha_f32_to_u8(alpha: &Array2<f32>) -> Array2<u8> {
    alpha.mapv(|v| (v.clamp(0.0, 1.0) * 255.0) as u8)
}

/// Expand canvas by adding padding around the image.
///
/// # Arguments
/// * `image` - Original RGBA image
/// * `expand` - Pixels to add on each side
///
/// # Returns
/// Expanded image with transparent padding
pub fn expand_canvas_u8(image: &Array3<u8>, expand: usize) -> Array3<u8> {
    let (h, w, c) = (image.shape()[0], image.shape()[1], image.shape()[2]);
    let new_h = h + expand * 2;
    let new_w = w + expand * 2;

    let mut result = Array3::<u8>::zeros((new_h, new_w, c));

    for y in 0..h {
        for x in 0..w {
            for ch in 0..c {
                result[[y + expand, x + expand, ch]] = image[[y, x, ch]];
            }
        }
    }

    result
}

/// Expand canvas for f32 images.
pub fn expand_canvas_f32(image: &Array3<f32>, expand: usize) -> Array3<f32> {
    let (h, w, c) = (image.shape()[0], image.shape()[1], image.shape()[2]);
    let new_h = h + expand * 2;
    let new_w = w + expand * 2;

    let mut result = Array3::<f32>::zeros((new_h, new_w, c));

    for y in 0..h {
        for x in 0..w {
            for ch in 0..c {
                result[[y + expand, x + expand, ch]] = image[[y, x, ch]];
            }
        }
    }

    result
}
