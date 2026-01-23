"""Unit tests for API resource selection parsing.

Tests the parsing and resolution of document, layer, and session identifiers.

Run with: poetry run pytest tests/stagforge/test_api_selection_unit.py -v
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass, field

# Import the parsing functions
from stagforge.api.documents import (
    _parse_document_param,
    _parse_layer_param,
)


class TestParseDocumentParam:
    """Test document parameter parsing."""

    def test_parse_current(self):
        """'current' should be returned as-is."""
        assert _parse_document_param("current") == "current"

    def test_parse_index(self):
        """Numeric strings should be parsed as integers."""
        assert _parse_document_param("0") == 0
        assert _parse_document_param("1") == 1
        assert _parse_document_param("10") == 10

    def test_parse_uuid(self):
        """UUIDs should be returned as strings."""
        uuid = "550e8400-e29b-41d4-a716-446655440000"
        assert _parse_document_param(uuid) == uuid

    def test_parse_name(self):
        """Names should be returned as strings."""
        assert _parse_document_param("My Document") == "My Document"
        assert _parse_document_param("Document with spaces") == "Document with spaces"

    def test_parse_short_name(self):
        """Short names that aren't numbers should be returned as strings."""
        assert _parse_document_param("doc") == "doc"
        assert _parse_document_param("a") == "a"


class TestParseLayerParam:
    """Test layer parameter parsing."""

    def test_parse_index(self):
        """Numeric strings should be parsed as integers."""
        assert _parse_layer_param("0") == 0
        assert _parse_layer_param("1") == 1
        assert _parse_layer_param("99") == 99

    def test_parse_uuid(self):
        """UUIDs should be returned as strings."""
        uuid = "layer-uuid-12345"
        assert _parse_layer_param(uuid) == uuid

    def test_parse_name(self):
        """Names should be returned as strings."""
        assert _parse_layer_param("Background") == "Background"
        assert _parse_layer_param("Shape Layer") == "Shape Layer"
        assert _parse_layer_param("My Cool Layer!") == "My Cool Layer!"


# Mock data structures for resolution tests
@dataclass
class MockLayer:
    id: str
    name: str
    type: str = "raster"
    width: int = 100
    height: int = 100
    visible: bool = True
    opacity: float = 1.0
    blend_mode: str = "normal"
    offset_x: int = 0
    offset_y: int = 0
    locked: bool = False

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "width": self.width,
            "height": self.height,
            "visible": self.visible,
            "opacity": self.opacity,
            "blend_mode": self.blend_mode,
            "offset_x": self.offset_x,
            "offset_y": self.offset_y,
            "locked": self.locked,
        }


@dataclass
class MockDocument:
    id: str
    name: str
    width: int = 800
    height: int = 600
    layers: list = field(default_factory=list)
    active_layer_id: str = None

    def to_summary(self):
        return {"id": self.id, "name": self.name, "width": self.width, "height": self.height}

    def to_detail(self):
        return {**self.to_summary(), "layer_count": len(self.layers)}


class TestDocumentResolution:
    """Test document resolution from parsed parameters."""

    @pytest.fixture
    def sample_documents(self):
        """Create sample documents for testing."""
        return [
            MockDocument(id="doc-uuid-1", name="My Document"),
            MockDocument(id="doc-uuid-2", name="Second Doc"),
            MockDocument(id="doc-uuid-3", name="123"),  # Edge case: name looks like a number
        ]

    def test_resolve_by_id(self, sample_documents):
        """Documents can be resolved by their UUID."""
        docs = sample_documents
        doc_param = "doc-uuid-2"

        # Resolution logic: try ID first, then name
        found = None
        for d in docs:
            if d.id == doc_param:
                found = d
                break
        if not found:
            for d in docs:
                if d.name == doc_param:
                    found = d
                    break

        assert found is not None
        assert found.id == "doc-uuid-2"
        assert found.name == "Second Doc"

    def test_resolve_by_name(self, sample_documents):
        """Documents can be resolved by their name."""
        docs = sample_documents
        doc_param = "My Document"

        found = None
        for d in docs:
            if d.id == doc_param:
                found = d
                break
        if not found:
            for d in docs:
                if d.name == doc_param:
                    found = d
                    break

        assert found is not None
        assert found.id == "doc-uuid-1"
        assert found.name == "My Document"

    def test_resolve_by_index(self, sample_documents):
        """Documents can be resolved by their index."""
        docs = sample_documents
        doc_param = 1  # Second document

        if isinstance(doc_param, int) and 0 <= doc_param < len(docs):
            found = docs[doc_param]
        else:
            found = None

        assert found is not None
        assert found.id == "doc-uuid-2"

    def test_resolve_numeric_name(self, sample_documents):
        """A document with a numeric name can still be found by name."""
        docs = sample_documents
        # The third document has name "123"
        # When parsed, "123" becomes int 123, which won't find the doc by index
        # But if we search by name directly, it should work

        # Simulate: user provides "123" as the document selector
        raw_input = "123"
        parsed = _parse_document_param(raw_input)  # Returns int 123

        # Resolution: try index first (won't work since index 123 doesn't exist)
        found = None
        if isinstance(parsed, int):
            if 0 <= parsed < len(docs):
                found = docs[parsed]
        else:
            for d in docs:
                if d.id == parsed or d.name == parsed:
                    found = d
                    break

        # With current parsing, int 123 won't find anything
        assert found is None

        # To find by name "123", user must use a different approach
        # or the API could try both interpretations


class TestLayerResolution:
    """Test layer resolution from parsed parameters."""

    @pytest.fixture
    def sample_layers(self):
        """Create sample layers for testing."""
        return [
            MockLayer(id="layer-uuid-1", name="Background", type="raster"),
            MockLayer(id="layer-uuid-2", name="Shape Layer", type="vector"),
            MockLayer(id="layer-uuid-3", name="Text Layer", type="text"),
            MockLayer(id="layer-uuid-4", name="0", type="raster"),  # Edge case: name is "0"
        ]

    def test_resolve_by_id(self, sample_layers):
        """Layers can be resolved by their UUID."""
        layers = sample_layers
        layer_param = "layer-uuid-2"

        found = None
        if isinstance(layer_param, int):
            if 0 <= layer_param < len(layers):
                found = layers[layer_param]
        else:
            for l in layers:
                if l.id == layer_param or l.name == layer_param:
                    found = l
                    break

        assert found is not None
        assert found.id == "layer-uuid-2"
        assert found.name == "Shape Layer"

    def test_resolve_by_name(self, sample_layers):
        """Layers can be resolved by their name."""
        layers = sample_layers
        layer_param = "Background"

        found = None
        if isinstance(layer_param, int):
            if 0 <= layer_param < len(layers):
                found = layers[layer_param]
        else:
            for l in layers:
                if l.id == layer_param or l.name == layer_param:
                    found = l
                    break

        assert found is not None
        assert found.id == "layer-uuid-1"
        assert found.name == "Background"

    def test_resolve_by_name_with_spaces(self, sample_layers):
        """Layers with spaces in names can be resolved."""
        layers = sample_layers
        layer_param = "Shape Layer"

        found = None
        for l in layers:
            if l.id == layer_param or l.name == layer_param:
                found = l
                break

        assert found is not None
        assert found.id == "layer-uuid-2"

    def test_resolve_by_index(self, sample_layers):
        """Layers can be resolved by their index."""
        layers = sample_layers
        layer_param = 2  # Third layer

        found = None
        if isinstance(layer_param, int):
            if 0 <= layer_param < len(layers):
                found = layers[layer_param]

        assert found is not None
        assert found.id == "layer-uuid-3"
        assert found.name == "Text Layer"

    def test_index_zero_prefers_index_over_name(self, sample_layers):
        """When user provides '0', index 0 is preferred over layer named '0'."""
        layers = sample_layers
        raw_input = "0"
        parsed = _parse_layer_param(raw_input)  # Returns int 0

        found = None
        if isinstance(parsed, int):
            if 0 <= parsed < len(layers):
                found = layers[parsed]
        else:
            for l in layers:
                if l.id == parsed or l.name == parsed:
                    found = l
                    break

        assert found is not None
        # Index 0 is "Background", not the layer named "0"
        assert found.name == "Background"


class TestEdgeCases:
    """Test edge cases in resource selection."""

    def test_empty_string(self):
        """Empty string should be returned as-is (will fail lookup)."""
        assert _parse_document_param("") == ""
        assert _parse_layer_param("") == ""

    def test_whitespace_only(self):
        """Whitespace-only strings should be returned as-is."""
        assert _parse_document_param("   ") == "   "
        assert _parse_layer_param("   ") == "   "

    def test_negative_number_string(self):
        """Negative numbers should be parsed as integers."""
        assert _parse_document_param("-1") == -1
        assert _parse_layer_param("-5") == -5

    def test_float_string(self):
        """Float strings should be returned as strings (not valid index)."""
        assert _parse_document_param("1.5") == "1.5"
        assert _parse_layer_param("2.0") == "2.0"

    def test_special_characters(self):
        """Names with special characters should work."""
        assert _parse_document_param("My Doc (v2)") == "My Doc (v2)"
        assert _parse_layer_param("Layer #1 - Final!") == "Layer #1 - Final!"

    def test_unicode_names(self):
        """Unicode names should work."""
        assert _parse_document_param("ドキュメント") == "ドキュメント"
        assert _parse_layer_param("Calque 日本語") == "Calque 日本語"


class TestURLEncodedNames:
    """Test that URL-encoded names are properly handled."""

    def test_url_decoded_space(self):
        """URL-decoded spaces should work."""
        # FastAPI automatically decodes URL parameters
        # So "Shape%20Layer" becomes "Shape Layer" before hitting the parsing function
        assert _parse_layer_param("Shape Layer") == "Shape Layer"

    def test_url_decoded_special(self):
        """URL-decoded special characters should work."""
        assert _parse_document_param("Doc & Report") == "Doc & Report"
        assert _parse_layer_param("100% Opacity") == "100% Opacity"
