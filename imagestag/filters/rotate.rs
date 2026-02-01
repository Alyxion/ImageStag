//! Image rotation and mirroring functions.
//!
//! Provides exact 90-degree rotation and mirroring operations for images.
//!
//! ## Supported Formats
//!
//! All functions support 1, 3, or 4 channel images in both u8 and f32 formats:
//! - Grayscale: (H, W, 1)
//! - RGB: (H, W, 3)
//! - RGBA: (H, W, 4)
//!
//! ## Rotation Direction
//!
//! All rotations are clockwise (CW):
//! - 90° CW: (x, y) -> (H - 1 - y, x)
//! - 180°: (x, y) -> (W - 1 - x, H - 1 - y)
//! - 270° CW (90° CCW): (x, y) -> (y, W - 1 - x)

use ndarray::{Array3, ArrayView3};

/// Rotate image 90 degrees clockwise (u8).
///
/// # Arguments
/// * `image` - Input image (H, W, C) where C is 1, 3, or 4
///
/// # Returns
/// Rotated image (W, H, C) - note dimensions are swapped
pub fn rotate_90_cw_u8(image: ArrayView3<u8>) -> Array3<u8> {
    let (h, w, c) = (image.shape()[0], image.shape()[1], image.shape()[2]);
    let mut result = Array3::<u8>::zeros((w, h, c));

    for y in 0..h {
        for x in 0..w {
            // 90° CW: (x, y) -> (h - 1 - y, x) in source coords
            // Or equivalently: new_y = x, new_x = h - 1 - y
            let new_y = x;
            let new_x = h - 1 - y;
            for ch in 0..c {
                result[[new_y, new_x, ch]] = image[[y, x, ch]];
            }
        }
    }

    result
}

/// Rotate image 90 degrees clockwise (f32).
pub fn rotate_90_cw_f32(image: ArrayView3<f32>) -> Array3<f32> {
    let (h, w, c) = (image.shape()[0], image.shape()[1], image.shape()[2]);
    let mut result = Array3::<f32>::zeros((w, h, c));

    for y in 0..h {
        for x in 0..w {
            let new_y = x;
            let new_x = h - 1 - y;
            for ch in 0..c {
                result[[new_y, new_x, ch]] = image[[y, x, ch]];
            }
        }
    }

    result
}

/// Rotate image 180 degrees (u8).
///
/// # Arguments
/// * `image` - Input image (H, W, C)
///
/// # Returns
/// Rotated image (H, W, C) - same dimensions
pub fn rotate_180_u8(image: ArrayView3<u8>) -> Array3<u8> {
    let (h, w, c) = (image.shape()[0], image.shape()[1], image.shape()[2]);
    let mut result = Array3::<u8>::zeros((h, w, c));

    for y in 0..h {
        for x in 0..w {
            // 180°: (x, y) -> (w - 1 - x, h - 1 - y)
            let new_y = h - 1 - y;
            let new_x = w - 1 - x;
            for ch in 0..c {
                result[[new_y, new_x, ch]] = image[[y, x, ch]];
            }
        }
    }

    result
}

/// Rotate image 180 degrees (f32).
pub fn rotate_180_f32(image: ArrayView3<f32>) -> Array3<f32> {
    let (h, w, c) = (image.shape()[0], image.shape()[1], image.shape()[2]);
    let mut result = Array3::<f32>::zeros((h, w, c));

    for y in 0..h {
        for x in 0..w {
            let new_y = h - 1 - y;
            let new_x = w - 1 - x;
            for ch in 0..c {
                result[[new_y, new_x, ch]] = image[[y, x, ch]];
            }
        }
    }

    result
}

/// Rotate image 270 degrees clockwise (90 degrees counter-clockwise) (u8).
///
/// # Arguments
/// * `image` - Input image (H, W, C)
///
/// # Returns
/// Rotated image (W, H, C) - dimensions are swapped
pub fn rotate_270_cw_u8(image: ArrayView3<u8>) -> Array3<u8> {
    let (h, w, c) = (image.shape()[0], image.shape()[1], image.shape()[2]);
    let mut result = Array3::<u8>::zeros((w, h, c));

    for y in 0..h {
        for x in 0..w {
            // 270° CW (90° CCW): (x, y) -> (y, w - 1 - x) in source coords
            // Or: new_y = w - 1 - x, new_x = y
            let new_y = w - 1 - x;
            let new_x = y;
            for ch in 0..c {
                result[[new_y, new_x, ch]] = image[[y, x, ch]];
            }
        }
    }

    result
}

/// Rotate image 270 degrees clockwise (90 degrees counter-clockwise) (f32).
pub fn rotate_270_cw_f32(image: ArrayView3<f32>) -> Array3<f32> {
    let (h, w, c) = (image.shape()[0], image.shape()[1], image.shape()[2]);
    let mut result = Array3::<f32>::zeros((w, h, c));

    for y in 0..h {
        for x in 0..w {
            let new_y = w - 1 - x;
            let new_x = y;
            for ch in 0..c {
                result[[new_y, new_x, ch]] = image[[y, x, ch]];
            }
        }
    }

    result
}

/// Flip image horizontally (mirror left-right) (u8).
///
/// # Arguments
/// * `image` - Input image (H, W, C)
///
/// # Returns
/// Flipped image (H, W, C) - same dimensions
pub fn flip_horizontal_u8(image: ArrayView3<u8>) -> Array3<u8> {
    let (h, w, c) = (image.shape()[0], image.shape()[1], image.shape()[2]);
    let mut result = Array3::<u8>::zeros((h, w, c));

    for y in 0..h {
        for x in 0..w {
            let new_x = w - 1 - x;
            for ch in 0..c {
                result[[y, new_x, ch]] = image[[y, x, ch]];
            }
        }
    }

    result
}

/// Flip image horizontally (mirror left-right) (f32).
pub fn flip_horizontal_f32(image: ArrayView3<f32>) -> Array3<f32> {
    let (h, w, c) = (image.shape()[0], image.shape()[1], image.shape()[2]);
    let mut result = Array3::<f32>::zeros((h, w, c));

    for y in 0..h {
        for x in 0..w {
            let new_x = w - 1 - x;
            for ch in 0..c {
                result[[y, new_x, ch]] = image[[y, x, ch]];
            }
        }
    }

    result
}

/// Flip image vertically (mirror top-bottom) (u8).
///
/// # Arguments
/// * `image` - Input image (H, W, C)
///
/// # Returns
/// Flipped image (H, W, C) - same dimensions
pub fn flip_vertical_u8(image: ArrayView3<u8>) -> Array3<u8> {
    let (h, w, c) = (image.shape()[0], image.shape()[1], image.shape()[2]);
    let mut result = Array3::<u8>::zeros((h, w, c));

    for y in 0..h {
        let new_y = h - 1 - y;
        for x in 0..w {
            for ch in 0..c {
                result[[new_y, x, ch]] = image[[y, x, ch]];
            }
        }
    }

    result
}

/// Flip image vertically (mirror top-bottom) (f32).
pub fn flip_vertical_f32(image: ArrayView3<f32>) -> Array3<f32> {
    let (h, w, c) = (image.shape()[0], image.shape()[1], image.shape()[2]);
    let mut result = Array3::<f32>::zeros((h, w, c));

    for y in 0..h {
        let new_y = h - 1 - y;
        for x in 0..w {
            for ch in 0..c {
                result[[new_y, x, ch]] = image[[y, x, ch]];
            }
        }
    }

    result
}

/// Rotate image by specified degrees (must be 90, 180, or 270) (u8).
///
/// # Arguments
/// * `image` - Input image (H, W, C)
/// * `degrees` - Rotation angle in degrees (90, 180, or 270)
///
/// # Returns
/// Rotated image. For 90/270, dimensions are swapped.
///
/// # Panics
/// If degrees is not 90, 180, or 270.
pub fn rotate_u8(image: ArrayView3<u8>, degrees: u32) -> Array3<u8> {
    match degrees {
        90 => rotate_90_cw_u8(image),
        180 => rotate_180_u8(image),
        270 => rotate_270_cw_u8(image),
        _ => panic!("Degrees must be 90, 180, or 270, got {}", degrees),
    }
}

/// Rotate image by specified degrees (must be 90, 180, or 270) (f32).
pub fn rotate_f32(image: ArrayView3<f32>, degrees: u32) -> Array3<f32> {
    match degrees {
        90 => rotate_90_cw_f32(image),
        180 => rotate_180_f32(image),
        270 => rotate_270_cw_f32(image),
        _ => panic!("Degrees must be 90, 180, or 270, got {}", degrees),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_rotate_90_cw_2x3_rgba() {
        // 2x3 image (H=2, W=3), 4 channels
        // Pixel values encode (row, col) position
        let image = Array3::from_shape_vec((2, 3, 4), vec![
            // Row 0
            0, 0, 0, 255,   // (0,0)
            0, 1, 0, 255,   // (0,1)
            0, 2, 0, 255,   // (0,2)
            // Row 1
            1, 0, 0, 255,   // (1,0)
            1, 1, 0, 255,   // (1,1)
            1, 2, 0, 255,   // (1,2)
        ]).unwrap();

        let rotated = rotate_90_cw_u8(image.view());

        // After 90° CW: 2x3 becomes 3x2
        assert_eq!(rotated.shape(), &[3, 2, 4]);

        // Check corners
        // Original (0,0) -> rotated (0, 1)
        assert_eq!(rotated[[0, 1, 0]], 0); // was at row 0
        assert_eq!(rotated[[0, 1, 1]], 0); // was at col 0

        // Original (0,2) -> rotated (2, 1)
        assert_eq!(rotated[[2, 1, 0]], 0); // was at row 0
        assert_eq!(rotated[[2, 1, 1]], 2); // was at col 2

        // Original (1,0) -> rotated (0, 0)
        assert_eq!(rotated[[0, 0, 0]], 1); // was at row 1
        assert_eq!(rotated[[0, 0, 1]], 0); // was at col 0
    }

    #[test]
    fn test_rotate_180_preserves_dimensions() {
        let image = Array3::<u8>::zeros((10, 20, 4));
        let rotated = rotate_180_u8(image.view());
        assert_eq!(rotated.shape(), &[10, 20, 4]);
    }

    #[test]
    fn test_rotate_270_swaps_dimensions() {
        let image = Array3::<u8>::zeros((10, 20, 4));
        let rotated = rotate_270_cw_u8(image.view());
        assert_eq!(rotated.shape(), &[20, 10, 4]);
    }

    #[test]
    fn test_flip_horizontal_preserves_dimensions() {
        let image = Array3::<u8>::zeros((10, 20, 3));
        let flipped = flip_horizontal_u8(image.view());
        assert_eq!(flipped.shape(), &[10, 20, 3]);
    }

    #[test]
    fn test_flip_vertical_preserves_dimensions() {
        let image = Array3::<f32>::zeros((10, 20, 1));
        let flipped = flip_vertical_f32(image.view());
        assert_eq!(flipped.shape(), &[10, 20, 1]);
    }

    #[test]
    fn test_rotate_360_identity() {
        // Rotate 90 four times should give identity
        let image = Array3::from_shape_vec((2, 3, 1), vec![
            1, 2, 3,
            4, 5, 6,
        ]).unwrap();

        let r1 = rotate_90_cw_u8(image.view());
        let r2 = rotate_90_cw_u8(r1.view());
        let r3 = rotate_90_cw_u8(r2.view());
        let r4 = rotate_90_cw_u8(r3.view());

        assert_eq!(image, r4);
    }

    #[test]
    fn test_flip_twice_identity() {
        let image = Array3::from_shape_vec((2, 3, 1), vec![
            1, 2, 3,
            4, 5, 6,
        ]).unwrap();

        let f1 = flip_horizontal_u8(image.view());
        let f2 = flip_horizontal_u8(f1.view());

        assert_eq!(image, f2);
    }

    #[test]
    fn test_grayscale_support() {
        // Grayscale (1 channel) should work
        let image = Array3::<u8>::zeros((100, 100, 1));
        let rotated = rotate_90_cw_u8(image.view());
        assert_eq!(rotated.shape(), &[100, 100, 1]);
    }

    #[test]
    fn test_rgb_support() {
        // RGB (3 channels) should work
        let image = Array3::<f32>::zeros((100, 100, 3));
        let rotated = rotate_90_cw_f32(image.view());
        assert_eq!(rotated.shape(), &[100, 100, 3]);
    }
}
