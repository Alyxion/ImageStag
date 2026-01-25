//! Filter modules for image processing effects.
//!
//! ## Supported Formats
//!
//! All cross-platform filters accept images with 1, 3, or 4 channels:
//!
//! | Format | Shape | Type | Description |
//! |--------|-------|------|-------------|
//! | Grayscale8 | (H, W, 1) | u8 | Single luminance channel, 0-255 |
//! | Grayscale float | (H, W, 1) | f32 | Single luminance channel, 0.0-1.0 |
//! | RGB8 | (H, W, 3) | u8 | Red, green, blue, 0-255 |
//! | RGB float | (H, W, 3) | f32 | Red, green, blue, 0.0-1.0 |
//! | RGBA8 | (H, W, 4) | u8 | RGB + alpha, 0-255 |
//! | RGBA float | (H, W, 4) | f32 | RGB + alpha, 0.0-1.0 |
//!
//! Channel count is inferred from input array dimensions. Filters process
//! only the channels that exist, avoiding unnecessary work on unused alpha.
//!
//! ## Architecture
//!
//! All filters follow these principles:
//! - **Multi-channel aware** - Handles 1, 3, or 4 channels efficiently
//! - **Dual precision** - Both u8 (0-255) and f32 (0.0-1.0) variants
//! - **Alpha preservation** - Alpha channel (if present) is always preserved
//! - **Grayscale handling** - Color-dependent filters (saturation, hue) are no-ops for grayscale
//! - **Thread-safe** - Use rayon for parallel processing where available
//!
//! ## Filter Categories
//!
//! - **Pixel-wise**: brightness, contrast, gamma, exposure, invert (work on all formats)
//! - **Color science**: hue_shift, vibrance, color_balance (require RGB/RGBA)
//! - **Tonal**: levels, curves, auto_levels (work on all formats)
//! - **Edge detection**: sobel, laplacian, find_edges (work on all formats)
//! - **Stylize**: posterize, solarize, threshold, emboss (work on all formats)
//! - **Noise**: add_noise, median, denoise (work on all formats)
//! - **Morphology**: dilate, erode (work on all formats)

// Cross-platform filter modules (work with both Python and WASM)
pub mod grayscale;
pub mod color_adjust;
pub mod color_science;
pub mod stylize;
pub mod levels_curves;
pub mod sharpen;
pub mod edge;
pub mod noise;
pub mod morphology;

// Python-only modules (require PyO3/numpy/rayon)
#[cfg(feature = "python")]
pub mod core;
#[cfg(feature = "python")]
pub mod basic;
#[cfg(feature = "python")]
pub mod blur;
#[cfg(feature = "python")]
pub mod drop_shadow;
#[cfg(feature = "python")]
pub mod stroke;
#[cfg(feature = "python")]
pub mod lighting;
