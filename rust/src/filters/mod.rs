//! Filter modules for image processing effects.
//!
//! ## Co-located Source Files
//!
//! Rust implementations are co-located with Python and JS wrappers in `imagestag/filters/`.
//! This mod.rs uses `#[path]` attributes to include them from that location.
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

// Cross-platform filter modules (work with both Python and WASM)
// Source files are co-located with Python/JS wrappers in imagestag/filters/

#[path = "../../../imagestag/filters/grayscale.rs"]
pub mod grayscale;

#[path = "../../../imagestag/filters/color_adjust.rs"]
pub mod color_adjust;

#[path = "../../../imagestag/filters/color_science.rs"]
pub mod color_science;

#[path = "../../../imagestag/filters/stylize.rs"]
pub mod stylize;

#[path = "../../../imagestag/filters/levels_curves.rs"]
pub mod levels_curves;

#[path = "../../../imagestag/filters/sharpen.rs"]
pub mod sharpen;

#[path = "../../../imagestag/filters/edge.rs"]
pub mod edge;

#[path = "../../../imagestag/filters/noise.rs"]
pub mod noise;

#[path = "../../../imagestag/filters/morphology.rs"]
pub mod morphology;

// Shared core utilities (available for both Python and WASM)
#[cfg(any(feature = "python", feature = "wasm"))]
#[path = "../../../imagestag/filters/core.rs"]
pub mod core;

// Python-only modules (require PyO3/numpy/rayon)
#[cfg(feature = "python")]
#[path = "../../../imagestag/filters/basic.rs"]
pub mod basic;

#[cfg(feature = "python")]
#[path = "../../../imagestag/filters/blur.rs"]
pub mod blur;
