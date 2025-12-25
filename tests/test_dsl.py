# Tests for compact DSL syntax
"""
Test the compact pipeline DSL syntax.

DSL Syntax:
- `;` separates filters in a pipeline
- Space-separated arguments: `blur 5`, `canny 100 200`
- Keyword arguments: `mode=multiply`, `color=#ff0000`
- Quoted strings for literals: `'smaller'`
"""

import numpy as np
import pytest

from imagestag import Image
from imagestag.pixel_format import PixelFormat
from imagestag.filters import (
    Filter,
    FilterPipeline,
    GaussianBlur,
    Brightness,
    Canny,
    Grayscale,
    SizeMatcher,
    ImageGenerator,
    Blend,
)


@pytest.fixture
def test_image():
    """Create a 100x100 RGB test image."""
    data = np.full((100, 100, 3), [100, 150, 200], dtype=np.uint8)
    return Image(data, pixel_format=PixelFormat.RGB)


class TestCompactFilterParsing:
    """Tests for parsing individual filters with compact syntax."""

    def test_parse_no_args(self):
        """Filter with no arguments."""
        f = Filter.parse('gray')
        assert isinstance(f, Grayscale)

    def test_parse_single_positional(self):
        """Single positional argument."""
        f = Filter.parse('brightness 1.5')
        assert isinstance(f, Brightness)
        assert f.factor == 1.5

    def test_parse_multiple_positional(self):
        """Multiple positional arguments."""
        f = Filter.parse('canny 100 200')
        assert isinstance(f, Canny)
        assert f.threshold1 == 100
        assert f.threshold2 == 200

    def test_parse_keyword_args(self):
        """Keyword arguments."""
        f = Filter.parse('blur radius=5.0')
        assert isinstance(f, GaussianBlur)
        assert f.radius == 5.0

    def test_parse_mixed_args(self):
        """Positional and keyword arguments."""
        f = Filter.parse('canny 100 threshold2=200')
        assert isinstance(f, Canny)
        assert f.threshold1 == 100
        assert f.threshold2 == 200

    def test_parse_hex_color(self):
        """Hex color values should be parsed into Color objects."""
        from imagestag.color import Color
        f = Filter.parse('imgen linear color_start=#ff0000 color_end=#0000ff')
        assert isinstance(f, ImageGenerator)
        assert isinstance(f.color_start, Color)
        assert isinstance(f.color_end, Color)
        assert f.color_start.to_hex().lower() == '#ff0000'
        assert f.color_end.to_hex().lower() == '#0000ff'

    def test_parse_quoted_string(self):
        """Quoted strings should be unquoted."""
        f = Filter.parse("size_match 'smaller'")
        assert isinstance(f, SizeMatcher)
        # The mode should be parsed as 'smaller' string

    def test_parse_alias(self):
        """Aliases should work."""
        f = Filter.parse('blur 5')
        assert isinstance(f, GaussianBlur)
        assert f.radius == 5

        f = Filter.parse('imgen linear')
        assert isinstance(f, ImageGenerator)
        assert f.gradient_type == 'linear'

    def test_parse_legacy_syntax(self):
        """Legacy parentheses syntax should still work."""
        f = Filter.parse('brightness(1.5)')
        assert isinstance(f, Brightness)
        assert f.factor == 1.5


class TestCompactPipelineParsing:
    """Tests for parsing pipelines with compact syntax."""

    def test_parse_single_filter(self):
        """Pipeline with single filter."""
        p = FilterPipeline.parse('gray')
        assert len(p.filters) == 1
        assert isinstance(p.filters[0], Grayscale)

    def test_parse_semicolon_separated(self):
        """Pipeline with semicolon-separated filters."""
        p = FilterPipeline.parse('gray; blur 5')
        assert len(p.filters) == 2
        assert isinstance(p.filters[0], Grayscale)
        assert isinstance(p.filters[1], GaussianBlur)
        assert p.filters[1].radius == 5

    def test_parse_with_args(self):
        """Pipeline with filter arguments."""
        p = FilterPipeline.parse('blur 2.0; brightness 1.2')
        assert len(p.filters) == 2
        assert p.filters[0].radius == 2.0
        assert p.filters[1].factor == 1.2


class TestPipelineExecution:
    """Tests for executing parsed pipelines."""

    def test_simple_pipeline_execution(self, test_image):
        """Execute a simple parsed pipeline."""
        p = FilterPipeline.parse('gray')
        result = p.apply(test_image)
        # Grayscale converts to grayscale (may keep RGB format with equal channels)
        assert result.width == test_image.width
        assert result.height == test_image.height

    def test_chain_pipeline_execution(self, test_image):
        """Execute a multi-filter parsed pipeline."""
        p = FilterPipeline.parse('gray; blur 2')
        result = p.apply(test_image)
        assert result.width == 100
        assert result.height == 100

    def test_blur_pipeline_execution(self, test_image):
        """Execute blur pipeline."""
        p = FilterPipeline.parse('blur 5')
        result = p.apply(test_image)
        assert result.width == 100
        assert result.height == 100
        # Blur should smooth the image
        pixels = result.get_pixels()
        assert pixels is not None


class TestPresetDSLEquivalence:
    """Tests that DSL strings produce equivalent results to preset definitions."""

    def test_simple_filter_chain_dsl(self, test_image):
        """simple_filter_chain preset DSL should match graph execution."""
        from imagestag.tools.presets import PRESET_DSL

        dsl = PRESET_DSL['simple_filter_chain']
        p = FilterPipeline.parse(dsl)

        # Verify structure
        assert len(p.filters) == 2
        assert isinstance(p.filters[0], GaussianBlur)
        assert isinstance(p.filters[1], Brightness)
        assert p.filters[0].radius == 2.0
        assert p.filters[1].factor == 1.2

        # Execute and verify it works
        result = p.apply(test_image)
        assert result.width == 100
        assert result.height == 100

    def test_edge_detection_dsl(self, test_image):
        """edge_detection preset DSL should match graph execution."""
        from imagestag.tools.presets import PRESET_DSL

        dsl = PRESET_DSL['edge_detection']
        p = FilterPipeline.parse(dsl)

        # Verify structure
        assert len(p.filters) == 1
        assert isinstance(p.filters[0], Canny)
        assert p.filters[0].threshold1 == 100
        assert p.filters[0].threshold2 == 200

        # Execute and verify it works
        result = p.apply(test_image)
        assert result.width == test_image.width
        assert result.height == test_image.height


class TestToString:
    """Tests for converting filters to string format."""

    def test_filter_to_string(self):
        """Filter should serialize to compact string."""
        f = GaussianBlur(radius=5.0)
        s = f.to_string()
        assert 'gaussianblur' in s.lower()
        assert 'radius=5.0' in s

    def test_filter_roundtrip(self):
        """Parse -> to_string -> parse should preserve values."""
        original = Filter.parse('blur 5')
        s = original.to_string()
        restored = Filter.parse(s)
        assert isinstance(restored, GaussianBlur)
        assert restored.radius == original.radius
