//! Color science filters: Hue Shift, Vibrance, Color Balance, Sepia, Temperature, Channel Mixer.
//!
//! These filters require color space conversions (RGB <-> HSL) or color matrix operations.
//! All filters support both u8 (0-255) and f32 (0.0-1.0) modes.
//!
//! ## Supported Formats
//!
//! - **Grayscale (1 channel)**: No-op (color operations require RGB)
//! - **RGB (3 channels)**: Full color processing
//! - **RGBA (4 channels)**: RGB processed, alpha preserved

use ndarray::{Array3, ArrayView3};

// ============================================================================
// Color Space Conversion Utilities
// ============================================================================

/// Convert RGB to HSL.
/// Input: r, g, b in 0.0-1.0
/// Output: (h, s, l) where h is 0.0-360.0, s and l are 0.0-1.0
#[inline]
fn rgb_to_hsl(r: f32, g: f32, b: f32) -> (f32, f32, f32) {
    let max = r.max(g).max(b);
    let min = r.min(g).min(b);
    let l = (max + min) / 2.0;

    if (max - min).abs() < 1e-6 {
        return (0.0, 0.0, l);
    }

    let d = max - min;
    let s = if l > 0.5 {
        d / (2.0 - max - min)
    } else {
        d / (max + min)
    };

    let h = if (max - r).abs() < 1e-6 {
        let mut h = (g - b) / d;
        if g < b {
            h += 6.0;
        }
        h * 60.0
    } else if (max - g).abs() < 1e-6 {
        ((b - r) / d + 2.0) * 60.0
    } else {
        ((r - g) / d + 4.0) * 60.0
    };

    (h, s, l)
}

/// Convert HSL to RGB.
/// Input: h in 0.0-360.0, s and l in 0.0-1.0
/// Output: (r, g, b) in 0.0-1.0
#[inline]
fn hsl_to_rgb(h: f32, s: f32, l: f32) -> (f32, f32, f32) {
    if s.abs() < 1e-6 {
        return (l, l, l);
    }

    let q = if l < 0.5 {
        l * (1.0 + s)
    } else {
        l + s - l * s
    };
    let p = 2.0 * l - q;

    let h_norm = h / 360.0;

    fn hue_to_rgb(p: f32, q: f32, mut t: f32) -> f32 {
        if t < 0.0 { t += 1.0; }
        if t > 1.0 { t -= 1.0; }
        if t < 1.0 / 6.0 { return p + (q - p) * 6.0 * t; }
        if t < 0.5 { return q; }
        if t < 2.0 / 3.0 { return p + (q - p) * (2.0 / 3.0 - t) * 6.0; }
        p
    }

    let r = hue_to_rgb(p, q, h_norm + 1.0 / 3.0);
    let g = hue_to_rgb(p, q, h_norm);
    let b = hue_to_rgb(p, q, h_norm - 1.0 / 3.0);

    (r, g, b)
}

/// Convert RGB to HSV.
/// Input: r, g, b in 0.0-1.0
/// Output: (h, s, v) where h is 0.0-1.0 (not 360), s and v are 0.0-1.0
/// Matches skimage.color.rgb2hsv behavior.
#[inline]
fn rgb_to_hsv(r: f32, g: f32, b: f32) -> (f32, f32, f32) {
    let max = r.max(g).max(b);
    let min = r.min(g).min(b);
    let v = max;
    let d = max - min;

    let s = if max.abs() < 1e-10 { 0.0 } else { d / max };

    if d.abs() < 1e-10 {
        return (0.0, s, v);
    }

    let h = if (max - r).abs() < 1e-10 {
        let mut h = (g - b) / d;
        if h < 0.0 { h += 6.0; }
        h / 6.0
    } else if (max - g).abs() < 1e-10 {
        ((b - r) / d + 2.0) / 6.0
    } else {
        ((r - g) / d + 4.0) / 6.0
    };

    (h, s, v)
}

/// Convert HSV to RGB.
/// Input: h in 0.0-1.0, s and v in 0.0-1.0
/// Output: (r, g, b) in 0.0-1.0
/// Matches skimage.color.hsv2rgb behavior.
#[inline]
fn hsv_to_rgb(h: f32, s: f32, v: f32) -> (f32, f32, f32) {
    if s.abs() < 1e-10 {
        return (v, v, v);
    }

    let h6 = h * 6.0;
    let i = h6.floor() as i32;
    let f = h6 - i as f32;
    let p = v * (1.0 - s);
    let q = v * (1.0 - s * f);
    let t = v * (1.0 - s * (1.0 - f));

    match i % 6 {
        0 => (v, t, p),
        1 => (q, v, p),
        2 => (p, v, t),
        3 => (p, q, v),
        4 => (t, p, v),
        _ => (v, p, q),
    }
}

// ============================================================================
// Hue Shift
// ============================================================================

/// Shift image hue (u8 version).
///
/// For grayscale input, returns a copy (no-op).
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels)
/// * `degrees` - Hue shift in degrees (0-360, wraps around)
///
/// # Returns
/// Hue-shifted image with same channel count
pub fn hue_shift_u8(input: ArrayView3<u8>, degrees: f32) -> Array3<u8> {
    let (height, width, channels) = input.dim();
    let mut output = Array3::<u8>::zeros((height, width, channels));

    // Grayscale: no-op (can't shift hue on single channel)
    if channels == 1 {
        for y in 0..height {
            for x in 0..width {
                output[[y, x, 0]] = input[[y, x, 0]];
            }
        }
        return output;
    }

    for y in 0..height {
        for x in 0..width {
            let r = input[[y, x, 0]] as f32 / 255.0;
            let g = input[[y, x, 1]] as f32 / 255.0;
            let b = input[[y, x, 2]] as f32 / 255.0;

            let (h, s, l) = rgb_to_hsl(r, g, b);
            let new_h = (h + degrees).rem_euclid(360.0);
            let (nr, ng, nb) = hsl_to_rgb(new_h, s, l);

            output[[y, x, 0]] = (nr * 255.0).clamp(0.0, 255.0) as u8;
            output[[y, x, 1]] = (ng * 255.0).clamp(0.0, 255.0) as u8;
            output[[y, x, 2]] = (nb * 255.0).clamp(0.0, 255.0) as u8;

            if channels == 4 {
                output[[y, x, 3]] = input[[y, x, 3]];
            }
        }
    }
    output
}

/// Shift image hue (f32 version).
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels), values 0.0-1.0
/// * `degrees` - Hue shift in degrees (0-360, wraps around)
///
/// # Returns
/// Hue-shifted image with same channel count
pub fn hue_shift_f32(input: ArrayView3<f32>, degrees: f32) -> Array3<f32> {
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

    for y in 0..height {
        for x in 0..width {
            let r = input[[y, x, 0]];
            let g = input[[y, x, 1]];
            let b = input[[y, x, 2]];

            let (h, s, l) = rgb_to_hsl(r, g, b);
            let new_h = (h + degrees).rem_euclid(360.0);
            let (nr, ng, nb) = hsl_to_rgb(new_h, s, l);

            output[[y, x, 0]] = nr.clamp(0.0, 1.0);
            output[[y, x, 1]] = ng.clamp(0.0, 1.0);
            output[[y, x, 2]] = nb.clamp(0.0, 1.0);

            if channels == 4 {
                output[[y, x, 3]] = input[[y, x, 3]];
            }
        }
    }
    output
}

// ============================================================================
// Vibrance
// ============================================================================

/// Adjust image vibrance (u8 version).
///
/// Vibrance boosts less-saturated colors more than already saturated colors.
/// Uses HSV color space to match skimage behavior exactly.
/// For grayscale input, returns a copy (no-op).
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels)
/// * `amount` - Vibrance adjustment: -1.0 to 1.0, 0.0 = no change
///
/// # Returns
/// Vibrance-adjusted image with same channel count
pub fn vibrance_u8(input: ArrayView3<u8>, amount: f32) -> Array3<u8> {
    let (height, width, channels) = input.dim();
    let mut output = Array3::<u8>::zeros((height, width, channels));

    if channels == 1 {
        for y in 0..height {
            for x in 0..width {
                output[[y, x, 0]] = input[[y, x, 0]];
            }
        }
        return output;
    }

    for y in 0..height {
        for x in 0..width {
            let r = input[[y, x, 0]] as f32 / 255.0;
            let g = input[[y, x, 1]] as f32 / 255.0;
            let b = input[[y, x, 2]] as f32 / 255.0;

            // Convert to HSV (matching skimage.color.rgb2hsv)
            let (h, s, v) = rgb_to_hsv(r, g, b);

            // Vibrance: boost saturation more for less-saturated pixels
            // adjustment = amount * (1 - sat)
            // new_sat = sat * (1 + adjustment)
            let adjustment = amount * (1.0 - s);
            let new_s = (s * (1.0 + adjustment)).clamp(0.0, 1.0);

            // Convert back to RGB
            let (nr, ng, nb) = hsv_to_rgb(h, new_s, v);

            output[[y, x, 0]] = (nr * 255.0).round() as u8;
            output[[y, x, 1]] = (ng * 255.0).round() as u8;
            output[[y, x, 2]] = (nb * 255.0).round() as u8;

            if channels == 4 {
                output[[y, x, 3]] = input[[y, x, 3]];
            }
        }
    }
    output
}

/// Adjust image vibrance (f32 version).
///
/// Uses HSV color space to match skimage behavior exactly.
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels), values 0.0-1.0
/// * `amount` - Vibrance adjustment: -1.0 to 1.0, 0.0 = no change
///
/// # Returns
/// Vibrance-adjusted image with same channel count
pub fn vibrance_f32(input: ArrayView3<f32>, amount: f32) -> Array3<f32> {
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

    for y in 0..height {
        for x in 0..width {
            let r = input[[y, x, 0]];
            let g = input[[y, x, 1]];
            let b = input[[y, x, 2]];

            // Convert to HSV
            let (h, s, v) = rgb_to_hsv(r, g, b);

            // Vibrance: boost saturation more for less-saturated pixels
            let adjustment = amount * (1.0 - s);
            let new_s = (s * (1.0 + adjustment)).clamp(0.0, 1.0);

            // Convert back to RGB
            let (nr, ng, nb) = hsv_to_rgb(h, new_s, v);

            output[[y, x, 0]] = nr.clamp(0.0, 1.0);
            output[[y, x, 1]] = ng.clamp(0.0, 1.0);
            output[[y, x, 2]] = nb.clamp(0.0, 1.0);

            if channels == 4 {
                output[[y, x, 3]] = input[[y, x, 3]];
            }
        }
    }
    output
}

// ============================================================================
// Color Balance
// ============================================================================

/// Adjust image color balance (u8 version).
///
/// Adjusts shadows, midtones, and highlights independently.
/// Matches skimage reference implementation with specific mask formulas.
/// For grayscale input, returns a copy (no-op).
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels)
/// * `shadows` - RGB adjustment for shadows, each -1.0 to 1.0
/// * `midtones` - RGB adjustment for midtones, each -1.0 to 1.0
/// * `highlights` - RGB adjustment for highlights, each -1.0 to 1.0
///
/// # Returns
/// Color-balanced image with same channel count
pub fn color_balance_u8(
    input: ArrayView3<u8>,
    shadows: [f32; 3],
    midtones: [f32; 3],
    highlights: [f32; 3],
) -> Array3<u8> {
    let (height, width, channels) = input.dim();
    let mut output = Array3::<u8>::zeros((height, width, channels));

    if channels == 1 {
        for y in 0..height {
            for x in 0..width {
                output[[y, x, 0]] = input[[y, x, 0]];
            }
        }
        return output;
    }

    for y in 0..height {
        for x in 0..width {
            // Process each channel independently (matching skimage)
            for c in 0..3 {
                let channel = input[[y, x, c]] as f32 / 255.0;

                // Masks based on channel value (not luminosity)
                // shadow_mask = clip(1.0 - channel * 3, 0, 1)
                let shadow_mask = (1.0 - channel * 3.0).clamp(0.0, 1.0);
                // mid_mask = clip(1.0 - |channel - 0.5| * 4, 0, 1)
                let mid_mask = (1.0 - (channel - 0.5).abs() * 4.0).clamp(0.0, 1.0);
                // highlight_mask = clip(channel * 3 - 2, 0, 1)
                let highlight_mask = (channel * 3.0 - 2.0).clamp(0.0, 1.0);

                let adjustment = shadows[c] * shadow_mask
                    + midtones[c] * mid_mask
                    + highlights[c] * highlight_mask;

                let new_val = (channel + adjustment).clamp(0.0, 1.0);
                output[[y, x, c]] = (new_val * 255.0).round() as u8;
            }

            if channels == 4 {
                output[[y, x, 3]] = input[[y, x, 3]];
            }
        }
    }
    output
}

/// Adjust image color balance (f32 version).
///
/// Matches skimage reference implementation.
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels), values 0.0-1.0
/// * `shadows` - RGB adjustment for shadows, each -1.0 to 1.0
/// * `midtones` - RGB adjustment for midtones, each -1.0 to 1.0
/// * `highlights` - RGB adjustment for highlights, each -1.0 to 1.0
///
/// # Returns
/// Color-balanced image with same channel count
pub fn color_balance_f32(
    input: ArrayView3<f32>,
    shadows: [f32; 3],
    midtones: [f32; 3],
    highlights: [f32; 3],
) -> Array3<f32> {
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

    for y in 0..height {
        for x in 0..width {
            // Process each channel independently (matching skimage)
            for c in 0..3 {
                let channel = input[[y, x, c]];

                // Masks based on channel value (not luminosity)
                let shadow_mask = (1.0 - channel * 3.0).clamp(0.0, 1.0);
                let mid_mask = (1.0 - (channel - 0.5).abs() * 4.0).clamp(0.0, 1.0);
                let highlight_mask = (channel * 3.0 - 2.0).clamp(0.0, 1.0);

                let adjustment = shadows[c] * shadow_mask
                    + midtones[c] * mid_mask
                    + highlights[c] * highlight_mask;

                output[[y, x, c]] = (channel + adjustment).clamp(0.0, 1.0);
            }

            if channels == 4 {
                output[[y, x, 3]] = input[[y, x, 3]];
            }
        }
    }
    output
}

// ============================================================================
// Sepia
// ============================================================================

/// Apply sepia tone effect (u8 version).
///
/// Uses the standard sepia color matrix blended with the original image.
/// For grayscale input, first converts to pseudo-RGB then applies matrix.
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels)
/// * `intensity` - Blend factor: 0.0 = no change, 1.0 = full sepia
///
/// # Returns
/// Sepia-toned image with same channel count
pub fn sepia_u8(input: ArrayView3<u8>, intensity: f32) -> Array3<u8> {
    let (height, width, channels) = input.dim();
    let mut output = Array3::<u8>::zeros((height, width, channels));
    let intensity = intensity.clamp(0.0, 1.0);

    // Sepia color matrix coefficients
    const SR: [f32; 3] = [0.393, 0.769, 0.189];
    const SG: [f32; 3] = [0.349, 0.686, 0.168];
    const SB: [f32; 3] = [0.272, 0.534, 0.131];

    for y in 0..height {
        for x in 0..width {
            let (r, g, b) = if channels == 1 {
                let v = input[[y, x, 0]] as f32;
                (v, v, v)
            } else {
                (
                    input[[y, x, 0]] as f32,
                    input[[y, x, 1]] as f32,
                    input[[y, x, 2]] as f32,
                )
            };

            let sepia_r = (SR[0] * r + SR[1] * g + SR[2] * b).min(255.0);
            let sepia_g = (SG[0] * r + SG[1] * g + SG[2] * b).min(255.0);
            let sepia_b = (SB[0] * r + SB[1] * g + SB[2] * b).min(255.0);

            // Blend between original and sepia
            let out_r = (r + (sepia_r - r) * intensity).clamp(0.0, 255.0) as u8;
            let out_g = (g + (sepia_g - g) * intensity).clamp(0.0, 255.0) as u8;
            let out_b = (b + (sepia_b - b) * intensity).clamp(0.0, 255.0) as u8;

            if channels == 1 {
                // For grayscale, output luminosity of sepia result
                output[[y, x, 0]] = ((out_r as f32 * 0.2126
                    + out_g as f32 * 0.7152
                    + out_b as f32 * 0.0722) as u8);
            } else {
                output[[y, x, 0]] = out_r;
                output[[y, x, 1]] = out_g;
                output[[y, x, 2]] = out_b;
                if channels == 4 {
                    output[[y, x, 3]] = input[[y, x, 3]];
                }
            }
        }
    }
    output
}

/// Apply sepia tone effect (f32 version).
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels, values 0.0-1.0
/// * `intensity` - Blend factor: 0.0 = no change, 1.0 = full sepia
///
/// # Returns
/// Sepia-toned image with same channel count
pub fn sepia_f32(input: ArrayView3<f32>, intensity: f32) -> Array3<f32> {
    let (height, width, channels) = input.dim();
    let mut output = Array3::<f32>::zeros((height, width, channels));
    let intensity = intensity.clamp(0.0, 1.0);

    const SR: [f32; 3] = [0.393, 0.769, 0.189];
    const SG: [f32; 3] = [0.349, 0.686, 0.168];
    const SB: [f32; 3] = [0.272, 0.534, 0.131];

    for y in 0..height {
        for x in 0..width {
            let (r, g, b) = if channels == 1 {
                let v = input[[y, x, 0]];
                (v, v, v)
            } else {
                (input[[y, x, 0]], input[[y, x, 1]], input[[y, x, 2]])
            };

            let sepia_r = (SR[0] * r + SR[1] * g + SR[2] * b).min(1.0);
            let sepia_g = (SG[0] * r + SG[1] * g + SG[2] * b).min(1.0);
            let sepia_b = (SB[0] * r + SB[1] * g + SB[2] * b).min(1.0);

            let out_r = (r + (sepia_r - r) * intensity).clamp(0.0, 1.0);
            let out_g = (g + (sepia_g - g) * intensity).clamp(0.0, 1.0);
            let out_b = (b + (sepia_b - b) * intensity).clamp(0.0, 1.0);

            if channels == 1 {
                output[[y, x, 0]] = (out_r * 0.2126 + out_g * 0.7152 + out_b * 0.0722)
                    .clamp(0.0, 1.0);
            } else {
                output[[y, x, 0]] = out_r;
                output[[y, x, 1]] = out_g;
                output[[y, x, 2]] = out_b;
                if channels == 4 {
                    output[[y, x, 3]] = input[[y, x, 3]];
                }
            }
        }
    }
    output
}

// ============================================================================
// Temperature
// ============================================================================

/// Adjust image color temperature (u8 version).
///
/// Warm (positive) adds red and reduces blue. Cool (negative) adds blue
/// and reduces red. Green channel is unchanged.
/// For grayscale input, returns a copy (no-op).
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels)
/// * `amount` - Temperature shift: -1.0 (cool) to 1.0 (warm)
///
/// # Returns
/// Temperature-adjusted image with same channel count
pub fn temperature_u8(input: ArrayView3<u8>, amount: f32) -> Array3<u8> {
    let (height, width, channels) = input.dim();
    let mut output = Array3::<u8>::zeros((height, width, channels));

    if channels == 1 {
        for y in 0..height {
            for x in 0..width {
                output[[y, x, 0]] = input[[y, x, 0]];
            }
        }
        return output;
    }

    let r_shift = amount * 30.0; // +/- 30 at full intensity
    let b_shift = -amount * 30.0;

    for y in 0..height {
        for x in 0..width {
            let r = input[[y, x, 0]] as f32 + r_shift;
            let g = input[[y, x, 1]] as f32;
            let b = input[[y, x, 2]] as f32 + b_shift;

            output[[y, x, 0]] = r.clamp(0.0, 255.0) as u8;
            output[[y, x, 1]] = g.clamp(0.0, 255.0) as u8;
            output[[y, x, 2]] = b.clamp(0.0, 255.0) as u8;

            if channels == 4 {
                output[[y, x, 3]] = input[[y, x, 3]];
            }
        }
    }
    output
}

/// Adjust image color temperature (f32 version).
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels, values 0.0-1.0
/// * `amount` - Temperature shift: -1.0 (cool) to 1.0 (warm)
///
/// # Returns
/// Temperature-adjusted image with same channel count
pub fn temperature_f32(input: ArrayView3<f32>, amount: f32) -> Array3<f32> {
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

    // Scale to 0.0-1.0 range (30/255 ≈ 0.118)
    let r_shift = amount * (30.0 / 255.0);
    let b_shift = -amount * (30.0 / 255.0);

    for y in 0..height {
        for x in 0..width {
            output[[y, x, 0]] = (input[[y, x, 0]] + r_shift).clamp(0.0, 1.0);
            output[[y, x, 1]] = input[[y, x, 1]];
            output[[y, x, 2]] = (input[[y, x, 2]] + b_shift).clamp(0.0, 1.0);

            if channels == 4 {
                output[[y, x, 3]] = input[[y, x, 3]];
            }
        }
    }
    output
}

// ============================================================================
// Channel Mixer
// ============================================================================

/// Mix image channels by swapping source channels (u8 version).
///
/// Each output channel is sourced from a specified input channel.
/// For grayscale input, returns a copy (no-op).
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels)
/// * `r_src` - Source channel for red output (0=R, 1=G, 2=B)
/// * `g_src` - Source channel for green output (0=R, 1=G, 2=B)
/// * `b_src` - Source channel for blue output (0=R, 1=G, 2=B)
///
/// # Returns
/// Channel-mixed image with same channel count
pub fn channel_mixer_u8(
    input: ArrayView3<u8>,
    r_src: u8,
    g_src: u8,
    b_src: u8,
) -> Array3<u8> {
    let (height, width, channels) = input.dim();
    let mut output = Array3::<u8>::zeros((height, width, channels));

    if channels == 1 {
        for y in 0..height {
            for x in 0..width {
                output[[y, x, 0]] = input[[y, x, 0]];
            }
        }
        return output;
    }

    let r_src = (r_src as usize).min(2);
    let g_src = (g_src as usize).min(2);
    let b_src = (b_src as usize).min(2);

    for y in 0..height {
        for x in 0..width {
            output[[y, x, 0]] = input[[y, x, r_src]];
            output[[y, x, 1]] = input[[y, x, g_src]];
            output[[y, x, 2]] = input[[y, x, b_src]];

            if channels == 4 {
                output[[y, x, 3]] = input[[y, x, 3]];
            }
        }
    }
    output
}

/// Mix image channels by swapping source channels (f32 version).
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels, values 0.0-1.0
/// * `r_src` - Source channel for red output (0=R, 1=G, 2=B)
/// * `g_src` - Source channel for green output (0=R, 1=G, 2=B)
/// * `b_src` - Source channel for blue output (0=R, 1=G, 2=B)
///
/// # Returns
/// Channel-mixed image with same channel count
pub fn channel_mixer_f32(
    input: ArrayView3<f32>,
    r_src: u8,
    g_src: u8,
    b_src: u8,
) -> Array3<f32> {
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

    let r_src = (r_src as usize).min(2);
    let g_src = (g_src as usize).min(2);
    let b_src = (b_src as usize).min(2);

    for y in 0..height {
        for x in 0..width {
            output[[y, x, 0]] = input[[y, x, r_src]];
            output[[y, x, 1]] = input[[y, x, g_src]];
            output[[y, x, 2]] = input[[y, x, b_src]];

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
    fn test_rgb_hsl_roundtrip() {
        let (r, g, b) = (0.8, 0.4, 0.2);
        let (h, s, l) = rgb_to_hsl(r, g, b);
        let (nr, ng, nb) = hsl_to_rgb(h, s, l);

        assert!((r - nr).abs() < 0.001);
        assert!((g - ng).abs() < 0.001);
        assert!((b - nb).abs() < 0.001);
    }

    #[test]
    fn test_hue_shift_180_rgba() {
        let mut img = Array3::<f32>::zeros((1, 1, 4));
        img[[0, 0, 0]] = 1.0; // Pure red
        img[[0, 0, 3]] = 1.0;

        let result = hue_shift_f32(img.view(), 180.0);

        // Red shifted 180 degrees should be cyan
        assert!(result[[0, 0, 0]] < 0.1);
        assert!(result[[0, 0, 1]] > 0.9);
        assert!(result[[0, 0, 2]] > 0.9);
    }

    #[test]
    fn test_hue_shift_rgb() {
        let mut img = Array3::<u8>::zeros((1, 1, 3));
        img[[0, 0, 0]] = 200;
        img[[0, 0, 1]] = 100;
        img[[0, 0, 2]] = 50;

        let result = hue_shift_u8(img.view(), 360.0);

        assert_eq!(result.dim().2, 3);
        assert!((result[[0, 0, 0]] as i32 - 200).abs() <= 1);
    }

    #[test]
    fn test_hue_shift_grayscale_noop() {
        let mut img = Array3::<u8>::zeros((1, 1, 1));
        img[[0, 0, 0]] = 128;

        let result = hue_shift_u8(img.view(), 90.0);

        assert_eq!(result.dim().2, 1);
        assert_eq!(result[[0, 0, 0]], 128); // Unchanged
    }

    #[test]
    fn test_vibrance_preserves_gray() {
        let mut img = Array3::<f32>::zeros((1, 1, 4));
        img[[0, 0, 0]] = 0.5;
        img[[0, 0, 1]] = 0.5;
        img[[0, 0, 2]] = 0.5;
        img[[0, 0, 3]] = 1.0;

        let result = vibrance_f32(img.view(), 1.0);

        assert!((result[[0, 0, 0]] - 0.5).abs() < 0.001);
        assert!((result[[0, 0, 1]] - 0.5).abs() < 0.001);
        assert!((result[[0, 0, 2]] - 0.5).abs() < 0.001);
    }

    #[test]
    fn test_vibrance_grayscale_noop() {
        let mut img = Array3::<f32>::zeros((1, 1, 1));
        img[[0, 0, 0]] = 0.5;

        let result = vibrance_f32(img.view(), 1.0);

        assert_eq!(result.dim().2, 1);
        assert!((result[[0, 0, 0]] - 0.5).abs() < 0.001);
    }

    #[test]
    fn test_color_balance_shadows() {
        let mut img = Array3::<u8>::zeros((1, 1, 4));
        img[[0, 0, 0]] = 30;
        img[[0, 0, 1]] = 30;
        img[[0, 0, 2]] = 30;
        img[[0, 0, 3]] = 255;

        let result = color_balance_u8(
            img.view(),
            [0.3, 0.0, 0.0],
            [0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0],
        );

        assert!(result[[0, 0, 0]] > result[[0, 0, 1]]);
    }

    #[test]
    fn test_color_balance_grayscale_noop() {
        let mut img = Array3::<u8>::zeros((1, 1, 1));
        img[[0, 0, 0]] = 128;

        let result = color_balance_u8(
            img.view(),
            [0.3, 0.0, 0.0],
            [0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0],
        );

        assert_eq!(result.dim().2, 1);
        assert_eq!(result[[0, 0, 0]], 128);
    }

    // Sepia tests

    #[test]
    fn test_sepia_full_intensity() {
        let mut img = Array3::<u8>::zeros((1, 1, 4));
        img[[0, 0, 0]] = 200;
        img[[0, 0, 1]] = 150;
        img[[0, 0, 2]] = 100;
        img[[0, 0, 3]] = 255;

        let result = sepia_u8(img.view(), 1.0);

        // Sepia should make R > G > B (warm tone)
        assert!(result[[0, 0, 0]] >= result[[0, 0, 1]]);
        assert!(result[[0, 0, 1]] >= result[[0, 0, 2]]);
        assert_eq!(result[[0, 0, 3]], 255); // Alpha preserved
    }

    #[test]
    fn test_sepia_zero_intensity() {
        let mut img = Array3::<f32>::zeros((1, 1, 4));
        img[[0, 0, 0]] = 0.8;
        img[[0, 0, 1]] = 0.4;
        img[[0, 0, 2]] = 0.2;
        img[[0, 0, 3]] = 1.0;

        let result = sepia_f32(img.view(), 0.0);

        // No change at intensity 0
        assert!((result[[0, 0, 0]] - 0.8).abs() < 0.001);
        assert!((result[[0, 0, 1]] - 0.4).abs() < 0.001);
        assert!((result[[0, 0, 2]] - 0.2).abs() < 0.001);
    }

    // Temperature tests

    #[test]
    fn test_temperature_warm() {
        let mut img = Array3::<u8>::zeros((1, 1, 4));
        img[[0, 0, 0]] = 128;
        img[[0, 0, 1]] = 128;
        img[[0, 0, 2]] = 128;
        img[[0, 0, 3]] = 255;

        let result = temperature_u8(img.view(), 1.0);

        // Warm: more red, less blue
        assert!(result[[0, 0, 0]] > 128);
        assert_eq!(result[[0, 0, 1]], 128);
        assert!(result[[0, 0, 2]] < 128);
    }

    #[test]
    fn test_temperature_cool() {
        let mut img = Array3::<f32>::zeros((1, 1, 3));
        img[[0, 0, 0]] = 0.5;
        img[[0, 0, 1]] = 0.5;
        img[[0, 0, 2]] = 0.5;

        let result = temperature_f32(img.view(), -1.0);

        // Cool: less red, more blue
        assert!(result[[0, 0, 0]] < 0.5);
        assert!((result[[0, 0, 1]] - 0.5).abs() < 0.001);
        assert!(result[[0, 0, 2]] > 0.5);
    }

    #[test]
    fn test_temperature_grayscale_noop() {
        let mut img = Array3::<u8>::zeros((1, 1, 1));
        img[[0, 0, 0]] = 128;

        let result = temperature_u8(img.view(), 1.0);
        assert_eq!(result[[0, 0, 0]], 128);
    }

    // Channel Mixer tests

    #[test]
    fn test_channel_mixer_identity() {
        let mut img = Array3::<u8>::zeros((1, 1, 4));
        img[[0, 0, 0]] = 100;
        img[[0, 0, 1]] = 150;
        img[[0, 0, 2]] = 200;
        img[[0, 0, 3]] = 255;

        // Identity mapping: R=R, G=G, B=B
        let result = channel_mixer_u8(img.view(), 0, 1, 2);

        assert_eq!(result[[0, 0, 0]], 100);
        assert_eq!(result[[0, 0, 1]], 150);
        assert_eq!(result[[0, 0, 2]], 200);
        assert_eq!(result[[0, 0, 3]], 255);
    }

    #[test]
    fn test_channel_mixer_swap() {
        let mut img = Array3::<f32>::zeros((1, 1, 3));
        img[[0, 0, 0]] = 0.2;
        img[[0, 0, 1]] = 0.5;
        img[[0, 0, 2]] = 0.8;

        // Swap: R=B, G=R, B=G
        let result = channel_mixer_f32(img.view(), 2, 0, 1);

        assert!((result[[0, 0, 0]] - 0.8).abs() < 0.001);
        assert!((result[[0, 0, 1]] - 0.2).abs() < 0.001);
        assert!((result[[0, 0, 2]] - 0.5).abs() < 0.001);
    }

    #[test]
    fn test_channel_mixer_grayscale_noop() {
        let mut img = Array3::<u8>::zeros((1, 1, 1));
        img[[0, 0, 0]] = 128;

        let result = channel_mixer_u8(img.view(), 2, 0, 1);
        assert_eq!(result[[0, 0, 0]], 128);
    }
}
