//! Morphology filters: Dilate, Erode.
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
    let color_channels = if channels == 4 { 3 } else { channels };

    // Pass 1: Horizontal dilation
    let mut temp_flat = vec![0u8; height * width * channels];
    temp_flat
        .par_chunks_mut(width * channels)
        .enumerate()
        .for_each(|(y, row)| {
            for x in 0..width {
                for c in 0..color_channels {
                    let mut max_val = 0u8;
                    let x_start = (x as isize - r).max(0) as usize;
                    let x_end = (x as isize + r + 1).min(width as isize) as usize;

                    for sx in x_start..x_end {
                        max_val = max_val.max(input[[y, sx, c]]);
                    }
                    row[x * channels + c] = max_val;
                }
                if channels == 4 {
                    row[x * channels + 3] = input[[y, x, 3]];
                }
            }
        });

    let temp = Array3::from_shape_vec((height, width, channels), temp_flat)
        .expect("Shape mismatch in dilate_u8 temp");

    // Pass 2: Vertical dilation
    let mut output_flat = vec![0u8; height * width * channels];
    output_flat
        .par_chunks_mut(width * channels)
        .enumerate()
        .for_each(|(y, row)| {
            let y_start = (y as isize - r).max(0) as usize;
            let y_end = (y as isize + r + 1).min(height as isize) as usize;

            for x in 0..width {
                for c in 0..color_channels {
                    let mut max_val = 0u8;
                    for sy in y_start..y_end {
                        max_val = max_val.max(temp[[sy, x, c]]);
                    }
                    row[x * channels + c] = max_val;
                }
                if channels == 4 {
                    row[x * channels + 3] = temp[[y, x, 3]];
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
    let color_channels = if channels == 4 { 3 } else { channels };

    // Pass 1: Horizontal dilation
    let mut temp_flat = vec![0.0f32; height * width * channels];
    temp_flat
        .par_chunks_mut(width * channels)
        .enumerate()
        .for_each(|(y, row)| {
            for x in 0..width {
                for c in 0..color_channels {
                    let mut max_val = 0.0f32;
                    let x_start = (x as isize - r).max(0) as usize;
                    let x_end = (x as isize + r + 1).min(width as isize) as usize;

                    for sx in x_start..x_end {
                        max_val = max_val.max(input[[y, sx, c]]);
                    }
                    row[x * channels + c] = max_val;
                }
                if channels == 4 {
                    row[x * channels + 3] = input[[y, x, 3]];
                }
            }
        });

    let temp = Array3::from_shape_vec((height, width, channels), temp_flat)
        .expect("Shape mismatch in dilate_f32 temp");

    // Pass 2: Vertical dilation
    let mut output_flat = vec![0.0f32; height * width * channels];
    output_flat
        .par_chunks_mut(width * channels)
        .enumerate()
        .for_each(|(y, row)| {
            let y_start = (y as isize - r).max(0) as usize;
            let y_end = (y as isize + r + 1).min(height as isize) as usize;

            for x in 0..width {
                for c in 0..color_channels {
                    let mut max_val = 0.0f32;
                    for sy in y_start..y_end {
                        max_val = max_val.max(temp[[sy, x, c]]);
                    }
                    row[x * channels + c] = max_val;
                }
                if channels == 4 {
                    row[x * channels + 3] = temp[[y, x, 3]];
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
    let color_channels = if channels == 4 { 3 } else { channels };

    // Pass 1: Horizontal erosion
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

                for c in 0..color_channels {
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
                if channels == 4 {
                    row[x * channels + 3] = input[[y, x, 3]];
                }
            }
        });

    let temp = Array3::from_shape_vec((height, width, channels), temp_flat)
        .expect("Shape mismatch in erode_u8 temp");

    // Pass 2: Vertical erosion
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
                for c in 0..color_channels {
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
                if channels == 4 {
                    row[x * channels + 3] = temp[[y, x, 3]];
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
    let color_channels = if channels == 4 { 3 } else { channels };

    // Pass 1: Horizontal erosion
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

                for c in 0..color_channels {
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
                if channels == 4 {
                    row[x * channels + 3] = input[[y, x, 3]];
                }
            }
        });

    let temp = Array3::from_shape_vec((height, width, channels), temp_flat)
        .expect("Shape mismatch in erode_f32 temp");

    // Pass 2: Vertical erosion
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
                for c in 0..color_channels {
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
                if channels == 4 {
                    row[x * channels + 3] = temp[[y, x, 3]];
                }
            }
        });

    Array3::from_shape_vec((height, width, channels), output_flat)
        .expect("Shape mismatch in erode_f32")
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
    fn test_dilate_preserves_alpha() {
        let mut img = Array3::<u8>::zeros((3, 3, 4));
        for y in 0..3 {
            for x in 0..3 {
                img[[y, x, 0]] = 128;
                img[[y, x, 3]] = 200;
            }
        }

        let result = dilate_u8(img.view(), 1.0);

        assert_eq!(result[[1, 1, 3]], 200);
    }

    #[test]
    fn test_erode_preserves_alpha() {
        let mut img = Array3::<f32>::zeros((3, 3, 4));
        for y in 0..3 {
            for x in 0..3 {
                img[[y, x, 0]] = 0.5;
                img[[y, x, 3]] = 0.7;
            }
        }

        let result = erode_f32(img.view(), 1.0);

        assert!((result[[1, 1, 3]] - 0.7).abs() < 0.001);
    }
}
