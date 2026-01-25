"""Cross-platform parity testing configuration.

This module defines shared configuration for Python/JavaScript filter
and layer effect parity tests. Both platforms use the same temp directory
and naming conventions to enable direct comparison.
"""
import os
from pathlib import Path
from typing import Literal

# Shared temp directory for parity test artifacts
# Uses a project-local tmp/ folder for easy inspection
_PROJECT_ROOT = Path(__file__).parent.parent.parent
PARITY_TEST_DIR = _PROJECT_ROOT / "tmp" / "parity"

# Image format for test outputs
# AVIF with matrix_coefficients=0 is truly lossless (stays in RGB, no YCbCr)
# Requires using pillow_heif directly, not Pillow's built-in AVIF encoder
OUTPUT_FORMAT: Literal["avif", "png", "webp", "rgba"] = "avif"

# Use lossless compression for parity testing (exact pixel match required)
LOSSLESS: bool = True

# Supported platforms
Platform = Literal["python", "js"]


def get_test_dir() -> Path:
    """Get the parity test directory, creating it if needed.

    Returns:
        Path to the parity test directory
    """
    PARITY_TEST_DIR.mkdir(parents=True, exist_ok=True)
    return PARITY_TEST_DIR


def get_output_path(
    category: str,
    name: str,
    test_case: str,
    platform: Platform,
    format: str | None = None,
) -> Path:
    """Get the output path for a parity test result.

    Naming convention: {category}/{name}_{test_case}_{platform}.{format}

    Args:
        category: Test category (e.g., "filters", "layer_effects")
        name: Filter/effect name (e.g., "grayscale", "drop_shadow")
        test_case: Test case identifier (e.g., "red_image", "astronaut")
        platform: Platform that generated this ("python" or "js")
        format: Image format (defaults to OUTPUT_FORMAT)

    Returns:
        Path for the output file

    Example:
        >>> get_output_path("filters", "grayscale", "red_image", "python")
        PosixPath('/tmp/imagestag_parity/filters/grayscale_red_image_python.avif')
    """
    fmt = format or OUTPUT_FORMAT
    test_dir = get_test_dir()
    category_dir = test_dir / category
    category_dir.mkdir(parents=True, exist_ok=True)
    return category_dir / f"{name}_{test_case}_{platform}.{fmt}"


def get_comparison_path(
    category: str,
    name: str,
    test_case: str,
) -> Path:
    """Get the path for a comparison/diff image.

    Args:
        category: Test category
        name: Filter/effect name
        test_case: Test case identifier

    Returns:
        Path for the comparison image
    """
    test_dir = get_test_dir()
    category_dir = test_dir / category
    category_dir.mkdir(parents=True, exist_ok=True)
    return category_dir / f"{name}_{test_case}_comparison.png"


def clear_test_dir(category: str | None = None) -> None:
    """Clear parity test artifacts.

    Args:
        category: If specified, only clear this category's artifacts.
                  If None, clear all artifacts.
    """
    import shutil

    test_dir = get_test_dir()
    if category:
        category_dir = test_dir / category
        if category_dir.exists():
            shutil.rmtree(category_dir)
    else:
        if test_dir.exists():
            shutil.rmtree(test_dir)
        test_dir.mkdir(parents=True, exist_ok=True)


def list_test_artifacts(category: str | None = None) -> list[Path]:
    """List all test artifacts.

    Args:
        category: If specified, only list this category's artifacts.

    Returns:
        List of artifact paths
    """
    test_dir = get_test_dir()
    if category:
        search_dir = test_dir / category
    else:
        search_dir = test_dir

    if not search_dir.exists():
        return []

    return sorted(search_dir.rglob("*.*"))


# Export config as JSON for JavaScript
def get_config_json() -> str:
    """Get configuration as JSON for JavaScript tests.

    Returns:
        JSON string with configuration
    """
    import json
    return json.dumps({
        "testDir": str(PARITY_TEST_DIR),
        "outputFormat": OUTPUT_FORMAT,
    })


def get_inputs_dir() -> Path:
    """Get the directory for ground truth input images.

    Returns:
        Path to the inputs directory
    """
    inputs_dir = PARITY_TEST_DIR / "inputs"
    inputs_dir.mkdir(parents=True, exist_ok=True)
    return inputs_dir


def save_ground_truth_input(name: str, image: "np.ndarray") -> Path:
    """Save a ground truth input image for JavaScript to use.

    This saves the image in a simple raw format that both
    Python and JavaScript can read identically.

    Format: 12-byte header (width u32le, height u32le, channels u32le) + raw bytes

    Args:
        name: Input name (e.g., 'deer', 'astronaut')
        image: numpy array (H, W, C) where C is 1, 3, or 4

    Returns:
        Path to the saved file
    """
    import numpy as np

    inputs_dir = get_inputs_dir()
    output_path = inputs_dir / f"{name}.raw"

    if image.ndim == 2:
        # Grayscale without channel dim - add it
        image = image[:, :, np.newaxis]

    height, width, channels = image.shape

    # Create header (width, height, channels) + data
    header = np.array([width, height, channels], dtype=np.uint32).tobytes()
    raw_data = image.astype(np.uint8).tobytes()

    with open(output_path, 'wb') as f:
        f.write(header + raw_data)

    return output_path


def save_all_ground_truth_inputs() -> list[Path]:
    """Save all registered ground truth inputs.

    This should be called before JavaScript tests run to ensure
    they have access to the same input images Python uses.

    Returns:
        List of saved file paths
    """
    from .registry import generate_input, _input_generators

    saved = []
    for name in _input_generators.keys():
        try:
            image = generate_input(name)
            path = save_ground_truth_input(name, image)
            saved.append(path)
        except Exception as e:
            print(f"Warning: Failed to save ground truth input '{name}': {e}")

    return saved


__all__ = [
    'PARITY_TEST_DIR',
    'OUTPUT_FORMAT',
    'Platform',
    'get_test_dir',
    'get_output_path',
    'get_comparison_path',
    'clear_test_dir',
    'list_test_artifacts',
    'get_config_json',
    'get_inputs_dir',
    'save_ground_truth_input',
    'save_all_ground_truth_inputs',
]
