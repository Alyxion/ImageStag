//! Layer effects for image styling (Photoshop-style layer styles).
//!
//! This module provides all layer effects:
//!
//! ## Shadow Effects
//! - **Drop Shadow** - Shadow cast behind the layer (`drop_shadow.rs`)
//! - **Inner Shadow** - Shadow inside the layer edges (`lighting.rs`)
//!
//! ## Glow Effects
//! - **Outer Glow** - Glow radiating outward from edges (`lighting.rs`)
//! - **Inner Glow** - Glow radiating inward from edges (`lighting.rs`)
//!
//! ## Bevel & Emboss
//! - **Bevel & Emboss** - 3D raised/sunken appearance (`lighting.rs`)
//!
//! ## Overlay Effects
//! - **Satin** - Silky interior shading (`satin.rs`)
//! - **Color Overlay** - Solid color fill preserving alpha (`lighting.rs`)
//! - **Gradient Overlay** - Gradient fill preserving alpha (`gradient_overlay.rs`)
//! - **Pattern Overlay** - Tiled pattern preserving alpha (`pattern_overlay.rs`)
//!
//! ## Stroke
//! - **Stroke** - Outline around layer content (`stroke.rs`)
//!
//! ## Layer Effects vs Filters
//!
//! Layer effects differ from filters in that they:
//! - Work primarily with the alpha channel
//! - May expand the canvas (returning position offsets)
//! - Preserve transparency while modifying colors
//! - Support blend modes and opacity

// Shadow and glow effects
pub mod drop_shadow;
pub mod lighting;

// Overlay effects
pub mod satin;
pub mod gradient_overlay;
pub mod pattern_overlay;

// Stroke effect
pub mod stroke;
