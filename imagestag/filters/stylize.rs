//! Stylize filters: Posterize, Solarize, Threshold, Emboss, Pixelate, Vignette.
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

use super::blur_wasm::gaussian_blur_wasm_u8;
use super::grayscale::grayscale_u8;

// ============================================================================
// Posterize
// ============================================================================

/// Reduce color levels (posterize) - u8 version.
///
/// Uses the standard posterize formula: output = (input / divisor) * divisor
/// where divisor = 256 / levels. This matches skimage/opencv behavior.
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
    let divisor = 256u16 / levels as u16;

    // Process only color channels (not alpha)
    let color_channels = if channels == 4 { 3 } else { channels };

    for y in 0..height {
        for x in 0..width {
            for c in 0..color_channels {
                let v = input[[y, x, c]] as u16;
                output[[y, x, c]] = ((v / divisor) * divisor) as u8;
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
/// Uses the standard posterize formula matching u8 version behavior.
/// output = floor(input * levels) / levels (quantized to level boundaries)
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
    // Match u8 behavior: divisor = 256/levels, so in 0-1 space it's 1/levels
    let divisor = 1.0 / levels;

    let color_channels = if channels == 4 { 3 } else { channels };

    for y in 0..height {
        for x in 0..width {
            for c in 0..color_channels {
                let v = input[[y, x, c]].clamp(0.0, 1.0);
                // Quantize: floor(v / divisor) * divisor
                let level = (v / divisor).floor();
                output[[y, x, c]] = (level * divisor).min(1.0 - divisor);
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

            let v = if lum >= threshold { 255 } else { 0 };

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

            let v = if lum >= threshold { 1.0 } else { 0.0 };

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
/// Matches skimage behavior: converts to grayscale first, then applies emboss.
/// Output is grayscale (same value for all RGB channels).
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels)
/// * `angle` - Light source angle in degrees (0-360)
/// * `depth` - Effect strength (0.0-10.0)
///
/// # Returns
/// Embossed image with same channel count (grayscale values in RGB)
pub fn emboss_u8(input: ArrayView3<u8>, angle: f32, depth: f32) -> Array3<u8> {
    let (height, width, channels) = input.dim();
    let mut output = Array3::<u8>::zeros((height, width, channels));

    // BT.709 luminosity coefficients for grayscale conversion
    const LUMA_R: f32 = 0.2126;
    const LUMA_G: f32 = 0.7152;
    const LUMA_B: f32 = 0.0722;

    // Calculate kernel based on angle (matching skimage)
    // Note: scipy.ndimage.convolve flips the kernel (true convolution)
    // So we pre-flip it here to match skimage's result
    let rad = angle.to_radians();
    let dx = rad.cos();
    let dy = rad.sin();

    // Emboss kernel - flipped to match scipy's convolve behavior
    // Original skimage kernel: [[-dy*d, -d, -dx*d], [-1, 1, 1], [dx*d, d, dy*d]]
    // Flipped (180 rotation): [[dy*d, d, dx*d], [1, 1, -1], [-dx*d, -d, -dy*d]]
    let kernel: [[f32; 3]; 3] = [
        [depth * dy, depth, depth * dx],
        [1.0, 1.0, -1.0],
        [-depth * dx, -depth, -depth * dy],
    ];

    // First, convert to grayscale
    let mut gray = vec![vec![0.0f32; width]; height];
    for y in 0..height {
        for x in 0..width {
            gray[y][x] = if channels == 1 {
                input[[y, x, 0]] as f32
            } else {
                LUMA_R * input[[y, x, 0]] as f32
                    + LUMA_G * input[[y, x, 1]] as f32
                    + LUMA_B * input[[y, x, 2]] as f32
            };
        }
    }

    // Apply emboss kernel to grayscale
    for y in 1..height.saturating_sub(1) {
        for x in 1..width.saturating_sub(1) {
            let mut sum = 0.0f32;

            for ky in 0..3 {
                for kx in 0..3 {
                    let py = y + ky - 1;
                    let px = x + kx - 1;
                    sum += gray[py][px] * kernel[ky][kx];
                }
            }

            // Add 128 to center the result around middle gray
            let v = (sum + 128.0).clamp(0.0, 255.0) as u8;

            // Output grayscale value to all color channels
            let color_channels = if channels == 4 { 3 } else { channels };
            for c in 0..color_channels {
                output[[y, x, c]] = v;
            }
            if channels == 4 {
                output[[y, x, 3]] = input[[y, x, 3]];
            }
        }
    }

    // Handle edges - output grayscale of original at edges
    for x in 0..width {
        let v0 = if channels == 1 {
            input[[0, x, 0]]
        } else {
            (LUMA_R * input[[0, x, 0]] as f32
                + LUMA_G * input[[0, x, 1]] as f32
                + LUMA_B * input[[0, x, 2]] as f32) as u8
        };
        let color_channels = if channels == 4 { 3 } else { channels };
        for c in 0..color_channels {
            output[[0, x, c]] = v0;
        }
        if channels == 4 {
            output[[0, x, 3]] = input[[0, x, 3]];
        }

        if height > 1 {
            let v_last = if channels == 1 {
                input[[height - 1, x, 0]]
            } else {
                (LUMA_R * input[[height - 1, x, 0]] as f32
                    + LUMA_G * input[[height - 1, x, 1]] as f32
                    + LUMA_B * input[[height - 1, x, 2]] as f32) as u8
            };
            for c in 0..color_channels {
                output[[height - 1, x, c]] = v_last;
            }
            if channels == 4 {
                output[[height - 1, x, 3]] = input[[height - 1, x, 3]];
            }
        }
    }
    for y in 0..height {
        let v0 = if channels == 1 {
            input[[y, 0, 0]]
        } else {
            (LUMA_R * input[[y, 0, 0]] as f32
                + LUMA_G * input[[y, 0, 1]] as f32
                + LUMA_B * input[[y, 0, 2]] as f32) as u8
        };
        let color_channels = if channels == 4 { 3 } else { channels };
        for c in 0..color_channels {
            output[[y, 0, c]] = v0;
        }
        if channels == 4 {
            output[[y, 0, 3]] = input[[y, 0, 3]];
        }

        if width > 1 {
            let v_last = if channels == 1 {
                input[[y, width - 1, 0]]
            } else {
                (LUMA_R * input[[y, width - 1, 0]] as f32
                    + LUMA_G * input[[y, width - 1, 1]] as f32
                    + LUMA_B * input[[y, width - 1, 2]] as f32) as u8
            };
            for c in 0..color_channels {
                output[[y, width - 1, c]] = v_last;
            }
            if channels == 4 {
                output[[y, width - 1, 3]] = input[[y, width - 1, 3]];
            }
        }
    }

    output
}

/// Apply emboss effect - f32 version.
///
/// Matches skimage behavior: converts to grayscale first, then applies emboss.
/// Output is grayscale (same value for all RGB channels).
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels), values 0.0-1.0
/// * `angle` - Light source angle in degrees (0-360)
/// * `depth` - Effect strength (0.0-10.0)
///
/// # Returns
/// Embossed image with same channel count (grayscale values in RGB)
pub fn emboss_f32(input: ArrayView3<f32>, angle: f32, depth: f32) -> Array3<f32> {
    let (height, width, channels) = input.dim();
    let mut output = Array3::<f32>::zeros((height, width, channels));

    // BT.709 luminosity coefficients
    const LUMA_R: f32 = 0.2126;
    const LUMA_G: f32 = 0.7152;
    const LUMA_B: f32 = 0.0722;

    // Calculate kernel based on angle (matching skimage)
    // Note: scipy.ndimage.convolve flips the kernel (true convolution)
    // So we pre-flip it here to match skimage's result
    let rad = angle.to_radians();
    let dx = rad.cos();
    let dy = rad.sin();

    // Emboss kernel - flipped to match scipy's convolve behavior
    // Original skimage kernel: [[-dy*d, -d, -dx*d], [-1, 1, 1], [dx*d, d, dy*d]]
    // Flipped (180 rotation): [[dy*d, d, dx*d], [1, 1, -1], [-dx*d, -d, -dy*d]]
    let kernel: [[f32; 3]; 3] = [
        [depth * dy, depth, depth * dx],
        [1.0, 1.0, -1.0],
        [-depth * dx, -depth, -depth * dy],
    ];

    // First, convert to grayscale (0-1 range)
    let mut gray = vec![vec![0.0f32; width]; height];
    for y in 0..height {
        for x in 0..width {
            gray[y][x] = if channels == 1 {
                input[[y, x, 0]]
            } else {
                LUMA_R * input[[y, x, 0]] + LUMA_G * input[[y, x, 1]] + LUMA_B * input[[y, x, 2]]
            };
        }
    }

    // Apply emboss kernel to grayscale
    for y in 1..height.saturating_sub(1) {
        for x in 1..width.saturating_sub(1) {
            let mut sum = 0.0f32;

            for ky in 0..3 {
                for kx in 0..3 {
                    let py = y + ky - 1;
                    let px = x + kx - 1;
                    // gray is in 0-1 range, kernel expects 0-255 scale for skimage compat
                    sum += gray[py][px] * 255.0 * kernel[ky][kx];
                }
            }

            // Add 128 and convert back to 0-1 range
            let v = ((sum + 128.0) / 255.0).clamp(0.0, 1.0);

            // Output grayscale value to all color channels
            let color_channels = if channels == 4 { 3 } else { channels };
            for c in 0..color_channels {
                output[[y, x, c]] = v;
            }
            if channels == 4 {
                output[[y, x, 3]] = input[[y, x, 3]];
            }
        }
    }

    // Handle edges - output grayscale of original at edges
    for x in 0..width {
        let v0 = if channels == 1 {
            input[[0, x, 0]]
        } else {
            LUMA_R * input[[0, x, 0]] + LUMA_G * input[[0, x, 1]] + LUMA_B * input[[0, x, 2]]
        };
        let color_channels = if channels == 4 { 3 } else { channels };
        for c in 0..color_channels {
            output[[0, x, c]] = v0;
        }
        if channels == 4 {
            output[[0, x, 3]] = input[[0, x, 3]];
        }

        if height > 1 {
            let v_last = if channels == 1 {
                input[[height - 1, x, 0]]
            } else {
                LUMA_R * input[[height - 1, x, 0]]
                    + LUMA_G * input[[height - 1, x, 1]]
                    + LUMA_B * input[[height - 1, x, 2]]
            };
            for c in 0..color_channels {
                output[[height - 1, x, c]] = v_last;
            }
            if channels == 4 {
                output[[height - 1, x, 3]] = input[[height - 1, x, 3]];
            }
        }
    }
    for y in 0..height {
        let v0 = if channels == 1 {
            input[[y, 0, 0]]
        } else {
            LUMA_R * input[[y, 0, 0]] + LUMA_G * input[[y, 0, 1]] + LUMA_B * input[[y, 0, 2]]
        };
        let color_channels = if channels == 4 { 3 } else { channels };
        for c in 0..color_channels {
            output[[y, 0, c]] = v0;
        }
        if channels == 4 {
            output[[y, 0, 3]] = input[[y, 0, 3]];
        }

        if width > 1 {
            let v_last = if channels == 1 {
                input[[y, width - 1, 0]]
            } else {
                LUMA_R * input[[y, width - 1, 0]]
                    + LUMA_G * input[[y, width - 1, 1]]
                    + LUMA_B * input[[y, width - 1, 2]]
            };
            for c in 0..color_channels {
                output[[y, width - 1, c]] = v_last;
            }
            if channels == 4 {
                output[[y, width - 1, 3]] = input[[y, width - 1, 3]];
            }
        }
    }

    output
}

// ============================================================================
// Pixelate
// ============================================================================

/// Apply pixelation effect (u8 version).
///
/// Divides the image into blocks and fills each with its average color.
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels)
/// * `block_size` - Size of each pixel block (minimum 1)
///
/// # Returns
/// Pixelated image with same channel count
pub fn pixelate_u8(input: ArrayView3<u8>, block_size: u32) -> Array3<u8> {
    let (height, width, channels) = input.dim();
    let mut output = Array3::<u8>::zeros((height, width, channels));
    let block_size = (block_size as usize).max(1);
    let color_channels = if channels == 4 { 3 } else { channels };

    // Process each block
    let mut by = 0;
    while by < height {
        let bh = block_size.min(height - by);
        let mut bx = 0;
        while bx < width {
            let bw = block_size.min(width - bx);
            let pixel_count = (bh * bw) as f32;

            // Compute average color for this block
            for c in 0..color_channels {
                let mut sum = 0u32;
                for y in by..by + bh {
                    for x in bx..bx + bw {
                        sum += input[[y, x, c]] as u32;
                    }
                }
                let avg = (sum as f32 / pixel_count).round() as u8;

                // Fill block with average
                for y in by..by + bh {
                    for x in bx..bx + bw {
                        output[[y, x, c]] = avg;
                    }
                }
            }

            // Average alpha too if present
            if channels == 4 {
                let mut sum = 0u32;
                for y in by..by + bh {
                    for x in bx..bx + bw {
                        sum += input[[y, x, 3]] as u32;
                    }
                }
                let avg = (sum as f32 / pixel_count).round() as u8;
                for y in by..by + bh {
                    for x in bx..bx + bw {
                        output[[y, x, 3]] = avg;
                    }
                }
            }

            bx += block_size;
        }
        by += block_size;
    }
    output
}

/// Apply pixelation effect (f32 version).
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels, values 0.0-1.0
/// * `block_size` - Size of each pixel block (minimum 1)
///
/// # Returns
/// Pixelated image with same channel count
pub fn pixelate_f32(input: ArrayView3<f32>, block_size: u32) -> Array3<f32> {
    let (height, width, channels) = input.dim();
    let mut output = Array3::<f32>::zeros((height, width, channels));
    let block_size = (block_size as usize).max(1);
    let color_channels = if channels == 4 { 3 } else { channels };

    let mut by = 0;
    while by < height {
        let bh = block_size.min(height - by);
        let mut bx = 0;
        while bx < width {
            let bw = block_size.min(width - bx);
            let pixel_count = (bh * bw) as f32;

            for c in 0..color_channels {
                let mut sum = 0.0f32;
                for y in by..by + bh {
                    for x in bx..bx + bw {
                        sum += input[[y, x, c]];
                    }
                }
                let avg = sum / pixel_count;

                for y in by..by + bh {
                    for x in bx..bx + bw {
                        output[[y, x, c]] = avg;
                    }
                }
            }

            if channels == 4 {
                let mut sum = 0.0f32;
                for y in by..by + bh {
                    for x in bx..bx + bw {
                        sum += input[[y, x, 3]];
                    }
                }
                let avg = sum / pixel_count;
                for y in by..by + bh {
                    for x in bx..bx + bw {
                        output[[y, x, 3]] = avg;
                    }
                }
            }

            bx += block_size;
        }
        by += block_size;
    }
    output
}

// ============================================================================
// Vignette
// ============================================================================

/// Apply vignette effect (u8 version).
///
/// Darkens the edges of the image using a radial falloff from the center.
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels)
/// * `amount` - Vignette strength: 0.0 = none, 1.0 = strong darkening at edges
///
/// # Returns
/// Vignetted image with same channel count
pub fn vignette_u8(input: ArrayView3<u8>, amount: f32) -> Array3<u8> {
    let (height, width, channels) = input.dim();
    let mut output = Array3::<u8>::zeros((height, width, channels));
    let color_channels = if channels == 4 { 3 } else { channels };

    let cx = width as f32 / 2.0;
    let cy = height as f32 / 2.0;
    let max_dist = (cx * cx + cy * cy).sqrt();

    for y in 0..height {
        for x in 0..width {
            let dx = x as f32 - cx;
            let dy = y as f32 - cy;
            let dist = (dx * dx + dy * dy).sqrt();
            let norm_dist = dist / max_dist;
            let factor = 1.0 - amount * norm_dist * norm_dist;
            let factor = factor.clamp(0.0, 1.0);

            for c in 0..color_channels {
                output[[y, x, c]] = (input[[y, x, c]] as f32 * factor)
                    .clamp(0.0, 255.0) as u8;
            }
            if channels == 4 {
                output[[y, x, 3]] = input[[y, x, 3]];
            }
        }
    }
    output
}

/// Apply vignette effect (f32 version).
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels, values 0.0-1.0
/// * `amount` - Vignette strength: 0.0 = none, 1.0 = strong darkening at edges
///
/// # Returns
/// Vignetted image with same channel count
pub fn vignette_f32(input: ArrayView3<f32>, amount: f32) -> Array3<f32> {
    let (height, width, channels) = input.dim();
    let mut output = Array3::<f32>::zeros((height, width, channels));
    let color_channels = if channels == 4 { 3 } else { channels };

    let cx = width as f32 / 2.0;
    let cy = height as f32 / 2.0;
    let max_dist = (cx * cx + cy * cy).sqrt();

    for y in 0..height {
        for x in 0..width {
            let dx = x as f32 - cx;
            let dy = y as f32 - cy;
            let dist = (dx * dx + dy * dy).sqrt();
            let norm_dist = dist / max_dist;
            let factor = (1.0 - amount * norm_dist * norm_dist).clamp(0.0, 1.0);

            for c in 0..color_channels {
                output[[y, x, c]] = (input[[y, x, c]] * factor).clamp(0.0, 1.0);
            }
            if channels == 4 {
                output[[y, x, 3]] = input[[y, x, 3]];
            }
        }
    }
    output
}

// ============================================================================
// Pencil Sketch
// ============================================================================

/// Pencil sketch effect - u8 version.
///
/// Algorithm:
/// 1. Convert to grayscale
/// 2. Invert the grayscale
/// 3. Gaussian blur the inverted image
/// 4. Color dodge blend: result = min(255, gray * 255 / max(1, 255 - blurred))
/// 5. Apply shade factor (darken the result)
///
/// This produces a pencil sketch appearance similar to cv2.pencilSketch.
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels)
/// * `sigma_s` - Smoothness (10-200, controls blur radius, mapped as sigma_s * 0.2)
/// * `shade_factor` - Shade factor as percentage (0-100, lower = darker strokes)
///
/// # Returns
/// Grayscale sketch image with same channel count (grayscale values, alpha preserved)
pub fn pencil_sketch_u8(
    input: ArrayView3<u8>,
    sigma_s: f32,
    shade_factor: f32,
) -> Array3<u8> {
    let (height, width, channels) = input.dim();
    let shade = (shade_factor / 100.0).clamp(0.0, 1.0);

    // 1. Grayscale (always produces same channel count as input)
    let gray = grayscale_u8(input);

    // 2. Invert the grayscale
    let mut inverted = Array3::<u8>::zeros((height, width, channels));
    let color_ch = channels.min(3);
    for y in 0..height {
        for x in 0..width {
            for c in 0..color_ch {
                inverted[[y, x, c]] = 255 - gray[[y, x, c]];
            }
            if channels == 4 {
                inverted[[y, x, 3]] = gray[[y, x, 3]];
            }
        }
    }

    // 3. Gaussian blur (sigma = sigma_s * 0.2)
    let sigma = sigma_s * 0.2;
    let blurred = gaussian_blur_wasm_u8(inverted.view(), sigma);

    // 4. Color dodge blend + 5. shade factor
    let mut output = Array3::<u8>::zeros((height, width, channels));
    for y in 0..height {
        for x in 0..width {
            for c in 0..color_ch {
                let g = gray[[y, x, c]] as f32;
                let b = blurred[[y, x, c]] as f32;
                let divisor = (255.0 - b).max(1.0);
                let dodge = ((g * 255.0) / divisor).min(255.0);
                let shaded = dodge * shade;
                output[[y, x, c]] = shaded.clamp(0.0, 255.0) as u8;
            }
            if channels == 4 {
                output[[y, x, 3]] = input[[y, x, 3]];
            }
        }
    }

    output
}

/// Pencil sketch effect - f32 version.
///
/// Same algorithm as pencil_sketch_u8 but for float images.
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels, values 0.0-1.0
/// * `sigma_s` - Smoothness (10-200, controls blur radius, mapped as sigma_s * 0.2)
/// * `shade_factor` - Shade factor as percentage (0-100, lower = darker strokes)
///
/// # Returns
/// Grayscale sketch image with same channel count
pub fn pencil_sketch_f32(
    input: ArrayView3<f32>,
    sigma_s: f32,
    shade_factor: f32,
) -> Array3<f32> {
    let (height, width, channels) = input.dim();
    let shade = (shade_factor / 100.0).clamp(0.0, 1.0);
    let color_ch = channels.min(3);

    // 1. Grayscale
    let mut gray = Array3::<f32>::zeros((height, width, channels));
    for y in 0..height {
        for x in 0..width {
            let lum = if channels == 1 {
                input[[y, x, 0]]
            } else {
                0.2125 * input[[y, x, 0]] + 0.7154 * input[[y, x, 1]] + 0.0721 * input[[y, x, 2]]
            };
            for c in 0..color_ch {
                gray[[y, x, c]] = lum;
            }
            if channels == 4 {
                gray[[y, x, 3]] = input[[y, x, 3]];
            }
        }
    }

    // 2. Invert
    let mut inverted = Array3::<f32>::zeros((height, width, channels));
    for y in 0..height {
        for x in 0..width {
            for c in 0..color_ch {
                inverted[[y, x, c]] = 1.0 - gray[[y, x, c]];
            }
            if channels == 4 {
                inverted[[y, x, 3]] = gray[[y, x, 3]];
            }
        }
    }

    // 3. Gaussian blur
    let sigma = sigma_s * 0.2;
    let blurred = super::blur_wasm::gaussian_blur_wasm_f32(inverted.view(), sigma);

    // 4. Color dodge blend + 5. shade factor
    let mut output = Array3::<f32>::zeros((height, width, channels));
    for y in 0..height {
        for x in 0..width {
            for c in 0..color_ch {
                let g = gray[[y, x, c]];
                let b = blurred[[y, x, c]];
                let divisor = (1.0 - b).max(1.0 / 255.0);
                let dodge = (g / divisor).min(1.0);
                output[[y, x, c]] = (dodge * shade).clamp(0.0, 1.0);
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

    // Pixelate tests

    #[test]
    fn test_pixelate_u8_uniform_block() {
        let mut img = Array3::<u8>::zeros((4, 4, 4));
        // Create a pattern: top-left block red, rest green
        for y in 0..4 {
            for x in 0..4 {
                if y < 2 && x < 2 {
                    img[[y, x, 0]] = 255; // Red
                } else {
                    img[[y, x, 1]] = 255; // Green
                }
                img[[y, x, 3]] = 255;
            }
        }

        let result = pixelate_u8(img.view(), 2);

        // Each 2x2 block should be uniform
        assert_eq!(result[[0, 0, 0]], result[[0, 1, 0]]);
        assert_eq!(result[[0, 0, 0]], result[[1, 0, 0]]);
        assert_eq!(result[[0, 0, 0]], result[[1, 1, 0]]);
    }

    #[test]
    fn test_pixelate_f32_block_size_1() {
        let mut img = Array3::<f32>::zeros((2, 2, 3));
        img[[0, 0, 0]] = 0.5;
        img[[0, 1, 0]] = 0.7;

        // Block size 1 should be identity
        let result = pixelate_f32(img.view(), 1);

        assert!((result[[0, 0, 0]] - 0.5).abs() < 0.001);
        assert!((result[[0, 1, 0]] - 0.7).abs() < 0.001);
    }

    // Vignette tests

    #[test]
    fn test_vignette_u8_center_unchanged() {
        let mut img = Array3::<u8>::zeros((5, 5, 4));
        for y in 0..5 {
            for x in 0..5 {
                img[[y, x, 0]] = 200;
                img[[y, x, 1]] = 200;
                img[[y, x, 2]] = 200;
                img[[y, x, 3]] = 255;
            }
        }

        let result = vignette_u8(img.view(), 1.0);

        // Center pixel should be brighter than corner
        assert!(result[[2, 2, 0]] > result[[0, 0, 0]]);
        assert_eq!(result[[2, 2, 3]], 255); // Alpha preserved
    }

    #[test]
    fn test_vignette_f32_zero_amount() {
        let mut img = Array3::<f32>::zeros((3, 3, 3));
        for y in 0..3 {
            for x in 0..3 {
                img[[y, x, 0]] = 0.8;
            }
        }

        let result = vignette_f32(img.view(), 0.0);

        // No vignette effect
        assert!((result[[0, 0, 0]] - 0.8).abs() < 0.001);
        assert!((result[[2, 2, 0]] - 0.8).abs() < 0.001);
    }

    // Pencil sketch tests

    #[test]
    fn test_pencil_sketch_u8_output_shape() {
        let mut img = Array3::<u8>::zeros((10, 10, 4));
        for y in 0..10 {
            for x in 0..10 {
                img[[y, x, 0]] = (x * 25) as u8;
                img[[y, x, 1]] = (y * 25) as u8;
                img[[y, x, 2]] = 128;
                img[[y, x, 3]] = 255;
            }
        }

        let result = pencil_sketch_u8(img.view(), 60.0, 50.0);

        assert_eq!(result.dim(), (10, 10, 4));
        // Alpha preserved
        assert_eq!(result[[5, 5, 3]], 255);
        // Output should be grayscale (R=G=B)
        assert_eq!(result[[5, 5, 0]], result[[5, 5, 1]]);
        assert_eq!(result[[5, 5, 0]], result[[5, 5, 2]]);
    }

    #[test]
    fn test_pencil_sketch_u8_shade_factor() {
        let mut img = Array3::<u8>::zeros((10, 10, 4));
        for y in 0..10 {
            for x in 0..10 {
                img[[y, x, 0]] = if x < 5 { 50 } else { 200 };
                img[[y, x, 1]] = if x < 5 { 50 } else { 200 };
                img[[y, x, 2]] = if x < 5 { 50 } else { 200 };
                img[[y, x, 3]] = 255;
            }
        }

        let full = pencil_sketch_u8(img.view(), 60.0, 100.0);
        let half = pencil_sketch_u8(img.view(), 60.0, 50.0);

        // 50% shade should be darker than 100%
        let mut full_sum: u32 = 0;
        let mut half_sum: u32 = 0;
        for y in 0..10 {
            for x in 0..10 {
                full_sum += full[[y, x, 0]] as u32;
                half_sum += half[[y, x, 0]] as u32;
            }
        }
        assert!(half_sum < full_sum);
    }

    #[test]
    fn test_pencil_sketch_f32() {
        let mut img = Array3::<f32>::zeros((10, 10, 4));
        for y in 0..10 {
            for x in 0..10 {
                img[[y, x, 0]] = x as f32 / 10.0;
                img[[y, x, 1]] = y as f32 / 10.0;
                img[[y, x, 2]] = 0.5;
                img[[y, x, 3]] = 1.0;
            }
        }

        let result = pencil_sketch_f32(img.view(), 60.0, 50.0);

        assert_eq!(result.dim(), (10, 10, 4));
        // Values should be in range
        for y in 0..10 {
            for x in 0..10 {
                assert!(result[[y, x, 0]] >= 0.0 && result[[y, x, 0]] <= 1.0);
                assert_eq!(result[[y, x, 3]], 1.0); // Alpha preserved
            }
        }
    }
}
