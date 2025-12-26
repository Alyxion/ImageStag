# ImageStag Filters - Benchmark Utilities
"""
Benchmark utilities for measuring filter and pipeline performance.

Supports benchmarking:
- Single filters
- Filter pipelines
- Multiple execution modes (sequential, data-parallel, stage-parallel)

Results are serializable dataclasses with ASCII table output.
"""

from __future__ import annotations

import time
import os
from dataclasses import dataclass, field, asdict
from typing import TYPE_CHECKING, Any
import json

if TYPE_CHECKING:
    from imagestag import Image
    from .base import Filter
    from .pipeline import FilterPipeline


@dataclass
class StageResult:
    """Timing result for a single pipeline stage."""
    name: str
    avg_ms: float
    total_ms: float
    frames: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ExecutorResult:
    """Result from a single executor run."""
    executor: str  # 'sequential', 'data_parallel', 'stage_parallel'
    total_time_s: float
    fps: float
    per_frame_ms: float
    frames: int
    stages: list[StageResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d['stages'] = [s.to_dict() for s in self.stages]
        return d


@dataclass
class BenchmarkResult:
    """Complete benchmark result - serializable."""
    name: str
    source_size: tuple[int, int]
    source_megapixels: float
    output_size: tuple[int, int] | None
    num_frames: int
    num_cpus: int
    target_fps: float | None
    passed: bool | None

    # Results per executor
    results: list[ExecutorResult] = field(default_factory=list)

    # Best result
    best_executor: str = ''
    best_fps: float = 0.0

    # Filter/pipeline info
    filter_name: str = ''
    pipeline_stages: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        d = asdict(self)
        d['results'] = [r.to_dict() for r in self.results]
        return d

    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> 'BenchmarkResult':
        """Create from dictionary."""
        results = [ExecutorResult(**r) for r in d.pop('results', [])]
        for r in results:
            r.stages = [StageResult(**s) for s in r.stages] if r.stages else []
        return cls(**d, results=results)

    def ascii_table(self) -> str:
        """Generate ASCII table representation."""
        lines = []
        lines.append("=" * 60)
        lines.append(f"BENCHMARK: {self.name}")
        lines.append("=" * 60)
        lines.append("")

        # Source info
        lines.append(f"Source: {self.source_size[0]}x{self.source_size[1]} ({self.source_megapixels:.2f} MP)")
        if self.output_size:
            lines.append(f"Output: {self.output_size[0]}x{self.output_size[1]}")
        lines.append(f"Frames: {self.num_frames}")
        lines.append(f"CPUs: {self.num_cpus}")
        lines.append("")

        # Pipeline/filter info
        if self.filter_name:
            lines.append(f"Filter: {self.filter_name}")
        if self.pipeline_stages:
            lines.append(f"Pipeline: {' → '.join(self.pipeline_stages)}")
        lines.append("")

        # Results table
        lines.append("-" * 60)
        lines.append(f"{'Executor':<20} {'Time':>10} {'FPS':>10} {'Per-frame':>12}")
        lines.append("-" * 60)

        for r in self.results:
            lines.append(
                f"{r.executor:<20} {r.total_time_s:>9.3f}s {r.fps:>10.1f} {r.per_frame_ms:>10.1f}ms"
            )

        lines.append("-" * 60)
        lines.append("")

        # Stage breakdown for stage-parallel
        for r in self.results:
            if r.stages:
                lines.append(f"Stage breakdown ({r.executor}):")
                for s in r.stages:
                    lines.append(f"  {s.name}: {s.avg_ms:.1f}ms avg")
                lines.append("")

        # Summary
        lines.append("=" * 60)
        if self.target_fps:
            status = "PASSED ✓" if self.passed else "FAILED ✗"
            lines.append(f"Target: {self.target_fps:.0f} FPS | Best: {self.best_fps:.1f} FPS | {status}")
        else:
            lines.append(f"Best: {self.best_fps:.1f} FPS ({self.best_executor})")
        lines.append("=" * 60)

        return "\n".join(lines)

    def print(self) -> None:
        """Print ASCII table to terminal."""
        print(self.ascii_table())


@dataclass
class BenchmarkConfig:
    """Configuration for benchmark runs."""
    num_frames: int = 30
    target_fps: float | None = None
    warmup_frames: int = 1
    run_sequential: bool = True
    run_data_parallel: bool = True
    run_stage_parallel: bool = True
    num_workers: int | None = None  # Auto-detect

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class Benchmark:
    """Benchmark runner for filters and pipelines.

    Example - Single filter::

        from imagestag.filters import Benchmark, Resize
        from imagestag.samples import group

        result = Benchmark.run_filter(
            Resize(scale=0.5),
            source=group(),
            num_frames=100
        )
        result.print()

    Example - Pipeline::

        from imagestag.filters import Benchmark, FilterPipeline, Resize, FalseColor

        pipeline = FilterPipeline([
            Resize(size=(1920, 1080)),
            FalseColor(colormap='hot'),
        ])

        result = Benchmark.run_pipeline(
            pipeline,
            source=group(),
            num_frames=30,
            target_fps=60
        )
        result.print()
        print(result.to_json())

    Example - Custom config::

        config = BenchmarkConfig(
            num_frames=100,
            target_fps=30,
            run_stage_parallel=False
        )
        result = Benchmark.run_filter(Resize(scale=0.5), source, config=config)
    """

    @staticmethod
    def run_filter(
        filter: 'Filter',
        source: 'Image',
        num_frames: int = 30,
        target_fps: float | None = None,
        config: BenchmarkConfig | None = None,
    ) -> BenchmarkResult:
        """Benchmark a single filter.

        :param filter: The filter to benchmark
        :param source: Source image
        :param num_frames: Number of frames to process
        :param target_fps: Target FPS for pass/fail (optional)
        :param config: Full config (overrides other params)
        :returns: BenchmarkResult with timing data
        """
        from .pipeline import FilterPipeline

        # Wrap single filter in pipeline
        pipeline = FilterPipeline(filters=[filter])

        if config is None:
            config = BenchmarkConfig(
                num_frames=num_frames,
                target_fps=target_fps,
                run_stage_parallel=False,  # No point for single filter
            )

        result = Benchmark._run(pipeline, source, config)
        result.filter_name = filter.__class__.__name__
        result.name = f"Filter: {filter.__class__.__name__}"
        return result

    @staticmethod
    def run_pipeline(
        pipeline: 'FilterPipeline | list[Filter]',
        source: 'Image',
        num_frames: int = 30,
        target_fps: float | None = None,
        config: BenchmarkConfig | None = None,
    ) -> BenchmarkResult:
        """Benchmark a filter pipeline.

        :param pipeline: FilterPipeline or list of filters
        :param source: Source image
        :param num_frames: Number of frames to process
        :param target_fps: Target FPS for pass/fail (optional)
        :param config: Full config (overrides other params)
        :returns: BenchmarkResult with timing data
        """
        from .pipeline import FilterPipeline

        if isinstance(pipeline, list):
            pipeline = FilterPipeline(filters=pipeline)

        if config is None:
            config = BenchmarkConfig(
                num_frames=num_frames,
                target_fps=target_fps,
            )

        result = Benchmark._run(pipeline, source, config)
        result.pipeline_stages = [f.__class__.__name__ for f in pipeline.filters]
        result.name = f"Pipeline: {' → '.join(result.pipeline_stages)}"
        return result

    @staticmethod
    def _run(
        pipeline: 'FilterPipeline',
        source: 'Image',
        config: BenchmarkConfig,
    ) -> BenchmarkResult:
        """Internal: Run benchmark with all executors."""
        from .executor import StreamingPipelineExecutor, BatchPipelineExecutor

        num_workers = config.num_workers or os.cpu_count() or 4

        # Warmup
        for _ in range(config.warmup_frames):
            _ = pipeline.apply(source)

        results: list[ExecutorResult] = []

        # Sequential
        if config.run_sequential:
            start = time.perf_counter()
            for _ in range(config.num_frames):
                _ = pipeline.apply(source)
            elapsed = time.perf_counter() - start

            results.append(ExecutorResult(
                executor='sequential',
                total_time_s=elapsed,
                fps=config.num_frames / elapsed,
                per_frame_ms=elapsed / config.num_frames * 1000,
                frames=config.num_frames,
            ))

        # Data-parallel
        if config.run_data_parallel:
            images = [source] * config.num_frames

            start = time.perf_counter()
            with BatchPipelineExecutor(pipeline, num_workers=num_workers) as executor:
                _ = executor.process_all(images)
            elapsed = time.perf_counter() - start

            results.append(ExecutorResult(
                executor='data_parallel',
                total_time_s=elapsed,
                fps=config.num_frames / elapsed,
                per_frame_ms=elapsed / config.num_frames * 1000,
                frames=config.num_frames,
            ))

        # Stage-parallel
        if config.run_stage_parallel and len(pipeline.filters) > 1:
            start = time.perf_counter()
            with StreamingPipelineExecutor(pipeline) as executor:
                for _ in range(config.num_frames):
                    executor.submit(source)
                _ = list(executor.results(config.num_frames))

                metrics = executor.get_metrics()
            elapsed = time.perf_counter() - start

            stages = [
                StageResult(
                    name=s.stage_name,
                    avg_ms=s.avg_time_ms,
                    total_ms=s.total_time_ms,
                    frames=s.frames_processed,
                )
                for s in metrics.stages
            ]

            results.append(ExecutorResult(
                executor='stage_parallel',
                total_time_s=elapsed,
                fps=config.num_frames / elapsed,
                per_frame_ms=elapsed / config.num_frames * 1000,
                frames=config.num_frames,
                stages=stages,
            ))

        # Find best
        best = max(results, key=lambda r: r.fps) if results else None
        best_executor = best.executor if best else ''
        best_fps = best.fps if best else 0.0

        # Check pass/fail
        passed = None
        if config.target_fps is not None:
            passed = best_fps >= config.target_fps

        # Get output size from a single apply
        output = pipeline.apply(source)
        output_size = (output.width, output.height)

        return BenchmarkResult(
            name='Benchmark',
            source_size=(source.width, source.height),
            source_megapixels=source.width * source.height / 1e6,
            output_size=output_size,
            num_frames=config.num_frames,
            num_cpus=os.cpu_count() or 1,
            target_fps=config.target_fps,
            passed=passed,
            results=results,
            best_executor=best_executor,
            best_fps=best_fps,
        )

    @staticmethod
    def compare_filters(
        filters: list['Filter'],
        source: 'Image',
        num_frames: int = 30,
    ) -> str:
        """Compare multiple filters side by side.

        :param filters: List of filters to compare
        :param source: Source image
        :param num_frames: Number of frames per filter
        :returns: ASCII comparison table
        """
        results = []
        for f in filters:
            r = Benchmark.run_filter(
                f, source, num_frames,
                config=BenchmarkConfig(
                    num_frames=num_frames,
                    run_sequential=True,
                    run_data_parallel=False,
                    run_stage_parallel=False,
                )
            )
            results.append((f.__class__.__name__, r))

        lines = []
        lines.append("=" * 50)
        lines.append("FILTER COMPARISON")
        lines.append("=" * 50)
        lines.append(f"Source: {source.width}x{source.height}")
        lines.append(f"Frames: {num_frames}")
        lines.append("")
        lines.append("-" * 50)
        lines.append(f"{'Filter':<25} {'FPS':>10} {'Per-frame':>12}")
        lines.append("-" * 50)

        for name, r in sorted(results, key=lambda x: -x[1].best_fps):
            seq = next((x for x in r.results if x.executor == 'sequential'), None)
            if seq:
                lines.append(f"{name:<25} {seq.fps:>10.1f} {seq.per_frame_ms:>10.1f}ms")

        lines.append("-" * 50)

        return "\n".join(lines)


__all__ = [
    'Benchmark',
    'BenchmarkConfig',
    'BenchmarkResult',
    'ExecutorResult',
    'StageResult',
]
