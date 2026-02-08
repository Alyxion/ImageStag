//! Morphology filters: Dilate, Erode, Open, Close, Gradient, TopHat, BlackHat.
//!
//! These filters apply morphological operations to images.
//! All filters support both u8 (0-255) and f32 (0.0-1.0) modes.
//!
//! ## Supported Formats
//!
//! All filters accept images with 1, 3, or 4 channels:
//! - **Grayscale**: (height, width, 1) - processes the single channel
//! - **RGB**: (height, width, 3) - processes all 3 channels
//! - **RGBA**: (height, width, 4) - processes RGB, preserves alpha
//!
//! ## Performance
//!
//! Uses separable algorithm: O(n × 2r) instead of O(n × r²).
//! Also parallelized using Rayon for multi-core speedup.
//! Produces diamond-shaped structuring element (acceptable for most uses).

use ndarray::{Array3, ArrayView3};
use rayon::prelude::*;

// ============================================================================
// Dilate
// ============================================================================

/// Apply dilation to image - u8 version.
///
/// Uses separable algorithm (horizontal + vertical passes) for O(n × 2r) complexity
/// instead of O(n × r²). Produces diamond-shaped structuring element.
/// Parallelized with Rayon for multi-core speedup.
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels)
/// * `radius` - Dilation radius
///
/// # Returns
/// Dilated image with same channel count
pub fn dilate_u8(input: ArrayView3<u8>, radius: f32) -> Array3<u8> {
    let (height, width, channels) = input.dim();
    let r = radius.ceil() as isize;

    // Pass 1: Horizontal dilation (all channels including alpha)
    let mut temp_flat = vec![0u8; height * width * channels];
    temp_flat
        .par_chunks_mut(width * channels)
        .enumerate()
        .for_each(|(y, row)| {
            for x in 0..width {
                let x_start = (x as isize - r).max(0) as usize;
                let x_end = (x as isize + r + 1).min(width as isize) as usize;

                for c in 0..channels {
                    let mut max_val = 0u8;
                    for sx in x_start..x_end {
                        max_val = max_val.max(input[[y, sx, c]]);
                    }
                    row[x * channels + c] = max_val;
                }
            }
        });

    let temp = Array3::from_shape_vec((height, width, channels), temp_flat)
        .expect("Shape mismatch in dilate_u8 temp");

    // Pass 2: Vertical dilation (all channels including alpha)
    let mut output_flat = vec![0u8; height * width * channels];
    output_flat
        .par_chunks_mut(width * channels)
        .enumerate()
        .for_each(|(y, row)| {
            let y_start = (y as isize - r).max(0) as usize;
            let y_end = (y as isize + r + 1).min(height as isize) as usize;

            for x in 0..width {
                for c in 0..channels {
                    let mut max_val = 0u8;
                    for sy in y_start..y_end {
                        max_val = max_val.max(temp[[sy, x, c]]);
                    }
                    row[x * channels + c] = max_val;
                }
            }
        });

    Array3::from_shape_vec((height, width, channels), output_flat)
        .expect("Shape mismatch in dilate_u8")
}

/// Apply dilation to image - f32 version.
///
/// Uses separable algorithm (horizontal + vertical passes) for O(n × 2r) complexity.
/// Parallelized with Rayon for multi-core speedup.
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels), values 0.0-1.0
/// * `radius` - Dilation radius
///
/// # Returns
/// Dilated image with same channel count
pub fn dilate_f32(input: ArrayView3<f32>, radius: f32) -> Array3<f32> {
    let (height, width, channels) = input.dim();
    let r = radius.ceil() as isize;

    // Pass 1: Horizontal dilation (all channels including alpha)
    let mut temp_flat = vec![0.0f32; height * width * channels];
    temp_flat
        .par_chunks_mut(width * channels)
        .enumerate()
        .for_each(|(y, row)| {
            for x in 0..width {
                let x_start = (x as isize - r).max(0) as usize;
                let x_end = (x as isize + r + 1).min(width as isize) as usize;

                for c in 0..channels {
                    let mut max_val = 0.0f32;
                    for sx in x_start..x_end {
                        max_val = max_val.max(input[[y, sx, c]]);
                    }
                    row[x * channels + c] = max_val;
                }
            }
        });

    let temp = Array3::from_shape_vec((height, width, channels), temp_flat)
        .expect("Shape mismatch in dilate_f32 temp");

    // Pass 2: Vertical dilation (all channels including alpha)
    let mut output_flat = vec![0.0f32; height * width * channels];
    output_flat
        .par_chunks_mut(width * channels)
        .enumerate()
        .for_each(|(y, row)| {
            let y_start = (y as isize - r).max(0) as usize;
            let y_end = (y as isize + r + 1).min(height as isize) as usize;

            for x in 0..width {
                for c in 0..channels {
                    let mut max_val = 0.0f32;
                    for sy in y_start..y_end {
                        max_val = max_val.max(temp[[sy, x, c]]);
                    }
                    row[x * channels + c] = max_val;
                }
            }
        });

    Array3::from_shape_vec((height, width, channels), output_flat)
        .expect("Shape mismatch in dilate_f32")
}

// ============================================================================
// Erode
// ============================================================================

/// Apply erosion to image - u8 version.
///
/// Uses separable algorithm (horizontal + vertical passes) for O(n × 2r) complexity
/// instead of O(n × r²). Produces diamond-shaped structuring element.
/// Parallelized with Rayon for multi-core speedup.
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels)
/// * `radius` - Erosion radius
///
/// # Returns
/// Eroded image with same channel count
pub fn erode_u8(input: ArrayView3<u8>, radius: f32) -> Array3<u8> {
    let (height, width, channels) = input.dim();
    let r = radius.ceil() as isize;

    // Pass 1: Horizontal erosion (all channels including alpha)
    let mut temp_flat = vec![255u8; height * width * channels];
    temp_flat
        .par_chunks_mut(width * channels)
        .enumerate()
        .for_each(|(y, row)| {
            for x in 0..width {
                // Check if we're near horizontal boundary
                let x_start = x as isize - r;
                let x_end = x as isize + r + 1;
                let hit_boundary = x_start < 0 || x_end > width as isize;

                for c in 0..channels {
                    if hit_boundary {
                        row[x * channels + c] = 0;
                    } else {
                        let mut min_val = 255u8;
                        for sx in x_start as usize..x_end as usize {
                            min_val = min_val.min(input[[y, sx, c]]);
                        }
                        row[x * channels + c] = min_val;
                    }
                }
            }
        });

    let temp = Array3::from_shape_vec((height, width, channels), temp_flat)
        .expect("Shape mismatch in erode_u8 temp");

    // Pass 2: Vertical erosion (all channels including alpha)
    let mut output_flat = vec![255u8; height * width * channels];
    output_flat
        .par_chunks_mut(width * channels)
        .enumerate()
        .for_each(|(y, row)| {
            // Check if we're near vertical boundary
            let y_start = y as isize - r;
            let y_end = y as isize + r + 1;
            let hit_boundary = y_start < 0 || y_end > height as isize;

            for x in 0..width {
                for c in 0..channels {
                    if hit_boundary || temp[[y, x, c]] == 0 {
                        // If horizontal pass already set to 0 or we're at vertical boundary
                        row[x * channels + c] = 0;
                    } else {
                        let mut min_val = 255u8;
                        for sy in y_start as usize..y_end as usize {
                            min_val = min_val.min(temp[[sy, x, c]]);
                        }
                        row[x * channels + c] = min_val;
                    }
                }
            }
        });

    Array3::from_shape_vec((height, width, channels), output_flat)
        .expect("Shape mismatch in erode_u8")
}

/// Apply erosion to image - f32 version.
///
/// Uses separable algorithm (horizontal + vertical passes) for O(n × 2r) complexity
/// instead of O(n × r²). Produces diamond-shaped structuring element.
/// Parallelized with Rayon for multi-core speedup.
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels), values 0.0-1.0
/// * `radius` - Erosion radius
///
/// # Returns
/// Eroded image with same channel count
pub fn erode_f32(input: ArrayView3<f32>, radius: f32) -> Array3<f32> {
    let (height, width, channels) = input.dim();
    let r = radius.ceil() as isize;

    // Pass 1: Horizontal erosion (all channels including alpha)
    let mut temp_flat = vec![1.0f32; height * width * channels];
    temp_flat
        .par_chunks_mut(width * channels)
        .enumerate()
        .for_each(|(y, row)| {
            for x in 0..width {
                // Check if we're near horizontal boundary
                let x_start = x as isize - r;
                let x_end = x as isize + r + 1;
                let hit_boundary = x_start < 0 || x_end > width as isize;

                for c in 0..channels {
                    if hit_boundary {
                        row[x * channels + c] = 0.0;
                    } else {
                        let mut min_val = 1.0f32;
                        for sx in x_start as usize..x_end as usize {
                            min_val = min_val.min(input[[y, sx, c]]);
                        }
                        row[x * channels + c] = min_val;
                    }
                }
            }
        });

    let temp = Array3::from_shape_vec((height, width, channels), temp_flat)
        .expect("Shape mismatch in erode_f32 temp");

    // Pass 2: Vertical erosion (all channels including alpha)
    let mut output_flat = vec![1.0f32; height * width * channels];
    output_flat
        .par_chunks_mut(width * channels)
        .enumerate()
        .for_each(|(y, row)| {
            // Check if we're near vertical boundary
            let y_start = y as isize - r;
            let y_end = y as isize + r + 1;
            let hit_boundary = y_start < 0 || y_end > height as isize;

            for x in 0..width {
                for c in 0..channels {
                    if hit_boundary || temp[[y, x, c]] == 0.0 {
                        // If horizontal pass already set to 0 or we're at vertical boundary
                        row[x * channels + c] = 0.0;
                    } else {
                        let mut min_val = 1.0f32;
                        for sy in y_start as usize..y_end as usize {
                            min_val = min_val.min(temp[[sy, x, c]]);
                        }
                        row[x * channels + c] = min_val;
                    }
                }
            }
        });

    Array3::from_shape_vec((height, width, channels), output_flat)
        .expect("Shape mismatch in erode_f32")
}

// ============================================================================
// Compound Operations
// ============================================================================

/// Morphological opening (erode then dilate) - u8 version.
///
/// Removes small bright spots (noise) while preserving larger bright regions.
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels
/// * `radius` - Structuring element radius
pub fn open_u8(input: ArrayView3<u8>, radius: f32) -> Array3<u8> {
    let eroded = erode_u8(input, radius);
    dilate_u8(eroded.view(), radius)
}

/// Morphological opening (erode then dilate) - f32 version.
pub fn open_f32(input: ArrayView3<f32>, radius: f32) -> Array3<f32> {
    let eroded = erode_f32(input, radius);
    dilate_f32(eroded.view(), radius)
}

/// Morphological closing (dilate then erode) - u8 version.
///
/// Fills small dark holes while preserving larger dark regions.
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels
/// * `radius` - Structuring element radius
pub fn close_u8(input: ArrayView3<u8>, radius: f32) -> Array3<u8> {
    let dilated = dilate_u8(input, radius);
    erode_u8(dilated.view(), radius)
}

/// Morphological closing (dilate then erode) - f32 version.
pub fn close_f32(input: ArrayView3<f32>, radius: f32) -> Array3<f32> {
    let dilated = dilate_f32(input, radius);
    erode_f32(dilated.view(), radius)
}

/// Morphological gradient (dilate - erode) - u8 version.
///
/// Extracts edges by computing the difference between dilation and erosion.
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels
/// * `radius` - Structuring element radius
pub fn gradient_u8(input: ArrayView3<u8>, radius: f32) -> Array3<u8> {
    let (height, width, channels) = input.dim();
    let dilated = dilate_u8(input, radius);
    let eroded = erode_u8(input, radius);
    let mut output = Array3::<u8>::zeros((height, width, channels));

    for y in 0..height {
        for x in 0..width {
            for c in 0..channels {
                output[[y, x, c]] = dilated[[y, x, c]].saturating_sub(eroded[[y, x, c]]);
            }
        }
    }
    output
}

/// Morphological gradient (dilate - erode) - f32 version.
pub fn gradient_f32(input: ArrayView3<f32>, radius: f32) -> Array3<f32> {
    let (height, width, channels) = input.dim();
    let dilated = dilate_f32(input, radius);
    let eroded = erode_f32(input, radius);
    let mut output = Array3::<f32>::zeros((height, width, channels));

    for y in 0..height {
        for x in 0..width {
            for c in 0..channels {
                output[[y, x, c]] = (dilated[[y, x, c]] - eroded[[y, x, c]]).max(0.0);
            }
        }
    }
    output
}

/// Top hat (original - open) - u8 version.
///
/// Extracts bright features smaller than the structuring element.
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels
/// * `radius` - Structuring element radius
pub fn tophat_u8(input: ArrayView3<u8>, radius: f32) -> Array3<u8> {
    let (height, width, channels) = input.dim();
    let opened = open_u8(input, radius);
    let mut output = Array3::<u8>::zeros((height, width, channels));

    for y in 0..height {
        for x in 0..width {
            for c in 0..channels {
                output[[y, x, c]] = input[[y, x, c]].saturating_sub(opened[[y, x, c]]);
            }
        }
    }
    output
}

/// Top hat (original - open) - f32 version.
pub fn tophat_f32(input: ArrayView3<f32>, radius: f32) -> Array3<f32> {
    let (height, width, channels) = input.dim();
    let opened = open_f32(input, radius);
    let mut output = Array3::<f32>::zeros((height, width, channels));

    for y in 0..height {
        for x in 0..width {
            for c in 0..channels {
                output[[y, x, c]] = (input[[y, x, c]] - opened[[y, x, c]]).max(0.0);
            }
        }
    }
    output
}

/// Black hat (close - original) - u8 version.
///
/// Extracts dark features smaller than the structuring element.
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels
/// * `radius` - Structuring element radius
pub fn blackhat_u8(input: ArrayView3<u8>, radius: f32) -> Array3<u8> {
    let (height, width, channels) = input.dim();
    let closed = close_u8(input, radius);
    let mut output = Array3::<u8>::zeros((height, width, channels));

    for y in 0..height {
        for x in 0..width {
            for c in 0..channels {
                output[[y, x, c]] = closed[[y, x, c]].saturating_sub(input[[y, x, c]]);
            }
        }
    }
    output
}

/// Black hat (close - original) - f32 version.
pub fn blackhat_f32(input: ArrayView3<f32>, radius: f32) -> Array3<f32> {
    let (height, width, channels) = input.dim();
    let closed = close_f32(input, radius);
    let mut output = Array3::<f32>::zeros((height, width, channels));

    for y in 0..height {
        for x in 0..width {
            for c in 0..channels {
                output[[y, x, c]] = (closed[[y, x, c]] - input[[y, x, c]]).max(0.0);
            }
        }
    }
    output
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_dilate_u8_grows_bright() {
        let mut img = Array3::<u8>::zeros((5, 5, 4));
        // Single bright pixel in center
        img[[2, 2, 0]] = 255;
        img[[2, 2, 3]] = 255;
        for y in 0..5 {
            for x in 0..5 {
                if y != 2 || x != 2 {
                    img[[y, x, 3]] = 255;
                }
            }
        }

        let result = dilate_u8(img.view(), 1.0);

        // Bright should have spread to neighbors
        assert!(result[[2, 1, 0]] > 0);
        assert!(result[[2, 3, 0]] > 0);
        assert!(result[[1, 2, 0]] > 0);
        assert!(result[[3, 2, 0]] > 0);
    }

    #[test]
    fn test_dilate_f32_max_propagates() {
        let mut img = Array3::<f32>::zeros((3, 3, 4));
        img[[1, 1, 0]] = 0.8;
        for y in 0..3 {
            for x in 0..3 {
                img[[y, x, 3]] = 1.0;
            }
        }

        let result = dilate_f32(img.view(), 1.0);

        // All neighbors should be 0.8
        assert!(result[[0, 1, 0]] >= 0.8);
        assert!(result[[2, 1, 0]] >= 0.8);
    }

    #[test]
    fn test_erode_u8_shrinks_bright() {
        let mut img = Array3::<u8>::zeros((5, 5, 4));
        // Fill with white, black center
        for y in 0..5 {
            for x in 0..5 {
                img[[y, x, 0]] = 255;
                img[[y, x, 3]] = 255;
            }
        }
        img[[2, 2, 0]] = 0;

        let result = erode_u8(img.view(), 1.0);

        // Black should have spread to neighbors
        assert!(result[[2, 1, 0]] < 255);
        assert!(result[[2, 3, 0]] < 255);
    }

    #[test]
    fn test_erode_f32_min_propagates() {
        let mut img = Array3::<f32>::zeros((3, 3, 4));
        // Fill with 1.0, center is 0.2
        for y in 0..3 {
            for x in 0..3 {
                img[[y, x, 0]] = 1.0;
                img[[y, x, 3]] = 1.0;
            }
        }
        img[[1, 1, 0]] = 0.2;

        let result = erode_f32(img.view(), 1.0);

        // All neighbors should be 0.2
        assert!(result[[0, 1, 0]] <= 0.2);
        assert!(result[[2, 1, 0]] <= 0.2);
    }

    #[test]
    fn test_dilate_processes_alpha() {
        let mut img = Array3::<u8>::zeros((3, 3, 4));
        // Center pixel has alpha=200, rest have alpha=100
        for y in 0..3 {
            for x in 0..3 {
                img[[y, x, 0]] = 128;
                img[[y, x, 3]] = 100;
            }
        }
        img[[1, 1, 3]] = 200;

        let result = dilate_u8(img.view(), 1.0);

        // Dilate should spread the higher alpha to neighbors
        assert_eq!(result[[0, 1, 3]], 200);
        assert_eq!(result[[1, 0, 3]], 200);
    }

    #[test]
    fn test_erode_processes_alpha() {
        let mut img = Array3::<f32>::zeros((3, 3, 4));
        // All pixels have alpha=0.7, center has alpha=0.2
        for y in 0..3 {
            for x in 0..3 {
                img[[y, x, 0]] = 0.5;
                img[[y, x, 3]] = 0.7;
            }
        }
        img[[1, 1, 3]] = 0.2;

        let result = erode_f32(img.view(), 1.0);

        // Erode should spread the lower alpha to neighbors
        assert!(result[[0, 1, 3]] <= 0.2);
    }

    // Compound ops tests

    #[test]
    fn test_open_removes_small_bright() {
        let mut img = Array3::<u8>::zeros((7, 7, 3));
        // Fill background
        for y in 0..7 {
            for x in 0..7 {
                img[[y, x, 0]] = 50;
            }
        }
        // Add single bright pixel (noise)
        img[[3, 3, 0]] = 255;

        let result = open_u8(img.view(), 1.0);

        // Single bright pixel should be removed by opening
        assert!(result[[3, 3, 0]] < 255);
    }

    #[test]
    fn test_close_fills_small_dark() {
        let mut img = Array3::<u8>::zeros((7, 7, 3));
        // Fill with white
        for y in 0..7 {
            for x in 0..7 {
                img[[y, x, 0]] = 200;
            }
        }
        // Add single dark pixel (hole)
        img[[3, 3, 0]] = 0;

        let result = close_u8(img.view(), 1.0);

        // Single dark pixel should be filled by closing
        assert!(result[[3, 3, 0]] > 0);
    }

    #[test]
    fn test_gradient_detects_edges() {
        let mut img = Array3::<u8>::zeros((5, 5, 3));
        // Left half dark, right half bright
        for y in 0..5 {
            for x in 0..5 {
                img[[y, x, 0]] = if x < 2 { 0 } else { 255 };
            }
        }

        let result = gradient_u8(img.view(), 1.0);

        // Edge should be bright
        assert!(result[[2, 2, 0]] > 0);
    }

    #[test]
    fn test_tophat_f32() {
        let mut img = Array3::<f32>::zeros((7, 7, 1));
        // Small bright spot
        img[[3, 3, 0]] = 1.0;

        let result = tophat_f32(img.view(), 2.0);

        // Should extract the bright spot
        assert!(result[[3, 3, 0]] > 0.0);
    }

    #[test]
    fn test_blackhat_f32() {
        let mut img = Array3::<f32>::zeros((7, 7, 1));
        for y in 0..7 {
            for x in 0..7 {
                img[[y, x, 0]] = 1.0;
            }
        }
        // Small dark spot
        img[[3, 3, 0]] = 0.0;

        let result = blackhat_f32(img.view(), 2.0);

        // Should extract the dark spot
        assert!(result[[3, 3, 0]] > 0.0);
    }
}
