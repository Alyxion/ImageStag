"""SVG samples API endpoints.

Provides access to the sample SVG files in imagestag/data/svgs/
for testing SVG layer functionality.
"""

from pathlib import Path
from fastapi import APIRouter, HTTPException, Response

router = APIRouter()

# Path to SVG samples directory
SVGS_DIR = Path(__file__).parent.parent.parent / "imagestag" / "samples" / "svgs"


@router.get("/svg-samples")
async def list_svg_samples():
    """List all available SVG samples from imagestag/data/svgs/

    Returns a list of samples organized by category (subdirectory).
    """
    samples = []

    if not SVGS_DIR.exists():
        return {"samples": samples}

    for svg_file in SVGS_DIR.rglob("*.svg"):
        # Get relative path from svgs directory
        rel_path = svg_file.relative_to(SVGS_DIR)

        # Category is the parent directory name
        category = rel_path.parent.name if rel_path.parent.name else "root"

        samples.append({
            "id": svg_file.stem,
            "path": str(rel_path),
            "category": category,
            "name": svg_file.stem.replace("-", " ").replace("_", " ").title(),
            "filename": svg_file.name,
        })

    # Sort by category then name
    samples.sort(key=lambda x: (x["category"], x["name"]))

    return {"samples": samples}


@router.get("/svg-samples/{category}/{filename}")
async def get_svg_sample(category: str, filename: str):
    """Get SVG content by category and filename.

    Args:
        category: Subdirectory name (e.g., "openclipart", "noto-emoji")
        filename: SVG filename with extension (e.g., "buck-deer-silhouette.svg")

    Returns:
        Raw SVG content with image/svg+xml content type
    """
    # Sanitize inputs to prevent path traversal
    if ".." in category or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid path")

    svg_path = SVGS_DIR / category / filename

    if not svg_path.exists():
        raise HTTPException(status_code=404, detail=f"SVG not found: {category}/{filename}")

    if not svg_path.is_file():
        raise HTTPException(status_code=400, detail="Not a file")

    if svg_path.suffix.lower() != ".svg":
        raise HTTPException(status_code=400, detail="Not an SVG file")

    # Read and return SVG content
    svg_content = svg_path.read_text(encoding="utf-8")

    return Response(
        content=svg_content,
        media_type="image/svg+xml",
        headers={"Content-Disposition": f'inline; filename="{filename}"'}
    )


@router.get("/svg-samples/{category}/{filename}/metadata")
async def get_svg_sample_metadata(category: str, filename: str):
    """Get metadata about an SVG sample.

    Parses the SVG to extract viewBox, width, height, and title.
    """
    import re

    # Sanitize inputs
    if ".." in category or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid path")

    svg_path = SVGS_DIR / category / filename

    if not svg_path.exists():
        raise HTTPException(status_code=404, detail=f"SVG not found: {category}/{filename}")

    svg_content = svg_path.read_text(encoding="utf-8")

    metadata = {
        "path": f"{category}/{filename}",
        "filename": filename,
        "category": category,
        "fileSize": svg_path.stat().st_size,
    }

    # Extract viewBox
    viewbox_match = re.search(r'viewBox\s*=\s*["\']([^"\']+)["\']', svg_content, re.IGNORECASE)
    if viewbox_match:
        parts = viewbox_match.group(1).strip().split()
        if len(parts) >= 4:
            metadata["viewBox"] = {
                "minX": float(parts[0]),
                "minY": float(parts[1]),
                "width": float(parts[2]),
                "height": float(parts[3]),
            }

    # Extract width/height attributes
    width_match = re.search(r'\bwidth\s*=\s*["\']([^"\']+)["\']', svg_content, re.IGNORECASE)
    height_match = re.search(r'\bheight\s*=\s*["\']([^"\']+)["\']', svg_content, re.IGNORECASE)

    if width_match:
        metadata["width"] = width_match.group(1)
    if height_match:
        metadata["height"] = height_match.group(1)

    # Extract title
    title_match = re.search(r'<title[^>]*>([^<]+)</title>', svg_content, re.IGNORECASE)
    if title_match:
        metadata["title"] = title_match.group(1).strip()

    return metadata
