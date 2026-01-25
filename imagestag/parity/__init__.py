"""Cross-platform parity testing framework for ImageStag filters and effects.

This module provides infrastructure for testing that Python (Rust) and JavaScript
(WASM) implementations of filters and layer effects produce identical output.

## Architecture

Both Python and JavaScript tests write their outputs to a shared temp directory
using a consistent naming convention:

    {temp}/imagestag_parity/{category}/{name}_{test_case}_{platform}.avif

Where:
- category: "filters" or "layer_effects"
- name: filter/effect name (e.g., "grayscale", "drop_shadow")
- test_case: test case identifier (e.g., "red_image", "astronaut")
- platform: "python" or "js"

## Usage

### Registering Parity Tests (Python)

```python
from imagestag.parity import register_filter_parity, TestCase

register_filter_parity("grayscale", [
    TestCase(
        id="red_image",
        description="Pure red becomes gray",
        width=100,
        height=100,
        input_generator="solid_red",
    ),
    TestCase(
        id="gradient",
        description="RGB gradient",
        width=100,
        height=100,
        input_generator="gradient_rgb",
    ),
])
```

### Running Tests

```python
from imagestag.parity import run_python_tests, compare_all_outputs

# Run Python-side tests (saves outputs)
run_python_tests("filters", "grayscale")

# Compare Python vs JS outputs (after JS tests have run)
results = compare_all_outputs("filters", "grayscale")
for result in results:
    print(result.message)
```

### JavaScript Tests

```javascript
import { runParityTests } from '/imgstag/static/parity/js/runner.js';

// Run JS-side tests (saves outputs)
await runParityTests('filters', 'grayscale');
```

## Test Directory

Default: `/tmp/imagestag_parity/`

Can be overridden with IMAGESTAG_PARITY_DIR environment variable.
"""

from .config import (
    PARITY_TEST_DIR,
    OUTPUT_FORMAT,
    Platform,
    get_test_dir,
    get_output_path,
    get_comparison_path,
    clear_test_dir,
    list_test_artifacts,
    get_config_json,
    get_inputs_dir,
    save_ground_truth_input,
    save_all_ground_truth_inputs,
)

from .comparison import (
    ComparisonResult,
    load_test_image,
    save_test_image,
    compute_pixel_diff,
    compare_outputs,
    save_comparison_image,
    images_match,
)

from .registry import (
    TestCase,
    ParityTestSpec,
    register_input_generator,
    get_input_generator,
    register_filter_parity,
    register_effect_parity,
    get_filter_tests,
    get_effect_tests,
    get_all_tests,
    export_registry_json,
    generate_input,
)

from .runner import (
    run_filter_test,
    run_effect_test,
    run_all_filter_tests,
    run_all_effect_tests,
    compare_filter_outputs,
    compare_effect_outputs,
    ParityTestRunner,
)

__all__ = [
    # Config
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
    # Comparison
    'ComparisonResult',
    'load_test_image',
    'save_test_image',
    'compute_pixel_diff',
    'compare_outputs',
    'save_comparison_image',
    'images_match',
    # Registry
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
    # Runner
    'run_filter_test',
    'run_effect_test',
    'run_all_filter_tests',
    'run_all_effect_tests',
    'compare_filter_outputs',
    'compare_effect_outputs',
    'ParityTestRunner',
]
