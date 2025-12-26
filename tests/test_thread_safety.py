"""Thread safety tests for filters and pipelines.

These tests verify that filters can be executed concurrently from multiple
threads without race conditions or corrupted results.
"""

import pytest
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

from imagestag import Image
from imagestag.pixel_format import PixelFormat
from imagestag.filters import (
    Resize,
    FalseColor,
    Grayscale,
    Brightness,
    GaussianBlur,
    FilterPipeline,
    StreamingPipelineExecutor,
    BatchPipelineExecutor,
)


@pytest.fixture
def test_images():
    """Create a list of distinct test images."""
    images = []
    for i in range(10):
        # Each image has a unique pattern based on its index
        pixels = np.full((100, 100, 3), i * 25, dtype=np.uint8)
        pixels[:, :, 0] = i * 25  # Red varies by index
        images.append(Image(pixels, pixel_format=PixelFormat.RGB))
    return images


class TestFilterThreadSafety:
    """Test that individual filters are thread-safe."""

    def test_resize_concurrent(self, test_images):
        """Resize filter should be thread-safe for concurrent calls."""
        resize = Resize(scale=0.5)
        results = []
        errors = []

        def process(img):
            try:
                return resize.apply(img)
            except Exception as e:
                errors.append(e)
                return None

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(process, img) for img in test_images]
            for f in as_completed(futures):
                result = f.result()
                if result is not None:
                    results.append(result)

        assert len(errors) == 0, f"Errors during concurrent execution: {errors}"
        assert len(results) == len(test_images)
        assert all(r.width == 50 for r in results)
        assert all(r.height == 50 for r in results)

    def test_falsecolor_concurrent(self, test_images):
        """FalseColor filter should be thread-safe with shared LUT cache."""
        fc = FalseColor(colormap='hot')
        results = []
        errors = []

        def process(img):
            try:
                return fc.apply(img)
            except Exception as e:
                errors.append(e)
                return None

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(process, img) for img in test_images]
            for f in as_completed(futures):
                result = f.result()
                if result is not None:
                    results.append(result)

        assert len(errors) == 0, f"Errors during concurrent execution: {errors}"
        assert len(results) == len(test_images)

    def test_same_filter_many_threads(self, test_images):
        """Same filter instance called from many threads simultaneously."""
        grayscale = Grayscale()
        call_count = threading.atomic = 0
        lock = threading.Lock()
        errors = []

        def process(img, thread_id):
            try:
                for _ in range(10):  # Each thread processes 10 times
                    result = grayscale.apply(img)
                    assert result.width == img.width
                with lock:
                    nonlocal call_count
                    call_count += 1
            except Exception as e:
                errors.append((thread_id, e))

        threads = []
        for i, img in enumerate(test_images):
            t = threading.Thread(target=process, args=(img, i))
            threads.append(t)

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors: {errors}"
        assert call_count == len(test_images)

    def test_different_colormaps_concurrent(self, test_images):
        """Different FalseColor instances with different colormaps."""
        colormaps = ['hot', 'viridis', 'plasma', 'inferno', 'magma']
        filters = [FalseColor(colormap=cm) for cm in colormaps]
        results = []
        errors = []

        def process(img, fc):
            try:
                return fc.apply(img)
            except Exception as e:
                errors.append(e)
                return None

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            for img in test_images:
                for fc in filters:
                    futures.append(executor.submit(process, img, fc))

            for f in as_completed(futures):
                result = f.result()
                if result is not None:
                    results.append(result)

        assert len(errors) == 0
        assert len(results) == len(test_images) * len(filters)


class TestPipelineThreadSafety:
    """Test that pipelines are thread-safe."""

    def test_pipeline_concurrent(self, test_images):
        """Pipeline should be thread-safe for concurrent processing."""
        pipeline = FilterPipeline(filters=[
            Resize(scale=0.5),
            GaussianBlur(radius=1),
            Grayscale(),
        ])
        results = []
        errors = []

        def process(img):
            try:
                return pipeline.apply(img)
            except Exception as e:
                errors.append(e)
                return None

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(process, img) for img in test_images]
            for f in as_completed(futures):
                result = f.result()
                if result is not None:
                    results.append(result)

        assert len(errors) == 0, f"Errors: {errors}"
        assert len(results) == len(test_images)
        assert all(r.width == 50 for r in results)


class TestExecutorThreadSafety:
    """Test executor thread safety."""

    def test_streaming_executor_preserves_results(self, test_images):
        """StreamingPipelineExecutor should produce correct results."""
        pipeline = FilterPipeline(filters=[
            Resize(scale=0.5),
            Brightness(factor=1.5),
        ])

        with StreamingPipelineExecutor(pipeline) as executor:
            for img in test_images:
                executor.submit(img)

            results = list(executor.results(len(test_images)))

        assert len(results) == len(test_images)
        assert all(r.width == 50 for r in results)

    def test_batch_executor_preserves_order(self, test_images):
        """BatchPipelineExecutor should preserve input order."""
        pipeline = FilterPipeline(filters=[
            Resize(scale=0.5),
        ])

        with BatchPipelineExecutor(pipeline, num_workers=4) as executor:
            results = executor.process_all(test_images)

        assert len(results) == len(test_images)

        # Verify order is preserved by checking red channel values
        for i, result in enumerate(results):
            pixels = result.get_pixels(PixelFormat.RGB)
            # The red channel should match the original image's pattern
            expected_red = i * 25
            actual_red = pixels[0, 0, 0]
            # Allow small difference due to resize interpolation
            assert abs(int(actual_red) - expected_red) < 30, \
                f"Image {i}: expected red ~{expected_red}, got {actual_red}"

    def test_multiple_executors_concurrent(self, test_images):
        """Multiple executors running concurrently should not interfere."""
        pipeline1 = FilterPipeline(filters=[Resize(scale=0.5)])
        pipeline2 = FilterPipeline(filters=[Grayscale()])

        results1 = []
        results2 = []
        errors = []

        def run_executor1():
            try:
                with BatchPipelineExecutor(pipeline1, num_workers=2) as executor:
                    results1.extend(executor.process_all(test_images))
            except Exception as e:
                errors.append(e)

        def run_executor2():
            try:
                with BatchPipelineExecutor(pipeline2, num_workers=2) as executor:
                    results2.extend(executor.process_all(test_images))
            except Exception as e:
                errors.append(e)

        t1 = threading.Thread(target=run_executor1)
        t2 = threading.Thread(target=run_executor2)

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert len(errors) == 0, f"Errors: {errors}"
        assert len(results1) == len(test_images)
        assert len(results2) == len(test_images)

        # Verify correct transformations
        assert all(r.width == 50 for r in results1)  # Resized
        assert all(r.width == 100 for r in results2)  # Grayscale, same size


class TestNoGlobalStateMutation:
    """Test that filters don't mutate global state."""

    def test_filter_instance_unchanged_after_apply(self, test_images):
        """Filter parameters should not change after apply()."""
        resize = Resize(scale=0.5)
        original_scale = resize.scale

        for img in test_images:
            _ = resize.apply(img)

        assert resize.scale == original_scale

    def test_brightness_instance_unchanged(self, test_images):
        """Brightness filter should not change its factor."""
        brightness = Brightness(factor=1.5)
        original_factor = brightness.factor

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(brightness.apply, img) for img in test_images]
            for f in futures:
                f.result()

        assert brightness.factor == original_factor

    def test_falsecolor_lut_cache_thread_safe(self, test_images):
        """FalseColor LUT cache should handle concurrent access safely."""
        # Clear the cache to force concurrent cache population
        FalseColor._lut_cache.clear()

        filters = [FalseColor(colormap='viridis') for _ in range(10)]

        def apply_filter(fc, img):
            return fc.apply(img)

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for fc, img in zip(filters, test_images):
                futures.append(executor.submit(apply_filter, fc, img))

            results = [f.result() for f in futures]

        # All results should be valid
        assert all(r.width == 100 for r in results)

        # Cache should have entries
        assert len(FalseColor._lut_cache) > 0
