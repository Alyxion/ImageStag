# Cross-Platform Parity Testing

ImageStag provides a framework for testing that Python and JavaScript implementations of filters and layer effects produce **identical** outputs.

## Core Principles

### 1. Single Rust Implementation - No Fallbacks

**All per-pixel operations MUST be implemented in Rust only.** There is NO JavaScript fallback code. This ensures:

- Identical algorithms on both platforms
- No subtle differences from reimplementation
- Single source of truth for image processing logic

### 2. Rust Compiles to Both Targets

The same Rust code compiles to:
- **Python**: Native extension via PyO3/maturin (`.so`/`.pyd`)
- **JavaScript**: WASM module via wasm-pack (`.wasm`)

### 3. Exact Pixel-Level Parity

Because both platforms execute identical compiled Rust code, outputs are **exactly identical** - not "close enough" or "within tolerance", but byte-for-byte identical.

### 4. Lossless Storage

Test outputs use lossless AVIF compression to ensure comparison isn't affected by encoding artifacts:
- **Python**: pillow-heif with `matrix_coefficients=0` (RGB, no YCbCr)
- **JavaScript**: sharp with `lossless: true`, `chromaSubsampling: '4:4:4'`

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Rust Implementation                       │
│                  (rust/src/filters/*.rs)                     │
│                                                              │
│  grayscale_rgba_impl() - Single source of truth             │
└─────────────────┬─────────────────────────┬─────────────────┘
                  │                         │
        ┌─────────┴─────────┐     ┌─────────┴─────────┐
        │  PyO3 + maturin   │     │  wasm-bindgen     │
        │  (--features py)  │     │  (--features wasm)│
        └─────────┬─────────┘     └─────────┬─────────┘
                  │                         │
        ┌─────────┴─────────┐     ┌─────────┴─────────┐
        │  Python Extension │     │  WASM Module      │
        │  imagestag_rust.so│     │  imagestag_rust.js│
        └───────────────────┘     └───────────────────┘
```

## Overview

The parity testing framework enables:

1. **Exact pixel match** - Both platforms use identical Rust code
2. **Shared ground truth images** served via API for consistent inputs
3. **Scalable test registration** for filters and layer effects
4. **Visual diff reports** for debugging failures

**Output Format:** Both Python and JavaScript save outputs as lossless AVIF:
- **Python**: Uses pillow-heif with `matrix_coefficients=0` (RGB, no YCbCr)
- **JavaScript**: Uses sharp with `lossless: true` and `chromaSubsampling: '4:4:4'`

## Ground Truth Images

Parity tests use two ground truth images to ensure Python and JavaScript use identical inputs:

| Input | Description | Size |
|-------|-------------|------|
| `deer_128` | Noto emoji deer (vector with transparency) | 128×128 |
| `astronaut_128` | Skimage astronaut (photographic) | 128×128 |

These images are:
- Rendered by Python and saved as `.rgba` files
- Served via API at `/imgstag/parity/inputs/{name}.rgba`
- Read by JavaScript from the saved files or fetched from API

## Architecture

```
                    ┌─────────────────────────────────────────┐
                    │     Project tmp/parity/ Directory       │
                    │                                         │
                    │  inputs/                                │
                    │    deer_128.rgba      (ground truth)    │
                    │    astronaut_128.rgba (ground truth)    │
                    │                                         │
                    │  filters/                               │
                    │    grayscale_deer_128_python.avif       │
                    │    grayscale_deer_128_js.avif           │
                    │    grayscale_deer_128_comparison.png    │
                    │                                         │
                    │  layer_effects/                         │
                    │    drop_shadow_deer_128_python.avif     │
                    │    drop_shadow_deer_128_js.avif         │
                    └─────────────────────────────────────────┘
                              ▲                    ▲
                              │                    │
              ┌───────────────┴──┐           ┌────┴───────────────┐
              │  Python Tests    │           │  JavaScript Tests  │
              │                  │           │                    │
              │  - Rust backend  │           │  - WASM/JS backend │
              │  - Save AVIF     │           │  - Save AVIF       │
              │  - Compare both  │           │  - Read inputs     │
              │  - pillow-heif   │           │  - sharp library   │
              └──────────────────┘           └────────────────────┘
```

## Building

### Prerequisites

```bash
# Install wasm-pack (one-time)
curl https://rustwasm.github.io/wasm-pack/installer/init.sh -sSf | sh

# Install Node.js dependencies
npm install
```

### Build WASM Module

```bash
# Build WASM for Node.js
wasm-pack build rust/ --target nodejs \
  --out-dir /projects/ImageStag/imagestag/filters/js/wasm \
  --features wasm --no-default-features
```

### Build Python Extension

```bash
# Build Python extension (uses maturin via poetry)
poetry run maturin develop --release
```

## Quick Start

### Running Parity Tests

```bash
# 1. Run Python tests (generates inputs and outputs)
poetry run pytest tests/test_filter_parity.py -v

# 2. Run JavaScript tests (reads inputs, generates outputs)
node imagestag/parity/js/run_tests.js

# 3. Run Python tests again to compare (verifies exact match)
poetry run pytest tests/test_filter_parity.py -v
```

### Test Artifacts

Outputs are saved to `tmp/parity/` in the project root:

```
ImageStag/tmp/parity/
├── inputs/                          # Ground truth images (raw RGBA)
│   ├── deer_128.rgba
│   └── astronaut_128.rgba
├── filters/
│   ├── grayscale_deer_128_python.avif   # Lossless AVIF (pillow-heif)
│   ├── grayscale_deer_128_js.avif       # Lossless AVIF (sharp)
│   ├── grayscale_deer_128_comparison.png  # Created on failure
│   └── ...
└── layer_effects/
    └── ...
```

**Note:** The `tmp/` directory is cleaned at the start of each Python test run and is excluded from git.

## API Endpoints

The ImageStag API provides endpoints for serving ground truth images:

### SVG to WebP Rendering

```
GET /imgstag/samples/svgs/{category}/{name}.webp?size=128&quality=90
```

Example:
```bash
curl "http://localhost:8080/imgstag/samples/svgs/noto-emoji/deer.webp?size=128" -o deer.webp
```

### Skimage to WebP

```
GET /imgstag/samples/skimage/{name}.webp?size=128&quality=90
```

Example:
```bash
curl "http://localhost:8080/imgstag/samples/skimage/astronaut.webp?size=128" -o astronaut.webp
```

### Raw Parity Inputs

```
GET /imgstag/parity/inputs/{input_id}.rgba
```

Returns raw RGBA bytes with 8-byte header (width u32le, height u32le).

Available inputs: `deer_128`, `astronaut_128`

## Adding a New Filter

**Remember: All per-pixel operations MUST be in Rust. No JavaScript implementations.**

### Step 1: Implement in Rust

Create the core implementation in `rust/src/filters/`:

```rust
// rust/src/filters/my_filter.rs

use ndarray::{Array3, ArrayView3};

/// Core implementation - shared by Python and WASM.
pub fn my_filter_rgba_impl(input: ArrayView3<u8>) -> Array3<u8> {
    let (height, width, _) = input.dim();
    let mut output = Array3::<u8>::zeros((height, width, 4));

    for y in 0..height {
        for x in 0..width {
            // Your filter logic here
            // ...
        }
    }

    output
}
```

### Step 2: Add WASM Export

Add to `rust/src/wasm.rs`:

```rust
#[wasm_bindgen]
pub fn my_filter_rgba_wasm(data: &[u8], width: usize, height: usize) -> Vec<u8> {
    let input = Array3::from_shape_vec((height, width, 4), data.to_vec())
        .expect("Invalid dimensions");
    my_filter_rgba_impl(input.view()).into_raw_vec()
}
```

### Step 3: Add Python Export

Add to `rust/src/lib.rs` (inside the `#[cfg(feature = "python")]` block):

```rust
#[pyfunction]
pub fn my_filter_rgba<'py>(
    py: Python<'py>,
    image: PyReadonlyArray3<'py, u8>,
) -> Bound<'py, PyArray3<u8>> {
    let input = image.as_array();
    my_filter_rgba_impl(input).into_pyarray(py)
}
```

### Step 4: Rebuild Both Targets

```bash
# Rebuild WASM
wasm-pack build rust/ --target nodejs \
  --out-dir $(pwd)/imagestag/filters/js/wasm \
  --features wasm --no-default-features

# Rebuild Python extension
poetry run maturin develop --release
```

### Step 5: Create JavaScript Wrapper

```javascript
// imagestag/filters/js/my_filter.js
import { my_filter_rgba_wasm } from './wasm/imagestag_rust.js';

export function myFilter(imageData) {
    const { data, width, height } = imageData;
    const result = my_filter_rgba_wasm(new Uint8Array(data.buffer), width, height);
    return {
        data: new Uint8ClampedArray(result.buffer),
        width,
        height
    };
}
```

### Step 6: Register Parity Tests (Python)

```python
# imagestag/parity/tests/my_filter.py
from ..registry import register_filter_parity, TestCase
from ..runner import register_filter_impl

def register_my_filter_parity():
    register_filter_parity("my_filter", [
        TestCase(id="deer_128", description="Deer emoji test",
                 width=128, height=128, input_generator="deer_128"),
        TestCase(id="astronaut_128", description="Astronaut test",
                 width=128, height=128, input_generator="astronaut_128"),
    ])

    from imagestag.filters import my_filter
    register_filter_impl("my_filter", my_filter)
```

### Step 7: Register Parity Tests (JavaScript)

```javascript
// imagestag/parity/js/tests/my_filter.js
import { myFilter } from '../../../filters/js/my_filter.js';

export const MY_FILTER_TEST_CASES = [
    {
        id: 'deer_128',
        description: 'Deer emoji test',
        width: 128,
        height: 128,
        inputGenerator: 'deer_128',
    },
    {
        id: 'astronaut_128',
        description: 'Astronaut test',
        width: 128,
        height: 128,
        inputGenerator: 'astronaut_128',
    },
];

// Uses Rust/WASM - NO fallback
export function myFilterFunction(imageData) {
    return myFilter(imageData);
}

export function registerMyFilterParity(runner) {
    runner.registerFilter('my_filter', myFilterFunction);
    runner.registerFilterTests('my_filter', MY_FILTER_TEST_CASES);
}
```

### Step 8: Register in JS Run Script

```javascript
// imagestag/parity/js/run_tests.js
import { registerMyFilterParity } from './tests/my_filter.js';

// In main():
registerMyFilterParity(runner);
```

## Comparison Settings

### Expected: Exact Match

Because both platforms use identical Rust code, outputs should be **exactly identical**. The tolerance setting exists only for edge cases (e.g., different AVIF encoders).

```python
from imagestag.parity import compare_filter_outputs

# Default: 0.1% tolerance (should be 0% with proper Rust implementation)
results = compare_filter_outputs("grayscale", tolerance=0.001)

# Strict: Require exact match
results = compare_filter_outputs("grayscale", tolerance=0.0)
```

### Threshold

Pixel differences below **threshold** (default: 4) are ignored:

```python
from imagestag.parity import compute_pixel_diff

# Any channel diff > 4 counts as different
diff_ratio, mask = compute_pixel_diff(img1, img2, threshold=4)
```

## Debugging Failures

### Comparison Images

When tests fail, comparison images are saved showing:
- Left: Python output
- Middle: JavaScript output
- Right: Diff visualization (red = different pixels)

```bash
# View comparison images
ls tmp/parity/filters/*_comparison.png
```

### Manual Comparison

```python
from imagestag.parity import load_test_image, save_comparison_image

# Load outputs
py_img = load_test_image("filters", "grayscale", "deer_128", "python")
js_img = load_test_image("filters", "grayscale", "deer_128", "js")

# Generate comparison
path = save_comparison_image("filters", "grayscale", "deer_128")
print(f"Comparison saved to: {path}")
```

## Python API Reference

```python
from imagestag.parity import (
    # Configuration
    PARITY_TEST_DIR,
    get_test_dir,
    clear_test_dir,
    get_inputs_dir,
    save_all_ground_truth_inputs,

    # Registry
    register_filter_parity,
    register_effect_parity,
    TestCase,

    # Running tests
    run_all_filter_tests,
    run_all_effect_tests,
    register_filter_impl,
    register_effect_impl,

    # Comparison
    compare_filter_outputs,
    compare_effect_outputs,
    load_test_image,
    save_test_image,
    images_match,
    compute_pixel_diff,

    # High-level runner
    ParityTestRunner,
)
```

## JavaScript API Reference

```javascript
import {
    ParityTestRunner,
    generateInput,
    getOutputPath,
    saveTestOutput,
    loadTestOutput,
    config,
} from './runner.js';
```

## Best Practices

1. **Implement ALL per-pixel operations in Rust** - No JavaScript fallbacks
2. **Expect exact pixel match** - Any difference indicates a bug (different code paths)
3. **Use ground truth images** (deer_128, astronaut_128) for consistent inputs
4. **Run Python tests first** to generate ground truth inputs
5. **Rebuild WASM after Rust changes** - `wasm-pack build rust/ --target nodejs ...`
6. **Save comparison images** to debug failures visually

## Layer Effects

Layer effects follow the same pattern but use different registry functions:

```python
# Python
from imagestag.parity import register_effect_parity, register_effect_impl

register_effect_parity("drop_shadow", [
    TestCase(id="deer_128", ...),
])
register_effect_impl("drop_shadow", drop_shadow_func)

# Compare
from imagestag.parity import compare_effect_outputs
results = compare_effect_outputs("drop_shadow")
```

```javascript
// JavaScript
runner.registerEffect('drop_shadow', dropShadowFunc);
runner.registerEffectTests('drop_shadow', DROP_SHADOW_TEST_CASES);
```
