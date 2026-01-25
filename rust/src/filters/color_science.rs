//! Color science filters: Hue Shift, Vibrance, Color Balance.
//!
//! These filters require color space conversions (RGB <-> HSL).
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
/// Vibrance boosts less-saturated colors while protecting skin tones.
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

    const LUMA_R: f32 = 0.2126;
    const LUMA_G: f32 = 0.7152;
    const LUMA_B: f32 = 0.0722;

    for y in 0..height {
        for x in 0..width {
            let r = input[[y, x, 0]] as f32 / 255.0;
            let g = input[[y, x, 1]] as f32 / 255.0;
            let b = input[[y, x, 2]] as f32 / 255.0;

            let max = r.max(g).max(b);
            let min = r.min(g).min(b);
            let sat = if max > 0.0 { (max - min) / max } else { 0.0 };

            let skin_factor = {
                let is_skin_like = r > g && g > b && r > 0.4 && g > 0.2;
                if is_skin_like { 0.5 } else { 1.0 }
            };

            let vibrance_factor = (1.0 - sat) * amount * skin_factor;
            let gray = LUMA_R * r + LUMA_G * g + LUMA_B * b;
            let sat_factor = 1.0 + vibrance_factor;

            let nr = (gray + (r - gray) * sat_factor).clamp(0.0, 1.0);
            let ng = (gray + (g - gray) * sat_factor).clamp(0.0, 1.0);
            let nb = (gray + (b - gray) * sat_factor).clamp(0.0, 1.0);

            output[[y, x, 0]] = (nr * 255.0) as u8;
            output[[y, x, 1]] = (ng * 255.0) as u8;
            output[[y, x, 2]] = (nb * 255.0) as u8;

            if channels == 4 {
                output[[y, x, 3]] = input[[y, x, 3]];
            }
        }
    }
    output
}

/// Adjust image vibrance (f32 version).
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

    const LUMA_R: f32 = 0.2126;
    const LUMA_G: f32 = 0.7152;
    const LUMA_B: f32 = 0.0722;

    for y in 0..height {
        for x in 0..width {
            let r = input[[y, x, 0]];
            let g = input[[y, x, 1]];
            let b = input[[y, x, 2]];

            let max = r.max(g).max(b);
            let min = r.min(g).min(b);
            let sat = if max > 0.0 { (max - min) / max } else { 0.0 };

            let skin_factor = {
                let is_skin_like = r > g && g > b && r > 0.4 && g > 0.2;
                if is_skin_like { 0.5 } else { 1.0 }
            };

            let vibrance_factor = (1.0 - sat) * amount * skin_factor;
            let gray = LUMA_R * r + LUMA_G * g + LUMA_B * b;
            let sat_factor = 1.0 + vibrance_factor;

            output[[y, x, 0]] = (gray + (r - gray) * sat_factor).clamp(0.0, 1.0);
            output[[y, x, 1]] = (gray + (g - gray) * sat_factor).clamp(0.0, 1.0);
            output[[y, x, 2]] = (gray + (b - gray) * sat_factor).clamp(0.0, 1.0);

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

/// Compute luminosity for a pixel.
#[inline]
fn luminosity(r: f32, g: f32, b: f32) -> f32 {
    0.2126 * r + 0.7152 * g + 0.0722 * b
}

/// Adjust image color balance (u8 version).
///
/// Adjusts shadows, midtones, and highlights independently.
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
            let r = input[[y, x, 0]] as f32 / 255.0;
            let g = input[[y, x, 1]] as f32 / 255.0;
            let b = input[[y, x, 2]] as f32 / 255.0;

            let lum = luminosity(r, g, b);

            let shadow_weight = 1.0 - lum;
            let highlight_weight = lum;
            let midtone_weight = 1.0 - (2.0 * lum - 1.0).abs();

            let total = shadow_weight + midtone_weight + highlight_weight;
            let sw = shadow_weight / total;
            let mw = midtone_weight / total;
            let hw = highlight_weight / total;

            let nr = r + sw * shadows[0] + mw * midtones[0] + hw * highlights[0];
            let ng = g + sw * shadows[1] + mw * midtones[1] + hw * highlights[1];
            let nb = b + sw * shadows[2] + mw * midtones[2] + hw * highlights[2];

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

/// Adjust image color balance (f32 version).
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
            let r = input[[y, x, 0]];
            let g = input[[y, x, 1]];
            let b = input[[y, x, 2]];

            let lum = luminosity(r, g, b);

            let shadow_weight = 1.0 - lum;
            let highlight_weight = lum;
            let midtone_weight = 1.0 - (2.0 * lum - 1.0).abs();

            let total = shadow_weight + midtone_weight + highlight_weight;
            let sw = shadow_weight / total;
            let mw = midtone_weight / total;
            let hw = highlight_weight / total;

            let nr = r + sw * shadows[0] + mw * midtones[0] + hw * highlights[0];
            let ng = g + sw * shadows[1] + mw * midtones[1] + hw * highlights[1];
            let nb = b + sw * shadows[2] + mw * midtones[2] + hw * highlights[2];

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
}
