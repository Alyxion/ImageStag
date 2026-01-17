//! ImageStag Rust Extensions
//!
//! High-performance image processing functions implemented in Rust
//! with Python bindings via PyO3.
//!
//! ## Image Format
//! All images use **RGBA** format (not BGR). Supported types:
//! - `u8`: 8-bit per channel (0-255)
//! - `f32`: Float per channel (0.0-1.0)
//!
//! ## Filter Architecture
//! Filters can produce output images with different dimensions than input,
//! useful for effects like drop shadows that extend beyond the original bounds.

mod filters;

use numpy::{IntoPyArray, PyArray1, PyArray2, PyArray3, PyReadonlyArray2, PyReadonlyArray3};
use pyo3::prelude::*;

// Re-export filter functions
use filters::drop_shadow::{drop_shadow_rgba, drop_shadow_rgba_f32};
use filters::stroke::{stroke_rgba, stroke_rgba_f32};
use filters::lighting::{
    bevel_emboss_rgba, inner_glow_rgba, outer_glow_rgba,
    inner_shadow_rgba, inner_shadow_rgba_f32,
    color_overlay_rgba, color_overlay_rgba_f32,
};
use filters::blur::{gaussian_blur_rgba, box_blur_rgba};
use filters::basic::{threshold_gray, invert_rgba, premultiply_alpha, unpremultiply_alpha};

/// ImageStag Rust extension module
#[pymodule]
fn imagestag_rust(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Basic operations
    m.add_function(wrap_pyfunction!(threshold_gray, m)?)?;
    m.add_function(wrap_pyfunction!(invert_rgba, m)?)?;
    m.add_function(wrap_pyfunction!(premultiply_alpha, m)?)?;
    m.add_function(wrap_pyfunction!(unpremultiply_alpha, m)?)?;

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
