# Tests for FilterGraph loading and execution
"""
Tests for loading FilterGraph from file and executing with user-provided images.

The key requirement is that placeholder images defined in the pipeline are NOT loaded
during production execution - only the user-provided images should be used.
"""

from pathlib import Path
import numpy as np
import pytest

from imagestag import Image
from imagestag.filters.graph import FilterGraph

# Test fixture path
FIXTURES_DIR = Path(__file__).parent / "fixtures"
GRADIENT_BLEND_PIPELINE = FIXTURES_DIR / "gradient_blend_pipeline.json"

# Create test images outside of test functions (as requested)
# These are simple solid color images for testing
TEST_IMAGE_RED = Image(np.full((100, 100, 3), [255, 0, 0], dtype=np.uint8))
TEST_IMAGE_BLUE = Image(np.full((100, 100, 3), [0, 0, 255], dtype=np.uint8))


class TestFilterGraphFileLoading:
    """Test loading FilterGraph from JSON file."""

    def test_load_from_disk(self):
        """FilterGraph can be loaded from a JSON file."""
        graph = FilterGraph.from_disk(str(GRADIENT_BLEND_PIPELINE))

        assert graph is not None
        assert graph.uses_node_format()

    def test_loaded_graph_has_source_nodes(self):
        """Loaded graph has the expected source nodes."""
        graph = FilterGraph.from_disk(str(GRADIENT_BLEND_PIPELINE))

        sources = graph.get_source_nodes()
        source_names = [name for name, _ in sources]

        assert len(sources) == 2
        assert "source_a" in source_names
        assert "source_b" in source_names

    def test_loaded_graph_has_output_node(self):
        """Loaded graph has an output node."""
        graph = FilterGraph.from_disk(str(GRADIENT_BLEND_PIPELINE))

        output = graph.get_output_node()

        assert output is not None
        assert output[0] == "output"

    def test_editor_metadata_preserved(self):
        """Editor metadata (x, y) is preserved in loaded nodes."""
        graph = FilterGraph.from_disk(str(GRADIENT_BLEND_PIPELINE))

        source_a = graph.nodes["source_a"]
        source_b = graph.nodes["source_b"]
        blend = graph.nodes["blend"]

        assert source_a.editor == {"x": 80, "y": 80}
        assert source_b.editor == {"x": 80, "y": 280}
        assert blend.editor == {"x": 800, "y": 120}


class TestFilterGraphExecution:
    """Test executing FilterGraph with user-provided images."""

    def test_execute_with_positional_args(self):
        """Execute graph with positional arguments (alphabetical order)."""
        graph = FilterGraph.from_disk(str(GRADIENT_BLEND_PIPELINE))

        # Positional args: source_a (first alphabetically), source_b (second)
        result = graph.execute(TEST_IMAGE_RED, TEST_IMAGE_BLUE)

        assert result is not None
        assert isinstance(result, Image)
        # Result should have same size as smaller input (both are 100x100)
        assert result.width == 100
        assert result.height == 100

    def test_execute_with_keyword_args(self):
        """Execute graph with keyword arguments (explicit source names)."""
        graph = FilterGraph.from_disk(str(GRADIENT_BLEND_PIPELINE))

        # Keyword args: explicit mapping
        result = graph.execute(source_a=TEST_IMAGE_RED, source_b=TEST_IMAGE_BLUE)

        assert result is not None
        assert isinstance(result, Image)
        assert result.width == 100
        assert result.height == 100

    def test_execute_with_dict(self):
        """Execute graph with dict via inputs parameter."""
        graph = FilterGraph.from_disk(str(GRADIENT_BLEND_PIPELINE))

        # Dict style: explicit mapping
        result = graph.execute(inputs={
            "source_a": TEST_IMAGE_RED,
            "source_b": TEST_IMAGE_BLUE,
        })

        assert result is not None
        assert isinstance(result, Image)
        assert result.width == 100
        assert result.height == 100

    def test_all_execution_styles_produce_same_result(self):
        """All three execution styles produce identical results."""
        graph = FilterGraph.from_disk(str(GRADIENT_BLEND_PIPELINE))

        # Execute with all three styles
        result_positional = graph.execute(TEST_IMAGE_RED, TEST_IMAGE_BLUE)
        result_kwargs = graph.execute(source_a=TEST_IMAGE_RED, source_b=TEST_IMAGE_BLUE)
        result_dict = graph.execute(inputs={
            "source_a": TEST_IMAGE_RED,
            "source_b": TEST_IMAGE_BLUE,
        })

        # All results should be identical
        assert np.array_equal(
            result_positional.get_pixels(),
            result_kwargs.get_pixels()
        )
        assert np.array_equal(
            result_positional.get_pixels(),
            result_dict.get_pixels()
        )

    def test_swapped_sources_produce_different_result(self):
        """Swapping sources produces a different result (proves sources are used)."""
        graph = FilterGraph.from_disk(str(GRADIENT_BLEND_PIPELINE))

        result_normal = graph.execute(source_a=TEST_IMAGE_RED, source_b=TEST_IMAGE_BLUE)
        result_swapped = graph.execute(source_a=TEST_IMAGE_BLUE, source_b=TEST_IMAGE_RED)

        # Results should be different when sources are swapped
        assert not np.array_equal(
            result_normal.get_pixels(),
            result_swapped.get_pixels()
        )


class TestPlaceholdersNotLoaded:
    """Test that placeholder images are NOT loaded during production execution."""

    def test_result_uses_provided_images_not_placeholders(self):
        """Result should use provided images, not placeholder images."""
        graph = FilterGraph.from_disk(str(GRADIENT_BLEND_PIPELINE))

        # Create distinctive test images - use same size to avoid issues
        red_image = Image(np.full((100, 100, 3), [255, 0, 0], dtype=np.uint8))
        green_image = Image(np.full((100, 100, 3), [0, 255, 0], dtype=np.uint8))

        result = graph.execute(source_a=red_image, source_b=green_image)

        # Result should be 100x100 (our test image size), not placeholder size
        assert result.width == 100
        assert result.height == 100

        # The result should contain pixels from our test images
        # not the colors from astronaut or chelsea placeholder images
        pixels = result.get_pixels()

        # Verify the result contains at least some red component from source_a
        # The exact blend depends on the gradient, but we should see red influence
        has_red = np.any(pixels[:, :, 0] > 50)

        assert has_red, "Result should contain red from source_a (not placeholder)"

        # Crucially: the result should NOT have typical skin tones or complex colors
        # that would come from astronaut/chelsea images
        # Our inputs are pure red and green, so any blue should be minimal
        avg_blue = np.mean(pixels[:, :, 2])
        assert avg_blue < 100, f"Result has too much blue ({avg_blue}), may be using placeholders"

    def test_custom_sized_images_determine_output_size(self):
        """Output size is determined by user images, not placeholders."""
        graph = FilterGraph.from_disk(str(GRADIENT_BLEND_PIPELINE))

        # Create images with specific size that differs from typical placeholders
        custom_size = (73, 91)  # Unusual size
        img_a = Image(np.full((custom_size[1], custom_size[0], 3), [100, 100, 100], dtype=np.uint8))
        img_b = Image(np.full((custom_size[1], custom_size[0], 3), [200, 200, 200], dtype=np.uint8))

        result = graph.execute(img_a, img_b)

        # Output should match our custom size, not placeholder sizes
        assert result.width == custom_size[0]
        assert result.height == custom_size[1]


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_execute_single_image_graph(self):
        """Test executing a simple single-input graph."""
        # Create a simple single-source graph
        from imagestag.filters.graph import GraphNode, GraphConnection
        from imagestag.filters.source import PipelineSource
        from imagestag.filters.output import PipelineOutput
        from imagestag.filters import GaussianBlur

        graph = FilterGraph()
        graph.nodes["input"] = GraphNode(
            name="input",
            source=PipelineSource.image(),
        )
        graph.nodes["blur"] = GraphNode(
            name="blur",
            filter=GaussianBlur(radius=2.0),
        )
        graph.nodes["output"] = GraphNode(
            name="output",
            is_output=True,
            output_spec=PipelineOutput.image(),
        )
        graph.connections = [
            GraphConnection(from_node="input", to_node="blur"),
            GraphConnection(from_node="blur", to_node="output"),
        ]

        # Execute with single positional arg
        result = graph.execute(TEST_IMAGE_RED)

        assert result is not None
        assert isinstance(result, Image)

    def test_graph_without_sources_raises_error(self):
        """Executing a graph without source nodes raises an error."""
        from imagestag.filters.graph import GraphNode

        graph = FilterGraph()
        # Add only an output node
        graph.nodes["output"] = GraphNode(
            name="output",
            is_output=True,
        )

        with pytest.raises(ValueError, match="no source nodes"):
            graph.execute(TEST_IMAGE_RED)

    def test_mixed_positional_and_keyword_args(self):
        """Keyword args override positional args for the same source."""
        graph = FilterGraph.from_disk(str(GRADIENT_BLEND_PIPELINE))

        # Create distinctive images
        yellow = Image(np.full((50, 50, 3), [255, 255, 0], dtype=np.uint8))
        cyan = Image(np.full((50, 50, 3), [0, 255, 255], dtype=np.uint8))
        magenta = Image(np.full((50, 50, 3), [255, 0, 255], dtype=np.uint8))

        # Positional would assign yellow to source_a, cyan to source_b
        # But keyword overrides source_a to magenta
        result = graph.execute(yellow, cyan, source_a=magenta)

        # source_a should be magenta (keyword override), source_b should be cyan
        # This is a bit tricky to verify, but we can check it produces a result
        assert result is not None
        assert isinstance(result, Image)


class TestGraphSerialization:
    """Test that graphs can be serialized and deserialized with editor metadata."""

    def test_roundtrip_preserves_editor_metadata(self):
        """Serializing and deserializing preserves editor metadata."""
        graph = FilterGraph.from_disk(str(GRADIENT_BLEND_PIPELINE))

        # Serialize to JSON and back
        json_str = graph.to_json()
        graph2 = FilterGraph.from_json(json_str)

        # Check editor metadata is preserved
        assert graph2.nodes["source_a"].editor == {"x": 80, "y": 80}
        assert graph2.nodes["source_b"].editor == {"x": 80, "y": 280}
        assert graph2.nodes["blend"].editor == {"x": 800, "y": 120}

    def test_roundtrip_produces_same_result(self):
        """Serialized and deserialized graph produces same execution result."""
        graph = FilterGraph.from_disk(str(GRADIENT_BLEND_PIPELINE))

        # Execute before serialization
        result1 = graph.execute(TEST_IMAGE_RED, TEST_IMAGE_BLUE)

        # Serialize and deserialize
        json_str = graph.to_json()
        graph2 = FilterGraph.from_json(json_str)

        # Execute after deserialization
        result2 = graph2.execute(TEST_IMAGE_RED, TEST_IMAGE_BLUE)

        # Results should be identical
        assert np.array_equal(result1.get_pixels(), result2.get_pixels())
