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

// BT.709 luminosity coefficients
const LUMA_R: f32 = 0.2126;
const LUMA_G: f32 = 0.7152;
const LUMA_B: f32 = 0.0722;

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

// ============================================================================
// Sobel Edge Detection
// ============================================================================

/// Apply Sobel edge detection - u8 version.
///
/// Uses skimage.filters.sobel kernels exactly:
/// - sobel_h: [[0.25, 0.5, 0.25], [0, 0, 0], [-0.25, -0.5, -0.25]] (detects horizontal edges)
/// - sobel_v: [[0.25, 0, -0.25], [0.5, 0, -0.5], [0.25, 0, -0.25]] (detects vertical edges)
///
/// Uses reflect padding at borders (matches scipy.ndimage.convolve mode='reflect').
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels)
/// * `direction` - "h" for horizontal, "v" for vertical, "both" for magnitude
///
/// # Returns
/// Edge-detected image with same channel count (grayscale values)
pub fn sobel_u8(input: ArrayView3<u8>, direction: &str) -> Array3<u8> {
    let (height, width, channels) = input.dim();
    let mut output = Array3::<u8>::zeros((height, width, channels));

    // Sobel kernels matching skimage.filters.sobel behavior exactly.
    // skimage uses smooth_weights=[0.25, 0.5, 0.25] and edge_weights=[1, 0, -1]
    // The combined kernel is the outer product.
    // For magnitude, skimage divides by sqrt(ndim)=sqrt(2) for 2D images.
    //
    // kernel_h detects horizontal edges (gradient in y direction)
    let kernel_h: [[f32; 3]; 3] = [
        [0.25, 0.5, 0.25],
        [0.0, 0.0, 0.0],
        [-0.25, -0.5, -0.25],
    ];
    // kernel_v detects vertical edges (gradient in x direction)
    let kernel_v: [[f32; 3]; 3] = [
        [0.25, 0.0, -0.25],
        [0.5, 0.0, -0.5],
        [0.25, 0.0, -0.25],
    ];

    // sqrt(2) for 2D image magnitude normalization (matches skimage)
    let sqrt_ndim = std::f32::consts::SQRT_2;

    let color_channels = if channels == 4 { 3 } else { channels };

    // Process ALL pixels using reflect padding at borders
    for y in 0..height {
        for x in 0..width {
            let mut gh = 0.0f32; // horizontal edge (sobel_h)
            let mut gv = 0.0f32; // vertical edge (sobel_v)

            for ky in 0..3i32 {
                for kx in 0..3i32 {
                    let py = y as i32 + ky - 1;
                    let px = x as i32 + kx - 1;
                    let lum = get_lum_u8_reflect(&input, py, px, height, width, channels);
                    gh += lum * kernel_h[ky as usize][kx as usize];
                    gv += lum * kernel_v[ky as usize][kx as usize];
                }
            }

            // skimage clips to [0,1] then scales to 0-255
            let edge_value = match direction {
                "h" => (gh.abs().clamp(0.0, 1.0) * 255.0).round() as u8,
                "v" => (gv.abs().clamp(0.0, 1.0) * 255.0).round() as u8,
                _ => {
                    // "both" - magnitude: sqrt((h^2 + v^2) / ndim) = sqrt(h^2 + v^2) / sqrt(ndim)
                    let mag = (gh * gh + gv * gv).sqrt() / sqrt_ndim;
                    (mag.clamp(0.0, 1.0) * 255.0).round() as u8
                }
            };

            for c in 0..color_channels {
                output[[y, x, c]] = edge_value;
            }
            if channels == 4 {
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
///
/// # Returns
/// Edge-detected image with same channel count (grayscale values)
pub fn sobel_f32(input: ArrayView3<f32>, direction: &str) -> Array3<f32> {
    let (height, width, channels) = input.dim();
    let mut output = Array3::<f32>::zeros((height, width, channels));

    // Same kernels as u8 version
    let kernel_h: [[f32; 3]; 3] = [
        [0.25, 0.5, 0.25],
        [0.0, 0.0, 0.0],
        [-0.25, -0.5, -0.25],
    ];
    let kernel_v: [[f32; 3]; 3] = [
        [0.25, 0.0, -0.25],
        [0.5, 0.0, -0.5],
        [0.25, 0.0, -0.25],
    ];

    let sqrt_ndim = std::f32::consts::SQRT_2;
    let color_channels = if channels == 4 { 3 } else { channels };

    // Process ALL pixels using reflect padding at borders
    for y in 0..height {
        for x in 0..width {
            let mut gh = 0.0f32;
            let mut gv = 0.0f32;

            for ky in 0..3i32 {
                for kx in 0..3i32 {
                    let py = y as i32 + ky - 1;
                    let px = x as i32 + kx - 1;
                    let lum = get_lum_f32_reflect(&input, py, px, height, width, channels);
                    gh += lum * kernel_h[ky as usize][kx as usize];
                    gv += lum * kernel_v[ky as usize][kx as usize];
                }
            }

            let edge_value = match direction {
                "h" => gh.abs().clamp(0.0, 1.0),
                "v" => gv.abs().clamp(0.0, 1.0),
                _ => ((gh * gh + gv * gv).sqrt() / sqrt_ndim).clamp(0.0, 1.0),
            };

            for c in 0..color_channels {
                output[[y, x, c]] = edge_value;
            }
            if channels == 4 {
                output[[y, x, 3]] = input[[y, x, 3]];
            }
        }
    }

    output
}

// ============================================================================
// Laplacian Edge Detection
// ============================================================================

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
/// * `kernel_size` - Kernel size: 3 or 5
///
/// # Returns
/// Edge-detected image with same channel count (grayscale values)
pub fn laplacian_u8(input: ArrayView3<u8>, kernel_size: u8) -> Array3<u8> {
    let (height, width, channels) = input.dim();
    let mut output = Array3::<u8>::zeros((height, width, channels));

    let color_channels = if channels == 4 { 3 } else { channels };

    // First pass: compute raw Laplacian values for ALL pixels with reflect padding
    let mut raw_values = vec![vec![0.0f32; width]; height];
    let mut max_abs = 0.0f32;

    for y in 0..height {
        for x in 0..width {
            let lap = if kernel_size >= 5 {
                // skimage uses ksize parameter for laplace
                // For ksize=5, it's a 5x5 kernel
                let kernel: [[f32; 5]; 5] = [
                    [0.0, 0.0, -1.0, 0.0, 0.0],
                    [0.0, -1.0, -2.0, -1.0, 0.0],
                    [-1.0, -2.0, 16.0, -2.0, -1.0],
                    [0.0, -1.0, -2.0, -1.0, 0.0],
                    [0.0, 0.0, -1.0, 0.0, 0.0],
                ];

                let mut sum = 0.0f32;
                for ky in 0..5i32 {
                    for kx in 0..5i32 {
                        let py = y as i32 + ky - 2;
                        let px = x as i32 + kx - 2;
                        let lum = get_lum_u8_reflect(&input, py, px, height, width, channels);
                        sum += lum * kernel[ky as usize][kx as usize];
                    }
                }
                sum
            } else {
                // Standard 3x3 Laplacian kernel (same as skimage ksize=3)
                let kernel: [[f32; 3]; 3] = [
                    [0.0, 1.0, 0.0],
                    [1.0, -4.0, 1.0],
                    [0.0, 1.0, 0.0],
                ];

                let mut sum = 0.0f32;
                for ky in 0..3i32 {
                    for kx in 0..3i32 {
                        let py = y as i32 + ky - 1;
                        let px = x as i32 + kx - 1;
                        let lum = get_lum_u8_reflect(&input, py, px, height, width, channels);
                        sum += lum * kernel[ky as usize][kx as usize];
                    }
                }
                sum
            };

            let abs_lap = lap.abs();
            raw_values[y][x] = abs_lap;
            if abs_lap > max_abs {
                max_abs = abs_lap;
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
/// * `kernel_size` - Kernel size: 3 or 5
///
/// # Returns
/// Edge-detected image with same channel count (grayscale values)
pub fn laplacian_f32(input: ArrayView3<f32>, kernel_size: u8) -> Array3<f32> {
    let (height, width, channels) = input.dim();
    let mut output = Array3::<f32>::zeros((height, width, channels));

    let color_channels = if channels == 4 { 3 } else { channels };

    // First pass: compute raw Laplacian values for ALL pixels with reflect padding
    let mut raw_values = vec![vec![0.0f32; width]; height];
    let mut max_abs = 0.0f32;

    for y in 0..height {
        for x in 0..width {
            let lap = if kernel_size >= 5 {
                let kernel: [[f32; 5]; 5] = [
                    [0.0, 0.0, -1.0, 0.0, 0.0],
                    [0.0, -1.0, -2.0, -1.0, 0.0],
                    [-1.0, -2.0, 16.0, -2.0, -1.0],
                    [0.0, -1.0, -2.0, -1.0, 0.0],
                    [0.0, 0.0, -1.0, 0.0, 0.0],
                ];

                let mut sum = 0.0f32;
                for ky in 0..5i32 {
                    for kx in 0..5i32 {
                        let py = y as i32 + ky - 2;
                        let px = x as i32 + kx - 2;
                        let lum = get_lum_f32_reflect(&input, py, px, height, width, channels);
                        sum += lum * kernel[ky as usize][kx as usize];
                    }
                }
                sum
            } else {
                let kernel: [[f32; 3]; 3] = [
                    [0.0, 1.0, 0.0],
                    [1.0, -4.0, 1.0],
                    [0.0, 1.0, 0.0],
                ];

                let mut sum = 0.0f32;
                for ky in 0..3i32 {
                    for kx in 0..3i32 {
                        let py = y as i32 + ky - 1;
                        let px = x as i32 + kx - 1;
                        let lum = get_lum_f32_reflect(&input, py, px, height, width, channels);
                        sum += lum * kernel[ky as usize][kx as usize];
                    }
                }
                sum
            };

            let abs_lap = lap.abs();
            raw_values[y][x] = abs_lap;
            if abs_lap > max_abs {
                max_abs = abs_lap;
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
                output[[y, x, 3]] = input[[y, x, 3]];
            }
        }
    }

    output
}

// ============================================================================
// Find Edges (Canny-like)
// ============================================================================

/// Apply Gaussian blur for Canny edge detection.
/// Uses constant mode with cval=0 (matching skimage canny default).
fn gaussian_blur_canny(gray: &[Vec<f32>], sigma: f32) -> Vec<Vec<f32>> {
    let height = gray.len();
    let width = if height > 0 { gray[0].len() } else { 0 };

    // Create Gaussian kernel (matching skimage gaussian)
    let radius = ((4.0 * sigma + 0.5).floor() as i32).max(1);
    let size = (2 * radius + 1) as usize;
    let mut kernel = vec![0.0f32; size];
    let mut sum = 0.0f32;
    for i in 0..size {
        let x = (i as i32 - radius) as f32;
        kernel[i] = (-x * x / (2.0 * sigma * sigma)).exp();
        sum += kernel[i];
    }
    for k in kernel.iter_mut() {
        *k /= sum;
    }

    // Horizontal pass with constant padding (cval=0)
    let mut temp = vec![vec![0.0f32; width]; height];
    for y in 0..height {
        for x in 0..width {
            let mut val = 0.0f32;
            for (i, &k) in kernel.iter().enumerate() {
                let px = x as i32 + i as i32 - radius;
                if px >= 0 && px < width as i32 {
                    val += gray[y][px as usize] * k;
                }
                // else: constant mode with cval=0 means we add 0
            }
            temp[y][x] = val;
        }
    }

    // Vertical pass
    let mut result = vec![vec![0.0f32; width]; height];
    for y in 0..height {
        for x in 0..width {
            let mut val = 0.0f32;
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
}

/// Find edges using Canny-like detection - u8 version.
///
/// Matches skimage.feature.canny behavior:
/// - Gaussian blur with sigma=1.0 (constant mode, cval=0)
/// - scipy.ndimage.sobel gradient computation
/// - Non-maximum suppression with bilinear interpolation
/// - Hysteresis thresholding (low=0.1, high=0.2)
/// - Binary output (0 or 255)
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels)
///
/// # Returns
/// Edge-detected image with same channel count (binary: 0 or 255)
pub fn find_edges_u8(input: ArrayView3<u8>) -> Array3<u8> {
    let (height, width, channels) = input.dim();
    let mut output = Array3::<u8>::zeros((height, width, channels));

    if height < 3 || width < 3 {
        return output;
    }

    let color_channels = if channels == 4 { 3 } else { channels };

    // Convert to grayscale (0-1 range)
    let mut gray = vec![vec![0.0f32; width]; height];
    for y in 0..height {
        for x in 0..width {
            gray[y][x] = get_lum_u8(&input, y, x, channels);
        }
    }

    // Gaussian blur with sigma=1.0 (matching skimage canny default, constant mode)
    let blurred = gaussian_blur_canny(&gray, 1.0);

    // Compute gradients using scipy.ndimage.sobel-compatible kernels
    // axis=0 (isobel): [[-1, -2, -1], [0, 0, 0], [1, 2, 1]] (row gradient)
    // axis=1 (jsobel): [[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]] (column gradient)
    // Note: these are NOT normalized like skimage.filters.sobel
    let kernel_i: [[f32; 3]; 3] = [[-1.0, -2.0, -1.0], [0.0, 0.0, 0.0], [1.0, 2.0, 1.0]];
    let kernel_j: [[f32; 3]; 3] = [[-1.0, 0.0, 1.0], [-2.0, 0.0, 2.0], [-1.0, 0.0, 1.0]];

    let mut isobel = vec![vec![0.0f32; width]; height]; // row gradient
    let mut jsobel = vec![vec![0.0f32; width]; height]; // column gradient
    let mut magnitude = vec![vec![0.0f32; width]; height];

    // Compute gradients with reflect padding (matching scipy.ndimage default)
    for y in 0..height {
        for x in 0..width {
            let mut gi = 0.0f32;
            let mut gj = 0.0f32;
            for ky in 0..3i32 {
                for kx in 0..3i32 {
                    let py = reflect_index(y as i32 + ky - 1, height);
                    let px = reflect_index(x as i32 + kx - 1, width);
                    let lum = blurred[py][px];
                    gi += lum * kernel_i[ky as usize][kx as usize];
                    gj += lum * kernel_j[ky as usize][kx as usize];
                }
            }
            isobel[y][x] = gi;
            jsobel[y][x] = gj;
            magnitude[y][x] = (gi * gi + gj * gj).sqrt();
        }
    }

    // Non-maximum suppression with bilinear interpolation (matching skimage)
    // We suppress pixels that are not local maxima along the gradient direction
    let mut low_mask = vec![vec![false; width]; height];
    let low_thresh = 0.1f32;
    let high_thresh = 0.2f32;

    // Create eroded mask (border pixels are not edges)
    let mut eroded_mask = vec![vec![true; width]; height];
    for x in 0..width {
        eroded_mask[0][x] = false;
        if height > 1 {
            eroded_mask[height - 1][x] = false;
        }
    }
    for y in 0..height {
        eroded_mask[y][0] = false;
        if width > 1 {
            eroded_mask[y][width - 1] = false;
        }
    }

    for y in 1..height - 1 {
        for x in 1..width - 1 {
            if !eroded_mask[y][x] {
                continue;
            }

            let mag = magnitude[y][x];
            if mag < low_thresh {
                continue;
            }

            let gi = isobel[y][x];
            let gj = jsobel[y][x];

            // Compute gradient direction and interpolate neighbors
            let abs_gi = gi.abs();
            let abs_gj = gj.abs();

            if abs_gi > abs_gj {
                // More vertical gradient - interpolate along columns
                let ratio = abs_gj / abs_gi.max(1e-10);
                let sign_i = if gi >= 0.0 { 1i32 } else { -1i32 };
                let sign_j = if gj >= 0.0 { 1i32 } else { -1i32 };

                let y1 = (y as i32 + sign_i) as usize;
                let y2 = (y as i32 - sign_i) as usize;
                let x1 = (x as i32 + sign_j) as usize;
                let x2 = (x as i32 - sign_j) as usize;

                // Bilinear interpolation for neighbor magnitudes
                let m1 = magnitude[y1][x] * (1.0 - ratio) + magnitude[y1][x1] * ratio;
                let m2 = magnitude[y2][x] * (1.0 - ratio) + magnitude[y2][x2] * ratio;

                if mag > m1 && mag > m2 {
                    low_mask[y][x] = true;
                }
            } else {
                // More horizontal gradient - interpolate along rows
                let ratio = abs_gi / abs_gj.max(1e-10);
                let sign_i = if gi >= 0.0 { 1i32 } else { -1i32 };
                let sign_j = if gj >= 0.0 { 1i32 } else { -1i32 };

                let y1 = (y as i32 + sign_i) as usize;
                let y2 = (y as i32 - sign_i) as usize;
                let x1 = (x as i32 + sign_j) as usize;
                let x2 = (x as i32 - sign_j) as usize;

                let m1 = magnitude[y][x1] * (1.0 - ratio) + magnitude[y1][x1] * ratio;
                let m2 = magnitude[y][x2] * (1.0 - ratio) + magnitude[y2][x2] * ratio;

                if mag > m1 && mag > m2 {
                    low_mask[y][x] = true;
                }
            }
        }
    }

    // Hysteresis thresholding using connected component labeling
    // First identify high-threshold pixels, then include connected low-threshold pixels
    let mut high_mask = vec![vec![false; width]; height];

    for y in 1..height - 1 {
        for x in 1..width - 1 {
            if low_mask[y][x] && magnitude[y][x] >= high_thresh {
                high_mask[y][x] = true;
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
                output[[y, x, 3]] = input[[y, x, 3]];
            }
        }
    }

    output
}

/// Find edges using Canny-like detection - f32 version.
///
/// Matches skimage.feature.canny behavior (same as u8 version).
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels), values 0.0-1.0
///
/// # Returns
/// Edge-detected image with same channel count (binary: 0.0 or 1.0)
pub fn find_edges_f32(input: ArrayView3<f32>) -> Array3<f32> {
    let (height, width, channels) = input.dim();
    let mut output = Array3::<f32>::zeros((height, width, channels));

    if height < 3 || width < 3 {
        return output;
    }

    let color_channels = if channels == 4 { 3 } else { channels };

    // Convert to grayscale
    let mut gray = vec![vec![0.0f32; width]; height];
    for y in 0..height {
        for x in 0..width {
            gray[y][x] = get_lum_f32(&input, y, x, channels);
        }
    }

    // Gaussian blur with sigma=1.0 (matching skimage canny default, constant mode)
    let blurred = gaussian_blur_canny(&gray, 1.0);

    // Compute gradients using scipy.ndimage.sobel-compatible kernels
    let kernel_i: [[f32; 3]; 3] = [[-1.0, -2.0, -1.0], [0.0, 0.0, 0.0], [1.0, 2.0, 1.0]];
    let kernel_j: [[f32; 3]; 3] = [[-1.0, 0.0, 1.0], [-2.0, 0.0, 2.0], [-1.0, 0.0, 1.0]];

    let mut isobel = vec![vec![0.0f32; width]; height];
    let mut jsobel = vec![vec![0.0f32; width]; height];
    let mut magnitude = vec![vec![0.0f32; width]; height];

    for y in 0..height {
        for x in 0..width {
            let mut gi = 0.0f32;
            let mut gj = 0.0f32;
            for ky in 0..3i32 {
                for kx in 0..3i32 {
                    let py = reflect_index(y as i32 + ky - 1, height);
                    let px = reflect_index(x as i32 + kx - 1, width);
                    let lum = blurred[py][px];
                    gi += lum * kernel_i[ky as usize][kx as usize];
                    gj += lum * kernel_j[ky as usize][kx as usize];
                }
            }
            isobel[y][x] = gi;
            jsobel[y][x] = gj;
            magnitude[y][x] = (gi * gi + gj * gj).sqrt();
        }
    }

    // Non-maximum suppression with bilinear interpolation
    let mut low_mask = vec![vec![false; width]; height];
    let low_thresh = 0.1f32;
    let high_thresh = 0.2f32;

    // Create eroded mask
    let mut eroded_mask = vec![vec![true; width]; height];
    for x in 0..width {
        eroded_mask[0][x] = false;
        if height > 1 {
            eroded_mask[height - 1][x] = false;
        }
    }
    for y in 0..height {
        eroded_mask[y][0] = false;
        if width > 1 {
            eroded_mask[y][width - 1] = false;
        }
    }

    for y in 1..height - 1 {
        for x in 1..width - 1 {
            if !eroded_mask[y][x] {
                continue;
            }

            let mag = magnitude[y][x];
            if mag < low_thresh {
                continue;
            }

            let gi = isobel[y][x];
            let gj = jsobel[y][x];
            let abs_gi = gi.abs();
            let abs_gj = gj.abs();

            if abs_gi > abs_gj {
                let ratio = abs_gj / abs_gi.max(1e-10);
                let sign_i = if gi >= 0.0 { 1i32 } else { -1i32 };
                let sign_j = if gj >= 0.0 { 1i32 } else { -1i32 };

                let y1 = (y as i32 + sign_i) as usize;
                let y2 = (y as i32 - sign_i) as usize;
                let x1 = (x as i32 + sign_j) as usize;
                let x2 = (x as i32 - sign_j) as usize;

                let m1 = magnitude[y1][x] * (1.0 - ratio) + magnitude[y1][x1] * ratio;
                let m2 = magnitude[y2][x] * (1.0 - ratio) + magnitude[y2][x2] * ratio;

                if mag > m1 && mag > m2 {
                    low_mask[y][x] = true;
                }
            } else {
                let ratio = abs_gi / abs_gj.max(1e-10);
                let sign_i = if gi >= 0.0 { 1i32 } else { -1i32 };
                let sign_j = if gj >= 0.0 { 1i32 } else { -1i32 };

                let y1 = (y as i32 + sign_i) as usize;
                let y2 = (y as i32 - sign_i) as usize;
                let x1 = (x as i32 + sign_j) as usize;
                let x2 = (x as i32 - sign_j) as usize;

                let m1 = magnitude[y][x1] * (1.0 - ratio) + magnitude[y1][x1] * ratio;
                let m2 = magnitude[y][x2] * (1.0 - ratio) + magnitude[y2][x2] * ratio;

                if mag > m1 && mag > m2 {
                    low_mask[y][x] = true;
                }
            }
        }
    }

    // Hysteresis thresholding
    let mut high_mask = vec![vec![false; width]; height];
    for y in 1..height - 1 {
        for x in 1..width - 1 {
            if low_mask[y][x] && magnitude[y][x] >= high_thresh {
                high_mask[y][x] = true;
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
                output[[y, x, 3]] = input[[y, x, 3]];
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

        let result = sobel_u8(img.view(), "h");

        // Edge should be detected at the boundary
        assert!(result[[2, 2, 0]] > 0);
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

        let result = sobel_f32(img.view(), "both");

        // Edge should be detected at corner
        assert!(result[[2, 2, 0]] > 0.0);
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

        let result = find_edges_u8(img.view());

        // Edge should be detected
        let has_edge = (1..4).any(|y| (1..4).any(|x| result[[y, x, 0]] > 0));
        assert!(has_edge);
    }
}
