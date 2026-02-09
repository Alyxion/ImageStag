//! Standalone gradient surface generator.
//!
//! Generates gradient images without requiring an input image.
//! Reuses gradient math from `layer_effects::gradient_overlay`.

use ndarray::Array3;
use numpy::{IntoPyArray, PyArray3};
use pyo3::prelude::*;

use crate::layer_effects::gradient_overlay::{
    GradientStop, calculate_gradient_t, interpolate_gradient,
};

/// Parse flat stops array into sorted GradientStop vec.
///
/// For u8 input: [pos, r, g, b, ...] where r,g,b are 0-255
/// For f32 input: [pos, r, g, b, ...] where r,g,b are 0.0-1.0
fn parse_stops(stops: &[f32], normalize: bool) -> Vec<GradientStop> {
    let mut gradient_stops: Vec<GradientStop> = stops.chunks(4)
        .filter(|c| c.len() == 4)
        .map(|c| GradientStop {
            position: c[0],
            r: if normalize { c[1] / 255.0 } else { c[1] },
            g: if normalize { c[2] / 255.0 } else { c[2] },
            b: if normalize { c[3] / 255.0 } else { c[3] },
        })
        .collect();

    gradient_stops.sort_by(|a, b| a.position.partial_cmp(&b.position).unwrap_or(std::cmp::Ordering::Equal));

    if gradient_stops.is_empty() {
        gradient_stops.push(GradientStop { position: 0.0, r: 0.0, g: 0.0, b: 0.0 });
        gradient_stops.push(GradientStop { position: 1.0, r: 1.0, g: 1.0, b: 1.0 });
    }

    gradient_stops
}

/// Generate a gradient image as RGBA u8 array.
///
/// # Arguments
/// * `width` - Image width in pixels
/// * `height` - Image height in pixels
/// * `stops` - Gradient stops as flat array: [pos, r, g, b, ...] (r,g,b: 0-255)
/// * `style` - Gradient style: "linear", "radial", "angle", "reflected", "diamond"
/// * `angle` - Angle in degrees
/// * `scale_x` - Horizontal scale (1.0 = 100%)
/// * `scale_y` - Vertical scale (1.0 = 100%)
/// * `offset_x` - Horizontal center offset (-1.0 to 1.0)
/// * `offset_y` - Vertical center offset (-1.0 to 1.0)
/// * `reverse` - Whether to reverse the gradient
/// * `channels` - Output channels: 3 (RGB) or 4 (RGBA)
#[pyfunction]
#[pyo3(signature = (width, height, stops, style="linear", angle=90.0, scale_x=1.0, scale_y=1.0, offset_x=0.0, offset_y=0.0, reverse=false, channels=4))]
pub fn generate_gradient<'py>(
    py: Python<'py>,
    width: usize,
    height: usize,
    stops: Vec<f32>,
    style: &str,
    angle: f32,
    scale_x: f32,
    scale_y: f32,
    offset_x: f32,
    offset_y: f32,
    reverse: bool,
    channels: usize,
) -> Bound<'py, PyArray3<u8>> {
    let gradient_stops = parse_stops(&stops, true); // normalize 0-255 to 0.0-1.0
    let ch = if channels == 3 { 3 } else { 4 };

    let mut result = Array3::<u8>::zeros((height, width, ch));

    for y in 0..height {
        for x in 0..width {
            let t = calculate_gradient_t(x, y, width, height, style, angle, scale_x, scale_y, offset_x, offset_y, reverse);
            let (r, g, b) = interpolate_gradient(&gradient_stops, t);
            result[[y, x, 0]] = (r * 255.0).clamp(0.0, 255.0) as u8;
            result[[y, x, 1]] = (g * 255.0).clamp(0.0, 255.0) as u8;
            result[[y, x, 2]] = (b * 255.0).clamp(0.0, 255.0) as u8;
            if ch == 4 {
                result[[y, x, 3]] = 255;
            }
        }
    }

    result.into_pyarray(py)
}

/// Generate a gradient image as RGBA f32 array.
///
/// Same as generate_gradient but returns f32 values (0.0-1.0).
/// Stops format: [pos, r, g, b, ...] where all values are 0.0-1.0
#[pyfunction]
#[pyo3(signature = (width, height, stops, style="linear", angle=90.0, scale_x=1.0, scale_y=1.0, offset_x=0.0, offset_y=0.0, reverse=false, channels=4))]
pub fn generate_gradient_f32<'py>(
    py: Python<'py>,
    width: usize,
    height: usize,
    stops: Vec<f32>,
    style: &str,
    angle: f32,
    scale_x: f32,
    scale_y: f32,
    offset_x: f32,
    offset_y: f32,
    reverse: bool,
    channels: usize,
) -> Bound<'py, PyArray3<f32>> {
    let gradient_stops = parse_stops(&stops, false); // already 0.0-1.0
    let ch = if channels == 3 { 3 } else { 4 };

    let mut result = Array3::<f32>::zeros((height, width, ch));

    for y in 0..height {
        for x in 0..width {
            let t = calculate_gradient_t(x, y, width, height, style, angle, scale_x, scale_y, offset_x, offset_y, reverse);
            let (r, g, b) = interpolate_gradient(&gradient_stops, t);
            result[[y, x, 0]] = r;
            result[[y, x, 1]] = g;
            result[[y, x, 2]] = b;
            if ch == 4 {
                result[[y, x, 3]] = 1.0;
            }
        }
    }

    result.into_pyarray(py)
}
