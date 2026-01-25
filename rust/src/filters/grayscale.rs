//! Grayscale conversion filter.
//!
//! Works with both PyO3 (numpy) and WASM (JS Uint8Array).
//! Uses ITU-R BT.709 luminosity coefficients.

use ndarray::{Array3, ArrayView3};

/// Convert RGBA image to grayscale (luminosity method).
///
/// Output is RGBA with R=G=B=luminosity, A preserved.
/// Uses ITU-R BT.709 coefficients: 0.2126 R + 0.7152 G + 0.0722 B
///
/// # Arguments
/// * `input` - 3D array view of shape (height, width, 4) with RGBA u8 values
///
/// # Returns
/// New array with grayscale values in RGB channels, alpha preserved
pub fn grayscale_rgba_impl(input: ArrayView3<u8>) -> Array3<u8> {
    let (height, width, _) = input.dim();
    let mut output = Array3::<u8>::zeros((height, width, 4));

    for y in 0..height {
        for x in 0..width {
            let r = input[[y, x, 0]] as f32;
            let g = input[[y, x, 1]] as f32;
            let b = input[[y, x, 2]] as f32;
            let a = input[[y, x, 3]];

            // ITU-R BT.709 luminosity coefficients
            let gray = (0.2126 * r + 0.7152 * g + 0.0722 * b) as u8;

            output[[y, x, 0]] = gray;
            output[[y, x, 1]] = gray;
            output[[y, x, 2]] = gray;
            output[[y, x, 3]] = a;
        }
    }

    output
}

#[cfg(test)]
mod tests {
    use super::*;
    use ndarray::Array3;

    #[test]
    fn test_grayscale_red() {
        // Pure red should become dark gray
        let mut img = Array3::<u8>::zeros((1, 1, 4));
        img[[0, 0, 0]] = 255; // R
        img[[0, 0, 3]] = 255; // A

        let result = grayscale_rgba_impl(img.view());

        // 0.2126 * 255 ≈ 54
        assert!((result[[0, 0, 0]] as i32 - 54).abs() <= 1);
        assert_eq!(result[[0, 0, 0]], result[[0, 0, 1]]);
        assert_eq!(result[[0, 0, 1]], result[[0, 0, 2]]);
        assert_eq!(result[[0, 0, 3]], 255);
    }

    #[test]
    fn test_grayscale_green() {
        // Pure green should become bright gray
        let mut img = Array3::<u8>::zeros((1, 1, 4));
        img[[0, 0, 1]] = 255; // G
        img[[0, 0, 3]] = 255; // A

        let result = grayscale_rgba_impl(img.view());

        // 0.7152 * 255 ≈ 182
        assert!((result[[0, 0, 0]] as i32 - 182).abs() <= 1);
    }

    #[test]
    fn test_grayscale_blue() {
        // Pure blue should become very dark gray
        let mut img = Array3::<u8>::zeros((1, 1, 4));
        img[[0, 0, 2]] = 255; // B
        img[[0, 0, 3]] = 255; // A

        let result = grayscale_rgba_impl(img.view());

        // 0.0722 * 255 ≈ 18
        assert!((result[[0, 0, 0]] as i32 - 18).abs() <= 1);
    }

    #[test]
    fn test_grayscale_preserves_alpha() {
        let mut img = Array3::<u8>::zeros((1, 1, 4));
        img[[0, 0, 0]] = 128;
        img[[0, 0, 1]] = 128;
        img[[0, 0, 2]] = 128;
        img[[0, 0, 3]] = 100; // Semi-transparent

        let result = grayscale_rgba_impl(img.view());

        assert_eq!(result[[0, 0, 3]], 100);
    }

    #[test]
    fn test_grayscale_white() {
        // White should stay white
        let mut img = Array3::<u8>::zeros((1, 1, 4));
        img[[0, 0, 0]] = 255;
        img[[0, 0, 1]] = 255;
        img[[0, 0, 2]] = 255;
        img[[0, 0, 3]] = 255;

        let result = grayscale_rgba_impl(img.view());

        // 0.2126 * 255 + 0.7152 * 255 + 0.0722 * 255 = 255
        assert_eq!(result[[0, 0, 0]], 255);
    }
}
