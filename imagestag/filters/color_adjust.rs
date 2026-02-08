//! Color adjustment filters: Brightness, Contrast, Saturation, Gamma, Exposure, Invert,
//! Equalize Histogram.
//!
//! These are pixel-wise operations that don't require spatial context.
//! All filters support both u8 (0-255) and f32 (0.0-1.0) modes.
//!
//! ## Supported Formats
//!
//! All filters accept images with 1, 3, or 4 channels:
//! - **Grayscale**: (height, width, 1) - single luminance channel
//! - **RGB**: (height, width, 3) - red, green, blue
//! - **RGBA**: (height, width, 4) - red, green, blue, alpha
//!
//! Channel count is inferred from the input array dimensions.
//! Alpha channel (if present) is always preserved unchanged.

use ndarray::{Array3, ArrayView3};

// ============================================================================
// Brightness
// ============================================================================

/// Adjust image brightness (u8 version).
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels)
/// * `amount` - Brightness adjustment: -1.0 (black) to 1.0 (white), 0.0 = no change
///
/// # Returns
/// Brightness-adjusted image with same channel count
pub fn brightness_u8(input: ArrayView3<u8>, amount: f32) -> Array3<u8> {
    let (height, width, channels) = input.dim();
    let mut output = Array3::<u8>::zeros((height, width, channels));
    let offset = amount * 255.0;

    // Determine how many color channels to process (exclude alpha if present)
    let color_channels = if channels == 4 { 3 } else { channels };

    for y in 0..height {
        for x in 0..width {
            for c in 0..color_channels {
                let v = input[[y, x, c]] as f32 + offset;
                output[[y, x, c]] = v.clamp(0.0, 255.0) as u8;
            }
            // Preserve alpha if present
            if channels == 4 {
                output[[y, x, 3]] = input[[y, x, 3]];
            }
        }
    }
    output
}

/// Adjust image brightness (f32 version).
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels), values 0.0-1.0
/// * `amount` - Brightness adjustment: -1.0 (black) to 1.0 (white), 0.0 = no change
///
/// # Returns
/// Brightness-adjusted image with same channel count
pub fn brightness_f32(input: ArrayView3<f32>, amount: f32) -> Array3<f32> {
    let (height, width, channels) = input.dim();
    let mut output = Array3::<f32>::zeros((height, width, channels));

    let color_channels = if channels == 4 { 3 } else { channels };

    for y in 0..height {
        for x in 0..width {
            for c in 0..color_channels {
                output[[y, x, c]] = (input[[y, x, c]] + amount).clamp(0.0, 1.0);
            }
            if channels == 4 {
                output[[y, x, 3]] = input[[y, x, 3]];
            }
        }
    }
    output
}

// ============================================================================
// Contrast
// ============================================================================

/// Adjust image contrast (u8 version).
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels)
/// * `amount` - Contrast adjustment: -1.0 (gray) to 1.0 (max contrast), 0.0 = no change
///
/// # Returns
/// Contrast-adjusted image with same channel count
pub fn contrast_u8(input: ArrayView3<u8>, amount: f32) -> Array3<u8> {
    let (height, width, channels) = input.dim();
    let mut output = Array3::<u8>::zeros((height, width, channels));

    let factor = if amount >= 0.0 {
        1.0 + amount * 3.0
    } else {
        1.0 + amount
    };

    let color_channels = if channels == 4 { 3 } else { channels };

    for y in 0..height {
        for x in 0..width {
            for c in 0..color_channels {
                let v = input[[y, x, c]] as f32;
                let adjusted = (v - 127.5) * factor + 127.5;
                output[[y, x, c]] = adjusted.clamp(0.0, 255.0) as u8;
            }
            if channels == 4 {
                output[[y, x, 3]] = input[[y, x, 3]];
            }
        }
    }
    output
}

/// Adjust image contrast (f32 version).
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels), values 0.0-1.0
/// * `amount` - Contrast adjustment: -1.0 (gray) to 1.0 (max contrast), 0.0 = no change
///
/// # Returns
/// Contrast-adjusted image with same channel count
pub fn contrast_f32(input: ArrayView3<f32>, amount: f32) -> Array3<f32> {
    let (height, width, channels) = input.dim();
    let mut output = Array3::<f32>::zeros((height, width, channels));

    let factor = if amount >= 0.0 {
        1.0 + amount * 3.0
    } else {
        1.0 + amount
    };

    let color_channels = if channels == 4 { 3 } else { channels };

    for y in 0..height {
        for x in 0..width {
            for c in 0..color_channels {
                let v = input[[y, x, c]];
                let adjusted = (v - 0.5) * factor + 0.5;
                output[[y, x, c]] = adjusted.clamp(0.0, 1.0);
            }
            if channels == 4 {
                output[[y, x, 3]] = input[[y, x, 3]];
            }
        }
    }
    output
}

// ============================================================================
// Saturation
// ============================================================================

/// Adjust image saturation (u8 version).
///
/// For grayscale images, this is a no-op (saturation requires color channels).
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels)
/// * `amount` - Saturation adjustment: -1.0 (grayscale) to 1.0 (vivid), 0.0 = no change
///
/// # Returns
/// Saturation-adjusted image with same channel count
pub fn saturation_u8(input: ArrayView3<u8>, amount: f32) -> Array3<u8> {
    let (height, width, channels) = input.dim();
    let mut output = Array3::<u8>::zeros((height, width, channels));

    // Saturation only makes sense for RGB/RGBA
    if channels == 1 {
        // Just copy grayscale
        for y in 0..height {
            for x in 0..width {
                output[[y, x, 0]] = input[[y, x, 0]];
            }
        }
        return output;
    }

    let factor = 1.0 + amount;

    // BT.709 luminosity coefficients
    const LUMA_R: f32 = 0.2126;
    const LUMA_G: f32 = 0.7152;
    const LUMA_B: f32 = 0.0722;

    for y in 0..height {
        for x in 0..width {
            let r = input[[y, x, 0]] as f32;
            let g = input[[y, x, 1]] as f32;
            let b = input[[y, x, 2]] as f32;

            let gray = LUMA_R * r + LUMA_G * g + LUMA_B * b;

            output[[y, x, 0]] = (gray + (r - gray) * factor).clamp(0.0, 255.0) as u8;
            output[[y, x, 1]] = (gray + (g - gray) * factor).clamp(0.0, 255.0) as u8;
            output[[y, x, 2]] = (gray + (b - gray) * factor).clamp(0.0, 255.0) as u8;

            if channels == 4 {
                output[[y, x, 3]] = input[[y, x, 3]];
            }
        }
    }
    output
}

/// Adjust image saturation (f32 version).
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels), values 0.0-1.0
/// * `amount` - Saturation adjustment: -1.0 (grayscale) to 1.0 (vivid), 0.0 = no change
///
/// # Returns
/// Saturation-adjusted image with same channel count
pub fn saturation_f32(input: ArrayView3<f32>, amount: f32) -> Array3<f32> {
    let (height, width, channels) = input.dim();
    let mut output = Array3::<f32>::zeros((height, width, channels));

    if channels == 1 {
        for y in 0..height {
            for x in 0..width {
                output[[y, x, 0]] = input[[y, x, 0]];
            }
        }
        return output;
    }

    let factor = 1.0 + amount;

    const LUMA_R: f32 = 0.2126;
    const LUMA_G: f32 = 0.7152;
    const LUMA_B: f32 = 0.0722;

    for y in 0..height {
        for x in 0..width {
            let r = input[[y, x, 0]];
            let g = input[[y, x, 1]];
            let b = input[[y, x, 2]];

            let gray = LUMA_R * r + LUMA_G * g + LUMA_B * b;

            output[[y, x, 0]] = (gray + (r - gray) * factor).clamp(0.0, 1.0);
            output[[y, x, 1]] = (gray + (g - gray) * factor).clamp(0.0, 1.0);
            output[[y, x, 2]] = (gray + (b - gray) * factor).clamp(0.0, 1.0);

            if channels == 4 {
                output[[y, x, 3]] = input[[y, x, 3]];
            }
        }
    }
    output
}

// ============================================================================
// Gamma
// ============================================================================

/// Apply gamma correction (u8 version).
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels)
/// * `gamma` - Gamma value: < 1.0 brightens, > 1.0 darkens, 1.0 = no change
///
/// # Returns
/// Gamma-corrected image with same channel count
pub fn gamma_u8(input: ArrayView3<u8>, gamma: f32) -> Array3<u8> {
    let (height, width, channels) = input.dim();
    let mut output = Array3::<u8>::zeros((height, width, channels));

    let inv_gamma = 1.0 / gamma.max(0.001);
    let color_channels = if channels == 4 { 3 } else { channels };

    for y in 0..height {
        for x in 0..width {
            for c in 0..color_channels {
                let v = input[[y, x, c]] as f32 / 255.0;
                let corrected = v.powf(inv_gamma);
                output[[y, x, c]] = (corrected * 255.0).clamp(0.0, 255.0) as u8;
            }
            if channels == 4 {
                output[[y, x, 3]] = input[[y, x, 3]];
            }
        }
    }
    output
}

/// Apply gamma correction (f32 version).
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels), values 0.0-1.0
/// * `gamma` - Gamma value: < 1.0 brightens, > 1.0 darkens, 1.0 = no change
///
/// # Returns
/// Gamma-corrected image with same channel count
pub fn gamma_f32(input: ArrayView3<f32>, gamma: f32) -> Array3<f32> {
    let (height, width, channels) = input.dim();
    let mut output = Array3::<f32>::zeros((height, width, channels));

    let inv_gamma = 1.0 / gamma.max(0.001);
    let color_channels = if channels == 4 { 3 } else { channels };

    for y in 0..height {
        for x in 0..width {
            for c in 0..color_channels {
                let v = input[[y, x, c]].clamp(0.0, 1.0);
                output[[y, x, c]] = v.powf(inv_gamma);
            }
            if channels == 4 {
                output[[y, x, 3]] = input[[y, x, 3]];
            }
        }
    }
    output
}

// ============================================================================
// Exposure
// ============================================================================

/// Adjust image exposure (u8 version).
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels)
/// * `exposure` - Exposure stops: negative darkens, positive brightens, 0.0 = no change
/// * `offset` - Black point offset: -1.0 to 1.0, 0.0 = no change
/// * `gamma` - Gamma correction: 0.1 to 10.0, 1.0 = no change
///
/// # Returns
/// Exposure-adjusted image with same channel count
pub fn exposure_u8(input: ArrayView3<u8>, exposure: f32, offset: f32, gamma: f32) -> Array3<u8> {
    let (height, width, channels) = input.dim();
    let mut output = Array3::<u8>::zeros((height, width, channels));

    let multiplier = 2.0_f32.powf(exposure);
    let inv_gamma = 1.0 / gamma.max(0.001);
    let color_channels = if channels == 4 { 3 } else { channels };

    for y in 0..height {
        for x in 0..width {
            for c in 0..color_channels {
                let v = input[[y, x, c]] as f32 / 255.0;
                let exposed = (v * multiplier + offset).clamp(0.0, 1.0);
                let corrected = exposed.powf(inv_gamma);
                output[[y, x, c]] = (corrected * 255.0).clamp(0.0, 255.0) as u8;
            }
            if channels == 4 {
                output[[y, x, 3]] = input[[y, x, 3]];
            }
        }
    }
    output
}

/// Adjust image exposure (f32 version).
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels), values 0.0-1.0
/// * `exposure` - Exposure stops: negative darkens, positive brightens, 0.0 = no change
/// * `offset` - Black point offset: -1.0 to 1.0, 0.0 = no change
/// * `gamma` - Gamma correction: 0.1 to 10.0, 1.0 = no change
///
/// # Returns
/// Exposure-adjusted image with same channel count
pub fn exposure_f32(input: ArrayView3<f32>, exposure: f32, offset: f32, gamma: f32) -> Array3<f32> {
    let (height, width, channels) = input.dim();
    let mut output = Array3::<f32>::zeros((height, width, channels));

    let multiplier = 2.0_f32.powf(exposure);
    let inv_gamma = 1.0 / gamma.max(0.001);
    let color_channels = if channels == 4 { 3 } else { channels };

    for y in 0..height {
        for x in 0..width {
            for c in 0..color_channels {
                let v = input[[y, x, c]];
                let exposed = (v * multiplier + offset).clamp(0.0, 1.0);
                output[[y, x, c]] = exposed.powf(inv_gamma);
            }
            if channels == 4 {
                output[[y, x, 3]] = input[[y, x, 3]];
            }
        }
    }
    output
}

// ============================================================================
// Invert
// ============================================================================

/// Invert image colors (u8 version).
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels)
///
/// # Returns
/// Color-inverted image (alpha preserved if present)
pub fn invert_u8(input: ArrayView3<u8>) -> Array3<u8> {
    let (height, width, channels) = input.dim();
    let mut output = Array3::<u8>::zeros((height, width, channels));

    let color_channels = if channels == 4 { 3 } else { channels };

    for y in 0..height {
        for x in 0..width {
            for c in 0..color_channels {
                output[[y, x, c]] = 255 - input[[y, x, c]];
            }
            if channels == 4 {
                output[[y, x, 3]] = input[[y, x, 3]];
            }
        }
    }
    output
}

/// Invert image colors (f32 version).
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels), values 0.0-1.0
///
/// # Returns
/// Color-inverted image (alpha preserved if present)
pub fn invert_f32(input: ArrayView3<f32>) -> Array3<f32> {
    let (height, width, channels) = input.dim();
    let mut output = Array3::<f32>::zeros((height, width, channels));

    let color_channels = if channels == 4 { 3 } else { channels };

    for y in 0..height {
        for x in 0..width {
            for c in 0..color_channels {
                output[[y, x, c]] = 1.0 - input[[y, x, c]];
            }
            if channels == 4 {
                output[[y, x, 3]] = input[[y, x, 3]];
            }
        }
    }
    output
}

// ============================================================================
// Equalize Histogram
// ============================================================================

/// Equalize image histogram (u8 version).
///
/// Performs per-channel histogram equalization using CDF mapping.
/// This spreads pixel values to use the full 0-255 range.
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels)
///
/// # Returns
/// Histogram-equalized image with same channel count
pub fn equalize_histogram_u8(input: ArrayView3<u8>) -> Array3<u8> {
    let (height, width, channels) = input.dim();
    let mut output = Array3::<u8>::zeros((height, width, channels));
    let color_channels = if channels == 4 { 3 } else { channels };
    let total_pixels = (height * width) as f32;

    for c in 0..color_channels {
        // Build histogram
        let mut hist = [0u32; 256];
        for y in 0..height {
            for x in 0..width {
                hist[input[[y, x, c]] as usize] += 1;
            }
        }

        // Build CDF
        let mut cdf = [0u32; 256];
        cdf[0] = hist[0];
        for i in 1..256 {
            cdf[i] = cdf[i - 1] + hist[i];
        }

        // Find minimum non-zero CDF value
        let cdf_min = cdf.iter().copied().find(|&v| v > 0).unwrap_or(0) as f32;

        // Build lookup table
        let mut lut = [0u8; 256];
        let denom = total_pixels - cdf_min;
        if denom > 0.0 {
            for i in 0..256 {
                lut[i] = ((cdf[i] as f32 - cdf_min) / denom * 255.0)
                    .clamp(0.0, 255.0) as u8;
            }
        }

        // Apply lookup table
        for y in 0..height {
            for x in 0..width {
                output[[y, x, c]] = lut[input[[y, x, c]] as usize];
            }
        }
    }

    // Preserve alpha
    if channels == 4 {
        for y in 0..height {
            for x in 0..width {
                output[[y, x, 3]] = input[[y, x, 3]];
            }
        }
    }

    output
}

/// Equalize image histogram (f32 version).
///
/// Performs per-channel histogram equalization by quantizing to 256 bins,
/// computing CDF, and mapping back to 0.0-1.0.
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels, values 0.0-1.0
///
/// # Returns
/// Histogram-equalized image with same channel count
pub fn equalize_histogram_f32(input: ArrayView3<f32>) -> Array3<f32> {
    let (height, width, channels) = input.dim();
    let mut output = Array3::<f32>::zeros((height, width, channels));
    let color_channels = if channels == 4 { 3 } else { channels };
    let total_pixels = (height * width) as f32;

    for c in 0..color_channels {
        // Build histogram (quantize to 256 bins)
        let mut hist = [0u32; 256];
        for y in 0..height {
            for x in 0..width {
                let bin = (input[[y, x, c]].clamp(0.0, 1.0) * 255.0) as usize;
                hist[bin.min(255)] += 1;
            }
        }

        // Build CDF
        let mut cdf = [0u32; 256];
        cdf[0] = hist[0];
        for i in 1..256 {
            cdf[i] = cdf[i - 1] + hist[i];
        }

        let cdf_min = cdf.iter().copied().find(|&v| v > 0).unwrap_or(0) as f32;
        let denom = total_pixels - cdf_min;

        // Apply equalization
        for y in 0..height {
            for x in 0..width {
                let bin = (input[[y, x, c]].clamp(0.0, 1.0) * 255.0) as usize;
                let bin = bin.min(255);
                if denom > 0.0 {
                    output[[y, x, c]] = ((cdf[bin] as f32 - cdf_min) / denom).clamp(0.0, 1.0);
                } else {
                    output[[y, x, c]] = input[[y, x, c]];
                }
            }
        }
    }

    // Preserve alpha
    if channels == 4 {
        for y in 0..height {
            for x in 0..width {
                output[[y, x, 3]] = input[[y, x, 3]];
            }
        }
    }

    output
}

#[cfg(test)]
mod tests {
    use super::*;

    // ========================================================================
    // Brightness Tests
    // ========================================================================

    #[test]
    fn test_brightness_u8_rgba() {
        let mut img = Array3::<u8>::zeros((1, 1, 4));
        img[[0, 0, 0]] = 100;
        img[[0, 0, 1]] = 100;
        img[[0, 0, 2]] = 100;
        img[[0, 0, 3]] = 255;

        let result = brightness_u8(img.view(), 0.5);

        assert!((result[[0, 0, 0]] as i32 - 227).abs() <= 1);
        assert_eq!(result[[0, 0, 3]], 255); // Alpha preserved
    }

    #[test]
    fn test_brightness_u8_rgb() {
        let mut img = Array3::<u8>::zeros((1, 1, 3));
        img[[0, 0, 0]] = 100;
        img[[0, 0, 1]] = 100;
        img[[0, 0, 2]] = 100;

        let result = brightness_u8(img.view(), 0.5);

        assert_eq!(result.dim().2, 3); // Still 3 channels
        assert!((result[[0, 0, 0]] as i32 - 227).abs() <= 1);
    }

    #[test]
    fn test_brightness_u8_grayscale() {
        let mut img = Array3::<u8>::zeros((1, 1, 1));
        img[[0, 0, 0]] = 100;

        let result = brightness_u8(img.view(), 0.5);

        assert_eq!(result.dim().2, 1); // Still 1 channel
        assert!((result[[0, 0, 0]] as i32 - 227).abs() <= 1);
    }

    #[test]
    fn test_brightness_f32_grayscale() {
        let mut img = Array3::<f32>::zeros((1, 1, 1));
        img[[0, 0, 0]] = 0.4;

        let result = brightness_f32(img.view(), 0.3);

        assert!((result[[0, 0, 0]] - 0.7).abs() < 0.001);
    }

    // ========================================================================
    // Contrast Tests
    // ========================================================================

    #[test]
    fn test_contrast_u8_rgba() {
        let mut img = Array3::<u8>::zeros((1, 1, 4));
        img[[0, 0, 0]] = 200;
        img[[0, 0, 3]] = 255;

        let result = contrast_u8(img.view(), 0.5);

        assert!(result[[0, 0, 0]] > 200);
        assert_eq!(result[[0, 0, 3]], 255);
    }

    #[test]
    fn test_contrast_u8_grayscale() {
        let mut img = Array3::<u8>::zeros((1, 1, 1));
        img[[0, 0, 0]] = 200;

        let result = contrast_u8(img.view(), 0.5);

        assert!(result[[0, 0, 0]] > 200);
    }

    // ========================================================================
    // Saturation Tests
    // ========================================================================

    #[test]
    fn test_saturation_u8_rgba() {
        let mut img = Array3::<u8>::zeros((1, 1, 4));
        img[[0, 0, 0]] = 255;
        img[[0, 0, 1]] = 0;
        img[[0, 0, 2]] = 0;
        img[[0, 0, 3]] = 255;

        let result = saturation_u8(img.view(), -1.0);

        // Should be grayscale
        assert_eq!(result[[0, 0, 0]], result[[0, 0, 1]]);
        assert_eq!(result[[0, 0, 1]], result[[0, 0, 2]]);
    }

    #[test]
    fn test_saturation_u8_grayscale_noop() {
        let mut img = Array3::<u8>::zeros((1, 1, 1));
        img[[0, 0, 0]] = 128;

        let result = saturation_u8(img.view(), 0.5);

        // Should be unchanged for grayscale
        assert_eq!(result[[0, 0, 0]], 128);
    }

    // ========================================================================
    // Gamma Tests
    // ========================================================================

    #[test]
    fn test_gamma_f32_rgb() {
        let mut img = Array3::<f32>::zeros((1, 1, 3));
        img[[0, 0, 0]] = 0.5;
        img[[0, 0, 1]] = 0.5;
        img[[0, 0, 2]] = 0.5;

        let result = gamma_f32(img.view(), 1.0);

        assert!((result[[0, 0, 0]] - 0.5).abs() < 0.001);
    }

    #[test]
    fn test_gamma_u8_grayscale() {
        let mut img = Array3::<u8>::zeros((1, 1, 1));
        img[[0, 0, 0]] = 128;

        let result = gamma_u8(img.view(), 1.0);

        assert_eq!(result[[0, 0, 0]], 128);
    }

    // ========================================================================
    // Exposure Tests
    // ========================================================================

    #[test]
    fn test_exposure_u8_rgb() {
        let mut img = Array3::<u8>::zeros((1, 1, 3));
        img[[0, 0, 0]] = 64;
        img[[0, 0, 1]] = 64;
        img[[0, 0, 2]] = 64;

        let result = exposure_u8(img.view(), 1.0, 0.0, 1.0);

        // One stop up doubles the brightness
        assert!((result[[0, 0, 0]] as i32 - 128).abs() <= 1);
    }

    // ========================================================================
    // Invert Tests
    // ========================================================================

    #[test]
    fn test_invert_u8_rgba() {
        let mut img = Array3::<u8>::zeros((1, 1, 4));
        img[[0, 0, 0]] = 100;
        img[[0, 0, 1]] = 200;
        img[[0, 0, 2]] = 50;
        img[[0, 0, 3]] = 128;

        let result = invert_u8(img.view());

        assert_eq!(result[[0, 0, 0]], 155);
        assert_eq!(result[[0, 0, 1]], 55);
        assert_eq!(result[[0, 0, 2]], 205);
        assert_eq!(result[[0, 0, 3]], 128); // Alpha unchanged
    }

    #[test]
    fn test_invert_u8_grayscale() {
        let mut img = Array3::<u8>::zeros((1, 1, 1));
        img[[0, 0, 0]] = 100;

        let result = invert_u8(img.view());

        assert_eq!(result[[0, 0, 0]], 155);
    }

    #[test]
    fn test_invert_f32_rgb() {
        let mut img = Array3::<f32>::zeros((1, 1, 3));
        img[[0, 0, 0]] = 0.3;
        img[[0, 0, 1]] = 0.7;
        img[[0, 0, 2]] = 0.0;

        let result = invert_f32(img.view());

        assert!((result[[0, 0, 0]] - 0.7).abs() < 0.001);
        assert!((result[[0, 0, 1]] - 0.3).abs() < 0.001);
        assert!((result[[0, 0, 2]] - 1.0).abs() < 0.001);
    }

    // ========================================================================
    // Equalize Histogram Tests
    // ========================================================================

    #[test]
    fn test_equalize_histogram_u8_uniform() {
        // A uniform image should stay roughly uniform after equalization
        let mut img = Array3::<u8>::zeros((2, 2, 4));
        for y in 0..2 {
            for x in 0..2 {
                img[[y, x, 0]] = 128;
                img[[y, x, 1]] = 128;
                img[[y, x, 2]] = 128;
                img[[y, x, 3]] = 255;
            }
        }

        let result = equalize_histogram_u8(img.view());

        // All pixels should map to the same value
        assert_eq!(result[[0, 0, 0]], result[[1, 1, 0]]);
        assert_eq!(result[[0, 0, 3]], 255); // Alpha preserved
    }

    #[test]
    fn test_equalize_histogram_u8_spread() {
        // Two distinct values should map to 0 and 255
        let mut img = Array3::<u8>::zeros((2, 1, 3));
        img[[0, 0, 0]] = 50;
        img[[0, 0, 1]] = 50;
        img[[0, 0, 2]] = 50;
        img[[1, 0, 0]] = 200;
        img[[1, 0, 1]] = 200;
        img[[1, 0, 2]] = 200;

        let result = equalize_histogram_u8(img.view());

        // Should spread to full range
        assert!(result[[0, 0, 0]] < result[[1, 0, 0]]);
    }

    #[test]
    fn test_equalize_histogram_f32() {
        let mut img = Array3::<f32>::zeros((2, 1, 1));
        img[[0, 0, 0]] = 0.2;
        img[[1, 0, 0]] = 0.8;

        let result = equalize_histogram_f32(img.view());

        // Should spread values
        assert!(result[[0, 0, 0]] < result[[1, 0, 0]]);
    }
}
