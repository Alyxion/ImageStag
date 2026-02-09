//! Gradient overlay layer effect.
//!
//! Fills the layer with a gradient while preserving the alpha channel.
//! Supports 5 gradient styles: linear, radial, angle, reflected, and diamond.

use ndarray::Array3;
use numpy::{IntoPyArray, PyArray3, PyReadonlyArray3};
use pyo3::prelude::*;

/// Gradient stop definition: position (0.0-1.0) and color (RGB).
#[derive(Clone, Debug)]
pub struct GradientStop {
    pub position: f32,
    pub r: f32,
    pub g: f32,
    pub b: f32,
}

/// Interpolate color at position t from gradient stops.
pub fn interpolate_gradient(stops: &[GradientStop], t: f32) -> (f32, f32, f32) {
    if stops.is_empty() {
        return (0.0, 0.0, 0.0);
    }
    if stops.len() == 1 {
        return (stops[0].r, stops[0].g, stops[0].b);
    }

    // Clamp t to valid range
    let t = t.clamp(0.0, 1.0);

    // Find the two stops we're between
    let mut prev_idx = 0;
    let mut next_idx = stops.len() - 1;

    for (i, stop) in stops.iter().enumerate() {
        if stop.position <= t {
            prev_idx = i;
        }
        if stop.position >= t && i > prev_idx {
            next_idx = i;
            break;
        }
    }

    let prev = &stops[prev_idx];
    let next = &stops[next_idx];

    // Interpolate between the two stops
    if (next.position - prev.position).abs() < 0.0001 {
        return (prev.r, prev.g, prev.b);
    }

    let local_t = (t - prev.position) / (next.position - prev.position);
    let local_t = local_t.clamp(0.0, 1.0);

    (
        prev.r + (next.r - prev.r) * local_t,
        prev.g + (next.g - prev.g) * local_t,
        prev.b + (next.b - prev.b) * local_t,
    )
}

/// Calculate gradient position t based on style.
///
/// Returns t in range [0.0, 1.0] for the given pixel position.
///
/// Parameters:
/// - `scale_x`, `scale_y`: Scale factors (1.0 = 100%). Separate X/Y for non-uniform scaling.
/// - `offset_x`, `offset_y`: Center offset as fraction (-1.0 to 1.0). 0.0 = center.
pub fn calculate_gradient_t(
    x: usize,
    y: usize,
    width: usize,
    height: usize,
    style: &str,
    angle: f32,
    scale_x: f32,
    scale_y: f32,
    offset_x: f32,
    offset_y: f32,
    reverse: bool,
) -> f32 {
    // Center with offset applied
    let cx = width as f32 / 2.0 + offset_x * width as f32 / 2.0;
    let cy = height as f32 / 2.0 + offset_y * height as f32 / 2.0;
    let px = x as f32;
    let py = y as f32;

    // Effective scale factors (avoid division by zero)
    let sx = if scale_x.abs() > 0.001 { scale_x } else { 0.001 };
    let sy = if scale_y.abs() > 0.001 { scale_y } else { 0.001 };

    let half_w = width as f32 / 2.0;
    let half_h = height as f32 / 2.0;

    let mut t = match style {
        "linear" => {
            // Linear gradient along angle with separate scaleX/Y
            let angle_rad = angle.to_radians();
            let dx = angle_rad.cos();
            let dy = -angle_rad.sin(); // Negative because Y increases downward

            // Scale the displacement from center
            let rx = (px - cx) / sx;
            let ry = (py - cy) / sy;
            let proj = rx * dx + ry * dy;

            // Normalize to [0, 1] based on image diagonal
            let max_dist = (half_w * half_w + half_h * half_h).sqrt();
            (proj / max_dist + 1.0) / 2.0
        }
        "radial" => {
            // Elliptical gradient from center with separate scaleX/Y
            let dx = (px - cx) / sx;
            let dy = (py - cy) / sy;
            let dist = (dx * dx + dy * dy).sqrt();
            let max_dist = (half_w * half_w + half_h * half_h).sqrt();
            dist / max_dist
        }
        "angle" => {
            // Angular gradient sweeping around center
            let dx = (px - cx) / sx;
            let dy = (py - cy) / sy;
            let mut angle_at_pixel = dy.atan2(dx);

            // Adjust by the specified angle
            let angle_rad = angle.to_radians();
            angle_at_pixel -= angle_rad;

            // Normalize to [0, 1]
            (angle_at_pixel + std::f32::consts::PI) / (2.0 * std::f32::consts::PI)
        }
        "reflected" => {
            // Linear gradient mirrored at center
            let angle_rad = angle.to_radians();
            let dx = angle_rad.cos();
            let dy = -angle_rad.sin();

            let rx = (px - cx) / sx;
            let ry = (py - cy) / sy;
            let proj = rx * dx + ry * dy;

            let max_dist = (half_w * half_w + half_h * half_h).sqrt();
            let linear_t = (proj / max_dist + 1.0) / 2.0;

            // Mirror: fold at 0.5
            (2.0 * (linear_t - 0.5)).abs()
        }
        "diamond" => {
            // Diamond-shaped gradient from center
            let dx = ((px - cx) / sx).abs();
            let dy = ((py - cy) / sy).abs();
            let dist = dx + dy; // Manhattan distance gives diamond shape
            let max_dist = half_w + half_h;
            dist / max_dist
        }
        _ => {
            // Default to linear if unknown style
            let angle_rad = angle.to_radians();
            let dx = angle_rad.cos();
            let dy = -angle_rad.sin();
            let rx = (px - cx) / sx;
            let ry = (py - cy) / sy;
            let proj = rx * dx + ry * dy;
            let max_dist = (half_w * half_w + half_h * half_h).sqrt();
            (proj / max_dist + 1.0) / 2.0
        }
    };

    // Clamp to valid range
    t = t.clamp(0.0, 1.0);

    // Apply reverse
    if reverse {
        t = 1.0 - t;
    }

    t
}

/// Apply gradient overlay to RGBA u8 image.
///
/// # Arguments
/// * `image` - Source RGBA image
/// * `stops` - Gradient color stops as flat array: [pos, r, g, b, pos, r, g, b, ...]
///             where pos is 0.0-1.0 and r,g,b are 0-255
/// * `style` - Gradient style: "linear", "radial", "angle", "reflected", "diamond"
/// * `angle` - Angle in degrees (for linear/reflected styles)
/// * `scale_x` - Horizontal scale factor (1.0 = 100%)
/// * `scale_y` - Vertical scale factor (1.0 = 100%)
/// * `offset_x` - Horizontal center offset (-1.0 to 1.0, 0.0 = center)
/// * `offset_y` - Vertical center offset (-1.0 to 1.0, 0.0 = center)
/// * `reverse` - Whether to reverse the gradient direction
/// * `opacity` - Effect opacity (0.0-1.0)
/// * `blend_mode` - Blend mode: "normal", "multiply", "screen", "overlay"
#[pyfunction]
#[pyo3(signature = (image, stops, style="linear", angle=90.0, scale_x=1.0, scale_y=1.0, offset_x=0.0, offset_y=0.0, reverse=false, opacity=1.0, blend_mode="normal"))]
pub fn gradient_overlay_rgba<'py>(
    py: Python<'py>,
    image: PyReadonlyArray3<'py, u8>,
    stops: Vec<f32>,
    style: &str,
    angle: f32,
    scale_x: f32,
    scale_y: f32,
    offset_x: f32,
    offset_y: f32,
    reverse: bool,
    opacity: f32,
    blend_mode: &str,
) -> Bound<'py, PyArray3<u8>> {
    let input = image.as_array();
    let (height, width, _) = (input.shape()[0], input.shape()[1], input.shape()[2]);

    // Parse gradient stops from flat array [pos, r, g, b, pos, r, g, b, ...]
    let mut gradient_stops: Vec<GradientStop> = Vec::new();
    for chunk in stops.chunks(4) {
        if chunk.len() == 4 {
            gradient_stops.push(GradientStop {
                position: chunk[0],
                r: chunk[1] / 255.0,
                g: chunk[2] / 255.0,
                b: chunk[3] / 255.0,
            });
        }
    }

    // Sort stops by position
    gradient_stops.sort_by(|a, b| a.position.partial_cmp(&b.position).unwrap_or(std::cmp::Ordering::Equal));

    // Default gradient if no stops provided
    if gradient_stops.is_empty() {
        gradient_stops.push(GradientStop { position: 0.0, r: 0.0, g: 0.0, b: 0.0 });
        gradient_stops.push(GradientStop { position: 1.0, r: 1.0, g: 1.0, b: 1.0 });
    }

    // Step 1: Generate gradient buffer
    let mut gradient_buf = Array3::<f32>::zeros((height, width, 3));
    for y in 0..height {
        for x in 0..width {
            let t = calculate_gradient_t(x, y, width, height, style, angle, scale_x, scale_y, offset_x, offset_y, reverse);
            let (r, g, b) = interpolate_gradient(&gradient_stops, t);
            gradient_buf[[y, x, 0]] = r;
            gradient_buf[[y, x, 1]] = g;
            gradient_buf[[y, x, 2]] = b;
        }
    }

    // Step 2: Blend with source using optimized per-mode loops
    let mut result = Array3::<u8>::zeros((height, width, 4));

    match blend_mode {
        "multiply" => {
            for y in 0..height {
                for x in 0..width {
                    let orig_a = input[[y, x, 3]];
                    if orig_a == 0 { continue; }
                    let orig_r = input[[y, x, 0]] as f32 / 255.0;
                    let orig_g = input[[y, x, 1]] as f32 / 255.0;
                    let orig_b = input[[y, x, 2]] as f32 / 255.0;
                    let mr = orig_r * gradient_buf[[y, x, 0]];
                    let mg = orig_g * gradient_buf[[y, x, 1]];
                    let mb = orig_b * gradient_buf[[y, x, 2]];
                    result[[y, x, 0]] = ((orig_r * (1.0 - opacity) + mr * opacity) * 255.0).clamp(0.0, 255.0) as u8;
                    result[[y, x, 1]] = ((orig_g * (1.0 - opacity) + mg * opacity) * 255.0).clamp(0.0, 255.0) as u8;
                    result[[y, x, 2]] = ((orig_b * (1.0 - opacity) + mb * opacity) * 255.0).clamp(0.0, 255.0) as u8;
                    result[[y, x, 3]] = orig_a;
                }
            }
        }
        "screen" => {
            for y in 0..height {
                for x in 0..width {
                    let orig_a = input[[y, x, 3]];
                    if orig_a == 0 { continue; }
                    let orig_r = input[[y, x, 0]] as f32 / 255.0;
                    let orig_g = input[[y, x, 1]] as f32 / 255.0;
                    let orig_b = input[[y, x, 2]] as f32 / 255.0;
                    let sr = 1.0 - (1.0 - orig_r) * (1.0 - gradient_buf[[y, x, 0]]);
                    let sg = 1.0 - (1.0 - orig_g) * (1.0 - gradient_buf[[y, x, 1]]);
                    let sb = 1.0 - (1.0 - orig_b) * (1.0 - gradient_buf[[y, x, 2]]);
                    result[[y, x, 0]] = ((orig_r * (1.0 - opacity) + sr * opacity) * 255.0).clamp(0.0, 255.0) as u8;
                    result[[y, x, 1]] = ((orig_g * (1.0 - opacity) + sg * opacity) * 255.0).clamp(0.0, 255.0) as u8;
                    result[[y, x, 2]] = ((orig_b * (1.0 - opacity) + sb * opacity) * 255.0).clamp(0.0, 255.0) as u8;
                    result[[y, x, 3]] = orig_a;
                }
            }
        }
        "overlay" => {
            for y in 0..height {
                for x in 0..width {
                    let orig_a = input[[y, x, 3]];
                    if orig_a == 0 { continue; }
                    let orig_r = input[[y, x, 0]] as f32 / 255.0;
                    let orig_g = input[[y, x, 1]] as f32 / 255.0;
                    let orig_b = input[[y, x, 2]] as f32 / 255.0;
                    let or = if orig_r < 0.5 { 2.0 * orig_r * gradient_buf[[y, x, 0]] } else { 1.0 - 2.0 * (1.0 - orig_r) * (1.0 - gradient_buf[[y, x, 0]]) };
                    let og = if orig_g < 0.5 { 2.0 * orig_g * gradient_buf[[y, x, 1]] } else { 1.0 - 2.0 * (1.0 - orig_g) * (1.0 - gradient_buf[[y, x, 1]]) };
                    let ob = if orig_b < 0.5 { 2.0 * orig_b * gradient_buf[[y, x, 2]] } else { 1.0 - 2.0 * (1.0 - orig_b) * (1.0 - gradient_buf[[y, x, 2]]) };
                    result[[y, x, 0]] = ((orig_r * (1.0 - opacity) + or * opacity) * 255.0).clamp(0.0, 255.0) as u8;
                    result[[y, x, 1]] = ((orig_g * (1.0 - opacity) + og * opacity) * 255.0).clamp(0.0, 255.0) as u8;
                    result[[y, x, 2]] = ((orig_b * (1.0 - opacity) + ob * opacity) * 255.0).clamp(0.0, 255.0) as u8;
                    result[[y, x, 3]] = orig_a;
                }
            }
        }
        _ => {
            // "normal" - simple alpha blend with gradient
            for y in 0..height {
                for x in 0..width {
                    let orig_a = input[[y, x, 3]];
                    if orig_a == 0 { continue; }
                    let orig_r = input[[y, x, 0]] as f32 / 255.0;
                    let orig_g = input[[y, x, 1]] as f32 / 255.0;
                    let orig_b = input[[y, x, 2]] as f32 / 255.0;
                    result[[y, x, 0]] = ((orig_r * (1.0 - opacity) + gradient_buf[[y, x, 0]] * opacity) * 255.0).clamp(0.0, 255.0) as u8;
                    result[[y, x, 1]] = ((orig_g * (1.0 - opacity) + gradient_buf[[y, x, 1]] * opacity) * 255.0).clamp(0.0, 255.0) as u8;
                    result[[y, x, 2]] = ((orig_b * (1.0 - opacity) + gradient_buf[[y, x, 2]] * opacity) * 255.0).clamp(0.0, 255.0) as u8;
                    result[[y, x, 3]] = orig_a;
                }
            }
        }
    }

    result.into_pyarray(py)
}

/// Apply gradient overlay to RGBA f32 image.
///
/// Same as gradient_overlay_rgba but for f32 images (0.0-1.0 range).
/// Stops format: [pos, r, g, b, pos, r, g, b, ...] where all values are 0.0-1.0
#[pyfunction]
#[pyo3(signature = (image, stops, style="linear", angle=90.0, scale_x=1.0, scale_y=1.0, offset_x=0.0, offset_y=0.0, reverse=false, opacity=1.0, blend_mode="normal"))]
pub fn gradient_overlay_rgba_f32<'py>(
    py: Python<'py>,
    image: PyReadonlyArray3<'py, f32>,
    stops: Vec<f32>,
    style: &str,
    angle: f32,
    scale_x: f32,
    scale_y: f32,
    offset_x: f32,
    offset_y: f32,
    reverse: bool,
    opacity: f32,
    blend_mode: &str,
) -> Bound<'py, PyArray3<f32>> {
    let input = image.as_array();
    let (height, width, _) = (input.shape()[0], input.shape()[1], input.shape()[2]);

    // Parse gradient stops (all values already 0.0-1.0 for f32)
    let mut gradient_stops: Vec<GradientStop> = Vec::new();
    for chunk in stops.chunks(4) {
        if chunk.len() == 4 {
            gradient_stops.push(GradientStop {
                position: chunk[0],
                r: chunk[1],
                g: chunk[2],
                b: chunk[3],
            });
        }
    }

    // Sort stops by position
    gradient_stops.sort_by(|a, b| a.position.partial_cmp(&b.position).unwrap_or(std::cmp::Ordering::Equal));

    // Default gradient if no stops provided
    if gradient_stops.is_empty() {
        gradient_stops.push(GradientStop { position: 0.0, r: 0.0, g: 0.0, b: 0.0 });
        gradient_stops.push(GradientStop { position: 1.0, r: 1.0, g: 1.0, b: 1.0 });
    }

    // Step 1: Generate gradient buffer
    let mut gradient_buf = Array3::<f32>::zeros((height, width, 3));
    for y in 0..height {
        for x in 0..width {
            let t = calculate_gradient_t(x, y, width, height, style, angle, scale_x, scale_y, offset_x, offset_y, reverse);
            let (r, g, b) = interpolate_gradient(&gradient_stops, t);
            gradient_buf[[y, x, 0]] = r;
            gradient_buf[[y, x, 1]] = g;
            gradient_buf[[y, x, 2]] = b;
        }
    }

    // Step 2: Blend with source using optimized per-mode loops
    let mut result = Array3::<f32>::zeros((height, width, 4));

    match blend_mode {
        "multiply" => {
            for y in 0..height {
                for x in 0..width {
                    let orig_a = input[[y, x, 3]];
                    if orig_a <= 0.0 { continue; }
                    let orig_r = input[[y, x, 0]];
                    let orig_g = input[[y, x, 1]];
                    let orig_b = input[[y, x, 2]];
                    let mr = orig_r * gradient_buf[[y, x, 0]];
                    let mg = orig_g * gradient_buf[[y, x, 1]];
                    let mb = orig_b * gradient_buf[[y, x, 2]];
                    result[[y, x, 0]] = orig_r * (1.0 - opacity) + mr * opacity;
                    result[[y, x, 1]] = orig_g * (1.0 - opacity) + mg * opacity;
                    result[[y, x, 2]] = orig_b * (1.0 - opacity) + mb * opacity;
                    result[[y, x, 3]] = orig_a;
                }
            }
        }
        "screen" => {
            for y in 0..height {
                for x in 0..width {
                    let orig_a = input[[y, x, 3]];
                    if orig_a <= 0.0 { continue; }
                    let orig_r = input[[y, x, 0]];
                    let orig_g = input[[y, x, 1]];
                    let orig_b = input[[y, x, 2]];
                    let sr = 1.0 - (1.0 - orig_r) * (1.0 - gradient_buf[[y, x, 0]]);
                    let sg = 1.0 - (1.0 - orig_g) * (1.0 - gradient_buf[[y, x, 1]]);
                    let sb = 1.0 - (1.0 - orig_b) * (1.0 - gradient_buf[[y, x, 2]]);
                    result[[y, x, 0]] = orig_r * (1.0 - opacity) + sr * opacity;
                    result[[y, x, 1]] = orig_g * (1.0 - opacity) + sg * opacity;
                    result[[y, x, 2]] = orig_b * (1.0 - opacity) + sb * opacity;
                    result[[y, x, 3]] = orig_a;
                }
            }
        }
        "overlay" => {
            for y in 0..height {
                for x in 0..width {
                    let orig_a = input[[y, x, 3]];
                    if orig_a <= 0.0 { continue; }
                    let orig_r = input[[y, x, 0]];
                    let orig_g = input[[y, x, 1]];
                    let orig_b = input[[y, x, 2]];
                    let or = if orig_r < 0.5 { 2.0 * orig_r * gradient_buf[[y, x, 0]] } else { 1.0 - 2.0 * (1.0 - orig_r) * (1.0 - gradient_buf[[y, x, 0]]) };
                    let og = if orig_g < 0.5 { 2.0 * orig_g * gradient_buf[[y, x, 1]] } else { 1.0 - 2.0 * (1.0 - orig_g) * (1.0 - gradient_buf[[y, x, 1]]) };
                    let ob = if orig_b < 0.5 { 2.0 * orig_b * gradient_buf[[y, x, 2]] } else { 1.0 - 2.0 * (1.0 - orig_b) * (1.0 - gradient_buf[[y, x, 2]]) };
                    result[[y, x, 0]] = orig_r * (1.0 - opacity) + or * opacity;
                    result[[y, x, 1]] = orig_g * (1.0 - opacity) + og * opacity;
                    result[[y, x, 2]] = orig_b * (1.0 - opacity) + ob * opacity;
                    result[[y, x, 3]] = orig_a;
                }
            }
        }
        _ => {
            // "normal" - simple alpha blend with gradient
            for y in 0..height {
                for x in 0..width {
                    let orig_a = input[[y, x, 3]];
                    if orig_a <= 0.0 { continue; }
                    result[[y, x, 0]] = input[[y, x, 0]] * (1.0 - opacity) + gradient_buf[[y, x, 0]] * opacity;
                    result[[y, x, 1]] = input[[y, x, 1]] * (1.0 - opacity) + gradient_buf[[y, x, 1]] * opacity;
                    result[[y, x, 2]] = input[[y, x, 2]] * (1.0 - opacity) + gradient_buf[[y, x, 2]] * opacity;
                    result[[y, x, 3]] = orig_a;
                }
            }
        }
    }

    result.into_pyarray(py)
}
