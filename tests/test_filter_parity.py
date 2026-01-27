"""Cross-platform parity tests for ImageStag filters.

This module runs parity tests comparing Python (Rust) and JavaScript implementations
of filters. Both platforms save outputs to a shared temp directory, and this test
compares them.

Test inputs are ground truth images:
- deer: Noto emoji deer at 400x400 (4-channel RGBA with transparency)
- astronaut: Skimage astronaut at 400x400 (3-channel RGB, no transparency)

Run with:
    # Run Python-side tests and compare
    poetry run pytest tests/test_filter_parity.py -v

    # Run JavaScript tests first (in a separate terminal)
    node imagestag/parity/js/run_tests.js

Test artifacts are saved to: tmp/parity/
"""

import pytest
import numpy as np
from pathlib import Path

# Import and register parity tests
import imagestag.parity.tests  # noqa: F401 - registers tests on import

from imagestag.parity import (
    get_test_dir,
    clear_test_dir,
    get_filter_tests,
    run_all_filter_tests,
    compare_filter_outputs,
    save_comparison_image,
    load_test_image,
    ComparisonResult,
    save_all_ground_truth_inputs,
    get_inputs_dir,
)


@pytest.fixture(scope="module", autouse=True)
def setup_parity_tests():
    """Setup parity test directory before running tests.

    Clears Python outputs but preserves JS outputs (if any) for comparison.
    Also saves ground truth inputs for JavaScript tests to use.
    """
    from imagestag.parity import PARITY_TEST_DIR
    import shutil

    # Check if JS outputs exist before clearing
    filters_dir = PARITY_TEST_DIR / "filters"
    js_outputs = list(filters_dir.glob("*_js.*")) if filters_dir.exists() else []
    has_js_outputs = len(js_outputs) > 0

    if has_js_outputs:
        # Only clear ImageStag outputs, preserve JS outputs
        for py_output in filters_dir.glob("*_imagestag.*"):
            py_output.unlink()
        # Clear inputs to regenerate them
        inputs_dir = PARITY_TEST_DIR / "inputs"
        if inputs_dir.exists():
            shutil.rmtree(inputs_dir)
    else:
        # No JS outputs, do a full clean
        clear_test_dir()

    get_test_dir()

    # Save ground truth inputs for JS to use
    saved = save_all_ground_truth_inputs()
    print(f"\nSaved {len(saved)} ground truth inputs to {get_inputs_dir()}")

    yield


class TestGrayscaleFilterParity:
    """Parity tests for the grayscale filter."""

    def test_python_outputs_generated(self):
        """Run Python-side grayscale tests and verify outputs are saved."""
        results = run_all_filter_tests("grayscale", clear=False)

        assert "grayscale" in results
        assert len(results["grayscale"]) > 0, "No test outputs were generated"

        # Verify outputs exist
        for path in results["grayscale"]:
            assert path.exists(), f"Output file not created: {path}"

    def test_grayscale_deer(self):
        """Test grayscale on deer emoji - vector with transparency."""
        from imagestag.parity.constants import TEST_WIDTH, TEST_HEIGHT
        run_all_filter_tests("grayscale")

        py_img = load_test_image("filters", "grayscale", "deer", "imagestag")
        assert py_img is not None, "ImageStag output not found"
        # Deer is 4-channel RGBA
        assert py_img.shape == (TEST_HEIGHT, TEST_WIDTH, 4), f"Unexpected shape: {py_img.shape}"

        # Verify R=G=B (grayscale property)
        assert np.allclose(py_img[:, :, 0], py_img[:, :, 1]), \
            "R and G channels should be equal"
        assert np.allclose(py_img[:, :, 1], py_img[:, :, 2]), \
            "G and B channels should be equal"

    def test_grayscale_astronaut(self):
        """Test grayscale on astronaut - photographic image."""
        from imagestag.parity.constants import TEST_WIDTH, TEST_HEIGHT
        run_all_filter_tests("grayscale")

        py_img = load_test_image("filters", "grayscale", "astronaut", "imagestag")
        assert py_img is not None, "ImageStag output not found"
        # Astronaut is 3-channel RGB (no alpha)
        assert py_img.shape == (TEST_HEIGHT, TEST_WIDTH, 3), f"Unexpected shape: {py_img.shape}"

        # Verify R=G=B (grayscale property)
        assert np.allclose(py_img[:, :, 0], py_img[:, :, 1]), \
            "R and G channels should be equal"
        assert np.allclose(py_img[:, :, 1], py_img[:, :, 2]), \
            "G and B channels should be equal"


class TestCrossplatformParity:
    """Tests that compare Python and JavaScript outputs.

    These tests require JavaScript tests to have run first and saved
    their outputs to the shared temp directory.
    """

    @pytest.fixture(autouse=True)
    def run_python_tests(self):
        """Ensure Python tests have run before comparison."""
        run_all_filter_tests("grayscale")

    def test_parity_comparison_structure(self):
        """Test that comparison infrastructure works correctly."""
        spec = get_filter_tests("grayscale")
        assert spec is not None
        assert len(spec.test_cases) == 2, "Expected 2 test cases (deer, astronaut)"

    def test_compare_outputs_reports_missing_js(self):
        """Test that comparison correctly reports missing JS outputs."""
        results = compare_filter_outputs("grayscale", save_comparisons=False)

        assert len(results) > 0
        for result in results:
            assert isinstance(result, ComparisonResult)
            assert hasattr(result, 'match')
            assert hasattr(result, 'diff_ratio')
            assert hasattr(result, 'message')

    def test_grayscale_parity_with_js(self):
        """Test grayscale parity between Python and JavaScript.

        This test requires JavaScript tests to have run first:
            node imagestag/parity/js/run_tests.js
        """
        from imagestag.parity import PARITY_TEST_DIR

        # Check if JS outputs exist
        filters_dir = PARITY_TEST_DIR / "filters"
        js_outputs = list(filters_dir.glob("grayscale_*_js.*")) if filters_dir.exists() else []
        if not js_outputs:
            pytest.skip("JavaScript test outputs not found - run: node imagestag/parity/js/run_tests.js")

        results = compare_filter_outputs(
            "grayscale",
            tolerance=0.001,  # 0.1% maximum difference
            save_comparisons=True,
        )

        failed = [r for r in results if not r.match]
        if failed:
            for result in failed:
                print(f"FAILED: {result.message}")

        assert len(failed) == 0, \
            f"{len(failed)} parity tests failed. Check {PARITY_TEST_DIR}/filters/ for comparison images"


class TestParityTestInfrastructure:
    """Tests for the parity testing infrastructure itself."""

    def test_test_dir_creation(self):
        """Test that test directory is created correctly."""
        test_dir = get_test_dir()
        assert test_dir.exists()
        assert test_dir.is_dir()

    def test_inputs_dir_creation(self):
        """Test that inputs directory is created correctly."""
        inputs_dir = get_inputs_dir()
        assert inputs_dir.exists()
        assert inputs_dir.is_dir()

    def test_ground_truth_inputs_saved(self):
        """Test that ground truth inputs are saved."""
        from imagestag.parity.constants import TEST_WIDTH, TEST_HEIGHT, TEST_INPUTS
        inputs_dir = get_inputs_dir()

        # Check that our two inputs exist (.raw format with 12-byte header)
        deer_path = inputs_dir / "deer.raw"
        astronaut_path = inputs_dir / "astronaut.raw"

        assert deer_path.exists(), "deer.raw not found"
        assert astronaut_path.exists(), "astronaut.raw not found"

        # Verify format: 12-byte header (width, height, channels as u32) + pixel data
        deer_channels = TEST_INPUTS["deer"]["channels"]  # 4 (RGBA)
        deer_data = deer_path.read_bytes()
        expected_deer_size = 12 + (TEST_WIDTH * TEST_HEIGHT * deer_channels)
        assert len(deer_data) == expected_deer_size, f"deer.raw has wrong size: {len(deer_data)} vs {expected_deer_size}"

        astronaut_channels = TEST_INPUTS["astronaut"]["channels"]  # 3 (RGB)
        astronaut_data = astronaut_path.read_bytes()
        expected_astronaut_size = 12 + (TEST_WIDTH * TEST_HEIGHT * astronaut_channels)
        assert len(astronaut_data) == expected_astronaut_size, f"astronaut.raw has wrong size: {len(astronaut_data)} vs {expected_astronaut_size}"

    def test_registry_export_json(self):
        """Test that registry can be exported as JSON."""
        from imagestag.parity import export_registry_json
        import json

        json_str = export_registry_json()
        data = json.loads(json_str)

        assert "filters" in data
        assert "grayscale" in data["filters"]
        assert "testCases" in data["filters"]["grayscale"]
        assert len(data["filters"]["grayscale"]["testCases"]) == 2


class TestBitDepthComparison:
    """Tests comparing u8 (8-bit) and f32 (float) filter outputs.

    These tests verify that:
    1. Both u8 and f32 versions produce valid outputs
    2. The difference between u8 and f32 outputs is minimal
    3. f32->u8 roundtrip preserves precision within expected tolerance
    """

    @pytest.fixture(autouse=True)
    def run_all_tests(self):
        """Ensure both u8 and f32 tests have run."""
        run_all_filter_tests("grayscale")
        run_all_filter_tests("grayscale_f32")

    def test_f32_outputs_generated(self):
        """Test that f32 grayscale outputs are generated."""
        results = run_all_filter_tests("grayscale_f32", clear=False)

        assert "grayscale_f32" in results
        assert len(results["grayscale_f32"]) == 2, "Expected 2 f32 test outputs"

        # Verify outputs exist
        for path in results["grayscale_f32"]:
            assert path.exists(), f"f32 output file not created: {path}"

    def test_u8_f32_parity_deer(self):
        """Test that u8 and f32 grayscale outputs match within 1 level.

        The f32 output is stored as 12-bit (0-4095), so we scale it to 8-bit
        for comparison. The difference should be at most 1 due to rounding.
        """
        u8_img = load_test_image("filters", "grayscale", "deer", "imagestag", "u8")
        f32_img = load_test_image("filters", "grayscale", "deer", "imagestag", "f32")

        assert u8_img is not None, "u8 output not found"
        assert f32_img is not None, "f32 output not found"

        # f32 output is 12-bit (0-4095), scale to 8-bit (0-255) for comparison
        if f32_img.dtype == np.uint16:
            # Scale 12-bit to 8-bit: value * 255 / 4095
            f32_scaled = (f32_img.astype(np.float32) * 255.0 / 4095.0).round().astype(np.int16)
        else:
            f32_scaled = f32_img.astype(np.int16)

        # Compare - max difference should be 1 (rounding)
        diff = np.abs(u8_img.astype(np.int16) - f32_scaled)
        max_diff = np.max(diff)

        assert max_diff <= 1, \
            f"u8 vs f32 difference too large: max_diff={max_diff}, expected <= 1"

        # Calculate diff ratio (pixels with any difference)
        diff_pixels = np.sum(np.any(diff > 0, axis=2))
        total_pixels = u8_img.shape[0] * u8_img.shape[1]
        diff_ratio = diff_pixels / total_pixels

        print(f"deer: max_diff={max_diff}, diff_ratio={diff_ratio:.4%}")

    def test_u8_f32_parity_astronaut(self):
        """Test that u8 and f32 astronaut outputs match within 1 level.

        The f32 output is stored as 12-bit (0-4095), so we scale it to 8-bit.
        """
        u8_img = load_test_image("filters", "grayscale", "astronaut", "imagestag", "u8")
        f32_img = load_test_image("filters", "grayscale", "astronaut", "imagestag", "f32")

        assert u8_img is not None, "u8 output not found"
        assert f32_img is not None, "f32 output not found"

        # f32 output is 12-bit (0-4095), scale to 8-bit (0-255) for comparison
        if f32_img.dtype == np.uint16:
            f32_scaled = (f32_img.astype(np.float32) * 255.0 / 4095.0).round().astype(np.int16)
        else:
            f32_scaled = f32_img.astype(np.int16)

        # Compare - max difference should be 1 (rounding)
        diff = np.abs(u8_img.astype(np.int16) - f32_scaled)
        max_diff = np.max(diff)

        assert max_diff <= 1, \
            f"u8 vs f32 difference too large: max_diff={max_diff}, expected <= 1"

        # Calculate diff ratio
        diff_pixels = np.sum(np.any(diff > 0, axis=2))
        total_pixels = u8_img.shape[0] * u8_img.shape[1]
        diff_ratio = diff_pixels / total_pixels

        print(f"astronaut: max_diff={max_diff}, diff_ratio={diff_ratio:.4%}")

    def test_f32_js_parity(self):
        """Test f32 grayscale parity between Python and JavaScript.

        This test requires JavaScript tests to have run first:
            node imagestag/parity/js/run_tests.js
        """
        from imagestag.parity import PARITY_TEST_DIR

        # Check if JS f32 outputs exist
        filters_dir = PARITY_TEST_DIR / "filters"
        js_outputs = list(filters_dir.glob("grayscale_f32_*_js.*")) if filters_dir.exists() else []
        if not js_outputs:
            pytest.skip("JavaScript f32 test outputs not found - run: node imagestag/parity/js/run_tests.js")

        results = compare_filter_outputs(
            "grayscale_f32",
            tolerance=0.001,  # 0.1% maximum difference
            save_comparisons=True,
        )

        failed = [r for r in results if not r.match]
        if failed:
            for result in failed:
                print(f"FAILED: {result.message}")

        assert len(failed) == 0, \
            f"{len(failed)} f32 parity tests failed. Check {PARITY_TEST_DIR}/filters/ for comparison images"

    def test_12bit_roundtrip_precision(self):
        """Test that 12-bit conversion preserves float precision.

        12-bit (0-4095) allows ~12 bits of precision per channel.
        Error should be less than 1 step (1/4095 ≈ 0.000244).
        """
        from imagestag.filters.grayscale import (
            convert_u8_to_f32,
            convert_f32_to_12bit,
            convert_12bit_to_f32,
        )

        # Create test image
        test_img = np.array([[[100, 150, 200, 255]]], dtype=np.uint8)

        # Convert to f32
        f32_img = convert_u8_to_f32(test_img)

        # Roundtrip through 12-bit
        as_12bit = convert_f32_to_12bit(f32_img)
        back_to_f32 = convert_12bit_to_f32(as_12bit)

        # Maximum error should be less than 1 full step in 12-bit
        # (accounting for u8->f32 quantization before the roundtrip)
        max_error = 1.0 / 4095.0
        actual_error = np.max(np.abs(f32_img - back_to_f32))

        assert actual_error < max_error, \
            f"12-bit roundtrip error too large: {actual_error} > {max_error}"

        print(f"12-bit roundtrip: actual_error={actual_error:.8f}, max_allowed={max_error:.8f}")
