"""Python-side parity test runner.

Runs registered parity tests for filters and layer effects,
saves outputs, and compares against JavaScript outputs.

Can also run reference implementations (OpenCV, scikit-image) for
comparison against ImageStag outputs.
"""
from typing import Callable, Any
import numpy as np
from pathlib import Path

from .config import get_test_dir, clear_test_dir
from .comparison import (
    save_test_image,
    compare_outputs,
    save_comparison_image,
    ComparisonResult,
)
from .registry import (
    get_filter_tests,
    get_effect_tests,
    generate_input,
    ParityTestSpec,
    TestCase,
)
from .reference_filters import (
    run_reference_filter,
    save_reference_output,
    list_opencv_filters,
    list_skimage_filters,
)


# Filter function type: (input: ndarray, **params) -> ndarray
FilterFunc = Callable[[np.ndarray], np.ndarray]

# Effect function type: (input: ndarray, **params) -> ndarray
EffectFunc = Callable[[np.ndarray], np.ndarray]

# Registry of filter implementations
_filter_impls: dict[str, FilterFunc] = {}

# Registry of effect implementations
_effect_impls: dict[str, EffectFunc] = {}


def register_filter_impl(name: str, func: FilterFunc) -> None:
    """Register a Python filter implementation for parity testing.

    Args:
        name: Filter name (must match registered parity tests)
        func: Filter function (input: ndarray) -> ndarray
    """
    _filter_impls[name] = func


def register_effect_impl(name: str, func: EffectFunc) -> None:
    """Register a Python effect implementation for parity testing.

    Args:
        name: Effect name (must match registered parity tests)
        func: Effect function (input: ndarray) -> ndarray
    """
    _effect_impls[name] = func


def _strip_f32_suffix(s: str) -> str:
    """Strip _f32 suffix from a string for unified naming."""
    if s.endswith("_f32"):
        return s[:-4]
    return s


def run_filter_test(
    name: str,
    test_case: TestCase,
    save: bool = True,
) -> tuple[np.ndarray, Path | None]:
    """Run a single filter test case.

    Args:
        name: Filter name (may include _f32 suffix)
        test_case: Test case specification
        save: Whether to save the output

    Returns:
        Tuple of (output_image, output_path)
    """
    func = _filter_impls.get(name)
    if func is None:
        raise ValueError(f"No ImageStag implementation registered for filter: {name}")

    # Generate input
    input_img = generate_input(
        test_case.input_generator,
        test_case.width,
        test_case.height,
    )

    # Apply filter (filters should support 1, 3, or 4 channels)
    output = func(input_img)

    # Save if requested
    # Naming: {filter}_{input}_imagestag_{bitdepth}.{format}
    # Strip _f32 suffix from filter name and test_case.id - bit_depth field handles that
    path = None
    if save:
        filter_name = _strip_f32_suffix(name)
        input_name = _strip_f32_suffix(test_case.id)
        path = save_test_image(
            output,
            "filters",
            filter_name,
            input_name,
            "imagestag",
            bit_depth=test_case.bit_depth,
        )

    return output, path


def run_effect_test(
    name: str,
    test_case: TestCase,
    save: bool = True,
) -> tuple[np.ndarray, Path | None]:
    """Run a single effect test case.

    Args:
        name: Effect name (may include _f32 suffix)
        test_case: Test case specification
        save: Whether to save the output

    Returns:
        Tuple of (output_image, output_path)
    """
    func = _effect_impls.get(name)
    if func is None:
        raise ValueError(f"No ImageStag implementation registered for effect: {name}")

    # Generate input
    input_img = generate_input(
        test_case.input_generator,
        test_case.width,
        test_case.height,
    )

    # Apply effect
    output = func(input_img)

    # Save if requested
    # Naming: {effect}_{input}_imagestag_{bitdepth}.{format}
    path = None
    if save:
        effect_name = _strip_f32_suffix(name)
        input_name = _strip_f32_suffix(test_case.id)
        path = save_test_image(
            output,
            "layer_effects",
            effect_name,
            input_name,
            "imagestag",
            bit_depth=test_case.bit_depth,
        )

    return output, path


def run_all_filter_tests(
    name: str | None = None,
    clear: bool = False,
    include_references: bool = True,
) -> dict[str, list[Path]]:
    """Run all registered filter parity tests.

    Also runs OpenCV and scikit-image reference implementations for comparison.

    Args:
        name: If specified, only run tests for this filter
        clear: Whether to clear existing outputs first
        include_references: Whether to also run OpenCV/SKImage references (default: True)

    Returns:
        Dict mapping filter names to list of output paths
    """
    if clear:
        clear_test_dir("filters")

    if name:
        specs = {name: get_filter_tests(name)}
        if specs[name] is None:
            raise ValueError(f"No parity tests registered for filter: {name}")
    else:
        specs = get_filter_tests()

    results: dict[str, list[Path]] = {}

    for filter_name, spec in specs.items():
        if spec is None:
            continue

        results[filter_name] = []
        for test_case in spec.test_cases:
            try:
                _, path = run_filter_test(filter_name, test_case)
                if path:
                    results[filter_name].append(path)

                # Also run reference implementations for u8 tests
                if include_references and test_case.bit_depth == "u8":
                    try:
                        run_reference_tests(filter_name, test_case, save=True)
                    except Exception as ref_e:
                        # Reference tests may fail if library doesn't support the filter
                        pass

            except Exception as e:
                print(f"Error running {filter_name}/{test_case.id}: {e}")

    return results


def run_all_effect_tests(
    name: str | None = None,
    clear: bool = False,
) -> dict[str, list[Path]]:
    """Run all registered effect parity tests.

    Args:
        name: If specified, only run tests for this effect
        clear: Whether to clear existing outputs first

    Returns:
        Dict mapping effect names to list of output paths
    """
    if clear:
        clear_test_dir("layer_effects")

    if name:
        specs = {name: get_effect_tests(name)}
        if specs[name] is None:
            raise ValueError(f"No parity tests registered for effect: {name}")
    else:
        specs = get_effect_tests()

    results: dict[str, list[Path]] = {}

    for effect_name, spec in specs.items():
        if spec is None:
            continue

        results[effect_name] = []
        for test_case in spec.test_cases:
            try:
                _, path = run_effect_test(effect_name, test_case)
                if path:
                    results[effect_name].append(path)
            except Exception as e:
                print(f"Error running {effect_name}/{test_case.id}: {e}")

    return results


def compare_filter_outputs(
    name: str,
    tolerance: float = 0.001,
    save_comparisons: bool = True,
) -> list[ComparisonResult]:
    """Compare Python and JS outputs for a filter.

    Args:
        name: Filter name
        tolerance: Maximum allowed diff ratio
        save_comparisons: Whether to save comparison images for failures

    Returns:
        List of comparison results
    """
    spec = get_filter_tests(name)
    if spec is None:
        raise ValueError(f"No parity tests registered for filter: {name}")

    results = []
    for test_case in spec.test_cases:
        result = compare_outputs("filters", name, test_case.id, tolerance)
        results.append(result)

        if not result.match and save_comparisons:
            save_comparison_image("filters", name, test_case.id)

    return results


# =============================================================================
# Reference Filter Support
# =============================================================================

def run_reference_tests(
    name: str,
    test_case: TestCase,
    save: bool = True,
) -> dict[str, tuple[np.ndarray | None, Path | None]]:
    """Run reference filter implementations for a test case.

    Only runs for u8 test cases (reference libraries don't support f32).

    Args:
        name: Filter name (may include _f32 suffix, will be stripped)
        test_case: Test case specification
        save: Whether to save the outputs

    Returns:
        Dict mapping library names to (output_image, output_path) tuples
    """
    # Skip f32 tests - reference libraries only support 8-bit
    if test_case.bit_depth == "f32":
        return {"opencv": (None, None), "skimage": (None, None)}

    # Strip _f32 suffix for clean naming
    filter_name = _strip_f32_suffix(name)
    input_name = _strip_f32_suffix(test_case.id)

    # Generate input
    input_img = generate_input(
        test_case.input_generator,
        test_case.width,
        test_case.height,
    )

    results = {}

    for library in ["opencv", "skimage"]:
        output = run_reference_filter(filter_name, input_img, test_case.params, library)

        path = None
        if output is not None and save:
            path = save_reference_output(
                output,
                "filters",
                filter_name,
                input_name,
                library,
            )

        results[library] = (output, path)

    return results


def run_all_reference_tests(
    name: str | None = None,
) -> dict[str, dict[str, list[Path]]]:
    """Run all reference implementations for registered filter tests.

    Only runs for u8 (8-bit) test cases.

    Args:
        name: If specified, only run for this filter

    Returns:
        Dict mapping library names to filter name -> paths dict
    """
    if name:
        specs = {name: get_filter_tests(name)}
        if specs[name] is None:
            raise ValueError(f"No parity tests registered for filter: {name}")
    else:
        specs = get_filter_tests()

    results = {"opencv": {}, "skimage": {}}

    for filter_name, spec in specs.items():
        if spec is None:
            continue

        results["opencv"][filter_name] = []
        results["skimage"][filter_name] = []

        for test_case in spec.test_cases:
            # Skip f32 tests
            if test_case.bit_depth == "f32":
                continue

            try:
                ref_outputs = run_reference_tests(filter_name, test_case)

                for library in ["opencv", "skimage"]:
                    _, path = ref_outputs[library]
                    if path:
                        results[library][filter_name].append(path)
            except Exception as e:
                print(f"Error running reference {filter_name}/{test_case.id}: {e}")

    return results


def get_available_references(name: str) -> dict[str, bool]:
    """Check which reference implementations are available for a filter.

    Args:
        name: Filter name

    Returns:
        Dict with "opencv" and "skimage" keys, True if available
    """
    return {
        "opencv": name in list_opencv_filters(),
        "skimage": name in list_skimage_filters(),
    }


def compare_effect_outputs(
    name: str,
    tolerance: float = 0.001,
    save_comparisons: bool = True,
) -> list[ComparisonResult]:
    """Compare Python and JS outputs for an effect.

    Args:
        name: Effect name
        tolerance: Maximum allowed diff ratio
        save_comparisons: Whether to save comparison images for failures

    Returns:
        List of comparison results
    """
    spec = get_effect_tests(name)
    if spec is None:
        raise ValueError(f"No parity tests registered for effect: {name}")

    results = []
    for test_case in spec.test_cases:
        result = compare_outputs("layer_effects", name, test_case.id, tolerance)
        results.append(result)

        if not result.match and save_comparisons:
            save_comparison_image("layer_effects", name, test_case.id)

    return results


class ParityTestRunner:
    """High-level test runner for cross-platform parity tests.

    Example:
        runner = ParityTestRunner()
        runner.register_filter("grayscale", grayscale_filter_func)
        runner.run_python_tests()

        # After JS tests have run...
        report = runner.compare_all()
        print(report)
    """

    def __init__(self, tolerance: float = 0.001):
        """Initialize the test runner.

        Args:
            tolerance: Default tolerance for comparisons
        """
        self.tolerance = tolerance
        self._filter_results: dict[str, list[ComparisonResult]] = {}
        self._effect_results: dict[str, list[ComparisonResult]] = {}

    def register_filter(self, name: str, func: FilterFunc) -> None:
        """Register a filter implementation."""
        register_filter_impl(name, func)

    def register_effect(self, name: str, func: EffectFunc) -> None:
        """Register an effect implementation."""
        register_effect_impl(name, func)

    def run_python_tests(
        self,
        filters: list[str] | None = None,
        effects: list[str] | None = None,
        clear: bool = True,
    ) -> None:
        """Run Python-side tests.

        Args:
            filters: Filter names to test (None = all registered)
            effects: Effect names to test (None = all registered)
            clear: Whether to clear existing outputs first
        """
        if filters is None:
            run_all_filter_tests(clear=clear)
        else:
            for name in filters:
                run_all_filter_tests(name, clear=clear)

        if effects is None:
            run_all_effect_tests(clear=clear)
        else:
            for name in effects:
                run_all_effect_tests(name, clear=clear)

    def compare_all(
        self,
        tolerance: float | None = None,
        save_comparisons: bool = True,
    ) -> dict[str, dict[str, list[ComparisonResult]]]:
        """Compare all Python vs JS outputs.

        Args:
            tolerance: Override default tolerance
            save_comparisons: Save comparison images for failures

        Returns:
            Dict with "filters" and "layer_effects" results
        """
        tol = tolerance or self.tolerance

        filter_tests = get_filter_tests()
        effect_tests = get_effect_tests()

        results = {
            "filters": {},
            "layer_effects": {},
        }

        for name in filter_tests:
            results["filters"][name] = compare_filter_outputs(
                name, tol, save_comparisons
            )

        for name in effect_tests:
            results["layer_effects"][name] = compare_effect_outputs(
                name, tol, save_comparisons
            )

        return results

    def generate_report(
        self,
        results: dict[str, dict[str, list[ComparisonResult]]] | None = None,
    ) -> str:
        """Generate a text report of comparison results.

        Args:
            results: Comparison results (runs compare_all if None)

        Returns:
            Formatted report string
        """
        if results is None:
            results = self.compare_all()

        lines = ["=" * 60, "Cross-Platform Parity Test Report", "=" * 60, ""]

        total_pass = 0
        total_fail = 0

        for category, tests in results.items():
            lines.append(f"\n## {category.upper()}\n")

            for name, comparisons in tests.items():
                lines.append(f"\n### {name}")
                for result in comparisons:
                    status = "✓ PASS" if result.match else "✗ FAIL"
                    lines.append(f"  {status}: {result.message}")
                    if result.match:
                        total_pass += 1
                    else:
                        total_fail += 1

        lines.append("")
        lines.append("=" * 60)
        lines.append(f"Total: {total_pass} passed, {total_fail} failed")
        lines.append("=" * 60)

        return "\n".join(lines)


__all__ = [
    'register_filter_impl',
    'register_effect_impl',
    'run_filter_test',
    'run_effect_test',
    'run_all_filter_tests',
    'run_all_effect_tests',
    'compare_filter_outputs',
    'compare_effect_outputs',
    'run_reference_tests',
    'run_all_reference_tests',
    'get_available_references',
    'ParityTestRunner',
]
