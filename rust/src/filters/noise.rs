//! Noise filters: Add Noise, Median, Denoise.
//!
//! These filters add or remove noise from images.
//! All filters support both u8 (0-255) and f32 (0.0-1.0) modes.
//!
//! ## Supported Formats
//!
//! All filters accept images with 1, 3, or 4 channels:
//! - **Grayscale**: (height, width, 1) - processes the single channel
//! - **RGB**: (height, width, 3) - processes all 3 channels
//! - **RGBA**: (height, width, 4) - processes RGB, preserves alpha
//!
//! ## Alpha Handling
//!
//! - **Add Noise**: Per-pixel operation, preserves alpha unchanged
//! - **Median**: Processes RGB channels independently, preserves alpha
//! - **Denoise**: Uses premultiplied alpha to prevent transparent pixel bleeding

use ndarray::{Array3, ArrayView3};

// ============================================================================
// Simple RNG (deterministic for parity testing)
// ============================================================================

/// Simple linear congruential generator for deterministic noise.
/// Uses MINSTD parameters.
struct SimpleRng {
    state: u64,
}

impl SimpleRng {
    fn new(seed: u64) -> Self {
        SimpleRng {
            state: seed.wrapping_add(1), // Avoid zero
        }
    }

    /// Generate next random u32.
    fn next_u32(&mut self) -> u32 {
        // MINSTD LCG
        self.state = self.state.wrapping_mul(48271).wrapping_add(1) % 2147483647;
        self.state as u32
    }

    /// Generate uniform random f32 in [0, 1).
    fn next_f32(&mut self) -> f32 {
        (self.next_u32() as f32) / (2147483647.0f32)
    }

    /// Generate Gaussian random f32 using Box-Muller transform.
    fn next_gaussian(&mut self) -> f32 {
        let u1 = self.next_f32().max(1e-10);
        let u2 = self.next_f32();
        (-2.0 * u1.ln()).sqrt() * (2.0 * std::f32::consts::PI * u2).cos()
    }
}

// ============================================================================
// Add Noise
// ============================================================================

/// Add noise to image - u8 version.
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels)
/// * `amount` - Noise amount (0.0-1.0, where 1.0 = max noise)
/// * `gaussian` - If true, use Gaussian noise; if false, use uniform noise
/// * `monochrome` - If true, same noise for all color channels; if false, independent noise
/// * `seed` - Random seed for deterministic results
///
/// # Returns
/// Noisy image with same channel count
pub fn add_noise_u8(
    input: ArrayView3<u8>,
    amount: f32,
    gaussian: bool,
    monochrome: bool,
    seed: u64,
) -> Array3<u8> {
    let (height, width, channels) = input.dim();
    let mut output = Array3::<u8>::zeros((height, width, channels));
    let mut rng = SimpleRng::new(seed);

    let scale = amount * 255.0;
    let color_channels = if channels == 4 { 3 } else { channels };

    for y in 0..height {
        for x in 0..width {
            if monochrome {
                // Same noise for all channels
                let noise = if gaussian {
                    rng.next_gaussian() * scale
                } else {
                    (rng.next_f32() - 0.5) * 2.0 * scale
                };

                for c in 0..color_channels {
                    let v = input[[y, x, c]] as f32 + noise;
                    output[[y, x, c]] = v.clamp(0.0, 255.0) as u8;
                }
            } else {
                // Independent noise per channel
                for c in 0..color_channels {
                    let noise = if gaussian {
                        rng.next_gaussian() * scale
                    } else {
                        (rng.next_f32() - 0.5) * 2.0 * scale
                    };

                    let v = input[[y, x, c]] as f32 + noise;
                    output[[y, x, c]] = v.clamp(0.0, 255.0) as u8;
                }
            }
            if channels == 4 {
                output[[y, x, 3]] = input[[y, x, 3]];
            }
        }
    }

    output
}

/// Add noise to image - f32 version.
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels), values 0.0-1.0
/// * `amount` - Noise amount (0.0-1.0, where 1.0 = max noise)
/// * `gaussian` - If true, use Gaussian noise; if false, use uniform noise
/// * `monochrome` - If true, same noise for all color channels; if false, independent noise
/// * `seed` - Random seed for deterministic results
///
/// # Returns
/// Noisy image with same channel count
pub fn add_noise_f32(
    input: ArrayView3<f32>,
    amount: f32,
    gaussian: bool,
    monochrome: bool,
    seed: u64,
) -> Array3<f32> {
    let (height, width, channels) = input.dim();
    let mut output = Array3::<f32>::zeros((height, width, channels));
    let mut rng = SimpleRng::new(seed);

    let color_channels = if channels == 4 { 3 } else { channels };

    for y in 0..height {
        for x in 0..width {
            if monochrome {
                let noise = if gaussian {
                    rng.next_gaussian() * amount
                } else {
                    (rng.next_f32() - 0.5) * 2.0 * amount
                };

                for c in 0..color_channels {
                    output[[y, x, c]] = (input[[y, x, c]] + noise).clamp(0.0, 1.0);
                }
            } else {
                for c in 0..color_channels {
                    let noise = if gaussian {
                        rng.next_gaussian() * amount
                    } else {
                        (rng.next_f32() - 0.5) * 2.0 * amount
                    };

                    output[[y, x, c]] = (input[[y, x, c]] + noise).clamp(0.0, 1.0);
                }
            }
            if channels == 4 {
                output[[y, x, 3]] = input[[y, x, 3]];
            }
        }
    }

    output
}

// ============================================================================
// Median Filter
// ============================================================================

/// Apply median filter - u8 version.
///
/// Removes salt-and-pepper noise while preserving edges.
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels)
/// * `radius` - Filter radius (1-10)
///
/// # Returns
/// Median-filtered image with same channel count
pub fn median_u8(input: ArrayView3<u8>, radius: u32) -> Array3<u8> {
    let (height, width, channels) = input.dim();
    let mut output = Array3::<u8>::zeros((height, width, channels));

    let radius = radius.min(10) as usize;
    let window_size = (radius * 2 + 1) * (radius * 2 + 1);

    let color_channels = if channels == 4 { 3 } else { channels };

    for y in 0..height {
        for x in 0..width {
            for c in 0..color_channels {
                let mut values: Vec<u8> = Vec::with_capacity(window_size);

                for dy in 0..=(radius * 2) {
                    let sy = (y as isize + dy as isize - radius as isize)
                        .clamp(0, height as isize - 1) as usize;

                    for dx in 0..=(radius * 2) {
                        let sx = (x as isize + dx as isize - radius as isize)
                            .clamp(0, width as isize - 1) as usize;

                        values.push(input[[sy, sx, c]]);
                    }
                }

                values.sort_unstable();
                output[[y, x, c]] = values[values.len() / 2];
            }
            if channels == 4 {
                output[[y, x, 3]] = input[[y, x, 3]];
            }
        }
    }

    output
}

/// Apply median filter - f32 version.
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels), values 0.0-1.0
/// * `radius` - Filter radius (1-10)
///
/// # Returns
/// Median-filtered image with same channel count
pub fn median_f32(input: ArrayView3<f32>, radius: u32) -> Array3<f32> {
    let (height, width, channels) = input.dim();
    let mut output = Array3::<f32>::zeros((height, width, channels));

    let radius = radius.min(10) as usize;
    let window_size = (radius * 2 + 1) * (radius * 2 + 1);

    let color_channels = if channels == 4 { 3 } else { channels };

    for y in 0..height {
        for x in 0..width {
            for c in 0..color_channels {
                let mut values: Vec<f32> = Vec::with_capacity(window_size);

                for dy in 0..=(radius * 2) {
                    let sy = (y as isize + dy as isize - radius as isize)
                        .clamp(0, height as isize - 1) as usize;

                    for dx in 0..=(radius * 2) {
                        let sx = (x as isize + dx as isize - radius as isize)
                            .clamp(0, width as isize - 1) as usize;

                        values.push(input[[sy, sx, c]]);
                    }
                }

                values.sort_by(|a, b| a.partial_cmp(b).unwrap());
                output[[y, x, c]] = values[values.len() / 2];
            }
            if channels == 4 {
                output[[y, x, 3]] = input[[y, x, 3]];
            }
        }
    }

    output
}

// ============================================================================
// Denoise (Non-Local Means)
// ============================================================================

/// Apply denoise filter - u8 version.
///
/// Uses Non-Local Means algorithm matching OpenCV's fastNlMeansDenoising.
/// Compares patches of pixels rather than individual pixels for better
/// edge preservation.
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels)
/// * `strength` - Denoising strength (0.0-1.0)
///
/// # Returns
/// Denoised image with same channel count
pub fn denoise_u8(input: ArrayView3<u8>, strength: f32) -> Array3<u8> {
    let (height, width, channels) = input.dim();
    let mut output = Array3::<u8>::zeros((height, width, channels));

    // NL-Means parameters (matching OpenCV defaults)
    // templateWindowSize = 7 (half = 3)
    // searchWindowSize = 21 (half = 10)
    // h = strength * 20 (filter strength)
    let template_half = 3usize; // 7x7 template
    let search_half = 10usize;  // 21x21 search window
    let h = (strength * 20.0).max(1.0); // Filter strength
    let h_sq = h * h;

    let color_channels = if channels == 4 { 3 } else { channels };
    let has_alpha = channels == 4;

    // Helper to get pixel value with boundary clamping
    let get_pixel = |y: isize, x: isize, c: usize| -> f32 {
        let cy = y.clamp(0, height as isize - 1) as usize;
        let cx = x.clamp(0, width as isize - 1) as usize;
        input[[cy, cx, c]] as f32
    };

    for y in 0..height {
        for x in 0..width {
            // For transparent pixels in RGBA, just copy
            if has_alpha && input[[y, x, 3]] < 1 {
                for c in 0..channels {
                    output[[y, x, c]] = input[[y, x, c]];
                }
                continue;
            }

            let mut sum_color = vec![0.0f32; color_channels];
            let mut weight_sum = 0.0f32;

            // Search window: look for similar patches
            let search_y_min = (y as isize - search_half as isize).max(0) as usize;
            let search_y_max = (y + search_half).min(height - 1);
            let search_x_min = (x as isize - search_half as isize).max(0) as usize;
            let search_x_max = (x + search_half).min(width - 1);

            for sy in search_y_min..=search_y_max {
                for sx in search_x_min..=search_x_max {
                    // Skip transparent pixels in search
                    if has_alpha && input[[sy, sx, 3]] < 1 {
                        continue;
                    }

                    // Compute patch similarity (SSD between template patches)
                    let mut ssd = 0.0f32;
                    let mut patch_pixels = 0;

                    for ty in -(template_half as isize)..=(template_half as isize) {
                        for tx in -(template_half as isize)..=(template_half as isize) {
                            let py1 = y as isize + ty;
                            let px1 = x as isize + tx;
                            let py2 = sy as isize + ty;
                            let px2 = sx as isize + tx;

                            // Sum squared differences for all color channels
                            for c in 0..color_channels {
                                let v1 = get_pixel(py1, px1, c);
                                let v2 = get_pixel(py2, px2, c);
                                ssd += (v1 - v2).powi(2);
                            }
                            patch_pixels += 1;
                        }
                    }

                    // Normalize SSD by patch size and channels
                    let normalized_ssd = ssd / (patch_pixels * color_channels) as f32;

                    // Weight: exp(-SSD / h²)
                    let weight = (-normalized_ssd / h_sq).exp();

                    // Accumulate weighted pixel values
                    for c in 0..color_channels {
                        sum_color[c] += input[[sy, sx, c]] as f32 * weight;
                    }
                    weight_sum += weight;
                }
            }

            // Normalize and write output
            if weight_sum > 0.0 {
                for c in 0..color_channels {
                    output[[y, x, c]] = (sum_color[c] / weight_sum).clamp(0.0, 255.0).round() as u8;
                }
            } else {
                for c in 0..color_channels {
                    output[[y, x, c]] = input[[y, x, c]];
                }
            }

            // Preserve alpha
            if has_alpha {
                output[[y, x, 3]] = input[[y, x, 3]];
            }
        }
    }

    output
}

/// Apply denoise filter - f32 version.
///
/// Uses Non-Local Means algorithm matching OpenCV's fastNlMeansDenoising.
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels), values 0.0-1.0
/// * `strength` - Denoising strength (0.0-1.0)
///
/// # Returns
/// Denoised image with same channel count
pub fn denoise_f32(input: ArrayView3<f32>, strength: f32) -> Array3<f32> {
    let (height, width, channels) = input.dim();
    let mut output = Array3::<f32>::zeros((height, width, channels));

    // NL-Means parameters (matching u8 version, scaled for 0-1 range)
    let template_half = 3usize;
    let search_half = 10usize;
    // h is scaled for 0-1 range: (strength * 20) / 255 ≈ strength * 0.078
    let h = (strength * 0.08).max(0.004);
    let h_sq = h * h;

    let color_channels = if channels == 4 { 3 } else { channels };
    let has_alpha = channels == 4;

    // Helper to get pixel value with boundary clamping
    let get_pixel = |y: isize, x: isize, c: usize| -> f32 {
        let cy = y.clamp(0, height as isize - 1) as usize;
        let cx = x.clamp(0, width as isize - 1) as usize;
        input[[cy, cx, c]]
    };

    for y in 0..height {
        for x in 0..width {
            // For transparent pixels in RGBA, just copy
            if has_alpha && input[[y, x, 3]] < 0.001 {
                for c in 0..channels {
                    output[[y, x, c]] = input[[y, x, c]];
                }
                continue;
            }

            let mut sum_color = vec![0.0f32; color_channels];
            let mut weight_sum = 0.0f32;

            // Search window
            let search_y_min = (y as isize - search_half as isize).max(0) as usize;
            let search_y_max = (y + search_half).min(height - 1);
            let search_x_min = (x as isize - search_half as isize).max(0) as usize;
            let search_x_max = (x + search_half).min(width - 1);

            for sy in search_y_min..=search_y_max {
                for sx in search_x_min..=search_x_max {
                    if has_alpha && input[[sy, sx, 3]] < 0.001 {
                        continue;
                    }

                    // Compute patch similarity (SSD)
                    let mut ssd = 0.0f32;
                    let mut patch_pixels = 0;

                    for ty in -(template_half as isize)..=(template_half as isize) {
                        for tx in -(template_half as isize)..=(template_half as isize) {
                            let py1 = y as isize + ty;
                            let px1 = x as isize + tx;
                            let py2 = sy as isize + ty;
                            let px2 = sx as isize + tx;

                            for c in 0..color_channels {
                                let v1 = get_pixel(py1, px1, c);
                                let v2 = get_pixel(py2, px2, c);
                                ssd += (v1 - v2).powi(2);
                            }
                            patch_pixels += 1;
                        }
                    }

                    let normalized_ssd = ssd / (patch_pixels * color_channels) as f32;
                    let weight = (-normalized_ssd / h_sq).exp();

                    for c in 0..color_channels {
                        sum_color[c] += input[[sy, sx, c]] * weight;
                    }
                    weight_sum += weight;
                }
            }

            if weight_sum > 0.0 {
                for c in 0..color_channels {
                    output[[y, x, c]] = (sum_color[c] / weight_sum).clamp(0.0, 1.0);
                }
            } else {
                for c in 0..color_channels {
                    output[[y, x, c]] = input[[y, x, c]];
                }
            }

            if has_alpha {
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
    fn test_add_noise_u8_deterministic() {
        let mut img = Array3::<u8>::zeros((3, 3, 4));
        for y in 0..3 {
            for x in 0..3 {
                img[[y, x, 0]] = 128;
                img[[y, x, 1]] = 128;
                img[[y, x, 2]] = 128;
                img[[y, x, 3]] = 255;
            }
        }

        let result1 = add_noise_u8(img.view(), 0.1, false, true, 12345);
        let result2 = add_noise_u8(img.view(), 0.1, false, true, 12345);

        // Same seed should produce same result
        assert_eq!(result1[[1, 1, 0]], result2[[1, 1, 0]]);
    }

    #[test]
    fn test_add_noise_f32_gaussian() {
        let mut img = Array3::<f32>::zeros((5, 5, 4));
        for y in 0..5 {
            for x in 0..5 {
                img[[y, x, 0]] = 0.5;
                img[[y, x, 3]] = 1.0;
            }
        }

        let result = add_noise_f32(img.view(), 0.1, true, false, 42);

        // Noise should change some values
        let has_change = (0..5).any(|y| (0..5).any(|x| (result[[y, x, 0]] - 0.5).abs() > 0.001));
        assert!(has_change);
    }

    #[test]
    fn test_median_u8_removes_salt_pepper() {
        let mut img = Array3::<u8>::zeros((5, 5, 4));
        for y in 0..5 {
            for x in 0..5 {
                img[[y, x, 0]] = 128;
                img[[y, x, 3]] = 255;
            }
        }
        // Add salt
        img[[2, 2, 0]] = 255;

        let result = median_u8(img.view(), 1);

        // Salt should be removed
        assert!(result[[2, 2, 0]] < 200);
    }

    #[test]
    fn test_median_f32_preserves_edge() {
        let mut img = Array3::<f32>::zeros((5, 5, 4));
        for y in 0..5 {
            for x in 0..5 {
                img[[y, x, 0]] = if x < 2 { 0.0 } else { 1.0 };
                img[[y, x, 3]] = 1.0;
            }
        }

        let result = median_f32(img.view(), 1);

        // Edge should still be present
        assert!(result[[2, 0, 0]] < 0.5);
        assert!(result[[2, 4, 0]] > 0.5);
    }

    #[test]
    fn test_denoise_u8_smooth_region() {
        let mut img = Array3::<u8>::zeros((5, 5, 4));
        for y in 0..5 {
            for x in 0..5 {
                img[[y, x, 0]] = 128;
                img[[y, x, 1]] = 128;
                img[[y, x, 2]] = 128;
                img[[y, x, 3]] = 255;
            }
        }
        // Add slight noise manually
        img[[2, 2, 0]] = 135;

        let result = denoise_u8(img.view(), 0.5);

        // Should smooth toward neighbors
        assert!((result[[2, 2, 0]] as i32 - 128).abs() <= 7);
    }

    #[test]
    fn test_denoise_f32_preserves_alpha() {
        let mut img = Array3::<f32>::zeros((3, 3, 4));
        for y in 0..3 {
            for x in 0..3 {
                img[[y, x, 0]] = 0.5;
                img[[y, x, 1]] = 0.5;
                img[[y, x, 2]] = 0.5;
                img[[y, x, 3]] = 0.7;
            }
        }

        let result = denoise_f32(img.view(), 0.5);

        assert!((result[[1, 1, 3]] - 0.7).abs() < 0.001);
    }
}
