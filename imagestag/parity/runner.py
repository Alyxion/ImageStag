"""Python-side parity test runner.

Runs registered parity tests for filters and layer effects,
saves outputs, and compares against JavaScript outputs.
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


def run_filter_test(
    name: str,
    test_case: TestCase,
    save: bool = True,
) -> tuple[np.ndarray, Path | None]:
    """Run a single filter test case.

    Args:
        name: Filter name
        test_case: Test case specification
        save: Whether to save the output

    Returns:
        Tuple of (output_image, output_path)
    """
    func = _filter_impls.get(name)
    if func is None:
        raise ValueError(f"No Python implementation registered for filter: {name}")

    # Generate input
    input_img = generate_input(
        test_case.input_generator,
        test_case.width,
        test_case.height,
    )

    # Apply filter
    output = func(input_img)

    # Save if requested
    path = None
    if save:
        path = save_test_image(
            output,
            "filters",
            name,
            test_case.id,
            "python",
        )

    return output, path


def run_effect_test(
    name: str,
    test_case: TestCase,
    save: bool = True,
) -> tuple[np.ndarray, Path | None]:
    """Run a single effect test case.

    Args:
        name: Effect name
        test_case: Test case specification
        save: Whether to save the output

    Returns:
        Tuple of (output_image, output_path)
    """
    func = _effect_impls.get(name)
    if func is None:
        raise ValueError(f"No Python implementation registered for effect: {name}")

    # Generate input
    input_img = generate_input(
        test_case.input_generator,
        test_case.width,
        test_case.height,
    )

    # Apply effect
    output = func(input_img)

    # Save if requested
    path = None
    if save:
        path = save_test_image(
            output,
            "layer_effects",
            name,
            test_case.id,
            "python",
        )

    return output, path


def run_all_filter_tests(
    name: str | None = None,
    clear: bool = False,
) -> dict[str, list[Path]]:
    """Run all registered filter parity tests.

    Args:
        name: If specified, only run tests for this filter
        clear: Whether to clear existing outputs first

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
    'ParityTestRunner',
]
