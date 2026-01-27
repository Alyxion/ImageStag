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

### 5. Dual Bit Depth Support

**Every filter MUST have both u8 and f32 implementations:**

| Bit Depth | Range | Use Case |
|-----------|-------|----------|
| **u8 (8-bit)** | 0-255 | Standard web/display |
| **f32 (float)** | 0.0-1.0 | HDR/linear workflows, chained operations |

Both versions use identical algorithms with the same coefficients. The f32 version preserves full precision when filters are chained together.

### 6. Bit Depth Consistency

For each filter, the u8 and f32 versions MUST produce equivalent results:
- Processing u8 directly should match processing u8→f32→filter→f32→u8
- Maximum difference: 1 level (due to rounding in conversions)

### 7. 12-bit Storage for Float Precision

When storing float outputs for comparison:
- Convert f32 (0.0-1.0) to u16 12-bit (0-4095)
- 12-bit provides ~4x more precision than 8-bit
- Roundtrip error < 1/4095 ≈ 0.000244

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                      Rust Implementation                             │
│                    (rust/src/filters/*.rs)                           │
│                                                                      │
│  ┌─────────────────────────────┐   ┌─────────────────────────────┐  │
│  │  grayscale_rgba_u8()        │   │  grayscale_rgba_f32()       │  │
│  │  Input: u8 (0-255)          │   │  Input: f32 (0.0-1.0)       │  │
│  │  Output: u8 (0-255)         │   │  Output: f32 (0.0-1.0)      │  │
│  └─────────────────────────────┘   └─────────────────────────────┘  │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  Conversion Utilities                                        │    │
│  │  u8_to_f32() | f32_to_u8() | f32_to_u16_12bit() | u16_to_f32│    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────┬─────────────────────────┬─────────────────────────┘
                  │                         │
        ┌─────────┴─────────┐     ┌─────────┴─────────┐
        │  PyO3 + maturin   │     │  wasm-bindgen     │
        │  (--features py)  │     │  (--features wasm)│
        └─────────┬─────────┘     └─────────┬─────────┘
                  │                         │
        ┌─────────┴─────────┐     ┌─────────┴─────────┐
        │  Python Extension │     │  WASM Module      │
        │  imagestag_rust.so│     │  imagestag_rust.js│
        │                   │     │                   │
        │  grayscale_rgba() │     │  grayscale_wasm() │
        │  grayscale_f32()  │     │  grayscale_f32()  │
        └───────────────────┘     └───────────────────┘
```

## When to Use u8 vs f32

| Scenario | Recommended | Why |
|----------|-------------|-----|
| Single filter application | u8 | Simpler, faster, sufficient precision |
| Chained filters (blur → grayscale → etc.) | f32 | Prevents precision loss accumulation |
| HDR/linear color workflows | f32 | Requires values > 1.0 or < 0.0 |
| Final output for display | u8 | Standard web/display format |
| Intermediate processing | f32 | Maximum precision |

**Float workflow example:**
```python
from imagestag.filters.grayscale import (
    convert_u8_to_f32, convert_f32_to_u8,
    grayscale_f32
)

# Load u8 image
img_u8 = load_image("photo.png")

# Convert to float for processing
img_f32 = convert_u8_to_f32(img_u8)

# Chain multiple filters (precision preserved)
result_f32 = grayscale_f32(img_f32)
result_f32 = other_filter_f32(result_f32)  # No precision loss

# Convert back to u8 for display/storage
result_u8 = convert_f32_to_u8(result_f32)
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
# Build WASM (architecture-independent, works on ARM64 and AMD64)
wasm-pack build rust/ --target web \
  --out-dir ../imagestag/wasm \
  --features wasm --no-default-features
```

### Build Python Extension

```bash
# Build Python extension (uses maturin via poetry)
poetry run maturin develop --release
```

## Quick Start

### Running All Parity Tests (Recommended)

The easiest way to run all parity tests is with the unified runner script:

```bash
# Run all Python and JavaScript parity tests, then compare
poetry run python scripts/run_all_parity_tests.py
```

This script:
1. Clears existing test outputs
2. Saves ground truth inputs for JS to use
3. Runs all Python filter tests (ImageStag + OpenCV/scikit-image references)
4. Runs all Python layer effect tests
5. Runs all JavaScript filter tests via Node.js
6. Runs all JavaScript layer effect tests via Node.js
7. Generates comparison images for any failures
8. Prints a summary report

**Optional flags:**

| Flag | Description |
|------|-------------|
| `--no-python` | Skip Python tests (use existing Python outputs) |
| `--no-js` | Skip JavaScript tests (use existing JS outputs) |
| `--no-compare` | Skip generating comparison images |

```bash
# Examples
poetry run python scripts/run_all_parity_tests.py --no-python   # Only run JS tests
poetry run python scripts/run_all_parity_tests.py --no-js      # Only run Python tests
poetry run python scripts/run_all_parity_tests.py --no-compare # Skip comparisons
```

### Running Tests Individually

You can also run tests separately:

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
├── inputs/                              # Ground truth images (raw RGBA)
│   ├── deer_128.rgba
│   └── astronaut_128.rgba
├── filters/                             # Filter test outputs
│   ├── grayscale_deer_128_imagestag_u8.avif  # Python/Rust output (u8)
│   ├── grayscale_deer_128_js_u8.avif         # JavaScript/WASM output (u8)
│   ├── grayscale_deer_128_imagestag_f32.avif # Python/Rust output (f32)
│   ├── grayscale_deer_128_js_f32.avif        # JavaScript/WASM output (f32)
│   ├── grayscale_deer_128_opencv.png         # OpenCV reference (u8 only)
│   ├── grayscale_deer_128_skimage.png        # scikit-image reference (u8 only)
│   └── ...
├── layer_effects/                       # Layer effect test outputs
│   ├── drop_shadow_deer_128_imagestag_u8.avif
│   ├── drop_shadow_deer_128_js_u8.avif
│   └── ...
└── comparisons/                         # Side-by-side comparison images
    ├── grayscale_deer_128_u8_comparison.png  # Only generated on failures
    └── ...
```

**File naming convention:**
- `{filter}_{input}_{platform}_{bitdepth}.avif` - Test outputs
- `{filter}_{input}_{library}.png` - Reference outputs (OpenCV/scikit-image)
- `{filter}_{input}_{bitdepth}_comparison.png` - Side-by-side comparisons

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

**Remember:**
- All per-pixel operations MUST be in Rust (no JavaScript fallbacks)
- Every filter MUST have both u8 AND f32 implementations
- Use identical algorithms for both bit depths

### Step 1: Implement in Rust (both u8 and f32)

Create the core implementations in `rust/src/filters/`:

```rust
// rust/src/filters/my_filter.rs

use ndarray::{Array3, ArrayView3};

// ============================================================================
// 8-bit (u8) Implementation
// ============================================================================

/// Core u8 implementation - shared by Python and WASM.
pub fn my_filter_rgba_u8(input: ArrayView3<u8>) -> Array3<u8> {
    let (height, width, _) = input.dim();
    let mut output = Array3::<u8>::zeros((height, width, 4));

    for y in 0..height {
        for x in 0..width {
            let r = input[[y, x, 0]] as f32;
            let g = input[[y, x, 1]] as f32;
            let b = input[[y, x, 2]] as f32;
            let a = input[[y, x, 3]];

            // Your filter logic here (use f32 for calculations)
            let result = /* calculation */;

            output[[y, x, 0]] = result as u8;
            output[[y, x, 1]] = result as u8;
            output[[y, x, 2]] = result as u8;
            output[[y, x, 3]] = a;
        }
    }

    output
}

// ============================================================================
// Float (f32) Implementation
// ============================================================================

/// Core f32 implementation - identical algorithm, float precision.
pub fn my_filter_rgba_f32(input: ArrayView3<f32>) -> Array3<f32> {
    let (height, width, _) = input.dim();
    let mut output = Array3::<f32>::zeros((height, width, 4));

    for y in 0..height {
        for x in 0..width {
            let r = input[[y, x, 0]];
            let g = input[[y, x, 1]];
            let b = input[[y, x, 2]];
            let a = input[[y, x, 3]];

            // Same filter logic (already in f32)
            let result = /* same calculation */;

            output[[y, x, 0]] = result;
            output[[y, x, 1]] = result;
            output[[y, x, 2]] = result;
            output[[y, x, 3]] = a;
        }
    }

    output
}
```

### Step 2: Add WASM Exports (u8 and f32)

Add to `rust/src/wasm.rs`:

```rust
use crate::filters::my_filter::{my_filter_rgba_u8, my_filter_rgba_f32};

// u8 version
#[wasm_bindgen]
pub fn my_filter_rgba_wasm(data: &[u8], width: usize, height: usize) -> Vec<u8> {
    let input = Array3::from_shape_vec((height, width, 4), data.to_vec())
        .expect("Invalid dimensions");
    my_filter_rgba_u8(input.view()).into_raw_vec_and_offset().0
}

// f32 version
#[wasm_bindgen]
pub fn my_filter_rgba_f32_wasm(data: &[f32], width: usize, height: usize) -> Vec<f32> {
    let input = Array3::from_shape_vec((height, width, 4), data.to_vec())
        .expect("Invalid dimensions");
    my_filter_rgba_f32(input.view()).into_raw_vec_and_offset().0
}
```

### Step 3: Add Python Exports (u8 and f32)

Add to `rust/src/lib.rs` (inside the `#[cfg(feature = "python")]` block):

```rust
use crate::filters::my_filter::{my_filter_rgba_u8, my_filter_rgba_f32};

// u8 version
#[pyfunction]
pub fn my_filter_rgba<'py>(
    py: Python<'py>,
    image: PyReadonlyArray3<'py, u8>,
) -> Bound<'py, PyArray3<u8>> {
    let input = image.as_array();
    my_filter_rgba_u8(input).into_pyarray(py)
}

// f32 version
#[pyfunction]
pub fn my_filter_rgba_f32<'py>(
    py: Python<'py>,
    image: PyReadonlyArray3<'py, f32>,
) -> Bound<'py, PyArray3<f32>> {
    let input = image.as_array();
    my_filter_rgba_f32(input).into_pyarray(py)
}

// Don't forget to add both to the module:
// m.add_function(wrap_pyfunction!(my_filter_rgba, m)?)?;
// m.add_function(wrap_pyfunction!(my_filter_rgba_f32, m)?)?;
```

### Step 4: Rebuild Both Targets

```bash
# Rebuild WASM (architecture-independent bytecode)
wasm-pack build rust/ --target web \
  --out-dir ../imagestag/wasm \
  --features wasm --no-default-features

# Rebuild Python extension (platform-specific)
poetry run maturin develop --release
```

### Step 5: Create JavaScript Wrapper (u8 and f32)

```javascript
// imagestag/filters/js/my_filter.js
import {
    my_filter_rgba_wasm,
    my_filter_rgba_f32_wasm,
    convert_u8_to_f32_wasm,
    convert_f32_to_u8_wasm,
} from './wasm/imagestag_rust.js';

// u8 version
export function myFilter(imageData) {
    const { data, width, height } = imageData;
    const result = my_filter_rgba_wasm(new Uint8Array(data.buffer), width, height);
    return {
        data: new Uint8ClampedArray(result.buffer),
        width,
        height
    };
}

// f32 version
export function myFilterF32(imageData) {
    const { data, width, height } = imageData;
    const result = my_filter_rgba_f32_wasm(new Float32Array(data.buffer), width, height);
    return {
        data: new Float32Array(result.buffer),
        width,
        height
    };
}

// Conversion utilities (re-export from grayscale.js or create common utils)
export { convertU8ToF32, convertF32ToU8 } from './grayscale.js';
```

### Step 6: Register Parity Tests (Python) - Both u8 and f32

```python
# imagestag/parity/tests/my_filter.py
from ..registry import register_filter_parity, TestCase
from ..runner import register_filter_impl

def register_my_filter_parity():
    # u8 tests
    register_filter_parity("my_filter", [
        TestCase(id="deer_128", description="Deer emoji test",
                 width=128, height=128, input_generator="deer_128", bit_depth="u8"),
        TestCase(id="astronaut_128", description="Astronaut test",
                 width=128, height=128, input_generator="astronaut_128", bit_depth="u8"),
    ])

    # f32 tests
    register_filter_parity("my_filter_f32", [
        TestCase(id="deer_128_f32", description="Deer emoji - float",
                 width=128, height=128, input_generator="deer_128", bit_depth="f32"),
        TestCase(id="astronaut_128_f32", description="Astronaut - float",
                 width=128, height=128, input_generator="astronaut_128", bit_depth="f32"),
    ])

    from imagestag.filters.my_filter import (
        my_filter, my_filter_f32,
        convert_u8_to_f32, convert_f32_to_u8,
    )

    # u8 implementation
    register_filter_impl("my_filter", my_filter)

    # f32 implementation (converts u8 input -> f32 -> process -> u8 output)
    def my_filter_f32_pipeline(image):
        img_f32 = convert_u8_to_f32(image)
        result_f32 = my_filter_f32(img_f32)
        return convert_f32_to_u8(result_f32)

    register_filter_impl("my_filter_f32", my_filter_f32_pipeline)
```

### Step 7: Register Parity Tests (JavaScript) - Both u8 and f32

```javascript
// imagestag/parity/js/tests/my_filter.js
import {
    myFilter,
    myFilterF32,
    convertU8ToF32,
    convertF32ToU8,
} from '../../../filters/js/my_filter.js';

// u8 test cases
export const MY_FILTER_TEST_CASES = [
    { id: 'deer_128', description: 'Deer emoji test',
      width: 128, height: 128, inputGenerator: 'deer_128', bitDepth: 'u8' },
    { id: 'astronaut_128', description: 'Astronaut test',
      width: 128, height: 128, inputGenerator: 'astronaut_128', bitDepth: 'u8' },
];

// f32 test cases
export const MY_FILTER_F32_TEST_CASES = [
    { id: 'deer_128_f32', description: 'Deer - float',
      width: 128, height: 128, inputGenerator: 'deer_128', bitDepth: 'f32' },
    { id: 'astronaut_128_f32', description: 'Astronaut - float',
      width: 128, height: 128, inputGenerator: 'astronaut_128', bitDepth: 'f32' },
];

// u8 filter (Rust/WASM - NO fallback)
export function myFilterFunction(imageData) {
    return myFilter(imageData);
}

// f32 filter (converts u8 -> f32 -> process -> u8)
export function myFilterF32Function(imageData) {
    const inputF32 = convertU8ToF32(imageData);
    const resultF32 = myFilterF32(inputF32);
    return convertF32ToU8(resultF32);
}

export function registerMyFilterParity(runner) {
    // u8 tests
    runner.registerFilter('my_filter', myFilterFunction);
    runner.registerFilterTests('my_filter', MY_FILTER_TEST_CASES);

    // f32 tests
    runner.registerFilter('my_filter_f32', myFilterF32Function);
    runner.registerFilterTests('my_filter_f32', MY_FILTER_F32_TEST_CASES);
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
2. **Implement BOTH u8 AND f32 versions** - Every filter needs both
3. **Use identical algorithms** - Same coefficients and logic for u8 and f32
4. **Expect exact pixel match** - Any difference indicates a bug (different code paths)
5. **Test u8 vs f32 consistency** - Results should differ by at most 1 level
6. **Use ground truth images** (deer_128, astronaut_128) for consistent inputs
7. **Run Python tests first** to generate ground truth inputs
8. **Rebuild WASM after Rust changes** - `wasm-pack build rust/ --target web ...`
9. **Save comparison images** to debug failures visually
10. **Use f32 for chained operations** - Prevents precision loss accumulation

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
