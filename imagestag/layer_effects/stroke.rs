//! Stroke/outline filter for layer effects.
//!
//! Creates an outline effect around non-transparent areas by:
//! 1. Extracting the alpha channel
//! 2. Dilating to create the stroke area
//! 3. Subtracting original alpha (for outside stroke)
//! 4. Colorizing with stroke color
//!
//! Supports inside, outside, and center stroke positions.

use ndarray::{Array2, Array3};
use numpy::{IntoPyArray, PyArray3, PyReadonlyArray3};
use pyo3::prelude::*;

use crate::filters::core::{dilate_alpha, erode_alpha, expand_canvas_f32};

/// Stroke position relative to the shape edge.
#[derive(Clone, Copy, Debug)]
pub enum StrokePosition {
    Outside,
    Inside,
    Center,
}

impl StrokePosition {
    fn from_str(s: &str) -> Self {
        match s.to_lowercase().as_str() {
            "inside" => StrokePosition::Inside,
            "center" => StrokePosition::Center,
            _ => StrokePosition::Outside,
        }
    }
}

/// Apply stroke/outline effect to RGBA image.
///
/// # Arguments
/// * `image` - Source RGBA image (height, width, 4) as u8
/// * `width` - Stroke width in pixels
/// * `color` - Stroke color as (R, G, B) tuple (0-255)
/// * `opacity` - Stroke opacity (0.0-1.0)
/// * `position` - Stroke position: "outside", "inside", or "center"
/// * `expand` - Extra pixels to add around image for stroke overflow
///
/// # Returns
/// RGBA image with stroke effect
#[pyfunction]
#[pyo3(signature = (image, width=2.0, color=(0, 0, 0), opacity=1.0, position="outside", expand=0))]
pub fn stroke_rgba<'py>(
    py: Python<'py>,
    image: PyReadonlyArray3<'py, u8>,
    width: f32,
    color: (u8, u8, u8),
    opacity: f32,
    position: &str,
    expand: usize,
) -> Bound<'py, PyArray3<u8>> {
    let input = image.as_array();
    let (height, img_width, _) = (input.shape()[0], input.shape()[1], input.shape()[2]);
    let pos = StrokePosition::from_str(position);

    // Convert to f32 for processing
    let mut input_f32 = Array3::<f32>::zeros((height, img_width, 4));
    for y in 0..height {
        for x in 0..img_width {
            input_f32[[y, x, 0]] = input[[y, x, 0]] as f32 / 255.0;
            input_f32[[y, x, 1]] = input[[y, x, 1]] as f32 / 255.0;
            input_f32[[y, x, 2]] = input[[y, x, 2]] as f32 / 255.0;
            input_f32[[y, x, 3]] = input[[y, x, 3]] as f32 / 255.0;
        }
    }

    // Calculate expansion needed for outside stroke
    let required_expand = match pos {
        StrokePosition::Outside | StrokePosition::Center => {
            if expand > 0 {
                expand
            } else {
                (width.ceil() as usize) + 2
            }
        }
        StrokePosition::Inside => expand,
    };

    // Expand canvas if needed
    let expanded = if required_expand > 0 {
        expand_canvas_f32(&input_f32, required_expand)
    } else {
        input_f32.clone()
    };

    let (new_h, new_w, _) = (expanded.shape()[0], expanded.shape()[1], expanded.shape()[2]);

    // Extract alpha channel
    let mut alpha = Array2::<f32>::zeros((new_h, new_w));
    for y in 0..new_h {
        for x in 0..new_w {
            alpha[[y, x]] = expanded[[y, x, 3]];
        }
    }

    // Create stroke mask based on position
    let stroke_mask = match pos {
        StrokePosition::Outside => {
            // Dilate - original = stroke area
            let dilated = dilate_alpha(&alpha, width);
            let mut mask = Array2::<f32>::zeros((new_h, new_w));
            for y in 0..new_h {
                for x in 0..new_w {
                    mask[[y, x]] = (dilated[[y, x]] - alpha[[y, x]]).max(0.0);
                }
            }
            mask
        }
        StrokePosition::Inside => {
            // Original - eroded = stroke area
            let eroded = erode_alpha(&alpha, width);
            let mut mask = Array2::<f32>::zeros((new_h, new_w));
            for y in 0..new_h {
                for x in 0..new_w {
                    mask[[y, x]] = (alpha[[y, x]] - eroded[[y, x]]).max(0.0);
                }
            }
            mask
        }
        StrokePosition::Center => {
            // Dilate half - erode half
            let half_width = width / 2.0;
            let dilated = dilate_alpha(&alpha, half_width);
            let eroded = erode_alpha(&alpha, half_width);
            let mut mask = Array2::<f32>::zeros((new_h, new_w));
            for y in 0..new_h {
                for x in 0..new_w {
                    mask[[y, x]] = (dilated[[y, x]] - eroded[[y, x]]).max(0.0);
                }
            }
            mask
        }
    };

    // Create result
    let mut result = Array3::<f32>::zeros((new_h, new_w, 4));

    let stroke_r = color.0 as f32 / 255.0;
    let stroke_g = color.1 as f32 / 255.0;
    let stroke_b = color.2 as f32 / 255.0;

    // Draw stroke first (behind original for outside)
    for y in 0..new_h {
        for x in 0..new_w {
            let stroke_a = stroke_mask[[y, x]] * opacity;
            if stroke_a > 0.0 {
                result[[y, x, 0]] = stroke_r;
                result[[y, x, 1]] = stroke_g;
                result[[y, x, 2]] = stroke_b;
                result[[y, x, 3]] = stroke_a;
            }
        }
    }

    // Composite original on top (for outside/center stroke)
    // For inside stroke, we keep original visible
    match pos {
        StrokePosition::Outside | StrokePosition::Center => {
            for y in 0..new_h {
                for x in 0..new_w {
                    let src_a = expanded[[y, x, 3]];
                    if src_a <= 0.0 {
                        continue;
                    }

                    let dst_a = result[[y, x, 3]];
                    let out_a = src_a + dst_a * (1.0 - src_a);

                    if out_a > 0.0 {
                        result[[y, x, 0]] = (expanded[[y, x, 0]] * src_a + result[[y, x, 0]] * dst_a * (1.0 - src_a)) / out_a;
                        result[[y, x, 1]] = (expanded[[y, x, 1]] * src_a + result[[y, x, 1]] * dst_a * (1.0 - src_a)) / out_a;
                        result[[y, x, 2]] = (expanded[[y, x, 2]] * src_a + result[[y, x, 2]] * dst_a * (1.0 - src_a)) / out_a;
                        result[[y, x, 3]] = out_a;
                    }
                }
            }
        }
        StrokePosition::Inside => {
            // For inside stroke, composite stroke over original
            for y in 0..new_h {
                for x in 0..new_w {
                    let orig_a = expanded[[y, x, 3]];
                    if orig_a <= 0.0 {
                        continue;
                    }

                    let stroke_a = result[[y, x, 3]];
                    if stroke_a <= 0.0 {
                        // No stroke here, just copy original
                        result[[y, x, 0]] = expanded[[y, x, 0]];
                        result[[y, x, 1]] = expanded[[y, x, 1]];
                        result[[y, x, 2]] = expanded[[y, x, 2]];
                        result[[y, x, 3]] = orig_a;
                    } else {
                        // Composite stroke over original (stroke is on top for inside)
                        let out_a = stroke_a + orig_a * (1.0 - stroke_a);
                        if out_a > 0.0 {
                            result[[y, x, 0]] = (result[[y, x, 0]] * stroke_a + expanded[[y, x, 0]] * orig_a * (1.0 - stroke_a)) / out_a;
                            result[[y, x, 1]] = (result[[y, x, 1]] * stroke_a + expanded[[y, x, 1]] * orig_a * (1.0 - stroke_a)) / out_a;
                            result[[y, x, 2]] = (result[[y, x, 2]] * stroke_a + expanded[[y, x, 2]] * orig_a * (1.0 - stroke_a)) / out_a;
                            result[[y, x, 3]] = out_a;
                        }
                    }
                }
            }
        }
    }

    // Convert back to u8
    result.mapv(|v| (v.clamp(0.0, 1.0) * 255.0) as u8).into_pyarray(py)
}

/// Apply stroke/outline effect to f32 RGBA image.
#[pyfunction]
#[pyo3(signature = (image, width=2.0, color=(0.0, 0.0, 0.0), opacity=1.0, position="outside", expand=0))]
pub fn stroke_rgba_f32<'py>(
    py: Python<'py>,
    image: PyReadonlyArray3<'py, f32>,
    width: f32,
    color: (f32, f32, f32),
    opacity: f32,
    position: &str,
    expand: usize,
) -> Bound<'py, PyArray3<f32>> {
    let input = image.as_array();
    let (height, img_width, _) = (input.shape()[0], input.shape()[1], input.shape()[2]);
    let pos = StrokePosition::from_str(position);

    // Clone input
    let mut input_f32 = Array3::<f32>::zeros((height, img_width, 4));
    for y in 0..height {
        for x in 0..img_width {
            for c in 0..4 {
                input_f32[[y, x, c]] = input[[y, x, c]];
            }
        }
    }

    // Calculate expansion
    let required_expand = match pos {
        StrokePosition::Outside | StrokePosition::Center => {
            if expand > 0 { expand } else { (width.ceil() as usize) + 2 }
        }
        StrokePosition::Inside => expand,
    };

    let expanded = if required_expand > 0 {
        expand_canvas_f32(&input_f32, required_expand)
    } else {
        input_f32
    };

    let (new_h, new_w, _) = (expanded.shape()[0], expanded.shape()[1], expanded.shape()[2]);

    // Extract alpha
    let mut alpha = Array2::<f32>::zeros((new_h, new_w));
    for y in 0..new_h {
        for x in 0..new_w {
            alpha[[y, x]] = expanded[[y, x, 3]];
        }
    }

    // Create stroke mask
    let stroke_mask = match pos {
        StrokePosition::Outside => {
            let dilated = dilate_alpha(&alpha, width);
            let mut mask = Array2::<f32>::zeros((new_h, new_w));
            for y in 0..new_h {
                for x in 0..new_w {
                    mask[[y, x]] = (dilated[[y, x]] - alpha[[y, x]]).max(0.0);
                }
            }
            mask
        }
        StrokePosition::Inside => {
            let eroded = erode_alpha(&alpha, width);
            let mut mask = Array2::<f32>::zeros((new_h, new_w));
            for y in 0..new_h {
                for x in 0..new_w {
                    mask[[y, x]] = (alpha[[y, x]] - eroded[[y, x]]).max(0.0);
                }
            }
            mask
        }
        StrokePosition::Center => {
            let half_width = width / 2.0;
            let dilated = dilate_alpha(&alpha, half_width);
            let eroded = erode_alpha(&alpha, half_width);
            let mut mask = Array2::<f32>::zeros((new_h, new_w));
            for y in 0..new_h {
                for x in 0..new_w {
                    mask[[y, x]] = (dilated[[y, x]] - eroded[[y, x]]).max(0.0);
                }
            }
            mask
        }
    };

    // Create result and apply stroke
    let mut result = Array3::<f32>::zeros((new_h, new_w, 4));

    for y in 0..new_h {
        for x in 0..new_w {
            let stroke_a = stroke_mask[[y, x]] * opacity;
            if stroke_a > 0.0 {
                result[[y, x, 0]] = color.0;
                result[[y, x, 1]] = color.1;
                result[[y, x, 2]] = color.2;
                result[[y, x, 3]] = stroke_a;
            }
        }
    }

    // Composite original
    match pos {
        StrokePosition::Outside | StrokePosition::Center => {
            for y in 0..new_h {
                for x in 0..new_w {
                    let src_a = expanded[[y, x, 3]];
                    if src_a <= 0.0 { continue; }

                    let dst_a = result[[y, x, 3]];
                    let out_a = src_a + dst_a * (1.0 - src_a);

                    if out_a > 0.0 {
                        result[[y, x, 0]] = (expanded[[y, x, 0]] * src_a + result[[y, x, 0]] * dst_a * (1.0 - src_a)) / out_a;
                        result[[y, x, 1]] = (expanded[[y, x, 1]] * src_a + result[[y, x, 1]] * dst_a * (1.0 - src_a)) / out_a;
                        result[[y, x, 2]] = (expanded[[y, x, 2]] * src_a + result[[y, x, 2]] * dst_a * (1.0 - src_a)) / out_a;
                        result[[y, x, 3]] = out_a;
                    }
                }
            }
        }
        StrokePosition::Inside => {
            for y in 0..new_h {
                for x in 0..new_w {
                    let orig_a = expanded[[y, x, 3]];
                    if orig_a <= 0.0 { continue; }

                    let stroke_a = result[[y, x, 3]];
                    if stroke_a <= 0.0 {
                        result[[y, x, 0]] = expanded[[y, x, 0]];
                        result[[y, x, 1]] = expanded[[y, x, 1]];
                        result[[y, x, 2]] = expanded[[y, x, 2]];
                        result[[y, x, 3]] = orig_a;
                    } else {
                        let out_a = stroke_a + orig_a * (1.0 - stroke_a);
                        if out_a > 0.0 {
                            result[[y, x, 0]] = (result[[y, x, 0]] * stroke_a + expanded[[y, x, 0]] * orig_a * (1.0 - stroke_a)) / out_a;
                            result[[y, x, 1]] = (result[[y, x, 1]] * stroke_a + expanded[[y, x, 1]] * orig_a * (1.0 - stroke_a)) / out_a;
                            result[[y, x, 2]] = (result[[y, x, 2]] * stroke_a + expanded[[y, x, 2]] * orig_a * (1.0 - stroke_a)) / out_a;
                            result[[y, x, 3]] = out_a;
                        }
                    }
                }
            }
        }
    }

    result.into_pyarray(py)
}

/// Get stroke-only layer (no original content composited).
///
/// Returns just the stroke effect without the original image.
/// Useful for baked SVG export where the stroke is rendered as a separate layer.
///
/// # Arguments
/// Same as stroke_rgba
///
/// # Returns
/// RGBA image with ONLY the stroke (original NOT composited)
#[pyfunction]
#[pyo3(signature = (image, width=2.0, color=(0, 0, 0), opacity=1.0, position="outside", expand=0))]
pub fn stroke_only_rgba<'py>(
    py: Python<'py>,
    image: PyReadonlyArray3<'py, u8>,
    width: f32,
    color: (u8, u8, u8),
    opacity: f32,
    position: &str,
    expand: usize,
) -> Bound<'py, PyArray3<u8>> {
    let input = image.as_array();
    let (height, img_width, _) = (input.shape()[0], input.shape()[1], input.shape()[2]);
    let pos = StrokePosition::from_str(position);

    // Convert to f32
    let mut input_f32 = Array3::<f32>::zeros((height, img_width, 4));
    for y in 0..height {
        for x in 0..img_width {
            input_f32[[y, x, 0]] = input[[y, x, 0]] as f32 / 255.0;
            input_f32[[y, x, 1]] = input[[y, x, 1]] as f32 / 255.0;
            input_f32[[y, x, 2]] = input[[y, x, 2]] as f32 / 255.0;
            input_f32[[y, x, 3]] = input[[y, x, 3]] as f32 / 255.0;
        }
    }

    // Calculate expansion
    let required_expand = match pos {
        StrokePosition::Outside | StrokePosition::Center => {
            if expand > 0 { expand } else { (width.ceil() as usize) + 2 }
        }
        StrokePosition::Inside => expand,
    };

    let expanded = if required_expand > 0 {
        expand_canvas_f32(&input_f32, required_expand)
    } else {
        input_f32.clone()
    };

    let (new_h, new_w, _) = (expanded.shape()[0], expanded.shape()[1], expanded.shape()[2]);

    // Extract alpha
    let mut alpha = Array2::<f32>::zeros((new_h, new_w));
    for y in 0..new_h {
        for x in 0..new_w {
            alpha[[y, x]] = expanded[[y, x, 3]];
        }
    }

    // Create stroke mask
    let stroke_mask = match pos {
        StrokePosition::Outside => {
            let dilated = dilate_alpha(&alpha, width);
            let mut mask = Array2::<f32>::zeros((new_h, new_w));
            for y in 0..new_h {
                for x in 0..new_w {
                    mask[[y, x]] = (dilated[[y, x]] - alpha[[y, x]]).max(0.0);
                }
            }
            mask
        }
        StrokePosition::Inside => {
            let eroded = erode_alpha(&alpha, width);
            let mut mask = Array2::<f32>::zeros((new_h, new_w));
            for y in 0..new_h {
                for x in 0..new_w {
                    mask[[y, x]] = (alpha[[y, x]] - eroded[[y, x]]).max(0.0);
                }
            }
            mask
        }
        StrokePosition::Center => {
            let half_width = width / 2.0;
            let dilated = dilate_alpha(&alpha, half_width);
            let eroded = erode_alpha(&alpha, half_width);
            let mut mask = Array2::<f32>::zeros((new_h, new_w));
            for y in 0..new_h {
                for x in 0..new_w {
                    mask[[y, x]] = (dilated[[y, x]] - eroded[[y, x]]).max(0.0);
                }
            }
            mask
        }
    };

    // Create stroke-only result (no original composited)
    let mut result = Array3::<f32>::zeros((new_h, new_w, 4));

    let stroke_r = color.0 as f32 / 255.0;
    let stroke_g = color.1 as f32 / 255.0;
    let stroke_b = color.2 as f32 / 255.0;

    for y in 0..new_h {
        for x in 0..new_w {
            let stroke_a = stroke_mask[[y, x]] * opacity;
            result[[y, x, 0]] = stroke_r;
            result[[y, x, 1]] = stroke_g;
            result[[y, x, 2]] = stroke_b;
            result[[y, x, 3]] = stroke_a;
        }
    }

    // NOTE: No compositing step - return stroke layer only

    result.mapv(|v| (v.clamp(0.0, 1.0) * 255.0) as u8).into_pyarray(py)
}

/// Get stroke-only layer for f32 RGBA image.
#[pyfunction]
#[pyo3(signature = (image, width=2.0, color=(0.0, 0.0, 0.0), opacity=1.0, position="outside", expand=0))]
pub fn stroke_only_rgba_f32<'py>(
    py: Python<'py>,
    image: PyReadonlyArray3<'py, f32>,
    width: f32,
    color: (f32, f32, f32),
    opacity: f32,
    position: &str,
    expand: usize,
) -> Bound<'py, PyArray3<f32>> {
    let input = image.as_array();
    let (height, img_width, _) = (input.shape()[0], input.shape()[1], input.shape()[2]);
    let pos = StrokePosition::from_str(position);

    let mut input_f32 = Array3::<f32>::zeros((height, img_width, 4));
    for y in 0..height {
        for x in 0..img_width {
            for c in 0..4 {
                input_f32[[y, x, c]] = input[[y, x, c]];
            }
        }
    }

    let required_expand = match pos {
        StrokePosition::Outside | StrokePosition::Center => {
            if expand > 0 { expand } else { (width.ceil() as usize) + 2 }
        }
        StrokePosition::Inside => expand,
    };

    let expanded = if required_expand > 0 {
        expand_canvas_f32(&input_f32, required_expand)
    } else {
        input_f32
    };

    let (new_h, new_w, _) = (expanded.shape()[0], expanded.shape()[1], expanded.shape()[2]);

    let mut alpha = Array2::<f32>::zeros((new_h, new_w));
    for y in 0..new_h {
        for x in 0..new_w {
            alpha[[y, x]] = expanded[[y, x, 3]];
        }
    }

    let stroke_mask = match pos {
        StrokePosition::Outside => {
            let dilated = dilate_alpha(&alpha, width);
            let mut mask = Array2::<f32>::zeros((new_h, new_w));
            for y in 0..new_h {
                for x in 0..new_w {
                    mask[[y, x]] = (dilated[[y, x]] - alpha[[y, x]]).max(0.0);
                }
            }
            mask
        }
        StrokePosition::Inside => {
            let eroded = erode_alpha(&alpha, width);
            let mut mask = Array2::<f32>::zeros((new_h, new_w));
            for y in 0..new_h {
                for x in 0..new_w {
                    mask[[y, x]] = (alpha[[y, x]] - eroded[[y, x]]).max(0.0);
                }
            }
            mask
        }
        StrokePosition::Center => {
            let half_width = width / 2.0;
            let dilated = dilate_alpha(&alpha, half_width);
            let eroded = erode_alpha(&alpha, half_width);
            let mut mask = Array2::<f32>::zeros((new_h, new_w));
            for y in 0..new_h {
                for x in 0..new_w {
                    mask[[y, x]] = (dilated[[y, x]] - eroded[[y, x]]).max(0.0);
                }
            }
            mask
        }
    };

    let mut result = Array3::<f32>::zeros((new_h, new_w, 4));

    for y in 0..new_h {
        for x in 0..new_w {
            let stroke_a = stroke_mask[[y, x]] * opacity;
            result[[y, x, 0]] = color.0;
            result[[y, x, 1]] = color.1;
            result[[y, x, 2]] = color.2;
            result[[y, x, 3]] = stroke_a;
        }
    }

    result.into_pyarray(py)
}
