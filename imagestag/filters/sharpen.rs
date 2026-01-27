//! Sharpen filters: Sharpen, Unsharp Mask, High Pass.
//!
//! These filters enhance or extract edge detail.
//! All filters support both u8 (0-255) and f32 (0.0-1.0) modes.
//!
//! ## Supported Formats
//!
//! All filters accept images with 1, 3, or 4 channels:
//! - **Grayscale**: (height, width, 1) - processes the single channel
//! - **RGB**: (height, width, 3) - processes all 3 channels
//! - **RGBA**: (height, width, 4) - processes RGB with alpha-aware boundary handling
//!
//! ## Alpha Handling
//!
//! For RGBA images, transparent neighbors (alpha=0) are treated like image boundaries:
//! their RGB values are replaced with the center pixel's RGB. This ensures:
//! - Transparent pixels have ZERO impact on the convolution result
//! - Opaque pixels adjacent to transparent regions remain unchanged
//! - No color bleeding from undefined RGB values in transparent pixels

use ndarray::{Array3, ArrayView3};

// ============================================================================
// Sharpen
// ============================================================================

/// Alpha threshold below which a pixel is considered transparent.
const ALPHA_THRESHOLD: f32 = 0.001;

/// Apply sharpening filter - u8 version.
///
/// Uses a 3x3 sharpening kernel. For RGBA, transparent neighbors are
/// replaced with center pixel color (boundary clamping).
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels)
/// * `amount` - Sharpening strength (0.0-10.0, 1.0 = standard)
///
/// # Returns
/// Sharpened image with same channel count
pub fn sharpen_u8(input: ArrayView3<u8>, amount: f32) -> Array3<u8> {
    let (height, width, channels) = input.dim();
    let mut output = Array3::<u8>::zeros((height, width, channels));

    // Sharpening kernel:
    //  0  -a   0
    // -a 1+4a -a
    //  0  -a   0
    // where a = amount

    let center_weight = 1.0 + 4.0 * amount;
    let edge_weight = -amount;

    let color_channels = if channels == 4 { 3 } else { channels };
    let has_alpha = channels == 4;

    for y in 1..height.saturating_sub(1) {
        for x in 1..width.saturating_sub(1) {
            if has_alpha {
                let a_center = input[[y, x, 3]] as f32 / 255.0;

                // Copy alpha unchanged
                output[[y, x, 3]] = input[[y, x, 3]];

                // If center pixel is transparent, just copy RGB
                if a_center < ALPHA_THRESHOLD {
                    for c in 0..3 {
                        output[[y, x, c]] = input[[y, x, c]];
                    }
                    continue;
                }

                // Get neighbor alpha values
                let a_top = input[[y - 1, x, 3]] as f32 / 255.0;
                let a_bottom = input[[y + 1, x, 3]] as f32 / 255.0;
                let a_left = input[[y, x - 1, 3]] as f32 / 255.0;
                let a_right = input[[y, x + 1, 3]] as f32 / 255.0;

                for c in 0..3 {
                    let v_center = input[[y, x, c]] as f32;

                    // For transparent neighbors, use center pixel value (boundary clamping)
                    // This ensures transparent pixels have ZERO impact
                    let v_top = if a_top >= ALPHA_THRESHOLD {
                        input[[y - 1, x, c]] as f32
                    } else {
                        v_center
                    };
                    let v_bottom = if a_bottom >= ALPHA_THRESHOLD {
                        input[[y + 1, x, c]] as f32
                    } else {
                        v_center
                    };
                    let v_left = if a_left >= ALPHA_THRESHOLD {
                        input[[y, x - 1, c]] as f32
                    } else {
                        v_center
                    };
                    let v_right = if a_right >= ALPHA_THRESHOLD {
                        input[[y, x + 1, c]] as f32
                    } else {
                        v_center
                    };

                    let sum = v_top * edge_weight
                        + v_bottom * edge_weight
                        + v_left * edge_weight
                        + v_right * edge_weight
                        + v_center * center_weight;

                    output[[y, x, c]] = sum.clamp(0.0, 255.0) as u8;
                }
            } else {
                // RGB or grayscale - no alpha handling needed
                for c in 0..color_channels {
                    let sum = input[[y - 1, x, c]] as f32 * edge_weight
                        + input[[y + 1, x, c]] as f32 * edge_weight
                        + input[[y, x - 1, c]] as f32 * edge_weight
                        + input[[y, x + 1, c]] as f32 * edge_weight
                        + input[[y, x, c]] as f32 * center_weight;

                    output[[y, x, c]] = sum.clamp(0.0, 255.0) as u8;
                }
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

/// Apply sharpening filter - f32 version.
///
/// Uses boundary clamping for RGBA images: transparent neighbors are
/// replaced with center pixel color (ZERO impact from transparent pixels).
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels), values 0.0-1.0
/// * `amount` - Sharpening strength (0.0-10.0, 1.0 = standard)
///
/// # Returns
/// Sharpened image with same channel count
pub fn sharpen_f32(input: ArrayView3<f32>, amount: f32) -> Array3<f32> {
    let (height, width, channels) = input.dim();
    let mut output = Array3::<f32>::zeros((height, width, channels));

    let center_weight = 1.0 + 4.0 * amount;
    let edge_weight = -amount;

    let color_channels = if channels == 4 { 3 } else { channels };
    let has_alpha = channels == 4;

    for y in 1..height.saturating_sub(1) {
        for x in 1..width.saturating_sub(1) {
            if has_alpha {
                let a_center = input[[y, x, 3]];

                // Copy alpha unchanged
                output[[y, x, 3]] = a_center;

                // If center pixel is transparent, just copy RGB
                if a_center < ALPHA_THRESHOLD {
                    for c in 0..3 {
                        output[[y, x, c]] = input[[y, x, c]];
                    }
                    continue;
                }

                // Get neighbor alpha values
                let a_top = input[[y - 1, x, 3]];
                let a_bottom = input[[y + 1, x, 3]];
                let a_left = input[[y, x - 1, 3]];
                let a_right = input[[y, x + 1, 3]];

                for c in 0..3 {
                    let v_center = input[[y, x, c]];

                    // For transparent neighbors, use center pixel value (boundary clamping)
                    // This ensures transparent pixels have ZERO impact
                    let v_top = if a_top >= ALPHA_THRESHOLD {
                        input[[y - 1, x, c]]
                    } else {
                        v_center
                    };
                    let v_bottom = if a_bottom >= ALPHA_THRESHOLD {
                        input[[y + 1, x, c]]
                    } else {
                        v_center
                    };
                    let v_left = if a_left >= ALPHA_THRESHOLD {
                        input[[y, x - 1, c]]
                    } else {
                        v_center
                    };
                    let v_right = if a_right >= ALPHA_THRESHOLD {
                        input[[y, x + 1, c]]
                    } else {
                        v_center
                    };

                    let sum = v_top * edge_weight
                        + v_bottom * edge_weight
                        + v_left * edge_weight
                        + v_right * edge_weight
                        + v_center * center_weight;

                    output[[y, x, c]] = sum.clamp(0.0, 1.0);
                }
            } else {
                // RGB or grayscale - no alpha handling needed
                for c in 0..color_channels {
                    let sum = input[[y - 1, x, c]] * edge_weight
                        + input[[y + 1, x, c]] * edge_weight
                        + input[[y, x - 1, c]] * edge_weight
                        + input[[y, x + 1, c]] * edge_weight
                        + input[[y, x, c]] * center_weight;

                    output[[y, x, c]] = sum.clamp(0.0, 1.0);
                }
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

// ============================================================================
// Gaussian Blur (helper for Unsharp Mask and High Pass)
// ============================================================================

/// 1D Gaussian kernel.
fn gaussian_kernel_1d(sigma: f32) -> Vec<f32> {
    if sigma <= 0.0 {
        return vec![1.0];
    }

    let kernel_size = ((sigma * 6.0).ceil() as usize) | 1;
    let half = kernel_size / 2;

    let mut kernel: Vec<f32> = (0..kernel_size)
        .map(|i| {
            let x = i as f32 - half as f32;
            (-x * x / (2.0 * sigma * sigma)).exp()
        })
        .collect();

    let sum: f32 = kernel.iter().sum();
    for v in kernel.iter_mut() {
        *v /= sum;
    }

    kernel
}

/// Apply separable Gaussian blur with proper alpha handling.
///
/// For RGBA images, uses premultiplied alpha to prevent transparent pixels
/// from bleeding into the result.
fn gaussian_blur_internal_u8(input: ArrayView3<u8>, sigma: f32) -> Array3<u8> {
    let (height, width, channels) = input.dim();
    let kernel = gaussian_kernel_1d(sigma);
    let half = kernel.len() / 2;
    let has_alpha = channels == 4;

    // For RGBA, we blur premultiplied values then unpremultiply
    // Horizontal pass - work in f32 with premultiplied alpha
    let mut temp = Array3::<f32>::zeros((height, width, channels));
    for y in 0..height {
        for x in 0..width {
            if has_alpha {
                let mut sum_rgb = [0.0f32; 3];
                let mut sum_alpha = 0.0f32;

                for (ki, &kv) in kernel.iter().enumerate() {
                    let sx = (x as isize + ki as isize - half as isize)
                        .clamp(0, width as isize - 1) as usize;
                    let a = input[[y, sx, 3]] as f32 / 255.0;
                    sum_alpha += a * kv;
                    for c in 0..3 {
                        // Premultiplied: RGB * alpha
                        sum_rgb[c] += input[[y, sx, c]] as f32 * a * kv;
                    }
                }

                for c in 0..3 {
                    temp[[y, x, c]] = sum_rgb[c];
                }
                temp[[y, x, 3]] = sum_alpha;
            } else {
                for c in 0..channels {
                    let mut sum = 0.0f32;
                    for (ki, &kv) in kernel.iter().enumerate() {
                        let sx = (x as isize + ki as isize - half as isize)
                            .clamp(0, width as isize - 1) as usize;
                        sum += input[[y, sx, c]] as f32 * kv;
                    }
                    temp[[y, x, c]] = sum;
                }
            }
        }
    }

    // Vertical pass
    let mut output = Array3::<u8>::zeros((height, width, channels));
    for y in 0..height {
        for x in 0..width {
            if has_alpha {
                let mut sum_rgb = [0.0f32; 3];
                let mut sum_alpha = 0.0f32;

                for (ki, &kv) in kernel.iter().enumerate() {
                    let sy = (y as isize + ki as isize - half as isize)
                        .clamp(0, height as isize - 1) as usize;
                    sum_alpha += temp[[sy, x, 3]] * kv;
                    for c in 0..3 {
                        sum_rgb[c] += temp[[sy, x, c]] * kv;
                    }
                }

                // Unpremultiply
                let final_alpha = sum_alpha.clamp(0.0, 1.0);
                output[[y, x, 3]] = (final_alpha * 255.0) as u8;

                if final_alpha > 0.001 {
                    for c in 0..3 {
                        let unpremultiplied = sum_rgb[c] / final_alpha;
                        output[[y, x, c]] = unpremultiplied.clamp(0.0, 255.0) as u8;
                    }
                } else {
                    for c in 0..3 {
                        output[[y, x, c]] = 0;
                    }
                }
            } else {
                for c in 0..channels {
                    let mut sum = 0.0f32;
                    for (ki, &kv) in kernel.iter().enumerate() {
                        let sy = (y as isize + ki as isize - half as isize)
                            .clamp(0, height as isize - 1) as usize;
                        sum += temp[[sy, x, c]] * kv;
                    }
                    output[[y, x, c]] = sum.clamp(0.0, 255.0) as u8;
                }
            }
        }
    }

    output
}

/// Apply separable Gaussian blur with proper alpha handling - f32 version.
fn gaussian_blur_internal_f32(input: ArrayView3<f32>, sigma: f32) -> Array3<f32> {
    let (height, width, channels) = input.dim();
    let kernel = gaussian_kernel_1d(sigma);
    let half = kernel.len() / 2;
    let has_alpha = channels == 4;

    // Horizontal pass - work with premultiplied alpha for RGBA
    let mut temp = Array3::<f32>::zeros((height, width, channels));
    for y in 0..height {
        for x in 0..width {
            if has_alpha {
                let mut sum_rgb = [0.0f32; 3];
                let mut sum_alpha = 0.0f32;

                for (ki, &kv) in kernel.iter().enumerate() {
                    let sx = (x as isize + ki as isize - half as isize)
                        .clamp(0, width as isize - 1) as usize;
                    let a = input[[y, sx, 3]];
                    sum_alpha += a * kv;
                    for c in 0..3 {
                        sum_rgb[c] += input[[y, sx, c]] * a * kv;
                    }
                }

                for c in 0..3 {
                    temp[[y, x, c]] = sum_rgb[c];
                }
                temp[[y, x, 3]] = sum_alpha;
            } else {
                for c in 0..channels {
                    let mut sum = 0.0f32;
                    for (ki, &kv) in kernel.iter().enumerate() {
                        let sx = (x as isize + ki as isize - half as isize)
                            .clamp(0, width as isize - 1) as usize;
                        sum += input[[y, sx, c]] * kv;
                    }
                    temp[[y, x, c]] = sum;
                }
            }
        }
    }

    // Vertical pass
    let mut output = Array3::<f32>::zeros((height, width, channels));
    for y in 0..height {
        for x in 0..width {
            if has_alpha {
                let mut sum_rgb = [0.0f32; 3];
                let mut sum_alpha = 0.0f32;

                for (ki, &kv) in kernel.iter().enumerate() {
                    let sy = (y as isize + ki as isize - half as isize)
                        .clamp(0, height as isize - 1) as usize;
                    sum_alpha += temp[[sy, x, 3]] * kv;
                    for c in 0..3 {
                        sum_rgb[c] += temp[[sy, x, c]] * kv;
                    }
                }

                // Unpremultiply
                let final_alpha = sum_alpha.clamp(0.0, 1.0);
                output[[y, x, 3]] = final_alpha;

                if final_alpha > 0.001 {
                    for c in 0..3 {
                        let unpremultiplied = sum_rgb[c] / final_alpha;
                        output[[y, x, c]] = unpremultiplied.clamp(0.0, 1.0);
                    }
                } else {
                    for c in 0..3 {
                        output[[y, x, c]] = 0.0;
                    }
                }
            } else {
                for c in 0..channels {
                    let mut sum = 0.0f32;
                    for (ki, &kv) in kernel.iter().enumerate() {
                        let sy = (y as isize + ki as isize - half as isize)
                            .clamp(0, height as isize - 1) as usize;
                        sum += temp[[sy, x, c]] * kv;
                    }
                    output[[y, x, c]] = sum.clamp(0.0, 1.0);
                }
            }
        }
    }

    output
}

// ============================================================================
// Unsharp Mask
// ============================================================================

/// Apply unsharp mask - u8 version.
///
/// Sharpens by subtracting a blurred version of the image.
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels)
/// * `amount` - Sharpening amount (0.0-5.0, 1.0 = 100%)
/// * `radius` - Blur radius for the mask (sigma, typically 0.5-3.0)
/// * `threshold` - Minimum difference to sharpen (0-255), prevents noise amplification
///
/// # Returns
/// Sharpened image with same channel count
pub fn unsharp_mask_u8(
    input: ArrayView3<u8>,
    amount: f32,
    radius: f32,
    threshold: u8,
) -> Array3<u8> {
    let (height, width, channels) = input.dim();
    let mut output = Array3::<u8>::zeros((height, width, channels));

    // Create blurred version
    let blurred = gaussian_blur_internal_u8(input, radius);

    let color_channels = if channels == 4 { 3 } else { channels };

    for y in 0..height {
        for x in 0..width {
            for c in 0..color_channels {
                let orig = input[[y, x, c]] as f32;
                let blur = blurred[[y, x, c]] as f32;
                let diff = orig - blur;

                // Only sharpen if difference exceeds threshold
                let sharpened = if diff.abs() > threshold as f32 {
                    orig + diff * amount
                } else {
                    orig
                };

                output[[y, x, c]] = sharpened.clamp(0.0, 255.0) as u8;
            }
            if channels == 4 {
                output[[y, x, 3]] = input[[y, x, 3]];
            }
        }
    }

    output
}

/// Apply unsharp mask - f32 version.
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels), values 0.0-1.0
/// * `amount` - Sharpening amount (0.0-5.0, 1.0 = 100%)
/// * `radius` - Blur radius for the mask (sigma, typically 0.5-3.0)
/// * `threshold` - Minimum difference to sharpen (0.0-1.0), prevents noise amplification
///
/// # Returns
/// Sharpened image with same channel count
pub fn unsharp_mask_f32(
    input: ArrayView3<f32>,
    amount: f32,
    radius: f32,
    threshold: f32,
) -> Array3<f32> {
    let (height, width, channels) = input.dim();
    let mut output = Array3::<f32>::zeros((height, width, channels));

    let blurred = gaussian_blur_internal_f32(input, radius);

    let color_channels = if channels == 4 { 3 } else { channels };

    for y in 0..height {
        for x in 0..width {
            for c in 0..color_channels {
                let orig = input[[y, x, c]];
                let blur = blurred[[y, x, c]];
                let diff = orig - blur;

                let sharpened = if diff.abs() > threshold {
                    orig + diff * amount
                } else {
                    orig
                };

                output[[y, x, c]] = sharpened.clamp(0.0, 1.0);
            }
            if channels == 4 {
                output[[y, x, 3]] = input[[y, x, 3]];
            }
        }
    }

    output
}

// ============================================================================
// High Pass
// ============================================================================

/// Apply high pass filter - u8 version.
///
/// Extracts high-frequency detail (edges) by subtracting a blurred version.
/// Result is centered at 128 (gray).
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels)
/// * `radius` - Blur radius (sigma). Larger = more detail extracted.
///
/// # Returns
/// High-pass filtered image with same channel count
pub fn high_pass_u8(input: ArrayView3<u8>, radius: f32) -> Array3<u8> {
    let (height, width, channels) = input.dim();
    let mut output = Array3::<u8>::zeros((height, width, channels));

    let blurred = gaussian_blur_internal_u8(input, radius);

    let color_channels = if channels == 4 { 3 } else { channels };

    for y in 0..height {
        for x in 0..width {
            for c in 0..color_channels {
                let orig = input[[y, x, c]] as f32;
                let blur = blurred[[y, x, c]] as f32;
                // Center at 128
                let high_pass = (orig - blur) + 128.0;
                output[[y, x, c]] = high_pass.clamp(0.0, 255.0) as u8;
            }
            if channels == 4 {
                output[[y, x, 3]] = input[[y, x, 3]];
            }
        }
    }

    output
}

/// Apply high pass filter - f32 version.
///
/// Result is centered at 0.5 (gray).
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels), values 0.0-1.0
/// * `radius` - Blur radius (sigma). Larger = more detail extracted.
///
/// # Returns
/// High-pass filtered image with same channel count
pub fn high_pass_f32(input: ArrayView3<f32>, radius: f32) -> Array3<f32> {
    let (height, width, channels) = input.dim();
    let mut output = Array3::<f32>::zeros((height, width, channels));

    let blurred = gaussian_blur_internal_f32(input, radius);

    let color_channels = if channels == 4 { 3 } else { channels };

    for y in 0..height {
        for x in 0..width {
            for c in 0..color_channels {
                let orig = input[[y, x, c]];
                let blur = blurred[[y, x, c]];
                // Center at 0.5
                let high_pass = (orig - blur) + 0.5;
                output[[y, x, c]] = high_pass.clamp(0.0, 1.0);
            }
            if channels == 4 {
                output[[y, x, 3]] = input[[y, x, 3]];
            }
        }
    }

    output
}

// ============================================================================
// Motion Blur
// ============================================================================

/// Apply motion blur - u8 version.
///
/// Creates directional blur simulating camera or object motion.
/// For RGBA images, uses premultiplied alpha to prevent transparent pixels
/// from bleeding into the result.
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels)
/// * `angle` - Direction of motion in degrees (0 = horizontal right)
/// * `distance` - Blur distance in pixels
///
/// # Returns
/// Motion-blurred image with same channel count
pub fn motion_blur_u8(input: ArrayView3<u8>, angle: f32, distance: f32) -> Array3<u8> {
    let (height, width, channels) = input.dim();
    let mut output = Array3::<u8>::zeros((height, width, channels));

    let angle_rad = angle.to_radians();
    let dx = angle_rad.cos();
    let dy = angle_rad.sin();

    let steps = (distance.abs().ceil() as usize).max(1);
    let step_weight = 1.0 / steps as f32;
    let has_alpha = channels == 4;

    for y in 0..height {
        for x in 0..width {
            if has_alpha {
                let mut sum_rgb = [0.0f32; 3];
                let mut sum_alpha = 0.0f32;

                for i in 0..steps {
                    let t = i as f32 - (steps as f32 - 1.0) / 2.0;
                    let sx = (x as f32 + dx * t).round() as isize;
                    let sy = (y as f32 + dy * t).round() as isize;

                    let sx = sx.clamp(0, width as isize - 1) as usize;
                    let sy = sy.clamp(0, height as isize - 1) as usize;

                    let a = input[[sy, sx, 3]] as f32 / 255.0;
                    sum_alpha += a * step_weight;
                    for c in 0..3 {
                        // Premultiplied: RGB * alpha
                        sum_rgb[c] += input[[sy, sx, c]] as f32 * a * step_weight;
                    }
                }

                // Unpremultiply
                let final_alpha = sum_alpha.clamp(0.0, 1.0);
                output[[y, x, 3]] = (final_alpha * 255.0) as u8;

                if final_alpha > 0.001 {
                    for c in 0..3 {
                        let unpremultiplied = sum_rgb[c] / final_alpha;
                        output[[y, x, c]] = unpremultiplied.clamp(0.0, 255.0) as u8;
                    }
                } else {
                    for c in 0..3 {
                        output[[y, x, c]] = 0;
                    }
                }
            } else {
                let mut sum = vec![0.0f32; channels];

                for i in 0..steps {
                    let t = i as f32 - (steps as f32 - 1.0) / 2.0;
                    let sx = (x as f32 + dx * t).round() as isize;
                    let sy = (y as f32 + dy * t).round() as isize;

                    let sx = sx.clamp(0, width as isize - 1) as usize;
                    let sy = sy.clamp(0, height as isize - 1) as usize;

                    for c in 0..channels {
                        sum[c] += input[[sy, sx, c]] as f32 * step_weight;
                    }
                }

                for c in 0..channels {
                    output[[y, x, c]] = sum[c].clamp(0.0, 255.0) as u8;
                }
            }
        }
    }

    output
}

/// Apply motion blur - f32 version.
///
/// For RGBA images, uses premultiplied alpha to prevent transparent pixels
/// from bleeding into the result.
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels), values 0.0-1.0
/// * `angle` - Direction of motion in degrees (0 = horizontal right)
/// * `distance` - Blur distance in pixels
///
/// # Returns
/// Motion-blurred image with same channel count
pub fn motion_blur_f32(input: ArrayView3<f32>, angle: f32, distance: f32) -> Array3<f32> {
    let (height, width, channels) = input.dim();
    let mut output = Array3::<f32>::zeros((height, width, channels));

    let angle_rad = angle.to_radians();
    let dx = angle_rad.cos();
    let dy = angle_rad.sin();

    let steps = (distance.abs().ceil() as usize).max(1);
    let step_weight = 1.0 / steps as f32;
    let has_alpha = channels == 4;

    for y in 0..height {
        for x in 0..width {
            if has_alpha {
                let mut sum_rgb = [0.0f32; 3];
                let mut sum_alpha = 0.0f32;

                for i in 0..steps {
                    let t = i as f32 - (steps as f32 - 1.0) / 2.0;
                    let sx = (x as f32 + dx * t).round() as isize;
                    let sy = (y as f32 + dy * t).round() as isize;

                    let sx = sx.clamp(0, width as isize - 1) as usize;
                    let sy = sy.clamp(0, height as isize - 1) as usize;

                    let a = input[[sy, sx, 3]];
                    sum_alpha += a * step_weight;
                    for c in 0..3 {
                        // Premultiplied: RGB * alpha
                        sum_rgb[c] += input[[sy, sx, c]] * a * step_weight;
                    }
                }

                // Unpremultiply
                let final_alpha = sum_alpha.clamp(0.0, 1.0);
                output[[y, x, 3]] = final_alpha;

                if final_alpha > 0.001 {
                    for c in 0..3 {
                        let unpremultiplied = sum_rgb[c] / final_alpha;
                        output[[y, x, c]] = unpremultiplied.clamp(0.0, 1.0);
                    }
                } else {
                    for c in 0..3 {
                        output[[y, x, c]] = 0.0;
                    }
                }
            } else {
                let mut sum = vec![0.0f32; channels];

                for i in 0..steps {
                    let t = i as f32 - (steps as f32 - 1.0) / 2.0;
                    let sx = (x as f32 + dx * t).round() as isize;
                    let sy = (y as f32 + dy * t).round() as isize;

                    let sx = sx.clamp(0, width as isize - 1) as usize;
                    let sy = sy.clamp(0, height as isize - 1) as usize;

                    for c in 0..channels {
                        sum[c] += input[[sy, sx, c]] * step_weight;
                    }
                }

                for c in 0..channels {
                    output[[y, x, c]] = sum[c].clamp(0.0, 1.0);
                }
            }
        }
    }

    output
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_sharpen_u8_preserves_flat() {
        // A flat color image should stay roughly the same
        let mut img = Array3::<u8>::zeros((3, 3, 4));
        for y in 0..3 {
            for x in 0..3 {
                img[[y, x, 0]] = 128;
                img[[y, x, 1]] = 128;
                img[[y, x, 2]] = 128;
                img[[y, x, 3]] = 255;
            }
        }

        let result = sharpen_u8(img.view(), 1.0);

        // Center pixel should stay 128
        assert_eq!(result[[1, 1, 0]], 128);
    }

    #[test]
    fn test_sharpen_f32_enhances_edge() {
        // Create an edge
        let mut img = Array3::<f32>::zeros((3, 3, 4));
        for y in 0..3 {
            for x in 0..3 {
                img[[y, x, 0]] = if x == 1 { 1.0 } else { 0.0 };
                img[[y, x, 3]] = 1.0;
            }
        }

        let result = sharpen_f32(img.view(), 1.0);

        // Center of bright column should be enhanced
        assert!(result[[1, 1, 0]] >= 1.0 || result[[1, 1, 0]] > 0.9);
    }

    #[test]
    fn test_unsharp_mask_u8_threshold() {
        let mut img = Array3::<u8>::zeros((3, 3, 4));
        for y in 0..3 {
            for x in 0..3 {
                img[[y, x, 0]] = 128;
                img[[y, x, 3]] = 255;
            }
        }
        // Add small noise
        img[[1, 1, 0]] = 130;

        // High threshold should ignore small noise
        let result = unsharp_mask_u8(img.view(), 2.0, 1.0, 50);

        // Should not be sharpened (difference of 2 < threshold 50)
        assert!((result[[1, 1, 0]] as i32 - 130).abs() <= 5);
    }

    #[test]
    fn test_high_pass_u8_flat_is_gray() {
        let mut img = Array3::<u8>::zeros((5, 5, 4));
        for y in 0..5 {
            for x in 0..5 {
                img[[y, x, 0]] = 100;
                img[[y, x, 1]] = 100;
                img[[y, x, 2]] = 100;
                img[[y, x, 3]] = 255;
            }
        }

        let result = high_pass_u8(img.view(), 1.0);

        // Flat area should be centered at 128
        assert!((result[[2, 2, 0]] as i32 - 128).abs() <= 2);
    }

    #[test]
    fn test_high_pass_f32_flat_is_gray() {
        let mut img = Array3::<f32>::zeros((5, 5, 4));
        for y in 0..5 {
            for x in 0..5 {
                img[[y, x, 0]] = 0.4;
                img[[y, x, 3]] = 1.0;
            }
        }

        let result = high_pass_f32(img.view(), 1.0);

        // Flat area should be centered at 0.5
        assert!((result[[2, 2, 0]] - 0.5).abs() < 0.01);
    }

    #[test]
    fn test_motion_blur_u8_horizontal() {
        let mut img = Array3::<u8>::zeros((3, 5, 4));
        // Vertical white line in center
        for y in 0..3 {
            img[[y, 2, 0]] = 255;
            img[[y, 2, 3]] = 255;
        }

        let result = motion_blur_u8(img.view(), 0.0, 3.0);

        // Blur should spread horizontally
        assert!(result[[1, 1, 0]] > 0); // Left of center has some white
        assert!(result[[1, 3, 0]] > 0); // Right of center has some white
    }
}
