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

use ndarray::{Array3, ArrayView3};

// ============================================================================
// Dilate
// ============================================================================

/// Apply dilation to image - u8 version.
///
/// Dilate takes the maximum value in the neighborhood,
/// making bright regions grow and dark regions shrink.
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels)
/// * `radius` - Dilation radius (uses circular structuring element)
///
/// # Returns
/// Dilated image with same channel count
pub fn dilate_u8(input: ArrayView3<u8>, radius: f32) -> Array3<u8> {
    let (height, width, channels) = input.dim();
    let mut output = Array3::<u8>::zeros((height, width, channels));

    let r_ceil = radius.ceil() as isize;
    let r_sq = radius * radius;

    let color_channels = if channels == 4 { 3 } else { channels };

    for y in 0..height {
        for x in 0..width {
            for c in 0..color_channels {
                let mut max_val = 0u8;

                for dy in -r_ceil..=r_ceil {
                    let sy = y as isize + dy;
                    if sy < 0 || sy >= height as isize {
                        continue;
                    }

                    for dx in -r_ceil..=r_ceil {
                        let sx = x as isize + dx;
                        if sx < 0 || sx >= width as isize {
                            continue;
                        }

                        let dist_sq = (dx * dx + dy * dy) as f32;
                        if dist_sq <= r_sq {
                            max_val = max_val.max(input[[sy as usize, sx as usize, c]]);
                        }
                    }
                }

                output[[y, x, c]] = max_val;
            }
            if channels == 4 {
                output[[y, x, 3]] = input[[y, x, 3]]; // Preserve alpha
            }
        }
    }

    output
}

/// Apply dilation to image - f32 version.
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels), values 0.0-1.0
/// * `radius` - Dilation radius (uses circular structuring element)
///
/// # Returns
/// Dilated image with same channel count
pub fn dilate_f32(input: ArrayView3<f32>, radius: f32) -> Array3<f32> {
    let (height, width, channels) = input.dim();
    let mut output = Array3::<f32>::zeros((height, width, channels));

    let r_ceil = radius.ceil() as isize;
    let r_sq = radius * radius;

    let color_channels = if channels == 4 { 3 } else { channels };

    for y in 0..height {
        for x in 0..width {
            for c in 0..color_channels {
                let mut max_val = 0.0f32;

                for dy in -r_ceil..=r_ceil {
                    let sy = y as isize + dy;
                    if sy < 0 || sy >= height as isize {
                        continue;
                    }

                    for dx in -r_ceil..=r_ceil {
                        let sx = x as isize + dx;
                        if sx < 0 || sx >= width as isize {
                            continue;
                        }

                        let dist_sq = (dx * dx + dy * dy) as f32;
                        if dist_sq <= r_sq {
                            max_val = max_val.max(input[[sy as usize, sx as usize, c]]);
                        }
                    }
                }

                output[[y, x, c]] = max_val;
            }
            if channels == 4 {
                output[[y, x, 3]] = input[[y, x, 3]];
            }
        }
    }

    output
}

// ============================================================================
// Erode
// ============================================================================

/// Apply erosion to image - u8 version.
///
/// Erode takes the minimum value in the neighborhood,
/// making dark regions grow and bright regions shrink.
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels)
/// * `radius` - Erosion radius (uses circular structuring element)
///
/// # Returns
/// Eroded image with same channel count
pub fn erode_u8(input: ArrayView3<u8>, radius: f32) -> Array3<u8> {
    let (height, width, channels) = input.dim();
    let mut output = Array3::<u8>::zeros((height, width, channels));

    let r_ceil = radius.ceil() as isize;
    let r_sq = radius * radius;

    let color_channels = if channels == 4 { 3 } else { channels };

    for y in 0..height {
        for x in 0..width {
            for c in 0..color_channels {
                let mut min_val = 255u8;

                for dy in -r_ceil..=r_ceil {
                    let sy = y as isize + dy;
                    if sy < 0 || sy >= height as isize {
                        min_val = 0; // Treat out-of-bounds as black
                        continue;
                    }

                    for dx in -r_ceil..=r_ceil {
                        let sx = x as isize + dx;
                        if sx < 0 || sx >= width as isize {
                            min_val = 0;
                            continue;
                        }

                        let dist_sq = (dx * dx + dy * dy) as f32;
                        if dist_sq <= r_sq {
                            min_val = min_val.min(input[[sy as usize, sx as usize, c]]);
                        }
                    }
                }

                output[[y, x, c]] = min_val;
            }
            if channels == 4 {
                output[[y, x, 3]] = input[[y, x, 3]];
            }
        }
    }

    output
}

/// Apply erosion to image - f32 version.
///
/// # Arguments
/// * `input` - Image with 1, 3, or 4 channels (height, width, channels), values 0.0-1.0
/// * `radius` - Erosion radius (uses circular structuring element)
///
/// # Returns
/// Eroded image with same channel count
pub fn erode_f32(input: ArrayView3<f32>, radius: f32) -> Array3<f32> {
    let (height, width, channels) = input.dim();
    let mut output = Array3::<f32>::zeros((height, width, channels));

    let r_ceil = radius.ceil() as isize;
    let r_sq = radius * radius;

    let color_channels = if channels == 4 { 3 } else { channels };

    for y in 0..height {
        for x in 0..width {
            for c in 0..color_channels {
                let mut min_val = 1.0f32;

                for dy in -r_ceil..=r_ceil {
                    let sy = y as isize + dy;
                    if sy < 0 || sy >= height as isize {
                        min_val = 0.0;
                        continue;
                    }

                    for dx in -r_ceil..=r_ceil {
                        let sx = x as isize + dx;
                        if sx < 0 || sx >= width as isize {
                            min_val = 0.0;
                            continue;
                        }

                        let dist_sq = (dx * dx + dy * dy) as f32;
                        if dist_sq <= r_sq {
                            min_val = min_val.min(input[[sy as usize, sx as usize, c]]);
                        }
                    }
                }

                output[[y, x, c]] = min_val;
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
