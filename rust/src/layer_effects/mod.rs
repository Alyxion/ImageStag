//! Layer effects for image styling (Photoshop-style layer styles).
//!
//! ## Co-located Source Files
//!
//! Rust implementations are co-located with Python and JS wrappers in `imagestag/layer_effects/`.
//! This mod.rs uses `#[path]` attributes to include them from that location.
//!
//! Each effect has a triplet of files:
//! - `effect_name.rs` - Rust implementation
//! - `effect_name.py` - Python wrapper
//! - `effect_name.js` - JavaScript wrapper
//!
//! ## Shadow Effects
//! - **Drop Shadow** - Shadow cast behind the layer
//! - **Inner Shadow** - Shadow inside the layer edges
//!
//! ## Glow Effects
//! - **Outer Glow** - Glow radiating outward from edges
//! - **Inner Glow** - Glow radiating inward from edges
//!
//! ## Bevel & Emboss
//! - **Bevel & Emboss** - 3D raised/sunken appearance
//!
//! ## Overlay Effects
//! - **Satin** - Silky interior shading
//! - **Color Overlay** - Solid color fill preserving alpha
//! - **Gradient Overlay** - Gradient fill preserving alpha
//! - **Pattern Overlay** - Tiled pattern preserving alpha
//!
//! ## Stroke
//! - **Stroke** - Outline around layer content

// Shadow effects
#[path = "../../../imagestag/layer_effects/drop_shadow.rs"]
pub mod drop_shadow;

#[path = "../../../imagestag/layer_effects/inner_shadow.rs"]
pub mod inner_shadow;

// Glow effects
#[path = "../../../imagestag/layer_effects/outer_glow.rs"]
pub mod outer_glow;

#[path = "../../../imagestag/layer_effects/inner_glow.rs"]
pub mod inner_glow;

// Bevel & Emboss
#[path = "../../../imagestag/layer_effects/bevel_emboss.rs"]
pub mod bevel_emboss;

// Overlay effects
#[path = "../../../imagestag/layer_effects/satin.rs"]
pub mod satin;

#[path = "../../../imagestag/layer_effects/color_overlay.rs"]
pub mod color_overlay;

#[path = "../../../imagestag/layer_effects/gradient_overlay.rs"]
pub mod gradient_overlay;

#[path = "../../../imagestag/layer_effects/pattern_overlay.rs"]
pub mod pattern_overlay;

// Stroke effect
#[path = "../../../imagestag/layer_effects/stroke.rs"]
pub mod stroke;
