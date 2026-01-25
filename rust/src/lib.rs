//! ImageStag Rust Extensions
//!
//! High-performance image processing functions implemented in Rust
//! with Python bindings via PyO3 and WASM bindings for JavaScript.
//!
//! ## Image Format
//! All images use **RGBA** format (not BGR). Supported types:
//! - `u8`: 8-bit per channel (0-255)
//! - `f32`: Float per channel (0.0-1.0)
//!
//! ## Filter Architecture
//! Filters can produce output images with different dimensions than input,
//! useful for effects like drop shadows that extend beyond the original bounds.

pub mod filters;

#[cfg(feature = "wasm")]
pub mod wasm;

// Python bindings (only when python feature is enabled)
#[cfg(feature = "python")]
mod python {
    use numpy::{IntoPyArray, PyArray3, PyReadonlyArray3};
    use pyo3::prelude::*;

    use crate::filters::drop_shadow::{drop_shadow_rgba, drop_shadow_rgba_f32};
    use crate::filters::stroke::{stroke_rgba, stroke_rgba_f32};
    use crate::filters::lighting::{
        bevel_emboss_rgba, inner_glow_rgba, outer_glow_rgba,
        inner_shadow_rgba, inner_shadow_rgba_f32,
        color_overlay_rgba, color_overlay_rgba_f32,
    };
    use crate::filters::blur::{gaussian_blur_rgba, box_blur_rgba};
    use crate::filters::basic::{threshold_gray, invert_rgba, premultiply_alpha, unpremultiply_alpha};
    use crate::filters::grayscale::grayscale_rgba_impl;

    /// Convert RGBA image to grayscale using BT.709 luminosity.
    ///
    /// Output is RGBA with R=G=B=luminosity, alpha preserved.
    #[pyfunction]
    pub fn grayscale_rgba<'py>(
        py: Python<'py>,
        image: PyReadonlyArray3<'py, u8>,
    ) -> Bound<'py, PyArray3<u8>> {
        let input = image.as_array();
        let result = grayscale_rgba_impl(input);
        result.into_pyarray(py)
    }

    /// ImageStag Rust extension module
    #[pymodule]
    pub fn imagestag_rust(m: &Bound<'_, PyModule>) -> PyResult<()> {
        // Basic operations
        m.add_function(wrap_pyfunction!(threshold_gray, m)?)?;
        m.add_function(wrap_pyfunction!(invert_rgba, m)?)?;
        m.add_function(wrap_pyfunction!(premultiply_alpha, m)?)?;
        m.add_function(wrap_pyfunction!(unpremultiply_alpha, m)?)?;
        m.add_function(wrap_pyfunction!(grayscale_rgba, m)?)?;

        // Blur filters
        m.add_function(wrap_pyfunction!(gaussian_blur_rgba, m)?)?;
        m.add_function(wrap_pyfunction!(box_blur_rgba, m)?)?;

        // Layer effects
        m.add_function(wrap_pyfunction!(drop_shadow_rgba, m)?)?;
        m.add_function(wrap_pyfunction!(drop_shadow_rgba_f32, m)?)?;
        m.add_function(wrap_pyfunction!(stroke_rgba, m)?)?;
        m.add_function(wrap_pyfunction!(stroke_rgba_f32, m)?)?;
        m.add_function(wrap_pyfunction!(bevel_emboss_rgba, m)?)?;
        m.add_function(wrap_pyfunction!(inner_glow_rgba, m)?)?;
        m.add_function(wrap_pyfunction!(outer_glow_rgba, m)?)?;
        m.add_function(wrap_pyfunction!(inner_shadow_rgba, m)?)?;
        m.add_function(wrap_pyfunction!(inner_shadow_rgba_f32, m)?)?;
        m.add_function(wrap_pyfunction!(color_overlay_rgba, m)?)?;
        m.add_function(wrap_pyfunction!(color_overlay_rgba_f32, m)?)?;

        Ok(())
    }
}

#[cfg(feature = "python")]
pub use python::imagestag_rust;
