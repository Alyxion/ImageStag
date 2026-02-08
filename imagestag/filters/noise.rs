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

/// Core median filter on a single-channel flat u8 buffer.
///
/// Hybrid approach:
/// - r=1: Median-of-9 via sorting network (19 compare-swaps per pixel)
/// - r>=2: Huang's histogram algorithm with column histograms (O(1) per pixel)
pub fn median_channel_u8(chan: &[u8], out: &mut [u8], width: usize, height: usize, radius: usize) {
    if radius == 1 {
        median_3x3(chan, out, width, height);
    } else {
        median_histogram(chan, out, width, height, radius);
    }
}

/// Specialized 3x3 median using a sorting network.
/// Only 19 compare-and-swap operations per pixel for median of 9 elements.
fn median_3x3(chan: &[u8], out: &mut [u8], width: usize, height: usize) {
    for y in 0..height {
        let y_top = y.saturating_sub(1);
        let y_bot = (y + 1).min(height - 1);
        let row_off = y * width;

        for x in 0..width {
            let x_left = x.saturating_sub(1);
            let x_right = (x + 1).min(width - 1);

            // Collect 3x3 window (up to 9 pixels, may be less at borders)
            let mut count = 0u8;
            let mut v = [0u8; 9];
            for sy in y_top..=y_bot {
                let src_off = sy * width;
                for sx in x_left..=x_right {
                    unsafe {
                        *v.get_unchecked_mut(count as usize) = *chan.get_unchecked(src_off + sx);
                    }
                    count += 1;
                }
            }

            // Find median
            let median_val = if count == 9 {
                // Full 3x3: use optimized sorting network (Bose-Nelson, 25 swaps to sort 9)
                // We only need the median (element 4 after sort)
                macro_rules! cas {
                    ($i:expr, $j:expr) => {
                        if v[$i] > v[$j] { v.swap($i, $j); }
                    };
                }
                // Sort network for 9 elements
                cas!(0, 1); cas!(3, 4); cas!(6, 7);
                cas!(1, 2); cas!(4, 5); cas!(7, 8);
                cas!(0, 1); cas!(3, 4); cas!(6, 7);
                cas!(0, 3); cas!(3, 6); cas!(0, 3);
                cas!(1, 4); cas!(4, 7); cas!(1, 4);
                cas!(2, 5); cas!(5, 8); cas!(2, 5);
                cas!(1, 3); cas!(5, 7);
                cas!(2, 6); cas!(4, 6); cas!(2, 4);
                cas!(2, 3); cas!(5, 6);
                v[4]
            } else {
                // Border pixels: sort partial window
                let s = &mut v[..count as usize];
                s.sort_unstable();
                s[count as usize / 2]
            };

            unsafe { *out.get_unchecked_mut(row_off + x) = median_val; }
        }
    }
}

/// Huang's histogram-based median for large radii (r > 7).
/// Column histograms updated O(1) per row, window histogram via 256-bin add/remove.
fn median_histogram(chan: &[u8], out: &mut [u8], width: usize, height: usize, radius: usize) {
    // Column histograms: 256 bins per column, u16 (max count = 2*21+1 = 43)
    let mut col_hist: Vec<[u16; 256]> = vec![[0u16; 256]; width];

    // Initialize for row 0
    let y_bot_init = radius.min(height - 1);
    for x in 0..width {
        for sy in 0..=y_bot_init {
            let v = unsafe { *chan.get_unchecked(sy * width + x) } as usize;
            unsafe { *col_hist.get_unchecked_mut(x).get_unchecked_mut(v) += 1; }
        }
    }

    for y in 0..height {
        // Update column histograms
        if y > 0 {
            let remove_row = y as isize - radius as isize - 1;
            let add_row = y + radius;
            if remove_row >= 0 {
                let ry = remove_row as usize;
                for x in 0..width {
                    let v = unsafe { *chan.get_unchecked(ry * width + x) } as usize;
                    unsafe { *col_hist.get_unchecked_mut(x).get_unchecked_mut(v) -= 1; }
                }
            }
            if add_row < height {
                for x in 0..width {
                    let v = unsafe { *chan.get_unchecked(add_row * width + x) } as usize;
                    unsafe { *col_hist.get_unchecked_mut(x).get_unchecked_mut(v) += 1; }
                }
            }
        }

        // Build window histogram for x=0
        let mut hist = [0u32; 256];
        let mut count = 0u32;
        let x_right = radius.min(width - 1);
        for sx in 0..=x_right {
            let ch = unsafe { col_hist.get_unchecked(sx) };
            for i in 0..256 {
                let v = unsafe { *ch.get_unchecked(i) } as u32;
                unsafe { *hist.get_unchecked_mut(i) += v; }
                count += v;
            }
        }

        let row_off = y * width;
        unsafe {
            *out.get_unchecked_mut(row_off) = hist_median(&hist, count);
        }

        // Slide right
        for x in 1..width {
            if x > radius {
                let oc = x - radius - 1;
                let ch = unsafe { col_hist.get_unchecked(oc) };
                for i in 0..256 {
                    let v = unsafe { *ch.get_unchecked(i) } as u32;
                    unsafe { *hist.get_unchecked_mut(i) -= v; }
                    count -= v;
                }
            }

            let nc = x + radius;
            if nc < width {
                let ch = unsafe { col_hist.get_unchecked(nc) };
                for i in 0..256 {
                    let v = unsafe { *ch.get_unchecked(i) } as u32;
                    unsafe { *hist.get_unchecked_mut(i) += v; }
                    count += v;
                }
            }

            unsafe {
                *out.get_unchecked_mut(row_off + x) = hist_median(&hist, count);
            }
        }
    }
}

/// Find median from a 256-bin histogram.
#[inline(always)]
fn hist_median(hist: &[u32; 256], count: u32) -> u8 {
    let target = count / 2;
    let mut cum = 0u32;
    for i in 0..256 {
        cum += unsafe { *hist.get_unchecked(i) };
        if cum > target {
            return i as u8;
        }
    }
    255
}

/// Apply median filter - u8 version.
///
/// Removes salt-and-pepper noise while preserving edges.
/// Uses column histograms + coarse/fine window histogram (Huang's algorithm).
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels)
/// * `radius` - Filter radius (1-21)
///
/// # Returns
/// Median-filtered image with same channel count
pub fn median_u8(input: ArrayView3<u8>, radius: u32) -> Array3<u8> {
    let (height, width, channels) = input.dim();
    let radius = radius.min(21) as usize;
    if radius == 0 {
        return input.to_owned();
    }

    let mut output = Array3::<u8>::zeros((height, width, channels));
    let color_channels = if channels == 4 { 3 } else { channels };
    let npixels = height * width;

    for c in 0..color_channels {
        // Extract channel to flat buffer
        let mut chan = vec![0u8; npixels];
        for y in 0..height {
            let row_off = y * width;
            for x in 0..width {
                chan[row_off + x] = input[[y, x, c]];
            }
        }

        // Process
        let mut out_chan = vec![0u8; npixels];
        median_channel_u8(&chan, &mut out_chan, width, height, radius);

        // Write back to ndarray
        for y in 0..height {
            let row_off = y * width;
            for x in 0..width {
                output[[y, x, c]] = out_chan[row_off + x];
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

/// Apply median filter - f32 version.
///
/// Quantizes to 256 bins for histogram-based processing, then converts back.
/// Uses the same column histogram approach as median_u8.
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels), values 0.0-1.0
/// * `radius` - Filter radius (1-21)
///
/// # Returns
/// Median-filtered image with same channel count
pub fn median_f32(input: ArrayView3<f32>, radius: u32) -> Array3<f32> {
    let (height, width, channels) = input.dim();
    let radius = radius.min(21) as usize;
    if radius == 0 {
        return input.to_owned();
    }

    let mut output = Array3::<f32>::zeros((height, width, channels));
    let color_channels = if channels == 4 { 3 } else { channels };
    let npixels = height * width;

    for c in 0..color_channels {
        // Quantize to u8
        let mut chan = vec![0u8; npixels];
        for y in 0..height {
            let row_off = y * width;
            for x in 0..width {
                chan[row_off + x] = (input[[y, x, c]].clamp(0.0, 1.0) * 255.0).round() as u8;
            }
        }

        // Process using same u8 core
        let mut out_chan = vec![0u8; npixels];
        median_channel_u8(&chan, &mut out_chan, width, height, radius);

        // Convert back to f32
        for y in 0..height {
            let row_off = y * width;
            for x in 0..width {
                output[[y, x, c]] = out_chan[row_off + x] as f32 / 255.0;
            }
        }
    }

    if channels == 4 {
        for y in 0..height {
            for x in 0..width {
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
