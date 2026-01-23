"""Vector layer rendering using resvg.

This MUST produce identical output to the JavaScript implementation
in frontend/js/core/VectorLayer.js and VectorShape.js.

IMPORTANT: resvg is the ONLY allowed Python SVG renderer.
Do NOT switch to CairoSVG, librsvg, or other renderers.
Chrome is the JS reference; resvg is the Python reference.

Algorithm:
- Convert shapes to SVG
- Render SVG using resvg
"""

import numpy as np
from typing import Any, Dict, List, Optional
from io import BytesIO

try:
    import resvg_py
    HAS_RESVG = True
except ImportError:
    HAS_RESVG = False


def shape_to_svg_element(shape: Dict[str, Any]) -> str:
    """Convert a shape data dict to an SVG element string.

    Args:
        shape: Shape data from VectorShape.toData()

    Returns:
        SVG element string
    """
    shape_type = shape.get("type", "")
    fill_color = shape.get("fillColor", "#000000")
    stroke_color = shape.get("strokeColor", "#000000")
    stroke_width = shape.get("strokeWidth", 1)
    do_fill = shape.get("fill", True)
    do_stroke = shape.get("stroke", False)
    opacity = shape.get("opacity", 1.0)

    fill = fill_color if do_fill else "none"
    stroke = stroke_color if do_stroke else "none"

    style = f'fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}" opacity="{opacity}"'

    if shape_type == "rect":
        x = shape.get("x", 0)
        y = shape.get("y", 0)
        width = shape.get("width", 0)
        height = shape.get("height", 0)
        corner_radius = shape.get("cornerRadius", 0)
        if corner_radius > 0:
            r = min(corner_radius, width / 2, height / 2)
            return f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="{r}" ry="{r}" {style}/>'
        return f'<rect x="{x}" y="{y}" width="{width}" height="{height}" {style}/>'

    elif shape_type == "ellipse":
        cx = shape.get("cx", 0)
        cy = shape.get("cy", 0)
        rx = abs(shape.get("rx", 0))
        ry = abs(shape.get("ry", 0))
        return f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" {style}/>'

    elif shape_type == "line":
        x1 = shape.get("x1", 0)
        y1 = shape.get("y1", 0)
        x2 = shape.get("x2", 0)
        y2 = shape.get("y2", 0)
        linecap = shape.get("lineCap", "round")
        # Lines don't fill, only stroke
        return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke_color}" stroke-width="{stroke_width}" stroke-linecap="{linecap}" opacity="{opacity}"/>'

    elif shape_type == "polygon":
        points = shape.get("points", [])
        if not points:
            return ""
        closed = shape.get("closed", True)
        # Points can be [{x, y}] or [[x, y]] format
        if isinstance(points[0], dict):
            points_str = " ".join(f"{p['x']},{p['y']}" for p in points)
        else:
            points_str = " ".join(f"{p[0]},{p[1]}" for p in points)
        if closed:
            return f'<polygon points="{points_str}" {style}/>'
        else:
            return f'<polyline points="{points_str}" {style}/>'

    elif shape_type == "path":
        # Path can have 'd' directly or need to be built from points
        d = shape.get("d", "")
        if not d and "points" in shape:
            d = _build_path_d(shape)
        if not d:
            return ""
        return f'<path d="{d}" {style}/>'

    return ""


def _build_path_d(shape: Dict[str, Any]) -> str:
    """Build SVG path 'd' attribute from path shape data.

    Args:
        shape: Path shape data with points array

    Returns:
        SVG path 'd' attribute string
    """
    points = shape.get("points", [])
    if len(points) < 2:
        return ""

    parts = [f"M {points[0]['x']} {points[0]['y']}"]

    for i in range(1, len(points)):
        from_pt = points[i - 1]
        to_pt = points[i]

        h_out = _get_handle_abs(from_pt, "handleOut")
        h_in = _get_handle_abs(to_pt, "handleIn")

        if h_out and h_in:
            # Cubic bezier
            parts.append(f"C {h_out['x']} {h_out['y']} {h_in['x']} {h_in['y']} {to_pt['x']} {to_pt['y']}")
        elif h_out:
            # Quadratic
            parts.append(f"Q {h_out['x']} {h_out['y']} {to_pt['x']} {to_pt['y']}")
        elif h_in:
            # Quadratic
            parts.append(f"Q {h_in['x']} {h_in['y']} {to_pt['x']} {to_pt['y']}")
        else:
            # Line
            parts.append(f"L {to_pt['x']} {to_pt['y']}")

    # Close path if needed
    closed = shape.get("closed", False)
    if closed and len(points) > 2:
        from_pt = points[-1]
        to_pt = points[0]
        h_out = _get_handle_abs(from_pt, "handleOut")
        h_in = _get_handle_abs(to_pt, "handleIn")

        if h_out and h_in:
            parts.append(f"C {h_out['x']} {h_out['y']} {h_in['x']} {h_in['y']} {to_pt['x']} {to_pt['y']}")
        elif h_out:
            parts.append(f"Q {h_out['x']} {h_out['y']} {to_pt['x']} {to_pt['y']}")
        elif h_in:
            parts.append(f"Q {h_in['x']} {h_in['y']} {to_pt['x']} {to_pt['y']}")
        parts.append("Z")

    return " ".join(parts)


def _get_handle_abs(point: Dict[str, Any], handle_name: str) -> Optional[Dict[str, float]]:
    """Get absolute position of a bezier handle.

    Args:
        point: Path point data
        handle_name: 'handleIn' or 'handleOut'

    Returns:
        Absolute position dict or None
    """
    handle = point.get(handle_name)
    if not handle:
        return None
    return {
        "x": point["x"] + handle["x"],
        "y": point["y"] + handle["y"]
    }


def shapes_to_svg(
    shapes: List[Dict[str, Any]],
    width: int,
    height: int,
    render_scale: int = 1,
) -> str:
    """Convert a list of shapes to an SVG document.

    Args:
        shapes: List of shape data dicts
        width: SVG logical width (viewBox)
        height: SVG logical height (viewBox)
        render_scale: Multiply width/height attributes for higher resolution render
            while keeping viewBox at logical size. Useful for supersampling.

    Returns:
        SVG document string
    """
    elements = [shape_to_svg_element(shape) for shape in shapes]
    elements_str = "\n  ".join(e for e in elements if e)

    # For supersampling: render at higher resolution by scaling width/height
    # but keep viewBox at logical coordinates so shapes render at correct positions
    render_width = width * render_scale
    render_height = height * render_scale

    # Use shape-rendering="crispEdges" for cross-platform parity.
    # This disables anti-aliasing, ensuring Chrome and resvg produce
    # identical pixel output. The AA algorithms differ between renderers,
    # but with crispEdges we achieve <0.1% pixel match.
    #
    # For production use where AA is desired, use "geometricPrecision"
    # and accept 1-4% pixel difference on curves/diagonals.
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{render_width}" height="{render_height}" viewBox="0 0 {width} {height}" shape-rendering="crispEdges">
  {elements_str}
</svg>'''


def render_vector_layer(
    layer_data: Dict[str, Any],
    width: Optional[int] = None,
    height: Optional[int] = None,
    supersample: int = 1,
) -> np.ndarray:
    """Render a vector layer to an RGBA numpy array using resvg.

    This matches the JavaScript VectorLayer.render() method.

    Args:
        layer_data: Serialized vector layer data containing:
            - shapes: Array of shape data
            - width, height: Layer dimensions
        width: Override output width
        height: Override output height
        supersample: Render at this multiple of target size then downscale.
            Use 2 or 4 for higher quality anti-aliasing. Default 1 (no supersampling).

    Returns:
        RGBA numpy array of rendered vector shapes
    """
    from PIL import Image

    shapes = layer_data.get("shapes", [])
    layer_width = width or layer_data.get("width", 100)
    layer_height = height or layer_data.get("height", 100)

    if not shapes:
        return np.zeros((layer_height, layer_width, 4), dtype=np.uint8)

    scale = max(1, supersample)

    # Convert shapes to SVG with optional supersampling
    # Using render_scale keeps viewBox at logical size but renders at higher resolution
    svg_str = shapes_to_svg(shapes, layer_width, layer_height, render_scale=scale)

    if not HAS_RESVG:
        print("Warning: resvg-py not available, vector rendering disabled")
        return np.zeros((layer_height, layer_width, 4), dtype=np.uint8)

    # Render SVG using resvg (the ONLY allowed Python SVG renderer)
    try:
        from resvg_py import svg_to_bytes
        png_bytes = svg_to_bytes(svg_string=svg_str)
        img = Image.open(BytesIO(png_bytes)).convert("RGBA")

        # Downscale if supersampling was used
        if scale > 1:
            img = img.resize(
                (layer_width, layer_height),
                Image.Resampling.BOX  # BOX is best for integer downscaling
            )

        return np.array(img)
    except Exception as e:
        print(f"Warning: resvg rendering failed: {e}")
        return np.zeros((layer_height, layer_width, 4), dtype=np.uint8)


def _scale_svg_dimensions(svg_str: str, scale: int) -> str:
    """Scale the width/height attributes of an SVG document.

    Only modifies the <svg> root element's width/height, not child elements.
    Keeps viewBox unchanged so the content renders at higher resolution.

    Args:
        svg_str: SVG document string
        scale: Scale factor for width/height

    Returns:
        Modified SVG string with scaled dimensions
    """
    import re

    # Find just the <svg ...> opening tag
    match = re.search(r'(<svg[^>]*>)', svg_str)
    if not match:
        return svg_str

    svg_tag = match.group(1)

    # Replace width and height in just this tag
    def replace_dim(m):
        attr = m.group(1)
        val = int(m.group(2))
        return f'{attr}="{val * scale}"'

    new_svg_tag = re.sub(r'(width)="(\d+)"', replace_dim, svg_tag, count=1)
    new_svg_tag = re.sub(r'(height)="(\d+)"', replace_dim, new_svg_tag, count=1)

    return svg_str.replace(svg_tag, new_svg_tag, 1)


def scale_shape(
    shape: Dict[str, Any],
    scale_x: float,
    scale_y: float,
    center_x: Optional[float] = None,
    center_y: Optional[float] = None,
) -> Dict[str, Any]:
    """Scale a shape by factors around a center point.

    This mirrors the JavaScript VectorShape.scale() implementations exactly.

    Args:
        shape: Shape data dict to scale (will be modified in place)
        scale_x: Horizontal scale factor
        scale_y: Vertical scale factor
        center_x: Center X coordinate (defaults to shape center)
        center_y: Center Y coordinate (defaults to shape center)

    Returns:
        The modified shape dict
    """
    shape_type = shape.get("type", "")

    if shape_type == "rect":
        x = shape.get("x", 0)
        y = shape.get("y", 0)
        w = shape.get("width", 0)
        h = shape.get("height", 0)

        cx = center_x if center_x is not None else (x + w / 2)
        cy = center_y if center_y is not None else (y + h / 2)

        shape["x"] = cx + (x - cx) * scale_x
        shape["y"] = cy + (y - cy) * scale_y
        shape["width"] = w * abs(scale_x)
        shape["height"] = h * abs(scale_y)

        if "cornerRadius" in shape:
            shape["cornerRadius"] = shape["cornerRadius"] * min(abs(scale_x), abs(scale_y))

    elif shape_type == "ellipse":
        ex = shape.get("cx", 0)
        ey = shape.get("cy", 0)
        rx = shape.get("rx", 0)
        ry = shape.get("ry", 0)

        cx = center_x if center_x is not None else ex
        cy = center_y if center_y is not None else ey

        shape["cx"] = cx + (ex - cx) * scale_x
        shape["cy"] = cy + (ey - cy) * scale_y
        shape["rx"] = rx * abs(scale_x)
        shape["ry"] = ry * abs(scale_y)

    elif shape_type == "line":
        x1 = shape.get("x1", 0)
        y1 = shape.get("y1", 0)
        x2 = shape.get("x2", 0)
        y2 = shape.get("y2", 0)

        min_x = min(x1, x2)
        max_x = max(x1, x2)
        min_y = min(y1, y2)
        max_y = max(y1, y2)
        bounds_w = max_x - min_x or 1
        bounds_h = max_y - min_y or 1

        cx = center_x if center_x is not None else (min_x + bounds_w / 2)
        cy = center_y if center_y is not None else (min_y + bounds_h / 2)

        shape["x1"] = cx + (x1 - cx) * scale_x
        shape["y1"] = cy + (y1 - cy) * scale_y
        shape["x2"] = cx + (x2 - cx) * scale_x
        shape["y2"] = cy + (y2 - cy) * scale_y

        if "strokeWidth" in shape:
            shape["strokeWidth"] = shape["strokeWidth"] * min(abs(scale_x), abs(scale_y))

    elif shape_type == "polygon":
        points = shape.get("points", [])
        if not points:
            return shape

        # Calculate bounds
        if isinstance(points[0], dict):
            xs = [p["x"] for p in points]
            ys = [p["y"] for p in points]
        else:
            xs = [p[0] for p in points]
            ys = [p[1] for p in points]

        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        bounds_w = max_x - min_x or 1
        bounds_h = max_y - min_y or 1

        cx = center_x if center_x is not None else (min_x + bounds_w / 2)
        cy = center_y if center_y is not None else (min_y + bounds_h / 2)

        if isinstance(points[0], dict):
            for pt in points:
                pt["x"] = cx + (pt["x"] - cx) * scale_x
                pt["y"] = cy + (pt["y"] - cy) * scale_y
        else:
            for pt in points:
                pt[0] = cx + (pt[0] - cx) * scale_x
                pt[1] = cy + (pt[1] - cy) * scale_y

    elif shape_type == "path":
        points = shape.get("points", [])
        if not points:
            return shape

        # Calculate bounds by sampling (matches JS getBounds)
        xs, ys = [], []
        for pt in points:
            xs.append(pt.get("x", 0))
            ys.append(pt.get("y", 0))

        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        bounds_w = max_x - min_x or 1
        bounds_h = max_y - min_y or 1

        cx = center_x if center_x is not None else (min_x + bounds_w / 2)
        cy = center_y if center_y is not None else (min_y + bounds_h / 2)

        for pt in points:
            # Scale anchor point
            pt["x"] = cx + (pt["x"] - cx) * scale_x
            pt["y"] = cy + (pt["y"] - cy) * scale_y

            # Scale handles (they are RELATIVE to anchor, so just multiply)
            if pt.get("handleIn"):
                pt["handleIn"]["x"] *= scale_x
                pt["handleIn"]["y"] *= scale_y
            if pt.get("handleOut"):
                pt["handleOut"]["x"] *= scale_x
                pt["handleOut"]["y"] *= scale_y

    return shape


def render_svg_string(
    svg_str: str,
    width: int,
    height: int,
    supersample: int = 1,
) -> np.ndarray:
    """Render an SVG string directly.

    Uses supersampling (render at higher resolution then downscale)
    to match browser anti-aliasing quality.

    Args:
        svg_str: SVG document string
        width: Output width
        height: Output height
        supersample: Render at this multiple of target size then downscale.
            Default 2 for quality matching Chrome. Use 1 to disable.

    Returns:
        RGBA numpy array
    """
    if not HAS_RESVG:
        return np.zeros((height, width, 4), dtype=np.uint8)

    try:
        from resvg_py import svg_to_bytes
        from PIL import Image

        scale = max(1, supersample)

        # Scale SVG dimensions for supersampling
        if scale > 1:
            svg_str = _scale_svg_dimensions(svg_str, scale)

        # svg_to_bytes returns PNG bytes directly
        png_bytes = svg_to_bytes(svg_string=svg_str)

        # Load PNG and convert to RGBA
        img = Image.open(BytesIO(png_bytes))
        img = img.convert("RGBA")

        # Downscale if supersampling was used
        if scale > 1:
            img = img.resize(
                (width, height),
                Image.Resampling.LANCZOS
            )

        return np.array(img)

    except Exception as e:
        print(f"Warning: SVG rendering failed: {e}")
        return np.zeros((height, width, 4), dtype=np.uint8)
