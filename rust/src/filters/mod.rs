//! Filter modules for image processing effects.
//!
//! ## Architecture
//!
//! All filters follow these principles:
//! - **RGBA format only** - No BGR/BGRA support
//! - **Dual precision** - Both u8 (0-255) and f32 (0.0-1.0) variants
//! - **Flexible output size** - Filters can expand canvas for effects like shadows
//! - **Anti-aliasing aware** - Sub-pixel accuracy where applicable
//! - **Thread-safe** - Use rayon for parallel processing
//!
//! ## Common Parameters
//!
//! Many filters accept these standard parameters:
//! - `expand`: Extra pixels to add around the image (for shadows, glows, strokes)
//! - `offset_x`, `offset_y`: Offset of the effect from the source
//! - `color`: RGBA color tuple (r, g, b, a) with values 0-255 or 0.0-1.0
//!
//! ## Layer Effects
//!
//! Layer effects (drop shadow, stroke, glow, etc.) are non-destructive effects
//! applied to image layers. All effects support:
//! - RGB8: uint8 (0-255), 3 channels
//! - RGBA8: uint8 (0-255), 4 channels
//! - RGBf32: float32 (0.0-1.0), 3 channels
//! - RGBAf32: float32 (0.0-1.0), 4 channels

// Grayscale - portable, works with both Python and WASM
pub mod grayscale;

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
