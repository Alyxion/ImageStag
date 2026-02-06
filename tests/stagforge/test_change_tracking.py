"""Tests for change tracking feature - Python unit tests.

Tests the change tracking fields (changeCounter, lastChangeTimestamp) on
layer and document models.
"""

import time
import pytest


class TestLayerChangeTracking:
    """Tests for layer change tracking fields."""

    def test_layer_has_change_tracking_fields(self):
        """BaseLayer model should have changeCounter and lastChangeTimestamp fields."""
        from stagforge.layers import BaseLayer

        # Check fields exist in model
        assert 'change_counter' in BaseLayer.model_fields
        assert 'last_change_timestamp' in BaseLayer.model_fields

        # Check aliases are correct (camelCase for JS)
        assert BaseLayer.model_fields['change_counter'].alias == 'changeCounter'
        assert BaseLayer.model_fields['last_change_timestamp'].alias == 'lastChangeTimestamp'

    def test_layer_default_values(self):
        """New layer should have default change tracking values."""
        from stagforge.layers import PixelLayer

        layer = PixelLayer(name="Test Layer", width=100, height=100)

        assert layer.change_counter == 0
        assert layer.last_change_timestamp == 0

    def test_layer_serialization_includes_change_tracking(self):
        """Layer serialization should include change tracking fields."""
        from stagforge.layers import PixelLayer

        layer = PixelLayer(
            name="Test Layer",
            width=100,
            height=100,
            change_counter=42,
            last_change_timestamp=1707123456789.0
        )

        data = layer.to_api_dict()

        assert data['changeCounter'] == 42
        assert data['lastChangeTimestamp'] == 1707123456789.0

    def test_layer_deserialization_restores_change_tracking(self):
        """Layer deserialization should restore change tracking fields."""
        from stagforge.layers import PixelLayer

        data = {
            'type': 'raster',
            'name': 'Test Layer',
            'width': 100,
            'height': 100,
            'changeCounter': 99,
            'lastChangeTimestamp': 1707123456789.0,
        }

        layer = PixelLayer.model_validate(data)

        assert layer.change_counter == 99
        assert layer.last_change_timestamp == 1707123456789.0

    def test_all_layer_types_have_change_tracking(self):
        """All layer types should have change tracking fields."""
        from stagforge.layers import PixelLayer, StaticSVGLayer, TextLayer, LayerGroup

        layer_classes = [PixelLayer, StaticSVGLayer, TextLayer, LayerGroup]

        for cls in layer_classes:
            assert 'change_counter' in cls.model_fields, f"{cls.__name__} missing change_counter"
            assert 'last_change_timestamp' in cls.model_fields, f"{cls.__name__} missing last_change_timestamp"


class TestDocumentChangeTracking:
    """Tests for document change tracking fields."""

    def test_document_has_change_tracking_fields(self):
        """Document model should have changeCounter and lastChangeTimestamp fields."""
        from stagforge.layers import Document

        # Check fields exist
        assert 'change_counter' in Document.model_fields
        assert 'last_change_timestamp' in Document.model_fields

        # Check aliases
        assert Document.model_fields['change_counter'].alias == 'changeCounter'
        assert Document.model_fields['last_change_timestamp'].alias == 'lastChangeTimestamp'

    def test_document_default_values(self):
        """New document should have default change tracking values."""
        from stagforge.layers import Document

        doc = Document(name="Test Doc", width=800, height=600)

        assert doc.change_counter == 0
        assert doc.last_change_timestamp == 0

    def test_document_serialization_includes_change_tracking(self):
        """Document serialization should include change tracking fields."""
        from stagforge.layers import Document

        doc = Document(
            name="Test Doc",
            width=800,
            height=600,
            change_counter=123,
            last_change_timestamp=1707123456789.0
        )

        data = doc.to_api_dict()

        assert data['changeCounter'] == 123
        assert data['lastChangeTimestamp'] == 1707123456789.0

    def test_document_deserialization_restores_change_tracking(self):
        """Document deserialization should restore change tracking fields."""
        from stagforge.layers import Document

        data = {
            '_version': 1,
            '_type': 'Document',
            'name': 'Test Doc',
            'width': 800,
            'height': 600,
            'layers': [],
            'changeCounter': 456,
            'lastChangeTimestamp': 1707123456789.0,
        }

        doc = Document.from_api_dict(data)

        assert doc.change_counter == 456
        assert doc.last_change_timestamp == 1707123456789.0


class TestChangeTrackingAPI:
    """Tests for the /changes API endpoint structure."""

    def test_changes_endpoint_exists(self, api_client):
        """The /changes endpoint should exist (returns 404 for no session, not 405)."""
        response = api_client.get("/sessions/nonexistent-id/documents/current/changes")
        # Should be 404 (session not found) not 405 (method not allowed)
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data.get("detail", "").lower() or "session" in data.get("detail", "").lower()

    def test_changes_endpoint_requires_session(self, api_client):
        """The /changes endpoint should require a valid session."""
        response = api_client.get("/sessions/current/documents/current/changes")
        assert response.status_code == 404
        # Should indicate no session found
        data = response.json()
        assert "session" in data.get("detail", "").lower() or "no active" in data.get("detail", "").lower()


class TestLayerTypeChangeTracking:
    """Tests for change tracking across different layer types."""

    def test_pixel_layer_change_tracking_roundtrip(self):
        """PixelLayer should preserve change tracking through serialize/deserialize."""
        from stagforge.layers import PixelLayer

        original = PixelLayer(
            name="Pixel Layer",
            width=100,
            height=100,
            change_counter=10,
            last_change_timestamp=1707123456000.0
        )

        # Serialize to dict
        data = original.to_api_dict(include_content=False)

        # Deserialize
        restored = PixelLayer.model_validate(data)

        assert restored.change_counter == original.change_counter
        assert restored.last_change_timestamp == original.last_change_timestamp

    def test_text_layer_change_tracking_roundtrip(self):
        """TextLayer should preserve change tracking through serialize/deserialize."""
        from stagforge.layers import TextLayer

        original = TextLayer(
            name="Text Layer",
            width=200,
            height=50,
            text="Hello",
            change_counter=25,
            last_change_timestamp=1707123456500.0
        )

        data = original.to_api_dict(include_content=False)
        restored = TextLayer.model_validate(data)

        assert restored.change_counter == original.change_counter
        assert restored.last_change_timestamp == original.last_change_timestamp

    def test_svg_layer_change_tracking_roundtrip(self):
        """StaticSVGLayer should preserve change tracking through serialize/deserialize."""
        from stagforge.layers import StaticSVGLayer

        original = StaticSVGLayer(
            name="SVG Layer",
            width=150,
            height=150,
            svg_content="<svg></svg>",
            change_counter=5,
            last_change_timestamp=1707123456250.0
        )

        data = original.to_api_dict(include_content=False)
        restored = StaticSVGLayer.model_validate(data)

        assert restored.change_counter == original.change_counter
        assert restored.last_change_timestamp == original.last_change_timestamp

    def test_layer_group_change_tracking_roundtrip(self):
        """LayerGroup should preserve change tracking through serialize/deserialize."""
        from stagforge.layers import LayerGroup

        original = LayerGroup(
            name="Group",
            change_counter=3,
            last_change_timestamp=1707123456100.0
        )

        data = original.to_api_dict()
        restored = LayerGroup.model_validate(data)

        assert restored.change_counter == original.change_counter
        assert restored.last_change_timestamp == original.last_change_timestamp
