//! Selection algorithms for image editing.
//!
//! This module provides cross-platform selection algorithms:
//! - **Contour extraction**: Marching squares for outline generation from alpha masks
//! - **Magic wand**: Flood fill based color/tolerance selection
//!
//! Both are used in Stagforge for selection tools and marching ants visualization.

pub mod contour;
pub mod magic_wand;

pub use contour::extract_contours;
pub use magic_wand::magic_wand_select;
