//! Lighting effects for layer styles.
//!
//! Provides:
//! - Bevel/Emboss - Creates 3D raised/sunken appearance
//! - Inner Glow - Glow effect inside the shape
//! - Outer Glow - Glow effect outside the shape

use ndarray::{Array2, Array3};
use numpy::{IntoPyArray, PyArray3, PyReadonlyArray3};
use pyo3::prelude::*;

use crate::filters::core::{blur_alpha_f32, dilate_alpha, erode_alpha, expand_canvas_f32};

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

/// Apply inner glow effect to RGBA image.
///
/// Creates a glow effect inside the shape edges.
///
/// # Arguments
/// * `image` - Source RGBA image
/// * `radius` - Glow blur radius
/// * `color` - Glow color (R, G, B)
/// * `opacity` - Glow opacity (0.0-1.0)
/// * `choke` - How much to contract the glow (0.0-1.0)
#[pyfunction]
#[pyo3(signature = (image, radius=10.0, color=(255, 255, 0), opacity=0.75, choke=0.0))]
pub fn inner_glow_rgba<'py>(
    py: Python<'py>,
    image: PyReadonlyArray3<'py, u8>,
    radius: f32,
    color: (u8, u8, u8),
    opacity: f32,
    choke: f32,
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

    // Extract alpha
    let mut alpha = Array2::<f32>::zeros((height, width));
    for y in 0..height {
        for x in 0..width {
            alpha[[y, x]] = input_f32[[y, x, 3]];
        }
    }

    // Create inner glow mask: erode alpha, blur, subtract from original
    let choke_radius = radius * choke;
    let eroded = if choke_radius > 0.0 {
        erode_alpha(&alpha, choke_radius)
    } else {
        alpha.clone()
    };

    // Blur the eroded alpha
    let blurred = blur_alpha_f32(&eroded, radius * (1.0 - choke * 0.5));

    // Inner glow = original alpha - blurred (inverted from edge)
    let mut glow_mask = Array2::<f32>::zeros((height, width));
    for y in 0..height {
        for x in 0..width {
            // Glow is strongest at edges, fading toward center
            let edge_dist = alpha[[y, x]] - blurred[[y, x]];
            glow_mask[[y, x]] = edge_dist.max(0.0) * alpha[[y, x]];
        }
    }

    // Compose result
    let mut result = Array3::<f32>::zeros((height, width, 4));

    // Copy original
    for y in 0..height {
        for x in 0..width {
            for c in 0..4 {
                result[[y, x, c]] = input_f32[[y, x, c]];
            }
        }
    }

    let glow_r = color.0 as f32 / 255.0;
    let glow_g = color.1 as f32 / 255.0;
    let glow_b = color.2 as f32 / 255.0;

    // Composite glow using "screen" blending (additive-like)
    for y in 0..height {
        for x in 0..width {
            let orig_a = input_f32[[y, x, 3]];
            if orig_a <= 0.0 {
                continue;
            }

            let glow_a = glow_mask[[y, x]] * opacity;
            if glow_a > 0.0 {
                // Screen blend: 1 - (1-a)(1-b)
                result[[y, x, 0]] = 1.0 - (1.0 - result[[y, x, 0]]) * (1.0 - glow_r * glow_a);
                result[[y, x, 1]] = 1.0 - (1.0 - result[[y, x, 1]]) * (1.0 - glow_g * glow_a);
                result[[y, x, 2]] = 1.0 - (1.0 - result[[y, x, 2]]) * (1.0 - glow_b * glow_a);
            }
        }
    }

    result.mapv(|v| (v.clamp(0.0, 1.0) * 255.0) as u8).into_pyarray(py)
}

/// Apply outer glow effect to RGBA image.
///
/// Creates a glow effect outside the shape edges.
///
/// # Arguments
/// * `image` - Source RGBA image
/// * `radius` - Glow blur radius
/// * `color` - Glow color (R, G, B)
/// * `opacity` - Glow opacity (0.0-1.0)
/// * `spread` - How much to expand the glow before blur (0.0-1.0)
/// * `expand` - Extra pixels to add around image
#[pyfunction]
#[pyo3(signature = (image, radius=10.0, color=(255, 255, 0), opacity=0.75, spread=0.0, expand=0))]
pub fn outer_glow_rgba<'py>(
    py: Python<'py>,
    image: PyReadonlyArray3<'py, u8>,
    radius: f32,
    color: (u8, u8, u8),
    opacity: f32,
    spread: f32,
    expand: usize,
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

    // Calculate expansion
    let required_expand = if expand > 0 {
        expand
    } else {
        (radius * 3.0).ceil() as usize + 2
    };

    let expanded = expand_canvas_f32(&input_f32, required_expand);
    let (new_h, new_w, _) = (expanded.shape()[0], expanded.shape()[1], expanded.shape()[2]);

    // Extract alpha
    let mut alpha = Array2::<f32>::zeros((new_h, new_w));
    for y in 0..new_h {
        for x in 0..new_w {
            alpha[[y, x]] = expanded[[y, x, 3]];
        }
    }

    // Apply spread (dilate before blur)
    let spread_radius = radius * spread;
    let spread_alpha = if spread_radius > 0.0 {
        dilate_alpha(&alpha, spread_radius)
    } else {
        alpha.clone()
    };

    // Blur the alpha
    let blurred = blur_alpha_f32(&spread_alpha, radius);

    // Create result with glow
    let mut result = Array3::<f32>::zeros((new_h, new_w, 4));

    let glow_r = color.0 as f32 / 255.0;
    let glow_g = color.1 as f32 / 255.0;
    let glow_b = color.2 as f32 / 255.0;

    // Draw glow first (outside only)
    for y in 0..new_h {
        for x in 0..new_w {
            // Glow is the blurred alpha minus original (outside only)
            let glow_a = (blurred[[y, x]] - alpha[[y, x]]).max(0.0) * opacity;
            if glow_a > 0.0 {
                result[[y, x, 0]] = glow_r;
                result[[y, x, 1]] = glow_g;
                result[[y, x, 2]] = glow_b;
                result[[y, x, 3]] = glow_a;
            }
        }
    }

    // Composite original on top
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

    result.mapv(|v| (v.clamp(0.0, 1.0) * 255.0) as u8).into_pyarray(py)
}

/// Apply inner shadow effect to RGBA image.
///
/// Creates a shadow inside the shape edges by:
/// 1. Inverting the alpha (shadow is where content isn't)
/// 2. Blurring the inverted alpha
/// 3. Offsetting the shadow
/// 4. Masking with original alpha (shadow only visible inside shape)
///
/// # Arguments
/// * `image` - Source RGBA image
/// * `offset_x` - Horizontal shadow offset
/// * `offset_y` - Vertical shadow offset
/// * `blur_radius` - Shadow blur radius
/// * `choke` - How much to contract before blur (0.0-1.0)
/// * `color` - Shadow color (R, G, B)
/// * `opacity` - Shadow opacity (0.0-1.0)
#[pyfunction]
#[pyo3(signature = (image, offset_x=2.0, offset_y=2.0, blur_radius=5.0, choke=0.0, color=(0, 0, 0), opacity=0.75))]
pub fn inner_shadow_rgba<'py>(
    py: Python<'py>,
    image: PyReadonlyArray3<'py, u8>,
    offset_x: f32,
    offset_y: f32,
    blur_radius: f32,
    choke: f32,
    color: (u8, u8, u8),
    opacity: f32,
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

    // Extract alpha
    let mut alpha = Array2::<f32>::zeros((height, width));
    for y in 0..height {
        for x in 0..width {
            alpha[[y, x]] = input_f32[[y, x, 3]];
        }
    }

    // Invert alpha for inner shadow (shadow comes from outside)
    let mut inverted = Array2::<f32>::zeros((height, width));
    for y in 0..height {
        for x in 0..width {
            inverted[[y, x]] = 1.0 - alpha[[y, x]];
        }
    }

    // Apply choke (erode the inverted alpha, which expands the shadow)
    let choke_radius = blur_radius * choke;
    let choked = if choke_radius > 0.0 {
        dilate_alpha(&inverted, choke_radius)
    } else {
        inverted
    };

    // Blur the shadow
    let blurred = blur_alpha_f32(&choked, blur_radius);

    // Create result - start with original
    let mut result = input_f32.clone();

    let shadow_r = color.0 as f32 / 255.0;
    let shadow_g = color.1 as f32 / 255.0;
    let shadow_b = color.2 as f32 / 255.0;

    let ox = offset_x.round() as isize;
    let oy = offset_y.round() as isize;

    // Apply shadow inside the shape
    for y in 0..height {
        for x in 0..width {
            let orig_a = alpha[[y, x]];
            if orig_a <= 0.0 {
                continue;
            }

            // Sample shadow alpha from offset position
            let sx = (x as isize - ox).clamp(0, width as isize - 1) as usize;
            let sy = (y as isize - oy).clamp(0, height as isize - 1) as usize;

            // Shadow is visible where blurred inverted alpha is > 0 AND inside original shape
            let shadow_a = blurred[[sy, sx]] * opacity * orig_a;

            if shadow_a > 0.0 {
                // Blend shadow color over original
                let out_a = shadow_a + result[[y, x, 3]] * (1.0 - shadow_a);
                if out_a > 0.0 {
                    result[[y, x, 0]] = (shadow_r * shadow_a + result[[y, x, 0]] * result[[y, x, 3]] * (1.0 - shadow_a)) / out_a;
                    result[[y, x, 1]] = (shadow_g * shadow_a + result[[y, x, 1]] * result[[y, x, 3]] * (1.0 - shadow_a)) / out_a;
                    result[[y, x, 2]] = (shadow_b * shadow_a + result[[y, x, 2]] * result[[y, x, 3]] * (1.0 - shadow_a)) / out_a;
                    result[[y, x, 3]] = out_a;
                }
            }
        }
    }

    result.mapv(|v| (v.clamp(0.0, 1.0) * 255.0) as u8).into_pyarray(py)
}

/// Apply inner shadow effect to f32 RGBA image.
#[pyfunction]
#[pyo3(signature = (image, offset_x=2.0, offset_y=2.0, blur_radius=5.0, choke=0.0, color=(0.0, 0.0, 0.0), opacity=0.75))]
pub fn inner_shadow_rgba_f32<'py>(
    py: Python<'py>,
    image: PyReadonlyArray3<'py, f32>,
    offset_x: f32,
    offset_y: f32,
    blur_radius: f32,
    choke: f32,
    color: (f32, f32, f32),
    opacity: f32,
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

    // Extract alpha
    let mut alpha = Array2::<f32>::zeros((height, width));
    for y in 0..height {
        for x in 0..width {
            alpha[[y, x]] = input_f32[[y, x, 3]];
        }
    }

    // Invert alpha
    let mut inverted = Array2::<f32>::zeros((height, width));
    for y in 0..height {
        for x in 0..width {
            inverted[[y, x]] = 1.0 - alpha[[y, x]];
        }
    }

    // Apply choke
    let choke_radius = blur_radius * choke;
    let choked = if choke_radius > 0.0 {
        dilate_alpha(&inverted, choke_radius)
    } else {
        inverted
    };

    // Blur
    let blurred = blur_alpha_f32(&choked, blur_radius);

    // Create result
    let mut result = input_f32.clone();

    let ox = offset_x.round() as isize;
    let oy = offset_y.round() as isize;

    for y in 0..height {
        for x in 0..width {
            let orig_a = alpha[[y, x]];
            if orig_a <= 0.0 {
                continue;
            }

            let sx = (x as isize - ox).clamp(0, width as isize - 1) as usize;
            let sy = (y as isize - oy).clamp(0, height as isize - 1) as usize;

            let shadow_a = blurred[[sy, sx]] * opacity * orig_a;

            if shadow_a > 0.0 {
                let out_a = shadow_a + result[[y, x, 3]] * (1.0 - shadow_a);
                if out_a > 0.0 {
                    result[[y, x, 0]] = (color.0 * shadow_a + result[[y, x, 0]] * result[[y, x, 3]] * (1.0 - shadow_a)) / out_a;
                    result[[y, x, 1]] = (color.1 * shadow_a + result[[y, x, 1]] * result[[y, x, 3]] * (1.0 - shadow_a)) / out_a;
                    result[[y, x, 2]] = (color.2 * shadow_a + result[[y, x, 2]] * result[[y, x, 3]] * (1.0 - shadow_a)) / out_a;
                    result[[y, x, 3]] = out_a;
                }
            }
        }
    }

    result.into_pyarray(py)
}

/// Apply color overlay effect to RGBA image.
///
/// Replaces all colors with a solid color while preserving alpha.
///
/// # Arguments
/// * `image` - Source RGBA image
/// * `color` - Overlay color (R, G, B)
/// * `opacity` - Overlay opacity (0.0-1.0)
#[pyfunction]
#[pyo3(signature = (image, color=(255, 0, 0), opacity=1.0))]
pub fn color_overlay_rgba<'py>(
    py: Python<'py>,
    image: PyReadonlyArray3<'py, u8>,
    color: (u8, u8, u8),
    opacity: f32,
) -> Bound<'py, PyArray3<u8>> {
    let input = image.as_array();
    let (height, width, _) = (input.shape()[0], input.shape()[1], input.shape()[2]);

    let mut result = Array3::<u8>::zeros((height, width, 4));

    for y in 0..height {
        for x in 0..width {
            let orig_a = input[[y, x, 3]] as f32 / 255.0;
            if orig_a <= 0.0 {
                continue;
            }

            // Blend overlay color with original based on opacity
            let blend_a = opacity;
            let orig_r = input[[y, x, 0]] as f32 / 255.0;
            let orig_g = input[[y, x, 1]] as f32 / 255.0;
            let orig_b = input[[y, x, 2]] as f32 / 255.0;
            let overlay_r = color.0 as f32 / 255.0;
            let overlay_g = color.1 as f32 / 255.0;
            let overlay_b = color.2 as f32 / 255.0;

            // Linear blend between original and overlay color
            let final_r = orig_r * (1.0 - blend_a) + overlay_r * blend_a;
            let final_g = orig_g * (1.0 - blend_a) + overlay_g * blend_a;
            let final_b = orig_b * (1.0 - blend_a) + overlay_b * blend_a;

            result[[y, x, 0]] = (final_r * 255.0) as u8;
            result[[y, x, 1]] = (final_g * 255.0) as u8;
            result[[y, x, 2]] = (final_b * 255.0) as u8;
            result[[y, x, 3]] = input[[y, x, 3]]; // Preserve alpha
        }
    }

    result.into_pyarray(py)
}

/// Apply color overlay effect to f32 RGBA image.
#[pyfunction]
#[pyo3(signature = (image, color=(1.0, 0.0, 0.0), opacity=1.0))]
pub fn color_overlay_rgba_f32<'py>(
    py: Python<'py>,
    image: PyReadonlyArray3<'py, f32>,
    color: (f32, f32, f32),
    opacity: f32,
) -> Bound<'py, PyArray3<f32>> {
    let input = image.as_array();
    let (height, width, _) = (input.shape()[0], input.shape()[1], input.shape()[2]);

    let mut result = Array3::<f32>::zeros((height, width, 4));

    for y in 0..height {
        for x in 0..width {
            let orig_a = input[[y, x, 3]];
            if orig_a <= 0.0 {
                continue;
            }

            let blend_a = opacity;

            result[[y, x, 0]] = input[[y, x, 0]] * (1.0 - blend_a) + color.0 * blend_a;
            result[[y, x, 1]] = input[[y, x, 1]] * (1.0 - blend_a) + color.1 * blend_a;
            result[[y, x, 2]] = input[[y, x, 2]] * (1.0 - blend_a) + color.2 * blend_a;
            result[[y, x, 3]] = orig_a;
        }
    }

    result.into_pyarray(py)
}
