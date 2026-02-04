#!/usr/bin/env python3
"""
Generate sample images for all layer effects.

Outputs comparison images for each effect:
- _rust.png: Effect applied via Rust extension
- _svg.png: Effect applied via SVG filter/defs, rendered to PNG
- _baked.svg: SVG with Rust effect baked as embedded raster image
- .svg: The SVG file with filter/defs applied

The "baked" approach embeds the Rust-rendered effect directly into the SVG
for 100% fidelity. Depending on the effect type:
- Underlay effects (drop shadow, outer glow): Effect rendered as image UNDER original SVG
- Overlay effects (stroke): Effect rendered as image OVER original SVG
- Replacement effects (inner shadow, overlays, bevel): Original content replaced with rasterized result

Output directory: tmp/effect_samples/

Usage:
    poetry run python scripts/generate_effect_samples.py
"""

import sys
import re
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import numpy as np
from PIL import Image

# SVG rendering
try:
    from stagforge.rendering.vector import render_svg_string
    HAS_RESVG = True
except ImportError:
    HAS_RESVG = False
    print("Warning: resvg not available, cannot render SVGs")

# Layer effects
from imagestag.layer_effects import (
    DropShadow,
    InnerShadow,
    OuterGlow,
    InnerGlow,
    BevelEmboss,
    Satin,
    Stroke,
    ColorOverlay,
    GradientOverlay,
    PatternOverlay,
    BevelStyle,
    StrokePosition,
    GradientStyle,
)
import base64
from io import BytesIO

# Effect categories for baked SVG approach
# These effects add something OUTSIDE the original shape - can extract effect-only layer
UNDERLAY_EFFECTS = (DropShadow, OuterGlow)  # Effect appears UNDER/around original content
OVERLAY_EFFECTS = (Stroke, InnerGlow)  # Effect appears OVER original content

# Effects that can use native SVG elements (gradient/pattern) with mask - no raster needed for content
VECTOR_OVERLAY_EFFECTS = (GradientOverlay, PatternOverlay)

# Effects that should NOT be baked - use SVG filter only (too tightly coupled to shape)
SVG_FILTER_ONLY_EFFECTS = (InnerShadow,)

# Effects that fundamentally modify pixels and cannot be separated
REPLACEMENT_EFFECTS = (ColorOverlay, BevelEmboss, Satin)

# Paths
SVG_DIR = project_root / "imagestag" / "samples" / "svgs"
DEER_SVG = SVG_DIR / "noto-emoji" / "deer.svg"
MALE_DEER_SVG = SVG_DIR / "openclipart" / "male-deer.svg"
OUTPUT_DIR = project_root / "tmp" / "effect_samples"

# Render size
RENDER_SIZE = 300


def load_svg_image(svg_path: Path, size: int = RENDER_SIZE) -> np.ndarray:
    """Load and render an SVG to RGBA numpy array."""
    if not HAS_RESVG:
        raise RuntimeError("resvg not available")
    svg_content = svg_path.read_text()
    return render_svg_string(svg_content, size, size, supersample=2)


def save_image(image: np.ndarray, path: Path, offset_x: int = 0, offset_y: int = 0):
    """Save numpy array as PNG image."""
    # If there's an offset, we need to handle expansion
    if offset_x != 0 or offset_y != 0:
        # The output image may be larger due to effect expansion
        # The offset tells us where the original content starts
        pass  # Image is already correctly positioned

    img = Image.fromarray(image.astype(np.uint8))
    img.save(path)


def create_checkerboard_pattern(size: int = 8) -> np.ndarray:
    """Create a checkerboard pattern."""
    pattern = np.zeros((size, size, 4), dtype=np.uint8)
    pattern[::2, ::2] = [200, 200, 200, 255]
    pattern[1::2, 1::2] = [200, 200, 200, 255]
    pattern[::2, 1::2] = [100, 100, 100, 255]
    pattern[1::2, ::2] = [100, 100, 100, 255]
    return pattern


def apply_svg_filter_to_svg(svg_content: str, effect, filter_id: str, render_size: int = RENDER_SIZE, rendered_image: np.ndarray = None) -> str:
    """
    Apply an SVG filter or defs to an SVG file.

    Returns modified SVG content with the effect applied.

    Args:
        svg_content: The SVG content string
        effect: The layer effect to apply
        filter_id: Unique ID for the filter/element
        render_size: Target render size in pixels
        rendered_image: Optional rendered image for contour-based effects (e.g., Stroke)
    """
    # Parse viewBox to calculate scale factor for filter parameters
    viewbox_match = re.search(r'viewBox="([^"]+)"', svg_content)
    if viewbox_match:
        vb = viewbox_match.group(1).split()
        vb_width = float(vb[2]) if len(vb) >= 3 else 100
        vb_height = float(vb[3]) if len(vb) >= 4 else 100
        # Use the larger dimension to calculate scale
        vb_size = max(vb_width, vb_height)
    else:
        vb_size = 100

    # Scale factor: convert pixel values to viewBox units
    # If viewBox is 128 and render_size is 300, scale = 128/300 = 0.427
    # So a 10px blur in Rust becomes 4.27 units in SVG viewBox
    scale = vb_size / render_size

    # Special handling for Stroke: use contour-based approach for smooth bezier curves
    if isinstance(effect, Stroke) and rendered_image is not None and hasattr(effect, 'to_svg_path'):
        alpha_mask = rendered_image[:, :, 3]  # Extract alpha channel
        stroke_path = effect.to_svg_path(alpha_mask, filter_id)
        if stroke_path:
            # Scale the stroke path coordinates from pixel space to viewBox space
            h, w = rendered_image.shape[:2]
            scale_x = vb_size / w
            scale_y = vb_size / h

            # Adjust stroke-width: the path is in pixel coords and will be scaled,
            # but we need to halve the width to match Rust's visual output
            # (SVG stroke is centered, Rust stroke is outside-only, plus scaling factors)
            adjusted_stroke_path = re.sub(
                r'stroke-width="([^"]+)"',
                lambda m: f'stroke-width="{float(m.group(1)) / 2.0}"',
                stroke_path
            )

            # Add the stroke path after the main content, before </svg>
            svg_content = re.sub(
                r'(</svg>)',
                f'<g transform="scale({scale_x:.6f}, {scale_y:.6f})">\n  {adjusted_stroke_path}\n</g>\n\\1',
                svg_content,
                count=1
            )
            return svg_content

    # Get filter or defs from effect (with scale for filter-based effects)
    svg_filter = effect.to_svg_filter(filter_id, scale=scale)
    has_defs = hasattr(effect, 'to_svg_defs')
    # Pass viewbox_scale to defs for pattern overlays that need coordinate scaling
    if has_defs:
        import inspect
        sig = inspect.signature(effect.to_svg_defs)
        if 'viewbox_scale' in sig.parameters:
            svg_defs = effect.to_svg_defs(filter_id, viewbox_scale=scale)
        else:
            svg_defs = effect.to_svg_defs(filter_id)
    else:
        svg_defs = None

    if svg_filter:
        # Filter-based effect: add filter to defs and apply to root group
        # Find or create defs section
        if '<defs>' in svg_content or '<defs ' in svg_content:
            # Insert filter into existing defs
            svg_content = re.sub(
                r'(<defs[^>]*>)',
                f'\\1\n  {svg_filter}',
                svg_content,
                count=1
            )
        else:
            # Add defs section after opening svg tag
            svg_content = re.sub(
                r'(<svg[^>]*>)',
                f'\\1\n<defs>\n  {svg_filter}\n</defs>',
                svg_content,
                count=1
            )

        # Wrap content in a group with the filter applied
        # Find closing </svg> and wrap content before it
        svg_content = re.sub(
            r'(</svg>)',
            f'</g>\n\\1',
            svg_content,
            count=1
        )
        # Add opening group after defs
        svg_content = re.sub(
            r'(</defs>)',
            f'\\1\n<g filter="url(#{filter_id})">',
            svg_content,
            count=1
        )

    elif svg_defs:
        # Defs-based effect (gradient/pattern): add to defs and overlay
        # Strategy depends on blend mode:
        # - Normal: clip-path to shape, overlay with opacity
        # - Multiply/other: use feBlend filter

        # Parse SVG dimensions
        width_match = re.search(r'width="([^"]+)"', svg_content)
        height_match = re.search(r'height="([^"]+)"', svg_content)
        viewbox_match = re.search(r'viewBox="([^"]+)"', svg_content)

        if viewbox_match:
            vb = viewbox_match.group(1).split()
            vb_x = float(vb[0]) if len(vb) >= 1 else 0
            vb_y = float(vb[1]) if len(vb) >= 2 else 0
            width = float(vb[2]) if len(vb) >= 3 else 100
            height = float(vb[3]) if len(vb) >= 4 else 100
        elif width_match and height_match:
            vb_x, vb_y = 0, 0
            width = float(re.sub(r'[^\d.]', '', width_match.group(1)))
            height = float(re.sub(r'[^\d.]', '', height_match.group(1)))
        else:
            vb_x, vb_y, width, height = 0, 0, 100, 100

        blend_mode = getattr(effect, 'blend_mode', 'normal')
        content_group_id = f"{filter_id}_content"

        # Find content structure
        defs_match = re.search(r'<defs[^>]*>.*?</defs>', svg_content, re.DOTALL)
        svg_tag_match = re.search(r'<svg[^>]*>', svg_content)

        # Use mask-based approach for all blend modes (clipPath has issues with complex paths in resvg)
        if blend_mode == 'normal':
            # Normal blend: use mask approach (same as multiply but without blend mode)
            # This works better than clipPath for complex SVGs

            mask_id = f"{filter_id}_mask"

            # First add defs with gradient/pattern
            if defs_match:
                insert_pos = svg_content.rfind('</defs>')
                svg_content = (
                    svg_content[:insert_pos] +
                    f'\n  {svg_defs}\n' +
                    svg_content[insert_pos:]
                )
            else:
                insert_pos = svg_tag_match.end() if svg_tag_match else 0
                svg_content = (
                    svg_content[:insert_pos] +
                    f'\n<defs>\n  {svg_defs}\n</defs>' +
                    svg_content[insert_pos:]
                )

            # Find main content
            defs_end = svg_content.find('</defs>')
            if defs_end != -1:
                defs_end += len('</defs>')
            else:
                defs_end = svg_tag_match.end() if svg_tag_match else 0

            svg_end = svg_content.rfind('</svg>')
            before_content = svg_content[:defs_end]
            main_content = svg_content[defs_end:svg_end].strip()
            after_content = svg_content[svg_end:]

            # Create mask from content using feColorMatrix to convert all colors to white
            # and force alpha to 1 for all visible content (handles low-opacity elements)
            # Matrix: RGB→white, Alpha→1 where there's any content
            to_white_filter_id = f"{mask_id}_to_white"
            mask_def = f'''
<defs>
  <filter id="{to_white_filter_id}">
    <!-- Convert colors to white and boost alpha to handle low-opacity elements -->
    <feColorMatrix type="matrix" values="0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  0 0 0 255 0"/>
  </filter>
  <mask id="{mask_id}">
    <g filter="url(#{to_white_filter_id})">
      {main_content}
    </g>
  </mask>
</defs>'''

            # Overlay rect masked to shape (no blend mode for normal)
            overlay_rect = f'<rect x="{vb_x}" y="{vb_y}" width="{width}" height="{height}" fill="url(#{filter_id})" mask="url(#{mask_id})" opacity="{effect.opacity}"/>'

            svg_content = (
                before_content +
                mask_def +
                f'\n<g id="{content_group_id}">\n{main_content}\n</g>\n' +
                overlay_rect + '\n' +
                after_content
            )

        else:
            # Multiply/other blend modes: use feBlend filter
            # This requires wrapping content in a filter that blends with the gradient/pattern

            blend_filter_id = f"{filter_id}_blend_filter"
            mask_id = f"{filter_id}_mask"

            # First add defs with gradient/pattern
            if defs_match:
                insert_pos = svg_content.rfind('</defs>')
                svg_content = (
                    svg_content[:insert_pos] +
                    f'\n  {svg_defs}\n' +
                    svg_content[insert_pos:]
                )
            else:
                insert_pos = svg_tag_match.end() if svg_tag_match else 0
                svg_content = (
                    svg_content[:insert_pos] +
                    f'\n<defs>\n  {svg_defs}\n</defs>' +
                    svg_content[insert_pos:]
                )

            # Find main content
            defs_end = svg_content.find('</defs>')
            if defs_end != -1:
                defs_end += len('</defs>')
            else:
                defs_end = svg_tag_match.end() if svg_tag_match else 0

            svg_end = svg_content.rfind('</svg>')
            before_content = svg_content[:defs_end]
            main_content = svg_content[defs_end:svg_end].strip()
            after_content = svg_content[svg_end:]

            # Create mask from content for clipping the blend result
            # Use a color matrix filter to convert all colors to white while preserving alpha
            # This is necessary because inline styles on SVG elements override group styles,
            # and SVG masks use luminance - darker original colors would reduce mask opacity
            to_white_filter_id = f"{mask_id}_to_white"
            mask_def = f'''
<defs>
  <filter id="{to_white_filter_id}">
    <feColorMatrix type="matrix" values="0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  0 0 0 1 0"/>
  </filter>
  <mask id="{mask_id}">
    <g filter="url(#{to_white_filter_id})">
      {main_content}
    </g>
  </mask>
</defs>'''

            # For multiply: draw content, then draw gradient/pattern on top with multiply blend
            # Use CSS mix-blend-mode on the overlay
            css_blend = blend_mode.replace('_', '-')

            overlay_rect = f'<rect x="{vb_x}" y="{vb_y}" width="{width}" height="{height}" fill="url(#{filter_id})" mask="url(#{mask_id})" opacity="{effect.opacity}" style="mix-blend-mode: {css_blend};"/>'

            svg_content = (
                before_content +
                mask_def +
                f'\n<g id="{content_group_id}">\n{main_content}\n</g>\n' +
                overlay_rect + '\n' +
                after_content
            )

    return svg_content


def image_to_data_url(img: np.ndarray) -> str:
    """Convert numpy RGBA image to base64 data URL."""
    pil_img = Image.fromarray(img)
    buffer = BytesIO()
    pil_img.save(buffer, format='PNG')
    b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    return f"data:image/png;base64,{b64}"


def extract_effect_layer(
    rust_result: np.ndarray,
    original: np.ndarray,
    mode: str = "underlay",
    offset_x: int = 0,
    offset_y: int = 0,
) -> np.ndarray:
    """
    Extract just the effect layer from the composited result.

    For UNDERLAY effects (drop shadow, outer glow):
        Effect is visible only OUTSIDE the original shape.
        Uses hard threshold to eliminate edge artifacts.

    For OVERLAY effects (stroke, inner shadow, inner glow):
        Effect is visible on top of or inside the original content.
        Extracts the effect contribution.

    Args:
        rust_result: Full composited result (effect + original)
        original: Original image without effect
        mode: "underlay" or "overlay"
        offset_x: X offset where original content starts in result (negative = expansion left)
        offset_y: Y offset where original content starts in result (negative = expansion top)

    Returns:
        Effect-only image with transparency where effect doesn't exist
    """
    result_h, result_w = rust_result.shape[:2]
    orig_h, orig_w = original.shape[:2]

    # Handle canvas expansion: pad original to match result size
    if result_h != orig_h or result_w != orig_w:
        padded_original = np.zeros((result_h, result_w, 4), dtype=original.dtype)
        paste_x = -offset_x if offset_x < 0 else 0
        paste_y = -offset_y if offset_y < 0 else 0
        end_x = min(paste_x + orig_w, result_w)
        end_y = min(paste_y + orig_h, result_h)
        src_w = end_x - paste_x
        src_h = end_y - paste_y
        padded_original[paste_y:end_y, paste_x:end_x] = original[:src_h, :src_w]
        original = padded_original

    effect_layer = np.zeros_like(rust_result, dtype=np.uint8)
    original_alpha = original[:, :, 3].astype(np.float32) / 255.0
    result_alpha = rust_result[:, :, 3].astype(np.float32) / 255.0

    if mode == "underlay":
        # UNDERLAY: Effect visible only OUTSIDE the original shape
        # Use very strict threshold to avoid including any anti-aliased edge pixels
        # that have original content blended in. Only take truly transparent areas.
        UNDERLAY_THRESHOLD = 0.01  # Nearly zero - only fully transparent original pixels

        outside_mask = original_alpha < UNDERLAY_THRESHOLD

        # Copy result pixels only where original is completely transparent
        effect_layer[outside_mask] = rust_result[outside_mask]

    elif mode == "overlay":
        # OVERLAY: Effect visible on top of or around original content
        # For stroke: visible outside original shape
        # For inner shadow/glow: visible inside original shape (on top of content)

        OVERLAY_OUTSIDE_THRESHOLD = 0.01  # Only fully transparent areas

        # Outside original shape: take result where original is completely transparent
        outside_mask = (original_alpha < OVERLAY_OUTSIDE_THRESHOLD) & (result_alpha > 0.01)
        effect_layer[outside_mask] = rust_result[outside_mask]

        # Inside original shape: compute difference between result and original
        # This extracts the effect contribution (inner shadow, inner glow)
        OVERLAY_INSIDE_THRESHOLD = 0.99  # Only fully opaque areas
        inside_mask = original_alpha >= OVERLAY_INSIDE_THRESHOLD

        if np.any(inside_mask):
            # Calculate color difference to find effect pixels
            result_rgb = rust_result[:, :, :3].astype(np.float32)
            original_rgb = original[:, :, :3].astype(np.float32)

            # Compute per-pixel color difference
            color_diff = np.sqrt(np.sum((result_rgb - original_rgb) ** 2, axis=2))

            # Where color differs significantly, there's an effect
            effect_inside = inside_mask & (color_diff > 3)

            if np.any(effect_inside):
                # For inner effects, compute the actual color contribution
                # Result = Original blended with Effect
                # We need to extract the Effect contribution

                # Simple approach: use the result color directly with alpha based on diff
                diff_magnitude = np.clip(color_diff / 100.0, 0, 1)  # Normalize difference

                for c in range(3):
                    # Use the result color (which has the effect applied)
                    effect_layer[effect_inside, c] = rust_result[effect_inside, c]

                # Alpha based on how different from original
                effect_layer[effect_inside, 3] = np.clip(
                    diff_magnitude[effect_inside] * 255,
                    0, 255
                ).astype(np.uint8)

    return effect_layer


def create_baked_svg(
    svg_content: str,
    effect,
    rust_result_image: np.ndarray,
    original_image: np.ndarray,
    render_size: int,
    offset_x: int = 0,
    offset_y: int = 0,
) -> str:
    """
    Create an SVG with the Rust-rendered effect baked in as an embedded image.

    Preserves original SVG vector content where possible:
    - UNDERLAY (drop shadow, outer glow): Effect-only layer UNDER original SVG vector
    - OVERLAY (stroke): Effect-only layer OVER original SVG vector
    - REPLACEMENT (all others): Full rasterization required (modifies pixels)

    This approach keeps the original SVG shapes sharp when zoomed, while the
    effect (shadow, glow, stroke) is rasterized for 100% fidelity.

    Args:
        svg_content: Original SVG content string
        effect: The layer effect instance
        rust_result_image: Full result from Rust (effect + original composited)
        original_image: Original rendered image (without effect)
        render_size: Render size in pixels
        offset_x: X offset from effect expansion (negative = expanded left)
        offset_y: Y offset from effect expansion (negative = expanded top)

    Returns:
        Modified SVG string with baked effect layer, or None if effect should use SVG filter only
    """
    # SVG_FILTER_ONLY_EFFECTS should not be baked - return None to use SVG filter
    if isinstance(effect, SVG_FILTER_ONLY_EFFECTS):
        return None

    # Parse viewBox
    viewbox_match = re.search(r'viewBox="([^"]+)"', svg_content)
    if viewbox_match:
        vb = viewbox_match.group(1).split()
        vb_x, vb_y = float(vb[0]), float(vb[1])
        vb_width = float(vb[2]) if len(vb) >= 3 else 100
        vb_height = float(vb[3]) if len(vb) >= 4 else 100
    else:
        vb_x, vb_y = 0, 0
        vb_width, vb_height = 100, 100

    # Calculate expansion in viewBox units
    result_h, result_w = rust_result_image.shape[:2]
    orig_h, orig_w = original_image.shape[:2]

    # Scale from render pixels to viewBox units
    scale_x = vb_width / orig_w
    scale_y = vb_height / orig_h

    # Expansion in viewBox units (offset is typically negative for expansion)
    expand_x = -offset_x * scale_x if offset_x < 0 else 0
    expand_y = -offset_y * scale_y if offset_y < 0 else 0

    # New viewBox dimensions if expanded
    new_vb_x = vb_x - expand_x
    new_vb_y = vb_y - expand_y
    new_vb_width = result_w * scale_x
    new_vb_height = result_h * scale_y

    # Find SVG structure
    svg_tag_match = re.search(r'<svg[^>]*>', svg_content)
    defs_end = svg_content.find('</defs>')
    svg_end = svg_content.rfind('</svg>')

    # Determine content insert position (after defs if present)
    if defs_end != -1:
        content_start = defs_end + len('</defs>')
    else:
        content_start = svg_tag_match.end() if svg_tag_match else 0

    # Get parts of the SVG
    svg_header = svg_content[:content_start]
    svg_body = svg_content[content_start:svg_end].strip()
    svg_close = '</svg>'

    # Check if viewBox needs expansion
    needs_expansion = result_h != orig_h or result_w != orig_w

    if isinstance(effect, UNDERLAY_EFFECTS):
        # UNDERLAY: Use dedicated shadow-only/glow-only methods for clean extraction
        # These Rust functions return ONLY the effect layer (no original composited)
        # This eliminates edge artifacts from alpha blending extraction
        if isinstance(effect, DropShadow):
            effect_result = effect.apply_shadow_only(original_image)
            effect_only = effect_result.image
            offset_x = effect_result.offset_x
            offset_y = effect_result.offset_y
        elif isinstance(effect, OuterGlow):
            effect_result = effect.apply_glow_only(original_image)
            effect_only = effect_result.image
            offset_x = effect_result.offset_x
            offset_y = effect_result.offset_y
        else:
            # Fallback: extract from composited result
            effect_only = extract_effect_layer(rust_result_image, original_image, mode="underlay",
                                               offset_x=offset_x, offset_y=offset_y)

        # Recalculate expansion based on effect-only result
        result_h, result_w = effect_only.shape[:2]
        expand_x = -offset_x * scale_x if offset_x < 0 else 0
        expand_y = -offset_y * scale_y if offset_y < 0 else 0
        new_vb_x = vb_x - expand_x
        new_vb_y = vb_y - expand_y
        new_vb_width = result_w * scale_x
        new_vb_height = result_h * scale_y
        needs_expansion = result_h != orig_h or result_w != orig_w

        effect_data_url = image_to_data_url(effect_only)

        if needs_expansion:
            # Canvas was expanded - update SVG header with new viewBox
            new_viewbox = f'viewBox="{new_vb_x} {new_vb_y} {new_vb_width} {new_vb_height}"'
            svg_header_expanded = re.sub(r'viewBox="[^"]+"', new_viewbox, svg_header)

            baked_svg = (
                svg_header_expanded +
                f'\n<!-- Baked effect layer (100% fidelity) - rendered under vector content -->\n'
                f'<image href="{effect_data_url}" x="{new_vb_x}" y="{new_vb_y}" width="{new_vb_width}" height="{new_vb_height}" preserveAspectRatio="none"/>\n'
                f'<!-- Original SVG vector content (stays sharp when zoomed) -->\n'
                f'{svg_body}\n' +
                svg_close
            )
        else:
            baked_svg = (
                svg_header +
                f'\n<!-- Baked effect layer (100% fidelity) - rendered under vector content -->\n'
                f'<image href="{effect_data_url}" x="{vb_x}" y="{vb_y}" width="{vb_width}" height="{vb_height}" preserveAspectRatio="none"/>\n'
                f'<!-- Original SVG vector content (stays sharp when zoomed) -->\n'
                f'{svg_body}\n' +
                svg_close
            )
        return baked_svg

    elif isinstance(effect, OVERLAY_EFFECTS):
        # OVERLAY: Use dedicated effect-only methods for clean extraction
        # These Rust functions return ONLY the effect layer (no original composited)
        # This eliminates edge artifacts from alpha blending extraction
        if isinstance(effect, Stroke):
            effect_result = effect.apply_stroke_only(original_image)
            effect_only = effect_result.image
            offset_x = effect_result.offset_x
            offset_y = effect_result.offset_y
        elif isinstance(effect, InnerGlow):
            effect_result = effect.apply_glow_only(original_image)
            effect_only = effect_result.image
            offset_x = effect_result.offset_x
            offset_y = effect_result.offset_y
        else:
            # Fallback: extract from composited result
            effect_only = extract_effect_layer(rust_result_image, original_image, mode="overlay",
                                               offset_x=offset_x, offset_y=offset_y)

        # Recalculate expansion based on effect-only result
        result_h, result_w = effect_only.shape[:2]
        expand_x = -offset_x * scale_x if offset_x < 0 else 0
        expand_y = -offset_y * scale_y if offset_y < 0 else 0
        new_vb_x = vb_x - expand_x
        new_vb_y = vb_y - expand_y
        new_vb_width = result_w * scale_x
        new_vb_height = result_h * scale_y
        needs_expansion = result_h != orig_h or result_w != orig_w

        effect_data_url = image_to_data_url(effect_only)

        if needs_expansion:
            # Canvas was expanded - update SVG header with new viewBox
            new_viewbox = f'viewBox="{new_vb_x} {new_vb_y} {new_vb_width} {new_vb_height}"'
            svg_header_expanded = re.sub(r'viewBox="[^"]+"', new_viewbox, svg_header)

            baked_svg = (
                svg_header_expanded +
                f'\n<!-- Original SVG vector content (stays sharp when zoomed) -->\n'
                f'{svg_body}\n'
                f'<!-- Baked effect layer (100% fidelity) - rendered over vector content -->\n'
                f'<image href="{effect_data_url}" x="{new_vb_x}" y="{new_vb_y}" width="{new_vb_width}" height="{new_vb_height}" preserveAspectRatio="none"/>\n' +
                svg_close
            )
        else:
            baked_svg = (
                svg_header +
                f'\n<!-- Original SVG vector content (stays sharp when zoomed) -->\n'
                f'{svg_body}\n'
                f'<!-- Baked effect layer (100% fidelity) - rendered over vector content -->\n'
                f'<image href="{effect_data_url}" x="{vb_x}" y="{vb_y}" width="{vb_width}" height="{vb_height}" preserveAspectRatio="none"/>\n' +
                svg_close
            )
        return baked_svg

    elif isinstance(effect, VECTOR_OVERLAY_EFFECTS):
        # VECTOR_OVERLAY: Use native SVG gradient/pattern with mask - no raster needed
        # This preserves vector content AND uses vector gradient/pattern
        filter_id = "baked_overlay"

        # Get the SVG defs (gradient or pattern definition)
        if hasattr(effect, 'to_svg_defs'):
            # Calculate scale for viewBox
            scale = max(vb_width, vb_height) / render_size
            import inspect
            sig = inspect.signature(effect.to_svg_defs)
            if 'viewbox_scale' in sig.parameters:
                svg_defs = effect.to_svg_defs(filter_id, viewbox_scale=scale)
            else:
                svg_defs = effect.to_svg_defs(filter_id)

            if svg_defs:
                # Create mask from content
                mask_id = f"{filter_id}_mask"
                to_white_filter_id = f"{mask_id}_to_white"

                blend_mode = getattr(effect, 'blend_mode', 'normal')
                css_blend = blend_mode.replace('_', '-') if blend_mode != 'normal' else ''
                blend_style = f' style="mix-blend-mode: {css_blend};"' if css_blend else ''

                # Build the baked SVG with native gradient/pattern
                mask_def = f'''
<defs>
  {svg_defs}
  <filter id="{to_white_filter_id}">
    <feColorMatrix type="matrix" values="0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  0 0 0 255 0"/>
  </filter>
  <mask id="{mask_id}">
    <g filter="url(#{to_white_filter_id})">
      {svg_body}
    </g>
  </mask>
</defs>'''

                overlay_rect = f'<rect x="{vb_x}" y="{vb_y}" width="{vb_width}" height="{vb_height}" fill="url(#{filter_id})" mask="url(#{mask_id})" opacity="{effect.opacity}"{blend_style}/>'

                baked_svg = (
                    svg_header +
                    mask_def +
                    f'\n<!-- Original SVG vector content (stays sharp when zoomed) -->\n'
                    f'{svg_body}\n'
                    f'<!-- Vector gradient/pattern overlay (no rasterization) -->\n'
                    f'{overlay_rect}\n' +
                    svg_close
                )
                return baked_svg

        # Fallback: if no defs available, use full rasterization
        effect_data_url = image_to_data_url(rust_result_image)
        if svg_tag_match:
            svg_open = svg_content[:svg_tag_match.end()]
        else:
            svg_open = '<svg>'

        baked_svg = (
            svg_open +
            f'\n<!-- Baked Rust effect (100% fidelity) - fallback rasterization -->\n'
            f'<image href="{effect_data_url}" x="{vb_x}" y="{vb_y}" width="{vb_width}" height="{vb_height}" preserveAspectRatio="none"/>\n'
            f'</svg>'
        )
        return baked_svg

    else:
        # REPLACEMENT: Effects that modify pixel colors (color overlay, bevel, satin)
        # These cannot be separated - must rasterize entire content
        effect_data_url = image_to_data_url(rust_result_image)

        # Find SVG opening tag
        if svg_tag_match:
            svg_open = svg_content[:svg_tag_match.end()]
        else:
            svg_open = '<svg>'

        baked_svg = (
            svg_open +
            f'\n<!-- Baked Rust effect (100% fidelity) - replaces content (effect modifies pixels) -->\n'
            f'<image href="{effect_data_url}" x="{vb_x}" y="{vb_y}" width="{vb_width}" height="{vb_height}" preserveAspectRatio="none"/>\n'
            f'</svg>'
        )
        return baked_svg


def create_checkerboard_background(width: int, height: int, tile_size: int = 16) -> np.ndarray:
    """Create a white-grey checkerboard background."""
    bg = np.zeros((height, width, 4), dtype=np.uint8)
    light = np.array([240, 240, 240, 255], dtype=np.uint8)
    dark = np.array([200, 200, 200, 255], dtype=np.uint8)

    for y in range(0, height, tile_size):
        for x in range(0, width, tile_size):
            color = light if ((x // tile_size) + (y // tile_size)) % 2 == 0 else dark
            y_end = min(y + tile_size, height)
            x_end = min(x + tile_size, width)
            bg[y:y_end, x:x_end] = color
    return bg


def composite_over_checkerboard(img: np.ndarray, tile_size: int = 16) -> np.ndarray:
    """Composite an RGBA image over a checkerboard background."""
    h, w = img.shape[:2]
    bg = create_checkerboard_background(w, h, tile_size)

    # Alpha compositing: result = fg * alpha + bg * (1 - alpha)
    if img.shape[2] == 4:
        alpha = img[:, :, 3:4].astype(np.float32) / 255.0
        fg = img[:, :, :3].astype(np.float32)
        bg_rgb = bg[:, :, :3].astype(np.float32)
        result_rgb = fg * alpha + bg_rgb * (1 - alpha)
        result = np.zeros((h, w, 4), dtype=np.uint8)
        result[:, :, :3] = result_rgb.astype(np.uint8)
        result[:, :, 3] = 255
        return result
    return img


def create_side_by_side(rust_img: np.ndarray, svg_img: np.ndarray, label: str, baked_img: np.ndarray = None) -> np.ndarray:
    """Create a side-by-side comparison image with labels on checkerboard background.

    Args:
        rust_img: Rust-rendered image
        svg_img: SVG filter-rendered image
        label: Label for the effect
        baked_img: Optional baked (Rust embedded in SVG) rendered image for 3-column comparison
    """
    from PIL import Image, ImageDraw, ImageFont

    # Composite all images over checkerboard
    rust_comp = composite_over_checkerboard(rust_img)
    svg_comp = composite_over_checkerboard(svg_img)
    baked_comp = composite_over_checkerboard(baked_img) if baked_img is not None else None

    h1, w1 = rust_comp.shape[:2]
    h2, w2 = svg_comp.shape[:2]

    # Use max height, combine widths with padding
    padding = 20
    label_height = 30

    if baked_comp is not None:
        h3, w3 = baked_comp.shape[:2]
        combined_h = max(h1, h2, h3) + label_height + padding
        combined_w = w1 + w2 + w3 + padding * 4
    else:
        combined_h = max(h1, h2) + label_height + padding
        combined_w = w1 + w2 + padding * 3

    # Create white background
    combined = np.ones((combined_h, combined_w, 4), dtype=np.uint8) * 255
    combined[:, :, 3] = 255  # Fully opaque

    # Place rust image
    y_offset = label_height + padding // 2
    combined[y_offset:y_offset + h1, padding:padding + w1] = rust_comp

    # Place svg image
    x_svg = padding * 2 + w1
    combined[y_offset:y_offset + h2, x_svg:x_svg + w2] = svg_comp

    # Place baked image if provided
    if baked_comp is not None:
        x_baked = padding * 3 + w1 + w2
        combined[y_offset:y_offset + h3, x_baked:x_baked + w3] = baked_comp

    # Convert to PIL to add text labels
    pil_img = Image.fromarray(combined)
    draw = ImageDraw.Draw(pil_img)

    # Try to use a basic font
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
    except:
        font = ImageFont.load_default()

    # Add labels
    draw.text((padding, 5), "RUST", fill=(0, 0, 0), font=font)
    draw.text((x_svg, 5), "SVG Filter", fill=(0, 0, 0), font=font)
    if baked_comp is not None:
        draw.text((x_baked, 5), "Baked", fill=(0, 0, 0), font=font)

    # Center label
    label_x = combined_w // 2 - len(label) * 3
    draw.text((label_x, 5), label, fill=(100, 100, 100), font=font)

    return np.array(pil_img)


def generate_effect_comparison(
    svg_path: Path,
    svg_content: str,
    rendered_image: np.ndarray,
    effect,
    effect_name: str,
    output_dir: Path,
    render_size: int = RENDER_SIZE,
):
    """
    Generate comparison outputs for a single effect on an SVG.

    Outputs:
    - {effect_name}_{base_name}_comparison.png: Side-by-side Rust vs SVG Filter vs Baked
    - {effect_name}_{base_name}.svg: The SVG with filter applied
    - {effect_name}_{base_name}_baked.svg: The SVG with Rust effect baked as embedded image
    """
    base_name = svg_path.stem  # e.g., "deer" or "male-deer"

    # 1. Apply effect via Rust
    try:
        result = effect.apply(rendered_image)
        rust_image = result.image
    except Exception as e:
        print(f"    ERROR (Rust): {e}")
        return

    # 2. Apply effect as SVG filter/defs
    filter_id = f"effect_{effect_name}"
    svg_image = None
    try:
        modified_svg = apply_svg_filter_to_svg(svg_content, effect, filter_id, render_size, rendered_image)

        # Save the SVG
        svg_out_path = output_dir / f"{effect_name}_{base_name}.svg"
        svg_out_path.write_text(modified_svg)

        # Render SVG to PNG
        svg_image = render_svg_string(modified_svg, render_size, render_size, supersample=2)
    except Exception as e:
        print(f"    ERROR (SVG filter): {e}")
        import traceback
        traceback.print_exc()

    # 3. Create baked SVG (Rust effect embedded as raster image)
    # Some effects (like InnerShadow) cannot be baked and return None
    baked_image = None
    try:
        baked_svg = create_baked_svg(svg_content, effect, rust_image, rendered_image, render_size,
                                     offset_x=result.offset_x, offset_y=result.offset_y)

        if baked_svg is not None:
            # Save the baked SVG
            baked_svg_path = output_dir / f"{effect_name}_{base_name}_baked.svg"
            baked_svg_path.write_text(baked_svg)

            # Render baked SVG to PNG
            baked_image = render_svg_string(baked_svg, render_size, render_size, supersample=2)
    except Exception as e:
        print(f"    ERROR (Baked): {e}")
        import traceback
        traceback.print_exc()

    # 4. Create comparison image (3 columns if baked available)
    if svg_image is not None:
        comparison = create_side_by_side(rust_image, svg_image, f"{effect_name}", baked_image)
        comparison_path = output_dir / f"{effect_name}_{base_name}_comparison.png"
        save_image(comparison, comparison_path)

        outputs = ["comparison.png", ".svg"]
        if baked_image is not None:
            outputs.append("_baked.svg")
        print(f"  {effect_name}_{base_name}: {', '.join(outputs)}")
    else:
        print(f"  {effect_name}_{base_name}: FAILED")


def generate_all_samples():
    """Generate sample images for all effects."""
    if not HAS_RESVG:
        print("ERROR: resvg required for SVG rendering")
        return

    # Clean and create output directory for fresh start
    import shutil
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Load source images
    print("Loading source SVGs...")
    deer_image = load_svg_image(DEER_SVG)
    male_deer_image = load_svg_image(MALE_DEER_SVG)

    # Save originals
    save_image(deer_image, OUTPUT_DIR / "00_original_deer.png")
    save_image(male_deer_image, OUTPUT_DIR / "00_original_male_deer.png")
    print(f"  Saved originals")

    # Define all effects with their configurations
    effects_configs = {
        "01_drop_shadow": [
            ("subtle", DropShadow(blur=3, offset_x=3, offset_y=3, color=(0, 0, 0), opacity=0.4)),
            ("strong", DropShadow(blur=10, offset_x=8, offset_y=8, color=(0, 0, 0), opacity=0.75)),
            ("colored", DropShadow(blur=6, offset_x=5, offset_y=5, color=(100, 50, 0), opacity=0.6)),
        ],
        "02_inner_shadow": [
            ("subtle", InnerShadow(blur=3, offset_x=2, offset_y=2, color=(0, 0, 0), opacity=0.3)),
            ("strong", InnerShadow(blur=8, offset_x=4, offset_y=4, color=(0, 0, 0), opacity=0.7)),
            ("colored", InnerShadow(blur=5, offset_x=3, offset_y=3, color=(50, 0, 80), opacity=0.5)),
        ],
        "03_outer_glow": [
            ("white", OuterGlow(radius=8, color=(255, 255, 255), opacity=0.6)),
            ("yellow", OuterGlow(radius=15, color=(255, 255, 0), opacity=0.75, spread=3)),
            ("blue", OuterGlow(radius=12, color=(0, 150, 255), opacity=0.7, spread=5)),
        ],
        "04_inner_glow": [
            ("white", InnerGlow(radius=5, color=(255, 255, 255), opacity=0.5)),
            ("orange", InnerGlow(radius=12, color=(255, 150, 0), opacity=0.7)),
            ("cyan", InnerGlow(radius=8, color=(0, 255, 255), opacity=0.6, choke=0.3)),
        ],
        "05_bevel_emboss": [
            ("inner_bevel", BevelEmboss(depth=4, angle=120, style=BevelStyle.INNER_BEVEL)),
            ("emboss", BevelEmboss(depth=5, angle=135, style=BevelStyle.EMBOSS)),
            ("pillow", BevelEmboss(depth=4, angle=90, altitude=45, style=BevelStyle.PILLOW_EMBOSS)),
        ],
        "06_satin": [
            ("black", Satin(color=(0, 0, 0), opacity=0.5, angle=19, distance=11, size=14)),
            ("gold", Satin(color=(200, 150, 50), opacity=0.6, angle=45, distance=15, size=20)),
            ("inverted", Satin(color=(100, 100, 100), opacity=0.4, angle=0, distance=8, size=10, invert=True)),
        ],
        "07_stroke": [
            ("outside_black", Stroke(width=4, color=(0, 0, 0), position=StrokePosition.OUTSIDE)),
            ("inside_red", Stroke(width=5, color=(255, 0, 0), position=StrokePosition.INSIDE)),
            ("center_blue", Stroke(width=4, color=(0, 100, 200), position=StrokePosition.CENTER)),
        ],
        "08_color_overlay": [
            ("red", ColorOverlay(color=(255, 0, 0), opacity=1.0)),
            ("blue_50", ColorOverlay(color=(0, 0, 255), opacity=0.5)),
            ("green_30", ColorOverlay(color=(0, 200, 50), opacity=0.3)),
        ],
        "09_gradient_overlay": [
            ("linear_bw", GradientOverlay(
                gradient=[(0.0, 0, 0, 0), (1.0, 255, 255, 255)],
                style=GradientStyle.LINEAR, angle=90)),
            ("radial_rainbow", GradientOverlay(
                gradient=[(0.0, 255, 0, 0), (0.5, 0, 255, 0), (1.0, 0, 0, 255)],
                style=GradientStyle.RADIAL)),
            ("reflected", GradientOverlay(
                gradient=[(0.0, 255, 200, 100), (1.0, 100, 50, 0)],
                style=GradientStyle.REFLECTED, angle=45)),
        ],
        "10_pattern_overlay": [
            ("checkerboard", PatternOverlay(pattern=create_checkerboard_pattern(8), scale=1.0)),
            ("checkerboard_2x", PatternOverlay(pattern=create_checkerboard_pattern(8), scale=2.0)),
            ("checkerboard_offset", PatternOverlay(pattern=create_checkerboard_pattern(8), scale=1.5, offset_x=4, offset_y=4)),
        ],
    }

    # Generate samples for each effect
    for effect_group, configs in effects_configs.items():
        print(f"\nGenerating {effect_group}...")

        for config_name, effect in configs:
            # Apply to deer
            try:
                result = effect.apply(deer_image)
                filename = f"{effect_group}_{config_name}_deer.png"
                save_image(result.image, OUTPUT_DIR / filename)
                print(f"  {filename}")
            except Exception as e:
                print(f"  ERROR on deer ({config_name}): {e}")

            # Apply to male deer
            try:
                result = effect.apply(male_deer_image)
                filename = f"{effect_group}_{config_name}_male_deer.png"
                save_image(result.image, OUTPUT_DIR / filename)
                print(f"  {filename}")
            except Exception as e:
                print(f"  ERROR on male_deer ({config_name}): {e}")

    # =========================================================================
    # Generate Rust vs SVG comparison outputs
    # =========================================================================
    print("\n\n" + "=" * 60)
    print("GENERATING RUST vs SVG COMPARISONS")
    print("=" * 60)

    comparison_dir = OUTPUT_DIR / "comparisons"
    comparison_dir.mkdir(exist_ok=True)

    # Load SVG content for both deer
    deer_svg_content = DEER_SVG.read_text()
    male_deer_svg_content = MALE_DEER_SVG.read_text()

    # Effects to compare (one representative config per effect type)
    # Using more intense/visible parameters for clear comparison
    comparison_effects = [
        ("drop_shadow", DropShadow(blur=8, offset_x=8, offset_y=8, color=(0, 0, 0), opacity=0.8)),
        ("inner_shadow", InnerShadow(blur=6, offset_x=4, offset_y=4, color=(0, 0, 0), opacity=0.7)),
        ("outer_glow", OuterGlow(radius=10, color=(255, 200, 0), opacity=0.8)),
        ("inner_glow", InnerGlow(radius=10, color=(255, 255, 255), opacity=0.8)),
        ("bevel_emboss", BevelEmboss(depth=5, angle=135, style=BevelStyle.INNER_BEVEL)),
        ("satin", Satin(color=(0, 0, 0), opacity=0.5, angle=19, distance=12, size=15)),
        ("stroke", Stroke(width=3, color=(255, 0, 0), position=StrokePosition.OUTSIDE)),  # Red 3px stroke
        ("color_overlay", ColorOverlay(color=(255, 100, 0), opacity=0.7)),
        # Gradient with normal blend mode (alpha blend/overlay)
        ("gradient_linear_normal", GradientOverlay(
            gradient=[(0.0, 50, 50, 150), (1.0, 200, 150, 50)],
            style=GradientStyle.LINEAR, angle=135, opacity=0.8, blend_mode="normal")),
        # Gradient with multiply blend mode
        ("gradient_linear_multiply", GradientOverlay(
            gradient=[(0.0, 50, 50, 150), (1.0, 200, 150, 50)],
            style=GradientStyle.LINEAR, angle=135, opacity=0.8, blend_mode="multiply")),
        ("gradient_radial", GradientOverlay(
            gradient=[(0.0, 255, 255, 200), (1.0, 100, 50, 0)],
            style=GradientStyle.RADIAL, opacity=0.7)),
        # Pattern with normal blend mode
        ("pattern_normal", PatternOverlay(pattern=create_checkerboard_pattern(8), scale=1.0, opacity=0.6, blend_mode="normal")),
        # Pattern with multiply blend mode
        ("pattern_multiply", PatternOverlay(pattern=create_checkerboard_pattern(8), scale=1.0, opacity=0.6, blend_mode="multiply")),
    ]

    print("\nGenerating comparisons for deer.svg...")
    for effect_name, effect in comparison_effects:
        generate_effect_comparison(
            DEER_SVG,
            deer_svg_content,
            deer_image,
            effect,
            effect_name,
            comparison_dir,
        )

    print("\nGenerating comparisons for male-deer.svg...")
    for effect_name, effect in comparison_effects:
        generate_effect_comparison(
            MALE_DEER_SVG,
            male_deer_svg_content,
            male_deer_image,
            effect,
            effect_name,
            comparison_dir,
        )

    print(f"\nComparisons saved to: {comparison_dir}")

    # Generate SVG filter samples
    print("\n\nGenerating SVG filter samples...")
    svg_output_dir = OUTPUT_DIR / "svg_filters"
    svg_output_dir.mkdir(exist_ok=True)

    # Generate SVG filter strings for reference
    svg_effects = [
        ("drop_shadow", DropShadow(blur=5, offset_x=5, offset_y=5, color=(0, 0, 0), opacity=0.5)),
        ("inner_shadow", InnerShadow(blur=5, offset_x=3, offset_y=3, color=(0, 0, 0), opacity=0.5)),
        ("outer_glow", OuterGlow(radius=10, color=(255, 255, 0), opacity=0.7)),
        ("inner_glow", InnerGlow(radius=8, color=(255, 255, 255), opacity=0.6)),
        ("bevel_emboss", BevelEmboss(depth=4, angle=120)),
        ("satin", Satin(color=(0, 0, 0), opacity=0.5)),
        ("stroke_outside", Stroke(width=3, color=(0, 0, 0), position=StrokePosition.OUTSIDE)),
        ("stroke_inside", Stroke(width=3, color=(255, 0, 0), position=StrokePosition.INSIDE)),
        ("color_overlay", ColorOverlay(color=(255, 0, 0), opacity=0.8)),
        ("gradient_linear", GradientOverlay(gradient=[(0.0, 0, 0, 0), (1.0, 255, 255, 255)])),
        ("gradient_radial", GradientOverlay(style=GradientStyle.RADIAL)),
        ("pattern_overlay", PatternOverlay(pattern=create_checkerboard_pattern(8))),
    ]

    # Write SVG filter samples and render to PNG for verification
    for name, effect in svg_effects:
        # Scale = 1.0 because the sample SVG viewBox (200x200) matches render size
        svg_filter = effect.to_svg_filter(f"filter_{name}", scale=1.0)
        fidelity = effect.svg_fidelity

        svg_file = svg_output_dir / f"{name}.svg"
        png_file = svg_output_dir / f"{name}.png"

        # Check if effect has defs-based approach (gradient/pattern)
        has_defs = hasattr(effect, 'to_svg_defs')
        svg_defs = effect.to_svg_defs(f"defs_{name}") if has_defs else None

        if svg_filter:
            # Create a complete SVG demonstrating the filter
            svg_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 200 200">
  <!-- SVG Fidelity: {fidelity}% -->
  {svg_filter}
  <rect x="50" y="50" width="100" height="100" fill="#FF6600" filter="url(#filter_{name})"/>
</svg>'''
            svg_file.write_text(svg_content)

            # Render SVG to PNG for verification
            try:
                png_image = render_svg_string(svg_content, 200, 200, supersample=1)
                save_image(png_image, png_file)
                print(f"  {name}.svg + .png (fidelity: {fidelity}%)")
            except Exception as e:
                print(f"  {name}.svg (fidelity: {fidelity}%) - PNG render failed: {e}")
        elif svg_defs:
            # Effect uses defs-based approach (gradient/pattern overlay)
            # Create SVG with defs + clipped rect overlay
            svg_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 200 200">
  <!-- SVG Fidelity: {fidelity}% (via defs, not filter) -->
  <defs>
    {svg_defs}
    <clipPath id="clip_{name}">
      <rect x="50" y="50" width="100" height="100"/>
    </clipPath>
  </defs>
  <!-- Base shape -->
  <rect x="50" y="50" width="100" height="100" fill="#FF6600"/>
  <!-- Overlay with gradient/pattern, clipped to shape -->
  <rect x="50" y="50" width="100" height="100" fill="url(#defs_{name})" clip-path="url(#clip_{name})" opacity="{effect.opacity}"/>
</svg>'''
            svg_file.write_text(svg_content)

            # Render SVG to PNG for verification
            try:
                png_image = render_svg_string(svg_content, 200, 200, supersample=1)
                save_image(png_image, png_file)
                print(f"  {name}.svg + .png (fidelity: {fidelity}% - defs-based)")
            except Exception as e:
                print(f"  {name}.svg (fidelity: {fidelity}% - defs-based) - PNG render failed: {e}")
        else:
            # Effect has no SVG equivalent
            svg_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 200 200">
  <!-- SVG Fidelity: {fidelity}% - No SVG equivalent -->
  <text x="100" y="100" text-anchor="middle" font-size="14">No SVG Filter</text>
  <rect x="50" y="50" width="100" height="100" fill="#FF6600" opacity="0.3"/>
</svg>'''
            svg_file.write_text(svg_content)

            # Render SVG to PNG
            try:
                png_image = render_svg_string(svg_content, 200, 200, supersample=1)
                save_image(png_image, png_file)
                print(f"  {name}.svg + .png (fidelity: {fidelity}% - no SVG filter)")
            except Exception as e:
                print(f"  {name}.svg (fidelity: {fidelity}% - no SVG filter)")

    # Generate stroke with contour path
    print("\n\nGenerating contour-based stroke sample...")
    stroke_effect = Stroke(width=3, color=(0, 100, 200), position=StrokePosition.OUTSIDE)
    alpha_mask = deer_image[:, :, 3]  # Extract alpha channel
    svg_path = stroke_effect.to_svg_path(alpha_mask, "deer_stroke")
    if svg_path:
        h, w = deer_image.shape[:2]
        svg_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
  <!-- Contour-based stroke path (100% fidelity) -->
  {svg_path}
</svg>'''
        svg_file = svg_output_dir / "stroke_contour_path.svg"
        svg_file.write_text(svg_content)
        print(f"  stroke_contour_path.svg")

    # Generate fidelity summary
    print("\n" + "=" * 60)
    print("SVG FIDELITY SUMMARY")
    print("=" * 60)
    print(f"{'Effect':<25} {'Fidelity':>10} {'SVG Support':>15}")
    print("-" * 60)

    summary_effects = [
        ("DropShadow", DropShadow()),
        ("InnerShadow", InnerShadow()),
        ("OuterGlow", OuterGlow()),
        ("InnerGlow", InnerGlow()),
        ("BevelEmboss", BevelEmboss()),
        ("Satin", Satin()),
        ("Stroke", Stroke()),
        ("ColorOverlay", ColorOverlay()),
        ("GradientOverlay (linear)", GradientOverlay(style=GradientStyle.LINEAR)),
        ("GradientOverlay (radial)", GradientOverlay(style=GradientStyle.RADIAL)),
        ("PatternOverlay", PatternOverlay()),
    ]

    for name, effect in summary_effects:
        fidelity = effect.svg_fidelity
        can_convert = "Yes" if effect.can_convert_to_svg() else "No"
        print(f"{name:<25} {fidelity:>10}% {can_convert:>15}")

    print("=" * 60)
    print(f"\nAll samples saved to: {OUTPUT_DIR}")
    print(f"SVG filters saved to: {svg_output_dir}")


if __name__ == "__main__":
    generate_all_samples()
