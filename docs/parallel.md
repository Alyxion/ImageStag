# Parallel Execution

ImageStag provides thread-safe executors for high-throughput image processing.

## Execution Models

| Model | Description | Best For |
|-------|-------------|----------|
| **Sequential** | Single-threaded | Debugging, simple tasks |
| **Data-Parallel** | Multiple images across threads | Batch processing |
| **Stage-Parallel** | Pipeline stages in threads | Streaming, real-time |

## BatchPipelineExecutor

Processes multiple images through a pipeline using a thread pool:

```python
from imagestag.filters import FilterPipeline, BatchPipelineExecutor, Resize, FalseColor

pipeline = FilterPipeline([
    Resize(size=(1920, 1080)),
    FalseColor(colormap='hot'),
])

images = [img1, img2, img3, ...]  # List of images

with BatchPipelineExecutor(pipeline, num_workers=8) as executor:
    results = executor.process_all(images)

# Results in same order as input
```

### Parameters

- `pipeline`: FilterPipeline or list of filters
- `num_workers`: Number of threads (default: CPU count)

### Methods

```python
# Process all images, preserving order
results = executor.process_all(images)

# With progress callback
results = executor.process_all(images, show_progress=True)

# Get metrics
metrics = executor.get_metrics()
print(f"FPS: {metrics.fps:.1f}")
```

## StreamingPipelineExecutor

Each pipeline stage runs in its own thread with producer-consumer queues:

```python
from imagestag.filters import StreamingPipelineExecutor

pipeline = FilterPipeline([
    Resize(size=(1920, 1080)),  # Thread 1
    FalseColor(colormap='hot'), # Thread 2
    Encode(format='jpeg'),      # Thread 3
])

with StreamingPipelineExecutor(pipeline) as executor:
    # Submit frames (non-blocking)
    for img in image_source:
        executor.submit(img)

    # Get results as they complete
    for result in executor.results():
        process(result)
```

### Pipeline Flow

```
Frame 1: [Resize] -> [FalseColor] -> [Encode] -> Done
Frame 2:    |          [Resize] -> [FalseColor] -> ...
Frame 3:    |             |          [Resize] -> ...
                    (overlapped execution)
```

### Parameters

- `pipeline`: FilterPipeline or list of filters
- `num_workers`: Workers per stage (default: 1)
- `queue_size`: Max items per queue (default: 32)
- `preserve_order`: Maintain submission order (default: True)

### Methods

```python
# Start workers (auto-called on first submit)
executor.start()

# Submit image (returns sequence number)
seq = executor.submit(image)

# Get single result (blocking)
result = executor.get_result(timeout=5.0)

# Iterate over N results
for result in executor.results(count=100):
    process(result)

# Process batch
results = executor.process_batch(images)

# Get metrics
metrics = executor.get_metrics()
for stage in metrics.stages:
    print(f"{stage.stage_name}: {stage.avg_time_ms:.1f}ms")

# Stop workers
executor.stop()
```

## Performance Comparison

```python
from imagestag.filters import Benchmark

result = Benchmark.run_pipeline(
    pipeline,
    source=image,
    num_frames=30,
    target_fps=60
)
result.print()
```

Output:
```
============================================================
BENCHMARK: Pipeline: Resize -> FalseColor -> Encode
============================================================

Source: 5478x3650 (19.99 MP)
Output: 1920x1080
Frames: 30
CPUs: 14

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

============================================================
Target: 60 FPS | Best: 119.5 FPS | PASSED
============================================================
```

## When to Use Each

### BatchPipelineExecutor (Data-Parallel)

Best when:
- Processing a fixed batch of images
- Pipeline stages have similar execution times
- Maximum throughput needed
- OpenCV-based filters (releases GIL)

### StreamingPipelineExecutor (Stage-Parallel)

Best when:
- Processing continuous stream (video, camera)
- Need low latency for individual frames
- Pipeline has CPU-bound and I/O-bound stages
- Memory-constrained (queue limits buffer size)

## Thread Safety

All ImageStag filters are thread-safe:

```python
# Same filter instance can be used from multiple threads
resize = Resize(scale=0.5)

with ThreadPoolExecutor(max_workers=8) as executor:
    results = list(executor.map(resize.apply, images))
```

### Thread Safety Guarantees

1. Filters don't modify instance state during `apply()`
2. Class-level caches (like FalseColor LUT) are write-once
3. No global state mutation
4. Input images are never modified

See [AGENTS.md](../AGENTS.md) for complete thread safety guidelines.

## Example: Real-time Video Processing

```python
import cv2
from imagestag import Image
from imagestag.filters import FilterPipeline, StreamingPipelineExecutor
from imagestag.pixel_format import PixelFormat

pipeline = FilterPipeline([
    Resize(size=(640, 480)),
    FalseColor(colormap='inferno'),
])

cap = cv2.VideoCapture(0)

with StreamingPipelineExecutor(pipeline) as executor:
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Submit frame
        img = Image(frame, pixel_format=PixelFormat.BGR)
        executor.submit(img)

        # Get processed result
        result = executor.get_result(timeout=0.1)
        if result:
            cv2.imshow('Processed', result.get_pixels(PixelFormat.BGR))

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

cap.release()
```
