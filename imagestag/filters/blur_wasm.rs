//! WASM-compatible blur filters: Gaussian Blur, Box Blur.
//!
//! These are single-threaded (no rayon) versions of the blur filters,
//! designed to work in WASM environments where threading is not available.
//!
//! ## Supported Formats
//!
//! All filters accept images with 1, 3, or 4 channels:
//! - **Grayscale**: (height, width, 1)
//! - **RGB**: (height, width, 3)
//! - **RGBA**: (height, width, 4) - uses premultiplied alpha blending

use ndarray::{Array3, ArrayView3};

/// Generate a 1D Gaussian kernel.
fn gaussian_kernel(sigma: f32) -> Vec<f32> {
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

// ============================================================================
// Gaussian Blur (WASM)
// ============================================================================

/// Separable Gaussian blur - u8 version (no rayon).
///
/// Uses premultiplied alpha for correct RGBA blending.
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels
/// * `sigma` - Blur radius (standard deviation)
///
/// # Returns
/// Blurred image with same channel count
pub fn gaussian_blur_wasm_u8(input: ArrayView3<u8>, sigma: f32) -> Array3<u8> {
    let (height, width, channels) = input.dim();
    if sigma <= 0.0 {
        return input.to_owned();
    }
    let kernel = gaussian_kernel(sigma);
    let half = kernel.len() / 2;
    let has_alpha = channels == 4;
    let color_channels = if has_alpha { 3 } else { channels };

    // Pass 1: Horizontal
    let mut temp = Array3::<f32>::zeros((height, width, channels));
    for y in 0..height {
        for x in 0..width {
            if has_alpha {
                let mut sum_rgb = [0.0f32; 3];
                let mut sum_a = 0.0f32;
                for (ki, &kv) in kernel.iter().enumerate() {
                    let sx = (x as isize + ki as isize - half as isize)
                        .clamp(0, width as isize - 1) as usize;
                    let a = input[[y, sx, 3]] as f32 / 255.0;
                    for c in 0..3 {
                        sum_rgb[c] += input[[y, sx, c]] as f32 * a * kv;
                    }
                    sum_a += a * kv;
                }
                for c in 0..3 {
                    temp[[y, x, c]] = sum_rgb[c];
                }
                temp[[y, x, 3]] = sum_a;
            } else {
                for c in 0..color_channels {
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

    // Pass 2: Vertical
    let mut output = Array3::<u8>::zeros((height, width, channels));
    for y in 0..height {
        for x in 0..width {
            if has_alpha {
                let mut sum_rgb = [0.0f32; 3];
                let mut sum_a = 0.0f32;
                for (ki, &kv) in kernel.iter().enumerate() {
                    let sy = (y as isize + ki as isize - half as isize)
                        .clamp(0, height as isize - 1) as usize;
                    for c in 0..3 {
                        sum_rgb[c] += temp[[sy, x, c]] * kv;
                    }
                    sum_a += temp[[sy, x, 3]] * kv;
                }
                let final_alpha = sum_a;
                if final_alpha > 0.001 {
                    for c in 0..3 {
                        output[[y, x, c]] = (sum_rgb[c] / final_alpha)
                            .clamp(0.0, 255.0) as u8;
                    }
                }
                output[[y, x, 3]] = (final_alpha * 255.0).clamp(0.0, 255.0) as u8;
            } else {
                for c in 0..color_channels {
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

/// Separable Gaussian blur - f32 version (no rayon).
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels, values 0.0-1.0
/// * `sigma` - Blur radius (standard deviation)
///
/// # Returns
/// Blurred image with same channel count
pub fn gaussian_blur_wasm_f32(input: ArrayView3<f32>, sigma: f32) -> Array3<f32> {
    let (height, width, channels) = input.dim();
    if sigma <= 0.0 {
        return input.to_owned();
    }
    let kernel = gaussian_kernel(sigma);
    let half = kernel.len() / 2;
    let has_alpha = channels == 4;
    let color_channels = if has_alpha { 3 } else { channels };

    // Pass 1: Horizontal
    let mut temp = Array3::<f32>::zeros((height, width, channels));
    for y in 0..height {
        for x in 0..width {
            if has_alpha {
                let mut sum_rgb = [0.0f32; 3];
                let mut sum_a = 0.0f32;
                for (ki, &kv) in kernel.iter().enumerate() {
                    let sx = (x as isize + ki as isize - half as isize)
                        .clamp(0, width as isize - 1) as usize;
                    let a = input[[y, sx, 3]];
                    for c in 0..3 {
                        sum_rgb[c] += input[[y, sx, c]] * a * kv;
                    }
                    sum_a += a * kv;
                }
                for c in 0..3 {
                    temp[[y, x, c]] = sum_rgb[c];
                }
                temp[[y, x, 3]] = sum_a;
            } else {
                for c in 0..color_channels {
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

    // Pass 2: Vertical
    let mut output = Array3::<f32>::zeros((height, width, channels));
    for y in 0..height {
        for x in 0..width {
            if has_alpha {
                let mut sum_rgb = [0.0f32; 3];
                let mut sum_a = 0.0f32;
                for (ki, &kv) in kernel.iter().enumerate() {
                    let sy = (y as isize + ki as isize - half as isize)
                        .clamp(0, height as isize - 1) as usize;
                    for c in 0..3 {
                        sum_rgb[c] += temp[[sy, x, c]] * kv;
                    }
                    sum_a += temp[[sy, x, 3]] * kv;
                }
                let final_alpha = sum_a;
                if final_alpha > 0.001 {
                    for c in 0..3 {
                        output[[y, x, c]] = (sum_rgb[c] / final_alpha).clamp(0.0, 1.0);
                    }
                }
                output[[y, x, 3]] = final_alpha.clamp(0.0, 1.0);
            } else {
                for c in 0..color_channels {
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
// Box Blur (WASM)
// ============================================================================

/// Box blur - u8 version (no rayon).
///
/// Uses premultiplied alpha for correct RGBA blending.
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels
/// * `radius` - Box blur radius (kernel is 2*radius+1)
///
/// # Returns
/// Blurred image with same channel count
pub fn box_blur_wasm_u8(input: ArrayView3<u8>, radius: u32) -> Array3<u8> {
    let (height, width, channels) = input.dim();
    let r = radius as isize;
    if r == 0 {
        return input.to_owned();
    }
    let has_alpha = channels == 4;
    let color_channels = if has_alpha { 3 } else { channels };

    // Pass 1: Horizontal
    let mut temp = Array3::<f32>::zeros((height, width, channels));
    for y in 0..height {
        for x in 0..width {
            let x_start = (x as isize - r).max(0) as usize;
            let x_end = (x as isize + r + 1).min(width as isize) as usize;
            let count = (x_end - x_start) as f32;

            if has_alpha {
                let mut sum_rgb = [0.0f32; 3];
                let mut sum_a = 0.0f32;
                for sx in x_start..x_end {
                    let a = input[[y, sx, 3]] as f32 / 255.0;
                    for c in 0..3 {
                        sum_rgb[c] += input[[y, sx, c]] as f32 * a;
                    }
                    sum_a += a;
                }
                for c in 0..3 {
                    temp[[y, x, c]] = sum_rgb[c] / count;
                }
                temp[[y, x, 3]] = sum_a / count;
            } else {
                for c in 0..color_channels {
                    let mut sum = 0.0f32;
                    for sx in x_start..x_end {
                        sum += input[[y, sx, c]] as f32;
                    }
                    temp[[y, x, c]] = sum / count;
                }
            }
        }
    }

    // Pass 2: Vertical
    let mut output = Array3::<u8>::zeros((height, width, channels));
    for y in 0..height {
        let y_start = (y as isize - r).max(0) as usize;
        let y_end = (y as isize + r + 1).min(height as isize) as usize;
        let count = (y_end - y_start) as f32;

        for x in 0..width {
            if has_alpha {
                let mut sum_rgb = [0.0f32; 3];
                let mut sum_a = 0.0f32;
                for sy in y_start..y_end {
                    for c in 0..3 {
                        sum_rgb[c] += temp[[sy, x, c]];
                    }
                    sum_a += temp[[sy, x, 3]];
                }
                let final_alpha = sum_a / count;
                if final_alpha > 0.001 {
                    for c in 0..3 {
                        output[[y, x, c]] = (sum_rgb[c] / count / final_alpha)
                            .clamp(0.0, 255.0) as u8;
                    }
                }
                output[[y, x, 3]] = (final_alpha * 255.0).clamp(0.0, 255.0) as u8;
            } else {
                for c in 0..color_channels {
                    let mut sum = 0.0f32;
                    for sy in y_start..y_end {
                        sum += temp[[sy, x, c]];
                    }
                    output[[y, x, c]] = (sum / count).clamp(0.0, 255.0) as u8;
                }
            }
        }
    }
    output
}

/// Box blur - f32 version (no rayon).
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels, values 0.0-1.0
/// * `radius` - Box blur radius
///
/// # Returns
/// Blurred image with same channel count
pub fn box_blur_wasm_f32(input: ArrayView3<f32>, radius: u32) -> Array3<f32> {
    let (height, width, channels) = input.dim();
    let r = radius as isize;
    if r == 0 {
        return input.to_owned();
    }
    let has_alpha = channels == 4;
    let color_channels = if has_alpha { 3 } else { channels };

    // Pass 1: Horizontal
    let mut temp = Array3::<f32>::zeros((height, width, channels));
    for y in 0..height {
        for x in 0..width {
            let x_start = (x as isize - r).max(0) as usize;
            let x_end = (x as isize + r + 1).min(width as isize) as usize;
            let count = (x_end - x_start) as f32;

            if has_alpha {
                let mut sum_rgb = [0.0f32; 3];
                let mut sum_a = 0.0f32;
                for sx in x_start..x_end {
                    let a = input[[y, sx, 3]];
                    for c in 0..3 {
                        sum_rgb[c] += input[[y, sx, c]] * a;
                    }
                    sum_a += a;
                }
                for c in 0..3 {
                    temp[[y, x, c]] = sum_rgb[c] / count;
                }
                temp[[y, x, 3]] = sum_a / count;
            } else {
                for c in 0..color_channels {
                    let mut sum = 0.0f32;
                    for sx in x_start..x_end {
                        sum += input[[y, sx, c]];
                    }
                    temp[[y, x, c]] = sum / count;
                }
            }
        }
    }

    // Pass 2: Vertical
    let mut output = Array3::<f32>::zeros((height, width, channels));
    for y in 0..height {
        let y_start = (y as isize - r).max(0) as usize;
        let y_end = (y as isize + r + 1).min(height as isize) as usize;
        let count = (y_end - y_start) as f32;

        for x in 0..width {
            if has_alpha {
                let mut sum_rgb = [0.0f32; 3];
                let mut sum_a = 0.0f32;
                for sy in y_start..y_end {
                    for c in 0..3 {
                        sum_rgb[c] += temp[[sy, x, c]];
                    }
                    sum_a += temp[[sy, x, 3]];
                }
                let final_alpha = sum_a / count;
                if final_alpha > 0.001 {
                    for c in 0..3 {
                        output[[y, x, c]] = (sum_rgb[c] / count / final_alpha).clamp(0.0, 1.0);
                    }
                }
                output[[y, x, 3]] = final_alpha.clamp(0.0, 1.0);
            } else {
                for c in 0..color_channels {
                    let mut sum = 0.0f32;
                    for sy in y_start..y_end {
                        sum += temp[[sy, x, c]];
                    }
                    output[[y, x, c]] = (sum / count).clamp(0.0, 1.0);
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
    fn test_gaussian_blur_wasm_u8_uniform() {
        let mut img = Array3::<u8>::zeros((5, 5, 4));
        for y in 0..5 {
            for x in 0..5 {
                img[[y, x, 0]] = 128;
                img[[y, x, 1]] = 128;
                img[[y, x, 2]] = 128;
                img[[y, x, 3]] = 255;
            }
        }

        let result = gaussian_blur_wasm_u8(img.view(), 1.0);

        // Uniform image should stay roughly uniform
        assert!((result[[2, 2, 0]] as i32 - 128).abs() <= 1);
    }

    #[test]
    fn test_gaussian_blur_wasm_f32_smooths() {
        let mut img = Array3::<f32>::zeros((5, 5, 3));
        img[[2, 2, 0]] = 1.0;

        let result = gaussian_blur_wasm_f32(img.view(), 1.0);

        // Center should be less than 1.0 (spread out)
        assert!(result[[2, 2, 0]] < 1.0);
        // Neighbors should be > 0
        assert!(result[[2, 1, 0]] > 0.0);
    }

    #[test]
    fn test_box_blur_wasm_u8_averages() {
        let mut img = Array3::<u8>::zeros((3, 3, 3));
        img[[1, 1, 0]] = 90; // 90 / 9 = 10 average

        let result = box_blur_wasm_u8(img.view(), 1);

        // Center should be roughly 10
        assert!(result[[1, 1, 0]] > 0);
        assert!(result[[1, 1, 0]] < 90);
    }

    #[test]
    fn test_box_blur_wasm_f32() {
        let mut img = Array3::<f32>::zeros((3, 3, 1));
        for y in 0..3 {
            for x in 0..3 {
                img[[y, x, 0]] = 0.5;
            }
        }

        let result = box_blur_wasm_f32(img.view(), 1);

        // Uniform should stay same
        assert!((result[[1, 1, 0]] - 0.5).abs() < 0.01);
    }

    #[test]
    fn test_gaussian_blur_wasm_zero_sigma() {
        let mut img = Array3::<u8>::zeros((3, 3, 3));
        img[[1, 1, 0]] = 200;

        let result = gaussian_blur_wasm_u8(img.view(), 0.0);

        // Zero sigma should be identity
        assert_eq!(result[[1, 1, 0]], 200);
    }
}
