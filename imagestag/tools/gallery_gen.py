# Gallery Generator
"""
Generate thumbnail gallery for all filters and presets.

This tool creates JPG thumbnails showing each filter's effect using
appropriate sample images and reasonable default parameters.

Usage:
    # Generate all thumbnails
    poetry run python -m imagestag.tools.gallery_gen

    # Custom output directory
    poetry run python -m imagestag.tools.gallery_gen --output docs/api/gallery

    # Custom thumbnail size
    poetry run python -m imagestag.tools.gallery_gen --size 256

    # Include originals for comparison
    poetry run python -m imagestag.tools.gallery_gen --originals
"""

from __future__ import annotations

import argparse
from pathlib import Path
from dataclasses import dataclass
from typing import Any

from imagestag import Image
from imagestag.skimage import SKImage
from imagestag.definitions import ImsFramework
from imagestag.filters.base import get_all_filters_info, FILTER_REGISTRY, FILTER_ALIASES
from imagestag.filters.demo_metadata import FILTER_METADATA, get_recommended_image


@dataclass
class GalleryConfig:
    """Configuration for gallery generation."""
    output_dir: Path = Path('docs/api/gallery')
    thumb_size: int = 256
    quality: int = 85
    include_originals: bool = False
    verbose: bool = True


# Legacy skip list for filters without proper class attributes yet
# These should eventually be moved to _gallery_skip on the class itself
SKIP_FILTERS = {
    # Multi-input filters (check _input_ports)
    'Blend', 'Composite', 'MaskApply', 'SizeMatcher', 'MergeChannels',
    'MergeRegions', 'MatchHistograms',
    # Analyzers (output is not an image)
    'ImageStats', 'HistogramAnalyzer', 'ColorAnalyzer', 'RegionAnalyzer',
    'BoundingBoxDetector',
    # Format converters
    'Encode', 'Decode', 'ConvertFormat', 'ToDataUrl',
    # Pipeline/graph (meta-filters)
    'FilterPipeline', 'FilterGraph',
    # Source/output nodes (not standalone filters)
    'PipelineSource', 'PipelineOutput',
    # Optional dependencies not always installed
    'DenoiseWavelet',  # Requires PyWavelets
}

# Default parameters for filters without metadata
DEFAULT_PARAMS: dict[str, dict[str, Any]] = {
    # Exposure
    'AdjustGamma': {'gamma': 0.5},
    'AdjustLog': {'gain': 1.0},
    'AdjustSigmoid': {'cutoff': 0.5, 'gain': 10},
    'RescaleIntensity': {'in_range': (50, 200)},
    # Morphology (advanced)
    'Frangi': {},
    'Hessian': {},
    'Meijering': {},
    'Sato': {},
    'Skeletonize': {},
    'MedialAxis': {},
    'RemoveSmallObjects': {'min_size': 100},
    'RemoveSmallHoles': {'area_threshold': 100},
    # Histogram
    'CLAHE': {'clip_limit': 2.0, 'tile_size': 8},  # tile_size, not grid_size
    'EqualizeHist': {},
    'AdaptiveThreshold': {'block_size': 11, 'c': 2},
    # Threshold
    'ThresholdOtsu': {},
    'ThresholdLi': {},
    'ThresholdYen': {},
    'ThresholdTriangle': {},
    'ThresholdNiblack': {'window_size': 15, 'k': 0.2},
    'ThresholdSauvola': {'window_size': 15, 'k': 0.2},
    # Texture
    'Gabor': {'frequency': 0.1},
    'GaborBank': {},
    'LBP': {'radius': 3, 'n_points': 24},
    # Segmentation
    'SLIC': {'n_segments': 100},
    'Felzenszwalb': {'scale': 100, 'sigma': 0.5, 'min_size': 50},
    'Watershed': {},
    # Restoration
    'DenoiseNLMeans': {},
    'DenoiseTV': {'weight': 0.1},
    'DenoiseWavelet': {},
    'Inpaint': {},  # Needs mask, will skip
    # Channels
    'SplitChannels': {},
    'ExtractChannel': {'channel': 'R'},
    # Color
    'FalseColor': {'colormap': 'hot'},
    'Posterize': {'bits': 4},  # bits, not levels
    'Solarize': {'threshold': 128},
    'Hue': {'shift': 0.3},
    'Sepia': {},
    'AutoContrast': {},
    'Equalize': {},
    # Edge
    'Scharr': {},
    'Laplacian': {'kernel_size': 3},  # kernel_size, not ksize
    # Blur (PIL built-in)
    'Smooth': {},
    'SmoothMore': {},
    'Detail': {},
    'Contour': {},
    'Emboss': {},
    'FindEdges': {},
    'Sharpen': {},  # No parameters
    'GaussianBlur': {'radius': 3.0},
    'MedianFilter': {'size': 5},
    'MinFilter': {'size': 3},
    'MaxFilter': {'size': 3},
    'ModeFilter': {'size': 5},
    'BilateralFilter': {'d': 9, 'sigma_color': 75, 'sigma_space': 75},
    # Geometric
    'Resize': {'scale': 0.5},
    'Rotate': {'angle': 30, 'expand': True},
    'Flip': {'mode': 'h'},  # mode='h' for horizontal, not horizontal=True
    # Generator (special - creates new image)
    'ImageGenerator': {'gradient_type': 'radial', 'width': 256, 'height': 256},
    # Detection with geometry drawing
    'DrawGeometry': {},  # Skip - needs geometry input
    'ExtractRegions': {},  # Skip - needs geometry input
}


def get_filter_params(filter_name: str) -> dict[str, Any]:
    """Get parameters for a filter from metadata or defaults."""
    # Check demo metadata first
    meta = FILTER_METADATA.get(filter_name, {})
    presets = meta.get('presets', [])
    if presets:
        # Use first preset
        return presets[0].get('params', {})

    # Fall back to defaults
    return DEFAULT_PARAMS.get(filter_name, {})


def create_synthetic_image(synthetic_type: str, size: int = 256) -> Image:
    """Create a synthetic test image for specific filter types.

    :param synthetic_type: Type of synthetic image ('lines', 'circles', etc.)
    :param size: Image size in pixels
    :returns: Synthetic test image
    """
    import numpy as np
    from imagestag import Image as Img
    from imagestag.pixel_format import PixelFormat

    if synthetic_type == 'circles':
        # Create image with circles at various sizes
        import cv2
        img = np.ones((size, size, 3), dtype=np.uint8) * 240  # Light gray background
        # Draw circles
        cv2.circle(img, (size // 4, size // 4), size // 8, (50, 50, 50), 2)
        cv2.circle(img, (3 * size // 4, size // 4), size // 6, (50, 50, 50), 2)
        cv2.circle(img, (size // 2, size // 2), size // 5, (30, 30, 30), 3)
        cv2.circle(img, (size // 4, 3 * size // 4), size // 10, (50, 50, 50), 2)
        cv2.circle(img, (3 * size // 4, 3 * size // 4), size // 7, (40, 40, 40), 2)
        return Img(img, pixel_format=PixelFormat.BGR, framework=ImsFramework.CV)

    elif synthetic_type == 'lines':
        # Create image with lines at various angles
        import cv2
        img = np.ones((size, size, 3), dtype=np.uint8) * 240  # Light gray background
        # Draw lines
        cv2.line(img, (10, 10), (size - 10, size - 10), (50, 50, 50), 2)
        cv2.line(img, (size - 10, 10), (10, size - 10), (50, 50, 50), 2)
        cv2.line(img, (size // 2, 10), (size // 2, size - 10), (40, 40, 40), 2)
        cv2.line(img, (10, size // 2), (size - 10, size // 2), (40, 40, 40), 2)
        cv2.line(img, (10, size // 4), (size - 10, size // 4), (60, 60, 60), 2)
        cv2.line(img, (10, 3 * size // 4), (size - 10, 3 * size // 4), (60, 60, 60), 2)
        return Img(img, pixel_format=PixelFormat.BGR, framework=ImsFramework.CV)

    else:
        # Default: return astronaut
        return SKImage.astronaut()


def save_synthetic_images(config: GalleryConfig) -> dict[str, Path]:
    """Save synthetic test images to originals folder.

    :param config: Gallery configuration
    :returns: Dict mapping synthetic type to saved path
    """
    originals_dir = config.output_dir / 'originals'
    originals_dir.mkdir(parents=True, exist_ok=True)

    saved = {}
    for synthetic_type in ['circles', 'lines']:
        img = create_synthetic_image(synthetic_type, config.thumb_size)
        path = originals_dir / f'synthetic_{synthetic_type}.jpg'
        img.to_pil().convert('RGB').save(str(path), quality=config.quality)
        saved[synthetic_type] = path
        if config.verbose:
            print(f"  ✓ synthetic_{synthetic_type}")

    return saved


def get_sample_image(filter_name: str, filter_cls: type | None = None) -> tuple[Image, str]:
    """Get appropriate sample image for a filter.

    :param filter_name: Name of the filter
    :param filter_cls: Optional filter class to check for _gallery_synthetic
    :returns: Tuple of (sample image, image name for gallery reference)
    """
    # Check if filter needs synthetic image
    if filter_cls and hasattr(filter_cls, '_gallery_synthetic') and filter_cls._gallery_synthetic:
        synthetic_type = filter_cls._gallery_synthetic
        return create_synthetic_image(synthetic_type), f'synthetic_{synthetic_type}'

    # Check class-level sample override
    if filter_cls and hasattr(filter_cls, '_gallery_sample') and filter_cls._gallery_sample:
        sample_name = filter_cls._gallery_sample
        try:
            return SKImage.load(sample_name), sample_name
        except ValueError:
            pass

    # Use demo metadata
    image_name = get_recommended_image(filter_name)
    try:
        return SKImage.load(image_name), image_name
    except ValueError:
        # Fall back to astronaut if image not found
        return SKImage.astronaut(), 'astronaut'


def create_channel_grid(channels: dict[str, Image], size: int = 256) -> Image:
    """Create a grid showing R/G/B channels with color tinting.

    :param channels: Dict of channel name to grayscale image
    :param size: Output size
    :returns: Combined grid image
    """
    import numpy as np
    from imagestag import Image as Img
    from imagestag.pixel_format import PixelFormat

    # Get channels in order
    r_gray = channels.get('R')
    g_gray = channels.get('G')
    b_gray = channels.get('B')

    if not all([r_gray, g_gray, b_gray]):
        return None

    # Get grayscale arrays
    r_data = r_gray.get_pixels_gray()
    g_data = g_gray.get_pixels_gray()
    b_data = b_gray.get_pixels_gray()

    # Create tinted versions
    h, w = r_data.shape
    zeros = np.zeros_like(r_data)

    r_tinted = np.stack([r_data, zeros, zeros], axis=2)  # Red tint
    g_tinted = np.stack([zeros, g_data, zeros], axis=2)  # Green tint
    b_tinted = np.stack([zeros, zeros, b_data], axis=2)  # Blue tint

    # Create 1x3 grid
    grid = np.concatenate([r_tinted, g_tinted, b_tinted], axis=1)

    result = Img(grid.astype(np.uint8), pixel_format=PixelFormat.RGB)
    # Resize to fit
    return result.resized_ext(max_size=(size, size // 3 * 3))


def generate_filter_thumbnail(
    filter_name: str,
    config: GalleryConfig,
) -> tuple[Path | None, str | None]:
    """Generate thumbnail for a single filter.

    :param filter_name: Name of the filter class
    :param config: Gallery configuration
    :returns: Tuple of (path to generated thumbnail, input image name) or (None, None) if skipped
    """
    # Get filter class from registry first
    filter_cls = FILTER_REGISTRY.get(filter_name) or FILTER_REGISTRY.get(filter_name.lower())
    if not filter_cls:
        if config.verbose:
            print(f"  ✗ {filter_name}: Not found in registry")
        return None, None

    # Check class-level gallery_skip attribute
    if getattr(filter_cls, '_gallery_skip', False):
        if config.verbose:
            print(f"  Skipping {filter_name} (class._gallery_skip)")
        return None, None

    # Check legacy skip list
    if filter_name in SKIP_FILTERS:
        if config.verbose:
            print(f"  Skipping {filter_name} (special filter)")
        return None, None

    try:
        # Get sample image (respects _gallery_synthetic and _gallery_sample)
        image, input_name = get_sample_image(filter_name, filter_cls)
        params = get_filter_params(filter_name)

        # Create and apply filter
        filter_instance = filter_cls(**params)
        result = filter_instance.apply(image)

        # Handle geometry output - draw it on the source image
        from imagestag.geometry_list import GeometryList
        if isinstance(result, GeometryList):
            from imagestag.filters import DrawGeometry
            drawer = DrawGeometry(color='#FF0000', thickness=2)
            result = drawer.apply_multi({'input': image, 'geometry': result})

        # Handle multi-output filters (e.g., SplitChannels)
        if isinstance(result, dict):
            if getattr(filter_cls, '_gallery_multi_output', False):
                # Create colored grid for channel outputs
                grid = create_channel_grid(result, config.thumb_size)
                if grid:
                    result = grid
                else:
                    result = next(iter(result.values()))
            else:
                # Use first output
                result = next(iter(result.values()))

        # Handle ImageList output
        if hasattr(result, '__iter__') and not isinstance(result, Image):
            try:
                result = list(result)[0]
            except (TypeError, IndexError):
                pass

        if not isinstance(result, Image):
            if config.verbose:
                print(f"  Skipping {filter_name} (non-image output: {type(result).__name__})")
            return None, None

        # Resize to thumbnail
        thumb = result.resized_ext(max_size=(config.thumb_size, config.thumb_size))

        # Save
        output_path = config.output_dir / 'filters' / f'{filter_name.lower()}.jpg'
        output_path.parent.mkdir(parents=True, exist_ok=True)
        thumb.to_pil().convert('RGB').save(str(output_path), quality=config.quality)

        if config.verbose:
            print(f"  ✓ {filter_name}")

        return output_path, input_name

    except Exception as e:
        if config.verbose:
            print(f"  ✗ {filter_name}: {e}")
        return None, None


def generate_preset_thumbnail(
    preset_key: str,
    config: GalleryConfig,
) -> Path | None:
    """Generate thumbnail for a preset.

    :param preset_key: Preset key
    :param config: Gallery configuration
    :returns: Path to generated thumbnail or None if failed
    """
    from imagestag.tools.preset_registry import get_preset

    preset = get_preset(preset_key)
    if not preset:
        if config.verbose:
            print(f"  ✗ Preset {preset_key} not found")
        return None

    try:
        # Load sample images for inputs
        images = {}
        for inp in preset.inputs:
            images[inp.name] = SKImage.load(inp.sample_image)

        # Execute as graph
        graph = preset.to_graph()

        # Handle single vs multi-input
        if len(images) == 1:
            result = graph.execute(list(images.values())[0])
        else:
            result = graph.execute(**images)

        if not isinstance(result, Image):
            if config.verbose:
                print(f"  Skipping {preset_key} (non-image output)")
            return None

        # Resize to thumbnail
        thumb = result.resized_ext(max_size=(config.thumb_size, config.thumb_size))

        # Save
        output_path = config.output_dir / 'presets' / f'{preset_key}.jpg'
        output_path.parent.mkdir(parents=True, exist_ok=True)
        thumb.to_pil().convert('RGB').save(str(output_path), quality=config.quality)

        if config.verbose:
            print(f"  ✓ {preset.name}")

        return output_path

    except Exception as e:
        if config.verbose:
            print(f"  ✗ {preset_key}: {e}")
        return None


def generate_original_thumbnails(config: GalleryConfig) -> dict[str, Path]:
    """Generate thumbnails of original sample images.

    :param config: Gallery configuration
    :returns: Dict mapping image name to path
    """
    originals_dir = config.output_dir / 'originals'
    originals_dir.mkdir(parents=True, exist_ok=True)

    paths = {}
    for name in SKImage.list_images():
        try:
            img = SKImage.load(name)
            thumb = img.resized_ext(max_size=(config.thumb_size, config.thumb_size))
            path = originals_dir / f'{name}.jpg'
            thumb.to_pil().convert('RGB').save(str(path), quality=config.quality)
            paths[name] = path
            if config.verbose:
                print(f"  ✓ {name}")
        except Exception as e:
            if config.verbose:
                print(f"  ✗ {name}: {e}")

    return paths


def generate_gallery_index(config: GalleryConfig, filter_inputs: dict[str, str]) -> Path:
    """Generate gallery index markdown with input/output comparisons.

    :param config: Gallery configuration
    :param filter_inputs: Dict mapping filter name to input image name
    :returns: Path to generated index file
    """
    from imagestag.filters.base import get_all_filters_info

    catalog = get_all_filters_info()

    # Group filters by category
    categories: dict[str, list[tuple[str, str]]] = {}
    for name, info in sorted(catalog.items()):
        cat = info.category or 'other'
        if cat not in categories:
            categories[cat] = []
        # Only include filters that have thumbnails
        thumb_path = config.output_dir / 'filters' / f'{name.lower()}.jpg'
        if thumb_path.exists():
            input_img = filter_inputs.get(name, 'astronaut')
            categories[cat].append((name, input_img))

    lines = [
        '# Filter Gallery',
        '',
        'Visual comparison of all filters showing input → output.',
        '',
        '## Sample Images',
        '',
        'These source images are used as inputs for filter demonstrations:',
        '',
        '| Image | Name |',
        '|-------|------|',
    ]

    # List all unique input images used
    unique_inputs = sorted(set(filter_inputs.values()))
    for img_name in unique_inputs:
        orig_path = config.output_dir / 'originals' / f'{img_name}.jpg'
        if orig_path.exists():
            lines.append(f'| ![{img_name}](originals/{img_name}.jpg) | {img_name} |')

    lines.append('')
    lines.append('---')
    lines.append('')

    # Generate comparison tables by category
    for cat, filters in sorted(categories.items()):
        lines.append(f'## {cat.title()}')
        lines.append('')
        lines.append('| Input | Output | Filter |')
        lines.append('|-------|--------|--------|')

        for name, input_img in sorted(filters):
            input_ref = f'![{input_img}](originals/{input_img}.jpg)'
            output_ref = f'![{name}](filters/{name.lower()}.jpg)'
            filter_link = f'[{name}](../filters/{name.lower()}.md)'
            lines.append(f'| {input_ref} | {output_ref} | {filter_link} |')

        lines.append('')

    # Add presets section
    lines.append('---')
    lines.append('')
    lines.append('## Presets')
    lines.append('')
    lines.append('| Output | Preset |')
    lines.append('|--------|--------|')

    presets_dir = config.output_dir / 'presets'
    if presets_dir.exists():
        for thumb in sorted(presets_dir.glob('*.jpg')):
            key = thumb.stem
            lines.append(f'| ![{key}](presets/{key}.jpg) | [{key}](../presets/{key}.md) |')

    lines.append('')

    index_path = config.output_dir / 'README.md'
    index_path.write_text('\n'.join(lines))

    return index_path


def generate_gallery(
    output_dir: str | Path = 'docs/api/gallery',
    thumb_size: int = 256,
    include_originals: bool = True,
    verbose: bool = True,
) -> dict:
    """Generate complete thumbnail gallery.

    :param output_dir: Output directory path
    :param thumb_size: Thumbnail size in pixels
    :param include_originals: Include original sample images
    :param verbose: Print progress
    :returns: Summary dict with counts
    """
    from imagestag.tools.preset_registry import PRESETS

    config = GalleryConfig(
        output_dir=Path(output_dir),
        thumb_size=thumb_size,
        include_originals=include_originals,
        verbose=verbose,
    )

    config.output_dir.mkdir(parents=True, exist_ok=True)

    summary = {
        'filters_success': 0,
        'filters_skipped': 0,
        'filters_failed': 0,
        'presets_success': 0,
        'presets_failed': 0,
        'originals': 0,
    }

    # Generate original thumbnails
    if include_originals:
        if verbose:
            print("Generating original thumbnails...")
        paths = generate_original_thumbnails(config)
        summary['originals'] = len(paths)

        # Save synthetic test images (circles, lines) to originals folder
        if verbose:
            print("\nGenerating synthetic test images...")
        save_synthetic_images(config)

    # Generate filter thumbnails and track which input image was used
    if verbose:
        print("\nGenerating filter thumbnails...")

    filter_inputs: dict[str, str] = {}  # filter_name -> input_image_name
    catalog = get_all_filters_info()
    for name in sorted(catalog.keys()):
        thumb_path, input_name = generate_filter_thumbnail(name, config)
        if thumb_path is not None:
            summary['filters_success'] += 1
            # Track which input image was used (from the filter thumbnail generator)
            filter_inputs[name] = input_name
        elif name in SKIP_FILTERS:
            summary['filters_skipped'] += 1
        else:
            summary['filters_failed'] += 1

    # Generate preset thumbnails
    if verbose:
        print("\nGenerating preset thumbnails...")

    for preset_key in PRESETS:
        result = generate_preset_thumbnail(preset_key, config)
        if result:
            summary['presets_success'] += 1
        else:
            summary['presets_failed'] += 1

    # Generate gallery index with input/output comparisons
    if verbose:
        print("\nGenerating gallery index...")
    generate_gallery_index(config, filter_inputs)

    return summary


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Generate thumbnail gallery for filters and presets',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                         # Generate to docs/api/gallery/
  %(prog)s --output gallery/       # Custom output directory
  %(prog)s --size 128              # Smaller thumbnails
  %(prog)s --originals             # Include original sample images
"""
    )
    parser.add_argument(
        '--output', '-o',
        default='docs/api/gallery',
        help='Output directory (default: docs/api/gallery)'
    )
    parser.add_argument(
        '--size', '-s',
        type=int,
        default=256,
        help='Thumbnail size in pixels (default: 256)'
    )
    parser.add_argument(
        '--originals',
        action='store_true',
        help='Include original sample image thumbnails'
    )
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Suppress progress output'
    )
    args = parser.parse_args()

    print(f'Generating gallery to {args.output}/')

    summary = generate_gallery(
        output_dir=args.output,
        thumb_size=args.size,
        include_originals=args.originals,
        verbose=not args.quiet,
    )

    print(f'\nGenerated:')
    print(f'  - {summary["filters_success"]} filter thumbnails')
    print(f'  - {summary["filters_skipped"]} filters skipped (special)')
    print(f'  - {summary["filters_failed"]} filters failed')
    print(f'  - {summary["presets_success"]} preset thumbnails')
    if summary['originals']:
        print(f'  - {summary["originals"]} original images')
    print('Done!')


if __name__ == '__main__':
    main()
