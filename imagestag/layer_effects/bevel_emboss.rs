//! Bevel and Emboss layer effect.
//!
//! Creates a 3D raised or sunken appearance using highlights and shadows.
//!
//! Co-located with:
//! - bevel_emboss.py (Python wrapper)
//! - bevel_emboss.js (JavaScript wrapper)

use ndarray::{Array2, Array3};
use numpy::{IntoPyArray, PyArray3, PyReadonlyArray3};
use pyo3::prelude::*;

use crate::filters::core::{blur_alpha_f32, expand_canvas_f32};

/// Apply bevel and emboss effect to RGBA image.
///
/// Creates a 3D raised or sunken appearance using highlights and shadows.
///
/// # Arguments
/// * `image` - Source RGBA image
/// * `depth` - Depth of the bevel effect in pixels
/// * `angle` - Light source angle in degrees (0 = right, 90 = top)
/// * `altitude` - Light altitude in degrees (0-90)
/// * `highlight_color` - Highlight color (R, G, B)
/// * `highlight_opacity` - Highlight opacity (0.0-1.0)
/// * `shadow_color` - Shadow color (R, G, B)
/// * `shadow_opacity` - Shadow opacity (0.0-1.0)
/// * `style` - "outer_bevel", "inner_bevel", "emboss", "pillow_emboss"
#[pyfunction]
#[pyo3(signature = (image, depth=3.0, angle=120.0, altitude=30.0, highlight_color=(255, 255, 255), highlight_opacity=0.75, shadow_color=(0, 0, 0), shadow_opacity=0.75, style="inner_bevel"))]
pub fn bevel_emboss_rgba<'py>(
    py: Python<'py>,
    image: PyReadonlyArray3<'py, u8>,
    depth: f32,
    angle: f32,
    altitude: f32,
    highlight_color: (u8, u8, u8),
    highlight_opacity: f32,
    shadow_color: (u8, u8, u8),
    shadow_opacity: f32,
    style: &str,
) -> Bound<'py, PyArray3<u8>> {
    let input = image.as_array();
    let (height, width, _) = (input.shape()[0], input.shape()[1], input.shape()[2]);

    // Convert to f32
    let mut input_f32 = Array3::<f32>::zeros((height, width, 4));
    for y in 0..height {
        for x in 0..width {
            input_f32[[y, x, 0]] = input[[y, x, 0]] as f32 / 255.0;
            input_f32[[y, x, 1]] = input[[y, x, 1]] as f32 / 255.0;
            input_f32[[y, x, 2]] = input[[y, x, 2]] as f32 / 255.0;
            input_f32[[y, x, 3]] = input[[y, x, 3]] as f32 / 255.0;
        }
    }

    // Expand canvas for outer effects
    let is_outer = style == "outer_bevel";
    let expand = if is_outer { (depth.ceil() as usize) + 2 } else { 0 };
    let expanded = if expand > 0 {
        expand_canvas_f32(&input_f32, expand)
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

    // Calculate light direction from angle
    let angle_rad = angle.to_radians();
    let dx = angle_rad.cos();
    let dy = -angle_rad.sin(); // Negative because Y increases downward

    // Create bump map by computing gradient of alpha
    let mut bump_x = Array2::<f32>::zeros((new_h, new_w));
    let mut bump_y = Array2::<f32>::zeros((new_h, new_w));

    for y in 1..new_h - 1 {
        for x in 1..new_w - 1 {
            bump_x[[y, x]] = (alpha[[y, x + 1]] - alpha[[y, x - 1]]) / 2.0;
            bump_y[[y, x]] = (alpha[[y + 1, x]] - alpha[[y - 1, x]]) / 2.0;
        }
    }

    // Blur the bump map for smoother effect
    let bump_x_blur = blur_alpha_f32(&bump_x, depth * 0.5);
    let bump_y_blur = blur_alpha_f32(&bump_y, depth * 0.5);

    // Calculate lighting contribution
    let mut result = Array3::<f32>::zeros((new_h, new_w, 4));

    // Copy original first
    for y in 0..new_h {
        for x in 0..new_w {
            for c in 0..4 {
                result[[y, x, c]] = expanded[[y, x, c]];
            }
        }
    }

    let hl_r = highlight_color.0 as f32 / 255.0;
    let hl_g = highlight_color.1 as f32 / 255.0;
    let hl_b = highlight_color.2 as f32 / 255.0;
    let sh_r = shadow_color.0 as f32 / 255.0;
    let sh_g = shadow_color.1 as f32 / 255.0;
    let sh_b = shadow_color.2 as f32 / 255.0;

    for y in 0..new_h {
        for x in 0..new_w {
            let orig_a = expanded[[y, x, 3]];
            if orig_a <= 0.0 && !is_outer {
                continue;
            }

            // Compute lighting intensity
            let bx = bump_x_blur[[y, x]] * depth;
            let by = bump_y_blur[[y, x]] * depth;
            let intensity = bx * dx + by * dy;

            if intensity > 0.0 {
                // Highlight
                let hl_a = intensity.min(1.0) * highlight_opacity * orig_a;
                if hl_a > 0.0 {
                    let src_a = hl_a;
                    let dst_a = result[[y, x, 3]];
                    let out_a = src_a + dst_a * (1.0 - src_a);
                    if out_a > 0.0 {
                        result[[y, x, 0]] = (hl_r * src_a + result[[y, x, 0]] * dst_a * (1.0 - src_a)) / out_a;
                        result[[y, x, 1]] = (hl_g * src_a + result[[y, x, 1]] * dst_a * (1.0 - src_a)) / out_a;
                        result[[y, x, 2]] = (hl_b * src_a + result[[y, x, 2]] * dst_a * (1.0 - src_a)) / out_a;
                        result[[y, x, 3]] = out_a;
                    }
                }
            } else if intensity < 0.0 {
                // Shadow
                let sh_a = (-intensity).min(1.0) * shadow_opacity * orig_a;
                if sh_a > 0.0 {
                    let src_a = sh_a;
                    let dst_a = result[[y, x, 3]];
                    let out_a = src_a + dst_a * (1.0 - src_a);
                    if out_a > 0.0 {
                        result[[y, x, 0]] = (sh_r * src_a + result[[y, x, 0]] * dst_a * (1.0 - src_a)) / out_a;
                        result[[y, x, 1]] = (sh_g * src_a + result[[y, x, 1]] * dst_a * (1.0 - src_a)) / out_a;
                        result[[y, x, 2]] = (sh_b * src_a + result[[y, x, 2]] * dst_a * (1.0 - src_a)) / out_a;
                        result[[y, x, 3]] = out_a;
                    }
                }
            }
        }
    }

    result.mapv(|v| (v.clamp(0.0, 1.0) * 255.0) as u8).into_pyarray(py)
}

/// Apply bevel and emboss effect to f32 RGBA image.
#[pyfunction]
#[pyo3(signature = (image, depth=3.0, angle=120.0, altitude=30.0, highlight_color=(1.0, 1.0, 1.0), highlight_opacity=0.75, shadow_color=(0.0, 0.0, 0.0), shadow_opacity=0.75, style="inner_bevel"))]
#[allow(unused_variables)]
pub fn bevel_emboss_rgba_f32<'py>(
    py: Python<'py>,
    image: PyReadonlyArray3<'py, f32>,
    depth: f32,
    angle: f32,
    altitude: f32,
    highlight_color: (f32, f32, f32),
    highlight_opacity: f32,
    shadow_color: (f32, f32, f32),
    shadow_opacity: f32,
    style: &str,
) -> Bound<'py, PyArray3<f32>> {
    let input = image.as_array();
    let (height, width, _) = (input.shape()[0], input.shape()[1], input.shape()[2]);

    // Clone input
    let mut input_f32 = Array3::<f32>::zeros((height, width, 4));
    for y in 0..height {
        for x in 0..width {
            for c in 0..4 {
                input_f32[[y, x, c]] = input[[y, x, c]];
            }
        }
    }

    // Expand canvas for outer effects
    let is_outer = style == "outer_bevel";
    let expand = if is_outer { (depth.ceil() as usize) + 2 } else { 0 };
    let expanded = if expand > 0 {
        expand_canvas_f32(&input_f32, expand)
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

    // Calculate light direction
    let angle_rad = angle.to_radians();
    let dx = angle_rad.cos();
    let dy = -angle_rad.sin();

    // Create bump map
    let mut bump_x = Array2::<f32>::zeros((new_h, new_w));
    let mut bump_y = Array2::<f32>::zeros((new_h, new_w));

    for y in 1..new_h - 1 {
        for x in 1..new_w - 1 {
            bump_x[[y, x]] = (alpha[[y, x + 1]] - alpha[[y, x - 1]]) / 2.0;
            bump_y[[y, x]] = (alpha[[y + 1, x]] - alpha[[y - 1, x]]) / 2.0;
        }
    }

    let bump_x_blur = blur_alpha_f32(&bump_x, depth * 0.5);
    let bump_y_blur = blur_alpha_f32(&bump_y, depth * 0.5);

    let mut result = Array3::<f32>::zeros((new_h, new_w, 4));

    for y in 0..new_h {
        for x in 0..new_w {
            for c in 0..4 {
                result[[y, x, c]] = expanded[[y, x, c]];
            }
        }
    }

    for y in 0..new_h {
        for x in 0..new_w {
            let orig_a = expanded[[y, x, 3]];
            if orig_a <= 0.0 && !is_outer {
                continue;
            }

            let bx = bump_x_blur[[y, x]] * depth;
            let by = bump_y_blur[[y, x]] * depth;
            let intensity = bx * dx + by * dy;

            if intensity > 0.0 {
                let hl_a = intensity.min(1.0) * highlight_opacity * orig_a;
                if hl_a > 0.0 {
                    let src_a = hl_a;
                    let dst_a = result[[y, x, 3]];
                    let out_a = src_a + dst_a * (1.0 - src_a);
                    if out_a > 0.0 {
                        result[[y, x, 0]] = (highlight_color.0 * src_a + result[[y, x, 0]] * dst_a * (1.0 - src_a)) / out_a;
                        result[[y, x, 1]] = (highlight_color.1 * src_a + result[[y, x, 1]] * dst_a * (1.0 - src_a)) / out_a;
                        result[[y, x, 2]] = (highlight_color.2 * src_a + result[[y, x, 2]] * dst_a * (1.0 - src_a)) / out_a;
                        result[[y, x, 3]] = out_a;
                    }
                }
            } else if intensity < 0.0 {
                let sh_a = (-intensity).min(1.0) * shadow_opacity * orig_a;
                if sh_a > 0.0 {
                    let src_a = sh_a;
                    let dst_a = result[[y, x, 3]];
                    let out_a = src_a + dst_a * (1.0 - src_a);
                    if out_a > 0.0 {
                        result[[y, x, 0]] = (shadow_color.0 * src_a + result[[y, x, 0]] * dst_a * (1.0 - src_a)) / out_a;
                        result[[y, x, 1]] = (shadow_color.1 * src_a + result[[y, x, 1]] * dst_a * (1.0 - src_a)) / out_a;
                        result[[y, x, 2]] = (shadow_color.2 * src_a + result[[y, x, 2]] * dst_a * (1.0 - src_a)) / out_a;
                        result[[y, x, 3]] = out_a;
                    }
                }
            }
        }
    }

    result.into_pyarray(py)
}
