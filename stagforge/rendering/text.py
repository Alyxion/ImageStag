"""Text layer rendering.

This MUST produce identical output to the JavaScript implementation
in frontend/js/core/TextLayer.js.

Algorithm:
- Render text at 4x resolution
- Apply Lanczos-3 downscaling to final size
"""

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from typing import Any, List, Dict, Optional, Tuple

from .lanczos import lanczos_resample


# Default render scale (must match JS _renderScale)
RENDER_SCALE = 4


def get_font(
    font_family: str,
    font_size: int,
    font_weight: str = "normal",
    font_style: str = "normal",
) -> ImageFont.FreeTypeFont:
    """Get a PIL font matching the specified parameters.

    Args:
        font_family: Font family name
        font_size: Font size in pixels
        font_weight: 'normal' or 'bold'
        font_style: 'normal' or 'italic'

    Returns:
        PIL font object
    """
    # Map common font families to system fonts
    font_map = {
        "Arial": "DejaVuSans",
        "Helvetica": "DejaVuSans",
        "sans-serif": "DejaVuSans",
        "Times New Roman": "DejaVuSerif",
        "Times": "DejaVuSerif",
        "serif": "DejaVuSerif",
        "Courier New": "DejaVuSansMono",
        "Courier": "DejaVuSansMono",
        "monospace": "DejaVuSansMono",
    }

    base_font = font_map.get(font_family, "DejaVuSans")

    # Build font filename based on weight/style
    suffix = ""
    if font_weight == "bold" and font_style == "italic":
        suffix = "-BoldOblique"
    elif font_weight == "bold":
        suffix = "-Bold"
    elif font_style == "italic":
        suffix = "-Oblique"

    font_name = f"{base_font}{suffix}.ttf"

    try:
        return ImageFont.truetype(font_name, font_size)
    except OSError:
        # Fallback to basic font
        try:
            return ImageFont.truetype("DejaVuSans.ttf", font_size)
        except OSError:
            return ImageFont.load_default()


def parse_color(color: str) -> Tuple[int, int, int, int]:
    """Parse a CSS color string to RGBA tuple.

    Args:
        color: CSS color string (e.g., '#FF0000', 'rgb(255,0,0)')

    Returns:
        (R, G, B, A) tuple with values 0-255
    """
    if color.startswith("#"):
        color = color.lstrip("#")
        if len(color) == 3:
            color = "".join(c * 2 for c in color)
        if len(color) == 6:
            return (
                int(color[0:2], 16),
                int(color[2:4], 16),
                int(color[4:6], 16),
                255,
            )
        elif len(color) == 8:
            return (
                int(color[0:2], 16),
                int(color[2:4], 16),
                int(color[4:6], 16),
                int(color[6:8], 16),
            )
    elif color.startswith("rgb"):
        # Parse rgb() or rgba()
        import re
        match = re.match(r"rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*([\d.]+))?\)", color)
        if match:
            r, g, b = int(match.group(1)), int(match.group(2)), int(match.group(3))
            a = int(float(match.group(4) or 1) * 255)
            return (r, g, b, a)

    # Default to black
    return (0, 0, 0, 255)


def measure_text_layer(
    runs: List[Dict[str, Any]],
    default_font_size: int = 24,
    default_font_family: str = "Arial",
    default_font_weight: str = "normal",
    default_font_style: str = "normal",
    line_height: float = 1.2,
    padding: int = 4,
) -> Tuple[int, int, List[float], int]:
    """Measure text dimensions.

    Args:
        runs: List of text runs
        default_*: Default typography settings
        line_height: Line height multiplier
        padding: Padding around text

    Returns:
        (width, height, line_heights, left_overhang)
    """
    # Parse runs into lines
    lines: List[List[Dict]] = [[]]
    current_line = 0

    for run in runs:
        text = run.get("text", "")
        parts = text.split("\n")
        for i, part in enumerate(parts):
            if i > 0:
                current_line += 1
                lines.append([])
            if part:
                lines[current_line].append({"run": run, "text": part})

    # Measure each line
    max_width = 0
    total_height = 0
    line_heights = []
    max_left_overhang = 0

    dummy_img = Image.new("RGBA", (1, 1))
    draw = ImageDraw.Draw(dummy_img)

    for line_runs in lines:
        line_width = 0
        line_max_font_size = default_font_size

        for item in line_runs:
            run = item["run"]
            text = item["text"]

            font_size = run.get("fontSize", default_font_size)
            font_family = run.get("fontFamily", default_font_family)
            font_weight = run.get("fontWeight", default_font_weight)
            font_style = run.get("fontStyle", default_font_style)

            font = get_font(font_family, font_size, font_weight, font_style)
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]

            # Check for left overhang
            if bbox[0] < 0:
                max_left_overhang = max(max_left_overhang, -bbox[0])

            line_width += text_width
            line_max_font_size = max(line_max_font_size, font_size)

        if not line_runs:
            line_max_font_size = default_font_size

        line_h = line_max_font_size * line_height
        line_heights.append(line_h)
        max_width = max(max_width, line_width)
        total_height += line_h

    extra_left = int(np.ceil(max_left_overhang))

    return (
        int(np.ceil(max_width)) + padding * 2 + extra_left,
        int(np.ceil(total_height)) + padding * 2,
        line_heights,
        extra_left,
    )


def render_text_layer(
    layer_data: Dict[str, Any],
    output_width: Optional[int] = None,
    output_height: Optional[int] = None,
) -> np.ndarray:
    """Render a text layer to an RGBA numpy array.

    This matches the JavaScript TextLayer.render() method exactly.

    Args:
        layer_data: Serialized text layer data containing:
            - runs: Array of text runs with text, fontSize, fontFamily, etc.
            - fontSize, fontFamily, fontWeight, fontStyle: Default styles
            - color: Default text color
            - textAlign: 'left', 'center', or 'right'
            - lineHeight: Line height multiplier
        output_width: Override output width (uses measured if None)
        output_height: Override output height (uses measured if None)

    Returns:
        RGBA numpy array of rendered text
    """
    runs = layer_data.get("runs", [])
    if not runs:
        # Empty text layer
        width = output_width or 100
        height = output_height or 32
        return np.zeros((height, width, 4), dtype=np.uint8)

    # Get default styles
    default_font_size = layer_data.get("fontSize", 24)
    default_font_family = layer_data.get("fontFamily", "Arial")
    default_font_weight = layer_data.get("fontWeight", "normal")
    default_font_style = layer_data.get("fontStyle", "normal")
    default_color = layer_data.get("color", "#000000")
    text_align = layer_data.get("textAlign", "left")
    line_height = layer_data.get("lineHeight", 1.2)
    padding = 4

    # Measure text
    width, height, line_heights, left_overhang = measure_text_layer(
        runs,
        default_font_size,
        default_font_family,
        default_font_weight,
        default_font_style,
        line_height,
        padding,
    )

    if output_width:
        width = output_width
    if output_height:
        height = output_height

    # Render at 4x resolution
    hi_res_width = width * RENDER_SCALE
    hi_res_height = height * RENDER_SCALE

    hi_res_img = Image.new("RGBA", (hi_res_width, hi_res_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(hi_res_img)

    # Parse runs into lines
    lines: List[List[Dict]] = [[]]
    current_line = 0

    for run in runs:
        text = run.get("text", "")
        parts = text.split("\n")
        for i, part in enumerate(parts):
            if i > 0:
                current_line += 1
                lines.append([])
            if part:
                lines[current_line].append({"run": run, "text": part})

    # Render each line
    y = padding * RENDER_SCALE

    for line_idx, line_runs in enumerate(lines):
        line_h = line_heights[line_idx] if line_idx < len(line_heights) else default_font_size * line_height

        # Calculate line width for alignment
        line_width = 0
        for item in line_runs:
            run = item["run"]
            text = item["text"]
            font_size = run.get("fontSize", default_font_size) * RENDER_SCALE
            font_family = run.get("fontFamily", default_font_family)
            font_weight = run.get("fontWeight", default_font_weight)
            font_style = run.get("fontStyle", default_font_style)

            font = get_font(font_family, font_size, font_weight, font_style)
            bbox = draw.textbbox((0, 0), text, font=font)
            line_width += bbox[2] - bbox[0]

        # Calculate starting X based on alignment
        left_offset = (padding + left_overhang) * RENDER_SCALE
        x = left_offset
        if text_align == "center":
            x = (hi_res_width - line_width) // 2
        elif text_align == "right":
            x = hi_res_width - padding * RENDER_SCALE - line_width

        # Render each run in the line
        for item in line_runs:
            run = item["run"]
            text = item["text"]

            font_size = run.get("fontSize", default_font_size) * RENDER_SCALE
            font_family = run.get("fontFamily", default_font_family)
            font_weight = run.get("fontWeight", default_font_weight)
            font_style = run.get("fontStyle", default_font_style)
            color = run.get("color", default_color)

            font = get_font(font_family, font_size, font_weight, font_style)
            rgba = parse_color(color)

            # Vertical alignment within line
            run_font_size = run.get("fontSize", default_font_size)
            run_line_height = run_font_size * line_height * RENDER_SCALE
            y_offset = (line_h * RENDER_SCALE - run_line_height) / 2

            draw.text((x, y + y_offset), text, font=font, fill=rgba)

            bbox = draw.textbbox((0, 0), text, font=font)
            x += bbox[2] - bbox[0]

        y += line_h * RENDER_SCALE

    # Convert to numpy array
    hi_res_array = np.array(hi_res_img)

    # Lanczos downscale from 4x to 1x
    result = lanczos_resample(hi_res_array, width, height, a=3)

    return result
