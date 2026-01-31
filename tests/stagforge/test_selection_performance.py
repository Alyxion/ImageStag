"""Performance benchmarks for selection operations.

Tests contour extraction, grow (dilation), and shrink (erosion) operations
across various resolutions and shape complexities.

Run with: poetry run pytest tests/stagforge/test_selection_performance.py -v -s
"""

import time
import math
import numpy as np
import pytest
from dataclasses import dataclass
from typing import Callable

# Import Rust functions
from imagestag import imagestag_rust
from imagestag.filters.morphology_filters import dilate, erode


@dataclass
class BenchmarkResult:
    """Result of a single benchmark."""
    name: str
    resolution: tuple[int, int]
    shape_type: str
    operation: str
    time_ms: float
    mask_pixels: int  # Number of selected pixels
    contour_points: int = 0  # Number of contour points (for contour extraction)


class SelectionMaskGenerator:
    """Generate various selection masks for testing."""

    @staticmethod
    def rectangle(width: int, height: int, margin_ratio: float = 0.1) -> np.ndarray:
        """Create a rectangular selection."""
        mask = np.zeros((height, width), dtype=np.uint8)
        mx = int(width * margin_ratio)
        my = int(height * margin_ratio)
        mask[my:height-my, mx:width-mx] = 255
        return mask

    @staticmethod
    def circle(width: int, height: int, radius_ratio: float = 0.4) -> np.ndarray:
        """Create a circular selection."""
        mask = np.zeros((height, width), dtype=np.uint8)
        cx, cy = width // 2, height // 2
        radius = min(width, height) * radius_ratio

        y, x = np.ogrid[:height, :width]
        dist = np.sqrt((x - cx)**2 + (y - cy)**2)
        mask[dist <= radius] = 255
        return mask

    @staticmethod
    def star(width: int, height: int, points: int = 5,
             outer_ratio: float = 0.4, inner_ratio: float = 0.2) -> np.ndarray:
        """Create a star-shaped (concave) selection."""
        mask = np.zeros((height, width), dtype=np.uint8)
        cx, cy = width // 2, height // 2
        outer_r = min(width, height) * outer_ratio
        inner_r = min(width, height) * inner_ratio

        # Generate star polygon points
        angles = []
        radii = []
        for i in range(points * 2):
            angle = (i * math.pi / points) - math.pi / 2
            r = outer_r if i % 2 == 0 else inner_r
            angles.append(angle)
            radii.append(r)

        # Fill polygon using scanline
        polygon_x = [int(cx + r * math.cos(a)) for a, r in zip(angles, radii)]
        polygon_y = [int(cy + r * math.sin(a)) for a, r in zip(angles, radii)]

        # Simple polygon fill
        from PIL import Image, ImageDraw
        img = Image.new('L', (width, height), 0)
        draw = ImageDraw.Draw(img)
        points_list = list(zip(polygon_x, polygon_y))
        draw.polygon(points_list, fill=255)
        mask = np.array(img)

        return mask

    @staticmethod
    def complex_concave(width: int, height: int) -> np.ndarray:
        """Create a complex concave shape (L-shape with notches)."""
        mask = np.zeros((height, width), dtype=np.uint8)

        # L-shape base
        h4, w4 = height // 4, width // 4
        mask[h4:height-h4, w4:w4*2] = 255  # Vertical bar
        mask[height//2:height-h4, w4:width-w4] = 255  # Horizontal bar

        # Add some notches for complexity
        notch_h = height // 8
        notch_w = width // 16
        for i in range(3):
            ny = h4 + (i + 1) * (height // 6)
            if ny + notch_h < height - h4:
                mask[ny:ny+notch_h, w4:w4+notch_w] = 0  # Cut notches

        return mask

    @staticmethod
    def multiple_circles(width: int, height: int, count: int = 5) -> np.ndarray:
        """Create multiple separate circular selections."""
        mask = np.zeros((height, width), dtype=np.uint8)

        np.random.seed(42)  # Reproducible
        radius = min(width, height) // 10

        for _ in range(count):
            cx = np.random.randint(radius, width - radius)
            cy = np.random.randint(radius, height - radius)

            y, x = np.ogrid[:height, :width]
            dist = np.sqrt((x - cx)**2 + (y - cy)**2)
            mask[dist <= radius] = 255

        return mask

    @staticmethod
    def checkerboard(width: int, height: int, cell_size: int = 50) -> np.ndarray:
        """Create a checkerboard pattern (many small selections)."""
        mask = np.zeros((height, width), dtype=np.uint8)

        for y in range(0, height, cell_size):
            for x in range(0, width, cell_size):
                if ((x // cell_size) + (y // cell_size)) % 2 == 0:
                    mask[y:min(y+cell_size, height), x:min(x+cell_size, width)] = 255

        return mask


class SelectionBenchmark:
    """Benchmark suite for selection operations."""

    def __init__(self):
        self.results: list[BenchmarkResult] = []

    def benchmark_contour_extraction(self, mask: np.ndarray,
                                     shape_type: str, resolution: tuple[int, int]) -> BenchmarkResult:
        """Benchmark contour extraction."""
        height, width = mask.shape
        mask_flat = mask.flatten().tolist()

        # Warm up
        _ = imagestag_rust.extract_contours(mask_flat, width, height)

        # Benchmark
        start = time.perf_counter()
        contours = imagestag_rust.extract_contours(mask_flat, width, height)
        elapsed = (time.perf_counter() - start) * 1000

        total_points = sum(len(c) for c in contours)

        result = BenchmarkResult(
            name=f"contour_{shape_type}_{width}x{height}",
            resolution=resolution,
            shape_type=shape_type,
            operation="contour_extraction",
            time_ms=elapsed,
            mask_pixels=int(np.sum(mask > 0)),
            contour_points=total_points
        )
        self.results.append(result)
        return result

    def benchmark_grow(self, mask: np.ndarray, radius: float,
                       shape_type: str, resolution: tuple[int, int]) -> BenchmarkResult:
        """Benchmark selection grow (dilation)."""
        # Need to convert to 3D for the filter (H, W, 1)
        mask_3d = mask.reshape(mask.shape[0], mask.shape[1], 1)

        # Warm up
        _ = dilate(mask_3d, radius)

        # Benchmark
        start = time.perf_counter()
        result_mask = dilate(mask_3d, radius)
        elapsed = (time.perf_counter() - start) * 1000

        result = BenchmarkResult(
            name=f"grow_{shape_type}_{resolution[0]}x{resolution[1]}_r{radius}",
            resolution=resolution,
            shape_type=shape_type,
            operation=f"grow_r{radius}",
            time_ms=elapsed,
            mask_pixels=int(np.sum(mask > 0))
        )
        self.results.append(result)
        return result

    def benchmark_shrink(self, mask: np.ndarray, radius: float,
                         shape_type: str, resolution: tuple[int, int]) -> BenchmarkResult:
        """Benchmark selection shrink (erosion)."""
        # Need to convert to 3D for the filter (H, W, 1)
        mask_3d = mask.reshape(mask.shape[0], mask.shape[1], 1)

        # Warm up
        _ = erode(mask_3d, radius)

        # Benchmark
        start = time.perf_counter()
        result_mask = erode(mask_3d, radius)
        elapsed = (time.perf_counter() - start) * 1000

        result = BenchmarkResult(
            name=f"shrink_{shape_type}_{resolution[0]}x{resolution[1]}_r{radius}",
            resolution=resolution,
            shape_type=shape_type,
            operation=f"shrink_r{radius}",
            time_ms=elapsed,
            mask_pixels=int(np.sum(mask > 0))
        )
        self.results.append(result)
        return result

    def print_summary(self):
        """Print summary of all benchmark results."""
        print("\n" + "=" * 80)
        print("SELECTION PERFORMANCE BENCHMARK RESULTS")
        print("=" * 80)

        # Group by operation
        by_operation = {}
        for r in self.results:
            op = r.operation
            if op not in by_operation:
                by_operation[op] = []
            by_operation[op].append(r)

        for operation, results in sorted(by_operation.items()):
            print(f"\n{operation.upper()}")
            print("-" * 60)
            print(f"{'Resolution':<15} {'Shape':<20} {'Time (ms)':<12} {'Pixels':<12}")
            print("-" * 60)

            for r in sorted(results, key=lambda x: (x.resolution[0] * x.resolution[1], x.shape_type)):
                res_str = f"{r.resolution[0]}x{r.resolution[1]}"
                extra = ""
                if r.contour_points > 0:
                    extra = f" ({r.contour_points} pts)"
                print(f"{res_str:<15} {r.shape_type:<20} {r.time_ms:<12.2f} {r.mask_pixels:<12}{extra}")

        # Performance analysis
        print("\n" + "=" * 80)
        print("PERFORMANCE ANALYSIS")
        print("=" * 80)

        # Find slowest operations
        if self.results:
            slowest = max(self.results, key=lambda x: x.time_ms)
            print(f"\nSlowest operation: {slowest.name}")
            print(f"  Time: {slowest.time_ms:.2f} ms")
            print(f"  Resolution: {slowest.resolution[0]}x{slowest.resolution[1]}")
            print(f"  Pixels: {slowest.mask_pixels}")

        # Scaling analysis
        print("\nScaling by resolution (contour extraction on circle):")
        circle_contours = [r for r in self.results
                          if r.operation == "contour_extraction" and r.shape_type == "circle"]
        if len(circle_contours) >= 2:
            circle_contours.sort(key=lambda x: x.resolution[0] * x.resolution[1])
            base = circle_contours[0]
            for r in circle_contours[1:]:
                size_ratio = (r.resolution[0] * r.resolution[1]) / (base.resolution[0] * base.resolution[1])
                time_ratio = r.time_ms / base.time_ms if base.time_ms > 0 else 0
                print(f"  {r.resolution[0]}x{r.resolution[1]}: {time_ratio:.1f}x time for {size_ratio:.1f}x pixels")


# Resolutions to test
RESOLUTIONS = [
    (256, 256),     # Small
    (512, 512),     # Medium
    (1280, 720),    # HD
    (1920, 1080),   # Full HD
]

# Shapes to test
SHAPE_GENERATORS = {
    "rectangle": SelectionMaskGenerator.rectangle,
    "circle": SelectionMaskGenerator.circle,
    "star_5pt": lambda w, h: SelectionMaskGenerator.star(w, h, points=5),
    "star_12pt": lambda w, h: SelectionMaskGenerator.star(w, h, points=12),
    "complex_concave": SelectionMaskGenerator.complex_concave,
    "multi_circles": SelectionMaskGenerator.multiple_circles,
    "checkerboard": SelectionMaskGenerator.checkerboard,
}


class TestSelectionPerformance:
    """Test selection operation performance."""

    @pytest.fixture(scope="class")
    def benchmark(self):
        """Create benchmark instance."""
        return SelectionBenchmark()

    @pytest.mark.parametrize("resolution", RESOLUTIONS)
    @pytest.mark.parametrize("shape_type", SHAPE_GENERATORS.keys())
    def test_contour_extraction(self, benchmark, resolution, shape_type):
        """Test contour extraction performance."""
        width, height = resolution
        generator = SHAPE_GENERATORS[shape_type]
        mask = generator(width, height)

        result = benchmark.benchmark_contour_extraction(mask, shape_type, resolution)

        # Performance assertions (adjust thresholds as needed)
        if resolution == (1920, 1080):
            # Full HD should complete in reasonable time
            assert result.time_ms < 5000, f"Contour extraction too slow: {result.time_ms:.2f}ms"

        print(f"  {shape_type} @ {width}x{height}: {result.time_ms:.2f}ms, "
              f"{result.contour_points} contour points")

    @pytest.mark.parametrize("resolution", RESOLUTIONS)
    @pytest.mark.parametrize("shape_type", ["circle", "star_5pt", "complex_concave"])
    @pytest.mark.parametrize("radius", [2.0, 5.0, 10.0])
    def test_grow(self, benchmark, resolution, shape_type, radius):
        """Test selection grow performance."""
        width, height = resolution
        generator = SHAPE_GENERATORS[shape_type]
        mask = generator(width, height)

        result = benchmark.benchmark_grow(mask, radius, shape_type, resolution)

        # Performance assertions
        if resolution == (1920, 1080) and radius == 10.0:
            assert result.time_ms < 10000, f"Grow too slow: {result.time_ms:.2f}ms"

        print(f"  grow {shape_type} r={radius} @ {width}x{height}: {result.time_ms:.2f}ms")

    @pytest.mark.parametrize("resolution", RESOLUTIONS)
    @pytest.mark.parametrize("shape_type", ["circle", "star_5pt", "complex_concave"])
    @pytest.mark.parametrize("radius", [2.0, 5.0, 10.0])
    def test_shrink(self, benchmark, resolution, shape_type, radius):
        """Test selection shrink performance."""
        width, height = resolution
        generator = SHAPE_GENERATORS[shape_type]
        mask = generator(width, height)

        result = benchmark.benchmark_shrink(mask, radius, shape_type, resolution)

        # Performance assertions
        if resolution == (1920, 1080) and radius == 10.0:
            assert result.time_ms < 10000, f"Shrink too slow: {result.time_ms:.2f}ms"

        print(f"  shrink {shape_type} r={radius} @ {width}x{height}: {result.time_ms:.2f}ms")

    @pytest.fixture(scope="class", autouse=True)
    def print_summary_at_end(self, benchmark, request):
        """Print summary after all tests complete."""
        yield
        # Print summary at end of test class
        benchmark.print_summary()


class TestConcavePolygonContours:
    """Specific tests for concave polygon contour extraction."""

    def test_star_contour_completeness(self):
        """Verify star contours form a complete boundary."""
        mask = SelectionMaskGenerator.star(500, 500, points=5)
        mask_flat = mask.flatten().tolist()

        contours = imagestag_rust.extract_contours(mask_flat, 500, 500)

        # Should have at least one contour
        assert len(contours) >= 1, "No contours extracted from star"

        # Main contour should have reasonable number of points
        main_contour = max(contours, key=len)
        assert len(main_contour) >= 10, f"Star contour has too few points: {len(main_contour)}"

        print(f"Star contour: {len(contours)} contours, main has {len(main_contour)} points")

    def test_complex_concave_contours(self):
        """Test L-shape with notches."""
        mask = SelectionMaskGenerator.complex_concave(500, 500)
        mask_flat = mask.flatten().tolist()

        contours = imagestag_rust.extract_contours(mask_flat, 500, 500)

        assert len(contours) >= 1, "No contours extracted from complex concave shape"

        total_points = sum(len(c) for c in contours)
        print(f"Complex concave: {len(contours)} contours, {total_points} total points")

    def test_multiple_disconnected_regions(self):
        """Test contours for multiple separate selections."""
        mask = SelectionMaskGenerator.multiple_circles(500, 500, count=5)
        mask_flat = mask.flatten().tolist()

        contours = imagestag_rust.extract_contours(mask_flat, 500, 500)

        # Should have multiple contours for separate regions
        print(f"Multiple circles: {len(contours)} contours")
        # Note: May be fewer than 5 if circles overlap
        assert len(contours) >= 1, "No contours extracted from multiple circles"


if __name__ == "__main__":
    # Run standalone benchmark
    print("Running Selection Performance Benchmark...")

    benchmark = SelectionBenchmark()

    for resolution in RESOLUTIONS:
        print(f"\n--- Resolution: {resolution[0]}x{resolution[1]} ---")

        for shape_type, generator in SHAPE_GENERATORS.items():
            mask = generator(*resolution)

            # Contour extraction
            result = benchmark.benchmark_contour_extraction(mask, shape_type, resolution)
            print(f"  contour {shape_type}: {result.time_ms:.2f}ms")

            # Grow/shrink for select shapes
            if shape_type in ["circle", "star_5pt"]:
                for radius in [2.0, 5.0, 10.0]:
                    grow_result = benchmark.benchmark_grow(mask, radius, shape_type, resolution)
                    shrink_result = benchmark.benchmark_shrink(mask, radius, shape_type, resolution)
                    print(f"    r={radius}: grow={grow_result.time_ms:.2f}ms, shrink={shrink_result.time_ms:.2f}ms")

    benchmark.print_summary()
