"""SVG layer rendering using resvg.

This renders raw SVG content identically to the JavaScript implementation
in frontend/js/core/SVGLayer.js.

IMPORTANT: resvg is the ONLY allowed Python SVG renderer.
Do NOT switch to CairoSVG, librsvg, or other renderers.
Chrome is the JS reference; resvg is the Python reference.
"""

import io
import re
import numpy as np
from typing import Any, Dict

from PIL import Image
from resvg_py import svg_to_bytes


def _normalize_svg_dimensions(svg_content: str, width: int, height: int) -> str:
    """Normalize SVG dimensions to pixel values.

    Some SVGs use units like mm, cm, in, pt, etc. which resvg may not handle
    well without explicit pixel dimensions. This function replaces the
    width/height attributes on the root <svg> element with pixel values.

    Args:
        svg_content: Raw SVG string
        width: Target width in pixels
        height: Target height in pixels

    Returns:
        SVG string with normalized dimensions
    """
    # Find the opening <svg> tag
    svg_tag_match = re.search(r'(<svg[^>]*>)', svg_content, re.IGNORECASE | re.DOTALL)
    if not svg_tag_match:
        return svg_content

    svg_tag = svg_tag_match.group(1)
    new_svg_tag = svg_tag

    # Replace width attribute (handles units like mm, cm, px, etc.)
    new_svg_tag = re.sub(
        r'\bwidth\s*=\s*["\'][^"\']*["\']',
        f'width="{width}"',
        new_svg_tag,
        count=1
    )

    # Replace height attribute
    new_svg_tag = re.sub(
        r'\bheight\s*=\s*["\'][^"\']*["\']',
        f'height="{height}"',
        new_svg_tag,
        count=1
    )

    # If width/height weren't present, add them before the closing >
    if 'width=' not in new_svg_tag.lower():
        new_svg_tag = new_svg_tag.replace('>', f' width="{width}">', 1)
    if 'height=' not in new_svg_tag.lower():
        new_svg_tag = new_svg_tag.replace('>', f' height="{height}">', 1)

    return svg_content.replace(svg_tag, new_svg_tag, 1)


def _render_svg_string(
    svg_content: str,
    width: int,
    height: int,
    supersample: int = 2,
) -> np.ndarray:
    """Render an SVG string to RGBA numpy array using resvg.

    Args:
        svg_content: SVG string to render
        width: Output width in pixels
        height: Output height in pixels
        supersample: Render at this multiple then downscale for quality

    Returns:
        RGBA numpy array of shape (height, width, 4)
    """
    # Render at supersampled size for quality
    render_width = width * supersample
    render_height = height * supersample

    # Render SVG to PNG bytes using resvg
    png_bytes = svg_to_bytes(
        svg_string=svg_content,
        width=render_width,
        height=render_height,
    )

    # Decode PNG to PIL Image
    image = Image.open(io.BytesIO(png_bytes))
    image = image.convert('RGBA')

    # Downscale using high-quality Lanczos resampling if supersampled
    if supersample > 1:
        image = image.resize((width, height), Image.Resampling.LANCZOS)

    return np.array(image, dtype=np.uint8)


def render_svg_layer(
    layer_data: Dict[str, Any],
    width: int = None,
    height: int = None,
    supersample: int = 2,
) -> np.ndarray:
    """Render an SVG layer to an RGBA numpy array using resvg.

    This matches the JavaScript SVGLayer.render() method.

    Args:
        layer_data: Serialized SVG layer data containing:
            - svgContent: Raw SVG string
            - width, height: Layer dimensions
        width: Override output width (uses layer width if not specified)
        height: Override output height (uses layer height if not specified)
        supersample: Render at this multiple of target size then downscale.
            Use 2 for quality matching Chrome. Default 2.

    Returns:
        RGBA numpy array of rendered SVG
    """
    svg_content = layer_data.get('svgContent', '')
    layer_width = width or layer_data.get('width', 100)
    layer_height = height or layer_data.get('height', 100)

    if not svg_content:
        return np.zeros((layer_height, layer_width, 4), dtype=np.uint8)

    # Normalize SVG dimensions to pixels (handles mm, cm, etc.)
    svg_content = _normalize_svg_dimensions(svg_content, layer_width, layer_height)

    return _render_svg_string(svg_content, layer_width, layer_height, supersample=supersample)
