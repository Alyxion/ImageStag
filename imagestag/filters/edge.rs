//! Edge detection filters: Sobel, Laplacian, Find Edges.
//!
//! These filters detect and highlight edges in images.
//! All filters support both u8 (0-255) and f32 (0.0-1.0) modes.
//! Implementations match skimage.filters behavior exactly.
//!
//! ## Supported Formats
//!
//! All filters accept images with 1, 3, or 4 channels:
//! - **Grayscale**: (height, width, 1) - uses single channel directly
//! - **RGB**: (height, width, 3) - computes luminance from RGB
//! - **RGBA**: (height, width, 4) - computes luminance from RGB, preserves alpha
//!
//! Output is always grayscale (same value for all color channels).

use ndarray::{Array3, ArrayView3};

// Luminosity coefficients (matching skimage.color.rgb2gray exactly)
const LUMA_R: f32 = 0.2125;
const LUMA_G: f32 = 0.7154;
const LUMA_B: f32 = 0.0721;

// f64 versions for high-precision edge detection
const LUMA_R_F64: f64 = 0.2125;
const LUMA_G_F64: f64 = 0.7154;
const LUMA_B_F64: f64 = 0.0721;

/// Get luminance from pixel (normalized to 0-1) with reflect padding at borders
#[inline]
fn get_lum_u8_reflect(input: &ArrayView3<u8>, y: i32, x: i32, height: usize, width: usize, channels: usize) -> f32 {
    // Reflect mode: (d c b a | a b c d | d c b a)
    let ry = reflect_index(y, height);
    let rx = reflect_index(x, width);

    if channels == 1 {
        input[[ry, rx, 0]] as f32 / 255.0
    } else {
        let r = input[[ry, rx, 0]] as f32 / 255.0;
        let g = input[[ry, rx, 1]] as f32 / 255.0;
        let b = input[[ry, rx, 2]] as f32 / 255.0;
        LUMA_R * r + LUMA_G * g + LUMA_B * b
    }
}

/// Reflect index for border handling (matches scipy 'reflect' mode)
#[inline]
fn reflect_index(i: i32, size: usize) -> usize {
    let s = size as i32;
    if i < 0 {
        (-i - 1).rem_euclid(s) as usize
    } else if i >= s {
        (2 * s - i - 1).rem_euclid(s) as usize
    } else {
        i as usize
    }
}

/// Get luminance from pixel (normalized to 0-1)
#[inline]
fn get_lum_u8(input: &ArrayView3<u8>, y: usize, x: usize, channels: usize) -> f32 {
    if channels == 1 {
        input[[y, x, 0]] as f32 / 255.0
    } else {
        let r = input[[y, x, 0]] as f32 / 255.0;
        let g = input[[y, x, 1]] as f32 / 255.0;
        let b = input[[y, x, 2]] as f32 / 255.0;
        LUMA_R * r + LUMA_G * g + LUMA_B * b
    }
}

#[inline]
fn get_lum_f32(input: &ArrayView3<f32>, y: usize, x: usize, channels: usize) -> f32 {
    if channels == 1 {
        input[[y, x, 0]]
    } else {
        LUMA_R * input[[y, x, 0]] + LUMA_G * input[[y, x, 1]] + LUMA_B * input[[y, x, 2]]
    }
}

/// Get luminance from pixel (f32) with reflect padding at borders
#[inline]
fn get_lum_f32_reflect(input: &ArrayView3<f32>, y: i32, x: i32, height: usize, width: usize, channels: usize) -> f32 {
    let ry = reflect_index(y, height);
    let rx = reflect_index(x, width);

    if channels == 1 {
        input[[ry, rx, 0]]
    } else {
        LUMA_R * input[[ry, rx, 0]] + LUMA_G * input[[ry, rx, 1]] + LUMA_B * input[[ry, rx, 2]]
    }
}

/// Get alpha from pixel (u8, normalized to 0-1) with reflect padding at borders
#[inline]
fn get_alpha_u8_reflect(input: &ArrayView3<u8>, y: i32, x: i32, height: usize, width: usize) -> f32 {
    let ry = reflect_index(y, height);
    let rx = reflect_index(x, width);
    input[[ry, rx, 3]] as f32 / 255.0
}

/// Get alpha from pixel (u8, normalized to 0-1)
#[inline]
fn get_alpha_u8(input: &ArrayView3<u8>, y: usize, x: usize) -> f32 {
    input[[y, x, 3]] as f32 / 255.0
}

/// Get alpha from pixel (f32) with reflect padding at borders
#[inline]
fn get_alpha_f32_reflect(input: &ArrayView3<f32>, y: i32, x: i32, height: usize, width: usize) -> f32 {
    let ry = reflect_index(y, height);
    let rx = reflect_index(x, width);
    input[[ry, rx, 3]]
}

/// Get alpha from pixel (f32)
#[inline]
fn get_alpha_f32(input: &ArrayView3<f32>, y: usize, x: usize) -> f32 {
    input[[y, x, 3]]
}

// ============================================================================
// Sobel Edge Detection
// ============================================================================

/// Build separable Sobel kernels for a given kernel size.
///
/// The smooth weights are obtained by repeated convolution of [1, 1]:
/// - size 3: [1, 2, 1] / 4
/// - size 5: [1, 4, 6, 4, 1] / 16
/// - size 7: [1, 6, 15, 20, 15, 6, 1] / 64
///
/// The edge weights are [1, 0, -1] (always 3-tap).
/// The combined kernel is the outer product of smooth × edge.
fn build_sobel_kernels(kernel_size: u8) -> (Vec<Vec<f32>>, Vec<Vec<f32>>) {
    let ks = kernel_size.max(3) as usize;
    // Ensure odd
    let ks = if ks % 2 == 0 { ks + 1 } else { ks };

    // Build smooth weights via repeated convolution of [1, 1]
    let mut smooth = vec![1.0f32; 1];
    for _ in 0..(ks - 1) {
        let mut next = vec![0.0f32; smooth.len() + 1];
        for (i, &s) in smooth.iter().enumerate() {
            next[i] += s;
            next[i + 1] += s;
        }
        smooth = next;
    }
    // Normalize smooth weights
    let smooth_sum: f32 = smooth.iter().sum();
    for s in smooth.iter_mut() {
        *s /= smooth_sum;
    }

    // Edge weights are always [1, 0, -1]
    let edge = vec![1.0f32, 0.0, -1.0];

    // kernel_h detects horizontal edges (gradient in y direction):
    // outer product of edge (vertical) × smooth (horizontal)
    let mut kernel_h = vec![vec![0.0f32; ks]; ks];
    // kernel_v detects vertical edges (gradient in x direction):
    // outer product of smooth (vertical) × edge (horizontal)
    let mut kernel_v = vec![vec![0.0f32; ks]; ks];

    let half = (ks as i32 - 1) / 2;
    for row in 0..ks {
        for col in 0..ks {
            // For kernel_h: rows use edge (3-tap centered), cols use smooth
            let edge_idx = row as i32 - half;
            if edge_idx >= -1 && edge_idx <= 1 {
                kernel_h[row][col] = edge[(edge_idx + 1) as usize] * smooth[col];
            }
            // For kernel_v: rows use smooth, cols use edge (3-tap centered)
            let edge_idx_c = col as i32 - half;
            if edge_idx_c >= -1 && edge_idx_c <= 1 {
                kernel_v[row][col] = smooth[row] * edge[(edge_idx_c + 1) as usize];
            }
        }
    }

    (kernel_h, kernel_v)
}

/// Apply Sobel edge detection - u8 version.
///
/// Uses skimage.filters.sobel kernels exactly for kernel_size=3:
/// - sobel_h: [[0.25, 0.5, 0.25], [0, 0, 0], [-0.25, -0.5, -0.25]] (detects horizontal edges)
/// - sobel_v: [[0.25, 0, -0.25], [0.5, 0, -0.5], [0.25, 0, -0.25]] (detects vertical edges)
///
/// For larger kernel sizes (5, 7), uses extended separable Sobel kernels.
///
/// Uses reflect padding at borders (matches scipy.ndimage.convolve mode='reflect').
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels)
/// * `direction` - "h" for horizontal, "v" for vertical, "both" for magnitude
/// * `kernel_size` - Kernel size: 3, 5, or 7 (default 3)
///
/// # Returns
/// Edge-detected image with same channel count (grayscale values)
pub fn sobel_u8(input: ArrayView3<u8>, direction: &str, kernel_size: u8) -> Array3<u8> {
    let (height, width, channels) = input.dim();
    let mut output = Array3::<u8>::zeros((height, width, channels));

    let (kernel_h, kernel_v) = build_sobel_kernels(kernel_size);
    let ks = kernel_h.len() as i32;
    let half = (ks - 1) / 2;

    // sqrt(2) for 2D image magnitude normalization (matches skimage)
    let sqrt_ndim = std::f32::consts::SQRT_2;

    let color_channels = if channels == 4 { 3 } else { channels };

    // Process ALL pixels using reflect padding at borders
    for y in 0..height {
        for x in 0..width {
            let mut gh = 0.0f32; // horizontal edge (sobel_h)
            let mut gv = 0.0f32; // vertical edge (sobel_v)

            for ky in 0..ks {
                for kx in 0..ks {
                    let py = y as i32 + ky - half;
                    let px = x as i32 + kx - half;
                    let lum = get_lum_u8_reflect(&input, py, px, height, width, channels);
                    gh += lum * kernel_h[ky as usize][kx as usize];
                    gv += lum * kernel_v[ky as usize][kx as usize];
                }
            }

            // skimage clips to [0,1] then scales to 0-255
            let rgb_edge = match direction {
                "h" => gh.abs(),
                "v" => gv.abs(),
                _ => {
                    // "both" - magnitude: sqrt((h^2 + v^2) / ndim) = sqrt(h^2 + v^2) / sqrt(ndim)
                    (gh * gh + gv * gv).sqrt() / sqrt_ndim
                }
            };

            let final_edge = if channels == 4 {
                // Compute alpha gradient with same kernels
                let mut ah = 0.0f32;
                let mut av = 0.0f32;
                for ky in 0..ks {
                    for kx in 0..ks {
                        let py = y as i32 + ky - half;
                        let px = x as i32 + kx - half;
                        let alpha = get_alpha_u8_reflect(&input, py, px, height, width);
                        ah += alpha * kernel_h[ky as usize][kx as usize];
                        av += alpha * kernel_v[ky as usize][kx as usize];
                    }
                }
                let alpha_edge = match direction {
                    "h" => ah.abs(),
                    "v" => av.abs(),
                    _ => (ah * ah + av * av).sqrt() / sqrt_ndim,
                };
                rgb_edge.max(alpha_edge)
            } else {
                rgb_edge
            };

            let edge_value = (final_edge.clamp(0.0, 1.0) * 255.0).round() as u8;

            for c in 0..color_channels {
                output[[y, x, c]] = edge_value;
            }
            if channels == 4 {
                // Preserve source alpha
                output[[y, x, 3]] = input[[y, x, 3]];
            }
        }
    }

    output
}

/// Apply Sobel edge detection - f32 version.
///
/// Uses reflect padding at borders (matches scipy.ndimage.convolve mode='reflect').
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels), values 0.0-1.0
/// * `direction` - "h" for horizontal, "v" for vertical, "both" for magnitude
/// * `kernel_size` - Kernel size: 3, 5, or 7 (default 3)
///
/// # Returns
/// Edge-detected image with same channel count (grayscale values)
pub fn sobel_f32(input: ArrayView3<f32>, direction: &str, kernel_size: u8) -> Array3<f32> {
    let (height, width, channels) = input.dim();
    let mut output = Array3::<f32>::zeros((height, width, channels));

    let (kernel_h, kernel_v) = build_sobel_kernels(kernel_size);
    let ks = kernel_h.len() as i32;
    let half = (ks - 1) / 2;

    let sqrt_ndim = std::f32::consts::SQRT_2;
    let color_channels = if channels == 4 { 3 } else { channels };

    // Process ALL pixels using reflect padding at borders
    for y in 0..height {
        for x in 0..width {
            let mut gh = 0.0f32;
            let mut gv = 0.0f32;

            for ky in 0..ks {
                for kx in 0..ks {
                    let py = y as i32 + ky - half;
                    let px = x as i32 + kx - half;
                    let lum = get_lum_f32_reflect(&input, py, px, height, width, channels);
                    gh += lum * kernel_h[ky as usize][kx as usize];
                    gv += lum * kernel_v[ky as usize][kx as usize];
                }
            }

            let rgb_edge = match direction {
                "h" => gh.abs(),
                "v" => gv.abs(),
                _ => (gh * gh + gv * gv).sqrt() / sqrt_ndim,
            };

            let final_edge = if channels == 4 {
                // Compute alpha gradient with same kernels
                let mut ah = 0.0f32;
                let mut av = 0.0f32;
                for ky in 0..ks {
                    for kx in 0..ks {
                        let py = y as i32 + ky - half;
                        let px = x as i32 + kx - half;
                        let alpha = get_alpha_f32_reflect(&input, py, px, height, width);
                        ah += alpha * kernel_h[ky as usize][kx as usize];
                        av += alpha * kernel_v[ky as usize][kx as usize];
                    }
                }
                let alpha_edge = match direction {
                    "h" => ah.abs(),
                    "v" => av.abs(),
                    _ => (ah * ah + av * av).sqrt() / sqrt_ndim,
                };
                rgb_edge.max(alpha_edge)
            } else {
                rgb_edge
            };

            let edge_value = final_edge.clamp(0.0, 1.0);

            for c in 0..color_channels {
                output[[y, x, c]] = edge_value;
            }
            if channels == 4 {
                // Preserve source alpha
                output[[y, x, 3]] = input[[y, x, 3]];
            }
        }
    }

    output
}

// ============================================================================
// Laplacian Edge Detection
// ============================================================================

/// Build a Laplacian kernel of given size.
///
/// Returns (kernel, size) where kernel is a flat Vec and size is the kernel dimension.
fn build_laplacian_kernel(kernel_size: u8) -> (Vec<Vec<f32>>, usize) {
    if kernel_size >= 7 {
        // 7x7 Laplacian kernel (extended discrete Laplacian pattern)
        let kernel: Vec<Vec<f32>> = vec![
            vec![0.0,  0.0,  0.0, -1.0,  0.0,  0.0,  0.0],
            vec![0.0,  0.0, -1.0, -2.0, -1.0,  0.0,  0.0],
            vec![0.0, -1.0, -2.0, -4.0, -2.0, -1.0,  0.0],
            vec![-1.0, -2.0, -4.0, 40.0, -4.0, -2.0, -1.0],
            vec![0.0, -1.0, -2.0, -4.0, -2.0, -1.0,  0.0],
            vec![0.0,  0.0, -1.0, -2.0, -1.0,  0.0,  0.0],
            vec![0.0,  0.0,  0.0, -1.0,  0.0,  0.0,  0.0],
        ];
        (kernel, 7)
    } else if kernel_size >= 5 {
        let kernel: Vec<Vec<f32>> = vec![
            vec![0.0,  0.0, -1.0,  0.0,  0.0],
            vec![0.0, -1.0, -2.0, -1.0,  0.0],
            vec![-1.0, -2.0, 16.0, -2.0, -1.0],
            vec![0.0, -1.0, -2.0, -1.0,  0.0],
            vec![0.0,  0.0, -1.0,  0.0,  0.0],
        ];
        (kernel, 5)
    } else {
        let kernel: Vec<Vec<f32>> = vec![
            vec![0.0,  1.0,  0.0],
            vec![1.0, -4.0,  1.0],
            vec![0.0,  1.0,  0.0],
        ];
        (kernel, 3)
    }
}

/// Apply Laplacian edge detection - u8 version.
///
/// Matches skimage.filters.laplace exactly:
/// 1. Apply Laplacian kernel with reflect padding at borders
/// 2. Take absolute value
/// 3. Normalize by dividing by maximum value in result
/// 4. Scale to 0-255
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels)
/// * `kernel_size` - Kernel size: 3, 5, or 7
///
/// # Returns
/// Edge-detected image with same channel count (grayscale values)
pub fn laplacian_u8(input: ArrayView3<u8>, kernel_size: u8) -> Array3<u8> {
    let (height, width, channels) = input.dim();
    let mut output = Array3::<u8>::zeros((height, width, channels));

    let color_channels = if channels == 4 { 3 } else { channels };
    let (kernel, ks) = build_laplacian_kernel(kernel_size);
    let half = (ks as i32 - 1) / 2;

    // First pass: compute raw Laplacian values for ALL pixels with reflect padding
    let mut raw_values = vec![vec![0.0f32; width]; height];
    let mut max_abs = 0.0f32;

    for y in 0..height {
        for x in 0..width {
            let mut sum = 0.0f32;
            let mut alpha_sum = 0.0f32;
            for ky in 0..ks as i32 {
                for kx in 0..ks as i32 {
                    let py = y as i32 + ky - half;
                    let px = x as i32 + kx - half;
                    let lum = get_lum_u8_reflect(&input, py, px, height, width, channels);
                    let kval = kernel[ky as usize][kx as usize];
                    sum += lum * kval;
                    if channels == 4 {
                        let alpha = get_alpha_u8_reflect(&input, py, px, height, width);
                        alpha_sum += alpha * kval;
                    }
                }
            }

            let combined = if channels == 4 {
                sum.abs().max(alpha_sum.abs())
            } else {
                sum.abs()
            };
            raw_values[y][x] = combined;
            if combined > max_abs {
                max_abs = combined;
            }
        }
    }

    // Second pass: normalize by max and write output
    for y in 0..height {
        for x in 0..width {
            let normalized = if max_abs > 0.0 {
                raw_values[y][x] / max_abs
            } else {
                0.0
            };

            let v = (normalized * 255.0).round() as u8;
            for c in 0..color_channels {
                output[[y, x, c]] = v;
            }
            if channels == 4 {
                // Preserve source alpha
                output[[y, x, 3]] = input[[y, x, 3]];
            }
        }
    }

    output
}

/// Apply Laplacian edge detection - f32 version.
///
/// Uses reflect padding at borders (matches scipy.ndimage.convolve mode='reflect').
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels), values 0.0-1.0
/// * `kernel_size` - Kernel size: 3, 5, or 7
///
/// # Returns
/// Edge-detected image with same channel count (grayscale values)
pub fn laplacian_f32(input: ArrayView3<f32>, kernel_size: u8) -> Array3<f32> {
    let (height, width, channels) = input.dim();
    let mut output = Array3::<f32>::zeros((height, width, channels));

    let color_channels = if channels == 4 { 3 } else { channels };
    let (kernel, ks) = build_laplacian_kernel(kernel_size);
    let half = (ks as i32 - 1) / 2;

    // First pass: compute raw Laplacian values for ALL pixels with reflect padding
    let mut raw_values = vec![vec![0.0f32; width]; height];
    let mut max_abs = 0.0f32;

    for y in 0..height {
        for x in 0..width {
            let mut sum = 0.0f32;
            let mut alpha_sum = 0.0f32;
            for ky in 0..ks as i32 {
                for kx in 0..ks as i32 {
                    let py = y as i32 + ky - half;
                    let px = x as i32 + kx - half;
                    let lum = get_lum_f32_reflect(&input, py, px, height, width, channels);
                    let kval = kernel[ky as usize][kx as usize];
                    sum += lum * kval;
                    if channels == 4 {
                        let alpha = get_alpha_f32_reflect(&input, py, px, height, width);
                        alpha_sum += alpha * kval;
                    }
                }
            }

            let combined = if channels == 4 {
                sum.abs().max(alpha_sum.abs())
            } else {
                sum.abs()
            };
            raw_values[y][x] = combined;
            if combined > max_abs {
                max_abs = combined;
            }
        }
    }

    // Second pass: normalize by max
    for y in 0..height {
        for x in 0..width {
            let normalized = if max_abs > 0.0 {
                raw_values[y][x] / max_abs
            } else {
                0.0
            };

            for c in 0..color_channels {
                output[[y, x, c]] = normalized;
            }
            if channels == 4 {
                // Preserve source alpha
                output[[y, x, 3]] = input[[y, x, 3]];
            }
        }
    }

    output
}

// ============================================================================
// Find Edges (Canny-like)
// ============================================================================

/// Apply Gaussian blur for Canny edge detection (f64 precision).
/// Uses constant mode with cval=0 and edge normalization.
///
/// Edge normalization: blur a mask of ones using the same kernel, then divide
/// the blurred image by the blurred mask. This compensates for the edge effects
/// of constant padding where zeros bleed into the image.
fn gaussian_blur_canny_f64(gray: &[Vec<f64>], sigma: f64) -> Vec<Vec<f64>> {
    let height = gray.len();
    let width = if height > 0 { gray[0].len() } else { 0 };

    if height == 0 || width == 0 {
        return vec![];
    }

    // Create Gaussian kernel
    let radius = ((4.0 * sigma + 0.5).floor() as i32).max(1);
    let size = (2 * radius + 1) as usize;
    let mut kernel = vec![0.0f64; size];
    let mut sum = 0.0f64;
    for i in 0..size {
        let x = (i as i32 - radius) as f64;
        kernel[i] = (-x * x / (2.0 * sigma * sigma)).exp();
        sum += kernel[i];
    }
    for k in kernel.iter_mut() {
        *k /= sum;
    }

    // Helper function to apply separable Gaussian blur with constant padding
    let apply_blur = |input: &[Vec<f64>]| -> Vec<Vec<f64>> {
        // Horizontal pass
        let mut temp = vec![vec![0.0f64; width]; height];
        for y in 0..height {
            for x in 0..width {
                let mut val = 0.0f64;
                for (i, &k) in kernel.iter().enumerate() {
                    let px = x as i32 + i as i32 - radius;
                    if px >= 0 && px < width as i32 {
                        val += input[y][px as usize] * k;
                    }
                }
                temp[y][x] = val;
            }
        }

        // Vertical pass
        let mut result = vec![vec![0.0f64; width]; height];
        for y in 0..height {
            for x in 0..width {
                let mut val = 0.0f64;
                for (i, &k) in kernel.iter().enumerate() {
                    let py = y as i32 + i as i32 - radius;
                    if py >= 0 && py < height as i32 {
                        val += temp[py as usize][x] * k;
                    }
                }
                result[y][x] = val;
            }
        }
        result
    };

    // Create mask of ones
    let mask = vec![vec![1.0f64; width]; height];

    // Blur the mask (this shows how much of the kernel weight is inside the image)
    let blurred_mask = apply_blur(&mask);

    // Blur the image
    let blurred_image = apply_blur(gray);

    // Divide image by mask (with epsilon to avoid division by zero)
    let eps = f64::EPSILON;
    let mut result = vec![vec![0.0f64; width]; height];
    for y in 0..height {
        for x in 0..width {
            result[y][x] = blurred_image[y][x] / (blurred_mask[y][x] + eps);
        }
    }

    result
}

/// Find edges using Canny edge detection - u8 version.
///
/// Algorithm:
/// - Gaussian blur with configurable sigma (constant mode, cval=0, edge normalization)
/// - Sobel gradient computation
/// - Non-maximum suppression with bilinear interpolation
/// - Hysteresis thresholding with configurable thresholds
/// - Binary output (0 or 255)
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels)
/// * `sigma` - Gaussian blur sigma (default 1.0)
/// * `low_threshold` - Low hysteresis threshold (default 0.1)
/// * `high_threshold` - High hysteresis threshold (default 0.2)
///
/// # Returns
/// Edge-detected image with same channel count (binary: 0 or 255)
pub fn find_edges_u8(input: ArrayView3<u8>, sigma: f64, low_threshold: f64, high_threshold: f64) -> Array3<u8> {
    let (height, width, channels) = input.dim();
    let mut output = Array3::<u8>::zeros((height, width, channels));

    if height < 3 || width < 3 {
        return output;
    }

    let color_channels = if channels == 4 { 3 } else { channels };

    // Convert to grayscale (0-1 range) using f64 precision throughout
    let mut gray = vec![vec![0.0f64; width]; height];
    for y in 0..height {
        for x in 0..width {
            if channels == 1 {
                gray[y][x] = input[[y, x, 0]] as f64 / 255.0;
            } else {
                let r = input[[y, x, 0]] as f64 / 255.0;
                let g = input[[y, x, 1]] as f64 / 255.0;
                let b = input[[y, x, 2]] as f64 / 255.0;
                gray[y][x] = LUMA_R_F64 * r + LUMA_G_F64 * g + LUMA_B_F64 * b;
            }
        }
    }

    // Extract alpha channel as grayscale buffer when channels == 4
    let gray_alpha = if channels == 4 {
        let mut alpha_buf = vec![vec![0.0f64; width]; height];
        for y in 0..height {
            for x in 0..width {
                alpha_buf[y][x] = input[[y, x, 3]] as f64 / 255.0;
            }
        }
        Some(alpha_buf)
    } else {
        None
    };

    // Gaussian blur with configurable sigma (constant mode, edge normalization)
    let blurred = gaussian_blur_canny_f64(&gray, sigma);
    let blurred_alpha = gray_alpha.as_ref().map(|a| gaussian_blur_canny_f64(a, sigma));

    // Compute gradients using Sobel kernels
    // axis=0 (isobel): [[-1, -2, -1], [0, 0, 0], [1, 2, 1]] (row gradient)
    // axis=1 (jsobel): [[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]] (column gradient)
    let kernel_i: [[f64; 3]; 3] = [[-1.0, -2.0, -1.0], [0.0, 0.0, 0.0], [1.0, 2.0, 1.0]];
    let kernel_j: [[f64; 3]; 3] = [[-1.0, 0.0, 1.0], [-2.0, 0.0, 2.0], [-1.0, 0.0, 1.0]];

    let mut isobel = vec![vec![0.0f64; width]; height]; // row gradient
    let mut jsobel = vec![vec![0.0f64; width]; height]; // column gradient
    let mut magnitude = vec![vec![0.0f64; width]; height];

    // Compute gradients with reflect padding (matching scipy.ndimage default)
    for y in 0..height {
        for x in 0..width {
            let mut gi = 0.0f64;
            let mut gj = 0.0f64;
            for ky in 0..3i32 {
                for kx in 0..3i32 {
                    let py = reflect_index(y as i32 + ky - 1, height);
                    let px = reflect_index(x as i32 + kx - 1, width);
                    let lum = blurred[py][px];
                    gi += lum * kernel_i[ky as usize][kx as usize];
                    gj += lum * kernel_j[ky as usize][kx as usize];
                }
            }

            if let Some(ref ba) = blurred_alpha {
                // Also compute alpha gradients
                let mut ai = 0.0f64;
                let mut aj = 0.0f64;
                for ky in 0..3i32 {
                    for kx in 0..3i32 {
                        let py = reflect_index(y as i32 + ky - 1, height);
                        let px = reflect_index(x as i32 + kx - 1, width);
                        let a = ba[py][px];
                        ai += a * kernel_i[ky as usize][kx as usize];
                        aj += a * kernel_j[ky as usize][kx as usize];
                    }
                }
                let rgb_mag = (gi * gi + gj * gj).sqrt();
                let alpha_mag = (ai * ai + aj * aj).sqrt();
                if alpha_mag > rgb_mag {
                    // Use alpha's direction for NMS
                    isobel[y][x] = ai;
                    jsobel[y][x] = aj;
                    magnitude[y][x] = alpha_mag;
                } else {
                    isobel[y][x] = gi;
                    jsobel[y][x] = gj;
                    magnitude[y][x] = rgb_mag;
                }
            } else {
                isobel[y][x] = gi;
                jsobel[y][x] = gj;
                magnitude[y][x] = (gi * gi + gj * gj).sqrt();
            }
        }
    }

    // Non-maximum suppression with bilinear interpolation
    let mut local_maxima = vec![vec![false; width]; height];
    let low_thresh = low_threshold;
    let high_thresh = high_threshold;
    for row in 1..height - 1 {
        for col in 1..width - 1 {
            let m = magnitude[row][col];
            if m < low_thresh {
                continue;
            }

            let gi = isobel[row][col]; // row gradient
            let gj = jsobel[row][col]; // col gradient

            // Gradient direction classification
            let is_down = gi <= 0.0;
            let is_up = gi >= 0.0;
            let is_left = gj <= 0.0;
            let is_right = gj >= 0.0;

            let cond1 = (is_up && is_right) || (is_down && is_left);
            let cond2 = (is_down && is_right) || (is_up && is_left);

            if !cond1 && !cond2 {
                continue;
            }

            let abs_i = gi.abs();
            let abs_j = gj.abs();

            // Bilinear interpolation for sub-pixel gradient direction
            let (neigh1_1, neigh1_2, neigh2_1, neigh2_2, w) = if cond1 {
                if abs_i > abs_j {
                    let w = abs_j / abs_i;
                    (magnitude[row + 1][col], magnitude[row + 1][col + 1],
                     magnitude[row - 1][col], magnitude[row - 1][col - 1], w)
                } else {
                    let w = abs_i / abs_j;
                    (magnitude[row][col + 1], magnitude[row + 1][col + 1],
                     magnitude[row][col - 1], magnitude[row - 1][col - 1], w)
                }
            } else {
                // cond2
                if abs_i < abs_j {
                    let w = abs_i / abs_j;
                    (magnitude[row][col + 1], magnitude[row - 1][col + 1],
                     magnitude[row][col - 1], magnitude[row + 1][col - 1], w)
                } else {
                    let w = abs_j / abs_i;
                    (magnitude[row - 1][col], magnitude[row - 1][col + 1],
                     magnitude[row + 1][col], magnitude[row + 1][col - 1], w)
                }
            };

            // Check if pixel is local maximum along gradient direction
            let c_plus = neigh1_2 * w + neigh1_1 * (1.0 - w) <= m;
            if c_plus {
                let c_minus = neigh2_2 * w + neigh2_1 * (1.0 - w) <= m;
                if c_minus {
                    local_maxima[row][col] = true;
                }
            }
        }
    }

    // Apply thresholding AFTER NMS
    let mut low_mask = vec![vec![false; width]; height];
    let mut high_mask = vec![vec![false; width]; height];

    for y in 1..height - 1 {
        for x in 1..width - 1 {
            if local_maxima[y][x] {
                let mag = magnitude[y][x];
                if mag >= low_thresh {
                    low_mask[y][x] = true;
                }
                if mag >= high_thresh {
                    high_mask[y][x] = true;
                }
            }
        }
    }

    // Use connected component labeling to find edges
    // A pixel is an edge if it's in low_mask AND connected to high_mask
    let mut edges = high_mask.clone();

    // Propagate edges from high to connected low pixels
    let mut changed = true;
    while changed {
        changed = false;
        for y in 1..height - 1 {
            for x in 1..width - 1 {
                if !edges[y][x] && low_mask[y][x] {
                    // Check 8-connected neighbors
                    for dy in -1i32..=1 {
                        for dx in -1i32..=1 {
                            if dy == 0 && dx == 0 {
                                continue;
                            }
                            let ny = (y as i32 + dy) as usize;
                            let nx = (x as i32 + dx) as usize;
                            if edges[ny][nx] {
                                edges[y][x] = true;
                                changed = true;
                                break;
                            }
                        }
                        if edges[y][x] {
                            break;
                        }
                    }
                }
            }
        }
    }

    // Write output (binary: 0 or 255)
    for y in 0..height {
        for x in 0..width {
            let v = if edges[y][x] { 255 } else { 0 };
            for c in 0..color_channels {
                output[[y, x, c]] = v;
            }
            if channels == 4 {
                // Preserve source alpha
                output[[y, x, 3]] = input[[y, x, 3]];
            }
        }
    }

    output
}

/// Find edges using Canny edge detection - f32 version.
///
/// Same algorithm as find_edges_u8, but for float input/output.
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels), values 0.0-1.0
/// * `sigma` - Gaussian blur sigma (default 1.0)
/// * `low_threshold` - Low hysteresis threshold (default 0.1)
/// * `high_threshold` - High hysteresis threshold (default 0.2)
///
/// # Returns
/// Edge-detected image with same channel count (binary: 0.0 or 1.0)
pub fn find_edges_f32(input: ArrayView3<f32>, sigma: f64, low_threshold: f64, high_threshold: f64) -> Array3<f32> {
    let (height, width, channels) = input.dim();
    let mut output = Array3::<f32>::zeros((height, width, channels));

    if height < 3 || width < 3 {
        return output;
    }

    let color_channels = if channels == 4 { 3 } else { channels };

    // Convert to grayscale using f64 precision throughout
    let mut gray = vec![vec![0.0f64; width]; height];
    for y in 0..height {
        for x in 0..width {
            if channels == 1 {
                gray[y][x] = input[[y, x, 0]] as f64;
            } else {
                let r = input[[y, x, 0]] as f64;
                let g = input[[y, x, 1]] as f64;
                let b = input[[y, x, 2]] as f64;
                gray[y][x] = LUMA_R_F64 * r + LUMA_G_F64 * g + LUMA_B_F64 * b;
            }
        }
    }

    // Extract alpha channel as grayscale buffer when channels == 4
    let gray_alpha = if channels == 4 {
        let mut alpha_buf = vec![vec![0.0f64; width]; height];
        for y in 0..height {
            for x in 0..width {
                alpha_buf[y][x] = input[[y, x, 3]] as f64;
            }
        }
        Some(alpha_buf)
    } else {
        None
    };

    // Gaussian blur with configurable sigma (constant mode, edge normalization)
    let blurred = gaussian_blur_canny_f64(&gray, sigma);
    let blurred_alpha = gray_alpha.as_ref().map(|a| gaussian_blur_canny_f64(a, sigma));

    // Compute gradients using Sobel kernels
    let kernel_i: [[f64; 3]; 3] = [[-1.0, -2.0, -1.0], [0.0, 0.0, 0.0], [1.0, 2.0, 1.0]];
    let kernel_j: [[f64; 3]; 3] = [[-1.0, 0.0, 1.0], [-2.0, 0.0, 2.0], [-1.0, 0.0, 1.0]];

    let mut isobel = vec![vec![0.0f64; width]; height];
    let mut jsobel = vec![vec![0.0f64; width]; height];
    let mut magnitude = vec![vec![0.0f64; width]; height];

    for y in 0..height {
        for x in 0..width {
            let mut gi = 0.0f64;
            let mut gj = 0.0f64;
            for ky in 0..3i32 {
                for kx in 0..3i32 {
                    let py = reflect_index(y as i32 + ky - 1, height);
                    let px = reflect_index(x as i32 + kx - 1, width);
                    let lum = blurred[py][px];
                    gi += lum * kernel_i[ky as usize][kx as usize];
                    gj += lum * kernel_j[ky as usize][kx as usize];
                }
            }

            if let Some(ref ba) = blurred_alpha {
                // Also compute alpha gradients
                let mut ai = 0.0f64;
                let mut aj = 0.0f64;
                for ky in 0..3i32 {
                    for kx in 0..3i32 {
                        let py = reflect_index(y as i32 + ky - 1, height);
                        let px = reflect_index(x as i32 + kx - 1, width);
                        let a = ba[py][px];
                        ai += a * kernel_i[ky as usize][kx as usize];
                        aj += a * kernel_j[ky as usize][kx as usize];
                    }
                }
                let rgb_mag = (gi * gi + gj * gj).sqrt();
                let alpha_mag = (ai * ai + aj * aj).sqrt();
                if alpha_mag > rgb_mag {
                    isobel[y][x] = ai;
                    jsobel[y][x] = aj;
                    magnitude[y][x] = alpha_mag;
                } else {
                    isobel[y][x] = gi;
                    jsobel[y][x] = gj;
                    magnitude[y][x] = rgb_mag;
                }
            } else {
                isobel[y][x] = gi;
                jsobel[y][x] = gj;
                magnitude[y][x] = (gi * gi + gj * gj).sqrt();
            }
        }
    }

    // Non-maximum suppression with bilinear interpolation
    let mut local_maxima = vec![vec![false; width]; height];
    let low_thresh = low_threshold;
    let high_thresh = high_threshold;

    for row in 1..height - 1 {
        for col in 1..width - 1 {
            let m = magnitude[row][col];
            if m < low_thresh {
                continue;
            }

            let gi = isobel[row][col];
            let gj = jsobel[row][col];

            let is_down = gi <= 0.0;
            let is_up = gi >= 0.0;
            let is_left = gj <= 0.0;
            let is_right = gj >= 0.0;

            let cond1 = (is_up && is_right) || (is_down && is_left);
            let cond2 = (is_down && is_right) || (is_up && is_left);

            if !cond1 && !cond2 {
                continue;
            }

            let abs_i = gi.abs();
            let abs_j = gj.abs();

            let (neigh1_1, neigh1_2, neigh2_1, neigh2_2, w) = if cond1 {
                if abs_i > abs_j {
                    let w = abs_j / abs_i;
                    (magnitude[row + 1][col], magnitude[row + 1][col + 1],
                     magnitude[row - 1][col], magnitude[row - 1][col - 1], w)
                } else {
                    let w = abs_i / abs_j;
                    (magnitude[row][col + 1], magnitude[row + 1][col + 1],
                     magnitude[row][col - 1], magnitude[row - 1][col - 1], w)
                }
            } else {
                if abs_i < abs_j {
                    let w = abs_i / abs_j;
                    (magnitude[row][col + 1], magnitude[row - 1][col + 1],
                     magnitude[row][col - 1], magnitude[row + 1][col - 1], w)
                } else {
                    let w = abs_j / abs_i;
                    (magnitude[row - 1][col], magnitude[row - 1][col + 1],
                     magnitude[row + 1][col], magnitude[row + 1][col - 1], w)
                }
            };

            let c_plus = neigh1_2 * w + neigh1_1 * (1.0 - w) <= m;
            if c_plus {
                let c_minus = neigh2_2 * w + neigh2_1 * (1.0 - w) <= m;
                if c_minus {
                    local_maxima[row][col] = true;
                }
            }
        }
    }

    // Apply thresholding AFTER NMS
    let mut low_mask = vec![vec![false; width]; height];
    let mut high_mask = vec![vec![false; width]; height];

    for row in 1..height - 1 {
        for col in 1..width - 1 {
            if local_maxima[row][col] {
                let mag = magnitude[row][col];
                if mag >= low_thresh {
                    low_mask[row][col] = true;
                }
                if mag >= high_thresh {
                    high_mask[row][col] = true;
                }
            }
        }
    }

    let mut edges = high_mask.clone();
    let mut changed = true;
    while changed {
        changed = false;
        for y in 1..height - 1 {
            for x in 1..width - 1 {
                if !edges[y][x] && low_mask[y][x] {
                    for dy in -1i32..=1 {
                        for dx in -1i32..=1 {
                            if dy == 0 && dx == 0 {
                                continue;
                            }
                            let ny = (y as i32 + dy) as usize;
                            let nx = (x as i32 + dx) as usize;
                            if edges[ny][nx] {
                                edges[y][x] = true;
                                changed = true;
                                break;
                            }
                        }
                        if edges[y][x] {
                            break;
                        }
                    }
                }
            }
        }
    }

    // Write output
    for y in 0..height {
        for x in 0..width {
            let v = if edges[y][x] { 1.0 } else { 0.0 };
            for c in 0..color_channels {
                output[[y, x, c]] = v;
            }
            if channels == 4 {
                // Preserve source alpha
                output[[y, x, 3]] = input[[y, x, 3]];
            }
        }
    }

    output
}

// ============================================================================
// Draw Contours
// ============================================================================

/// Trace a single contour starting from (start_y, start_x) using 8-connected
/// Moore neighborhood tracing. Returns the contour as a list of (y, x) points.
fn trace_contour(binary: &[Vec<bool>], visited: &mut [Vec<bool>],
                 start_y: usize, start_x: usize, height: usize, width: usize) -> Vec<(usize, usize)> {
    // Moore neighborhood: 8 directions (clockwise from up)
    //   7 0 1
    //   6 . 2
    //   5 4 3
    let dy: [i32; 8] = [-1, -1, 0, 1, 1, 1, 0, -1];
    let dx: [i32; 8] = [0, 1, 1, 1, 0, -1, -1, -1];

    let mut contour = Vec::new();
    contour.push((start_y, start_x));
    visited[start_y][start_x] = true;

    // Find the entry direction: the first background neighbor (going clockwise)
    // We entered from the left (direction 6), so start scanning from direction 7
    let mut backtrack_dir: usize = 6; // we came from the left (the scan direction)

    let mut cur_y = start_y;
    let mut cur_x = start_x;

    let max_steps = height * width * 2; // safety limit
    for _ in 0..max_steps {
        // Start scanning from (backtrack_dir + 1) mod 8
        let scan_start = (backtrack_dir + 1) % 8;
        let mut found = false;

        for i in 0..8 {
            let dir = (scan_start + i) % 8;
            let ny = cur_y as i32 + dy[dir];
            let nx = cur_x as i32 + dx[dir];

            if ny < 0 || ny >= height as i32 || nx < 0 || nx >= width as i32 {
                continue;
            }

            let ny = ny as usize;
            let nx = nx as usize;

            if binary[ny][nx] {
                // Found the next contour pixel
                cur_y = ny;
                cur_x = nx;
                visited[ny][nx] = true;
                contour.push((ny, nx));
                // Backtrack direction: opposite of dir
                backtrack_dir = (dir + 4) % 8;
                found = true;
                break;
            }
        }

        if !found || (cur_y == start_y && cur_x == start_x) {
            break;
        }
    }

    contour
}

/// Draw a line between two points using Bresenham's algorithm with given width.
fn draw_line_on_output_u8(
    output: &mut Array3<u8>,
    y0: usize, x0: usize, y1: usize, x1: usize,
    half_width: usize,
    height: usize, width: usize, color_channels: usize,
    color_r: u8, color_g: u8, color_b: u8,
) {
    // Bresenham's line algorithm
    let mut x = x0 as i32;
    let mut y = y0 as i32;
    let x_end = x1 as i32;
    let y_end = y1 as i32;
    let dx_abs = (x_end - x).abs();
    let dy_abs = (y_end - y).abs();
    let sx: i32 = if x < x_end { 1 } else { -1 };
    let sy: i32 = if y < y_end { 1 } else { -1 };
    let mut err = dx_abs - dy_abs;

    loop {
        // Draw a filled circle/square at this point
        let hw = half_width as i32;
        for py in (y - hw)..=(y + hw) {
            if py < 0 || py >= height as i32 { continue; }
            for px in (x - hw)..=(x + hw) {
                if px < 0 || px >= width as i32 { continue; }
                let pu = py as usize;
                let pxu = px as usize;
                if color_channels >= 1 { output[[pu, pxu, 0]] = color_r; }
                if color_channels >= 2 { output[[pu, pxu, 1]] = color_g; }
                if color_channels >= 3 { output[[pu, pxu, 2]] = color_b; }
            }
        }

        if x == x_end && y == y_end { break; }
        let e2 = 2 * err;
        if e2 > -dy_abs { err -= dy_abs; x += sx; }
        if e2 < dx_abs { err += dx_abs; y += sy; }
    }
}

/// Draw contours on an image - u8 version.
///
/// Matches cv2.findContours + cv2.drawContours behavior:
/// 1. Convert to grayscale luminance
/// 2. Threshold at given level → binary mask
/// 3. Trace contours using Moore neighborhood tracing (8-connected)
/// 4. Draw contour lines on copy of input with given line_width and color
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels)
/// * `threshold` - Binary threshold (0-255)
/// * `line_width` - Width of contour lines (1-10)
/// * `color_r` - Red component of contour color (0-255)
/// * `color_g` - Green component of contour color (0-255)
/// * `color_b` - Blue component of contour color (0-255)
///
/// # Returns
/// Image with contours drawn, same dimensions and channel count
pub fn draw_contours_u8(
    input: ArrayView3<u8>,
    threshold_val: u8,
    line_width: u8,
    color_r: u8,
    color_g: u8,
    color_b: u8,
) -> Array3<u8> {
    let (height, width, channels) = input.dim();
    let mut output = input.to_owned();

    if height < 2 || width < 2 {
        return output;
    }

    // Build grayscale luminance image and threshold
    let mut binary = vec![vec![false; width]; height];
    for y in 0..height {
        for x in 0..width {
            let lum = if channels == 1 {
                input[[y, x, 0]]
            } else {
                let r = input[[y, x, 0]] as f32;
                let g = input[[y, x, 1]] as f32;
                let b = input[[y, x, 2]] as f32;
                (LUMA_R * r + LUMA_G * g + LUMA_B * b).round() as u8
            };
            binary[y][x] = lum >= threshold_val;
        }
    }

    // Trace all contours using Moore neighborhood tracing
    let mut visited = vec![vec![false; width]; height];
    let mut contours: Vec<Vec<(usize, usize)>> = Vec::new();

    // Scan left-to-right, top-to-bottom for contour start points
    // A contour starts where we transition from background to foreground
    for y in 0..height {
        for x in 0..width {
            if !binary[y][x] || visited[y][x] {
                continue;
            }
            // Check if this is a border pixel (has at least one background neighbor)
            let has_bg_neighbor = x == 0 || !binary[y][x - 1]
                || (y > 0 && !binary[y - 1][x])
                || x + 1 >= width || !binary[y][x + 1]
                || (y + 1 < height && !binary[y + 1][x]);

            if has_bg_neighbor {
                let contour = trace_contour(&binary, &mut visited, y, x, height, width);
                if contour.len() >= 2 {
                    contours.push(contour);
                }
            }
        }
    }

    // Draw contours as connected line segments
    let half = ((line_width as usize).max(1) - 1) / 2;
    let color_channels = channels.min(3);

    for contour in &contours {
        for i in 0..contour.len() {
            let (y0, x0) = contour[i];
            let (y1, x1) = contour[(i + 1) % contour.len()];
            draw_line_on_output_u8(
                &mut output, y0, x0, y1, x1,
                half, height, width, color_channels,
                color_r, color_g, color_b,
            );
        }
    }

    output
}

/// Draw contours on an image - f32 version.
///
/// Same algorithm as draw_contours_u8 but for float images.
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels, values 0.0-1.0
/// * `threshold` - Binary threshold (0.0-1.0)
/// * `line_width` - Width of contour lines (1-10)
/// * `color_r` - Red component (0.0-1.0)
/// * `color_g` - Green component (0.0-1.0)
/// * `color_b` - Blue component (0.0-1.0)
pub fn draw_contours_f32(
    input: ArrayView3<f32>,
    threshold_val: f32,
    line_width: u8,
    color_r: f32,
    color_g: f32,
    color_b: f32,
) -> Array3<f32> {
    let (height, width, channels) = input.dim();
    let mut output = input.to_owned();

    if height < 2 || width < 2 {
        return output;
    }

    // Build binary mask from grayscale luminance
    let mut binary = vec![vec![false; width]; height];
    for y in 0..height {
        for x in 0..width {
            binary[y][x] = get_lum_f32(&input, y, x, channels) >= threshold_val;
        }
    }

    // Trace all contours
    let mut visited = vec![vec![false; width]; height];
    let mut contours: Vec<Vec<(usize, usize)>> = Vec::new();

    for y in 0..height {
        for x in 0..width {
            if !binary[y][x] || visited[y][x] {
                continue;
            }
            let has_bg_neighbor = x == 0 || !binary[y][x - 1]
                || (y > 0 && !binary[y - 1][x])
                || x + 1 >= width || !binary[y][x + 1]
                || (y + 1 < height && !binary[y + 1][x]);

            if has_bg_neighbor {
                let contour = trace_contour(&binary, &mut visited, y, x, height, width);
                if contour.len() >= 2 {
                    contours.push(contour);
                }
            }
        }
    }

    // Draw contours
    let half = ((line_width as usize).max(1) - 1) / 2;
    let color_channels = channels.min(3);

    for contour in &contours {
        for i in 0..contour.len() {
            let (y0, x0) = contour[i];
            let (y1, x1) = contour[(i + 1) % contour.len()];

            // Bresenham's line with width
            let mut bx = x0 as i32;
            let mut by = y0 as i32;
            let bx_end = x1 as i32;
            let by_end = y1 as i32;
            let bdx = (bx_end - bx).abs();
            let bdy = (by_end - by).abs();
            let sx: i32 = if bx < bx_end { 1 } else { -1 };
            let sy: i32 = if by < by_end { 1 } else { -1 };
            let mut err = bdx - bdy;

            loop {
                let hw = half as i32;
                for py in (by - hw)..=(by + hw) {
                    if py < 0 || py >= height as i32 { continue; }
                    for px in (bx - hw)..=(bx + hw) {
                        if px < 0 || px >= width as i32 { continue; }
                        let pu = py as usize;
                        let pxu = px as usize;
                        if color_channels >= 1 { output[[pu, pxu, 0]] = color_r; }
                        if color_channels >= 2 { output[[pu, pxu, 1]] = color_g; }
                        if color_channels >= 3 { output[[pu, pxu, 2]] = color_b; }
                    }
                }
                if bx == bx_end && by == by_end { break; }
                let e2 = 2 * err;
                if e2 > -bdy { err -= bdy; bx += sx; }
                if e2 < bdx { err += bdx; by += sy; }
            }
        }
    }

    output
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_sobel_u8_detects_vertical_edge() {
        let mut img = Array3::<u8>::zeros((5, 5, 4));
        // Create vertical edge: left side black, right side white
        for y in 0..5 {
            for x in 0..5 {
                img[[y, x, 0]] = if x < 2 { 0 } else { 255 };
                img[[y, x, 1]] = if x < 2 { 0 } else { 255 };
                img[[y, x, 2]] = if x < 2 { 0 } else { 255 };
                img[[y, x, 3]] = 255;
            }
        }

        // Use "v" direction to detect vertical edges (gradient in x direction)
        let result = sobel_u8(img.view(), "v", 3);

        // Edge should be detected at the boundary
        assert!(result[[2, 2, 0]] > 0);
        // Output alpha should match input alpha
        assert_eq!(result[[2, 2, 3]], 255);
    }

    #[test]
    fn test_sobel_f32_both_directions() {
        let mut img = Array3::<f32>::zeros((5, 5, 4));
        // Create corner pattern
        for y in 0..5 {
            for x in 0..5 {
                let v = if y < 2 && x < 2 { 1.0 } else { 0.0 };
                img[[y, x, 0]] = v;
                img[[y, x, 1]] = v;
                img[[y, x, 2]] = v;
                img[[y, x, 3]] = 1.0;
            }
        }

        let result = sobel_f32(img.view(), "both", 3);

        // Edge should be detected at corner
        assert!(result[[2, 2, 0]] > 0.0);
        // Output alpha should match input alpha
        assert_eq!(result[[2, 2, 3]], 1.0);
    }

    #[test]
    fn test_sobel_u8_kernel_size_5() {
        let mut img = Array3::<u8>::zeros((9, 9, 4));
        for y in 0..9 {
            for x in 0..9 {
                img[[y, x, 0]] = if x < 4 { 0 } else { 255 };
                img[[y, x, 1]] = if x < 4 { 0 } else { 255 };
                img[[y, x, 2]] = if x < 4 { 0 } else { 255 };
                img[[y, x, 3]] = 255;
            }
        }
        let result = sobel_u8(img.view(), "v", 5);
        assert!(result[[4, 4, 0]] > 0, "Sobel 5x5 should detect edge");
    }

    #[test]
    fn test_sobel_u8_kernel_size_7() {
        let mut img = Array3::<u8>::zeros((11, 11, 4));
        for y in 0..11 {
            for x in 0..11 {
                img[[y, x, 0]] = if x < 5 { 0 } else { 255 };
                img[[y, x, 1]] = if x < 5 { 0 } else { 255 };
                img[[y, x, 2]] = if x < 5 { 0 } else { 255 };
                img[[y, x, 3]] = 255;
            }
        }
        let result = sobel_u8(img.view(), "both", 7);
        assert!(result[[5, 5, 0]] > 0, "Sobel 7x7 should detect edge");
    }

    #[test]
    fn test_laplacian_u8_flat_is_zero() {
        let mut img = Array3::<u8>::zeros((5, 5, 4));
        for y in 0..5 {
            for x in 0..5 {
                img[[y, x, 0]] = 128;
                img[[y, x, 1]] = 128;
                img[[y, x, 2]] = 128;
                img[[y, x, 3]] = 255;
            }
        }

        let result = laplacian_u8(img.view(), 3);

        // Flat area should have no edges
        assert_eq!(result[[2, 2, 0]], 0);
        // Output alpha should match input alpha
        assert_eq!(result[[2, 2, 3]], 255);
    }

    #[test]
    fn test_laplacian_f32_5x5() {
        let mut img = Array3::<f32>::zeros((7, 7, 4));
        // Create a point
        for y in 0..7 {
            for x in 0..7 {
                img[[y, x, 0]] = if y == 3 && x == 3 { 1.0 } else { 0.0 };
                img[[y, x, 3]] = 1.0;
            }
        }

        let result = laplacian_f32(img.view(), 5);

        // Point should create response
        assert!(result[[3, 3, 0]] > 0.0);
        // Output alpha should match input alpha
        assert_eq!(result[[3, 3, 3]], 1.0);
    }

    #[test]
    fn test_find_edges_u8() {
        let mut img = Array3::<u8>::zeros((5, 5, 4));
        // Create a simple edge
        for y in 0..5 {
            for x in 0..5 {
                img[[y, x, 0]] = if x < 2 { 50 } else { 200 };
                img[[y, x, 1]] = if x < 2 { 50 } else { 200 };
                img[[y, x, 2]] = if x < 2 { 50 } else { 200 };
                img[[y, x, 3]] = 255;
            }
        }

        let result = find_edges_u8(img.view(), 1.0, 0.1, 0.2);

        // Edge should be detected
        let has_edge = (1..4).any(|y| (1..4).any(|x| result[[y, x, 0]] > 0));
        assert!(has_edge);
        // Output alpha should match input alpha
        assert_eq!(result[[2, 2, 3]], 255);
    }

    #[test]
    fn test_laplacian_u8_7x7() {
        let mut img = Array3::<u8>::zeros((11, 11, 4));
        // Create a point
        for y in 0..11 {
            for x in 0..11 {
                img[[y, x, 0]] = if y == 5 && x == 5 { 255 } else { 0 };
                img[[y, x, 3]] = 255;
            }
        }
        let result = laplacian_u8(img.view(), 7);
        // Point should create response
        assert!(result[[5, 5, 0]] > 0, "Laplacian 7x7 should detect point");
    }

    #[test]
    fn test_find_edges_custom_params() {
        let mut img = Array3::<u8>::zeros((9, 9, 4));
        for y in 0..9 {
            for x in 0..9 {
                img[[y, x, 0]] = if x < 4 { 50 } else { 200 };
                img[[y, x, 1]] = if x < 4 { 50 } else { 200 };
                img[[y, x, 2]] = if x < 4 { 50 } else { 200 };
                img[[y, x, 3]] = 255;
            }
        }
        // Higher sigma, lower thresholds
        let result = find_edges_u8(img.view(), 2.0, 0.05, 0.1);
        let has_edge = (1..8).any(|y| (1..8).any(|x| result[[y, x, 0]] > 0));
        assert!(has_edge, "Find edges with custom params should detect edge");
    }

    // ========================================================================
    // Alpha-aware edge detection tests
    // ========================================================================

    #[test]
    fn test_sobel_u8_detects_alpha_edge() {
        // Uniform black RGB, alpha goes 0→255 — edge should be detected
        let mut img = Array3::<u8>::zeros((5, 5, 4));
        for y in 0..5 {
            for x in 0..5 {
                img[[y, x, 0]] = 0; // uniform black
                img[[y, x, 1]] = 0;
                img[[y, x, 2]] = 0;
                img[[y, x, 3]] = if x < 2 { 0 } else { 255 };
            }
        }

        let result = sobel_u8(img.view(), "both", 3);

        // Edge should be detected at the alpha boundary
        // Check column 2 (the transition) in middle rows
        let has_edge = (1..4).any(|y| result[[y, 2, 0]] > 0);
        assert!(has_edge, "Sobel should detect alpha boundary edge");
    }

    #[test]
    fn test_sobel_u8_preserves_alpha() {
        // Varying alpha — output alpha must match input pixel-for-pixel
        let mut img = Array3::<u8>::zeros((5, 5, 4));
        for y in 0..5 {
            for x in 0..5 {
                img[[y, x, 0]] = if x < 2 { 0 } else { 255 };
                img[[y, x, 1]] = if x < 2 { 0 } else { 255 };
                img[[y, x, 2]] = if x < 2 { 0 } else { 255 };
                img[[y, x, 3]] = (y * 50 + x * 10) as u8;
            }
        }

        let result = sobel_u8(img.view(), "both", 3);

        for y in 0..5 {
            for x in 0..5 {
                assert_eq!(
                    result[[y, x, 3]], img[[y, x, 3]],
                    "Alpha mismatch at ({}, {}): expected {}, got {}",
                    y, x, img[[y, x, 3]], result[[y, x, 3]]
                );
            }
        }
    }

    #[test]
    fn test_laplacian_u8_detects_alpha_edge() {
        // Uniform gray RGB, alpha has a sharp transition
        let mut img = Array3::<u8>::zeros((5, 5, 4));
        for y in 0..5 {
            for x in 0..5 {
                img[[y, x, 0]] = 128;
                img[[y, x, 1]] = 128;
                img[[y, x, 2]] = 128;
                img[[y, x, 3]] = if x < 2 { 0 } else { 255 };
            }
        }

        let result = laplacian_u8(img.view(), 3);

        // The alpha transition should produce a non-zero edge response
        let has_edge = (0..5).any(|y| (0..5).any(|x| result[[y, x, 0]] > 0));
        assert!(has_edge, "Laplacian should detect alpha boundary edge");
    }

    #[test]
    fn test_find_edges_u8_detects_alpha_edge() {
        // Larger image for Canny (needs at least 3x3 interior).
        // Uniform black RGB, alpha boundary in the middle.
        let mut img = Array3::<u8>::zeros((9, 9, 4));
        for y in 0..9 {
            for x in 0..9 {
                img[[y, x, 0]] = 0;
                img[[y, x, 1]] = 0;
                img[[y, x, 2]] = 0;
                img[[y, x, 3]] = if x < 4 { 0 } else { 255 };
            }
        }

        let result = find_edges_u8(img.view(), 1.0, 0.1, 0.2);

        // Edge should be detected at the alpha boundary
        let has_edge = (1..8).any(|y| (1..8).any(|x| result[[y, x, 0]] > 0));
        assert!(has_edge, "Find edges should detect alpha boundary edge");
    }
}
