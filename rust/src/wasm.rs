//! WebAssembly exports for ImageStag filters.
//!
//! These functions are exposed to JavaScript via wasm-bindgen.

use wasm_bindgen::prelude::*;
use ndarray::Array3;

use crate::filters::grayscale::grayscale_rgba_impl;

/// Convert RGBA image to grayscale using BT.709 luminosity.
///
/// # Arguments
/// * `data` - Flat array of RGBA bytes (length = width * height * 4)
/// * `width` - Image width in pixels
/// * `height` - Image height in pixels
///
/// # Returns
/// Flat array of RGBA bytes with grayscale values
#[wasm_bindgen]
pub fn grayscale_rgba_wasm(
    data: &[u8],
    width: usize,
    height: usize,
) -> Vec<u8> {
    // Reshape flat array to 3D
    let input = Array3::from_shape_vec(
        (height, width, 4),
        data.to_vec()
    ).expect("Invalid dimensions");

    let result = grayscale_rgba_impl(input.view());
    result.into_raw_vec()
}
