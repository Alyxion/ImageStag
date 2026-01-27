//! Gradient overlay layer effect.
//!
//! Fills the layer with a gradient while preserving the alpha channel.
//! Supports 5 gradient styles: linear, radial, angle, reflected, and diamond.

use ndarray::Array3;
use numpy::{IntoPyArray, PyArray3, PyReadonlyArray3};
use pyo3::prelude::*;

/// Gradient stop definition: position (0.0-1.0) and color (RGB).
#[derive(Clone, Debug)]
struct GradientStop {
    position: f32,
    r: f32,
    g: f32,
    b: f32,
}

/// Interpolate color at position t from gradient stops.
fn interpolate_gradient(stops: &[GradientStop], t: f32) -> (f32, f32, f32) {
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
fn calculate_gradient_t(
    x: usize,
    y: usize,
    width: usize,
    height: usize,
    style: &str,
    angle: f32,
    scale: f32,
    reverse: bool,
) -> f32 {
    let cx = width as f32 / 2.0;
    let cy = height as f32 / 2.0;
    let px = x as f32;
    let py = y as f32;

    let mut t = match style {
        "linear" => {
            // Linear gradient along angle
            let angle_rad = angle.to_radians();
            let dx = angle_rad.cos();
            let dy = -angle_rad.sin(); // Negative because Y increases downward

            // Project pixel onto gradient line through center
            let rx = px - cx;
            let ry = py - cy;
            let proj = rx * dx + ry * dy;

            // Normalize to [0, 1] based on image diagonal
            let max_dist = (cx * cx + cy * cy).sqrt();
            (proj / max_dist + 1.0) / 2.0
        }
        "radial" => {
            // Circular gradient from center
            let dx = px - cx;
            let dy = py - cy;
            let dist = (dx * dx + dy * dy).sqrt();
            let max_dist = (cx * cx + cy * cy).sqrt();
            dist / max_dist
        }
        "angle" => {
            // Angular gradient sweeping around center
            let dx = px - cx;
            let dy = py - cy;
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

            let rx = px - cx;
            let ry = py - cy;
            let proj = rx * dx + ry * dy;

            let max_dist = (cx * cx + cy * cy).sqrt();
            let linear_t = (proj / max_dist + 1.0) / 2.0;

            // Mirror: fold at 0.5
            (2.0 * (linear_t - 0.5)).abs()
        }
        "diamond" => {
            // Diamond-shaped gradient from center
            let dx = (px - cx).abs();
            let dy = (py - cy).abs();
            let dist = dx + dy; // Manhattan distance gives diamond shape
            let max_dist = cx + cy;
            dist / max_dist
        }
        _ => {
            // Default to linear if unknown style
            let angle_rad = angle.to_radians();
            let dx = angle_rad.cos();
            let dy = -angle_rad.sin();
            let rx = px - cx;
            let ry = py - cy;
            let proj = rx * dx + ry * dy;
            let max_dist = (cx * cx + cy * cy).sqrt();
            (proj / max_dist + 1.0) / 2.0
        }
    };

    // Apply scale
    if scale != 1.0 && scale > 0.0 {
        // Scale from center (0.5)
        t = 0.5 + (t - 0.5) / scale;
    }

    // Clamp to valid range after scaling
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
/// * `scale` - Scale factor (1.0 = 100%)
/// * `reverse` - Whether to reverse the gradient direction
/// * `opacity` - Effect opacity (0.0-1.0)
#[pyfunction]
#[pyo3(signature = (image, stops, style="linear", angle=90.0, scale=1.0, reverse=false, opacity=1.0))]
pub fn gradient_overlay_rgba<'py>(
    py: Python<'py>,
    image: PyReadonlyArray3<'py, u8>,
    stops: Vec<f32>,
    style: &str,
    angle: f32,
    scale: f32,
    reverse: bool,
    opacity: f32,
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

    let mut result = Array3::<u8>::zeros((height, width, 4));

    for y in 0..height {
        for x in 0..width {
            let orig_a = input[[y, x, 3]];
            if orig_a == 0 {
                continue;
            }

            // Calculate gradient position
            let t = calculate_gradient_t(x, y, width, height, style, angle, scale, reverse);

            // Get gradient color at this position
            let (grad_r, grad_g, grad_b) = interpolate_gradient(&gradient_stops, t);

            // Blend with original based on opacity
            let orig_r = input[[y, x, 0]] as f32 / 255.0;
            let orig_g = input[[y, x, 1]] as f32 / 255.0;
            let orig_b = input[[y, x, 2]] as f32 / 255.0;

            let final_r = orig_r * (1.0 - opacity) + grad_r * opacity;
            let final_g = orig_g * (1.0 - opacity) + grad_g * opacity;
            let final_b = orig_b * (1.0 - opacity) + grad_b * opacity;

            result[[y, x, 0]] = (final_r * 255.0).clamp(0.0, 255.0) as u8;
            result[[y, x, 1]] = (final_g * 255.0).clamp(0.0, 255.0) as u8;
            result[[y, x, 2]] = (final_b * 255.0).clamp(0.0, 255.0) as u8;
            result[[y, x, 3]] = orig_a; // Preserve alpha
        }
    }

    result.into_pyarray(py)
}

/// Apply gradient overlay to RGBA f32 image.
///
/// Same as gradient_overlay_rgba but for f32 images (0.0-1.0 range).
/// Stops format: [pos, r, g, b, pos, r, g, b, ...] where all values are 0.0-1.0
#[pyfunction]
#[pyo3(signature = (image, stops, style="linear", angle=90.0, scale=1.0, reverse=false, opacity=1.0))]
pub fn gradient_overlay_rgba_f32<'py>(
    py: Python<'py>,
    image: PyReadonlyArray3<'py, f32>,
    stops: Vec<f32>,
    style: &str,
    angle: f32,
    scale: f32,
    reverse: bool,
    opacity: f32,
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

    let mut result = Array3::<f32>::zeros((height, width, 4));

    for y in 0..height {
        for x in 0..width {
            let orig_a = input[[y, x, 3]];
            if orig_a <= 0.0 {
                continue;
            }

            // Calculate gradient position
            let t = calculate_gradient_t(x, y, width, height, style, angle, scale, reverse);

            // Get gradient color at this position
            let (grad_r, grad_g, grad_b) = interpolate_gradient(&gradient_stops, t);

            // Blend with original based on opacity
            let final_r = input[[y, x, 0]] * (1.0 - opacity) + grad_r * opacity;
            let final_g = input[[y, x, 1]] * (1.0 - opacity) + grad_g * opacity;
            let final_b = input[[y, x, 2]] * (1.0 - opacity) + grad_b * opacity;

            result[[y, x, 0]] = final_r;
            result[[y, x, 1]] = final_g;
            result[[y, x, 2]] = final_b;
            result[[y, x, 3]] = orig_a; // Preserve alpha
        }
    }

    result.into_pyarray(py)
}
