//! Levels and curves filters: Levels, Curves, Auto Levels.
//!
//! These filters manipulate the tonal range of images.
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
// Levels
// ============================================================================

/// Apply levels adjustment - u8 version.
///
/// Remaps input levels to output levels with optional gamma correction.
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels)
/// * `in_black` - Input black point (0-255)
/// * `in_white` - Input white point (0-255)
/// * `out_black` - Output black point (0-255)
/// * `out_white` - Output white point (0-255)
/// * `gamma` - Gamma correction (0.1-10.0, 1.0 = no gamma)
///
/// # Returns
/// Levels-adjusted image with same channel count
pub fn levels_u8(
    input: ArrayView3<u8>,
    in_black: u8,
    in_white: u8,
    out_black: u8,
    out_white: u8,
    gamma: f32,
) -> Array3<u8> {
    let (height, width, channels) = input.dim();
    let mut output = Array3::<u8>::zeros((height, width, channels));

    let in_range = (in_white as f32 - in_black as f32).max(1.0);
    let out_range = out_white as f32 - out_black as f32;
    let inv_gamma = 1.0 / gamma.max(0.001);

    let color_channels = if channels == 4 { 3 } else { channels };

    for y in 0..height {
        for x in 0..width {
            for c in 0..color_channels {
                let v = input[[y, x, c]] as f32;

                // Map input range to 0-1
                let normalized = ((v - in_black as f32) / in_range).clamp(0.0, 1.0);

                // Apply gamma
                let gamma_corrected = normalized.powf(inv_gamma);

                // Map to output range
                let result = out_black as f32 + gamma_corrected * out_range;

                output[[y, x, c]] = result.clamp(0.0, 255.0) as u8;
            }
            if channels == 4 {
                output[[y, x, 3]] = input[[y, x, 3]];
            }
        }
    }
    output
}

/// Apply levels adjustment - f32 version.
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels), values 0.0-1.0
/// * `in_black` - Input black point (0.0-1.0)
/// * `in_white` - Input white point (0.0-1.0)
/// * `out_black` - Output black point (0.0-1.0)
/// * `out_white` - Output white point (0.0-1.0)
/// * `gamma` - Gamma correction (0.1-10.0, 1.0 = no gamma)
///
/// # Returns
/// Levels-adjusted image with same channel count
pub fn levels_f32(
    input: ArrayView3<f32>,
    in_black: f32,
    in_white: f32,
    out_black: f32,
    out_white: f32,
    gamma: f32,
) -> Array3<f32> {
    let (height, width, channels) = input.dim();
    let mut output = Array3::<f32>::zeros((height, width, channels));

    let in_range = (in_white - in_black).max(0.001);
    let out_range = out_white - out_black;
    let inv_gamma = 1.0 / gamma.max(0.001);

    let color_channels = if channels == 4 { 3 } else { channels };

    for y in 0..height {
        for x in 0..width {
            for c in 0..color_channels {
                let v = input[[y, x, c]];

                let normalized = ((v - in_black) / in_range).clamp(0.0, 1.0);
                let gamma_corrected = normalized.powf(inv_gamma);
                let result = out_black + gamma_corrected * out_range;

                output[[y, x, c]] = result.clamp(0.0, 1.0);
            }
            if channels == 4 {
                output[[y, x, 3]] = input[[y, x, 3]];
            }
        }
    }
    output
}

// ============================================================================
// Curves
// ============================================================================

/// Cubic spline interpolation using Catmull-Rom spline.
fn catmull_rom_spline(points: &[(f32, f32)], t: f32) -> f32 {
    if points.is_empty() {
        return t;
    }
    if points.len() == 1 {
        return points[0].1;
    }

    // Find the segment containing t
    let mut i = 0;
    while i < points.len() - 1 && points[i + 1].0 < t {
        i += 1;
    }

    if i >= points.len() - 1 {
        return points.last().unwrap().1;
    }

    let p0 = if i > 0 { points[i - 1] } else { points[i] };
    let p1 = points[i];
    let p2 = points[i + 1];
    let p3 = if i + 2 < points.len() {
        points[i + 2]
    } else {
        points[i + 1]
    };

    let segment_t = if (p2.0 - p1.0).abs() < 1e-6 {
        0.0
    } else {
        (t - p1.0) / (p2.0 - p1.0)
    };

    let t2 = segment_t * segment_t;
    let t3 = t2 * segment_t;

    // Catmull-Rom coefficients
    let v = 0.5
        * ((2.0 * p1.1)
            + (-p0.1 + p2.1) * segment_t
            + (2.0 * p0.1 - 5.0 * p1.1 + 4.0 * p2.1 - p3.1) * t2
            + (-p0.1 + 3.0 * p1.1 - 3.0 * p2.1 + p3.1) * t3);

    v.clamp(0.0, 1.0)
}

/// Apply curves adjustment - u8 version.
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels)
/// * `points` - Control points as (input, output) pairs, values 0.0-1.0
///              Must include (0,0) and (1,1) endpoints if you want them anchored.
///
/// # Returns
/// Curves-adjusted image with same channel count
pub fn curves_u8(input: ArrayView3<u8>, points: &[(f32, f32)]) -> Array3<u8> {
    let (height, width, channels) = input.dim();
    let mut output = Array3::<u8>::zeros((height, width, channels));

    // Pre-compute lookup table for efficiency
    let mut lut = [0u8; 256];
    for i in 0..256 {
        let t = i as f32 / 255.0;
        let result = catmull_rom_spline(points, t);
        lut[i] = (result * 255.0).clamp(0.0, 255.0) as u8;
    }

    let color_channels = if channels == 4 { 3 } else { channels };

    for y in 0..height {
        for x in 0..width {
            for c in 0..color_channels {
                output[[y, x, c]] = lut[input[[y, x, c]] as usize];
            }
            if channels == 4 {
                output[[y, x, 3]] = input[[y, x, 3]];
            }
        }
    }
    output
}

/// Apply curves adjustment - f32 version.
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels), values 0.0-1.0
/// * `points` - Control points as (input, output) pairs, values 0.0-1.0
///
/// # Returns
/// Curves-adjusted image with same channel count
pub fn curves_f32(input: ArrayView3<f32>, points: &[(f32, f32)]) -> Array3<f32> {
    let (height, width, channels) = input.dim();
    let mut output = Array3::<f32>::zeros((height, width, channels));

    let color_channels = if channels == 4 { 3 } else { channels };

    for y in 0..height {
        for x in 0..width {
            for c in 0..color_channels {
                let v = input[[y, x, c]].clamp(0.0, 1.0);
                output[[y, x, c]] = catmull_rom_spline(points, v);
            }
            if channels == 4 {
                output[[y, x, 3]] = input[[y, x, 3]];
            }
        }
    }
    output
}

// ============================================================================
// Auto Levels
// ============================================================================

/// Compute histogram for a channel.
fn compute_histogram_u8(input: ArrayView3<u8>, channel: usize) -> [u32; 256] {
    let (height, width, _) = input.dim();
    let mut hist = [0u32; 256];

    for y in 0..height {
        for x in 0..width {
            let v = input[[y, x, channel]] as usize;
            hist[v] += 1;
        }
    }
    hist
}

/// Find the percentile value in a histogram.
fn find_percentile(hist: &[u32; 256], percentile: f32, total: u32) -> u8 {
    // Handle edge cases for 0% and 100%
    if percentile <= 0.0 {
        // Return first non-zero bucket (minimum value)
        for (i, &count) in hist.iter().enumerate() {
            if count > 0 {
                return i as u8;
            }
        }
        return 0;
    }

    if percentile >= 1.0 {
        // Return last non-zero bucket (maximum value)
        for i in (0..256).rev() {
            if hist[i] > 0 {
                return i as u8;
            }
        }
        return 255;
    }

    let target = (total as f32 * percentile) as u32;
    let mut sum = 0u32;

    for (i, &count) in hist.iter().enumerate() {
        sum += count;
        if sum >= target {
            return i as u8;
        }
    }
    255
}

/// Apply auto levels (histogram stretch) - u8 version.
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels)
/// * `clip_percent` - Percentage to clip from each end (0.0-50.0, typically 0.5-2.0)
///
/// # Returns
/// Auto-leveled image with same channel count
pub fn auto_levels_u8(input: ArrayView3<u8>, clip_percent: f32) -> Array3<u8> {
    let (height, width, channels) = input.dim();
    let mut output = Array3::<u8>::zeros((height, width, channels));

    let total_pixels = (height * width) as u32;
    let clip = (clip_percent / 100.0).clamp(0.0, 0.5);

    let color_channels = if channels == 4 { 3 } else { channels };

    // Process each channel independently
    for c in 0..color_channels {
        let hist = compute_histogram_u8(input, c);

        let low = find_percentile(&hist, clip, total_pixels);
        let high = find_percentile(&hist, 1.0 - clip, total_pixels);

        let range = (high as f32 - low as f32).max(1.0);

        for y in 0..height {
            for x in 0..width {
                let v = input[[y, x, c]] as f32;
                let stretched = ((v - low as f32) / range * 255.0).clamp(0.0, 255.0);
                output[[y, x, c]] = stretched as u8;
            }
        }
    }

    // Copy alpha
    if channels == 4 {
        for y in 0..height {
            for x in 0..width {
                output[[y, x, 3]] = input[[y, x, 3]];
            }
        }
    }

    output
}

/// Apply auto levels (histogram stretch) - f32 version.
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels), values 0.0-1.0
/// * `clip_percent` - Percentage to clip from each end (0.0-50.0, typically 0.5-2.0)
///
/// # Returns
/// Auto-leveled image with same channel count
pub fn auto_levels_f32(input: ArrayView3<f32>, clip_percent: f32) -> Array3<f32> {
    let (height, width, channels) = input.dim();
    let mut output = Array3::<f32>::zeros((height, width, channels));

    let total_pixels = (height * width) as u32;
    let clip = (clip_percent / 100.0).clamp(0.0, 0.5);

    let color_channels = if channels == 4 { 3 } else { channels };

    // For f32, we need to build histograms differently
    // Use 4096 bins for 12-bit precision
    const BINS: usize = 4096;

    for c in 0..color_channels {
        let mut hist = vec![0u32; BINS];

        // Build histogram
        for y in 0..height {
            for x in 0..width {
                let v = input[[y, x, c]].clamp(0.0, 1.0);
                let bin = ((v * (BINS - 1) as f32) as usize).min(BINS - 1);
                hist[bin] += 1;
            }
        }

        // Find percentiles
        let target_low = (total_pixels as f32 * clip) as u32;
        let target_high = (total_pixels as f32 * (1.0 - clip)) as u32;

        let mut sum = 0u32;
        let mut low_bin = 0;
        let mut high_bin = BINS - 1;

        for (i, &count) in hist.iter().enumerate() {
            sum += count;
            if sum >= target_low && low_bin == 0 {
                low_bin = i;
            }
            if sum >= target_high {
                high_bin = i;
                break;
            }
        }

        let low = low_bin as f32 / (BINS - 1) as f32;
        let high = high_bin as f32 / (BINS - 1) as f32;
        let range = (high - low).max(0.001);

        for y in 0..height {
            for x in 0..width {
                let v = input[[y, x, c]];
                let stretched = ((v - low) / range).clamp(0.0, 1.0);
                output[[y, x, c]] = stretched;
            }
        }
    }

    // Copy alpha
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

    #[test]
    fn test_levels_u8_identity() {
        let mut img = Array3::<u8>::zeros((1, 1, 4));
        img[[0, 0, 0]] = 128;
        img[[0, 0, 3]] = 255;

        let result = levels_u8(img.view(), 0, 255, 0, 255, 1.0);

        assert_eq!(result[[0, 0, 0]], 128);
    }

    #[test]
    fn test_levels_u8_invert() {
        let mut img = Array3::<u8>::zeros((1, 1, 4));
        img[[0, 0, 0]] = 100;
        img[[0, 0, 3]] = 255;

        let result = levels_u8(img.view(), 0, 255, 255, 0, 1.0);

        // 100/255 -> 1 - 100/255 = 0.608 -> 155
        assert!((result[[0, 0, 0]] as i32 - 155).abs() <= 1);
    }

    #[test]
    fn test_levels_f32_stretch() {
        let mut img = Array3::<f32>::zeros((1, 1, 4));
        img[[0, 0, 0]] = 0.5;
        img[[0, 0, 3]] = 1.0;

        // Map 0.25-0.75 to 0-1
        let result = levels_f32(img.view(), 0.25, 0.75, 0.0, 1.0, 1.0);

        // 0.5 is at middle of 0.25-0.75, so should map to 0.5
        assert!((result[[0, 0, 0]] - 0.5).abs() < 0.01);
    }

    #[test]
    fn test_curves_u8_identity() {
        let mut img = Array3::<u8>::zeros((1, 1, 4));
        img[[0, 0, 0]] = 128;
        img[[0, 0, 3]] = 255;

        let points = vec![(0.0, 0.0), (1.0, 1.0)];
        let result = curves_u8(img.view(), &points);

        assert!((result[[0, 0, 0]] as i32 - 128).abs() <= 1);
    }

    #[test]
    fn test_curves_f32_s_curve() {
        let mut img = Array3::<f32>::zeros((1, 1, 4));
        img[[0, 0, 0]] = 0.5;
        img[[0, 0, 3]] = 1.0;

        // S-curve: shadows darker, highlights brighter
        let points = vec![
            (0.0, 0.0),
            (0.25, 0.15),
            (0.5, 0.5),
            (0.75, 0.85),
            (1.0, 1.0),
        ];
        let result = curves_f32(img.view(), &points);

        // Midpoint should stay roughly at 0.5
        assert!((result[[0, 0, 0]] - 0.5).abs() < 0.1);
    }

    #[test]
    fn test_auto_levels_u8() {
        let mut img = Array3::<u8>::zeros((2, 2, 4));
        // Low contrast image: values 64-192 (same across all RGB channels)
        img[[0, 0, 0]] = 64;
        img[[0, 0, 1]] = 64;
        img[[0, 0, 2]] = 64;
        img[[0, 1, 0]] = 128;
        img[[0, 1, 1]] = 128;
        img[[0, 1, 2]] = 128;
        img[[1, 0, 0]] = 160;
        img[[1, 0, 1]] = 160;
        img[[1, 0, 2]] = 160;
        img[[1, 1, 0]] = 192;
        img[[1, 1, 1]] = 192;
        img[[1, 1, 2]] = 192;
        for y in 0..2 {
            for x in 0..2 {
                img[[y, x, 3]] = 255;
            }
        }

        let result = auto_levels_u8(img.view(), 0.0);

        // After stretch, min should be 0, max should be 255
        let min = result[[0, 0, 0]].min(result[[0, 1, 0]]).min(result[[1, 0, 0]]).min(result[[1, 1, 0]]);
        let max = result[[0, 0, 0]].max(result[[0, 1, 0]]).max(result[[1, 0, 0]]).max(result[[1, 1, 0]]);

        assert_eq!(min, 0);
        assert_eq!(max, 255);
    }

    #[test]
    fn test_auto_levels_f32_preserves_alpha() {
        let mut img = Array3::<f32>::zeros((1, 1, 4));
        img[[0, 0, 0]] = 0.5;
        img[[0, 0, 1]] = 0.5;
        img[[0, 0, 2]] = 0.5;
        img[[0, 0, 3]] = 0.7;

        let result = auto_levels_f32(img.view(), 0.0);

        assert!((result[[0, 0, 3]] - 0.7).abs() < 0.001);
    }
}
