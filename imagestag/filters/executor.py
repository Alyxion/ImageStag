"""
Parallel streaming pipeline executor for ImageStag filters.

Provides multi-threaded execution of filter pipelines with:
- Stage-based parallelism (pipeline parallel)
- Frame-based parallelism (data parallel)
- Producer-consumer queues between stages
- Streaming input support
- Performance metrics
"""

from __future__ import annotations

import threading
import queue
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Iterator, Any
from concurrent.futures import ThreadPoolExecutor, Future
import os

if TYPE_CHECKING:
    from imagestag import Image
    from .pipeline import FilterPipeline
    from .graph import FilterGraph
    from .base import Filter, FilterContext


@dataclass
class StageMetrics:
    """Performance metrics for a pipeline stage.

    :param stage_name: Name of the stage
    :param frames_processed: Number of frames processed
    :param total_time_ms: Total processing time in milliseconds
    """
    stage_name: str
    frames_processed: int = 0
    total_time_ms: float = 0.0

    @property
    def avg_time_ms(self) -> float:
        """Average processing time per frame in milliseconds."""
        if self.frames_processed == 0:
            return 0.0
        return self.total_time_ms / self.frames_processed


@dataclass
class ExecutorMetrics:
    """Overall executor performance metrics.

    :param stages: Per-stage metrics
    :param frames_submitted: Number of frames submitted for processing
    :param frames_completed: Number of frames that completed processing
    :param start_time: Start timestamp (perf_counter)
    :param end_time: End timestamp (perf_counter)
    """
    stages: list[StageMetrics] = field(default_factory=list)
    frames_submitted: int = 0
    frames_completed: int = 0
    start_time: float = 0.0
    end_time: float = 0.0

    @property
    def total_time_s(self) -> float:
        """Total execution time in seconds."""
        return self.end_time - self.start_time

    @property
    def fps(self) -> float:
        """Frames per second throughput."""
        if self.total_time_s <= 0:
            return 0.0
        return self.frames_completed / self.total_time_s

    def summary(self) -> str:
        """Generate human-readable summary of metrics."""
        lines = [
            "=== Pipeline Execution Metrics ===",
            f"Frames: {self.frames_completed} / {self.frames_submitted}",
            f"Total time: {self.total_time_s:.3f}s",
            f"Throughput: {self.fps:.1f} FPS",
            "",
            "Per-stage breakdown:",
        ]
        for stage in self.stages:
            lines.append(f"  {stage.stage_name}: {stage.avg_time_ms:.2f}ms avg")
        return "\n".join(lines)


@dataclass
class _PipelineStage:
    """Internal: A single stage in the execution pipeline."""
    name: str
    filter: 'Filter'
    input_queue: queue.Queue
    output_queue: queue.Queue
    metrics: StageMetrics = field(default_factory=lambda: StageMetrics(""))
    _stop_event: threading.Event = field(default_factory=threading.Event)

    def __post_init__(self):
        self.metrics.stage_name = self.name


class StreamingPipelineExecutor:
    """Parallel executor for filter pipelines with streaming support.

    Executes pipeline stages in parallel using producer-consumer queues.
    Each stage runs in its own thread, allowing overlapped execution
    where frame N can be at stage 3 while frame N+1 is at stage 2.

    This enables efficient processing of continuous image streams,
    such as video frames or real-time camera input.

    Example::

        pipeline = FilterPipeline([
            Resize(scale=0.5),
            FalseColor('hot'),
        ])

        with StreamingPipelineExecutor(pipeline, num_workers=4) as executor:
            # Submit frames
            for img in image_source:
                executor.submit(img)

            # Get results
            for result in executor.results():
                process(result)

    :param pipeline: FilterPipeline, FilterGraph, or list of Filters to execute
    :param num_workers: Number of parallel workers (auto-detect if None)
    :param queue_size: Max items per queue (controls memory usage)
    :param preserve_order: If True, results come out in submission order
    """

    def __init__(
        self,
        pipeline: 'FilterPipeline | FilterGraph | list[Filter]',
        num_workers: int | None = None,
        queue_size: int = 32,
        preserve_order: bool = True,
    ):
        from .pipeline import FilterPipeline
        from .graph import FilterGraph

        # Normalize to list of filters
        if isinstance(pipeline, FilterGraph):
            # For FilterGraph, use its internal pipeline if simple
            # Complex DAGs not yet supported
            if hasattr(pipeline, 'to_pipeline'):
                self._filters = list(pipeline.to_pipeline().filters)
            else:
                raise NotImplementedError(
                    "Complex FilterGraph parallelization not yet supported. "
                    "Use FilterPipeline or convert graph to pipeline first."
                )
        elif isinstance(pipeline, FilterPipeline):
            self._filters = list(pipeline.filters)
        else:
            self._filters = list(pipeline)

        self._num_workers = num_workers or os.cpu_count() or 4
        self._queue_size = queue_size
        self._preserve_order = preserve_order

        # Build stage pipeline
        self._stages: list[_PipelineStage] = []
        self._input_queue: queue.Queue = queue.Queue(queue_size)
        self._output_queue: queue.Queue = queue.Queue(queue_size)

        self._workers: list[threading.Thread] = []
        self._stop_event = threading.Event()
        self._started = False
        self._metrics = ExecutorMetrics()

        # Sequence tracking for ordered results
        self._next_seq = 0
        self._pending_results: dict[int, Any] = {}
        self._result_lock = threading.Lock()
        self._next_result_seq = 0

        self._build_stages()

    def _build_stages(self) -> None:
        """Build the stage pipeline with queues."""
        prev_queue = self._input_queue

        for i, f in enumerate(self._filters):
            stage_name = f"{i}_{f.__class__.__name__}"
            is_last = (i == len(self._filters) - 1)
            output_q = self._output_queue if is_last else queue.Queue(self._queue_size)

            stage = _PipelineStage(
                name=stage_name,
                filter=f,
                input_queue=prev_queue,
                output_queue=output_q,
            )
            self._stages.append(stage)
            self._metrics.stages.append(stage.metrics)
            prev_queue = output_q

    def start(self) -> None:
        """Start worker threads.

        Called automatically on first submit() if not called explicitly.
        """
        if self._started:
            return

        self._metrics.start_time = time.perf_counter()

        # Start a thread for each stage
        for stage in self._stages:
            worker = threading.Thread(
                target=self._stage_worker,
                args=(stage,),
                daemon=True,
                name=f"PipelineWorker-{stage.name}",
            )
            worker.start()
            self._workers.append(worker)

        self._started = True

    def _stage_worker(self, stage: _PipelineStage) -> None:
        """Worker loop for a single stage."""
        while not self._stop_event.is_set():
            try:
                item = stage.input_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            if item is None:  # Poison pill
                stage.output_queue.put(None)
                break

            seq, image = item

            # Process
            start = time.perf_counter()
            try:
                result = stage.filter.apply(image)
            except Exception as e:
                # On error, pass through original with error metadata
                result = image
                if hasattr(result, 'metadata'):
                    result.metadata['_pipeline_error'] = str(e)
            elapsed = (time.perf_counter() - start) * 1000

            # Update metrics
            stage.metrics.frames_processed += 1
            stage.metrics.total_time_ms += elapsed

            stage.output_queue.put((seq, result))

    def submit(self, image: 'Image') -> int:
        """Submit an image for processing (non-blocking).

        :param image: Image to process
        :returns: Sequence number for this submission
        """
        if not self._started:
            self.start()

        seq = self._next_seq
        self._next_seq += 1
        self._metrics.frames_submitted += 1

        self._input_queue.put((seq, image))
        return seq

    def get_result(self, timeout: float | None = None) -> 'Image | None':
        """Get next processed result (blocking).

        If preserve_order is True, returns results in submission order.

        :param timeout: Max seconds to wait (None = forever)
        :returns: Processed image, or None if stopped
        """
        try:
            item = self._output_queue.get(timeout=timeout)
        except queue.Empty:
            return None

        if item is None:
            return None

        seq, result = item
        self._metrics.frames_completed += 1
        return result

    def results(self, count: int | None = None) -> Iterator['Image']:
        """Iterate over results as they complete.

        :param count: Number of results to yield (None = all submitted)
        :yields: Processed images
        """
        target = count if count is not None else self._metrics.frames_submitted
        received = 0

        while received < target:
            result = self.get_result()
            if result is None:
                break
            yield result
            received += 1

    def process_batch(
        self,
        images: list['Image'],
        show_progress: bool = False,
    ) -> list['Image']:
        """Process a batch of images in parallel.

        Convenience method that handles submitting and collecting results.

        :param images: List of images to process
        :param show_progress: Print progress updates
        :returns: List of processed images in same order as input
        """
        if not self._started:
            self.start()

        # Submit all
        for img in images:
            self.submit(img)

        # Collect results
        results = []
        for i, result in enumerate(self.results(len(images))):
            results.append(result)
            if show_progress and (i + 1) % 10 == 0:
                print(f"Processed {i + 1}/{len(images)} frames")

        return results

    def stop(self) -> None:
        """Stop all workers gracefully."""
        self._stop_event.set()

        # Send poison pills
        self._input_queue.put(None)

        # Wait for workers
        for w in self._workers:
            w.join(timeout=1.0)

        self._metrics.end_time = time.perf_counter()

    def get_metrics(self) -> ExecutorMetrics:
        """Get execution metrics.

        :returns: ExecutorMetrics with timing and throughput data
        """
        self._metrics.end_time = time.perf_counter()
        return self._metrics

    def __enter__(self) -> 'StreamingPipelineExecutor':
        self.start()
        return self

    def __exit__(self, *args) -> None:
        self.stop()


class BatchPipelineExecutor:
    """Data-parallel batch executor using ThreadPoolExecutor.

    For simpler use cases where you want to process N images
    across M threads, without pipeline parallelism.

    Example::

        with BatchPipelineExecutor(pipeline, num_workers=8) as executor:
            results = executor.process_all(images)

    :param pipeline: FilterPipeline or list of Filters
    :param num_workers: Number of parallel workers (auto-detect if None)
    """

    def __init__(
        self,
        pipeline: 'FilterPipeline | list[Filter]',
        num_workers: int | None = None,
    ):
        from .pipeline import FilterPipeline

        if isinstance(pipeline, list):
            pipeline = FilterPipeline(filters=pipeline)
        self._pipeline = pipeline
        self._num_workers = num_workers or os.cpu_count() or 4
        self._executor: ThreadPoolExecutor | None = None
        self._metrics = ExecutorMetrics()

    def _process_one(self, image: 'Image') -> 'Image':
        """Process a single image through the pipeline."""
        return self._pipeline.apply(image)

    def process_all(
        self,
        images: list['Image'],
        show_progress: bool = False,
    ) -> list['Image']:
        """Process all images in parallel, preserving order.

        :param images: List of images to process
        :param show_progress: Print progress updates
        :returns: List of processed images in same order as input
        """
        self._metrics.start_time = time.perf_counter()
        self._metrics.frames_submitted = len(images)

        futures: list[Future] = []

        for img in images:
            future = self._executor.submit(self._process_one, img)
            futures.append(future)

        results = []
        for i, future in enumerate(futures):
            results.append(future.result())
            self._metrics.frames_completed += 1
            if show_progress and (i + 1) % 10 == 0:
                print(f"Processed {i + 1}/{len(images)} frames")

        self._metrics.end_time = time.perf_counter()
        return results

    def get_metrics(self) -> ExecutorMetrics:
        """Get execution metrics."""
        return self._metrics

    def __enter__(self) -> 'BatchPipelineExecutor':
        self._executor = ThreadPoolExecutor(max_workers=self._num_workers)
        return self

    def __exit__(self, *args) -> None:
        if self._executor:
            self._executor.shutdown(wait=True)


__all__ = [
    'StreamingPipelineExecutor',
    'BatchPipelineExecutor',
    'ExecutorMetrics',
    'StageMetrics',
]
