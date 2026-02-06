"""
Document Generator - Create SFR documents with random names, colors, and icons.

Loads the same JSON configs used by JavaScript for consistent naming.
"""

import base64
import io
import json
import random
import uuid
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw

from .sfr import SFRDocument


# Config file paths (relative to stagforge/frontend/js/config/)
STAGFORGE_DIR = Path(__file__).parent.parent
CONFIG_DIR = STAGFORGE_DIR / "frontend" / "js" / "config"

# Cached configs
_adjectives: list[dict] | None = None
_nouns: list[dict] | None = None
_icons: list[str] | None = None

# Fallback data if configs not found
FALLBACK_ADJECTIVES = [
    {"word": "luminous", "color": "#F6D365"},
    {"word": "radiant", "color": "#FDA085"},
    {"word": "velvet", "color": "#9B59B6"},
    {"word": "azure", "color": "#5DADE2"},
    {"word": "emerald", "color": "#55EFC4"},
    {"word": "coral", "color": "#FF7675"},
    {"word": "golden", "color": "#F9CA24"},
    {"word": "silver", "color": "#B2BEC3"},
]

FALLBACK_NOUNS = [
    {"word": "canvas", "icon": "🎨"},
    {"word": "snapshot", "icon": "📷"},
    {"word": "sketch", "icon": "✏️"},
    {"word": "portrait", "icon": "🖼️"},
    {"word": "landscape", "icon": "🏞️"},
    {"word": "palette", "icon": "🎨"},
    {"word": "brushstroke", "icon": "🖌️"},
    {"word": "gradient", "icon": "🌈"},
]

FALLBACK_ICONS = [
    "🎨", "🖼️", "🖌️", "✏️", "✨", "💫", "⭐", "🌟",
    "📷", "📸", "💡", "🔥", "❤️", "💙", "💜", "🌈",
]


def _load_configs() -> None:
    """Load JSON configs from frontend/js/config/."""
    global _adjectives, _nouns, _icons

    # Load adjectives
    adj_path = CONFIG_DIR / "document-adjectives.json"
    if adj_path.exists():
        with open(adj_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            _adjectives = data.get("adjectives", FALLBACK_ADJECTIVES)
    else:
        _adjectives = FALLBACK_ADJECTIVES

    # Load nouns
    noun_path = CONFIG_DIR / "document-nouns.json"
    if noun_path.exists():
        with open(noun_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            _nouns = data.get("nouns", FALLBACK_NOUNS)
    else:
        _nouns = FALLBACK_NOUNS

    # Load icons
    icon_path = CONFIG_DIR / "icon-picker.json"
    if icon_path.exists():
        with open(icon_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            _icons = data.get("icons", FALLBACK_ICONS)
    else:
        _icons = FALLBACK_ICONS


def get_adjectives() -> list[dict]:
    """Get list of adjectives with colors."""
    if _adjectives is None:
        _load_configs()
    return _adjectives or FALLBACK_ADJECTIVES


def get_nouns() -> list[dict]:
    """Get list of nouns with icons."""
    if _nouns is None:
        _load_configs()
    return _nouns or FALLBACK_NOUNS


def get_icons() -> list[str]:
    """Get list of emoji icons."""
    if _icons is None:
        _load_configs()
    return _icons or FALLBACK_ICONS


def generate_document_identity() -> dict:
    """
    Generate a random document identity (name, icon, color).

    Returns:
        Dict with 'name', 'icon', 'color' keys
    """
    adjectives = get_adjectives()
    nouns = get_nouns()

    adj = random.choice(adjectives)
    noun = random.choice(nouns)

    # Capitalize words for title case
    name = f"{adj['word'].capitalize()} {noun['word'].capitalize()}"

    return {
        "name": name,
        "icon": noun["icon"],
        "color": adj["color"],
    }


def generate_document_name() -> str:
    """Generate a random document name."""
    return generate_document_identity()["name"]


def generate_document_color() -> str:
    """Generate a random document color."""
    return random.choice(get_adjectives())["color"]


def generate_document_icon() -> str:
    """Generate a random document icon."""
    return random.choice(get_nouns())["icon"]


def create_solid_image_data_url(
    width: int, height: int, color: tuple[int, int, int, int] = (255, 0, 0, 255)
) -> str:
    """Create a solid color image as a data URL."""
    img = Image.new("RGBA", (width, height), color)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    b64 = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def create_gradient_image_data_url(
    width: int,
    height: int,
    color1: tuple[int, int, int, int] = (255, 100, 100, 255),
    color2: tuple[int, int, int, int] = (100, 100, 255, 255),
    direction: str = "horizontal",
) -> str:
    """Create a gradient image as a data URL."""
    img = Image.new("RGBA", (width, height))
    draw = ImageDraw.Draw(img)

    for i in range(width if direction == "horizontal" else height):
        ratio = i / (width if direction == "horizontal" else height)
        r = int(color1[0] + (color2[0] - color1[0]) * ratio)
        g = int(color1[1] + (color2[1] - color1[1]) * ratio)
        b = int(color1[2] + (color2[2] - color1[2]) * ratio)
        a = int(color1[3] + (color2[3] - color1[3]) * ratio)

        if direction == "horizontal":
            draw.line([(i, 0), (i, height)], fill=(r, g, b, a))
        else:
            draw.line([(0, i), (width, i)], fill=(r, g, b, a))

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    b64 = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def create_checkerboard_image_data_url(
    width: int,
    height: int,
    color1: tuple[int, int, int, int] = (200, 200, 200, 255),
    color2: tuple[int, int, int, int] = (255, 255, 255, 255),
    cell_size: int = 20,
) -> str:
    """Create a checkerboard pattern image as a data URL."""
    img = Image.new("RGBA", (width, height))

    for y in range(0, height, cell_size):
        for x in range(0, width, cell_size):
            color = color1 if ((x // cell_size) + (y // cell_size)) % 2 == 0 else color2
            for dy in range(min(cell_size, height - y)):
                for dx in range(min(cell_size, width - x)):
                    img.putpixel((x + dx, y + dy), color)

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    b64 = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def create_sample_svg(
    width: int = 100, height: int = 100, shape: str = "circle", color: str = "#3498DB"
) -> str:
    """Create a simple SVG string."""
    if shape == "circle":
        return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">
  <circle cx="{width//2}" cy="{height//2}" r="{min(width, height)//3}" fill="{color}" />
</svg>'''
    elif shape == "rect":
        return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">
  <rect x="{width//4}" y="{height//4}" width="{width//2}" height="{height//2}" fill="{color}" rx="5" />
</svg>'''
    elif shape == "star":
        cx, cy = width // 2, height // 2
        r = min(width, height) // 3
        points = []
        for i in range(5):
            # Outer point
            angle = -90 + i * 72
            import math

            px = cx + r * math.cos(math.radians(angle))
            py = cy + r * math.sin(math.radians(angle))
            points.append(f"{px},{py}")
            # Inner point
            angle += 36
            px = cx + r * 0.4 * math.cos(math.radians(angle))
            py = cy + r * 0.4 * math.sin(math.radians(angle))
            points.append(f"{px},{py}")
        return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">
  <polygon points="{' '.join(points)}" fill="{color}" />
</svg>'''
    else:
        # Default triangle
        return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">
  <polygon points="{width//2},{height//4} {width*3//4},{height*3//4} {width//4},{height*3//4}" fill="{color}" />
</svg>'''


def create_empty_document(
    width: int = 800,
    height: int = 600,
    name: Optional[str] = None,
    icon: Optional[str] = None,
    color: Optional[str] = None,
    with_background: bool = True,
) -> SFRDocument:
    """
    Create an empty SFR document.

    Args:
        width: Document width in pixels
        height: Document height in pixels
        name: Document name (random if not provided)
        icon: Document icon emoji (random if not provided)
        color: Document color hex (random if not provided)
        with_background: Include a white background layer

    Returns:
        SFRDocument instance
    """
    identity = generate_document_identity()

    doc = SFRDocument(
        id=str(uuid.uuid4()),
        name=name or identity["name"],
        icon=icon or identity["icon"],
        color=color or identity["color"],
        width=width,
        height=height,
        layers=[],
    )

    if with_background:
        # Add white background layer
        doc.layers.append(
            {
                "id": str(uuid.uuid4()),
                "type": "raster",
                "name": "Background",
                "width": width,
                "height": height,
                "offsetX": 0,
                "offsetY": 0,
                "opacity": 1.0,
                "blendMode": "normal",
                "visible": True,
                "locked": False,
                "imageData": create_solid_image_data_url(width, height, (255, 255, 255, 255)),
            }
        )

    return doc


def create_sample_document(
    width: int = 800,
    height: int = 600,
    name: Optional[str] = None,
    include_raster: bool = True,
    include_text: bool = True,
    include_svg: bool = True,
    include_gradient: bool = False,
) -> SFRDocument:
    """
    Create a sample SFR document with various layer types.

    Args:
        width: Document width in pixels
        height: Document height in pixels
        name: Document name (random if not provided)
        include_raster: Include a raster layer with painted content
        include_text: Include a text layer
        include_svg: Include an SVG layer
        include_gradient: Include a gradient background

    Returns:
        SFRDocument instance
    """
    identity = generate_document_identity()

    doc = SFRDocument(
        id=str(uuid.uuid4()),
        name=name or identity["name"],
        icon=identity["icon"],
        color=identity["color"],
        width=width,
        height=height,
        layers=[],
    )

    # Background layer
    if include_gradient:
        bg_image = create_gradient_image_data_url(
            width, height, (240, 240, 255, 255), (255, 240, 240, 255), "vertical"
        )
    else:
        bg_image = create_solid_image_data_url(width, height, (255, 255, 255, 255))

    doc.layers.append(
        {
            "id": str(uuid.uuid4()),
            "type": "raster",
            "name": "Background",
            "width": width,
            "height": height,
            "offsetX": 0,
            "offsetY": 0,
            "opacity": 1.0,
            "blendMode": "normal",
            "visible": True,
            "locked": True,
            "imageData": bg_image,
        }
    )

    # Raster layer with some painted content
    if include_raster:
        # Create an image with some shapes
        img = Image.new("RGBA", (200, 200), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse([20, 20, 180, 180], fill=(255, 100, 100, 200))
        draw.rectangle([60, 60, 140, 140], fill=(100, 100, 255, 200))

        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        paint_data = f"data:image/png;base64,{base64.b64encode(buffer.getvalue()).decode('ascii')}"

        doc.layers.append(
            {
                "id": str(uuid.uuid4()),
                "type": "raster",
                "name": "Paint Layer",
                "width": 200,
                "height": 200,
                "offsetX": 50,
                "offsetY": 50,
                "opacity": 1.0,
                "blendMode": "normal",
                "visible": True,
                "locked": False,
                "imageData": paint_data,
            }
        )

    # SVG layer
    if include_svg:
        svg_content = create_sample_svg(150, 150, "star", "#F1C40F")
        doc.layers.append(
            {
                "id": str(uuid.uuid4()),
                "type": "svg",
                "name": "Star Shape",
                "width": 150,
                "height": 150,
                "offsetX": width - 200,
                "offsetY": 50,
                "opacity": 1.0,
                "blendMode": "normal",
                "visible": True,
                "locked": False,
                "svgContent": svg_content,
                "naturalWidth": 150,
                "naturalHeight": 150,
            }
        )

    # Text layer
    if include_text:
        doc.layers.append(
            {
                "id": str(uuid.uuid4()),
                "type": "text",
                "name": "Sample Text",
                "width": 300,
                "height": 60,
                "offsetX": (width - 300) // 2,
                "offsetY": height - 100,
                "opacity": 1.0,
                "blendMode": "normal",
                "visible": True,
                "locked": False,
                "text": doc.name,
                "fontSize": 32,
                "fontFamily": "Arial",
                "color": "#2C3E50",
                "runs": [
                    {
                        "text": doc.name,
                        "fontSize": 32,
                        "fontFamily": "Arial",
                        "color": "#2C3E50",
                    }
                ],
            }
        )

    return doc
