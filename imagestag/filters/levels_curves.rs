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

/// PCHIP (Piecewise Cubic Hermite Interpolating Polynomial) interpolation.
/// Matches scipy.interpolate.PchipInterpolator behavior.
///
/// PCHIP preserves monotonicity and doesn't overshoot at control points,
/// making it ideal for tone curve adjustments.
fn pchip_interpolate(points: &[(f32, f32)], t: f32) -> f32 {
    let n = points.len();

    if n == 0 {
        return t;
    }
    if n == 1 {
        return points[0].1;
    }

    // For 2 points, use linear interpolation
    if n == 2 {
        let (x0, y0) = points[0];
        let (x1, y1) = points[1];
        if (x1 - x0).abs() < 1e-10 {
            return y0;
        }
        let slope = (y1 - y0) / (x1 - x0);
        return y0 + slope * (t - x0);
    }

    // Compute segment widths (h) and slopes (delta)
    let mut h = vec![0.0f32; n - 1];
    let mut delta = vec![0.0f32; n - 1];
    for i in 0..n - 1 {
        h[i] = points[i + 1].0 - points[i].0;
        if h[i].abs() < 1e-10 {
            h[i] = 1e-10;
        }
        delta[i] = (points[i + 1].1 - points[i].1) / h[i];
    }

    // Compute PCHIP slopes at each point
    let mut d = vec![0.0f32; n];

    // Interior points: weighted harmonic mean
    for i in 1..n - 1 {
        if delta[i - 1].signum() != delta[i].signum() || delta[i - 1].abs() < 1e-10 || delta[i].abs() < 1e-10 {
            // Sign change or zero slope - set derivative to 0 for monotonicity
            d[i] = 0.0;
        } else {
            // Weighted harmonic mean of adjacent slopes
            let w1 = 2.0 * h[i] + h[i - 1];
            let w2 = h[i] + 2.0 * h[i - 1];
            d[i] = (w1 + w2) / (w1 / delta[i - 1] + w2 / delta[i]);
        }
    }

    // Endpoint derivatives using one-sided formula (non-centered differences)
    // Left endpoint
    d[0] = pchip_endpoint_slope(h[0], h[1], delta[0], delta[1]);
    // Right endpoint
    d[n - 1] = pchip_endpoint_slope(h[n - 2], h[n - 3].max(h[n - 2]), delta[n - 2], delta[n - 3].max(delta[n - 2]));

    // More accurate endpoint formula
    d[0] = ((2.0 * h[0] + h[1]) * delta[0] - h[0] * delta[1]) / (h[0] + h[1]);
    if d[0].signum() != delta[0].signum() {
        d[0] = 0.0;
    } else if delta[0].signum() != delta[1].signum() && d[0].abs() > 3.0 * delta[0].abs() {
        d[0] = 3.0 * delta[0];
    }

    d[n - 1] = ((2.0 * h[n - 2] + h[n - 3]) * delta[n - 2] - h[n - 2] * delta[n - 3]) / (h[n - 2] + h[n - 3]);
    if d[n - 1].signum() != delta[n - 2].signum() {
        d[n - 1] = 0.0;
    } else if delta[n - 2].signum() != delta[n - 3].signum() && d[n - 1].abs() > 3.0 * delta[n - 2].abs() {
        d[n - 1] = 3.0 * delta[n - 2];
    }

    // Find the segment containing t
    let mut k = 0;
    for i in 0..n - 1 {
        if t >= points[i].0 && t <= points[i + 1].0 {
            k = i;
            break;
        }
        if i == n - 2 {
            k = i;
        }
    }

    // Handle extrapolation
    if t < points[0].0 {
        // Linear extrapolation from left
        return points[0].1 + d[0] * (t - points[0].0);
    }
    if t > points[n - 1].0 {
        // Linear extrapolation from right
        return points[n - 1].1 + d[n - 1] * (t - points[n - 1].0);
    }

    // Hermite interpolation on segment k
    let x_k = points[k].0;
    let x_k1 = points[k + 1].0;
    let y_k = points[k].1;
    let y_k1 = points[k + 1].1;
    let d_k = d[k];
    let d_k1 = d[k + 1];
    let h_k = h[k];

    // Normalized parameter
    let s = (t - x_k) / h_k;
    let s2 = s * s;
    let s3 = s2 * s;

    // Hermite basis functions
    let h00 = 2.0 * s3 - 3.0 * s2 + 1.0;
    let h10 = s3 - 2.0 * s2 + s;
    let h01 = -2.0 * s3 + 3.0 * s2;
    let h11 = s3 - s2;

    // Interpolated value
    y_k * h00 + h_k * d_k * h10 + y_k1 * h01 + h_k * d_k1 * h11
}

/// Helper for PCHIP endpoint slope calculation.
#[inline]
fn pchip_endpoint_slope(h1: f32, h2: f32, delta1: f32, delta2: f32) -> f32 {
    let d = ((2.0 * h1 + h2) * delta1 - h1 * delta2) / (h1 + h2);
    if d.signum() != delta1.signum() {
        0.0
    } else if delta1.signum() != delta2.signum() && d.abs() > 3.0 * delta1.abs() {
        3.0 * delta1
    } else {
        d
    }
}

/// Apply curves adjustment - u8 version.
///
/// Uses PCHIP interpolation to match scipy.interpolate.PchipInterpolator.
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
        let result = pchip_interpolate(points, t);
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
/// Uses PCHIP interpolation to match scipy.interpolate.PchipInterpolator.
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
                output[[y, x, c]] = pchip_interpolate(points, v).clamp(0.0, 1.0);
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

/// Collect all pixel values from a channel into a sorted array for percentile calculation.
fn collect_channel_values_u8(input: ArrayView3<u8>, channel: usize) -> Vec<u8> {
    let (height, width, _) = input.dim();
    let mut values = Vec::with_capacity(height * width);

    for y in 0..height {
        for x in 0..width {
            values.push(input[[y, x, channel]]);
        }
    }
    values.sort_unstable();
    values
}

/// Compute percentile from sorted values, matching numpy.percentile behavior.
/// Uses linear interpolation between adjacent values.
fn percentile_from_sorted_u8(sorted: &[u8], p: f32) -> f32 {
    if sorted.is_empty() {
        return 0.0;
    }
    if sorted.len() == 1 {
        return sorted[0] as f32;
    }

    // numpy percentile uses linear interpolation
    // index = (n - 1) * p / 100
    let n = sorted.len() as f32;
    let idx = (n - 1.0) * p / 100.0;

    let idx_low = idx.floor() as usize;
    let idx_high = idx.ceil() as usize;

    if idx_low == idx_high || idx_high >= sorted.len() {
        return sorted[idx_low.min(sorted.len() - 1)] as f32;
    }

    let frac = idx - idx_low as f32;
    let v_low = sorted[idx_low] as f32;
    let v_high = sorted[idx_high] as f32;

    v_low + frac * (v_high - v_low)
}

/// Apply auto levels (histogram stretch) - u8 version.
///
/// Matches numpy.percentile behavior for clipping calculation.
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels)
/// * `clip_percent` - Fraction to clip from each end (0.0-0.5, e.g., 0.01 = 1%)
///
/// # Returns
/// Auto-leveled image with same channel count
pub fn auto_levels_u8(input: ArrayView3<u8>, clip_percent: f32) -> Array3<u8> {
    let (height, width, channels) = input.dim();
    let mut output = Array3::<u8>::zeros((height, width, channels));

    // clip_percent is a fraction (0.01 = 1%)
    // Convert to percentile values: 0.01 -> 1% and 99%
    let p_low = clip_percent * 100.0;  // e.g., 1.0 for 1%
    let p_high = (1.0 - clip_percent) * 100.0;  // e.g., 99.0 for 99%

    let color_channels = if channels == 4 { 3 } else { channels };

    // Process each channel independently
    for c in 0..color_channels {
        let sorted = collect_channel_values_u8(input, c);

        let low = percentile_from_sorted_u8(&sorted, p_low);
        let high = percentile_from_sorted_u8(&sorted, p_high);

        let range = (high - low).max(1.0);

        for y in 0..height {
            for x in 0..width {
                let v = input[[y, x, c]] as f32;
                let stretched = ((v - low) * 255.0 / range).clamp(0.0, 255.0);
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

/// Collect all pixel values from a channel into a sorted array for percentile calculation.
fn collect_channel_values_f32(input: ArrayView3<f32>, channel: usize) -> Vec<f32> {
    let (height, width, _) = input.dim();
    let mut values = Vec::with_capacity(height * width);

    for y in 0..height {
        for x in 0..width {
            values.push(input[[y, x, channel]]);
        }
    }
    values.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
    values
}

/// Compute percentile from sorted values, matching numpy.percentile behavior.
fn percentile_from_sorted_f32(sorted: &[f32], p: f32) -> f32 {
    if sorted.is_empty() {
        return 0.0;
    }
    if sorted.len() == 1 {
        return sorted[0];
    }

    let n = sorted.len() as f32;
    let idx = (n - 1.0) * p / 100.0;

    let idx_low = idx.floor() as usize;
    let idx_high = idx.ceil() as usize;

    if idx_low == idx_high || idx_high >= sorted.len() {
        return sorted[idx_low.min(sorted.len() - 1)];
    }

    let frac = idx - idx_low as f32;
    let v_low = sorted[idx_low];
    let v_high = sorted[idx_high];

    v_low + frac * (v_high - v_low)
}

/// Apply auto levels (histogram stretch) - f32 version.
///
/// Matches numpy.percentile behavior for clipping calculation.
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels), values 0.0-1.0
/// * `clip_percent` - Fraction to clip from each end (0.0-0.5, e.g., 0.01 = 1%)
///
/// # Returns
/// Auto-leveled image with same channel count
pub fn auto_levels_f32(input: ArrayView3<f32>, clip_percent: f32) -> Array3<f32> {
    let (height, width, channels) = input.dim();
    let mut output = Array3::<f32>::zeros((height, width, channels));

    // clip_percent is a fraction (0.01 = 1%)
    let p_low = clip_percent * 100.0;
    let p_high = (1.0 - clip_percent) * 100.0;

    let color_channels = if channels == 4 { 3 } else { channels };

    for c in 0..color_channels {
        let sorted = collect_channel_values_f32(input, c);

        let low = percentile_from_sorted_f32(&sorted, p_low);
        let high = percentile_from_sorted_f32(&sorted, p_high);

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
