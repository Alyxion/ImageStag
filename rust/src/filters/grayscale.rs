//! Grayscale conversion filter.
//!
//! Works with both PyO3 (numpy) and WASM (JS).
//! Uses ITU-R BT.709 luminosity coefficients.
//!
//! ## Supported Formats
//!
//! All filters accept images with 1, 3, or 4 channels:
//! - **Grayscale**: (height, width, 1) - no-op, returns copy
//! - **RGB**: (height, width, 3) - converts to R=G=B=luminosity
//! - **RGBA**: (height, width, 4) - converts to R=G=B=luminosity, alpha preserved
//!
//! ## Bit Depth Support
//!
//! - **u8 (8-bit)**: Values 0-255, standard for web/display
//! - **f32 (float)**: Values 0.0-1.0, for HDR/linear workflows
//!
//! Both versions use identical algorithms. The f32 version preserves
//! full precision for chained operations.

use ndarray::{Array3, ArrayView3};

/// ITU-R BT.709 luminosity coefficients (same for all bit depths)
pub const LUMA_R: f32 = 0.2126;
pub const LUMA_G: f32 = 0.7152;
pub const LUMA_B: f32 = 0.0722;

/// RGB channel weights for grayscale conversion.
/// Default uses BT.709 coefficients. Custom weights allow
/// Photoshop-style Black & White adjustments.
#[derive(Clone, Copy, Debug)]
pub struct GrayscaleWeights {
    pub r: f32,
    pub g: f32,
    pub b: f32,
}

impl Default for GrayscaleWeights {
    fn default() -> Self {
        Self {
            r: LUMA_R,
            g: LUMA_G,
            b: LUMA_B,
        }
    }
}

impl GrayscaleWeights {
    /// BT.709 luminosity (default)
    pub fn bt709() -> Self {
        Self::default()
    }

    /// Simple average (R+G+B)/3
    pub fn average() -> Self {
        Self { r: 1.0/3.0, g: 1.0/3.0, b: 1.0/3.0 }
    }

    /// Lightness: (max(R,G,B) + min(R,G,B)) / 2
    /// Note: This requires special handling, not just weights
    pub fn lightness() -> Self {
        // Approximation - true lightness needs min/max
        Self { r: 0.5, g: 0.5, b: 0.0 }
    }

    /// Create custom weights (normalized automatically)
    pub fn custom(r: f32, g: f32, b: f32) -> Self {
        let sum = (r + g + b).abs().max(0.001);
        Self {
            r: r / sum,
            g: g / sum,
            b: b / sum,
        }
    }
}

// ============================================================================
// 8-bit (u8) Implementation
// ============================================================================

/// Convert image to grayscale with custom RGB weights - u8 version.
///
/// Output has same channel count as input:
/// - Grayscale (1ch): no-op, returns copy
/// - RGB (3ch): R=G=B=weighted_luminosity
/// - RGBA (4ch): R=G=B=weighted_luminosity, alpha preserved
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels)
/// * `weights` - RGB channel weights for conversion
///
/// # Returns
/// Grayscale image with same channel count
pub fn grayscale_weighted_u8(input: ArrayView3<u8>, weights: GrayscaleWeights) -> Array3<u8> {
    let (height, width, channels) = input.dim();
    let mut output = Array3::<u8>::zeros((height, width, channels));

    match channels {
        1 => {
            // Grayscale input - just copy
            for y in 0..height {
                for x in 0..width {
                    output[[y, x, 0]] = input[[y, x, 0]];
                }
            }
        }
        3 => {
            // RGB input
            for y in 0..height {
                for x in 0..width {
                    let r = input[[y, x, 0]] as f32;
                    let g = input[[y, x, 1]] as f32;
                    let b = input[[y, x, 2]] as f32;
                    let gray = (weights.r * r + weights.g * g + weights.b * b).clamp(0.0, 255.0) as u8;
                    output[[y, x, 0]] = gray;
                    output[[y, x, 1]] = gray;
                    output[[y, x, 2]] = gray;
                }
            }
        }
        4 => {
            // RGBA input
            for y in 0..height {
                for x in 0..width {
                    let r = input[[y, x, 0]] as f32;
                    let g = input[[y, x, 1]] as f32;
                    let b = input[[y, x, 2]] as f32;
                    let gray = (weights.r * r + weights.g * g + weights.b * b).clamp(0.0, 255.0) as u8;
                    output[[y, x, 0]] = gray;
                    output[[y, x, 1]] = gray;
                    output[[y, x, 2]] = gray;
                    output[[y, x, 3]] = input[[y, x, 3]];
                }
            }
        }
        _ => {
            // Unsupported channel count - copy as-is
            for y in 0..height {
                for x in 0..width {
                    for c in 0..channels {
                        output[[y, x, c]] = input[[y, x, c]];
                    }
                }
            }
        }
    }

    output
}

/// Convert image to grayscale (luminosity method) - u8 version.
///
/// Output has same channel count as input:
/// - Grayscale (1ch): no-op, returns copy
/// - RGB (3ch): R=G=B=luminosity
/// - RGBA (4ch): R=G=B=luminosity, alpha preserved
///
/// Uses ITU-R BT.709 coefficients.
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels)
///
/// # Returns
/// Grayscale image with same channel count
pub fn grayscale_u8(input: ArrayView3<u8>) -> Array3<u8> {
    grayscale_weighted_u8(input, GrayscaleWeights::default())
}


/// Backward-compatible alias for RGBA-only version
pub fn grayscale_rgba_u8(input: ArrayView3<u8>) -> Array3<u8> {
    grayscale_u8(input)
}

/// Alias for backward compatibility
pub fn grayscale_rgba_impl(input: ArrayView3<u8>) -> Array3<u8> {
    grayscale_u8(input)
}

// ============================================================================
// Float (f32) Implementation
// ============================================================================

/// Convert image to grayscale with custom RGB weights - f32 version.
///
/// Output has same channel count as input:
/// - Grayscale (1ch): no-op, returns copy
/// - RGB (3ch): R=G=B=weighted_luminosity
/// - RGBA (4ch): R=G=B=weighted_luminosity, alpha preserved
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels), values 0.0-1.0
/// * `weights` - RGB channel weights for conversion
///
/// # Returns
/// Grayscale image with same channel count
pub fn grayscale_weighted_f32(input: ArrayView3<f32>, weights: GrayscaleWeights) -> Array3<f32> {
    let (height, width, channels) = input.dim();
    let mut output = Array3::<f32>::zeros((height, width, channels));

    match channels {
        1 => {
            // Grayscale input - just copy
            for y in 0..height {
                for x in 0..width {
                    output[[y, x, 0]] = input[[y, x, 0]];
                }
            }
        }
        3 => {
            // RGB input
            for y in 0..height {
                for x in 0..width {
                    let r = input[[y, x, 0]];
                    let g = input[[y, x, 1]];
                    let b = input[[y, x, 2]];
                    let gray = (weights.r * r + weights.g * g + weights.b * b).clamp(0.0, 1.0);
                    output[[y, x, 0]] = gray;
                    output[[y, x, 1]] = gray;
                    output[[y, x, 2]] = gray;
                }
            }
        }
        4 => {
            // RGBA input
            for y in 0..height {
                for x in 0..width {
                    let r = input[[y, x, 0]];
                    let g = input[[y, x, 1]];
                    let b = input[[y, x, 2]];
                    let gray = (weights.r * r + weights.g * g + weights.b * b).clamp(0.0, 1.0);
                    output[[y, x, 0]] = gray;
                    output[[y, x, 1]] = gray;
                    output[[y, x, 2]] = gray;
                    output[[y, x, 3]] = input[[y, x, 3]];
                }
            }
        }
        _ => {
            // Unsupported channel count - copy as-is
            for y in 0..height {
                for x in 0..width {
                    for c in 0..channels {
                        output[[y, x, c]] = input[[y, x, c]];
                    }
                }
            }
        }
    }

    output
}

/// Convert image to grayscale (luminosity method) - f32 version.
///
/// Uses ITU-R BT.709 coefficients.
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels), values 0.0-1.0
///
/// # Returns
/// Grayscale image with same channel count
pub fn grayscale_f32(input: ArrayView3<f32>) -> Array3<f32> {
    grayscale_weighted_f32(input, GrayscaleWeights::default())
}

/// Backward-compatible alias for RGBA-only version
pub fn grayscale_rgba_f32(input: ArrayView3<f32>) -> Array3<f32> {
    grayscale_f32(input)
}

// ============================================================================
// Conversion Utilities
// ============================================================================

/// Convert u8 image (0-255) to f32 (0.0-1.0)
pub fn u8_to_f32(input: ArrayView3<u8>) -> Array3<f32> {
    input.mapv(|v| v as f32 / 255.0)
}

/// Convert f32 image (0.0-1.0) to u8 (0-255)
pub fn f32_to_u8(input: ArrayView3<f32>) -> Array3<u8> {
    input.mapv(|v| (v.clamp(0.0, 1.0) * 255.0) as u8)
}

/// Convert f32 image (0.0-1.0) to u16 for 12-bit storage (0-4095)
pub fn f32_to_u16_12bit(input: ArrayView3<f32>) -> Array3<u16> {
    input.mapv(|v| (v.clamp(0.0, 1.0) * 4095.0) as u16)
}

/// Convert u16 12-bit (0-4095) to f32 (0.0-1.0)
pub fn u16_12bit_to_f32(input: ArrayView3<u16>) -> Array3<f32> {
    input.mapv(|v| v as f32 / 4095.0)
}

#[cfg(test)]
mod tests {
    use super::*;
    use ndarray::Array3;

    // ========================================================================
    // u8 Tests - All Channel Configurations
    // ========================================================================

    #[test]
    fn test_grayscale_u8_rgba_red() {
        let mut img = Array3::<u8>::zeros((1, 1, 4));
        img[[0, 0, 0]] = 255; // R
        img[[0, 0, 3]] = 255; // A

        let result = grayscale_u8(img.view());

        // 0.2126 * 255 ≈ 54
        assert!((result[[0, 0, 0]] as i32 - 54).abs() <= 1);
        assert_eq!(result[[0, 0, 0]], result[[0, 0, 1]]);
        assert_eq!(result[[0, 0, 1]], result[[0, 0, 2]]);
        assert_eq!(result[[0, 0, 3]], 255);
    }

    #[test]
    fn test_grayscale_u8_rgb() {
        let mut img = Array3::<u8>::zeros((1, 1, 3));
        img[[0, 0, 0]] = 255; // R
        img[[0, 0, 1]] = 0;   // G
        img[[0, 0, 2]] = 0;   // B

        let result = grayscale_u8(img.view());

        assert_eq!(result.dim().2, 3); // Still 3 channels
        assert!((result[[0, 0, 0]] as i32 - 54).abs() <= 1);
        assert_eq!(result[[0, 0, 0]], result[[0, 0, 1]]);
        assert_eq!(result[[0, 0, 1]], result[[0, 0, 2]]);
    }

    #[test]
    fn test_grayscale_u8_grayscale_noop() {
        let mut img = Array3::<u8>::zeros((1, 1, 1));
        img[[0, 0, 0]] = 128;

        let result = grayscale_u8(img.view());

        assert_eq!(result.dim().2, 1); // Still 1 channel
        assert_eq!(result[[0, 0, 0]], 128); // Unchanged
    }

    #[test]
    fn test_grayscale_u8_green() {
        let mut img = Array3::<u8>::zeros((1, 1, 4));
        img[[0, 0, 1]] = 255; // G
        img[[0, 0, 3]] = 255; // A

        let result = grayscale_u8(img.view());

        // 0.7152 * 255 ≈ 182
        assert!((result[[0, 0, 0]] as i32 - 182).abs() <= 1);
    }

    #[test]
    fn test_grayscale_u8_preserves_alpha() {
        let mut img = Array3::<u8>::zeros((1, 1, 4));
        img[[0, 0, 0]] = 128;
        img[[0, 0, 1]] = 128;
        img[[0, 0, 2]] = 128;
        img[[0, 0, 3]] = 100;

        let result = grayscale_u8(img.view());
        assert_eq!(result[[0, 0, 3]], 100);
    }

    // ========================================================================
    // f32 Tests - All Channel Configurations
    // ========================================================================

    #[test]
    fn test_grayscale_f32_rgba_red() {
        let mut img = Array3::<f32>::zeros((1, 1, 4));
        img[[0, 0, 0]] = 1.0; // R
        img[[0, 0, 3]] = 1.0; // A

        let result = grayscale_f32(img.view());

        assert!((result[[0, 0, 0]] - LUMA_R).abs() < 0.0001);
        assert_eq!(result[[0, 0, 0]], result[[0, 0, 1]]);
        assert_eq!(result[[0, 0, 1]], result[[0, 0, 2]]);
        assert_eq!(result[[0, 0, 3]], 1.0);
    }

    #[test]
    fn test_grayscale_f32_rgb() {
        let mut img = Array3::<f32>::zeros((1, 1, 3));
        img[[0, 0, 0]] = 1.0; // R

        let result = grayscale_f32(img.view());

        assert_eq!(result.dim().2, 3); // Still 3 channels
        assert!((result[[0, 0, 0]] - LUMA_R).abs() < 0.0001);
    }

    #[test]
    fn test_grayscale_f32_grayscale_noop() {
        let mut img = Array3::<f32>::zeros((1, 1, 1));
        img[[0, 0, 0]] = 0.5;

        let result = grayscale_f32(img.view());

        assert_eq!(result.dim().2, 1); // Still 1 channel
        assert!((result[[0, 0, 0]] - 0.5).abs() < 0.0001); // Unchanged
    }

    #[test]
    fn test_grayscale_f32_green() {
        let mut img = Array3::<f32>::zeros((1, 1, 4));
        img[[0, 0, 1]] = 1.0; // G
        img[[0, 0, 3]] = 1.0; // A

        let result = grayscale_f32(img.view());

        assert!((result[[0, 0, 0]] - LUMA_G).abs() < 0.0001);
    }

    #[test]
    fn test_grayscale_f32_white() {
        let mut img = Array3::<f32>::zeros((1, 1, 4));
        img[[0, 0, 0]] = 1.0;
        img[[0, 0, 1]] = 1.0;
        img[[0, 0, 2]] = 1.0;
        img[[0, 0, 3]] = 1.0;

        let result = grayscale_f32(img.view());

        // 0.2126 + 0.7152 + 0.0722 = 1.0
        assert!((result[[0, 0, 0]] - 1.0).abs() < 0.0001);
    }

    #[test]
    fn test_grayscale_f32_preserves_alpha() {
        let mut img = Array3::<f32>::zeros((1, 1, 4));
        img[[0, 0, 0]] = 0.5;
        img[[0, 0, 1]] = 0.5;
        img[[0, 0, 2]] = 0.5;
        img[[0, 0, 3]] = 0.39;

        let result = grayscale_f32(img.view());
        assert!((result[[0, 0, 3]] - 0.39).abs() < 0.0001);
    }

    // ========================================================================
    // u8 vs f32 Comparison Tests
    // ========================================================================

    #[test]
    fn test_u8_f32_consistency() {
        let mut img_u8 = Array3::<u8>::zeros((1, 1, 4));
        img_u8[[0, 0, 0]] = 200;
        img_u8[[0, 0, 1]] = 100;
        img_u8[[0, 0, 2]] = 50;
        img_u8[[0, 0, 3]] = 255;

        let img_f32 = u8_to_f32(img_u8.view());

        let result_u8 = grayscale_u8(img_u8.view());
        let result_f32 = grayscale_f32(img_f32.view());

        let result_f32_as_u8 = f32_to_u8(result_f32.view());

        let diff = (result_u8[[0, 0, 0]] as i32 - result_f32_as_u8[[0, 0, 0]] as i32).abs();
        assert!(diff <= 1, "u8 and f32 results should match within 1, got diff={}", diff);
    }

    #[test]
    fn test_12bit_roundtrip() {
        let mut img = Array3::<f32>::zeros((1, 1, 4));
        img[[0, 0, 0]] = 0.123456;
        img[[0, 0, 1]] = 0.654321;
        img[[0, 0, 2]] = 0.333333;
        img[[0, 0, 3]] = 1.0;

        let as_12bit = f32_to_u16_12bit(img.view());
        let back_to_f32 = u16_12bit_to_f32(as_12bit.view());

        let max_error = 1.0 / 4095.0;
        for i in 0..4 {
            let diff = (img[[0, 0, i]] - back_to_f32[[0, 0, i]]).abs();
            assert!(diff < max_error, "12-bit roundtrip error too large: {}", diff);
        }
    }
}
