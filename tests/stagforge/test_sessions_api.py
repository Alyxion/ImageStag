"""Tests for the sessions API with multi-document support."""

import pytest
from datetime import datetime

from stagforge.sessions import (
    SessionManager,
    EditorSession,
    DocumentInfo,
    LayerInfo,
    SessionState,
)


class TestLayerInfo:
    """Tests for LayerInfo model."""

    def test_layer_info_defaults(self):
        """Test LayerInfo with default values."""
        layer = LayerInfo(id="layer-1", name="Layer 1")
        assert layer.id == "layer-1"
        assert layer.name == "Layer 1"
        assert layer.visible == True
        assert layer.locked == False
        assert layer.opacity == 1.0
        assert layer.blend_mode == "normal"
        assert layer.type == "raster"
        assert layer.parent_id is None

    def test_layer_info_to_dict(self):
        """Test LayerInfo serialization."""
        layer = LayerInfo(
            id="layer-1",
            name="Test Layer",
            visible=False,
            locked=True,
            opacity=0.5,
            blend_mode="multiply",
            type="vector",
            width=100,
            height=200,
            offset_x=10,
            offset_y=20,
            parent_id="group-1",
        )
        data = layer.to_dict()
        assert data["id"] == "layer-1"
        assert data["name"] == "Test Layer"
        assert data["visible"] == False
        assert data["locked"] == True
        assert data["opacity"] == 0.5
        assert data["blend_mode"] == "multiply"
        assert data["type"] == "vector"
        assert data["width"] == 100
        assert data["height"] == 200
        assert data["offset_x"] == 10
        assert data["offset_y"] == 20
        assert data["parent_id"] == "group-1"


class TestDocumentInfo:
    """Tests for DocumentInfo model."""

    def test_document_info_defaults(self):
        """Test DocumentInfo with default values."""
        doc = DocumentInfo(id="doc-1", name="Document 1")
        assert doc.id == "doc-1"
        assert doc.name == "Document 1"
        assert doc.width == 800
        assert doc.height == 600
        assert doc.layers == []
        assert doc.active_layer_id is None
        assert doc.is_modified == False

    def test_document_info_with_layers(self):
        """Test DocumentInfo with layers."""
        layers = [
            LayerInfo(id="layer-1", name="Layer 1"),
            LayerInfo(id="layer-2", name="Layer 2"),
        ]
        doc = DocumentInfo(
            id="doc-1",
            name="Test Doc",
            width=1024,
            height=768,
            layers=layers,
            active_layer_id="layer-1",
        )
        assert len(doc.layers) == 2
        assert doc.layers[0].name == "Layer 1"
        assert doc.active_layer_id == "layer-1"

    def test_document_to_summary(self):
        """Test DocumentInfo summary serialization."""
        layers = [
            LayerInfo(id="layer-1", name="Layer 1"),
            LayerInfo(id="layer-2", name="Layer 2"),
        ]
        doc = DocumentInfo(
            id="doc-1",
            name="Test Doc",
            width=1024,
            height=768,
            layers=layers,
            active_layer_id="layer-1",
            is_modified=True,
        )
        summary = doc.to_summary()
        assert summary["id"] == "doc-1"
        assert summary["name"] == "Test Doc"
        assert summary["width"] == 1024
        assert summary["height"] == 768
        assert summary["layer_count"] == 2
        assert summary["active_layer_id"] == "layer-1"
        assert summary["is_modified"] == True
        assert "created_at" in summary
        assert "modified_at" in summary

    def test_document_to_detail(self):
        """Test DocumentInfo detailed serialization."""
        layers = [
            LayerInfo(id="layer-1", name="Layer 1", type="raster"),
            LayerInfo(id="layer-2", name="Layer 2", type="vector"),
        ]
        doc = DocumentInfo(
            id="doc-1",
            name="Test Doc",
            width=1024,
            height=768,
            layers=layers,
        )
        detail = doc.to_detail()
        assert detail["id"] == "doc-1"
        assert detail["name"] == "Test Doc"
        assert len(detail["layers"]) == 2
        assert detail["layers"][0]["name"] == "Layer 1"
        assert detail["layers"][0]["type"] == "raster"
        assert detail["layers"][1]["name"] == "Layer 2"
        assert detail["layers"][1]["type"] == "vector"


class TestSessionState:
    """Tests for SessionState model."""

    def test_session_state_defaults(self):
        """Test SessionState with default values."""
        state = SessionState()
        assert state.documents == []
        assert state.active_document_id is None
        assert state.active_tool == "brush"
        assert state.foreground_color == "#000000"
        assert state.background_color == "#FFFFFF"
        assert state.zoom == 1.0

    def test_get_active_document(self):
        """Test getting active document from state."""
        docs = [
            DocumentInfo(id="doc-1", name="Doc 1"),
            DocumentInfo(id="doc-2", name="Doc 2"),
        ]
        state = SessionState(
            documents=docs,
            active_document_id="doc-2",
        )
        active = state.get_active_document()
        assert active is not None
        assert active.id == "doc-2"
        assert active.name == "Doc 2"

    def test_get_active_document_none(self):
        """Test getting active document when none is active."""
        state = SessionState()
        assert state.get_active_document() is None

    def test_get_active_document_invalid_id(self):
        """Test getting active document with invalid ID."""
        docs = [DocumentInfo(id="doc-1", name="Doc 1")]
        state = SessionState(
            documents=docs,
            active_document_id="nonexistent",
        )
        assert state.get_active_document() is None


class TestEditorSession:
    """Tests for EditorSession model."""

    def test_editor_session_defaults(self):
        """Test EditorSession with default values."""
        session = EditorSession(id="session-1")
        assert session.id == "session-1"
        assert isinstance(session.created_at, datetime)
        assert isinstance(session.last_activity, datetime)
        assert session.state is not None
        assert session.client is None
        assert session.editor is None

    def test_session_to_summary(self):
        """Test EditorSession summary serialization."""
        docs = [
            DocumentInfo(id="doc-1", name="My Document"),
        ]
        state = SessionState(
            documents=docs,
            active_document_id="doc-1",
            active_tool="eraser",
            foreground_color="#FF0000",
        )
        session = EditorSession(id="session-1", state=state)
        summary = session.to_summary()
        assert summary["id"] == "session-1"
        assert summary["document_count"] == 1
        assert summary["active_document_id"] == "doc-1"
        assert summary["active_document_name"] == "My Document"
        assert summary["active_tool"] == "eraser"
        assert summary["foreground_color"] == "#FF0000"
        assert "created_at" in summary
        assert "last_activity" in summary

    def test_session_to_detail(self):
        """Test EditorSession detailed serialization."""
        layers = [LayerInfo(id="layer-1", name="Background")]
        docs = [
            DocumentInfo(id="doc-1", name="Doc 1", layers=layers),
            DocumentInfo(id="doc-2", name="Doc 2"),
        ]
        state = SessionState(
            documents=docs,
            active_document_id="doc-1",
        )
        session = EditorSession(id="session-1", state=state)
        detail = session.to_detail()
        assert detail["id"] == "session-1"
        assert len(detail["documents"]) == 2
        assert detail["documents"][0]["name"] == "Doc 1"
        assert len(detail["documents"][0]["layers"]) == 1
        assert detail["documents"][1]["name"] == "Doc 2"
        assert detail["active_document_id"] == "doc-1"

    def test_update_activity(self):
        """Test updating session activity timestamp."""
        session = EditorSession(id="session-1")
        old_activity = session.last_activity
        import time
        time.sleep(0.01)  # Small delay
        session.update_activity()
        assert session.last_activity >= old_activity


class TestSessionManager:
    """Tests for SessionManager."""

    def test_register_new_session(self):
        """Test registering a new session."""
        manager = SessionManager()
        session = manager.register("session-1")
        assert session.id == "session-1"
        assert manager.get("session-1") is session

    def test_register_existing_session(self):
        """Test registering an existing session updates it."""
        manager = SessionManager()
        session1 = manager.register("session-1")
        session2 = manager.register("session-1", client="client", editor="editor")
        assert session1 is session2
        assert session2.client == "client"
        assert session2.editor == "editor"

    def test_unregister_session(self):
        """Test unregistering a session."""
        manager = SessionManager()
        manager.register("session-1")
        assert manager.get("session-1") is not None
        manager.unregister("session-1")
        assert manager.get("session-1") is None

    def test_get_all_sessions(self):
        """Test getting all sessions."""
        manager = SessionManager()
        manager.register("session-1")
        manager.register("session-2")
        manager.register("session-3")
        sessions = manager.get_all()
        assert len(sessions) == 3
        ids = {s.id for s in sessions}
        assert ids == {"session-1", "session-2", "session-3"}

    def test_update_state_documents(self):
        """Test updating session state with documents."""
        manager = SessionManager()
        manager.register("session-1")

        state_update = {
            "active_tool": "brush",
            "foreground_color": "#FF0000",
            "active_document_id": "doc-1",
            "documents": [
                {
                    "id": "doc-1",
                    "name": "Test Document",
                    "width": 1024,
                    "height": 768,
                    "is_modified": True,
                    "layers": [
                        {
                            "id": "layer-1",
                            "name": "Background",
                            "type": "raster",
                            "visible": True,
                            "opacity": 1.0,
                        },
                        {
                            "id": "layer-2",
                            "name": "Layer 1",
                            "type": "vector",
                            "parentId": None,
                        },
                    ],
                },
            ],
        }

        manager.update_state("session-1", state_update)

        session = manager.get("session-1")
        assert session.state.active_tool == "brush"
        assert session.state.foreground_color == "#FF0000"
        assert session.state.active_document_id == "doc-1"
        assert len(session.state.documents) == 1

        doc = session.state.documents[0]
        assert doc.id == "doc-1"
        assert doc.name == "Test Document"
        assert doc.width == 1024
        assert doc.height == 768
        assert doc.is_modified == True
        assert len(doc.layers) == 2

        assert doc.layers[0].id == "layer-1"
        assert doc.layers[0].name == "Background"
        assert doc.layers[0].type == "raster"
        assert doc.layers[1].id == "layer-2"
        assert doc.layers[1].name == "Layer 1"
        assert doc.layers[1].type == "vector"

    def test_update_state_nonexistent_session(self):
        """Test updating state for nonexistent session does nothing."""
        manager = SessionManager()
        # Should not raise
        manager.update_state("nonexistent", {"active_tool": "brush"})

    def test_session_summary_includes_active_doc_name(self):
        """Test that session summary includes active document name."""
        manager = SessionManager()
        manager.register("session-1")

        manager.update_state("session-1", {
            "active_document_id": "doc-1",
            "documents": [
                {"id": "doc-1", "name": "My Artwork", "layers": []},
            ],
        })

        session = manager.get("session-1")
        summary = session.to_summary()
        assert summary["active_document_name"] == "My Artwork"

    def test_layer_group_type(self):
        """Test that layer groups are properly identified."""
        manager = SessionManager()
        manager.register("session-1")

        manager.update_state("session-1", {
            "documents": [
                {
                    "id": "doc-1",
                    "name": "Doc",
                    "layers": [
                        {"id": "group-1", "name": "Group", "type": "group"},
                        {"id": "layer-1", "name": "Layer", "type": "raster", "parentId": "group-1"},
                    ],
                },
            ],
        })

        session = manager.get("session-1")
        doc = session.state.documents[0]
        assert doc.layers[0].type == "group"
        assert doc.layers[1].parent_id == "group-1"

    def test_get_all_sorted_by_activity(self):
        """Test that sessions are returned sorted by most recent activity."""
        import time
        manager = SessionManager()

        # Register sessions with small delays
        s1 = manager.register("session-1")
        time.sleep(0.01)
        s2 = manager.register("session-2")
        time.sleep(0.01)
        s3 = manager.register("session-3")

        # session-3 should be first (most recent)
        sessions = manager.get_all()
        assert sessions[0].id == "session-3"
        assert sessions[1].id == "session-2"
        assert sessions[2].id == "session-1"

        # Update session-1 activity
        time.sleep(0.01)
        s1.update_activity()

        # Now session-1 should be first
        sessions = manager.get_all()
        assert sessions[0].id == "session-1"

    def test_get_most_recent(self):
        """Test getting the most recently active session."""
        import time
        manager = SessionManager()

        # No sessions - should return None
        assert manager.get_most_recent() is None

        # Register sessions
        s1 = manager.register("session-1")
        time.sleep(0.01)
        s2 = manager.register("session-2")

        # session-2 should be most recent
        assert manager.get_most_recent().id == "session-2"

        # Update session-1 activity
        time.sleep(0.01)
        s1.update_activity()

        # Now session-1 should be most recent
        assert manager.get_most_recent().id == "session-1"

    def test_get_or_default_with_session_id(self):
        """Test get_or_default returns session by ID when provided."""
        manager = SessionManager()
        manager.register("session-1")
        manager.register("session-2")

        # Should get specific session
        session = manager.get_or_default("session-1")
        assert session is not None
        assert session.id == "session-1"

    def test_get_or_default_without_session_id(self):
        """Test get_or_default returns most recent when no ID provided."""
        import time
        manager = SessionManager()

        manager.register("session-1")
        time.sleep(0.01)
        manager.register("session-2")

        # Should get most recent session (session-2)
        session = manager.get_or_default(None)
        assert session is not None
        assert session.id == "session-2"

    def test_get_or_default_no_sessions(self):
        """Test get_or_default returns None when no sessions exist."""
        manager = SessionManager()
        assert manager.get_or_default(None) is None

    def test_get_or_default_invalid_session_id(self):
        """Test get_or_default returns None for invalid session ID."""
        manager = SessionManager()
        manager.register("session-1")
        assert manager.get_or_default("nonexistent") is None
