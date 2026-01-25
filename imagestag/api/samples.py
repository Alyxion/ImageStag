"""Sample assets API with dynamic skimage rendering and SVG rasterization."""
from fastapi import APIRouter, Response, Query
from fastapi.responses import FileResponse
from pathlib import Path
from io import BytesIO
from PIL import Image
import numpy as np

router = APIRouter(tags=["samples"])
SAMPLES_DIR = Path(__file__).parent.parent / "samples"

# Available skimage samples
SKIMAGE_SAMPLES = [
    "astronaut", "camera", "chelsea", "clock", "coffee", "coins",
    "horse", "hubble_deep_field", "moon", "page", "rocket",
    "brick", "grass", "gravel"
]


def _render_svg_to_image(svg_path: Path, width: int, height: int) -> Image.Image:
    """Render SVG to PIL Image at specified size.

    Uses cairosvg for high-quality SVG rendering.
    """
    import cairosvg

    # Render SVG to PNG bytes at the requested size
    png_bytes = cairosvg.svg2png(
        url=str(svg_path),
        output_width=width,
        output_height=height,
    )
    return Image.open(BytesIO(png_bytes))


@router.get("/samples")
async def list_samples():
    """List all available samples."""
    # Static images
    images_dir = SAMPLES_DIR / "images"
    static_images = []
    if images_dir.exists():
        static_images = [f.name for f in images_dir.glob("*.*") if f.is_file()]

    # SVG categories
    svgs = {}
    svgs_dir = SAMPLES_DIR / "svgs"
    if svgs_dir.exists():
        for cat_dir in svgs_dir.iterdir():
            if cat_dir.is_dir():
                svgs[cat_dir.name] = [f.name for f in cat_dir.glob("*.svg")]

    return {
        "skimage": SKIMAGE_SAMPLES,
        "static": static_images,
        "svgs": svgs,
    }


@router.get("/samples/skimage/{name}.{format}")
async def get_skimage_sample(
    name: str,
    format: str,
    quality: int = Query(default=85, ge=1, le=100),
):
    """Render skimage sample to PNG or JPG on demand.

    Examples:
        /imgstag/samples/skimage/astronaut.png
        /imgstag/samples/skimage/astronaut.jpg?quality=85
    """
    if name not in SKIMAGE_SAMPLES:
        return Response(status_code=404, content=f"Unknown sample: {name}")

    if format not in ("png", "jpg", "jpeg"):
        return Response(status_code=400, content=f"Unsupported format: {format}")

    from skimage import data
    img_func = getattr(data, name, None)
    if not img_func:
        return Response(status_code=404, content=f"Sample not found: {name}")

    img_array = img_func()

    # Convert to PIL Image
    if img_array.ndim == 2:
        # Grayscale
        pil_img = Image.fromarray(img_array, mode='L')
    elif img_array.shape[2] == 4:
        # RGBA
        pil_img = Image.fromarray(img_array, mode='RGBA')
    else:
        # RGB
        pil_img = Image.fromarray(img_array, mode='RGB')

    # Encode to bytes
    buf = BytesIO()
    if format == "png":
        pil_img.save(buf, format="PNG")
        media_type = "image/png"
    else:
        # Convert RGBA to RGB for JPEG
        if pil_img.mode == 'RGBA':
            bg = Image.new('RGB', pil_img.size, (255, 255, 255))
            bg.paste(pil_img, mask=pil_img.split()[3])
            pil_img = bg
        elif pil_img.mode == 'L':
            pil_img = pil_img.convert('RGB')
        pil_img.save(buf, format="JPEG", quality=quality)
        media_type = "image/jpeg"

    return Response(content=buf.getvalue(), media_type=media_type)


@router.get("/samples/images/{filename}")
async def get_static_image(filename: str):
    """Get static sample image."""
    path = SAMPLES_DIR / "images" / filename
    if not path.exists():
        return Response(status_code=404, content=f"Image not found: {filename}")
    return FileResponse(path)


@router.get("/samples/svgs/{category}/{filename}")
async def get_svg(category: str, filename: str):
    """Get sample SVG."""
    path = SAMPLES_DIR / "svgs" / category / filename
    if not path.exists():
        return Response(status_code=404, content=f"SVG not found: {category}/{filename}")
    return FileResponse(path, media_type="image/svg+xml")


@router.get("/samples/svgs/{category}/{name}.webp")
async def get_svg_as_webp(
    category: str,
    name: str,
    size: int = Query(default=128, ge=16, le=1024),
    quality: int = Query(default=90, ge=1, le=100),
):
    """Render SVG to WebP at specified size.

    This endpoint provides a ground truth image that can be used by both
    Python and JavaScript for parity testing.

    Args:
        category: SVG category folder (e.g., "noto-emoji")
        name: SVG filename without extension (e.g., "deer")
        size: Output size in pixels (square, default 128)
        quality: WebP quality (default 90)

    Examples:
        /imgstag/samples/svgs/noto-emoji/deer.webp?size=128
        /imgstag/samples/svgs/noto-emoji/fire.webp?size=256&quality=95
    """
    svg_path = SAMPLES_DIR / "svgs" / category / f"{name}.svg"
    if not svg_path.exists():
        return Response(status_code=404, content=f"SVG not found: {category}/{name}.svg")

    try:
        pil_img = _render_svg_to_image(svg_path, size, size)

        # Convert to RGBA if not already
        if pil_img.mode != 'RGBA':
            pil_img = pil_img.convert('RGBA')

        buf = BytesIO()
        pil_img.save(buf, format="WEBP", quality=quality, lossless=False)

        return Response(content=buf.getvalue(), media_type="image/webp")
    except ImportError:
        return Response(
            status_code=500,
            content="cairosvg not installed. Install with: pip install cairosvg"
        )
    except Exception as e:
        return Response(status_code=500, content=f"Failed to render SVG: {e}")


@router.get("/samples/skimage/{name}.webp")
async def get_skimage_as_webp(
    name: str,
    size: int = Query(default=None, ge=16, le=1024),
    quality: int = Query(default=90, ge=1, le=100),
):
    """Render skimage sample to WebP, optionally resized.

    This endpoint provides a ground truth image that can be used by both
    Python and JavaScript for parity testing.

    Args:
        name: Skimage sample name (e.g., "astronaut")
        size: Optional output size in pixels (square). If not specified,
              returns original size.
        quality: WebP quality (default 90)

    Examples:
        /imgstag/samples/skimage/astronaut.webp
        /imgstag/samples/skimage/astronaut.webp?size=128
    """
    if name not in SKIMAGE_SAMPLES:
        return Response(status_code=404, content=f"Unknown sample: {name}")

    from skimage import data
    img_func = getattr(data, name, None)
    if not img_func:
        return Response(status_code=404, content=f"Sample not found: {name}")

    img_array = img_func()

    # Convert to PIL Image
    if img_array.ndim == 2:
        pil_img = Image.fromarray(img_array, mode='L').convert('RGBA')
    elif img_array.shape[2] == 4:
        pil_img = Image.fromarray(img_array, mode='RGBA')
    else:
        pil_img = Image.fromarray(img_array, mode='RGB').convert('RGBA')

    # Resize if specified
    if size:
        pil_img = pil_img.resize((size, size), Image.Resampling.LANCZOS)

    buf = BytesIO()
    pil_img.save(buf, format="WEBP", quality=quality, lossless=False)

    return Response(content=buf.getvalue(), media_type="image/webp")


@router.get("/parity/inputs/{input_id}.rgba")
async def get_parity_input(input_id: str):
    """Get raw RGBA data for a parity test input.

    Returns the exact same bytes that both Python and JS should use as input.
    This ensures ground truth consistency.

    Available inputs:
        - deer_128: Noto emoji deer rendered at 128x128
        - astronaut_128: Skimage astronaut resized to 128x128

    Format: 8-byte header (width u32le, height u32le) + raw RGBA bytes
    """
    if input_id == "deer_128":
        svg_path = SAMPLES_DIR / "svgs" / "noto-emoji" / "deer.svg"
        if not svg_path.exists():
            return Response(status_code=404, content="deer.svg not found")
        try:
            pil_img = _render_svg_to_image(svg_path, 128, 128)
            if pil_img.mode != 'RGBA':
                pil_img = pil_img.convert('RGBA')
        except ImportError:
            return Response(status_code=500, content="cairosvg not installed")

    elif input_id == "astronaut_128":
        from skimage import data
        img_array = data.astronaut()
        pil_img = Image.fromarray(img_array, mode='RGB').convert('RGBA')
        pil_img = pil_img.resize((128, 128), Image.Resampling.LANCZOS)

    else:
        return Response(status_code=404, content=f"Unknown input: {input_id}")

    # Convert to numpy array
    img_array = np.array(pil_img, dtype=np.uint8)
    width, height = pil_img.size

    # Create header + RGBA data
    header = np.array([width, height], dtype=np.uint32).tobytes()
    rgba_data = img_array.tobytes()

    return Response(
        content=header + rgba_data,
        media_type="application/octet-stream",
        headers={"X-Image-Width": str(width), "X-Image-Height": str(height)}
    )
