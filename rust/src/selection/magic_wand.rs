//! Magic wand selection using flood fill algorithm.
//!
//! Selects contiguous regions of similar color based on tolerance.

use std::collections::VecDeque;

/// Magic wand selection result with metadata.
pub struct MagicWandResult {
    /// Selection mask (255 = selected, 0 = not selected)
    pub mask: Vec<u8>,
    /// Bounds of selected region
    pub bounds: Option<(usize, usize, usize, usize)>, // (x, y, width, height)
    /// Number of selected pixels
    pub pixel_count: usize,
}

/// Perform magic wand selection using flood fill.
///
/// # Arguments
/// * `image` - RGBA image data (4 bytes per pixel)
/// * `width` - Image width
/// * `height` - Image height
/// * `start_x` - Starting X coordinate
/// * `start_y` - Starting Y coordinate
/// * `tolerance` - Color tolerance (0-255)
/// * `contiguous` - If true, only selects connected pixels; if false, selects all matching pixels
/// * `sample_merged` - If true, sample from merged image; otherwise sample from single layer
///
/// # Returns
/// Selection mask as Vec<u8>
pub fn magic_wand_select(
    image: &[u8],
    width: usize,
    height: usize,
    start_x: usize,
    start_y: usize,
    tolerance: u8,
    contiguous: bool,
) -> Vec<u8> {
    let result = magic_wand_select_detailed(image, width, height, start_x, start_y, tolerance, contiguous);
    result.mask
}

/// Perform magic wand selection with detailed results.
pub fn magic_wand_select_detailed(
    image: &[u8],
    width: usize,
    height: usize,
    start_x: usize,
    start_y: usize,
    tolerance: u8,
    contiguous: bool,
) -> MagicWandResult {
    let mut mask = vec![0u8; width * height];

    if width == 0 || height == 0 || start_x >= width || start_y >= height {
        return MagicWandResult {
            mask,
            bounds: None,
            pixel_count: 0,
        };
    }

    // Get the reference color at start position
    let start_idx = (start_y * width + start_x) * 4;
    let ref_r = image[start_idx];
    let ref_g = image[start_idx + 1];
    let ref_b = image[start_idx + 2];
    let ref_a = image[start_idx + 3];

    let tol = tolerance as i32;
    let mut pixel_count = 0;
    let mut min_x = width;
    let mut min_y = height;
    let mut max_x = 0;
    let mut max_y = 0;

    if contiguous {
        // Flood fill approach - only select connected pixels
        let mut queue = VecDeque::new();
        let mut visited = vec![false; width * height];

        queue.push_back((start_x, start_y));
        visited[start_y * width + start_x] = true;

        while let Some((x, y)) = queue.pop_front() {
            let idx = (y * width + x) * 4;
            let r = image[idx];
            let g = image[idx + 1];
            let b = image[idx + 2];
            let a = image[idx + 3];

            if color_matches(r, g, b, a, ref_r, ref_g, ref_b, ref_a, tol) {
                mask[y * width + x] = 255;
                pixel_count += 1;
                min_x = min_x.min(x);
                min_y = min_y.min(y);
                max_x = max_x.max(x);
                max_y = max_y.max(y);

                // Add unvisited neighbors
                for (dx, dy) in &[(-1i32, 0i32), (1, 0), (0, -1), (0, 1)] {
                    let nx = x as i32 + dx;
                    let ny = y as i32 + dy;

                    if nx >= 0 && nx < width as i32 && ny >= 0 && ny < height as i32 {
                        let nx = nx as usize;
                        let ny = ny as usize;
                        let nidx = ny * width + nx;
                        if !visited[nidx] {
                            visited[nidx] = true;
                            queue.push_back((nx, ny));
                        }
                    }
                }
            }
        }
    } else {
        // Non-contiguous - select all matching pixels in the image
        for y in 0..height {
            for x in 0..width {
                let idx = (y * width + x) * 4;
                let r = image[idx];
                let g = image[idx + 1];
                let b = image[idx + 2];
                let a = image[idx + 3];

                if color_matches(r, g, b, a, ref_r, ref_g, ref_b, ref_a, tol) {
                    mask[y * width + x] = 255;
                    pixel_count += 1;
                    min_x = min_x.min(x);
                    min_y = min_y.min(y);
                    max_x = max_x.max(x);
                    max_y = max_y.max(y);
                }
            }
        }
    }

    let bounds = if pixel_count > 0 {
        Some((min_x, min_y, max_x - min_x + 1, max_y - min_y + 1))
    } else {
        None
    };

    MagicWandResult {
        mask,
        bounds,
        pixel_count,
    }
}

/// Check if a color matches the reference color within tolerance.
#[inline]
fn color_matches(
    r: u8, g: u8, b: u8, a: u8,
    ref_r: u8, ref_g: u8, ref_b: u8, ref_a: u8,
    tolerance: i32,
) -> bool {
    // Calculate color difference using maximum channel difference
    let dr = (r as i32 - ref_r as i32).abs();
    let dg = (g as i32 - ref_g as i32).abs();
    let db = (b as i32 - ref_b as i32).abs();
    let da = (a as i32 - ref_a as i32).abs();

    // All channels must be within tolerance
    dr <= tolerance && dg <= tolerance && db <= tolerance && da <= tolerance
}

/// Color distance calculation for advanced tolerance modes.
#[allow(dead_code)]
fn color_distance_euclidean(
    r: u8, g: u8, b: u8, a: u8,
    ref_r: u8, ref_g: u8, ref_b: u8, ref_a: u8,
) -> f32 {
    let dr = r as f32 - ref_r as f32;
    let dg = g as f32 - ref_g as f32;
    let db = b as f32 - ref_b as f32;
    let da = a as f32 - ref_a as f32;

    (dr * dr + dg * dg + db * db + da * da).sqrt()
}

/// Calculate color distance in Lab color space for perceptual matching.
#[allow(dead_code)]
fn color_distance_lab(
    r: u8, g: u8, b: u8,
    ref_r: u8, ref_g: u8, ref_b: u8,
) -> f32 {
    // Convert to Lab and calculate deltaE
    // Simplified implementation using approximation
    let (l1, a1, b1) = rgb_to_lab_approx(r, g, b);
    let (l2, a2, b2) = rgb_to_lab_approx(ref_r, ref_g, ref_b);

    let dl = l1 - l2;
    let da = a1 - a2;
    let db = b1 - b2;

    (dl * dl + da * da + db * db).sqrt()
}

/// Approximate RGB to Lab conversion.
fn rgb_to_lab_approx(r: u8, g: u8, b: u8) -> (f32, f32, f32) {
    // Simplified conversion
    let r = r as f32 / 255.0;
    let g = g as f32 / 255.0;
    let b = b as f32 / 255.0;

    // sRGB to linear
    let r = if r > 0.04045 { ((r + 0.055) / 1.055).powf(2.4) } else { r / 12.92 };
    let g = if g > 0.04045 { ((g + 0.055) / 1.055).powf(2.4) } else { g / 12.92 };
    let b = if b > 0.04045 { ((b + 0.055) / 1.055).powf(2.4) } else { b / 12.92 };

    // RGB to XYZ (D65)
    let x = r * 0.4124564 + g * 0.3575761 + b * 0.1804375;
    let y = r * 0.2126729 + g * 0.7151522 + b * 0.0721750;
    let z = r * 0.0193339 + g * 0.1191920 + b * 0.9503041;

    // Normalize for D65
    let x = x / 0.95047;
    let z = z / 1.08883;

    // XYZ to Lab
    let fx = if x > 0.008856 { x.powf(1.0 / 3.0) } else { (7.787 * x) + 16.0 / 116.0 };
    let fy = if y > 0.008856 { y.powf(1.0 / 3.0) } else { (7.787 * y) + 16.0 / 116.0 };
    let fz = if z > 0.008856 { z.powf(1.0 / 3.0) } else { (7.787 * z) + 16.0 / 116.0 };

    let l = 116.0 * fy - 16.0;
    let a = 500.0 * (fx - fy);
    let b = 200.0 * (fy - fz);

    (l, a, b)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_single_color_fill() {
        // 5x5 solid red image
        let mut image = vec![0u8; 5 * 5 * 4];
        for i in 0..25 {
            image[i * 4] = 255;     // R
            image[i * 4 + 1] = 0;   // G
            image[i * 4 + 2] = 0;   // B
            image[i * 4 + 3] = 255; // A
        }

        let mask = magic_wand_select(&image, 5, 5, 2, 2, 0, true);

        // Should select all pixels
        assert!(mask.iter().all(|&v| v == 255));
    }

    #[test]
    fn test_two_regions() {
        // 4x4 image: left half red, right half blue
        let mut image = vec![0u8; 4 * 4 * 4];
        for y in 0..4 {
            for x in 0..4 {
                let idx = (y * 4 + x) * 4;
                if x < 2 {
                    // Red
                    image[idx] = 255;
                    image[idx + 1] = 0;
                    image[idx + 2] = 0;
                } else {
                    // Blue
                    image[idx] = 0;
                    image[idx + 1] = 0;
                    image[idx + 2] = 255;
                }
                image[idx + 3] = 255;
            }
        }

        // Click on red side (contiguous)
        let mask = magic_wand_select(&image, 4, 4, 0, 0, 0, true);

        // Should select only left half (8 pixels)
        let selected: usize = mask.iter().map(|&v| if v > 0 { 1 } else { 0 }).sum();
        assert_eq!(selected, 8);
    }

    #[test]
    fn test_tolerance() {
        // 3x3 image with gradient red values
        let mut image = vec![0u8; 3 * 3 * 4];
        let values = [250u8, 245, 240, 235, 230, 225, 220, 215, 210];
        for (i, &val) in values.iter().enumerate() {
            image[i * 4] = val;
            image[i * 4 + 1] = 0;
            image[i * 4 + 2] = 0;
            image[i * 4 + 3] = 255;
        }

        // Click on center (230) with tolerance 10
        let mask = magic_wand_select(&image, 3, 3, 1, 1, 10, true);

        // Should select pixels with values 220-240 (220, 225, 230, 235, 240)
        let selected: usize = mask.iter().map(|&v| if v > 0 { 1 } else { 0 }).sum();
        assert!(selected >= 5);
    }

    #[test]
    fn test_non_contiguous() {
        // 5x5 image with checkerboard pattern
        let mut image = vec![0u8; 5 * 5 * 4];
        for y in 0..5 {
            for x in 0..5 {
                let idx = (y * 5 + x) * 4;
                if (x + y) % 2 == 0 {
                    image[idx] = 255; // Red
                } else {
                    image[idx] = 0; // Black
                }
                image[idx + 1] = 0;
                image[idx + 2] = 0;
                image[idx + 3] = 255;
            }
        }

        // Non-contiguous selection of red (should get all red squares)
        let mask = magic_wand_select(&image, 5, 5, 0, 0, 0, false);

        // Should select ~13 pixels (checkerboard pattern)
        let selected: usize = mask.iter().map(|&v| if v > 0 { 1 } else { 0 }).sum();
        assert_eq!(selected, 13);
    }
}
