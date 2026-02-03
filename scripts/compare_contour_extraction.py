#!/usr/bin/env python3
"""
Compare contour extraction algorithms on SVG test images.

This script:
1. Renders SVG files at 512x512 via resvg
2. Extracts alpha mask
3. Runs marching squares algorithm with various settings
4. Renders the extracted contours back as SVG
5. Compares the results visually
6. Saves all outputs to tmp/mask_comparison/
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import numpy as np
from PIL import Image
from resvg_py import svg_to_bytes

# Import our Rust functions
from imagestag import imagestag_rust


def render_svg_to_rgba(svg_path: Path, width: int, height: int) -> np.ndarray:
    """Render an SVG file to RGBA numpy array using resvg."""
    # Render with resvg
    png_bytes = svg_to_bytes(
        svg_path=str(svg_path),
        width=width,
        height=height,
        background=None,  # Transparent background
    )

    # Convert to numpy array
    img = Image.open(__import__('io').BytesIO(png_bytes))
    img = img.convert('RGBA')
    return np.array(img)


def extract_alpha_mask(rgba: np.ndarray) -> np.ndarray:
    """Extract the alpha channel as a 1D array."""
    return rgba[:, :, 3].flatten().astype(np.uint8)


def compute_pixel_diff(img1: np.ndarray, img2: np.ndarray, compare_mode: str = 'alpha') -> tuple[float, np.ndarray]:
    """
    Compute pixel difference between two RGBA images.

    Args:
        img1: First image (RGBA)
        img2: Second image (RGBA)
        compare_mode: 'alpha' to compare only alpha channels, 'rgb' for full color

    Returns:
        - diff_ratio: Percentage of pixels that differ
        - diff_image: Visual diff image (red = difference)
    """
    if img1.shape != img2.shape:
        raise ValueError(f"Shape mismatch: {img1.shape} vs {img2.shape}")

    h, w = img1.shape[:2]

    if compare_mode == 'alpha':
        # Compare alpha channels only - useful for silhouette comparison
        val1 = img1[:, :, 3].astype(np.float32)
        val2 = img2[:, :, 3].astype(np.float32)
        diff = np.abs(val1 - val2)
    else:
        # Compare all RGB channels (weighted)
        rgb1 = img1[:, :, :3].astype(np.float32)
        rgb2 = img2[:, :, :3].astype(np.float32)
        diff = np.mean(np.abs(rgb1 - rgb2), axis=2)

    # Count pixels with significant difference (> 5 out of 255)
    diff_mask = diff > 5
    diff_count = np.sum(diff_mask)
    total_pixels = h * w
    diff_ratio = diff_count / total_pixels * 100

    # Create visual diff image
    diff_image = np.zeros((h, w, 4), dtype=np.uint8)
    diff_image[:, :, 0] = np.clip(diff, 0, 255).astype(np.uint8)  # Red channel shows diff
    diff_image[:, :, 3] = np.where(diff_mask, 255, 50)  # Alpha shows diff areas

    return diff_ratio, diff_image


def render_svg_string(svg_content: str, width: int, height: int) -> np.ndarray:
    """Render SVG string to RGBA numpy array."""
    png_bytes = svg_to_bytes(
        svg_string=svg_content,
        width=width,
        height=height,
        background=None,
    )
    img = Image.open(__import__('io').BytesIO(png_bytes))
    img = img.convert('RGBA')
    return np.array(img)


def process_svg(
    svg_path: Path,
    output_dir: Path,
    size: int = 512,
) -> dict:
    """
    Process a single SVG file through the contour extraction pipeline.

    Returns dict with results and metrics.
    """
    name = svg_path.stem
    print(f"\nProcessing: {name}")
    print("=" * 50)

    results = {'name': name, 'variants': []}

    # 1. Render original SVG
    print(f"  Rendering original at {size}x{size}...")
    original = render_svg_to_rgba(svg_path, size, size)
    Image.fromarray(original).save(output_dir / f"{name}_01_original.png")

    # 2. Extract alpha mask
    print("  Extracting alpha mask...")
    mask = extract_alpha_mask(original)

    # Save mask as grayscale image
    mask_img = mask.reshape(size, size)
    Image.fromarray(mask_img, mode='L').save(output_dir / f"{name}_02_alpha_mask.png")

    # Create reference image: white silhouette on black background
    # This is what our contour extraction should produce
    reference = np.zeros((size, size, 4), dtype=np.uint8)
    reference[:, :, 0] = mask_img  # R
    reference[:, :, 1] = mask_img  # G
    reference[:, :, 2] = mask_img  # B
    reference[:, :, 3] = 255  # Fully opaque
    Image.fromarray(reference).save(output_dir / f"{name}_02b_reference.png")

    # 3. Test different contour extraction settings
    # Use smaller epsilon values for better preservation of curves
    # Note: eps=1.0 removed as it produces too rough results
    test_configs = [
        {
            'name': 'raw_marching_squares',
            'desc': 'Raw marching squares (no simplification)',
            'threshold': 0.5,
            'simplify_epsilon': 0.0,
            'fit_beziers': False,
            'bezier_smoothness': 0.25,
        },
        {
            'name': 'simplified_eps03',
            'desc': 'Simplified (epsilon=0.3)',
            'threshold': 0.5,
            'simplify_epsilon': 0.3,
            'fit_beziers': False,
            'bezier_smoothness': 0.25,
        },
        {
            'name': 'simplified_eps05',
            'desc': 'Simplified (epsilon=0.5)',
            'threshold': 0.5,
            'simplify_epsilon': 0.5,
            'fit_beziers': False,
            'bezier_smoothness': 0.25,
        },
        {
            'name': 'bezier_eps03',
            'desc': 'Bezier (eps=0.3, smooth=0.25)',
            'threshold': 0.5,
            'simplify_epsilon': 0.3,
            'fit_beziers': True,
            'bezier_smoothness': 0.25,
        },
        {
            'name': 'bezier_eps05',
            'desc': 'Bezier (eps=0.5, smooth=0.25)',
            'threshold': 0.5,
            'simplify_epsilon': 0.5,
            'fit_beziers': True,
            'bezier_smoothness': 0.25,
        },
    ]

    for i, config in enumerate(test_configs, start=3):
        print(f"  Testing: {config['desc']}...")

        # Extract contours using our Rust function
        # Use white fill on black background to match alpha mask appearance
        svg_content = imagestag_rust.contours_to_svg(
            mask=list(mask),
            width=size,
            height=size,
            threshold=config['threshold'],
            simplify_epsilon=config['simplify_epsilon'],
            fit_beziers=config['fit_beziers'],
            bezier_smoothness=config['bezier_smoothness'],
            fill_color="#FFFFFF",
            stroke_color=None,
            stroke_width=0.0,
            background_color="#000000",
        )

        # Save the SVG for debugging
        svg_filename = f"{name}_{i:02d}_{config['name']}.svg"
        (output_dir / svg_filename).write_text(svg_content)

        # Count points in contours for stats
        contours = imagestag_rust.extract_contours_precise(
            mask=list(mask),
            width=size,
            height=size,
            threshold=config['threshold'],
            simplify_epsilon=config['simplify_epsilon'],
            fit_beziers=config['fit_beziers'],
            bezier_smoothness=config['bezier_smoothness'],
        )

        total_points = sum(len(c['points']) for c in contours)
        num_contours = len(contours)

        # Render the extracted contours back to image
        rendered = render_svg_string(svg_content, size, size)
        png_filename = f"{name}_{i:02d}_{config['name']}.png"
        Image.fromarray(rendered).save(output_dir / png_filename)

        # Compare with reference (white silhouette on black)
        # Use RGB comparison since both images have solid backgrounds
        diff_ratio, diff_image = compute_pixel_diff(reference, rendered, compare_mode='rgb')
        diff_filename = f"{name}_{i:02d}_{config['name']}_diff.png"
        Image.fromarray(diff_image).save(output_dir / diff_filename)

        variant_result = {
            'config': config['name'],
            'description': config['desc'],
            'num_contours': num_contours,
            'total_points': total_points,
            'diff_ratio': diff_ratio,
            'svg_file': svg_filename,
            'png_file': png_filename,
        }
        results['variants'].append(variant_result)

        print(f"    Contours: {num_contours}, Points: {total_points}, Diff: {diff_ratio:.2f}%")

    return results


def main():
    output_dir = project_root / "tmp" / "mask_comparison"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Test SVG files
    svg_files = [
        project_root / "imagestag/samples/svgs/noto-emoji/deer.svg",
        project_root / "imagestag/samples/svgs/openclipart/male-deer.svg",
    ]

    all_results = []

    for svg_path in svg_files:
        if not svg_path.exists():
            print(f"Warning: {svg_path} not found, skipping")
            continue

        results = process_svg(svg_path, output_dir)
        all_results.append(results)

    # Generate summary report
    print("\n" + "=" * 70)
    print("SUMMARY REPORT")
    print("=" * 70)

    report_lines = [
        "# Contour Extraction Comparison Report",
        "",
        "## Test Images",
        "",
    ]

    for result in all_results:
        report_lines.append(f"### {result['name']}")
        report_lines.append("")
        report_lines.append("| Config | Contours | Points | Diff % | SVG File |")
        report_lines.append("|--------|----------|--------|--------|----------|")

        for v in result['variants']:
            report_lines.append(
                f"| {v['description'][:30]} | {v['num_contours']} | {v['total_points']} | "
                f"{v['diff_ratio']:.2f}% | [{v['svg_file']}]({v['svg_file']}) |"
            )

        report_lines.append("")

        # Print to console too
        print(f"\n{result['name']}:")
        for v in result['variants']:
            print(f"  {v['description'][:35]:35} - Contours: {v['num_contours']:3}, "
                  f"Points: {v['total_points']:5}, Diff: {v['diff_ratio']:.2f}%")

    # Write report
    report_path = output_dir / "REPORT.md"
    report_path.write_text("\n".join(report_lines))
    print(f"\nReport saved to: {report_path}")
    print(f"Output directory: {output_dir}")


if __name__ == "__main__":
    main()
