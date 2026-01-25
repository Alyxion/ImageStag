//! Grayscale conversion filter.
//!
//! Works with both PyO3 (numpy) and WASM (JS).
//! Uses ITU-R BT.709 luminosity coefficients.
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
const LUMA_R: f32 = 0.2126;
const LUMA_G: f32 = 0.7152;
const LUMA_B: f32 = 0.0722;

// ============================================================================
// 8-bit (u8) Implementation
// ============================================================================

/// Convert RGBA u8 image to grayscale (luminosity method).
///
/// Output is RGBA with R=G=B=luminosity, A preserved.
/// Uses ITU-R BT.709 coefficients.
///
/// # Arguments
/// * `input` - 3D array view of shape (height, width, 4) with RGBA u8 values (0-255)
///
/// # Returns
/// New array with grayscale values in RGB channels, alpha preserved
pub fn grayscale_rgba_u8(input: ArrayView3<u8>) -> Array3<u8> {
    let (height, width, _) = input.dim();
    let mut output = Array3::<u8>::zeros((height, width, 4));

    for y in 0..height {
        for x in 0..width {
            let r = input[[y, x, 0]] as f32;
            let g = input[[y, x, 1]] as f32;
            let b = input[[y, x, 2]] as f32;
            let a = input[[y, x, 3]];

            // ITU-R BT.709 luminosity
            let gray = (LUMA_R * r + LUMA_G * g + LUMA_B * b) as u8;

            output[[y, x, 0]] = gray;
            output[[y, x, 1]] = gray;
            output[[y, x, 2]] = gray;
            output[[y, x, 3]] = a;
        }
    }

    output
}

/// Alias for backward compatibility
pub fn grayscale_rgba_impl(input: ArrayView3<u8>) -> Array3<u8> {
    grayscale_rgba_u8(input)
}

// ============================================================================
// Float (f32) Implementation
// ============================================================================

/// Convert RGBA f32 image to grayscale (luminosity method).
///
/// Output is RGBA with R=G=B=luminosity, A preserved.
/// Uses ITU-R BT.709 coefficients.
///
/// # Arguments
/// * `input` - 3D array view of shape (height, width, 4) with RGBA f32 values (0.0-1.0)
///
/// # Returns
/// New array with grayscale values in RGB channels, alpha preserved
pub fn grayscale_rgba_f32(input: ArrayView3<f32>) -> Array3<f32> {
    let (height, width, _) = input.dim();
    let mut output = Array3::<f32>::zeros((height, width, 4));

    for y in 0..height {
        for x in 0..width {
            let r = input[[y, x, 0]];
            let g = input[[y, x, 1]];
            let b = input[[y, x, 2]];
            let a = input[[y, x, 3]];

            // ITU-R BT.709 luminosity (same coefficients as u8)
            let gray = LUMA_R * r + LUMA_G * g + LUMA_B * b;

            output[[y, x, 0]] = gray;
            output[[y, x, 1]] = gray;
            output[[y, x, 2]] = gray;
            output[[y, x, 3]] = a;
        }
    }

    output
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
    // u8 Tests
    // ========================================================================

    #[test]
    fn test_grayscale_u8_red() {
        let mut img = Array3::<u8>::zeros((1, 1, 4));
        img[[0, 0, 0]] = 255; // R
        img[[0, 0, 3]] = 255; // A

        let result = grayscale_rgba_u8(img.view());

        // 0.2126 * 255 ≈ 54
        assert!((result[[0, 0, 0]] as i32 - 54).abs() <= 1);
        assert_eq!(result[[0, 0, 0]], result[[0, 0, 1]]);
        assert_eq!(result[[0, 0, 1]], result[[0, 0, 2]]);
        assert_eq!(result[[0, 0, 3]], 255);
    }

    #[test]
    fn test_grayscale_u8_green() {
        let mut img = Array3::<u8>::zeros((1, 1, 4));
        img[[0, 0, 1]] = 255; // G
        img[[0, 0, 3]] = 255; // A

        let result = grayscale_rgba_u8(img.view());

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

        let result = grayscale_rgba_u8(img.view());
        assert_eq!(result[[0, 0, 3]], 100);
    }

    // ========================================================================
    // f32 Tests
    // ========================================================================

    #[test]
    fn test_grayscale_f32_red() {
        let mut img = Array3::<f32>::zeros((1, 1, 4));
        img[[0, 0, 0]] = 1.0; // R
        img[[0, 0, 3]] = 1.0; // A

        let result = grayscale_rgba_f32(img.view());

        // 0.2126 * 1.0 = 0.2126
        assert!((result[[0, 0, 0]] - LUMA_R).abs() < 0.0001);
        assert_eq!(result[[0, 0, 0]], result[[0, 0, 1]]);
        assert_eq!(result[[0, 0, 1]], result[[0, 0, 2]]);
        assert_eq!(result[[0, 0, 3]], 1.0);
    }

    #[test]
    fn test_grayscale_f32_green() {
        let mut img = Array3::<f32>::zeros((1, 1, 4));
        img[[0, 0, 1]] = 1.0; // G
        img[[0, 0, 3]] = 1.0; // A

        let result = grayscale_rgba_f32(img.view());

        // 0.7152 * 1.0 = 0.7152
        assert!((result[[0, 0, 0]] - LUMA_G).abs() < 0.0001);
    }

    #[test]
    fn test_grayscale_f32_white() {
        let mut img = Array3::<f32>::zeros((1, 1, 4));
        img[[0, 0, 0]] = 1.0;
        img[[0, 0, 1]] = 1.0;
        img[[0, 0, 2]] = 1.0;
        img[[0, 0, 3]] = 1.0;

        let result = grayscale_rgba_f32(img.view());

        // 0.2126 + 0.7152 + 0.0722 = 1.0
        assert!((result[[0, 0, 0]] - 1.0).abs() < 0.0001);
    }

    #[test]
    fn test_grayscale_f32_preserves_alpha() {
        let mut img = Array3::<f32>::zeros((1, 1, 4));
        img[[0, 0, 0]] = 0.5;
        img[[0, 0, 1]] = 0.5;
        img[[0, 0, 2]] = 0.5;
        img[[0, 0, 3]] = 0.39; // ~100/255

        let result = grayscale_rgba_f32(img.view());
        assert!((result[[0, 0, 3]] - 0.39).abs() < 0.0001);
    }

    // ========================================================================
    // u8 vs f32 Comparison Tests
    // ========================================================================

    #[test]
    fn test_u8_f32_consistency() {
        // Create u8 image
        let mut img_u8 = Array3::<u8>::zeros((1, 1, 4));
        img_u8[[0, 0, 0]] = 200; // R
        img_u8[[0, 0, 1]] = 100; // G
        img_u8[[0, 0, 2]] = 50;  // B
        img_u8[[0, 0, 3]] = 255; // A

        // Convert to f32
        let img_f32 = u8_to_f32(img_u8.view());

        // Process both
        let result_u8 = grayscale_rgba_u8(img_u8.view());
        let result_f32 = grayscale_rgba_f32(img_f32.view());

        // Convert f32 result to u8 for comparison
        let result_f32_as_u8 = f32_to_u8(result_f32.view());

        // Should match within 1 (rounding difference)
        let diff = (result_u8[[0, 0, 0]] as i32 - result_f32_as_u8[[0, 0, 0]] as i32).abs();
        assert!(diff <= 1, "u8 and f32 results should match within 1, got diff={}", diff);
    }

    #[test]
    fn test_12bit_roundtrip() {
        // Create f32 image with precise values
        let mut img = Array3::<f32>::zeros((1, 1, 4));
        img[[0, 0, 0]] = 0.123456;
        img[[0, 0, 1]] = 0.654321;
        img[[0, 0, 2]] = 0.333333;
        img[[0, 0, 3]] = 1.0;

        // Convert to 12-bit and back
        let as_12bit = f32_to_u16_12bit(img.view());
        let back_to_f32 = u16_12bit_to_f32(as_12bit.view());

        // 12-bit precision: 1/4095 ≈ 0.000244
        // Max error should be less than 1 step (accounts for rounding at boundaries)
        let max_error = 1.0 / 4095.0;
        for i in 0..4 {
            let diff = (img[[0, 0, i]] - back_to_f32[[0, 0, i]]).abs();
            assert!(diff < max_error, "12-bit roundtrip error too large: {}", diff);
        }
    }
}
