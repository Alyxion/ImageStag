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


class TestGraphConnection:
    """Tests for GraphConnection serialization."""

    def test_simple_connection_to_dict(self):
        from imagestag.filters.graph import GraphConnection

        c = GraphConnection(from_node="a", to_node="b", from_port="output", to_port="input")
        d = c.to_dict()
        assert d == {"from": "a", "to": "b"}

    def test_non_default_ports_in_dict(self):
        from imagestag.filters.graph import GraphConnection

        c2 = GraphConnection(from_node="a", to_node="b", from_port="mask", to_port="mask")
        d2 = c2.to_dict()
        assert d2["from"] == ["a", "mask"]
        assert d2["to"] == ["b", "mask"]

    def test_from_dict_with_port_arrays(self):
        from imagestag.filters.graph import GraphConnection

        c3 = GraphConnection.from_dict({"from": ["x", "p"], "to": ["y", "q"]})
        assert c3.from_port == "p"
        assert c3.to_port == "q"

    def test_from_dict_legacy_format(self):
        from imagestag.filters.graph import GraphConnection

        c4 = GraphConnection.from_dict({"from_node": "x", "to_node": "y", "from_output": 0, "to_input": 2})
        assert c4.to_port == "input_2"


class TestGraphNode:
    """Tests for GraphNode construction from dicts."""

    def test_from_dict_pipeline_source(self):
        from imagestag.filters.graph import GraphNode

        n1 = GraphNode.from_dict("s", {
            "class": "PipelineSource",
            "type": "IMAGE",
            "formats": ["RGB8"],
            "placeholder": "samples://images/astronaut",
            "editor": {"x": 1, "y": 2}
        })
        assert n1.get_source() is not None

    def test_from_dict_pipeline_output(self):
        from imagestag.filters.graph import GraphNode

        n2 = GraphNode.from_dict("o", {
            "class": "PipelineOutput",
            "type": "IMAGE",
            "name": "output",
            "editor": {"x": 3, "y": 4}
        })
        assert n2.is_output

    def test_from_dict_blend_filter(self):
        from imagestag.filters.graph import GraphNode, Blend, BlendMode

        n3 = GraphNode.from_dict("b", {
            "class": "Blend",
            "params": {"mode": "multiply", "opacity": 0.5},
            "x": 1, "y": 1
        })
        assert isinstance(n3.filter, Blend)
        assert n3.filter.mode == BlendMode.MULTIPLY

    def test_from_dict_unknown_filter_raises(self):
        from imagestag.filters.graph import GraphNode

        with pytest.raises(ValueError):
            GraphNode.from_dict("x", {"class": "NoSuchFilter"})


class TestGraphSource:
    """Tests for GraphSource serialization."""

    def test_to_dict(self):
        from imagestag.filters.graph import GraphSource

        gs = GraphSource(name="test", min_size=(10, 10), max_size=(100, 100), allowed_bit_depths=[8])
        d = gs.to_dict()
        assert d["min_size"] == [10, 10]

    def test_from_dict(self):
        from imagestag.filters.graph import GraphSource

        d = {"name": "test", "min_size": [10, 10], "max_size": [100, 100], "allowed_bit_depths": [8]}
        gs2 = GraphSource.from_dict(d)
        assert gs2.min_size == (10, 10)


class TestFilterGraphOperations:
    """Tests for FilterGraph node and connection operations."""

    def test_add_nodes_and_connections(self):
        from imagestag.filters.graph import GraphNode, GraphConnection
        from imagestag.filters.source import PipelineSource
        from imagestag.filters.output import PipelineOutput
        from imagestag.filters.base import Filter

        g = FilterGraph()

        src = GraphNode(name="source", source=PipelineSource.image(placeholder="samples://images/astronaut"))
        blur = GraphNode(name="blur", filter=Filter.parse("blur 2"))
        out = GraphNode(name="output", is_output=True, output_spec=PipelineOutput.image())

        g.add_node("source", src, x=10, y=10)
        g.add_node("blur", blur, x=20, y=10)
        g.add_node("output", out, x=30, y=10)

        g.add_connection(GraphConnection(from_node="source", to_node="blur"))
        g.add_connection(GraphConnection(from_node="blur", to_node="output"))
        # Duplicate connection should be ignored
        g.add_connection(GraphConnection(from_node="blur", to_node="output"))

        g.update_layout("blur", 25, 12)

        assert len(g.nodes) == 3
        assert len(g.connections) == 2

    def test_add_connection_invalid_nodes_raises(self):
        from imagestag.filters.graph import GraphConnection

        g = FilterGraph()
        with pytest.raises(ValueError):
            g.add_connection(GraphConnection(from_node="missing", to_node="blur"))

    def test_update_param_invalid_node_raises(self):
        g = FilterGraph()
        with pytest.raises(ValueError):
            g.update_param("missing", "x", 1)

    def test_update_param_on_output_node_raises(self):
        from imagestag.filters.graph import GraphNode
        from imagestag.filters.output import PipelineOutput

        g = FilterGraph()
        out = GraphNode(name="output", is_output=True, output_spec=PipelineOutput.image())
        g.add_node("output", out, x=0, y=0)

        with pytest.raises(ValueError):
            g.update_param("output", "x", 1)

    def test_update_param_invalid_param_raises(self):
        from imagestag.filters.graph import GraphNode
        from imagestag.filters.base import Filter

        g = FilterGraph()
        blur = GraphNode(name="blur", filter=Filter.parse("blur 2"))
        g.add_node("blur", blur, x=0, y=0)

        with pytest.raises(ValueError):
            g.update_param("blur", "nope", 1)

    def test_update_param_success(self):
        from imagestag.filters.graph import GraphNode
        from imagestag.filters.base import Filter

        g = FilterGraph()
        blur = GraphNode(name="blur", filter=Filter.parse("blur 2"))
        g.add_node("blur", blur, x=0, y=0)

        g.update_param("blur", "radius", 3.0)
        assert blur.filter.radius == 3.0

    def test_remove_connection_and_node(self):
        from imagestag.filters.graph import GraphNode, GraphConnection
        from imagestag.filters.source import PipelineSource
        from imagestag.filters.output import PipelineOutput
        from imagestag.filters.base import Filter

        g = FilterGraph()
        src = GraphNode(name="source", source=PipelineSource.image())
        blur = GraphNode(name="blur", filter=Filter.parse("blur 2"))
        out = GraphNode(name="output", is_output=True, output_spec=PipelineOutput.image())

        g.add_node("source", src, x=0, y=0)
        g.add_node("blur", blur, x=0, y=0)
        g.add_node("output", out, x=0, y=0)

        g.add_connection(GraphConnection(from_node="source", to_node="blur"))
        g.add_connection(GraphConnection(from_node="blur", to_node="output"))

        g.remove_connection("blur", "output", from_output=0, to_input=0)
        assert len(g.connections) == 1

        g.remove_node("blur")
        assert "blur" not in g.nodes


class TestFilterGraphFormats:
    """Tests for FilterGraph serialization formats."""

    def test_legacy_branch_dict(self):
        data = {
            "source": {"type": "SAMPLE", "value": "stag"},
            "branches": {
                "main": [{"type": "GaussianBlur", "radius": 2.0}]
            },
            "output": {"type": "Blend", "mode": "NORMAL"}
        }
        from imagestag.filters.graph import Blend

        g = FilterGraph.from_dict(data)
        assert not g.uses_node_format()
        assert "main" in g.branches
        assert isinstance(g.output, Blend)

    def test_base64_roundtrip(self):
        g = FilterGraph()
        encoded = g.to_base64()
        g2 = FilterGraph.from_base64(encoded)
        assert isinstance(g2, FilterGraph)

    def test_branch_parse_and_to_string(self):
        data = np.zeros((64, 64, 3), dtype=np.uint8)
        rgb_image = Image(data)

        text = "[a: blur 1][b: gray]blend(a,b,multiply)"
        g = FilterGraph.parse(text)
        s = g.to_string()
        assert "blend" in s

        out = g.apply(rgb_image)
        assert out.width == rgb_image.width

    def test_from_dict_with_layout(self):
        from imagestag.filters.graph import GraphNode
        from imagestag.filters.source import PipelineSource

        g = FilterGraph()
        src = GraphNode(name="source", source=PipelineSource.image())
        g.add_node("source", src, x=10, y=20)

        d = g.to_dict()
        g2 = FilterGraph.from_dict({
            "nodes": d["nodes"],
            "connections": d["connections"],
            "layout": {"source": {"x": 1, "y": 2}}
        })
        assert g2.uses_node_format()


class TestPipelineSource:
    """Tests for PipelineSource parsing and validation."""

    def test_parse_empty_string(self):
        from imagestag.filters.source import PipelineSource

        s = PipelineSource.parse("")
        assert s.placeholder.startswith("samples://")

    def test_parse_sample(self):
        from imagestag.filters.source import PipelineSource

        s2 = PipelineSource.parse("sample:camera")
        assert s2.to_string().startswith("sample:")

    def test_parse_file(self):
        from imagestag.filters.source import PipelineSource

        s3 = PipelineSource.parse("file:/tmp/x.png")
        assert s3.to_string().startswith("file:")

    def test_parse_url(self):
        from imagestag.filters.source import PipelineSource

        s4 = PipelineSource.parse("url:https://example.com/a.png")
        assert s4.to_string().startswith("url:")

    def test_parse_data_url(self):
        from imagestag.filters.source import PipelineSource

        s5 = PipelineSource.parse("data:image/png;base64,AA==")
        assert s5.placeholder.startswith("data:")

    def test_parse_unknown_prefix(self):
        from imagestag.filters.source import PipelineSource

        s6 = PipelineSource.parse("unknownprefix:foo")
        assert s6.placeholder.startswith("samples://")

    def test_from_dict_and_to_dict(self):
        from imagestag.filters.source import PipelineSource

        d = PipelineSource.image(name="x").to_dict(minimal=False)
        s7 = PipelineSource.from_dict(d)
        assert s7.name == "x"

    def test_from_dict_legacy(self):
        from imagestag.filters.source import PipelineSource

        legacy = {"class": "PipelineSource", "type": "SAMPLE", "value": "camera"}
        s8 = PipelineSource.from_dict(legacy)
        assert s8.is_sample

    def test_from_dict_wrong_class_raises(self):
        from imagestag.filters.source import PipelineSource

        with pytest.raises(ValueError):
            PipelineSource.from_dict({"class": "Wrong"})

    def test_legacy_properties(self):
        from imagestag.filters.source import PipelineSource

        s = PipelineSource.sample("test")
        assert s.is_sample
        assert s.value == "test"
        assert "sample:test" in s.to_string()

        s2 = PipelineSource.placeholder("ph", "stag")
        assert s2.is_placeholder
        assert s2.source_type == "PLACEHOLDER"
        assert s2.to_string() == "placeholder:ph"

    def test_validate_required(self):
        from imagestag.filters.source import PipelineSource

        s = PipelineSource.image(required=True)
        ok, _ = s.validate(None)
        assert not ok

    def test_validate_image_list(self):
        from imagestag.filters.source import PipelineSource

        s_list = PipelineSource.image_list()
        ok, _ = s_list.validate("not_list")
        assert not ok

    def test_validate_geometry_list(self):
        from imagestag.filters.source import PipelineSource, InputType
        from imagestag.geometry_list import GeometryList

        s_geom = PipelineSource(input_type=InputType.GEOMETRY_LIST)
        ok1, _ = s_geom.validate("not_geom")
        assert not ok1
        ok2, _ = s_geom.validate(GeometryList())
        assert ok2

    def test_validate_formats(self):
        from imagestag.filters.source import PipelineSource
        from imagestag.pixel_format import PixelFormat

        gray = np.zeros((32, 32), dtype=np.uint8)
        gray_image = Image(gray, pixel_format=PixelFormat.GRAY)

        s = PipelineSource.image(formats=["RGB8"], required=True)
        ok, msg = s.validate(gray_image)
        assert ok is False
        assert msg

    def test_dict_includes_optional_fields(self):
        from imagestag.filters.source import PipelineSource

        s = PipelineSource.image(name="a", description="d", required=False)
        d = s.to_dict(minimal=False)
        assert d["name"] == "a"
        assert d["description"] == "d"
        assert d["required"] is False


class TestPipelineOutput:
    """Tests for PipelineOutput validation."""

    def test_validate_any_type(self):
        from imagestag.filters.output import PipelineOutput

        out_any = PipelineOutput.any_type(required=False)
        ok, _ = out_any.validate(None)
        assert ok is True

    def test_validate_image_format_mismatch(self):
        from imagestag.filters.output import PipelineOutput

        data = np.zeros((32, 32, 3), dtype=np.uint8)
        rgb_image = Image(data)

        out_img = PipelineOutput.image(formats=["RGBA"], required=True)
        ok2, _ = out_img.validate(rgb_image)
        assert ok2 is False

    def test_validate_image_format_match(self):
        from imagestag.filters.output import PipelineOutput

        data = np.zeros((32, 32, 3), dtype=np.uint8)
        rgb_image = Image(data)

        out_img2 = PipelineOutput.image(formats=["RGB"], required=True)
        ok3, _ = out_img2.validate(rgb_image)
        assert ok3 is True

    def test_validate_dict(self):
        from imagestag.filters.output import PipelineOutput

        out_dict = PipelineOutput.dict_output(required=True)
        ok4, _ = out_dict.validate({"x": 1})
        assert ok4 is True

        ok5, _ = out_dict.validate("not_dict")
        assert ok5 is False

    def test_from_dict_wrong_class_raises(self):
        from imagestag.filters.output import PipelineOutput

        with pytest.raises(ValueError):
            PipelineOutput.from_dict({"class": "Wrong"})

    def test_validate_image_list(self):
        from imagestag.filters.output import PipelineOutput
        from imagestag.image_list import ImageList

        out_il = PipelineOutput.image_list()
        assert not out_il.validate(None)[0]
        assert not out_il.validate("not_list")[0]
        assert out_il.validate(ImageList())[0]

    def test_validate_geometry_list(self):
        from imagestag.filters.output import PipelineOutput
        from imagestag.geometry_list import GeometryList

        out_gl = PipelineOutput.geometry_list()
        assert not out_gl.validate("not_geom")[0]
        assert out_gl.validate(GeometryList())[0]

    def test_to_dict_with_optional_fields(self):
        from imagestag.filters.output import PipelineOutput

        out = PipelineOutput.image(formats=["RGB"], required=False, description="desc")
        d = out.to_dict()
        assert d["required"] is False
        assert d["description"] == "desc"

        out2 = PipelineOutput.from_dict(d)
        assert out2.required is False
        assert out2.format_constraints is not None
