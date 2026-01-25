"""Registry for cross-platform parity tests.

Filters and layer effects register their test cases here. Both Python and
JavaScript implementations use this registry to know which tests to run.

Parity test inputs are sourced from pre-rendered images served by the API
to ensure Python and JavaScript use identical ground truth images.
"""
from dataclasses import dataclass, field
from typing import Callable, Any
import json
import numpy as np
from pathlib import Path

# Type for test input generator functions
TestInputGenerator = Callable[[], np.ndarray]

# Path to samples directory
_SAMPLES_DIR = Path(__file__).parent.parent / "samples"


@dataclass
class TestCase:
    """A single parity test case."""
    id: str
    description: str
    width: int
    height: int
    input_generator: str  # Name of input generator function
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class ParityTestSpec:
    """Specification for a filter/effect's parity tests."""
    category: str  # "filters" or "layer_effects"
    name: str      # Filter/effect name (e.g., "grayscale")
    test_cases: list[TestCase] = field(default_factory=list)


# Global registries
_filter_tests: dict[str, ParityTestSpec] = {}
_effect_tests: dict[str, ParityTestSpec] = {}

# Built-in input generators
_input_generators: dict[str, TestInputGenerator] = {}


def register_input_generator(name: str):
    """Decorator to register an input generator function.

    Example:
        @register_input_generator("deer_128")
        def gen_deer_128() -> np.ndarray:
            ...
    """
    def decorator(func: TestInputGenerator) -> TestInputGenerator:
        _input_generators[name] = func
        return func
    return decorator


def get_input_generator(name: str) -> TestInputGenerator | None:
    """Get a registered input generator by name."""
    return _input_generators.get(name)


def register_filter_parity(name: str, test_cases: list[TestCase]) -> None:
    """Register parity tests for a filter.

    Args:
        name: Filter name (e.g., "grayscale")
        test_cases: List of test cases
    """
    _filter_tests[name] = ParityTestSpec(
        category="filters",
        name=name,
        test_cases=test_cases
    )


def register_effect_parity(name: str, test_cases: list[TestCase]) -> None:
    """Register parity tests for a layer effect.

    Args:
        name: Effect name (e.g., "drop_shadow")
        test_cases: List of test cases
    """
    _effect_tests[name] = ParityTestSpec(
        category="layer_effects",
        name=name,
        test_cases=test_cases
    )


def get_filter_tests(name: str | None = None) -> dict[str, ParityTestSpec] | ParityTestSpec | None:
    """Get registered filter parity tests.

    Args:
        name: If specified, get tests for this filter only

    Returns:
        All filter tests or specific filter's tests
    """
    if name:
        return _filter_tests.get(name)
    return _filter_tests.copy()


def get_effect_tests(name: str | None = None) -> dict[str, ParityTestSpec] | ParityTestSpec | None:
    """Get registered layer effect parity tests.

    Args:
        name: If specified, get tests for this effect only

    Returns:
        All effect tests or specific effect's tests
    """
    if name:
        return _effect_tests.get(name)
    return _effect_tests.copy()


def get_all_tests() -> dict[str, dict[str, ParityTestSpec]]:
    """Get all registered parity tests.

    Returns:
        Dict with "filters" and "layer_effects" keys
    """
    return {
        "filters": _filter_tests.copy(),
        "layer_effects": _effect_tests.copy(),
    }


def export_registry_json() -> str:
    """Export the registry as JSON for JavaScript tests.

    Returns:
        JSON string with all test specifications
    """
    def spec_to_dict(spec: ParityTestSpec) -> dict:
        return {
            "category": spec.category,
            "name": spec.name,
            "testCases": [
                {
                    "id": tc.id,
                    "description": tc.description,
                    "width": tc.width,
                    "height": tc.height,
                    "inputGenerator": tc.input_generator,
                    "params": tc.params,
                }
                for tc in spec.test_cases
            ]
        }

    data = {
        "filters": {k: spec_to_dict(v) for k, v in _filter_tests.items()},
        "layerEffects": {k: spec_to_dict(v) for k, v in _effect_tests.items()},
        "inputGenerators": list(_input_generators.keys()),
    }
    return json.dumps(data, indent=2)


# =============================================================================
# Built-in Input Generators (ground truth images)
#
# These generators produce the exact same output as the API endpoints
# to ensure consistency between Python and JavaScript.
# =============================================================================

def _render_svg_to_rgba(svg_path: Path, width: int, height: int) -> np.ndarray:
    """Render SVG to RGBA numpy array at specified size."""
    import cairosvg
    from PIL import Image
    from io import BytesIO

    png_bytes = cairosvg.svg2png(
        url=str(svg_path),
        output_width=width,
        output_height=height,
    )
    pil_img = Image.open(BytesIO(png_bytes))
    if pil_img.mode != 'RGBA':
        pil_img = pil_img.convert('RGBA')
    return np.array(pil_img, dtype=np.uint8)


@register_input_generator("deer_128")
def gen_deer_128() -> np.ndarray:
    """Noto emoji deer rendered at 128x128.

    This is the primary test image for parity testing - a colorful
    vector graphic with transparency.
    """
    svg_path = _SAMPLES_DIR / "svgs" / "noto-emoji" / "deer.svg"
    if not svg_path.exists():
        raise FileNotFoundError(f"deer.svg not found at {svg_path}")
    return _render_svg_to_rgba(svg_path, 128, 128)


@register_input_generator("astronaut_128")
def gen_astronaut_128() -> np.ndarray:
    """Skimage astronaut resized to 128x128.

    This is a photographic test image with full color range
    and no transparency.
    """
    from PIL import Image
    from skimage import data

    astronaut = data.astronaut()
    pil_img = Image.fromarray(astronaut, mode='RGB').convert('RGBA')
    pil_img = pil_img.resize((128, 128), Image.Resampling.LANCZOS)
    return np.array(pil_img, dtype=np.uint8)


def generate_input(name: str, width: int | None = None, height: int | None = None) -> np.ndarray:
    """Generate test input using a registered generator.

    Args:
        name: Generator name
        width: Optional width override (scales the image)
        height: Optional height override (scales the image)

    Returns:
        RGBA numpy array
    """
    generator = _input_generators.get(name)
    if generator is None:
        raise ValueError(f"Unknown input generator: {name}")

    img = generator()

    # Resize if dimensions specified and different from generated
    if width and height and (img.shape[1] != width or img.shape[0] != height):
        from PIL import Image as PILImage
        pil_img = PILImage.fromarray(img)
        pil_img = pil_img.resize((width, height), PILImage.Resampling.LANCZOS)
        img = np.array(pil_img)

    return img


__all__ = [
    'TestCase',
    'ParityTestSpec',
    'register_input_generator',
    'get_input_generator',
    'register_filter_parity',
    'register_effect_parity',
    'get_filter_tests',
    'get_effect_tests',
    'get_all_tests',
    'export_registry_json',
    'generate_input',
]
