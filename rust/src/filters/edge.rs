//! Edge detection filters: Sobel, Laplacian, Find Edges.
//!
//! These filters detect and highlight edges in images.
//! All filters support both u8 (0-255) and f32 (0.0-1.0) modes.
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

// ============================================================================
// Sobel Edge Detection
// ============================================================================

/// Apply Sobel edge detection - u8 version.
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

    // Sobel kernels
    let kernel_h: [[i32; 3]; 3] = [[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]];
    let kernel_v: [[i32; 3]; 3] = [[-1, -2, -1], [0, 0, 0], [1, 2, 1]];

    // BT.709 luminosity coefficients
    const LUMA_R: f32 = 0.2126;
    const LUMA_G: f32 = 0.7152;
    const LUMA_B: f32 = 0.0722;

    let color_channels = if channels == 4 { 3 } else { channels };

    for y in 1..height.saturating_sub(1) {
        for x in 1..width.saturating_sub(1) {
            let mut gx = 0i32;
            let mut gy = 0i32;

            for ky in 0..3 {
                for kx in 0..3 {
                    let py = y + ky - 1;
                    let px = x + kx - 1;

                    // Get luminance of pixel
                    let lum = if channels == 1 {
                        input[[py, px, 0]] as i32
                    } else {
                        let r = input[[py, px, 0]] as f32;
                        let g = input[[py, px, 1]] as f32;
                        let b = input[[py, px, 2]] as f32;
                        (LUMA_R * r + LUMA_G * g + LUMA_B * b) as i32
                    };

                    gx += lum * kernel_h[ky][kx];
                    gy += lum * kernel_v[ky][kx];
                }
            }

            let edge_value = match direction {
                "h" => gx.abs().min(255) as u8,
                "v" => gy.abs().min(255) as u8,
                _ => {
                    // "both" - magnitude
                    let mag = ((gx * gx + gy * gy) as f32).sqrt();
                    mag.min(255.0) as u8
                }
            };

            // Set all color channels to same edge value
            for c in 0..color_channels {
                output[[y, x, c]] = edge_value;
            }
            if channels == 4 {
                output[[y, x, 3]] = input[[y, x, 3]];
            }
        }
    }

    // Set borders to zero (preserving alpha)
    for x in 0..width {
        for c in 0..color_channels {
            output[[0, x, c]] = 0;
            if height > 1 {
                output[[height - 1, x, c]] = 0;
            }
        }
        if channels == 4 {
            output[[0, x, 3]] = input[[0, x, 3]];
            if height > 1 {
                output[[height - 1, x, 3]] = input[[height - 1, x, 3]];
            }
        }
    }
    for y in 0..height {
        for c in 0..color_channels {
            output[[y, 0, c]] = 0;
            if width > 1 {
                output[[y, width - 1, c]] = 0;
            }
        }
        if channels == 4 {
            output[[y, 0, 3]] = input[[y, 0, 3]];
            if width > 1 {
                output[[y, width - 1, 3]] = input[[y, width - 1, 3]];
            }
        }
    }

    output
}

/// Apply Sobel edge detection - f32 version.
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

    let kernel_h: [[f32; 3]; 3] = [[-1.0, 0.0, 1.0], [-2.0, 0.0, 2.0], [-1.0, 0.0, 1.0]];
    let kernel_v: [[f32; 3]; 3] = [[-1.0, -2.0, -1.0], [0.0, 0.0, 0.0], [1.0, 2.0, 1.0]];

    const LUMA_R: f32 = 0.2126;
    const LUMA_G: f32 = 0.7152;
    const LUMA_B: f32 = 0.0722;

    let color_channels = if channels == 4 { 3 } else { channels };

    for y in 1..height.saturating_sub(1) {
        for x in 1..width.saturating_sub(1) {
            let mut gx = 0.0f32;
            let mut gy = 0.0f32;

            for ky in 0..3 {
                for kx in 0..3 {
                    let py = y + ky - 1;
                    let px = x + kx - 1;

                    let lum = if channels == 1 {
                        input[[py, px, 0]]
                    } else {
                        let r = input[[py, px, 0]];
                        let g = input[[py, px, 1]];
                        let b = input[[py, px, 2]];
                        LUMA_R * r + LUMA_G * g + LUMA_B * b
                    };

                    gx += lum * kernel_h[ky][kx];
                    gy += lum * kernel_v[ky][kx];
                }
            }

            // Normalize: max possible value is 4 * 1.0 = 4.0
            let edge_value = match direction {
                "h" => (gx.abs() / 4.0).min(1.0),
                "v" => (gy.abs() / 4.0).min(1.0),
                _ => {
                    let mag = (gx * gx + gy * gy).sqrt();
                    (mag / 5.66).min(1.0) // sqrt(4^2 + 4^2) ≈ 5.66
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

    // Set borders (preserving alpha)
    for x in 0..width {
        if channels == 4 {
            output[[0, x, 3]] = input[[0, x, 3]];
            if height > 1 {
                output[[height - 1, x, 3]] = input[[height - 1, x, 3]];
            }
        }
    }
    for y in 0..height {
        if channels == 4 {
            output[[y, 0, 3]] = input[[y, 0, 3]];
            if width > 1 {
                output[[y, width - 1, 3]] = input[[y, width - 1, 3]];
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
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels)
/// * `kernel_size` - Kernel size: 3 or 5
///
/// # Returns
/// Edge-detected image with same channel count (grayscale values)
pub fn laplacian_u8(input: ArrayView3<u8>, kernel_size: u8) -> Array3<u8> {
    let (height, width, channels) = input.dim();
    let mut output = Array3::<u8>::zeros((height, width, channels));

    const LUMA_R: f32 = 0.2126;
    const LUMA_G: f32 = 0.7152;
    const LUMA_B: f32 = 0.0722;

    let half = if kernel_size >= 5 { 2 } else { 1 };
    let color_channels = if channels == 4 { 3 } else { channels };

    for y in half..height.saturating_sub(half) {
        for x in half..width.saturating_sub(half) {
            let lap = if kernel_size >= 5 {
                // 5x5 Laplacian
                let kernel: [[i32; 5]; 5] = [
                    [0, 0, -1, 0, 0],
                    [0, -1, -2, -1, 0],
                    [-1, -2, 16, -2, -1],
                    [0, -1, -2, -1, 0],
                    [0, 0, -1, 0, 0],
                ];

                let mut sum = 0i32;
                for ky in 0..5 {
                    for kx in 0..5 {
                        let py = y + ky - 2;
                        let px = x + kx - 2;

                        let lum = if channels == 1 {
                            input[[py, px, 0]] as i32
                        } else {
                            let r = input[[py, px, 0]] as f32;
                            let g = input[[py, px, 1]] as f32;
                            let b = input[[py, px, 2]] as f32;
                            (LUMA_R * r + LUMA_G * g + LUMA_B * b) as i32
                        };

                        sum += lum * kernel[ky][kx];
                    }
                }
                sum.abs().min(255) as u8
            } else {
                // 3x3 Laplacian
                let kernel: [[i32; 3]; 3] = [[0, -1, 0], [-1, 4, -1], [0, -1, 0]];

                let mut sum = 0i32;
                for ky in 0..3 {
                    for kx in 0..3 {
                        let py = y + ky - 1;
                        let px = x + kx - 1;

                        let lum = if channels == 1 {
                            input[[py, px, 0]] as i32
                        } else {
                            let r = input[[py, px, 0]] as f32;
                            let g = input[[py, px, 1]] as f32;
                            let b = input[[py, px, 2]] as f32;
                            (LUMA_R * r + LUMA_G * g + LUMA_B * b) as i32
                        };

                        sum += lum * kernel[ky][kx];
                    }
                }
                sum.abs().min(255) as u8
            };

            for c in 0..color_channels {
                output[[y, x, c]] = lap;
            }
            if channels == 4 {
                output[[y, x, 3]] = input[[y, x, 3]];
            }
        }
    }

    // Set borders (preserving alpha)
    if channels == 4 {
        for x in 0..width {
            for y_edge in 0..half {
                output[[y_edge, x, 3]] = input[[y_edge, x, 3]];
                if height > y_edge {
                    output[[height - 1 - y_edge, x, 3]] = input[[height - 1 - y_edge, x, 3]];
                }
            }
        }
        for y in 0..height {
            for x_edge in 0..half {
                output[[y, x_edge, 3]] = input[[y, x_edge, 3]];
                if width > x_edge {
                    output[[y, width - 1 - x_edge, 3]] = input[[y, width - 1 - x_edge, 3]];
                }
            }
        }
    }

    output
}

/// Apply Laplacian edge detection - f32 version.
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

    const LUMA_R: f32 = 0.2126;
    const LUMA_G: f32 = 0.7152;
    const LUMA_B: f32 = 0.0722;

    let half = if kernel_size >= 5 { 2 } else { 1 };
    let color_channels = if channels == 4 { 3 } else { channels };

    for y in half..height.saturating_sub(half) {
        for x in half..width.saturating_sub(half) {
            let lap = if kernel_size >= 5 {
                let kernel: [[f32; 5]; 5] = [
                    [0.0, 0.0, -1.0, 0.0, 0.0],
                    [0.0, -1.0, -2.0, -1.0, 0.0],
                    [-1.0, -2.0, 16.0, -2.0, -1.0],
                    [0.0, -1.0, -2.0, -1.0, 0.0],
                    [0.0, 0.0, -1.0, 0.0, 0.0],
                ];

                let mut sum = 0.0f32;
                for ky in 0..5 {
                    for kx in 0..5 {
                        let py = y + ky - 2;
                        let px = x + kx - 2;

                        let lum = if channels == 1 {
                            input[[py, px, 0]]
                        } else {
                            let r = input[[py, px, 0]];
                            let g = input[[py, px, 1]];
                            let b = input[[py, px, 2]];
                            LUMA_R * r + LUMA_G * g + LUMA_B * b
                        };

                        sum += lum * kernel[ky][kx];
                    }
                }
                // Normalize: max output is 16.0
                (sum.abs() / 16.0).min(1.0)
            } else {
                let kernel: [[f32; 3]; 3] = [[0.0, -1.0, 0.0], [-1.0, 4.0, -1.0], [0.0, -1.0, 0.0]];

                let mut sum = 0.0f32;
                for ky in 0..3 {
                    for kx in 0..3 {
                        let py = y + ky - 1;
                        let px = x + kx - 1;

                        let lum = if channels == 1 {
                            input[[py, px, 0]]
                        } else {
                            let r = input[[py, px, 0]];
                            let g = input[[py, px, 1]];
                            let b = input[[py, px, 2]];
                            LUMA_R * r + LUMA_G * g + LUMA_B * b
                        };

                        sum += lum * kernel[ky][kx];
                    }
                }
                // Normalize: max output is 4.0
                (sum.abs() / 4.0).min(1.0)
            };

            for c in 0..color_channels {
                output[[y, x, c]] = lap;
            }
            if channels == 4 {
                output[[y, x, 3]] = input[[y, x, 3]];
            }
        }
    }

    // Set borders (preserving alpha)
    if channels == 4 {
        for x in 0..width {
            for y_edge in 0..half {
                output[[y_edge, x, 3]] = input[[y_edge, x, 3]];
                if height > y_edge {
                    output[[height - 1 - y_edge, x, 3]] = input[[height - 1 - y_edge, x, 3]];
                }
            }
        }
        for y in 0..height {
            for x_edge in 0..half {
                output[[y, x_edge, 3]] = input[[y, x_edge, 3]];
                if width > x_edge {
                    output[[y, width - 1 - x_edge, 3]] = input[[y, width - 1 - x_edge, 3]];
                }
            }
        }
    }

    output
}

// ============================================================================
// Find Edges
// ============================================================================

/// Find edges using combined edge detection - u8 version.
///
/// Uses a combination of Sobel and post-processing for clean edges.
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels)
///
/// # Returns
/// Edge-detected image with same channel count (white edges on black)
pub fn find_edges_u8(input: ArrayView3<u8>) -> Array3<u8> {
    let (height, width, channels) = input.dim();
    let mut output = Array3::<u8>::zeros((height, width, channels));

    // Use Sobel magnitude
    let sobel = sobel_u8(input, "both");

    let color_channels = if channels == 4 { 3 } else { channels };

    // Apply non-maximum suppression and thresholding
    for y in 1..height.saturating_sub(1) {
        for x in 1..width.saturating_sub(1) {
            let edge_val = sobel[[y, x, 0]];

            // Simple threshold and enhancement
            let enhanced = if edge_val > 20 {
                ((edge_val as f32 * 2.0).min(255.0)) as u8
            } else {
                0
            };

            for c in 0..color_channels {
                output[[y, x, c]] = enhanced;
            }
            if channels == 4 {
                output[[y, x, 3]] = input[[y, x, 3]];
            }
        }
    }

    // Copy alpha for borders
    if channels == 4 {
        for x in 0..width {
            output[[0, x, 3]] = input[[0, x, 3]];
            if height > 1 {
                output[[height - 1, x, 3]] = input[[height - 1, x, 3]];
            }
        }
        for y in 0..height {
            output[[y, 0, 3]] = input[[y, 0, 3]];
            if width > 1 {
                output[[y, width - 1, 3]] = input[[y, width - 1, 3]];
            }
        }
    }

    output
}

/// Find edges using combined edge detection - f32 version.
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels), values 0.0-1.0
///
/// # Returns
/// Edge-detected image with same channel count (white edges on black)
pub fn find_edges_f32(input: ArrayView3<f32>) -> Array3<f32> {
    let (height, width, channels) = input.dim();
    let mut output = Array3::<f32>::zeros((height, width, channels));

    let sobel = sobel_f32(input, "both");

    let color_channels = if channels == 4 { 3 } else { channels };

    for y in 1..height.saturating_sub(1) {
        for x in 1..width.saturating_sub(1) {
            let edge_val = sobel[[y, x, 0]];

            // Simple threshold and enhancement
            let enhanced = if edge_val > 0.08 {
                (edge_val * 2.0).min(1.0)
            } else {
                0.0
            };

            for c in 0..color_channels {
                output[[y, x, c]] = enhanced;
            }
            if channels == 4 {
                output[[y, x, 3]] = input[[y, x, 3]];
            }
        }
    }

    // Copy alpha for borders
    if channels == 4 {
        for x in 0..width {
            output[[0, x, 3]] = input[[0, x, 3]];
            if height > 1 {
                output[[height - 1, x, 3]] = input[[height - 1, x, 3]];
            }
        }
        for y in 0..height {
            output[[y, 0, 3]] = input[[y, 0, 3]];
            if width > 1 {
                output[[y, width - 1, 3]] = input[[y, width - 1, 3]];
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
