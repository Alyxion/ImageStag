#!/usr/bin/env python
"""
Benchmark script for parallel pipeline execution.

Demonstrates the Benchmark utility for measuring filter and pipeline performance.

Usage:
    poetry run python samples/benchmark_pipeline.py
    poetry run python samples/benchmark_pipeline.py --frames 60 --target 60
    poetry run python samples/benchmark_pipeline.py --compare
"""

import argparse
import time

from imagestag import Image
from imagestag.samples import group
from imagestag.pixel_format import PixelFormat
from imagestag.definitions import ImsFramework
from imagestag.filters import (
    Benchmark,
    BenchmarkConfig,
    FilterPipeline,
    Resize,
    FalseColor,
    Encode,
    ToDataUrl,
    GaussianBlur,
    Grayscale,
)


def prepare_source_image(target_megapixels: float = 20.0) -> Image:
    """Load and upscale source image to target megapixels.

    Returns image in CV (OpenCV) format for optimal pipeline performance.
    """
    print("Loading source image...")
    img = group()
    print(f"  Original size: {img.width}x{img.height} = {img.width * img.height / 1e6:.2f} MP")

    # Calculate scale to reach target megapixels
    current_mp = img.width * img.height / 1e6
    scale = (target_megapixels / current_mp) ** 0.5

    new_width = int(img.width * scale)
    new_height = int(img.height * scale)

    print(f"  Upscaling to: {new_width}x{new_height} = {new_width * new_height / 1e6:.2f} MP")
    start = time.perf_counter()
    upscaled = img.resized((new_width, new_height))
    elapsed = time.perf_counter() - start
    print(f"  Upscale time: {elapsed:.3f}s")

    # Convert to CV (OpenCV BGR) format for optimal pipeline performance
    pixels = upscaled.get_pixels(PixelFormat.BGR)
    cv_img = Image(pixels, pixel_format=PixelFormat.BGR, framework=ImsFramework.CV)
    print(f"  Framework: {cv_img.framework.name}")
    print()

    return cv_img


def run_pipeline_benchmark(args) -> bool:
    """Run the full pipeline benchmark."""
    print("\n=== ImageStag Pipeline Benchmark ===\n")

    # Prepare source
    source = prepare_source_image(args.mp)

    # Build pipeline: Resize -> FalseColor -> Encode -> ToDataUrl
    pipeline = FilterPipeline(filters=[
        Resize(size=(1920, 1080)),
        FalseColor(colormap=args.colormap),
        Encode(format='jpeg', quality=args.quality),
        ToDataUrl(format='jpeg', quality=args.quality),
    ])

    # Configure benchmark
    config = BenchmarkConfig(
        num_frames=args.frames,
        target_fps=args.target,
        warmup_frames=2,
        num_workers=args.workers,
    )

    # Run benchmark
    result = Benchmark.run_pipeline(pipeline, source, config=config)

    # Print results
    result.print()

    # Save JSON if requested
    if args.json:
        with open(args.json, 'w') as f:
            f.write(result.to_json())
        print(f"\nSaved results to: {args.json}")

    return result.passed if result.passed is not None else True


def run_filter_comparison(args) -> None:
    """Compare different filters side by side."""
    print("\n=== Filter Comparison ===\n")

    source = prepare_source_image(args.mp)

    filters = [
        Resize(scale=0.5),
        Resize(size=(1920, 1080)),
        FalseColor(colormap='hot'),
        FalseColor(colormap='viridis'),
        GaussianBlur(radius=3),
        Grayscale(),
        Encode(format='jpeg', quality=80),
    ]

    print(Benchmark.compare_filters(filters, source, num_frames=args.frames))


def run_single_filter_benchmark(args) -> None:
    """Benchmark a single filter."""
    print("\n=== Single Filter Benchmark ===\n")

    source = prepare_source_image(args.mp)

    # Parse filter from args or use default
    filter_map = {
        'resize': Resize(size=(1920, 1080)),
        'falsecolor': FalseColor(colormap='hot'),
        'blur': GaussianBlur(radius=5),
        'grayscale': Grayscale(),
        'encode': Encode(format='jpeg', quality=80),
    }

    filter_name = args.filter.lower() if args.filter else 'resize'
    if filter_name not in filter_map:
        print(f"Unknown filter: {filter_name}")
        print(f"Available: {', '.join(filter_map.keys())}")
        return

    f = filter_map[filter_name]

    result = Benchmark.run_filter(
        f,
        source,
        num_frames=args.frames,
        target_fps=args.target,
    )
    result.print()


def main():
    parser = argparse.ArgumentParser(
        description="ImageStag Pipeline Benchmark",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                      # Default: 30 frames pipeline benchmark
  %(prog)s --frames 60          # 60 frames
  %(prog)s --target 60          # 60 FPS target
  %(prog)s --compare            # Compare multiple filters
  %(prog)s --filter resize      # Single filter benchmark
  %(prog)s --json results.json  # Save JSON results
"""
    )
    parser.add_argument("--frames", type=int, default=30,
                        help="Number of frames to process (default: 30)")
    parser.add_argument("--target", type=float, default=60,
                        help="Target FPS (default: 60)")
    parser.add_argument("--workers", type=int, default=None,
                        help="Number of workers (default: auto)")
    parser.add_argument("--mp", type=float, default=20.0,
                        help="Source megapixels (default: 20)")
    parser.add_argument("--colormap", type=str, default='hot',
                        help="Colormap to use (default: hot)")
    parser.add_argument("--quality", type=int, default=80,
                        help="JPEG quality (default: 80)")
    parser.add_argument("--compare", action="store_true",
                        help="Compare multiple filters")
    parser.add_argument("--filter", type=str, default=None,
                        help="Benchmark single filter (resize, falsecolor, blur, grayscale, encode)")
    parser.add_argument("--json", type=str, default=None,
                        help="Save JSON results to file")
    args = parser.parse_args()

    if args.compare:
        run_filter_comparison(args)
    elif args.filter:
        run_single_filter_benchmark(args)
    else:
        success = run_pipeline_benchmark(args)
        exit(0 if success else 1)


if __name__ == "__main__":
    main()
