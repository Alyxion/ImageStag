# Task: Optimize Selection Grow/Shrink Performance

## Status: COMPLETED

Selection grow/shrink operations are now optimized using a separable algorithm.

### Benchmark Results (1920x1080)

| Operation | Radius | Before | After | Speedup |
|-----------|--------|--------|-------|---------|
| Grow | 2px | 40ms | 3ms | ~13x |
| Grow | 5px | 175ms | 5ms | ~35x |
| Grow | 10px | 700ms | 5ms | **~140x** |
| Shrink | 10px | 706ms | 3ms | **~235x** |

**Target**: All operations complete in <100ms for interactive use. **ACHIEVED** (<10ms)

## Root Cause (Fixed)

The old implementation in `imagestag/filters/morphology.rs` used a brute-force O(n × r²) algorithm:

```rust
for y in 0..height {
    for x in 0..width {
        for dy in -r_ceil..=r_ceil {
            for dx in -r_ceil..=r_ceil {
                // Check if within circular radius
                // Take max (dilate) or min (erode)
            }
        }
    }
}
```

For 1920×1080 with radius 10:
- Pixels: 2,073,600
- Checks per pixel: ~314 (π × 10²)
- Total operations: ~651 million

## Optimization Strategies

### 1. Separable Approximation (Recommended)

Replace circular structuring element with separable (horizontal + vertical) passes:

```rust
// Pass 1: Horizontal dilation
for y in 0..height {
    for x in 0..width {
        // Only check x-radius neighbors
    }
}

// Pass 2: Vertical dilation on result
for y in 0..height {
    for x in 0..width {
        // Only check y-radius neighbors
    }
}
```

**Complexity**: O(n × 2r) instead of O(n × r²)
**Expected speedup**: ~10-15x for r=10

**Trade-off**: Result is diamond-shaped instead of circular. For selection masks (binary), this is usually acceptable.

### 2. van Herk/Gil-Werman Algorithm

O(n) algorithm regardless of radius using running min/max with a deque:

```rust
// For each row:
// 1. Forward pass: compute max in windows
// 2. Backward pass: combine results
```

**Complexity**: O(n) - constant time regardless of radius
**Expected speedup**: ~50x for r=10

**References**:
- van Herk (1992): "A Fast Algorithm for Local Minimum and Maximum Filters"
- Gil & Werman (1993): "Computing 2-D Min, Median, and Max Filters"

### 3. Parallel Processing with Rayon

Add parallelization using rayon:

```rust
use rayon::prelude::*;

// Process rows in parallel
(0..height).into_par_iter().for_each(|y| {
    // Process row
});
```

**Expected speedup**: 4-8x on multi-core CPUs

### 4. SIMD Optimization

Use SIMD for the inner loop comparisons:

```rust
use std::simd::*;

// Process 8 or 16 pixels at once
let chunk = u8x16::from_slice(&input[...]);
let max = existing_max.simd_max(chunk);
```

**Expected speedup**: 4-16x depending on operation

## Implemented Optimizations

### 1. Separable Algorithm (DONE)
- Replaced O(n × r²) circular kernel with O(n × 2r) separable passes
- Pass 1: Horizontal max/min across row
- Pass 2: Vertical max/min on intermediate result
- Produces diamond-shaped structuring element (acceptable for selection masks)
- **This is the main optimization providing 100-200x speedup**

### 2. Rayon Parallelization (DONE)
- Added `par_chunks_mut` to process rows in parallel
- Works in Python (PyO3), but WASM remains single-threaded
- Provides additional speedup on multi-core CPUs

## Future Optimizations (Optional)

1. **van Herk/Gil-Werman for very large radii** - O(n) regardless of radius
   - Only beneficial for r > 50, current performance is sufficient

## Files Modified

- `imagestag/filters/morphology.rs` - Core implementation (separable algorithm)
- `rust/src/filters/morphology.rs` - Duplicate file, also updated for consistency

## Testing

Run benchmark after changes:

```bash
poetry run python tests/stagforge/test_selection_performance.py
```

## Contour Extraction Performance

Contour extraction is already fast enough:
- 1920x1080 checkerboard (worst case): 19ms
- No optimization needed currently

## Priority

**High** - Slow grow/shrink degrades user experience significantly when working with high-resolution images.
