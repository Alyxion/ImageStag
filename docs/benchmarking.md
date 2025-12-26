# Benchmarking

ImageStag provides utilities for measuring filter and pipeline performance.

## Quick Start

```python
from imagestag.filters import Benchmark, Resize, FalseColor, FilterPipeline
from imagestag.samples import group

image = group()

# Benchmark single filter
result = Benchmark.run_filter(Resize(scale=0.5), image, num_frames=30)
result.print()

# Benchmark pipeline
pipeline = FilterPipeline([
    Resize(size=(1920, 1080)),
    FalseColor(colormap='hot'),
])
result = Benchmark.run_pipeline(pipeline, image, num_frames=30, target_fps=60)
result.print()
```

## Benchmark.run_filter()

Benchmark a single filter:

```python
result = Benchmark.run_filter(
    filter=Resize(scale=0.5),
    source=image,
    num_frames=30,           # Frames to process
    target_fps=60,           # Optional pass/fail threshold
    config=None              # Optional BenchmarkConfig
)
```

## Benchmark.run_pipeline()

Benchmark a filter pipeline:

```python
result = Benchmark.run_pipeline(
    pipeline=FilterPipeline([Resize(scale=0.5), FalseColor('hot')]),
    source=image,
    num_frames=30,
    target_fps=60,
    config=None
)
```

Accepts `FilterPipeline` or `list[Filter]`.

## Benchmark.compare_filters()

Compare multiple filters side by side:

```python
filters = [
    Resize(scale=0.5),
    Resize(scale=0.25),
    FalseColor(colormap='viridis'),
    GaussianBlur(radius=3),
]

table = Benchmark.compare_filters(filters, image, num_frames=10)
print(table)
```

Output:
```
==================================================
FILTER COMPARISON
==================================================
Source: 2739x1825
Frames: 10

--------------------------------------------------
Filter                           FPS    Per-frame
--------------------------------------------------
Resize                         512.4        2.0ms
Resize                         319.5        3.1ms
GaussianBlur                   185.2        5.4ms
FalseColor                      49.6       20.2ms
--------------------------------------------------
```

## BenchmarkConfig

Fine-grained control over benchmark execution:

```python
from imagestag.filters import BenchmarkConfig

config = BenchmarkConfig(
    num_frames=100,           # Frames to process
    target_fps=60,            # Target for pass/fail
    warmup_frames=5,          # Warmup runs before timing
    run_sequential=True,      # Run sequential test
    run_data_parallel=True,   # Run BatchPipelineExecutor
    run_stage_parallel=True,  # Run StreamingPipelineExecutor
    num_workers=None,         # Auto-detect CPU count
)

result = Benchmark.run_pipeline(pipeline, image, config=config)
```

## BenchmarkResult

Results are serializable dataclasses:

```python
result = Benchmark.run_pipeline(pipeline, image)

# Properties
result.name              # Benchmark name
result.source_size       # (width, height)
result.source_megapixels # MP count
result.output_size       # Output dimensions
result.num_frames        # Frames processed
result.num_cpus          # CPU count
result.target_fps        # Target FPS (if set)
result.passed            # True/False/None
result.best_executor     # 'sequential', 'data_parallel', 'stage_parallel'
result.best_fps          # Best FPS achieved
result.results           # List[ExecutorResult]
result.pipeline_stages   # Stage names (for pipelines)
result.filter_name       # Filter name (for single filters)

# Output methods
result.print()           # Print ASCII table
table = result.ascii_table()  # Get table string

# Serialization
json_str = result.to_json()
d = result.to_dict()
restored = BenchmarkResult.from_dict(d)
```

## ExecutorResult

Per-executor timing data:

```python
for r in result.results:
    print(f"{r.executor}: {r.fps:.1f} FPS, {r.per_frame_ms:.1f}ms/frame")

    # Stage breakdown (stage_parallel only)
    for stage in r.stages:
        print(f"  {stage.name}: {stage.avg_ms:.1f}ms avg")
```

## ASCII Output Example

```
============================================================
BENCHMARK: Pipeline: Resize -> FalseColor -> Encode -> ToDataUrl
============================================================

Source: 5478x3650 (19.99 MP)
Output: 1920x1080
Frames: 30
CPUs: 14

Pipeline: Resize -> FalseColor -> Encode -> ToDataUrl

------------------------------------------------------------
Executor                   Time        FPS    Per-frame
------------------------------------------------------------
sequential               0.564s       53.2       18.8ms
data_parallel            0.251s      119.5        8.4ms
stage_parallel           0.353s       85.0       11.8ms
------------------------------------------------------------

Stage breakdown (stage_parallel):
  0_Resize: 8.8ms avg
  1_FalseColor: 9.3ms avg
  2_Encode: 5.8ms avg
  3_ToDataUrl: 0.4ms avg

============================================================
Target: 60 FPS | Best: 119.5 FPS | PASSED
============================================================
```

## JSON Serialization

```python
# Save results
with open("benchmark_results.json", "w") as f:
    f.write(result.to_json())

# Load results
import json
with open("benchmark_results.json") as f:
    data = json.load(f)
    restored = BenchmarkResult.from_dict(data)
```

## Sample Benchmark Script

```python
#!/usr/bin/env python
"""Run standard benchmarks."""

from imagestag import Image
from imagestag.samples import group
from imagestag.pixel_format import PixelFormat
from imagestag.definitions import ImsFramework
from imagestag.filters import (
    Benchmark, FilterPipeline,
    Resize, FalseColor, Encode, ToDataUrl
)

# Prepare high-res source (20 MP)
img = group()
scale = (20.0 / (img.width * img.height / 1e6)) ** 0.5
upscaled = img.resized(scale=scale)

# Convert to CV for optimal performance
pixels = upscaled.get_pixels(PixelFormat.BGR)
source = Image(pixels, pixel_format=PixelFormat.BGR, framework=ImsFramework.CV)

# Build pipeline
pipeline = FilterPipeline([
    Resize(size=(1920, 1080)),
    FalseColor(colormap='hot'),
    Encode(format='jpeg', quality=80),
    ToDataUrl(),
])

# Run benchmark
result = Benchmark.run_pipeline(
    pipeline,
    source,
    num_frames=30,
    target_fps=60
)

result.print()
print(f"\nJSON:\n{result.to_json()}")
```
