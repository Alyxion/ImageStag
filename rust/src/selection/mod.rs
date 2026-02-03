//! Selection algorithms for image editing.
//!
//! This module provides cross-platform selection algorithms:
//! - **Contour extraction**: Basic boundary tracing for marching ants display
//! - **Marching squares**: Sub-pixel precision contour extraction with simplification
//! - **Magic wand**: Flood fill based color/tolerance selection
//!
//! Both are used in Stagforge for selection tools and marching ants visualization.

pub mod contour;
pub mod magic_wand;
pub mod marching_squares;

pub use contour::extract_contours;
pub use magic_wand::magic_wand_select;
pub use marching_squares::{
    extract_contours_precise, marching_squares, douglas_peucker, douglas_peucker_closed,
    fit_bezier_curves, contours_to_svg, contours_to_flat, simplify_contour,
    Point, BezierSegment, Contour,
};
