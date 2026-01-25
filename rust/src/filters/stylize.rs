//! Stylize filters: Posterize, Solarize, Threshold, Emboss.
//!
//! These are artistic effect filters.
//! All filters support both u8 (0-255) and f32 (0.0-1.0) modes.
//!
//! ## Supported Formats
//!
//! All filters accept images with 1, 3, or 4 channels:
//! - **Grayscale**: (height, width, 1) - processes the single channel
//! - **RGB**: (height, width, 3) - processes all 3 channels
//! - **RGBA**: (height, width, 4) - processes RGB, preserves alpha

use ndarray::{Array3, ArrayView3};

// ============================================================================
// Posterize
// ============================================================================

/// Reduce color levels (posterize) - u8 version.
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels)
/// * `levels` - Number of levels per channel (2-256)
///
/// # Returns
/// Posterized image with same channel count
pub fn posterize_u8(input: ArrayView3<u8>, levels: u8) -> Array3<u8> {
    let (height, width, channels) = input.dim();
    let mut output = Array3::<u8>::zeros((height, width, channels));

    let levels = levels.max(2);
    let step = 255.0 / (levels - 1) as f32;
    let divisor = 256.0 / levels as f32;

    // Process only color channels (not alpha)
    let color_channels = if channels == 4 { 3 } else { channels };

    for y in 0..height {
        for x in 0..width {
            for c in 0..color_channels {
                let v = input[[y, x, c]] as f32;
                let level = (v / divisor).floor();
                output[[y, x, c]] = (level * step).clamp(0.0, 255.0) as u8;
            }
            if channels == 4 {
                output[[y, x, 3]] = input[[y, x, 3]];
            }
        }
    }
    output
}

/// Reduce color levels (posterize) - f32 version.
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels), values 0.0-1.0
/// * `levels` - Number of levels per channel (2-256)
///
/// # Returns
/// Posterized image with same channel count
pub fn posterize_f32(input: ArrayView3<f32>, levels: u8) -> Array3<f32> {
    let (height, width, channels) = input.dim();
    let mut output = Array3::<f32>::zeros((height, width, channels));

    let levels = levels.max(2) as f32;
    let step = 1.0 / (levels - 1.0);

    let color_channels = if channels == 4 { 3 } else { channels };

    for y in 0..height {
        for x in 0..width {
            for c in 0..color_channels {
                let v = input[[y, x, c]].clamp(0.0, 1.0);
                let level = (v * levels).floor().min(levels - 1.0);
                output[[y, x, c]] = level * step;
            }
            if channels == 4 {
                output[[y, x, 3]] = input[[y, x, 3]];
            }
        }
    }
    output
}

// ============================================================================
// Solarize
// ============================================================================

/// Apply solarize effect - u8 version.
///
/// Inverts tones above the threshold, creating a part-negative effect.
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels)
/// * `threshold` - Threshold value (0-255). Pixels above this are inverted.
///
/// # Returns
/// Solarized image with same channel count
pub fn solarize_u8(input: ArrayView3<u8>, threshold: u8) -> Array3<u8> {
    let (height, width, channels) = input.dim();
    let mut output = Array3::<u8>::zeros((height, width, channels));

    let color_channels = if channels == 4 { 3 } else { channels };

    for y in 0..height {
        for x in 0..width {
            for c in 0..color_channels {
                let v = input[[y, x, c]];
                output[[y, x, c]] = if v > threshold { 255 - v } else { v };
            }
            if channels == 4 {
                output[[y, x, 3]] = input[[y, x, 3]];
            }
        }
    }
    output
}

/// Apply solarize effect - f32 version.
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels), values 0.0-1.0
/// * `threshold` - Threshold value (0.0-1.0). Pixels above this are inverted.
///
/// # Returns
/// Solarized image with same channel count
pub fn solarize_f32(input: ArrayView3<f32>, threshold: f32) -> Array3<f32> {
    let (height, width, channels) = input.dim();
    let mut output = Array3::<f32>::zeros((height, width, channels));

    let color_channels = if channels == 4 { 3 } else { channels };

    for y in 0..height {
        for x in 0..width {
            for c in 0..color_channels {
                let v = input[[y, x, c]];
                output[[y, x, c]] = if v > threshold { 1.0 - v } else { v };
            }
            if channels == 4 {
                output[[y, x, 3]] = input[[y, x, 3]];
            }
        }
    }
    output
}

// ============================================================================
// Threshold
// ============================================================================

/// Apply binary threshold - u8 version.
///
/// For grayscale input, thresholds the single channel.
/// For RGB/RGBA, converts to luminosity first, then thresholds.
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels)
/// * `threshold` - Threshold value (0-255). Pixels are black or white.
///
/// # Returns
/// Thresholded image with same channel count (black and white)
pub fn threshold_u8(input: ArrayView3<u8>, threshold: u8) -> Array3<u8> {
    let (height, width, channels) = input.dim();
    let mut output = Array3::<u8>::zeros((height, width, channels));

    // BT.709 luminosity coefficients
    const LUMA_R: f32 = 0.2126;
    const LUMA_G: f32 = 0.7152;
    const LUMA_B: f32 = 0.0722;

    for y in 0..height {
        for x in 0..width {
            let lum = if channels == 1 {
                // Grayscale: use single channel directly
                input[[y, x, 0]]
            } else {
                // RGB/RGBA: compute luminosity
                let r = input[[y, x, 0]] as f32;
                let g = input[[y, x, 1]] as f32;
                let b = input[[y, x, 2]] as f32;
                (LUMA_R * r + LUMA_G * g + LUMA_B * b) as u8
            };

            let v = if lum > threshold { 255 } else { 0 };

            // Set all color channels to same value
            let color_channels = if channels == 4 { 3 } else { channels };
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

/// Apply binary threshold - f32 version.
///
/// For grayscale input, thresholds the single channel.
/// For RGB/RGBA, converts to luminosity first, then thresholds.
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels), values 0.0-1.0
/// * `threshold` - Threshold value (0.0-1.0). Pixels are black or white.
///
/// # Returns
/// Thresholded image with same channel count (black and white)
pub fn threshold_f32(input: ArrayView3<f32>, threshold: f32) -> Array3<f32> {
    let (height, width, channels) = input.dim();
    let mut output = Array3::<f32>::zeros((height, width, channels));

    const LUMA_R: f32 = 0.2126;
    const LUMA_G: f32 = 0.7152;
    const LUMA_B: f32 = 0.0722;

    for y in 0..height {
        for x in 0..width {
            let lum = if channels == 1 {
                // Grayscale: use single channel directly
                input[[y, x, 0]]
            } else {
                // RGB/RGBA: compute luminosity
                let r = input[[y, x, 0]];
                let g = input[[y, x, 1]];
                let b = input[[y, x, 2]];
                LUMA_R * r + LUMA_G * g + LUMA_B * b
            };

            let v = if lum > threshold { 1.0 } else { 0.0 };

            let color_channels = if channels == 4 { 3 } else { channels };
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

// ============================================================================
// Emboss
// ============================================================================

/// Apply emboss effect - u8 version.
///
/// Creates a 3D raised effect using directional convolution.
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels)
/// * `angle` - Light source angle in degrees (0-360)
/// * `depth` - Effect strength (0.0-10.0)
///
/// # Returns
/// Embossed image with same channel count
pub fn emboss_u8(input: ArrayView3<u8>, angle: f32, depth: f32) -> Array3<u8> {
    let (height, width, channels) = input.dim();
    let mut output = Array3::<u8>::zeros((height, width, channels));

    // Calculate kernel offsets based on angle
    let angle_rad = angle.to_radians();
    let dx = angle_rad.cos();
    let dy = angle_rad.sin();

    // Emboss kernel based on direction
    let kernel: [[f32; 3]; 3] = [
        [-dy * depth, -dx * depth - dy * depth, -dx * depth],
        [-dy * depth, 1.0, dy * depth],
        [dx * depth, dx * depth + dy * depth, dy * depth],
    ];

    let color_channels = if channels == 4 { 3 } else { channels };

    for y in 1..height.saturating_sub(1) {
        for x in 1..width.saturating_sub(1) {
            for c in 0..color_channels {
                let mut sum = 0.0f32;

                for ky in 0..3 {
                    for kx in 0..3 {
                        let py = y + ky - 1;
                        let px = x + kx - 1;
                        sum += input[[py, px, c]] as f32 * kernel[ky][kx];
                    }
                }

                // Add 128 to center the result around middle gray
                let v = (sum + 128.0).clamp(0.0, 255.0) as u8;
                output[[y, x, c]] = v;
            }
            if channels == 4 {
                output[[y, x, 3]] = input[[y, x, 3]];
            }
        }
    }

    // Copy edges
    for x in 0..width {
        for c in 0..channels {
            output[[0, x, c]] = input[[0, x, c]];
            if height > 1 {
                output[[height - 1, x, c]] = input[[height - 1, x, c]];
            }
        }
    }
    for y in 0..height {
        for c in 0..channels {
            output[[y, 0, c]] = input[[y, 0, c]];
            if width > 1 {
                output[[y, width - 1, c]] = input[[y, width - 1, c]];
            }
        }
    }

    output
}

/// Apply emboss effect - f32 version.
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels), values 0.0-1.0
/// * `angle` - Light source angle in degrees (0-360)
/// * `depth` - Effect strength (0.0-10.0)
///
/// # Returns
/// Embossed image with same channel count
pub fn emboss_f32(input: ArrayView3<f32>, angle: f32, depth: f32) -> Array3<f32> {
    let (height, width, channels) = input.dim();
    let mut output = Array3::<f32>::zeros((height, width, channels));

    let angle_rad = angle.to_radians();
    let dx = angle_rad.cos();
    let dy = angle_rad.sin();

    let kernel: [[f32; 3]; 3] = [
        [-dy * depth, -dx * depth - dy * depth, -dx * depth],
        [-dy * depth, 1.0, dy * depth],
        [dx * depth, dx * depth + dy * depth, dy * depth],
    ];

    let color_channels = if channels == 4 { 3 } else { channels };

    for y in 1..height.saturating_sub(1) {
        for x in 1..width.saturating_sub(1) {
            for c in 0..color_channels {
                let mut sum = 0.0f32;

                for ky in 0..3 {
                    for kx in 0..3 {
                        let py = y + ky - 1;
                        let px = x + kx - 1;
                        sum += input[[py, px, c]] * kernel[ky][kx];
                    }
                }

                // Add 0.5 to center the result around middle gray
                output[[y, x, c]] = (sum + 0.5).clamp(0.0, 1.0);
            }
            if channels == 4 {
                output[[y, x, 3]] = input[[y, x, 3]];
            }
        }
    }

    // Copy edges
    for x in 0..width {
        for c in 0..channels {
            output[[0, x, c]] = input[[0, x, c]];
            if height > 1 {
                output[[height - 1, x, c]] = input[[height - 1, x, c]];
            }
        }
    }
    for y in 0..height {
        for c in 0..channels {
            output[[y, 0, c]] = input[[y, 0, c]];
            if width > 1 {
                output[[y, width - 1, c]] = input[[y, width - 1, c]];
            }
        }
    }

    output
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_posterize_u8_2_levels() {
        let mut img = Array3::<u8>::zeros((1, 1, 4));
        img[[0, 0, 0]] = 100;
        img[[0, 0, 3]] = 255;

        let result = posterize_u8(img.view(), 2);

        // With 2 levels, should be either 0 or 255
        assert!(result[[0, 0, 0]] == 0 || result[[0, 0, 0]] == 255);
    }

    #[test]
    fn test_posterize_f32_4_levels() {
        let mut img = Array3::<f32>::zeros((1, 1, 4));
        img[[0, 0, 0]] = 0.6;
        img[[0, 0, 3]] = 1.0;

        let result = posterize_f32(img.view(), 4);

        // With 4 levels: 0, 0.333, 0.666, 1.0
        // 0.6 should map to 0.666
        assert!((result[[0, 0, 0]] - 0.666).abs() < 0.01);
    }

    #[test]
    fn test_solarize_u8_below_threshold() {
        let mut img = Array3::<u8>::zeros((1, 1, 4));
        img[[0, 0, 0]] = 100; // Below threshold of 128
        img[[0, 0, 3]] = 255;

        let result = solarize_u8(img.view(), 128);

        // Should not be inverted
        assert_eq!(result[[0, 0, 0]], 100);
    }

    #[test]
    fn test_solarize_u8_above_threshold() {
        let mut img = Array3::<u8>::zeros((1, 1, 4));
        img[[0, 0, 0]] = 200; // Above threshold of 128
        img[[0, 0, 3]] = 255;

        let result = solarize_u8(img.view(), 128);

        // Should be inverted: 255 - 200 = 55
        assert_eq!(result[[0, 0, 0]], 55);
    }

    #[test]
    fn test_threshold_u8() {
        let mut img = Array3::<u8>::zeros((1, 2, 4));
        img[[0, 0, 0]] = 50;  // Dark
        img[[0, 0, 1]] = 50;
        img[[0, 0, 2]] = 50;
        img[[0, 0, 3]] = 255;
        img[[0, 1, 0]] = 200; // Light
        img[[0, 1, 1]] = 200;
        img[[0, 1, 2]] = 200;
        img[[0, 1, 3]] = 255;

        let result = threshold_u8(img.view(), 128);

        assert_eq!(result[[0, 0, 0]], 0);   // Dark -> black
        assert_eq!(result[[0, 1, 0]], 255); // Light -> white
    }

    #[test]
    fn test_threshold_f32() {
        let mut img = Array3::<f32>::zeros((1, 1, 4));
        img[[0, 0, 0]] = 0.6;
        img[[0, 0, 1]] = 0.6;
        img[[0, 0, 2]] = 0.6;
        img[[0, 0, 3]] = 1.0;

        let result = threshold_f32(img.view(), 0.5);

        assert_eq!(result[[0, 0, 0]], 1.0); // Above threshold -> white
    }

    #[test]
    fn test_emboss_preserves_alpha() {
        let mut img = Array3::<u8>::zeros((3, 3, 4));
        for y in 0..3 {
            for x in 0..3 {
                img[[y, x, 0]] = 128;
                img[[y, x, 1]] = 128;
                img[[y, x, 2]] = 128;
                img[[y, x, 3]] = 200;
            }
        }

        let result = emboss_u8(img.view(), 45.0, 1.0);

        // Alpha should be preserved
        assert_eq!(result[[1, 1, 3]], 200);
    }
}
