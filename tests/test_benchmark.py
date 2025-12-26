"""Tests for Benchmark utilities."""

import pytest
import json
import numpy as np
from imagestag import Image
from imagestag.pixel_format import PixelFormat
from imagestag.filters import (
    Benchmark,
    BenchmarkConfig,
    BenchmarkResult,
    ExecutorResult,
    StageResult,
    Resize,
    FalseColor,
    Grayscale,
    FilterPipeline,
)


@pytest.fixture
def test_image():
    """Create a test image."""
    pixels = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
    return Image(pixels, pixel_format=PixelFormat.RGB)


class TestBenchmarkConfig:
    """Tests for BenchmarkConfig."""

    def test_default_config(self):
        """BenchmarkConfig should have sensible defaults."""
        config = BenchmarkConfig()
        assert config.num_frames == 30
        assert config.target_fps is None
        assert config.warmup_frames == 1
        assert config.run_sequential is True
        assert config.run_data_parallel is True
        assert config.run_stage_parallel is True
        assert config.num_workers is None

    def test_custom_config(self):
        """BenchmarkConfig should accept custom values."""
        config = BenchmarkConfig(
            num_frames=100,
            target_fps=60,
            warmup_frames=5,
            run_sequential=False,
            num_workers=8,
        )
        assert config.num_frames == 100
        assert config.target_fps == 60
        assert config.warmup_frames == 5
        assert config.run_sequential is False
        assert config.num_workers == 8

    def test_to_dict(self):
        """BenchmarkConfig should serialize to dict."""
        config = BenchmarkConfig(num_frames=50, target_fps=30)
        d = config.to_dict()
        assert d['num_frames'] == 50
        assert d['target_fps'] == 30


class TestStageResult:
    """Tests for StageResult."""

    def test_stage_result_creation(self):
        """StageResult should store stage timing data."""
        stage = StageResult(
            name='Resize',
            avg_ms=5.0,
            total_ms=50.0,
            frames=10,
        )
        assert stage.name == 'Resize'
        assert stage.avg_ms == 5.0
        assert stage.total_ms == 50.0
        assert stage.frames == 10

    def test_to_dict(self):
        """StageResult should serialize to dict."""
        stage = StageResult(name='Test', avg_ms=1.0, total_ms=10.0, frames=10)
        d = stage.to_dict()
        assert d['name'] == 'Test'
        assert d['avg_ms'] == 1.0


class TestExecutorResult:
    """Tests for ExecutorResult."""

    def test_executor_result_creation(self):
        """ExecutorResult should store executor timing data."""
        result = ExecutorResult(
            executor='sequential',
            total_time_s=1.0,
            fps=30.0,
            per_frame_ms=33.3,
            frames=30,
        )
        assert result.executor == 'sequential'
        assert result.total_time_s == 1.0
        assert result.fps == 30.0
        assert result.frames == 30

    def test_executor_result_with_stages(self):
        """ExecutorResult should support stage breakdown."""
        stages = [
            StageResult(name='Stage1', avg_ms=10.0, total_ms=100.0, frames=10),
            StageResult(name='Stage2', avg_ms=5.0, total_ms=50.0, frames=10),
        ]
        result = ExecutorResult(
            executor='stage_parallel',
            total_time_s=0.5,
            fps=20.0,
            per_frame_ms=50.0,
            frames=10,
            stages=stages,
        )
        assert len(result.stages) == 2
        assert result.stages[0].name == 'Stage1'

    def test_to_dict(self):
        """ExecutorResult should serialize to dict."""
        result = ExecutorResult(
            executor='data_parallel',
            total_time_s=0.5,
            fps=60.0,
            per_frame_ms=16.7,
            frames=30,
        )
        d = result.to_dict()
        assert d['executor'] == 'data_parallel'
        assert d['fps'] == 60.0


class TestBenchmarkResult:
    """Tests for BenchmarkResult."""

    def test_benchmark_result_creation(self):
        """BenchmarkResult should store complete benchmark data."""
        result = BenchmarkResult(
            name='Test Benchmark',
            source_size=(1920, 1080),
            source_megapixels=2.07,
            output_size=(960, 540),
            num_frames=30,
            num_cpus=8,
            target_fps=60.0,
            passed=True,
        )
        assert result.name == 'Test Benchmark'
        assert result.source_size == (1920, 1080)
        assert result.passed is True

    def test_to_dict(self):
        """BenchmarkResult should serialize to dict."""
        result = BenchmarkResult(
            name='Test',
            source_size=(100, 100),
            source_megapixels=0.01,
            output_size=(50, 50),
            num_frames=10,
            num_cpus=4,
            target_fps=None,
            passed=None,
            best_executor='sequential',
            best_fps=100.0,
        )
        d = result.to_dict()
        assert d['name'] == 'Test'
        assert d['best_fps'] == 100.0

    def test_to_json(self):
        """BenchmarkResult should serialize to JSON."""
        result = BenchmarkResult(
            name='Test',
            source_size=(100, 100),
            source_megapixels=0.01,
            output_size=(50, 50),
            num_frames=10,
            num_cpus=4,
            target_fps=30.0,
            passed=True,
            results=[
                ExecutorResult(
                    executor='sequential',
                    total_time_s=0.5,
                    fps=20.0,
                    per_frame_ms=50.0,
                    frames=10,
                )
            ],
        )
        json_str = result.to_json()
        parsed = json.loads(json_str)
        assert parsed['name'] == 'Test'
        assert len(parsed['results']) == 1
        assert parsed['results'][0]['executor'] == 'sequential'

    def test_from_dict(self):
        """BenchmarkResult should deserialize from dict."""
        d = {
            'name': 'Test',
            'source_size': (100, 100),
            'source_megapixels': 0.01,
            'output_size': (50, 50),
            'num_frames': 10,
            'num_cpus': 4,
            'target_fps': None,
            'passed': None,
            'best_executor': 'sequential',
            'best_fps': 50.0,
            'filter_name': '',
            'pipeline_stages': [],
            'results': [
                {
                    'executor': 'sequential',
                    'total_time_s': 0.2,
                    'fps': 50.0,
                    'per_frame_ms': 20.0,
                    'frames': 10,
                    'stages': [],
                }
            ],
        }
        result = BenchmarkResult.from_dict(d)
        assert result.name == 'Test'
        assert result.best_fps == 50.0
        assert len(result.results) == 1
        assert result.results[0].fps == 50.0

    def test_ascii_table(self):
        """BenchmarkResult should generate ASCII table."""
        result = BenchmarkResult(
            name='Test',
            source_size=(100, 100),
            source_megapixels=0.01,
            output_size=(50, 50),
            num_frames=10,
            num_cpus=4,
            target_fps=30.0,
            passed=True,
            best_executor='sequential',
            best_fps=50.0,
            results=[
                ExecutorResult(
                    executor='sequential',
                    total_time_s=0.2,
                    fps=50.0,
                    per_frame_ms=20.0,
                    frames=10,
                )
            ],
        )
        table = result.ascii_table()
        assert 'BENCHMARK' in table
        assert 'sequential' in table
        assert '50.0' in table
        assert 'PASSED' in table


class TestBenchmarkRunFilter:
    """Tests for Benchmark.run_filter()."""

    def test_run_filter_returns_result(self, test_image):
        """run_filter should return BenchmarkResult."""
        result = Benchmark.run_filter(
            Resize(scale=0.5),
            source=test_image,
            num_frames=5,
        )
        assert isinstance(result, BenchmarkResult)
        assert result.num_frames == 5
        assert result.filter_name == 'Resize'
        assert 'Filter: Resize' in result.name

    def test_run_filter_measures_fps(self, test_image):
        """run_filter should measure FPS."""
        result = Benchmark.run_filter(
            Grayscale(),
            source=test_image,
            num_frames=10,
        )
        assert result.best_fps > 0
        assert len(result.results) > 0
        assert all(r.fps > 0 for r in result.results)

    def test_run_filter_with_target(self, test_image):
        """run_filter should check against target FPS."""
        result = Benchmark.run_filter(
            Resize(scale=0.5),
            source=test_image,
            num_frames=5,
            target_fps=1.0,  # Very low target, should pass
        )
        assert result.passed is True

    def test_run_filter_with_config(self, test_image):
        """run_filter should accept BenchmarkConfig."""
        config = BenchmarkConfig(
            num_frames=5,
            target_fps=1.0,
            run_data_parallel=False,
        )
        result = Benchmark.run_filter(
            Resize(scale=0.5),
            source=test_image,
            config=config,
        )
        # Should only have sequential result (stage_parallel disabled for single filter)
        executor_names = [r.executor for r in result.results]
        assert 'sequential' in executor_names
        assert 'data_parallel' not in executor_names

    def test_run_filter_captures_output_size(self, test_image):
        """run_filter should capture output dimensions."""
        result = Benchmark.run_filter(
            Resize(scale=0.5),
            source=test_image,
            num_frames=3,
        )
        assert result.source_size == (100, 100)
        assert result.output_size == (50, 50)


class TestBenchmarkRunPipeline:
    """Tests for Benchmark.run_pipeline()."""

    def test_run_pipeline_returns_result(self, test_image):
        """run_pipeline should return BenchmarkResult."""
        pipeline = FilterPipeline(filters=[
            Resize(scale=0.5),
            Grayscale(),
        ])
        result = Benchmark.run_pipeline(
            pipeline,
            source=test_image,
            num_frames=5,
        )
        assert isinstance(result, BenchmarkResult)
        assert result.num_frames == 5
        assert result.pipeline_stages == ['Resize', 'Grayscale']
        assert 'Pipeline:' in result.name

    def test_run_pipeline_from_list(self, test_image):
        """run_pipeline should accept list of filters."""
        result = Benchmark.run_pipeline(
            [Resize(scale=0.5), Grayscale()],
            source=test_image,
            num_frames=5,
        )
        assert result.pipeline_stages == ['Resize', 'Grayscale']

    def test_run_pipeline_includes_stage_parallel(self, test_image):
        """run_pipeline should include stage-parallel for multi-stage."""
        pipeline = FilterPipeline(filters=[
            Resize(scale=0.5),
            Grayscale(),
            FalseColor(colormap='hot'),
        ])
        result = Benchmark.run_pipeline(
            pipeline,
            source=test_image,
            num_frames=5,
        )
        executor_names = [r.executor for r in result.results]
        assert 'stage_parallel' in executor_names

    def test_run_pipeline_stage_metrics(self, test_image):
        """run_pipeline should include per-stage metrics."""
        pipeline = FilterPipeline(filters=[
            Resize(scale=0.5),
            Grayscale(),
        ])
        result = Benchmark.run_pipeline(
            pipeline,
            source=test_image,
            num_frames=5,
        )
        # Find stage_parallel result
        stage_result = next(
            (r for r in result.results if r.executor == 'stage_parallel'),
            None
        )
        if stage_result:
            assert len(stage_result.stages) == 2
            assert stage_result.stages[0].name.endswith('Resize')
            assert stage_result.stages[1].name.endswith('Grayscale')


class TestBenchmarkCompareFilters:
    """Tests for Benchmark.compare_filters()."""

    def test_compare_filters_returns_table(self, test_image):
        """compare_filters should return ASCII table string."""
        filters = [
            Resize(scale=0.5),
            Grayscale(),
        ]
        table = Benchmark.compare_filters(filters, test_image, num_frames=3)
        assert isinstance(table, str)
        assert 'FILTER COMPARISON' in table
        assert 'Resize' in table
        assert 'Grayscale' in table

    def test_compare_filters_sorted_by_fps(self, test_image):
        """compare_filters should sort by FPS (fastest first)."""
        # Create filters with different speeds
        filters = [
            Resize(scale=0.5),  # Fast
            FalseColor(colormap='viridis'),  # Slower
        ]
        table = Benchmark.compare_filters(filters, test_image, num_frames=3)
        # Resize should appear before FalseColor (faster)
        resize_pos = table.find('Resize')
        falsecolor_pos = table.find('FalseColor')
        assert resize_pos < falsecolor_pos


class TestBenchmarkIntegration:
    """Integration tests for Benchmark."""

    def test_full_roundtrip(self, test_image):
        """Benchmark result should survive JSON roundtrip."""
        result = Benchmark.run_filter(
            Resize(scale=0.5),
            source=test_image,
            num_frames=3,
            target_fps=1.0,
        )

        # Serialize to JSON
        json_str = result.to_json()

        # Parse back
        parsed = json.loads(json_str)
        restored = BenchmarkResult.from_dict(parsed)

        # Verify
        assert restored.name == result.name
        assert restored.best_fps == result.best_fps
        assert restored.passed == result.passed
        assert len(restored.results) == len(result.results)

    def test_print_does_not_error(self, test_image, capsys):
        """result.print() should not raise errors."""
        result = Benchmark.run_filter(
            Resize(scale=0.5),
            source=test_image,
            num_frames=3,
        )
        result.print()
        captured = capsys.readouterr()
        assert 'BENCHMARK' in captured.out
