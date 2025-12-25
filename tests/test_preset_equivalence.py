# Test preset graph vs DSL equivalence
"""
Comprehensive tests for all preset pipelines.

This module auto-discovers ALL presets from the central registry and verifies:
1. Graph execution produces valid output images
2. DSL parsing produces valid output images
3. Graph and DSL execution produce equivalent results (for linear pipelines)

For complex presets with branches/combiners, only graph execution is tested
since DSL parsing for complex graphs is not yet implemented.
"""

import numpy as np
import pytest

from imagestag import Image
from imagestag.filters.graph import FilterGraph
from imagestag.filters.source import ExecutionMode
from imagestag.skimage import SKImage
from imagestag.tools.preset_registry import (
    ALL_PRESETS,
    PRESETS,
    Preset,
    get_linear_presets,
)


def load_sample_image(name: str) -> Image:
    """Load a sample image by name.

    Tries ImageStag samples first, then scikit-image samples.
    """
    from imagestag import samples as imagestag_samples

    # Try imagestag samples first (stag, group)
    if name in imagestag_samples.list_images():
        return imagestag_samples.load(name)

    # Try scikit-image samples
    if name in SKImage.list_images():
        return SKImage.load(name)

    raise ValueError(f"Sample image not found: {name}")


def load_preset_inputs(preset: Preset) -> dict[str, Image]:
    """Load all input images for a preset based on its input specifications."""
    inputs = {}
    for inp in preset.inputs:
        inputs[inp.name] = load_sample_image(inp.sample_image)
    return inputs


# =============================================================================
# DISCOVERY TESTS - Verify preset registry is complete
# =============================================================================

class TestPresetRegistry:
    """Tests for the preset registry structure."""

    def test_all_presets_have_keys(self):
        """Every preset in ALL_PRESETS must have a unique key."""
        keys = [p.key for p in ALL_PRESETS]
        assert len(keys) == len(set(keys)), "Duplicate preset keys found"

    def test_all_presets_in_dict(self):
        """PRESETS dict contains all presets from ALL_PRESETS."""
        for preset in ALL_PRESETS:
            assert preset.key in PRESETS
            assert PRESETS[preset.key] is preset

    def test_all_presets_have_graph(self):
        """Every preset must have a graph definition."""
        for preset in ALL_PRESETS:
            assert preset.graph is not None
            assert 'nodes' in preset.graph
            assert 'connections' in preset.graph

    def test_all_presets_have_dsl(self):
        """Every preset must have a DSL string."""
        for preset in ALL_PRESETS:
            assert preset.dsl is not None
            assert len(preset.dsl) > 0

    def test_all_presets_have_inputs(self):
        """Every preset must have at least one input."""
        for preset in ALL_PRESETS:
            assert len(preset.inputs) > 0

    def test_preset_count(self):
        """Ensure we have the expected number of presets."""
        # Update this number when adding new presets
        assert len(ALL_PRESETS) >= 7, (
            f"Expected at least 7 presets, found {len(ALL_PRESETS)}"
        )


# =============================================================================
# GRAPH EXECUTION TESTS - Test each preset's graph on real images
# =============================================================================

class TestGraphExecution:
    """Test graph execution for all presets using real sample images."""

    @pytest.mark.parametrize(
        "preset_key",
        [p.key for p in ALL_PRESETS],
        ids=[p.key for p in ALL_PRESETS],
    )
    def test_graph_execution(self, preset_key: str):
        """Execute preset graph on actual sample images."""
        preset = PRESETS[preset_key]

        # Load input images
        inputs = load_preset_inputs(preset)

        # Build graph from preset
        graph = preset.to_graph()

        # Execute graph
        if len(inputs) == 1:
            # Single input
            result = graph.execute(list(inputs.values())[0])
        else:
            # Multiple inputs - use keyword args
            result = graph.execute(**inputs)

        # Verify output
        assert result is not None, f"Graph execution returned None for {preset_key}"
        assert isinstance(result, Image), (
            f"Expected Image, got {type(result)} for {preset_key}"
        )
        assert result.width > 0, f"Result has zero width for {preset_key}"
        assert result.height > 0, f"Result has zero height for {preset_key}"

    @pytest.mark.parametrize(
        "preset_key",
        [p.key for p in ALL_PRESETS],
        ids=[p.key for p in ALL_PRESETS],
    )
    def test_graph_designer_mode(self, preset_key: str):
        """Execute preset graph in designer mode (loads placeholders)."""
        preset = PRESETS[preset_key]
        graph = preset.to_graph()

        # Execute in designer mode
        result = graph.execute(mode=ExecutionMode.DESIGNER)

        # Verify output
        assert result is not None, (
            f"Designer mode execution returned None for {preset_key}"
        )
        assert isinstance(result, Image), (
            f"Expected Image, got {type(result)} for {preset_key}"
        )


# =============================================================================
# DSL EXECUTION TESTS - Test DSL parsing and execution for ALL presets
# =============================================================================

class TestDSLExecution:
    """Test DSL parsing and execution for all presets (linear and complex)."""

    @pytest.mark.parametrize(
        "preset_key",
        [p.key for p in ALL_PRESETS],
        ids=[p.key for p in ALL_PRESETS],
    )
    def test_dsl_execution(self, preset_key: str):
        """Parse DSL to graph and execute on sample images."""
        preset = PRESETS[preset_key]

        # Load input images
        inputs = load_preset_inputs(preset)

        # Parse DSL to graph (works for both linear and complex)
        graph = preset.to_dsl_graph()

        # Execute graph
        if len(inputs) == 1:
            result = graph.execute(list(inputs.values())[0])
        else:
            result = graph.execute(**inputs)

        # Verify output
        assert result is not None, f"DSL execution returned None for {preset_key}"
        assert isinstance(result, Image), (
            f"Expected Image, got {type(result)} for {preset_key}"
        )
        assert result.width > 0, f"Result has zero width for {preset_key}"
        assert result.height > 0, f"Result has zero height for {preset_key}"


class TestLinearPipelineDSL:
    """Test FilterPipeline.parse() for linear presets (backward compatibility)."""

    @pytest.mark.parametrize(
        "preset_key",
        [p.key for p in get_linear_presets()],
        ids=[p.key for p in get_linear_presets()],
    )
    def test_pipeline_parsing(self, preset_key: str):
        """Parse linear DSL to FilterPipeline and execute."""
        preset = PRESETS[preset_key]

        # Get input image (linear pipelines have single input)
        inputs = load_preset_inputs(preset)
        input_image = list(inputs.values())[0]

        # Parse DSL to pipeline (legacy method for linear pipelines)
        pipeline = preset.to_pipeline()

        # Execute pipeline
        result = pipeline.apply(input_image)

        # Verify output
        assert result is not None, f"Pipeline execution returned None for {preset_key}"
        assert isinstance(result, Image), (
            f"Expected Image, got {type(result)} for {preset_key}"
        )
        assert result.width > 0, f"Result has zero width for {preset_key}"
        assert result.height > 0, f"Result has zero height for {preset_key}"


# =============================================================================
# EQUIVALENCE TESTS - Verify graph and DSL produce same output
# =============================================================================

class TestGraphDSLEquivalence:
    """Test that graph and DSL execution produce equivalent results."""

    @pytest.mark.parametrize(
        "preset_key",
        [p.key for p in ALL_PRESETS],
        ids=[p.key for p in ALL_PRESETS],
    )
    def test_equivalence(self, preset_key: str):
        """Graph and DSL should produce identical output for all presets."""
        preset = PRESETS[preset_key]

        # Load input images
        inputs = load_preset_inputs(preset)

        # Execute graph (from dict)
        graph = preset.to_graph()
        if len(inputs) == 1:
            graph_result = graph.execute(list(inputs.values())[0])
        else:
            graph_result = graph.execute(**inputs)

        # Execute DSL graph
        dsl_graph = preset.to_dsl_graph()
        if len(inputs) == 1:
            dsl_result = dsl_graph.execute(list(inputs.values())[0])
        else:
            dsl_result = dsl_graph.execute(**inputs)

        # Compare results
        assert graph_result is not None, "Graph result is None"
        assert dsl_result is not None, "DSL result is None"

        # Check dimensions match
        assert graph_result.width == dsl_result.width, (
            f"Width mismatch: graph={graph_result.width}, dsl={dsl_result.width}"
        )
        assert graph_result.height == dsl_result.height, (
            f"Height mismatch: graph={graph_result.height}, dsl={dsl_result.height}"
        )

        # Compare pixels
        graph_pixels = graph_result.get_pixels()
        dsl_pixels = dsl_result.get_pixels()

        # Calculate pixel difference
        diff = np.abs(graph_pixels.astype(np.float32) - dsl_pixels.astype(np.float32))
        max_diff = np.max(diff)
        mean_diff = np.mean(diff)

        # Allow small tolerance for floating point differences
        tolerance = 2.0  # Allow up to 2 pixel value difference
        assert max_diff <= tolerance, (
            f"Pixel mismatch for {preset_key}: max_diff={max_diff:.2f}, "
            f"mean_diff={mean_diff:.2f}"
        )


# =============================================================================
# SPECIFIC PRESET TESTS - Verify specific preset behaviors
# =============================================================================

class TestSpecificPresets:
    """Tests for specific preset behaviors."""

    def test_simple_filter_chain_structure(self):
        """Verify simple_filter_chain has correct filter structure."""
        from imagestag.filters import GaussianBlur, Brightness

        preset = PRESETS['simple_filter_chain']
        pipeline = preset.to_pipeline()

        assert len(pipeline.filters) == 2
        assert isinstance(pipeline.filters[0], GaussianBlur)
        assert isinstance(pipeline.filters[1], Brightness)
        assert pipeline.filters[0].radius == 2.0
        assert pipeline.filters[1].factor == 1.2

    def test_edge_detection_structure(self):
        """Verify edge_detection has correct filter structure."""
        from imagestag.filters import Canny

        preset = PRESETS['edge_detection']
        pipeline = preset.to_pipeline()

        assert len(pipeline.filters) == 1
        assert isinstance(pipeline.filters[0], Canny)
        assert pipeline.filters[0].threshold1 == 100
        assert pipeline.filters[0].threshold2 == 200

    def test_gradient_blend_has_two_inputs(self):
        """Verify gradient_blend preset has two input sources."""
        preset = PRESETS['gradient_blend']
        assert len(preset.inputs) == 2
        assert preset.inputs[0].name == 'source_a'
        assert preset.inputs[1].name == 'source_b'

    def test_face_detection_uses_group_image(self):
        """Verify face_detection uses the group sample image."""
        preset = PRESETS['face_detection']
        assert preset.inputs[0].sample_image == 'group'

    def test_circle_detection_uses_coins_image(self):
        """Verify circle_detection uses the coins sample image."""
        preset = PRESETS['circle_detection']
        assert preset.inputs[0].sample_image == 'coins'


# =============================================================================
# SERIALIZATION TESTS - Test graph serialization roundtrip
# =============================================================================

class TestSerialization:
    """Test preset graph serialization."""

    @pytest.mark.parametrize(
        "preset_key",
        [p.key for p in ALL_PRESETS],
        ids=[p.key for p in ALL_PRESETS],
    )
    def test_graph_roundtrip(self, preset_key: str):
        """Graph should serialize and deserialize correctly."""
        preset = PRESETS[preset_key]

        # Build graph
        graph = preset.to_graph()

        # Serialize to JSON
        json_str = graph.to_json()

        # Deserialize
        restored = FilterGraph.from_json(json_str)

        # Re-serialize
        json_str2 = restored.to_json()

        # JSON should be equivalent (may differ in formatting)
        import json
        dict1 = json.loads(json_str)
        dict2 = json.loads(json_str2)

        assert dict1 == dict2, f"Serialization mismatch for {preset_key}"
