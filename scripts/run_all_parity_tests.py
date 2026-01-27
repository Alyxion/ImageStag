#!/usr/bin/env python3
"""
Run all parity tests for filters and layer effects across Python and JavaScript.

This script:
1. Clears existing test outputs
2. Saves ground truth inputs for JS to use
3. Runs all Python filter tests (ImageStag, OpenCV, scikit-image references)
4. Runs all Python layer effect tests
5. Runs all JavaScript filter tests via Node.js
6. Runs all JavaScript layer effect tests via Node.js
7. Generates comparison images (Python vs JS side-by-side)

Usage:
    python scripts/run_all_parity_tests.py [--no-js] [--no-python] [--no-compare]

Output directory: tmp/parity/
"""

import argparse
import subprocess
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def run_python_tests():
    """Run all Python parity tests."""
    print("\n" + "=" * 60)
    print("PYTHON PARITY TESTS")
    print("=" * 60)

    # Import after path setup
    import imagestag.parity.tests  # noqa: F401 - registers tests
    from imagestag.parity import (
        clear_test_dir,
        save_all_ground_truth_inputs,
        get_inputs_dir,
    )
    from imagestag.parity.runner import run_all_filter_tests, run_all_effect_tests

    # Clear and setup
    print("\n[1/4] Clearing test directory...")
    clear_test_dir()

    print("[2/4] Saving ground truth inputs...")
    saved = save_all_ground_truth_inputs()
    print(f"      Saved {len(saved)} inputs to {get_inputs_dir()}")

    # Run filter tests
    print("\n[3/4] Running Python filter tests...")
    filter_results = run_all_filter_tests(include_references=True)

    filter_count = sum(len(paths) for paths in filter_results.values())
    print(f"      Generated {filter_count} filter outputs:")
    for name, paths in sorted(filter_results.items()):
        print(f"        - {name}: {len(paths)} images")

    # Run layer effect tests
    print("\n[4/4] Running Python layer effect tests...")
    effect_results = run_all_effect_tests()

    effect_count = sum(len(paths) for paths in effect_results.values())
    print(f"      Generated {effect_count} layer effect outputs:")
    for name, paths in sorted(effect_results.items()):
        print(f"        - {name}: {len(paths)} images")

    total = filter_count + effect_count
    print(f"\n✓ Python tests complete: {total} images generated")

    return filter_results, effect_results


def run_js_tests():
    """Run all JavaScript parity tests via Node.js."""
    print("\n" + "=" * 60)
    print("JAVASCRIPT PARITY TESTS")
    print("=" * 60)

    js_dir = PROJECT_ROOT / "imagestag" / "parity" / "js"

    # Run filter tests
    print("\n[1/2] Running JavaScript filter tests...")
    filter_result = subprocess.run(
        ["node", "run_tests.js"],
        cwd=js_dir,
        capture_output=True,
        text=True,
    )

    if filter_result.returncode != 0:
        print(f"      ERROR: {filter_result.stderr}")
        return False

    # Parse results from output
    lines = filter_result.stdout.strip().split("\n")
    for line in lines[-5:]:
        if line.strip():
            print(f"      {line}")

    # Run layer effect tests
    print("\n[2/2] Running JavaScript layer effect tests...")
    effect_result = subprocess.run(
        ["node", "run_layer_effect_tests.js"],
        cwd=js_dir,
        capture_output=True,
        text=True,
    )

    if effect_result.returncode != 0:
        print(f"      ERROR: {effect_result.stderr}")
        return False

    # Parse results from output
    lines = effect_result.stdout.strip().split("\n")
    for line in lines[-5:]:
        if line.strip():
            print(f"      {line}")

    print("\n✓ JavaScript tests complete")
    return True


def generate_comparisons():
    """Generate side-by-side comparison images for Python vs JS."""
    print("\n" + "=" * 60)
    print("GENERATING COMPARISONS")
    print("=" * 60)

    import imagestag.parity.tests  # noqa: F401
    from imagestag.parity import PARITY_TEST_DIR
    from imagestag.parity.runner import (
        get_all_filter_names,
        get_all_effect_names,
        compare_filter_outputs,
        compare_effect_outputs,
    )

    comparisons_dir = PARITY_TEST_DIR / "comparisons"
    comparisons_dir.mkdir(parents=True, exist_ok=True)

    # Compare filters
    print("\n[1/2] Comparing filter outputs...")
    filter_names = get_all_filter_names()
    filter_results = []

    for name in filter_names:
        try:
            results = compare_filter_outputs(name, tolerance=0.01, save_comparisons=True)
            passed = sum(1 for r in results if r.match)
            failed = sum(1 for r in results if not r.match)
            filter_results.append((name, passed, failed, results))
            status = "✓" if failed == 0 else "✗"
            print(f"      {status} {name}: {passed} passed, {failed} failed")
        except Exception as e:
            print(f"      ✗ {name}: Error - {e}")
            filter_results.append((name, 0, 0, []))

    # Compare layer effects
    print("\n[2/2] Comparing layer effect outputs...")
    effect_names = get_all_effect_names()
    effect_results = []

    for name in effect_names:
        try:
            results = compare_effect_outputs(name, tolerance=0.01, save_comparisons=True)
            passed = sum(1 for r in results if r.match)
            failed = sum(1 for r in results if not r.match)
            effect_results.append((name, passed, failed, results))
            status = "✓" if failed == 0 else "✗"
            print(f"      {status} {name}: {passed} passed, {failed} failed")
        except Exception as e:
            print(f"      ✗ {name}: Error - {e}")
            effect_results.append((name, 0, 0, []))

    # Summary
    total_passed = sum(p for _, p, _, _ in filter_results + effect_results)
    total_failed = sum(f for _, _, f, _ in filter_results + effect_results)

    print(f"\n✓ Comparisons complete: {total_passed} passed, {total_failed} failed")
    print(f"  Comparison images saved to: {comparisons_dir}")

    return filter_results, effect_results


def print_summary(py_filters, py_effects, js_success, comparisons):
    """Print final summary."""
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    from imagestag.parity import PARITY_TEST_DIR

    # Count files
    filters_dir = PARITY_TEST_DIR / "filters"
    effects_dir = PARITY_TEST_DIR / "layer_effects"

    py_filter_count = len(list(filters_dir.glob("*_imagestag_*.png"))) if filters_dir.exists() else 0
    js_filter_count = len(list(filters_dir.glob("*_js_*.png"))) if filters_dir.exists() else 0
    ref_filter_count = len(list(filters_dir.glob("*_opencv.png"))) + len(list(filters_dir.glob("*_skimage.png"))) if filters_dir.exists() else 0

    py_effect_count = len(list(effects_dir.glob("*_imagestag_*.png"))) if effects_dir.exists() else 0
    js_effect_count = len(list(effects_dir.glob("*_js_*.png"))) if effects_dir.exists() else 0

    print(f"\nFilters:")
    print(f"  Python (ImageStag): {py_filter_count} images")
    print(f"  JavaScript (WASM):  {js_filter_count} images")
    print(f"  References:         {ref_filter_count} images")

    print(f"\nLayer Effects:")
    print(f"  Python (ImageStag): {py_effect_count} images")
    print(f"  JavaScript (WASM):  {js_effect_count} images")

    if comparisons:
        filter_comps, effect_comps = comparisons
        total_passed = sum(p for _, p, _, _ in filter_comps + effect_comps)
        total_failed = sum(f for _, _, f, _ in filter_comps + effect_comps)
        print(f"\nParity Comparisons:")
        print(f"  Passed: {total_passed}")
        print(f"  Failed: {total_failed}")

    print(f"\nOutput directory: {PARITY_TEST_DIR}")
    print(f"  filters/         - Filter test outputs")
    print(f"  layer_effects/   - Layer effect test outputs")
    print(f"  inputs/          - Ground truth inputs")
    print(f"  comparisons/     - Side-by-side comparison images")


def main():
    parser = argparse.ArgumentParser(
        description="Run all parity tests for filters and layer effects"
    )
    parser.add_argument(
        "--no-python",
        action="store_true",
        help="Skip Python tests",
    )
    parser.add_argument(
        "--no-js",
        action="store_true",
        help="Skip JavaScript tests",
    )
    parser.add_argument(
        "--no-compare",
        action="store_true",
        help="Skip generating comparison images",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("IMAGESTAG PARITY TEST RUNNER")
    print("=" * 60)
    print(f"Project root: {PROJECT_ROOT}")

    py_filters, py_effects = None, None
    js_success = False
    comparisons = None

    # Run Python tests
    if not args.no_python:
        py_filters, py_effects = run_python_tests()
    else:
        print("\n[Skipping Python tests]")

    # Run JavaScript tests
    if not args.no_js:
        js_success = run_js_tests()
    else:
        print("\n[Skipping JavaScript tests]")

    # Generate comparisons
    if not args.no_compare and not args.no_python and not args.no_js:
        comparisons = generate_comparisons()
    elif not args.no_compare:
        print("\n[Skipping comparisons - need both Python and JS tests]")

    # Print summary
    print_summary(py_filters, py_effects, js_success, comparisons)

    print("\n" + "=" * 60)
    print("DONE")
    print("=" * 60)


if __name__ == "__main__":
    main()
